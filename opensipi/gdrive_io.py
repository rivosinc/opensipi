# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
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
    """Given items returned by Google Drive API.
    Prints them in a tabular way.
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
    """
    Scale bytes to its proper byte format
    e.g:
        1253656 => '1.20MB'
        1253656678 => '1.17GB'
    """
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if b < factor:
            return f"{b:.2f}{unit}{suffix}"
        b /= factor
    return f"{b:.2f}Y{suffix}"


class GdriveIO:
    """a class to initialize gdrive service"""

    def __init__(self, info):
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
        """"""
        creds = service_account.Credentials.from_service_account_file(
            filename=self.account_key, scopes=self.SCOPES
        )
        # return Google Drive API service
        return build("drive", "v3", credentials=creds)


class Gdrive:
    """a class of gdrive"""

    def __init__(self, info):
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
        """
        search inside a folder and return queried info
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
        """query folder id if exists"""
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
        """query file id if exists"""
        query = "name = '" + name + "' and trashed=false and '" + parent_folder_id + "' in parents"
        result = self.search(query)
        id = ""
        if len(result) > 1:
            raise NonUniqueFileInDrive(self.lg)
        elif len(result) == 1:
            id = result[0][0]  # id only
        return id

    def create_folder(self, folder_name, parent_folder_id):
        """
        create a folder and return its id
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
        """Create a gsheet and return its id."""
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
        """Upload a file to a folder."""
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
        """Download a file from a drive folder."""
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
        for key, value in response.cookies.items():
            if key.startswith("download_warning"):
                return value
        return None

    def __save_response_content(self, response, destination):
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
    """a class wrapper of GdriveIO"""

    def __init__(self, info):
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
        """make folders in the Grive and return its id"""
        # get project folder id
        self.proj_folder_id = self.__mk_folder(self.proj_name, self.root_drive_id)
        # get sim type folder id
        self.sim_type_folder_id = self.__mk_folder(self.sim_type_name, self.proj_folder_id)
        # get run folder id
        self.run_folder_id = self.__mk_folder(self.run_folder_name, self.sim_type_folder_id)

    def upload_folder(self, root):
        """Upload all files in a local folder."""
        # get a list of all files in the root directory
        # and its sub-directories
        dir_list = [
            os.path.join(path, name) for path, subdirs, files in os.walk(root) for name in files
        ]
        file_id_book, uni_file_type = self.upload_dir_list(root, dir_list)
        return file_id_book, uni_file_type

    def upload_folder_tgt_ext(self, root, tgt):
        """upload all files with a specified extension"""
        dir_list = [
            os.path.join(path, name)
            for path, subdirs, files in os.walk(root)
            for name in files
            if re.search(tgt, name)
        ]
        file_id_book, uni_file_type = self.upload_dir_list(root, dir_list)
        return file_id_book, uni_file_type

    def upload_dir_list(self, root, dir_list):
        """upload all files in the dir_list"""
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
        """Upload the pdf report to the drive."""
        file_name = get_str_after_last_symbol(dir, SL)
        parent_id = self.run_folder_id
        file_id = self.__upload_file(dir, parent_id, file_name)
        file_id_book = {"report": file_id}
        return file_id_book

    def download_file(self, name, parent_folder_id, dl_file_dir):
        """down a file from G drive"""
        query = "name = '" + name + "' and trashed=false and '" + parent_folder_id + "' in parents"
        self.drive.download_file(query, dl_file_dir)

    def get_summary_sheet_id(self, sheet_title, parent_id):
        """Create a gSheet if it doesn't exist."""
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
        """get folder id"""
        folder_id = self.drive.q_folder_id(name, parent_id)
        if folder_id == "":
            folder_id = self.drive.create_folder(name, parent_id)
            self.lg.debug("Folder " + name + " is created!")
        else:
            self.lg.debug("Folder " + name + " already exists!")
        return folder_id

    def __upload_file(self, dir, parent_id, file_name):
        """upload a file if it doesn't exist"""
        file_id = self.drive.q_file_id(file_name, parent_id)
        if file_id == "":
            file_id = self.drive.upload_file(dir, parent_id)
            self.lg.debug(file_name + " is uploaded to G drive " + self.run_folder_name)
        else:
            self.lg.debug(file_name + " already exists in G drive " + self.run_folder_name)
        return file_id
