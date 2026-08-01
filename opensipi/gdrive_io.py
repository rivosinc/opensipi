# SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
Description:
    This module handles Google Drive services.

    ``GdriveIO`` authorizes, ``Gdrive`` wraps the raw Drive API calls, and
``XtractResults2Drive`` puts them to work by mirroring a run's output folder
into Drive under ``project / sim type / run``.

    Creating anything goes through a query-then-create step, so re-uploading a
run reuses the folders and files already there rather than producing
duplicates. A name that turns out to be ambiguous is treated as an error rather
than guessed at, since picking the wrong one would silently scatter a run's
results.

References:
1. How to use Google Drive API in Python
https://www.thepythoncode.com/article/using-google-drive--api-in-python
"""

import os
import pickle
import re

import requests
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from tabulate import tabulate
from tqdm import tqdm

from opensipi.util.common import SL, get_str_after_last_symbol, rm_ext, unique_list
from opensipi.util.exceptions import NoneUniqueFolderInDrive, NonUniqueFileInDrive


def list_files(items):
    """Print items returned by the Google Drive API as a table.

    A debugging aid. The table is printed rather than returned.

    Args:
        items (list of dict): File resources as returned by the Drive API.
            Each is read for ``id``, ``name``, ``parents``, ``size``,
            ``mimeType``, and ``modifiedTime``.

    Note:
        The two fallbacks for a missing field catch the wrong exception types.
        A resource without ``parents`` or ``size`` raises ``KeyError``, which
        neither the ``NameError`` nor the ``TypeError`` handler intercepts, so
        the ``"N/A"`` placeholders are only reached when the field is present
        but null.
    """
    if not items:
        # empty drive
        print("No files found.")
    else:
        rows = []
        for item in items:
            # get the File ID
            id = item["id"]
            # get the name of file
            name = item["name"]
            try:
                # parent directory ID
                parents = item["parents"]
            except NameError:
                # has no parrents
                parents = "N/A"
            try:
                # get the size in nice bytes format (KB, MB, etc.)
                size = get_size_format(int(item["size"]))
            except TypeError:
                # not a file, may be a folder
                size = "N/A"
            # get the Google Drive type of file
            mime_type = item["mimeType"]
            # get last modified date time
            modified_time = item["modifiedTime"]
            # append everything to the list
            rows.append((id, name, parents, size, mime_type, modified_time))
        print("Files:")
        # convert to a human readable table
        table = tabulate(rows, headers=["ID", "Name", "Parents", "Size", "Type", "Modified Time"])
        # print the table
        print(table)


def get_size_format(b, factor=1024, suffix="B"):
    """Scale bytes to its proper byte format.

    e.g:
        1253656 => '1.20MB'
        1253656678 => '1.17GB'

    Args:
        b (int or float): The size to scale.
        factor (int, optional): Step between units. Defaults to ``1024``. Pass
            ``1000`` for decimal units.
        suffix (str, optional): Unit suffix. Defaults to ``"B"``.

    Returns:
        str: The size with two decimals and a unit prefix, the prefix rising
        until the value drops below ``factor``, capped at ``Y``.
    """
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if b < factor:
            return f"{b:.2f}{unit}{suffix}"
        b /= factor
    return f"{b:.2f}Y{suffix}"


class GdriveIO:
    """a class to initialize gdrive service

    Holds the credentials and the scopes, and builds an authorized Drive
    service from them. Two authorization paths are offered, one interactive and
    one unattended.
    """

    def __init__(self, info):
        """Record the credentials and the scopes to authorize with.

        Nothing is authorized here. Call one of the ``gdrive_auth_*`` methods
        to obtain a service.

        Args:
            info (dict): Google Drive access information.

                * ``account_key`` (str): Path to the credentials file, being a
                  service account key or an OAuth client secret depending on
                  which authorization path is used.
                * ``config_dir`` (str): Directory the cached end user token is
                  kept in.

        Attributes:
            SCOPES (list of str): The Drive permissions requested. Narrowing
                this list invalidates a cached end user token, so
                ``gdrive_token.pickle`` must then be deleted by hand.
        """
        # define variables
        self.account_key = info["account_key"]
        self.config_dir = info["config_dir"]
        # If modifying these scopes, delete the file token.pickle.
        self.SCOPES = [
            "https://www.googleapis.com/auth/drive.metadata.readonly",
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive.appdata",
        ]

    def gdrive_auth_end_user(self):
        """Authorize as the end user and return a Drive service.

        A token cached from a previous run is reused, and refreshed in place
        when it has expired. Only when no usable token exists is the browser
        consent flow started, so this is interactive on first use and silent
        afterwards. The token is written back to ``config_dir`` either way.

        Returns:
            googleapiclient.discovery.Resource: An authorized Drive v3 service.
        """
        creds = None
        # The file token.pickle stores the user's access and refresh
        # tokens, and is created automatically when the authorization
        # flow completes for the first time.
        token_dir = self.config_dir + "gdrive_token.pickle"
        if os.path.exists(token_dir):
            with open(token_dir, "rb") as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available,
        # let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.account_key, self.SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(token_dir, "wb") as token:
                pickle.dump(creds, token)
        # return Google Drive API service
        return build("drive", "v3", credentials=creds)

    def gdrive_auth_service_account(self):
        """Authorize as a service account and return a Drive service.

        Needs no consent and no cached token, so this is the path used for
        unattended runs. The target Drive folders must be shared with the
        service account's address.

        Returns:
            googleapiclient.discovery.Resource: An authorized Drive v3 service.
        """
        creds = service_account.Credentials.from_service_account_file(
            filename=self.account_key, scopes=self.SCOPES
        )
        # return Google Drive API service
        return build("drive", "v3", credentials=creds)


class Gdrive:
    """a class of gdrive

    Thin wrappers over the Drive API for the operations this application needs:
    searching, creating folders and sheets, and uploading and downloading
    files.
    """

    def __init__(self, info):
        """Authorize and prepare the download settings.

        Args:
            info (dict): Passed through to :class:`GdriveIO`, plus a ``log``
                key holding the run logger.

        Attributes:
            URL (str): Base URL used for downloads, which go through a plain
                HTTP session rather than the API client.
            CHUNK_SIZE (int): Download chunk size in bytes.

        Note:
            Authorization is hardwired to the service account path. The end
            user path is left commented out just above it.
        """
        # define variables
        self.lg = info["log"].getChild("/" + __name__)
        # define constants
        # base URL for download
        self.URL = "https://docs.google.com/uc?export=download"
        self.CHUNK_SIZE = 32768
        # gdrive IO
        # self.service = GdriveIO(info).gdrive_auth_end_user()
        self.service = GdriveIO(info).gdrive_auth_service_account()

    def search(self, query):
        """Search inside a folder and return queried info.

        Paging is followed to the end, so the result is complete rather than
        capped at one page.

        Args:
            query (str): A Drive API query string.

        Returns:
            list of tuple: One ``(id, name, mimeType)`` per match. Empty if
            nothing matched.
        """
        # search for the file
        result = []
        page_token = None
        while True:
            response = (
                self.service.files()
                .list(
                    q=query,
                    spaces="drive",
                    includeItemsFromAllDrives=True,
                    supportsAllDrives=True,
                    fields="nextPageToken, files(id, name, mimeType)",
                    pageToken=page_token,
                )
                .execute()
            )
            # iterate over filtered files
            for file in response.get("files", []):
                result.append((file["id"], file["name"], file["mimeType"]))
            page_token = response.get("nextPageToken", None)
            if not page_token:
                # no more files
                break
        return result

    def q_folder_id(self, name, parent_folder_id):
        """Query folder id if exists.

        Args:
            name (str): Folder name to look for.
            parent_folder_id (str): ID of the folder to look inside.

        Returns:
            str: The folder ID, or an empty string if there is no such folder.
            The caller distinguishes the two to decide whether to create it.

        Raises:
            NoneUniqueFolderInDrive: If more than one folder of that name
                exists in that parent, since there would be no safe way to pick
                one.
        """
        query = (
            "name = '"
            + name
            + "' and mimeType = "
            + "'application/vnd.google-apps.folder' and trashed=false and '"
            + parent_folder_id
            + "' in parents"
        )
        result = self.search(query)
        id = ""
        if len(result) > 1:
            raise NoneUniqueFolderInDrive(self.lg)
        elif len(result) == 1:
            id = result[0][0]  # id only
        return id

    def q_file_id(self, name, parent_folder_id):
        """Query file id if exists.

        Args:
            name (str): File name to look for, with extension.
            parent_folder_id (str): ID of the folder to look inside.

        Returns:
            str: The file ID, or an empty string if there is no such file.

        Raises:
            NonUniqueFileInDrive: If more than one file of that name exists in
                that parent.
        """
        query = "name = '" + name + "' and trashed=false and '" + parent_folder_id + "' in parents"
        result = self.search(query)
        id = ""
        if len(result) > 1:
            raise NonUniqueFileInDrive(self.lg)
        elif len(result) == 1:
            id = result[0][0]  # id only
        return id

    def create_folder(self, folder_name, parent_folder_id):
        """Create a folder and return its id.

        No check is made for an existing folder of the same name. Use
        :meth:`q_folder_id` first if that matters.

        Args:
            folder_name (str): Name of the folder to create.
            parent_folder_id (str): ID of the folder to create it in.

        Returns:
            str: ID of the new folder.
        """
        # folder details
        folder_metadata = {
            "name": folder_name,  # string
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_folder_id],  # list of string
        }
        # create the folder
        file = (
            self.service.files()
            .create(body=folder_metadata, supportsAllDrives=True, fields="id")
            .execute()
        )
        # get the folder id
        folder_id = file.get("id")
        return folder_id

    def create_gsheet(self, file_name, folder_id):
        """Create a gsheet and return its id.

        Creates a native Google Sheet, not an uploaded spreadsheet file.

        Args:
            file_name (str): Title of the sheet to create.
            folder_id (str): ID of the folder to create it in.

        Returns:
            str: ID of the new sheet.
        """
        file_metadata = {
            "name": file_name,  # with extension
            "parents": [folder_id],  # list of string
            "mimeType": "application/vnd.google-apps.spreadsheet",
        }
        file = (
            self.service.files()
            .create(body=file_metadata, supportsAllDrives=True, fields="id")
            .execute()
        )
        # get the file id
        file_id = file.get("id")
        return file_id

    def upload_file(self, file_dir, folder_id):
        """Upload a file to a folder.

        The upload is resumable, so a large result file survives a transient
        interruption. The name in Drive is taken from the local file name.

        Args:
            file_dir (str): Full path of the local file.
            folder_id (str): ID of the folder to upload into.

        Returns:
            str: ID of the uploaded file.
        """
        # first, define file metadata, such as the name and
        # the parent folder ID
        file_name = get_str_after_last_symbol(file_dir, SL)
        file_metadata = {
            "name": file_name,  # with extension
            "parents": [folder_id],  # list of string
        }
        # upload
        media = MediaFileUpload(file_dir, resumable=True)
        file = (
            self.service.files()
            .create(body=file_metadata, supportsAllDrives=True, media_body=media, fields="id")
            .execute()
        )
        # get the file id
        file_id = file.get("id")
        return file_id

    def download_file(self, query, dir):
        """Download a file from a drive folder.

        The first match wins if the query is ambiguous. The file is made
        readable by anyone with the link before it is fetched, since the
        download goes through a plain HTTP session that carries no credentials.

        Args:
            query (str): A Drive API query string identifying the file.
            dir (str): Full path to write the downloaded file to.

        Note:
            The sharing permission is granted permanently and is not revoked
            afterwards.
        """
        # search for the file by name
        search_result = self.search(query)
        if search_result:
            # get the GDrive ID of the file
            file_id = search_result[0][0]
            # make it shareable
            self.service.permissions().create(
                body={"role": "reader", "type": "anyone"}, supportsAllDrives=True, fileId=file_id
            ).execute()
            # download file
            self.__download_file_from_google_drive(file_id, dir)
        else:
            self.lg.debug("The file was not found!")

    def __download_file_from_google_drive(self, id, destination):
        """Stream a shared Drive file to disk.

        Drive interposes a confirmation page on larger files rather than
        serving them directly, so the request is retried with the confirmation
        token when one comes back.

        Args:
            id (str): Drive file ID. The file must already be shared.
            destination (str): Full path to write to.
        """
        # init a HTTP session
        session = requests.Session()
        # make a request
        response = session.get(self.URL, params={"id": id}, stream=True)
        print("[+] Downloading", response.url)
        # get confirmation token
        token = self.__get_confirm_token(response)
        if token:
            params = {"id": id, "confirm": token}
            response = session.get(self.URL, params=params, stream=True)
        # download to disk
        self.__save_response_content(response, destination)

    def __get_confirm_token(self, response):
        """Pull the download confirmation token out of the response cookies.

        Args:
            response (requests.Response): The response to inspect.

        Returns:
            str or None: The token value, or ``None`` if Drive served the file
            directly and set no warning cookie.
        """
        for key, value in response.cookies.items():
            if key.startswith("download_warning"):
                return value
        return None

    def __save_response_content(self, response, destination):
        """Write a streamed response to disk with a progress bar.

        Args:
            response (requests.Response): A streaming response.
            destination (str): Full path to write to.

        Raises:
            IndexError: If the response carries no ``content-disposition``
                file name to parse.
        """
        # get the file size from Content-length response header
        file_size = int(response.headers.get("Content-Length", 0))
        # extract Content disposition from response headers
        content_disposition = response.headers.get("content-disposition")
        # parse filename
        filename = re.findall('filename="(.+)"', content_disposition)[0]
        print("[+] File size:", file_size)
        print("[+] File name:", filename)
        progress = tqdm(
            response.iter_content(self.CHUNK_SIZE),
            f"Downloading {filename}",
            total=file_size,
            unit="Byte",
            unit_scale=True,
            unit_divisor=1024,
        )
        with open(destination, "wb") as f:
            for chunk in progress:
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    # update the progress bar
                    progress.update(len(chunk))
        progress.close()


class XtractResults2Drive:
    """a class wrapper of GdriveIO

    Mirrors one run's output into Google Drive, under a
    ``project / sim type / run`` folder tree that is created on demand.
    """

    def __init__(self, info):
        """Authorize and ensure this run's folder tree exists in Drive.

        The folder tree is created here, so an instance is ready to upload into
        as soon as it is built.

        Args:
            info (dict): Upload related information.

                * ``root_drive_id`` (str): ID of the Drive folder the project
                  tree is created under.
                * ``proj_name`` (str): Project name, the first tree level.
                * ``sim_type_name`` (str): Simulation type, the second level.
                * ``run_time`` (str): Run time stamp, part of the run folder
                  name.
                * ``usr_id`` (str): User ID, also part of the run folder name,
                  so that runs from different users stay distinct.
                * ``log`` (logging.Logger): The run logger.
                * ``account_key`` and ``config_dir``: Passed through to
                  :class:`Gdrive`.
        """
        # define variables
        self.root_drive_id = info["root_drive_id"]
        self.proj_name = info["proj_name"]
        self.run_time = info["run_time"]
        self.usr_id = info["usr_id"]
        self.sim_type_name = info["sim_type_name"]
        self.lg = info["log"].getChild("/" + __name__)
        self.run_folder_name = "Run_" + self.run_time + "_" + self.usr_id
        self.result_folder_name = "Result"
        self.report_folder_name = "Report"
        # initialize drive service
        self.drive = Gdrive(info)
        self.lg.debug("Start uploading results to G drive!")
        # get id for all folders
        self.__get_folder_id()

    def __get_folder_id(self):
        """Make folders in the Gdrive and return its id.

        Walks the ``project / sim type / run`` tree top down, reusing each
        level if it is already there. The IDs are stored on the instance as
        ``proj_folder_id``, ``sim_type_folder_id``, and ``run_folder_id``.
        """
        # get project folder id
        self.proj_folder_id = self.__mk_folder(self.proj_name, self.root_drive_id)
        # get sim type folder id
        self.sim_type_folder_id = self.__mk_folder(self.sim_type_name, self.proj_folder_id)
        # get run folder id
        self.run_folder_id = self.__mk_folder(self.run_folder_name, self.sim_type_folder_id)

    def upload_folder(self, root):
        """Upload all files in a local folder.

        Args:
            root (str): Local folder to walk, sub-directories included.

        Returns:
            tuple: A 2-tuple ``(file_id_book, uni_file_type)``, as described in
            :meth:`upload_dir_list`.
        """
        # get a list of all files in the root directory
        # and its sub-directories
        dir_list = [
            os.path.join(path, name) for path, subdirs, files in os.walk(root) for name in files
        ]
        file_id_book, uni_file_type = self.upload_dir_list(root, dir_list)
        return file_id_book, uni_file_type

    def upload_folder_tgt_ext(self, root, tgt):
        """Upload all files with a specified extension.

        Args:
            root (str): Local folder to walk, sub-directories included.
            tgt (str): Regular expression matched against each file name. It is
                searched for, not anchored, so a bare extension works.

        Returns:
            tuple: A 2-tuple ``(file_id_book, uni_file_type)``, as described in
            :meth:`upload_dir_list`.
        """
        dir_list = [
            os.path.join(path, name)
            for path, subdirs, files in os.walk(root)
            for name in files
            if re.search(tgt, name)
        ]
        file_id_book, uni_file_type = self.upload_dir_list(root, dir_list)
        return file_id_book, uni_file_type

    def upload_dir_list(self, root, dir_list):
        """Upload all files in the dir_list.

        Each file's path relative to ``root`` is recreated as folders under the
        run folder, so the Drive copy mirrors the local layout. Files are
        grouped by simulation key, taken from the file name up to the run time
        stamp, which is what lets the summary sheet put one simulation per row.

        Args:
            root (str): Local folder the paths are relative to.
            dir_list (list of str): Full paths of the files to upload.

        Returns:
            tuple: A 2-tuple ``(file_id_book, uni_file_type)``, where
            ``file_id_book`` maps a simulation key to a list of
            ``[file_name, file_id, folder_name]`` entries, and
            ``uni_file_type`` lists the distinct containing folder names in
            first-seen order.

        Note:
            Only one level of nesting is recreated. The loop reassigns its
            remaining path to a list rather than to a string, so its condition
            can never hold a second time and a file nested two or more levels
            deep is uploaded one level down, under the folder name of the
            level above it. A file sitting directly in ``root`` raises
            ``NameError``, or is silently attributed to the previous file's
            folder if one was already seen.
        """
        file_id_book = {}
        file_type = []
        for dir in dir_list:
            file_name = get_str_after_last_symbol(dir, SL)
            parent_id = self.run_folder_id
            dir_local = dir.replace(root, "")
            while SL in dir_local:
                tmp = dir_local.split(SL)
                folder_name = tmp[0]
                dir_local = tmp[1:]
                parent_id = self.__mk_folder(folder_name, parent_id)
            file_id = self.__upload_file(dir, parent_id, file_name)
            # get file id book
            file_key = rm_ext(file_name).split("_" + self.run_time)[0]
            if file_key in file_id_book:
                file_id_book[file_key].append([file_name, file_id, folder_name])
            else:
                file_id_book[file_key] = []
                file_id_book[file_key].append([file_name, file_id, folder_name])
            file_type.append(folder_name)
        uni_file_type = unique_list(file_type)
        return file_id_book, uni_file_type

    def upload_report(self, dir):
        """Upload the pdf report to the drive.

        The report goes straight into the run folder rather than into a
        sub-folder.

        Args:
            dir (str): Full path of the local report file.

        Returns:
            dict: ``{"report": file_id}``, shaped this way so the summary sheet
            can look the report up by name.
        """
        file_name = get_str_after_last_symbol(dir, SL)
        parent_id = self.run_folder_id
        file_id = self.__upload_file(dir, parent_id, file_name)
        file_id_book = {"report": file_id}
        return file_id_book

    def download_file(self, name, parent_folder_id, dl_file_dir):
        """Download a file from G drive by name.

        Args:
            name (str): File name to look for, with extension.
            parent_folder_id (str): ID of the folder to look inside.
            dl_file_dir (str): Full path to write the file to.
        """
        query = "name = '" + name + "' and trashed=false and '" + parent_folder_id + "' in parents"
        self.drive.download_file(query, dl_file_dir)

    def get_summary_sheet_id(self, sheet_title, parent_id):
        """Create a gSheet if it doesn't exist.

        The sheet lives in a project folder of its own, outside the per-run
        tree, so that successive runs of a project accumulate into one summary.

        Args:
            sheet_title (str): Title of the summary sheet.
            parent_id (str): ID of the folder the project folder is created
                under.

        Returns:
            str: ID of the existing or newly created sheet.
        """
        # first create a project folder
        sheet_folder_id = self.__mk_folder(self.proj_name, parent_id)
        # put the summary sheet in the project folder
        file_id = self.drive.q_file_id(sheet_title, sheet_folder_id)
        if file_id == "":
            file_id = self.drive.create_gsheet(sheet_title, sheet_folder_id)
            self.lg.debug(sheet_title + " is created in G drive 1_output_gsheets")
        else:
            self.lg.debug(sheet_title + " already exists in G drive 1_output_gsheets")
        return file_id

    def __mk_folder(self, name, parent_id):
        """Get a folder id, creating the folder if it is not there yet.

        Args:
            name (str): Folder name.
            parent_id (str): ID of the folder to look in and create under.

        Returns:
            str: ID of the existing or newly created folder.
        """
        folder_id = self.drive.q_folder_id(name, parent_id)
        if folder_id == "":
            folder_id = self.drive.create_folder(name, parent_id)
            self.lg.debug("Folder " + name + " is created!")
        else:
            self.lg.debug("Folder " + name + " already exists!")
        return folder_id

    def __upload_file(self, dir, parent_id, file_name):
        """Upload a file if it doesn't exist.

        An already uploaded file is left as it is rather than replaced, so
        re-running an upload does not re-transfer what is already there.

        Args:
            dir (str): Full path of the local file.
            parent_id (str): ID of the folder to upload into.
            file_name (str): Name to look for in that folder.

        Returns:
            str: ID of the existing or newly uploaded file.
        """
        file_id = self.drive.q_file_id(file_name, parent_id)
        if file_id == "":
            file_id = self.drive.upload_file(dir, parent_id)
            self.lg.debug(file_name + " is uploaded to G drive " + self.run_folder_name)
        else:
            self.lg.debug(file_name + " already exists in G drive " + self.run_folder_name)
        return file_id
