# SPDX-FileCopyrightText: © 2025 Google LLC
#
# SPDX-License-Identifier: Apache-2.0

"""functions for google IO services"""

import pickle
import datetime
import os
import csv
from urllib.parse import urlparse, parse_qs
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from PyCode.utility import pwt_msgbox_print as msgbox
from PyCode.tab_writter import tab_create_irdrop
from PyCode.tab_writter import tab_upload_resmeas, tab_upload_limited_irdrop
from PyCode.tab_writter import tab_upload_multibrd_limited_irdrop
from PyCode.tab_writter import summary_create, summary_update


#
CLIENT_SECRET_FILE = "client_secret.json"


def create_service(client_secret_file, api_name, api_version, *scopes):
    """create google api service"""
    print(client_secret_file, api_name, api_version, scopes, sep="-")
    client_secret_file_ = client_secret_file
    api_service_name = api_name
    api_version_ = api_version
    scopes_ = [scope for scope in scopes[0]]
    print(scopes_)

    cred = None

    pickle_file = f"token_{api_service_name}_{api_version_}.pickle"
    # print(pickle_file)

    if os.path.exists(pickle_file):
        with open(pickle_file, "rb") as token:
            cred = pickle.load(token)

    if not cred or not cred.valid:
        if cred and cred.expired and cred.refresh_token:
            cred.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_file_, scopes_)
            cred = flow.run_local_server()

        with open(pickle_file, "wb") as token:
            pickle.dump(cred, token)

    try:
        # need the discovery_service_url for exe file to work
        discovery_service_url = (
            "https://sheets.googleapis.com/$discovery/rest?version=v4"
        )

        if api_service_name == "drive":
            discovery_service_url = (
                "https://www.googleapis.com/discovery/v1/apis/drive/v3/rest"
            )
            # service = build(API_SERVICE_NAME, API_VERSION, credentials=cred)
            service = build(
                api_service_name,
                api_version_,
                credentials=cred,
                discoveryServiceUrl=discovery_service_url,
            )
        else:
            service = build(
                api_service_name,
                api_version_,
                credentials=cred,
                discoveryServiceUrl=discovery_service_url,
            )
        print(api_service_name, "service created successfully")
        return service
    except RuntimeError as e:
        print("Unable to connect.")
        print(e)
        return None


def simulation_setting_reader(
    spreadsheet_url,
    tab_name,
    pwt_msgbox,
    single_board_workflow=["single_ir", "single_resmeas", "single_limitedir"],
    multi_board_workflow=["multibrd_ir", "multibrd_limitedir"],
):
    """read the settings from input gsheet"""

    api_service_name = "sheets"
    api_version = "v4"
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    service = create_service(CLIENT_SECRET_FILE, api_service_name, api_version, scope)
    cha = list(spreadsheet_url)
    spreadsheet_id = "".join(cha[39:83])

    try:
        merge_list = find_merged_cells(service, spreadsheet_id, tab_name)
    except ValueError:
        merge_list = ""
        print("There are no merge cells in the input spreadsheet")

    # single_board_workflow=('single_ir','single_resmeas','single_limitedir')
    # multi_board_workflow=('multibrd_ir')
    header_row = 1
    response = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, majorDimension="COLUMNS", range=tab_name)
        .execute()
    )
    tab_data = response["values"]

    unique_keys_col = tab_data[0][header_row:]
    unique_keys = []
    duplicates = []

    # check for duplicatekeys ##########################
    for item in unique_keys_col:
        if item == "":
            continue  # Skip empty strings
        if item in unique_keys:
            item = item.strip()
            duplicates.append(item)
        else:
            unique_keys.append(item)

        if duplicates:
            msgbox(pwt_msgbox, f"Duplicates keys found: {duplicates}")
            raise KeyError

    enabled_col = tab_data[1][header_row:]
    enabled_indices = [
        index for index, value in enumerate(enabled_col) if value == "TRUE"
    ]
    workflow_col = tab_data[2][header_row:]
    brd_path_col = tab_data[3][header_row:]
    stackup_info_col = tab_data[4][header_row:]
    pwt_path_col = tab_data[5][header_row:]
    out_gsheet_url_col = tab_data[6][header_row:]
    out_gsheet_tab_col = tab_data[7][header_row:]
    drive_folder_url_col = tab_data[8][header_row:]
    simulation_options_col = tab_data[9][header_row:]
    project_folder_col = tab_data[10][header_row:]
    # out_gsheet_url=tab_data[4][header_col:]

    # sheet_indices = [index + header_row for index in enabled_indices]
    sim_list = []

    # iterate through enabled items ##########################
    for index in enabled_indices:
        unique_key = unique_keys_col[index].strip()
        workflow = workflow_col[index].strip()

        if unique_key:
            # msgbox(PWT_msgbox,f'Key {unique_key} is enabled')

            # ========== read settings for SINGLE BOARD workflow ==================

            if workflow.lower() in single_board_workflow:
                if brd_path_col[index]:
                    brd_path = {"Brd_path": brd_path_col[index].strip()}
                else:
                    msgbox(
                        pwt_msgbox,
                        f"Brd file path is not provided for sim key {unique_key}",
                    )
                    raise FileNotFoundError

                try:
                    # stack up is optional to have
                    stackup_info = {"Stackup_info": stackup_info_col[index].strip()}
                except ValueError:
                    stackup_info = ""

                try:
                    pwt_path = pwt_path_col[index].strip()  # PWT is optional to have
                    if not os.path.exists(pwt_path):
                        msgbox(
                            pwt_msgbox,
                            "Cannot find the defined powertree file. Please check path again!",
                        )
                        raise FileNotFoundError
                except FileNotFoundError:
                    pwt_path = ""

                try:
                    # output gsheet is also optional
                    out_gsheet_url = out_gsheet_url_col[index].strip()
                except ValueError:
                    out_gsheet_url = ""
                try:
                    out_gsheet_tab = out_gsheet_tab_col[index].strip()
                except ValueError:
                    out_gsheet_tab = ""
                if (out_gsheet_url == "" or out_gsheet_tab == "") != (
                    out_gsheet_url == "" and out_gsheet_tab == ""
                ):
                    msgbox(pwt_msgbox, "Either gsheet url or gsheet tab is empty")
                    raise ValueError

                try:
                    # drive folder url is optional
                    drive_folder_url = drive_folder_url_col[index].strip()
                except ValueError:
                    drive_folder_url = ""

                try:
                    # simulation options is optional
                    simulation_options = simulation_options_col[index].strip()
                except ValueError:
                    simulation_options = ""

                try:
                    # project folder path is optional
                    project_folder = project_folder_col[index].strip()
                except ValueError:
                    project_folder = ""

                per_key_info = {
                    "unique_key": unique_key,
                    "workflow": workflow,
                    "Brd_path": brd_path,
                    "Stackup_info": stackup_info,
                    "PWT_path": pwt_path,
                    "out_gsheet_url": out_gsheet_url,
                    "out_gsheet_tab": out_gsheet_tab,
                    "drive_folder_url": drive_folder_url,
                    "simulation_options": simulation_options,
                    "project_folder": project_folder,
                }
                sim_list.append(per_key_info)

            # ========== read settings for MULTIBOARD workflow ==================

            if workflow.lower() in multi_board_workflow:
                brd_path = {}  # intialize dict
                stackup_info = {}
                simulation_options = {}
                # find the merge cell indices, use the indices to find stackup and brd path
                start_row_index = 0
                end_row_index = 0
                for sublist in merge_list:
                    if index + header_row in sublist:
                        start_row_index = sublist[0] - header_row
                        end_row_index = sublist[1] - header_row

                for i in range(start_row_index, end_row_index + 1):

                    if brd_path_col[i]:
                        try:
                            brd_path_parts = brd_path_col[i].split(
                                ":", 1
                            )  # split by the first :
                            block_name = brd_path_parts[0].strip()
                            bloack_brd_file_path = brd_path_parts[1].strip()
                            brd_path[block_name] = bloack_brd_file_path
                        except ValueError as e:
                            msgbox(
                                pwt_msgbox,
                                f"Syntax error for the brd path on row {i+header_row+1}: {str(e)}",
                            )
                            raise ValueError
                    else:
                        msgbox(pwt_msgbox, f"Missing a brd file for {unique_key}")
                        raise FileNotFoundError

                    try:
                        stackup_info[block_name] = stackup_info_col[i]
                    except ValueError:
                        # if stackinfo is empty, attach the brd_path key, and value=''
                        stackup_info[block_name] = ""

                    try:
                        # simulation options is optional
                        simulation_options[block_name] = simulation_options_col[
                            i
                        ].strip()
                    except ValueError:
                        simulation_options[block_name] = ""

                if len(brd_path.keys()) < end_row_index + 1 - start_row_index:
                    msgbox(
                        pwt_msgbox, f"Duplicate block names are found for {unique_key}!"
                    )
                    raise ValueError

                try:
                    # PWT is mandatory to in multibrd workflow
                    pwt_path = pwt_path_col[index].strip()
                    if not os.path.exists(pwt_path):
                        msgbox(
                            pwt_msgbox,
                            "Cannot find the defined powertree file. Please check path again!",
                        )
                        raise FileNotFoundError
                except FileNotFoundError:
                    msgbox(pwt_msgbox, "Error getting Powertree info!")
                    raise FileNotFoundError

                try:
                    # output gsheet is also optional
                    out_gsheet_url = out_gsheet_url_col[index].strip()
                except ValueError:
                    out_gsheet_url = ""
                try:
                    out_gsheet_tab = out_gsheet_tab_col[index].strip()
                except ValueError:
                    out_gsheet_tab = ""
                if (out_gsheet_url == "" or out_gsheet_tab == "") != (
                    out_gsheet_url == "" and out_gsheet_tab == ""
                ):
                    msgbox(pwt_msgbox, "Either gsheet url or gsheet tab is empty")
                    raise ValueError

                try:
                    # drive folder url is optional
                    drive_folder_url = drive_folder_url_col[index].strip()
                except ValueError:
                    drive_folder_url = ""

                try:
                    # project folder path is optional
                    project_folder = project_folder_col[index].strip()
                except ValueError:
                    project_folder = ""

                per_key_info = {
                    "unique_key": unique_key,
                    "workflow": workflow,
                    "Brd_path": brd_path,
                    "Stackup_info": stackup_info,
                    "PWT_path": pwt_path,
                    "out_gsheet_url": out_gsheet_url,
                    "out_gsheet_tab": out_gsheet_tab,
                    "drive_folder_url": drive_folder_url,
                    "simulation_options": simulation_options,
                    "project_folder": project_folder,
                }
                sim_list.append(per_key_info)

        else:
            msgbox(
                pwt_msgbox,
                f"Row {index+header_row} is enabled but no unique key value is provided!",
            )
            raise ValueError

    return sim_list


def find_merged_cells(service, spreadsheet_id, tab_name):
    """find which cells are merged in the spreadsheet"""
    sheet_properties = (
        service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    )
    for sheet in sheet_properties["sheets"]:
        if sheet["properties"]["title"] == tab_name:
            # sheetID = sheet["properties"]["sheetId"]
            merge_list = []
            for item in sheet["merges"]:
                if item["startColumnIndex"] == 2:
                    row_indices = [item["startRowIndex"], item["endRowIndex"] - 1]
                    merge_list.append(row_indices)
            break

    return merge_list


def stackup_settings_reader(spreadsheet_url, stackup_tab_name):
    """read stackup info from input gsheet"""
    # creat service

    api_service_name = "sheets"
    api_version = "v4"
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    service = create_service(CLIENT_SECRET_FILE, api_service_name, api_version, scopes)

    cha = list(spreadsheet_url)
    spreadsheet_id = "".join(cha[39:83])
    response2 = (
        service.spreadsheets()
        .values()
        .get(
            spreadsheetId=spreadsheet_id, majorDimension="ROWS", range=stackup_tab_name
        )
        .execute()
    )
    settings2 = response2["values"]
    temp = 2
    while settings2[temp] != [] and settings2[temp] != ["StackUp"]:
        temp += 1
    material = settings2[2:temp]
    row_length = len(settings2[1])  # make sure the length of each row are the same
    for i in range(len(material)):
        if len(material[i]) < row_length:
            for j in range(row_length - len(material[i])):
                material[i].append("")

    while settings2[temp] == []:
        temp += 1

    stackup = settings2[
        temp + 1:
    ]  # attention: there is an extra row under stackup now
    row_length = len(stackup[0])  # make sure the length of each row are the same
    for i in range(len(stackup)):
        if len(stackup[i]) < row_length:
            for j in range(row_length - len(stackup[i])):
                stackup[i].append("")

    return material, stackup


def extract_folder_id(url):
    """get the google drive folder ID"""
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    if "id" in query_params:
        return query_params["id"][0]
    elif "folders" in parsed_url.path:
        path_parts = parsed_url.path.split("/")
        if len(path_parts) > 2:
            return path_parts[-1]
    print("Unable to extract folder ID from the drive folder URL.")
    return None


def pdf_drive_upload(drive_folder_url, pdf_file_path):
    """upload pdf report to google drive"""
    client_secrete_file = "client_secret.json"
    api_service_name = "drive"
    api_version = "v3"
    scopes = ["https://www.googleapis.com/auth/drive"]

    service = create_service(client_secrete_file, api_service_name, api_version, scopes)

    folder_id = extract_folder_id(drive_folder_url)
    file_names = [pdf_file_path]
    mime_type = "application/pdf"

    for file_name in file_names:
        file_metadata = {"name": file_name.split("\\")[-1], "parents": [folder_id]}

        media = MediaFileUpload(file_name, mimetype=mime_type)

        response = (
            service.files()
            .create(
                supportsAllDrives=True,
                body=file_metadata,
                media_body=media,
                fields="id",
            )
            .execute()
        )

        file_id = response["id"]
        file_url = f"https://drive.google.com/file/d/{file_id}/view?usp=drivesdk"
        # print('File ID: {}'.format(file_id))
        print(f"PDN report file URL: {file_url}")
        return file_url


def brd_result_writter(sim_info, pwt_msgbox):
    """
    spreadsheet_url, sink_path, sinkpin_path, tab_name, cell_color, merge_flag, call_time, file_num, occupied_row
    unit is mV
    pass (margin > 5mV): green;
    Marginally pass (5mV > margin > 0): yellow;
    Marginally fail (0 > margin > -5mV): orange;
    Fail (-5mV > margin): red
    """
    # CSV_folder_path=sim_info.CSV_folder_path
    result_folder_path = sim_info["Result_folder_path"]
    spreadsheet_url = sim_info["out_gsheet_url"]
    tab_name = sim_info["out_gsheet_tab"]
    workflow = sim_info["workflow"]
    pdn_report_url = sim_info["PDN_report_url"]
    # try:
    #     PDN_report_url=sim_info['PDN_report_url']
    # except:
    #     PDN_report_url='' #generate a empty link

    # 1. creat service
    client_secret_file = "client_secret.json"
    api_service_name = "sheets"
    api_version = "v4"
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    service = create_service(client_secret_file, api_service_name, api_version, scopes)
    cha = list(spreadsheet_url)
    spreadsheet_id = "".join(cha[39:83])

    # 2. open the Google spreadsheet
    sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = sheet_metadata.get("sheets", "")
    sheet_title = []
    for item in sheets:
        sheet_title.append(item["properties"]["title"])

    # 3. determine simulation mode and upload data
    if workflow.lower() == "Single_IR".lower():

        if not os.path.exists(os.path.join(result_folder_path, "CSVFolder")):
            msgbox(pwt_msgbox, "CSV folder is not found!")
            raise FileNotFoundError
        else:
            sink_path = os.path.join(result_folder_path, "CSVFolder\\Sink.csv")
            sinkpin_path = os.path.join(result_folder_path, "CSVFolder\\SinkPin.csv")
        # use absolute value to determine the background color of the cell
        cell_color = {"absolute": 5}
        # modification date
        t = os.path.getmtime(sink_path)
        ti = str(datetime.datetime.fromtimestamp(t))

        # 2. read simulation data from a csv file
        sink_csv_data = []
        with open(sink_path, "r", encoding="utf-8") as csvfile:
            csv_data = csv.reader(csvfile, delimiter=",")
            for row in csv_data:
                sink_csv_data.append(row)
        sinkpin_data = []
        if os.path.exists(sinkpin_path):
            with open(sinkpin_path, "r", encoding="utf-8") as csvfile:
                csv_data = csv.reader(csvfile, delimiter=",")
                for row in csv_data:
                    sinkpin_data.append(row)

        file_num = 1
        # merge_flag=0
        call_time = 1
        occupied_row = []
        case_num = 1
        # convert tab name and sheet title to lower case to make case insenstive
        # Convert all strings in sheet_title to lowercase
        # sheet_title_lower = [title.lower() for title in sheet_title]
        if tab_name in sheet_title:
            # if file_num == 1: # there is only one file, don't call create but update,
            # means the tab is already there
            #     if merge_flag == 0: #useer set don't merge with the previous result
            #         case_num = 1
            #     else: #user want to merge this with previous result
            #         case_num = 2
            # else: #there are multiple files
            #     if merge_flag == 0: #useer set don't merge with the previous result,
            # but the current multiple files will merge together
            #         if call_time == 0:
            #             case_num = 1 #don't merge with previous results
            #         else:
            #             case_num = 2
            #     else:
            #         case_num = 2
            occupied_index = tab_update_irdrop(
                tab_name,
                service,
                spreadsheet_id,
                sink_csv_data,
                sinkpin_data,
                ti,
                cell_color,
                sink_path,
                case_num,
                occupied_row,
                call_time,
                file_num,
                pdn_report_url,
            )
        else:
            occupied_index = tab_create_irdrop(
                tab_name,
                service,
                spreadsheet_id,
                sink_csv_data,
                sinkpin_data,
                ti,
                cell_color,
                sink_path,
                pdn_report_url,
            )
            sheet_title.append(tab_name)

        # update summary tab
        if "SUMMARY" in sheet_title:
            summary_update(service, spreadsheet_id, sheet_title)
        else:
            summary_create(service, spreadsheet_id, sheet_title)

        return occupied_index

    elif workflow.lower() == "Single_resmeas".lower():
        # read resis.csv data
        if not os.path.exists(os.path.join(result_folder_path, "CSVFolder")):
            msgbox(pwt_msgbox, "CSV folder is not found!")
            raise FileNotFoundError
        else:
            resis_path = os.path.join(result_folder_path, "CSVFolder\\Resis.csv")
        try:
            tab_upload_resmeas(
                tab_name, service, spreadsheet_id, resis_path, pdn_report_url
            )
        except RuntimeError as e:
            # msgbox(PWT_msgbox,f"Error uploading resistance measurment result to gsheet: {str(e)}")
            msgbox(
                pwt_msgbox,
                f"Error uploading resistance measurment result to gsheet: {str(e)}",
            )

    elif workflow.lower() == "Single_limitedIR".lower():
        # use absolute value to determine the background color of the cell
        cell_color = {"absolute": 5}
        try:
            tab_upload_limited_irdrop(
                tab_name,
                service,
                spreadsheet_id,
                result_folder_path,
                cell_color,
                pdn_report_url,
            )
        except RuntimeError as e:
            msgbox(
                pwt_msgbox,
                f"Error uploading current limited IR drop result to gsheet: {str(e)}",
            )

    elif workflow.lower() == "multibrd_ir":
        # use absolute value to determine the background color of the cell
        cell_color = {"absolute": 5}
        for root, dirs, _ in os.walk(result_folder_path):
            for dir_name in dirs:
                if dir_name.endswith("_Result_Files"):
                    print(os.path.join(root, dir_name))
                    sink_path = None
                    block_name = dir_name.split("_Result_Files")[0]
                    sink_path = os.path.join(root, dir_name, "CSVFolder\\Sink.csv")
                    sinkpin_path = os.path.join(
                        root, dir_name, "CSVFolder\\Sinkpin.csv"
                    )
                    tab_name = sim_info["out_gsheet_tab"] + "_" + block_name + "_sinks"

                    if os.path.exists(sink_path):
                        t = os.path.getmtime(sink_path)
                        ti = str(datetime.datetime.fromtimestamp(t))
                        sink_csv_data = []
                        with open(sink_path, 'r', encoding='utf-8') as csvfile:
                            csv_data = csv.reader(csvfile, delimiter=",")
                            for row in csv_data:
                                sink_csv_data.append(row)
                    else:
                        msgbox(pwt_msgbox, f"{sink_path} is not found!")
                        # raise Exception

                    sinkpin_data = []
                    if os.path.exists(sinkpin_path):
                        with open(sinkpin_path, 'r', encoding='utf-8') as csvfile:
                            csv_data = csv.reader(csvfile, delimiter=",")
                            for row in csv_data:
                                sinkpin_data.append(row)

                    file_num = 1
                    # merge_flag=0
                    call_time = 1
                    occupied_row = []
                    case_num = 1
                    if tab_name in sheet_title:
                        if os.path.exists(sink_path):
                            try:
                                occupied_index = tab_update_irdrop(
                                    tab_name,
                                    service,
                                    spreadsheet_id,
                                    sink_csv_data,
                                    sinkpin_data,
                                    ti,
                                    cell_color,
                                    sink_path,
                                    case_num,
                                    occupied_row,
                                    call_time,
                                    file_num,
                                    pdn_report_url,
                                )
                            except RuntimeError:
                                msgbox(
                                    pwt_msgbox,
                                    f"result for {tab_name} is not uploaded!",
                                )
                        else:
                            msgbox(
                                pwt_msgbox, f"result for {tab_name} is not uploaded!"
                            )

                    else:
                        if os.path.exists(sink_path):
                            try:
                                occupied_index = tab_create_irdrop(
                                    tab_name,
                                    service,
                                    spreadsheet_id,
                                    sink_csv_data,
                                    sinkpin_data,
                                    ti,
                                    cell_color,
                                    sink_path,
                                    pdn_report_url,
                                )
                                sheet_title.append(tab_name)
                            except RuntimeError:
                                msgbox(
                                    pwt_msgbox,
                                    f"result for {tab_name} is not uploaded!",
                                )
                        else:
                            msgbox(
                                pwt_msgbox, f"result for {tab_name} is not uploaded!"
                            )

    elif workflow.lower() == "multibrd_limitedir":
        # use absolute value to determine the background color of the cell
        cell_color = {"absolute": 5}
        try:
            tab_upload_multibrd_limited_irdrop(
                tab_name,
                service,
                spreadsheet_id,
                result_folder_path,
                cell_color,
                pdn_report_url,
            )
        except RuntimeError as e:
            msgbox(
                pwt_msgbox,
                f"Error uploading current limited IR drop result to gsheet: {str(e)}",
            )
