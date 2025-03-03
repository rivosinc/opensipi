# SPDX-FileCopyrightText: © 2025 Google LLC
#
# SPDX-License-Identifier: Apache-2.0

"""include all the functions for uploading the results to gsheet"""
import csv
import datetime
import os
import re
import xml.etree.ElementTree as ET


def tab_create_irdrop(
    tab_name,
    service,
    spreadsheet_id,
    sink_csv_data,
    sinkpin_data,
    ti,
    cell_color,
    sink_path,
    pdn_report_url,
):
    """create a tab for uploading IR drop result"""
    # there is no simulation result loaded before, first generate a new sheet
    batch_updat_spreadsheet_body = {"requests": [{"addSheet": {"properties": {"title": tab_name}}}]}
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body=batch_updat_spreadsheet_body
    ).execute()
    response3 = (
        service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    )  # get sheetID for the newly generated tab
    sheet_id = ""
    for item in response3.get("sheets"):
        if item.get("properties").get("title") == tab_name:
            sheet_id = str(item.get("properties").get("sheetId"))
            # sheet_index = item.get("properties").get("index")

    # splite the first colum of csv data
    net = []
    refdes = []
    full_net = []
    for i in range(len(sink_csv_data) - 1):
        temp = sink_csv_data[i + 1][0].split("_")
        refdes.append(temp[1])
        net.append("_".join(temp[2:-1]))
        full_net.append(sink_csv_data[i + 1][0])

    # post-process the sinkpin.csv data -- only equal current
    sinkpin = {}
    if sinkpin_data:
        for i in range(len(sinkpin_data) - 1):
            if sinkpin_data[i + 1][0] != " ":
                row_index_temp = full_net.index(sinkpin_data[i + 1][0])
                if sink_csv_data[row_index_temp + 1][1].replace(" ", "") == "EqualCurrent":
                    index_temp = list(sinkpin_data[i + 1][1].replace(" ", "")).index(".") + 1
                    sink_temp = sinkpin_data[i + 1][0]
                    sinkpin[sink_temp] = sinkpin_data[i + 1][1].replace(" ", "")[index_temp:]
                else:  # UNEQUAL CURRRENT
                    index_temp = list(sinkpin_data[i + 1][1].replace(" ", "")).index(".") + 1
                    sink_temp = sinkpin_data[i + 1][0]
                    if sinkpin_data[i + 1][10] != "":
                        sinkpin[sink_temp] = [
                            [
                                sinkpin_data[i + 1][1].replace(" ", "")[0 : index_temp - 1],
                                sinkpin_data[i + 1][1].replace(" ", "")[index_temp:],
                                sinkpin_data[i + 1][10].replace(" ", ""),
                                sinkpin_data[i + 1][2],
                            ]
                        ]  # voltage drop of the pin; column C, D, E still use sink.csv
                    else:
                        sinkpin[sink_temp] = [
                            [
                                sinkpin_data[i + 1][1].replace(" ", "")[0 : index_temp - 1],
                                sinkpin_data[i + 1][1].replace(" ", "")[index_temp:],
                                "-9999",
                                sinkpin_data[i + 1][2],
                            ]
                        ]
            else:  # sinkpin.csv is empty
                if sink_csv_data[row_index_temp + 1][1].replace(" ", "") == "EqualCurrent":
                    if "GND" not in sinkpin_data[i + 1][7]:  # not GND or AGND
                        index_temp = list(sinkpin_data[i + 1][1].replace(" ", "")).index(".") + 1
                        sinkpin[sink_temp] = (
                            sinkpin[sink_temp]
                            + " "
                            + sinkpin_data[i + 1][1].replace(" ", "")[index_temp:]
                        )
                else:  # UNEQUAL CURRRENT
                    if "GND" not in sinkpin_data[i + 1][7]:  # not GND or AGND
                        index_temp = list(sinkpin_data[i + 1][1].replace(" ", "")).index(".") + 1
                        if sinkpin_data[i + 1][10].replace(" ", "") != "":
                            sinkpin[sink_temp].append(
                                [
                                    sinkpin_data[i + 1][1].replace(" ", "")[0 : index_temp - 1],
                                    sinkpin_data[i + 1][1].replace(" ", "")[index_temp:],
                                    sinkpin_data[i + 1][10].replace(" ", ""),
                                    sinkpin_data[i + 1][2],
                                ]
                            )
                        else:
                            sinkpin[sink_temp].append(
                                [
                                    sinkpin_data[i + 1][1].replace(" ", "")[0 : index_temp - 1],
                                    sinkpin_data[i + 1][1].replace(" ", "")[index_temp:],
                                    "-9999",
                                    sinkpin_data[i + 1][2],
                                ]
                            )
                    else:
                        if "GND" not in sinkpin[sink_temp][-1]:
                            if sinkpin_data[i + 1][10].replace(" ", "") != "":
                                sinkpin[sink_temp].append(
                                    [
                                        sinkpin_data[i + 1][1].replace(" ", "")[0 : index_temp - 1],
                                        sinkpin_data[i + 1][1].replace(" ", "")[index_temp:],
                                        sinkpin_data[i + 1][10].replace(" ", ""),
                                        "GND",
                                    ]
                                )
                            else:
                                sinkpin[sink_temp].append(
                                    [
                                        sinkpin_data[i + 1][1].replace(" ", "")[0 : index_temp - 1],
                                        sinkpin_data[i + 1][1].replace(" ", "")[index_temp:],
                                        "0",
                                        "GND",
                                    ]
                                )
    else:
        for i in range(len(full_net)):
            sink_temp = full_net[i]  # in case sinkpin.csv is missing
            sinkpin[sink_temp] = ""

    # for equal voltage, there is no sinkpin data, so empty
    for i in range(len(full_net)):
        if sink_csv_data[i + 1][1].replace(" ", "") == "EqualVoltage":
            sink_temp = full_net[i]
            sinkpin[sink_temp] = ""

    # prepare header
    header_rows = 6  # number of rows occupied by header
    title_rows = 3
    if list(cell_color.keys())[0] == "absolute":
        header_above = [
            [
                "",
                "Pass (Margin>" + str(cell_color["absolute"]) + "mV)",
                "",
                "Violations",
                "",
                "",
            ],
            [
                "",
                "Marginally pass (" + str(cell_color["absolute"]) + "mV" + ">Margin>0)",
                "",
                "",
                "",
                "",
            ],
            [
                "",
                "Marginally violate (0>Margin>" + str(-1 * cell_color["absolute"]) + "mV)",
                "",
                "",
                "",
                "",
            ],
            [
                "",
                "Violate (" + str(-1 * cell_color["absolute"]) + "mV>Margin)",
                "",
                "",
                "",
                "",
            ],
            ["", "Multiboard ", "", "", "", ""],
        ]  # headers are defined row by row
    else:
        header_above = [
            [
                "",
                "Pass (Margin>" + str(cell_color["percentage"] * 100) + "%)",
                "",
                "Violations",
                "",
                "",
            ],
            [
                "",
                "Marginally pass (" + str(cell_color["percentage"] * 100) + "%" + ">Margin>0)",
                "",
                "",
                "",
                "",
            ],
            [
                "",
                "Marginally violate (0>Margin>" + str(-1 * cell_color["percentage"] * 100) + "%)",
                "",
                "",
                "",
                "",
            ],
            [
                "",
                "Violate (" + str(-1 * cell_color["percentage"] * 100) + "%>Margin)",
                "",
                "",
                "",
                "",
            ],
        ]
    for i in range(header_rows - len(header_above) + 2):
        header_above.append(["", "", "", "", ""])

    # prepare data to write
    header = [["", "", "", "", "", ""], ["", "", "", "", "", ""]]
    data = [[ti, ""], [sink_path, ""]]  # two merged headers date, and csv link
    for i in range(len(sink_csv_data)):
        # data preparation to avoid empty cells
        if not sink_csv_data[i][6].strip():  # empty is true
            sink_csv_data[i][6] = "-9999"
        if not sink_csv_data[i][9].strip():  # empty is true
            sink_csv_data[i][9] = "-9.999"

        if i == 0:
            header.append(
                [
                    "Net",
                    "Sink RefDes",
                    "Sink Pin Name",
                    sink_csv_data[i][2],
                    sink_csv_data[i][3],
                    sink_csv_data[i][5],
                ]
            )
            data.append([sink_csv_data[0][6], "Margin (mV)"])
        else:
            if (
                sink_csv_data[i][1].replace(" ", "") == "EqualCurrent"
                or sink_csv_data[i][1].replace(" ", "") == "EqualVoltage"
            ):
                if sink_csv_data[i][0] == sink_csv_data[i - 1][0]:
                    header.append(
                        [
                            "",
                            "",
                            "",
                            sink_csv_data[i][2],
                            sink_csv_data[i][3],
                            sink_csv_data[i][5],
                        ]
                    )
                else:
                    header.append(
                        [
                            net[i - 1],
                            refdes[i - 1],
                            sinkpin[sink_csv_data[i][0]],
                            sink_csv_data[i][2],
                            sink_csv_data[i][3],
                            sink_csv_data[i][5],
                        ]
                    )
                if sink_csv_data[i][9].strip():  # sink_csv_data[i][9] (margin) not empty
                    data.append(
                        [
                            round(float(sink_csv_data[i][6]), 4),
                            str(round(float(sink_csv_data[i][9]) * 1e3, 1)),
                        ]
                    )
                else:  # empty
                    data.append(
                        [
                            round(float(sink_csv_data[i][6].strip()), 4),
                            str(round(float(sink_csv_data[i][9].strip()), 1)),
                        ]
                    )
            else:
                # if the sink mode is Unequal current
                nominal_vol = float(sink_csv_data[i][3])
                lower_tolerance = float(sink_csv_data[i][5]) / 100
                if sinkpin[sink_csv_data[i][0]] != "":
                    # if we have sinkpin info
                    for j in range(len(sinkpin[sink_csv_data[i][0]]) - 1):
                        if j == 0:
                            header.append(
                                [
                                    net[i - 1],
                                    refdes[i - 1],
                                    sinkpin[sink_csv_data[i][0]][0][1],
                                    sinkpin[sink_csv_data[i][0]][0][3],
                                    sink_csv_data[i][3],
                                    sink_csv_data[i][5],
                                ]
                            )
                        else:
                            header.append(
                                [
                                    "",
                                    "",
                                    sinkpin[sink_csv_data[i][0]][j][1],
                                    sinkpin[sink_csv_data[i][0]][j][3],
                                    sink_csv_data[i][3],
                                    sink_csv_data[i][5],
                                ]
                            )
                        # avoid empty cells in sinkpin.csv for unequal current
                        if (not sinkpin[sink_csv_data[i][0]][j][2].strip()) or (
                            not sinkpin[sink_csv_data[i][0]][-1][2].strip()
                        ):  # empty is true
                            actual_vol = -9999
                            margin = -9.999
                        else:
                            actual_vol = float(sinkpin[sink_csv_data[i][0]][j][2]) - float(
                                sinkpin[sink_csv_data[i][0]][-1][2]
                            )
                            margin = actual_vol - nominal_vol * (1 - lower_tolerance)
                        data.append([round(actual_vol, 4), round(margin * 1e3, 1)])
                elif (
                    sinkpin[sink_csv_data[i][0]].strip() == "" and sink_csv_data[i][9].strip() != ""
                ):
                    if sink_csv_data[i][0] == sink_csv_data[i - 1][0]:
                        header.append(
                            [
                                "",
                                "",
                                "",
                                sink_csv_data[i][2],
                                sink_csv_data[i][3],
                                sink_csv_data[i][5],
                            ]
                        )
                    else:
                        header.append(
                            [
                                net[i - 1],
                                refdes[i - 1],
                                sinkpin[sink_csv_data[i][0]],
                                sink_csv_data[i][2],
                                sink_csv_data[i][3],
                                sink_csv_data[i][5],
                            ]
                        )
                    # sinkpin info is missing, but have lumped result for the unequal current rail
                    data.append(
                        [
                            round(float(sink_csv_data[i][6]), 4),
                            str(round(float(sink_csv_data[i][9]) * 1e3, 1)),
                        ]
                    )

    # will be removed in the future: fill in column A and B to use sort
    for i in range(len(header) - 2):
        if not header[i + 2][0]:  # is empty
            header[i + 2][0] = header[i + 1][0]
            header[i + 2][1] = header[i + 1][1]

    # count the violation number
    formula = "=("
    for i in range(len(data) - 3):
        formula = formula + "COUNTIF($H" + str(header_rows + title_rows + 1 + i) + ',"<0")' + "+"
    formula = formula[:-1]
    formula = formula + ')&"/"&('
    for i in range(len(data) - 3):
        formula = formula + "NOT(ISBLANK($F" + str(header_rows + title_rows + 1 + i) + ")) +"
    formula = formula[:-1]
    formula = formula + ")"

    header_above[0][4] = formula

    worksheet_name = tab_name + "!"
    cell_range_insert = "A1"  # the position of the first cell
    value_range_body = {"majorDimension": "ROWS", "values": header_above}
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        valueInputOption="USER_ENTERED",
        range=worksheet_name + cell_range_insert,
        body=value_range_body,
    ).execute()

    # header_old = header

    worksheet_name = tab_name + "!"
    cell_range_insert = "A" + str(header_rows + 1)  # the position of the first cell
    value_range_body = {"majorDimension": "ROWS", "values": header}
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        valueInputOption="USER_ENTERED",
        range=worksheet_name + cell_range_insert,
        body=value_range_body,
    ).execute()

    header_col = len(header[0])

    worksheet_name = tab_name + "!"
    cell_range_insert = chr(ord("@") + header_col + 1) + str(
        header_rows + 1
    )  # the position of the first cell
    value_range_body = {"majorDimension": "ROWS", "values": data}
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        valueInputOption="USER_ENTERED",
        range=worksheet_name + cell_range_insert,
        body=value_range_body,
    ).execute()

    # change the color according to conditional formatting
    my_range = {
        "sheetId": sheet_id,
        "startRowIndex": header_rows + title_rows,
        "endRowIndex": len(data) + header_rows,
        "startColumnIndex": 7,
        "endColumnIndex": 8,
    }

    # initialize rule content
    red_rule = ""
    orange_rule = ""
    yellow_rule = ""
    green_rule = ""
    blue_rule = ""

    if list(cell_color.keys())[0] == "percentage":  # change color according to percentage
        criteria = cell_color["percentage"]
        red_rule = (
            "=LT( (G"
            + str(header_rows + title_rows + 1)
            + "-E"
            + str(header_rows + title_rows + 1)
            + ")/"
            + "E"
            + str(header_rows + title_rows + 1)
            + ","
            + str(-1 * criteria)
            + ")"
        )
        orange_rule = (
            "=AND(GT( (G"
            + str(header_rows + title_rows + 1)
            + "-E"
            + str(header_rows + title_rows + 1)
            + ")/"
            + "E"
            + str(header_rows + title_rows + 1)
            + ","
            + str(-1 * criteria)
            + "), LTE( (G"
            + str(header_rows + title_rows + 1)
            + "-E"
            + str(header_rows + title_rows + 1)
            + ")/"
            + "E"
            + str(header_rows + title_rows + 1)
            + ","
            + str(0)
            + "))"
        )
        yellow_rule = (
            "=AND(GT( (G"
            + str(header_rows + title_rows + 1)
            + "-E"
            + str(header_rows + title_rows + 1)
            + ")/"
            + "E"
            + str(header_rows + title_rows + 1)
            + ","
            + str(0)
            + "), LTE( (G"
            + str(header_rows + title_rows + 1)
            + "-E"
            + str(header_rows + title_rows + 1)
            + ")/"
            + "E"
            + str(header_rows + title_rows + 1)
            + ","
            + str(criteria)
            + "))"
        )
        green_rule = (
            "=AND(GT( (G"
            + str(header_rows + title_rows + 1)
            + "-E"
            + str(header_rows + title_rows + 1)
            + ")/"
            + "E"
            + str(header_rows + title_rows + 1)
            + ","
            + str(criteria)
            + "), NOT(ISBLANK(G"
            + str(header_rows + title_rows + 1)
            + ")))"
        )
    else:
        criteria = cell_color["absolute"]
        red_rule = "=LT(H" + str(header_rows + title_rows + 1) + "," + str(-1 * criteria) + ")"
        orange_rule = (
            "=AND(GT(H"
            + str(header_rows + title_rows + 1)
            + ","
            + str(-1 * criteria)
            + ")*NOT(ISBLANK(H"
            + str(header_rows + title_rows + 1)
            + ")), LTE(H"
            + str(header_rows + title_rows + 1)
            + ","
            + str(0)
            + "))"
        )
        yellow_rule = (
            "=AND(GT(H"
            + str(header_rows + title_rows + 1)
            + ","
            + str(0)
            + "), LTE(H"
            + str(header_rows + title_rows + 1)
            + ","
            + str(criteria)
            + "))"
        )
        green_rule = (
            "=AND(GT(H"
            + str(header_rows + title_rows + 1)
            + ","
            + str(criteria)
            + "),NOT(ISBLANK(H"
            + str(header_rows + title_rows + 1)
            + ")))"
        )

        blue_rule = "=NOT(F" + str(header_rows + title_rows + 1) + ")"
    requests = [
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [my_range],
                    "booleanRule": {
                        "condition": {
                            "type": "CUSTOM_FORMULA",
                            "values": [{"userEnteredValue": red_rule}],
                        },
                        "format": {
                            "backgroundColor": {
                                "red": 0.918,
                                "green": 0.6,
                                "blue": 0.6,
                            }  # red
                        },
                    },
                },
                "index": 0,
            }
        },
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [my_range],
                    "booleanRule": {
                        "condition": {
                            "type": "CUSTOM_FORMULA",
                            "values": [{"userEnteredValue": orange_rule}],
                        },
                        "format": {
                            "backgroundColor": {
                                "red": 1,
                                "green": 0.74,
                                "blue": 0.02,
                            }  # orange
                        },
                    },
                },
                "index": 0,
            }
        },
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [my_range],
                    "booleanRule": {
                        "condition": {
                            "type": "CUSTOM_FORMULA",
                            "values": [{"userEnteredValue": yellow_rule}],
                        },
                        "format": {
                            "backgroundColor": {
                                "red": 1,
                                "green": 0.898,
                                "blue": 0.6,
                            }  # light yellow
                        },
                    },
                },
                "index": 0,
            }
        },
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [my_range],
                    "booleanRule": {
                        "condition": {
                            "type": "CUSTOM_FORMULA",
                            "values": [{"userEnteredValue": green_rule}],
                        },
                        "format": {
                            "backgroundColor": {
                                "red": 0.714,
                                "green": 0.843,
                                "blue": 0.659,
                            }  # light green
                        },
                    },
                },
                "index": 0,
            }
        },
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [my_range],
                    "booleanRule": {
                        "condition": {
                            "type": "CUSTOM_FORMULA",
                            "values": [{"userEnteredValue": blue_rule}],
                        },
                        "format": {
                            "backgroundColor": {
                                "red": 0.643,
                                "green": 0.760,
                                "blue": 0.956,
                            }  # light blue
                        },
                    },
                },
                "index": 0,
            }
        },
    ]
    body = {"requests": requests}
    service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()

    # 3.4 change the color of some cells if the simulation result is larger than spec
    start_r_blue = []
    end_r_blue = []
    start_c_blue = []
    end_c_blue = []
    start_r_red = []
    end_r_red = []
    start_c_red = []
    end_c_red = []
    start_r_orange = []
    end_r_orange = []
    start_c_orange = []
    end_c_orange = []
    start_r_yellow = []
    end_r_yellow = []
    start_c_yellow = []
    end_c_yellow = []
    start_r_green = []
    end_r_green = []
    start_c_green = []
    end_c_green = []
    start_r_blue.append(4)
    start_c_blue.append(0)
    end_r_blue.append(5)
    end_c_blue.append(1)
    start_r_red.append(3)
    start_c_red.append(0)
    end_r_red.append(4)
    end_c_red.append(1)
    start_r_orange.append(2)
    start_c_orange.append(0)
    end_r_orange.append(3)
    end_c_orange.append(1)
    start_r_yellow.append(1)
    start_c_yellow.append(0)
    end_r_yellow.append(2)
    end_c_yellow.append(1)
    start_r_green.append(0)
    start_c_green.append(0)
    end_r_green.append(1)
    end_c_green.append(1)

    # construct request
    if start_r_red != [] or start_r_orange != [] or start_r_green != []:
        request_body = {}
        request_body["requests"] = []
        for i in range(len(start_r_red)):
            updateCells = {}
            temp = {}
            updateCells["range"] = {
                "sheetId": sheet_id,
                "startRowIndex": start_r_red[i],
                "endRowIndex": end_r_red[i],
                "startColumnIndex": start_c_red[i],
                "endColumnIndex": end_c_red[i],
            }
            updateCells["rows"] = [
                {
                    "values": [
                        {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": 0.918,
                                    "green": 0.6,
                                    "blue": 0.6,
                                }  # light red
                            }
                        }
                    ]
                }
            ]
            updateCells["fields"] = "userEnteredFormat.backgroundColor"
            temp["updateCells"] = updateCells
            request_body["requests"].append(temp)

        for i in range(len(start_r_green)):
            updateCells = {}
            temp = {}
            updateCells["range"] = {
                "sheetId": sheet_id,
                "startRowIndex": start_r_green[i],
                "endRowIndex": end_r_green[i],
                "startColumnIndex": start_c_green[i],
                "endColumnIndex": end_c_green[i],
            }
            updateCells["rows"] = [
                {
                    "values": [
                        {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": 0.714,
                                    "green": 0.843,
                                    "blue": 0.659,
                                }  # light green
                            }
                        }
                    ]
                }
            ]
            updateCells["fields"] = "userEnteredFormat.backgroundColor"
            temp["updateCells"] = updateCells
            request_body["requests"].append(temp)

        for i in range(len(start_r_orange)):
            updateCells = {}
            temp = {}
            updateCells["range"] = {
                "sheetId": sheet_id,
                "startRowIndex": start_r_orange[i],
                "endRowIndex": end_r_orange[i],
                "startColumnIndex": start_c_orange[i],
                "endColumnIndex": end_c_orange[i],
            }
            updateCells["rows"] = [
                {
                    "values": [
                        {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": 1,
                                    "green": 0.74,
                                    "blue": 0.02,
                                }  # orange
                            }
                        }
                    ]
                }
            ]
            updateCells["fields"] = "userEnteredFormat.backgroundColor"
            temp["updateCells"] = updateCells
            request_body["requests"].append(temp)

        for i in range(len(start_r_yellow)):
            updateCells = {}
            temp = {}
            updateCells["range"] = {
                "sheetId": sheet_id,
                "startRowIndex": start_r_yellow[i],
                "endRowIndex": end_r_yellow[i],
                "startColumnIndex": start_c_yellow[i],
                "endColumnIndex": end_c_yellow[i],
            }
            updateCells["rows"] = [
                {
                    "values": [
                        {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": 1,
                                    "green": 0.898,
                                    "blue": 0.6,
                                }  # light yellow
                            }
                        }
                    ]
                }
            ]
            updateCells["fields"] = "userEnteredFormat.backgroundColor"
            temp["updateCells"] = updateCells
            request_body["requests"].append(temp)
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=request_body
        ).execute()

        for i in range(len(start_r_blue)):
            updateCells = {}
            temp = {}
            updateCells["range"] = {
                "sheetId": sheet_id,
                "startRowIndex": start_r_blue[i],
                "endRowIndex": end_r_blue[i],
                "startColumnIndex": start_c_blue[i],
                "endColumnIndex": end_c_blue[i],
            }
            updateCells["rows"] = [
                {
                    "values": [
                        {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": 0.643,
                                    "green": 0.760,
                                    "blue": 0.956,
                                }  # light blue
                            }
                        }
                    ]
                }
            ]
            updateCells["fields"] = "userEnteredFormat.backgroundColor"
            temp["updateCells"] = updateCells
            request_body["requests"].append(temp)
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=request_body
        ).execute()

    # attach PDF report link to the date and time cell
    # if PDN report url is available, add the hyperlink to the simulation date cell
    if pdn_report_url != "":
        hyperlink_formula = f'=HYPERLINK("{pdn_report_url}", "{ti}")'  # ti is the date and time
        # Build the batch update request
        batch_update_body = {
            "requests": [
                {
                    "updateCells": {
                        "range": {
                            "sheetId": sheet_id,  # Replace with the actual sheet ID if known
                            "startRowIndex": header_rows,
                            "endRowIndex": header_rows + 1,
                            "startColumnIndex": header_col,
                            "endColumnIndex": header_col + 1,
                        },
                        "rows": [
                            {"values": [{"userEnteredValue": {"formulaValue": hyperlink_formula}}]}
                        ],
                        "fields": "userEnteredValue",
                    }
                }
            ]
        }

        # Call the Sheets API to update the cell with the hyperlink
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=batch_update_body
        ).execute()

    # add cell borders, set cell width and merge somes cells
    request_body = {
        "requests": [
            {
                "mergeCells": {
                    "mergeType": "MERGE_COLUMNS",
                    "range": {
                        "endColumnIndex": header_col,
                        "endRowIndex": header_rows + title_rows,
                        "sheetId": sheet_id,
                        "startColumnIndex": 0,
                        "startRowIndex": header_rows,
                    },
                },
            },
            {
                "mergeCells": {
                    "mergeType": "MERGE_ROWS",
                    "range": {
                        "endColumnIndex": header_col + 2,
                        "endRowIndex": header_rows + title_rows - 1,
                        "sheetId": sheet_id,
                        "startColumnIndex": header_col,
                        "startRowIndex": header_rows,
                    },
                },
            },
            {
                "updateBorders": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": len(data) + header_rows,
                        "startColumnIndex": 0,
                        "endColumnIndex": 6,
                    },
                    "top": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                    "bottom": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                    "right": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                    "innerHorizontal": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                    "innerVertical": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                }
            },
            {
                "updateBorders": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": header_rows,
                        "endRowIndex": len(data) + header_rows,
                        "startColumnIndex": 0,
                        "endColumnIndex": header_col + 2,
                    },
                    "top": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                    "bottom": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                    "right": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                    "innerHorizontal": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                    "innerVertical": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                }
            },
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": 0,
                        "endIndex": header_col + 1,
                    },
                    "properties": {"pixelSize": 100},
                    "fields": "pixelSize",
                }
            },
            {
                "updateCells": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        # "endRowIndex": len(existing_pwr) + 8,
                        "startColumnIndex": 0,  # ,
                        # "endColumnIndex": existing_cols
                    },
                    "rows": [
                        {"values": [{"userEnteredFormat": {"wrapStrategy": "OVERFLOW_CELL"}}]}
                    ],
                    # "fields": "userEnteredFormat(wrapStrategy)"
                    "fields": "userEnteredFormat.wrapStrategy",
                }
            },
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": sheet_id,
                        "gridProperties": {"frozenColumnCount": header_col},
                    },
                    "fields": "gridProperties.frozenColumnCount",
                }
            },
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": sheet_id,
                        "gridProperties": {"frozenRowCount": header_rows},
                    },
                    "fields": "gridProperties.frozenRowCount",
                }
            },
        ]
    }
    service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=request_body).execute()

    request_body = {
        "requests": [
            {
                "sortRange": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": header_rows + title_rows,
                        "startColumnIndex": 0,
                    },
                    "sortSpecs": [
                        {"dimensionIndex": 1, "sortOrder": "ASCENDING"},
                        {"dimensionIndex": 0, "sortOrder": "ASCENDING"},
                        {"dimensionIndex": 3, "sortOrder": "ASCENDING"},
                    ],
                }
            }
        ]
    }
    service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=request_body).execute()

    # zxc = 1
    temp_index = list(range(0, len(header), 1))

    return temp_index


def tab_update_irdrop(
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
):
    """needs update"""
    # response2 = (
    #     service.spreadsheets()
    #     .values()
    #     .get(spreadsheetId=spreadsheet_id, majorDimension="COLUMNS", range=tab_name)
    #     .execute()
    # )
    # header_rows = 6  # number of rows occupied by header
    # title_rows = 3
    # header_col = 6  # number of columns occupied by header
    # last_col = len(response2["values"]) + 2  # this is for adding border

    # existing_net = response2["values"][0][header_rows + title_rows:]
    # existing_ref = response2["values"][1][header_rows + title_rows:]
    # existing_pin = response2["values"][2][header_rows + title_rows:]
    tab_name = "test"
    service = "test"
    spreadsheet_id = "test"
    sink_csv_data = "test"
    sinkpin_data = "test"
    ti = "test"
    cell_color = "test"
    sink_path = "test"
    case_num = "test"
    occupied_row = "test"
    call_time = "test"
    pdn_report_url = "test"
    file_num = "1"

    return (
        tab_name,
        service,
        spreadsheet_id,
        sink_csv_data,
        file_num,
        sinkpin_data,
        ti,
        cell_color,
        sink_path,
        case_num,
        occupied_row,
        call_time,
        pdn_report_url,
    )

    # if call_time == 0 and case_num == 2:
    #     # if it is the first run and user want to merge, need to read for later occupation check
    #     existing_data = response2["values"][6][header_rows + title_rows:]
    #     occupied_row = []
    #     for i in range(len(existing_data)):
    #         if existing_data[i] != "":
    #             occupied_row.append(i)

    # # some cells of existing_net and existing_ref can be empty
    # # it's because there are multiple sinkpins
    # if len(existing_net) < len(existing_pin):
    #     for i in range(len(existing_pin) - len(existing_net)):
    #         existing_net.append("")
    # if len(existing_ref) < len(existing_pin):
    #     for i in range(len(existing_pin) - len(existing_ref)):
    #         existing_ref.append("")
    # for i in range(len(existing_pin)):
    #     if not existing_net[i]:  # empty
    #         existing_net[i] = existing_net[i - 1]
    # for i in range(len(existing_pin)):
    #     if not existing_ref[i]:
    #         existing_ref[i] = existing_ref[i - 1]
    # # ori_row_num = len(existing_ref) + header_rows + title_rows

    # # Equal voltage existing pin is empty
    # if len(existing_net) > len(existing_pin):
    #     for i in range(len(existing_net) - len(existing_pin)):
    #         existing_pin.append("")

    # response5 = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    # for item in response5.get("sheets"):
    #     if item.get("properties").get("title") == tab_name:
    #         sheet_id = str(item.get("properties").get("sheetId"))
    #         # sheet_index = item.get("properties").get("index")

    # # splite the first column of csv data
    # net = []
    # refdes = []
    # full_net = []
    # for i in range(len(sink_csv_data) - 1):
    #     temp = sink_csv_data[i + 1][0].split("_")
    #     refdes.append(temp[1])
    #     net.append("_".join(temp[2:-1]))
    #     full_net.append(sink_csv_data[i + 1][0])

    # # post-process the sinkpin data
    # sinkpin = {}
    # if sinkpin_data:
    #     for i in range(len(sinkpin_data) - 1):
    #         if sinkpin_data[i + 1][0] != " ":
    #             row_index_temp = full_net.index(sinkpin_data[i + 1][0])
    #             if (
    #                 sink_csv_data[row_index_temp + 1][1].replace(" ", "")
    #                 == "EqualCurrent"
    #             ):
    #                 index_temp = (
    #                     list(sinkpin_data[i + 1][1].replace(" ", "")).index(".") + 1
    #                 )
    #                 sink_temp = sinkpin_data[i + 1][0]
    #                 sinkpin[sink_temp] = sinkpin_data[i + 1][1].replace(" ", "")[
    #                     index_temp:
    #                 ]
    #             else:  # UNEQUAL CURRRENT
    #                 index_temp = (
    #                     list(sinkpin_data[i + 1][1].replace(" ", "")).index(".") + 1
    #                 )
    #                 sink_temp = sinkpin_data[i + 1][0]
    #                 if sinkpin_data[i + 1][10].replace(" ", "") != "":
    #                     sinkpin[sink_temp] = [
    #                         [
    #                             sinkpin_data[i + 1][1].replace(" ", "")[
    #                                 0: index_temp - 1
    #                             ],
    #                             sinkpin_data[i + 1][1].replace(" ", "")[index_temp:],
    #                             sinkpin_data[i + 1][10].replace(" ", ""),
    #                             sinkpin_data[i + 1][2],
    #                         ]
    #                     ]  # voltage drop of the pin; column C, D, E still use sink.csv
    #                 else:
    #                     sinkpin[sink_temp] = [
    #                         [
    #                             sinkpin_data[i + 1][1].replace(" ", "")[
    #                                 0: index_temp - 1
    #                             ],
    #                             sinkpin_data[i + 1][1].replace(" ", "")[index_temp:],
    #                             "-9999",
    #                             sinkpin_data[i + 1][2],
    #                         ]
    #                     ]
    #         else:  # is empty
    #             if (
    #                 sink_csv_data[row_index_temp + 1][1].replace(" ", "")
    #                 == "EqualCurrent"
    #             ):
    #                 if "GND" not in sinkpin_data[i + 1][7]:  # not GND or AGND
    #                     index_temp = (
    #                         list(sinkpin_data[i + 1][1].replace(" ", "")).index(".") + 1
    #                     )
    #                     sinkpin[sink_temp] = (
    #                         sinkpin[sink_temp]
    #                         + " "
    #                         + sinkpin_data[i + 1][1].replace(" ", "")[index_temp:]
    #                     )
    #             else:  # UNEQUAL CURRRENT
    #                 if "GND" not in sinkpin_data[i + 1][7]:  # not GND or AGND
    #                     index_temp = (
    #                         list(sinkpin_data[i + 1][1].replace(" ", "")).index(".") + 1
    #                     )
    #                     if sinkpin_data[i + 1][10].replace(" ", "") != "":
    #                         sinkpin[sink_temp].append(
    #                             [
    #                                 sinkpin_data[i + 1][1].replace(" ", "")[
    #                                     0: index_temp - 1
    #                                 ],
    #                                 sinkpin_data[i + 1][1].replace(" ", "")[
    #                                     index_temp:
    #                                 ],
    #                                 sinkpin_data[i + 1][10].replace(" ", ""),
    #                                 sinkpin_data[i + 1][2],
    #                             ]
    #                         )
    #                     else:
    #                         sinkpin[sink_temp].append(
    #                             [
    #                                 sinkpin_data[i + 1][1].replace(" ", "")[
    #                                     0: index_temp - 1
    #                                 ],
    #                                 sinkpin_data[i + 1][1].replace(" ", "")[
    #                                     index_temp:
    #                                 ],
    #                                 "-9999",
    #                                 sinkpin_data[i + 1][2],
    #                             ]
    #                         )
    #                 else:
    #                     if "GND" not in sinkpin[sink_temp][-1]:
    #                         if sinkpin_data[i + 1][10].replace(" ", "") != "":
    #                             sinkpin[sink_temp].append(
    #                                 [
    #                                     sinkpin_data[i + 1][1].replace(" ", "")[
    #                                         0: index_temp - 1
    #                                     ],
    #                                     sinkpin_data[i + 1][1].replace(" ", "")[
    #                                         index_temp:
    #                                     ],
    #                                     sinkpin_data[i + 1][10].replace(" ", ""),
    #                                     "GND",
    #                                 ]
    #                             )
    #                         else:
    #                             sinkpin[sink_temp].append(
    #                                 [
    #                                     sinkpin_data[i + 1][1].replace(" ", "")[
    #                                         0: index_temp - 1
    #                                     ],
    #                                     sinkpin_data[i + 1][1].replace(" ", "")[
    #                                         index_temp:
    #                                     ],
    #                                     "0",
    #                                     "GND",
    #                                 ]
    #                             )
    # else:
    #     for i in range(
    #         len(full_net)
    #     ):  # if sinkpin.csv is missing, sink pin info is empty
    #         sink_temp = full_net[i]
    #         sinkpin[sink_temp] = ""

    # # for equal voltage, there is no sinkpin data, so empty
    # for i in range(len(full_net)):
    #     if sink_csv_data[i + 1][1].replace(" ", "") == "EqualVoltage":
    #         sink_temp = full_net[i]
    #         sinkpin[sink_temp] = ""

    # # get all the new data from .csv file
    # data = []
    # header = []  # if there are duplicated sinkpins, the net and sink ref will be empty
    # for i in range(len(sink_csv_data) - 1):
    #     # data preparation to avoid empty cells
    #     if not sink_csv_data[i + 1][6].strip():  # empty is true
    #         sink_csv_data[i + 1][6] = "-9999"
    #     if not sink_csv_data[i + 1][9].strip():  # empty is true
    #         sink_csv_data[i + 1][9] = "-9.999"

    #     if (
    #         sink_csv_data[i + 1][1].replace(" ", "") == "EqualCurrent"
    #         or sink_csv_data[i + 1][1].replace(" ", "") == "EqualVoltage"
    #     ):
    #         data.append([sink_csv_data[i + 1][6], sink_csv_data[i + 1][9]])
    #         header.append(
    #             [
    #                 net[i],
    #                 refdes[i],
    #                 sinkpin[sink_csv_data[i + 1][0]],
    #                 sink_csv_data[i + 1][2],
    #                 sink_csv_data[i + 1][3],
    #                 sink_csv_data[i + 1][5],
    #             ]
    #         )
    #     else:
    #         nominal_vol = float(sink_csv_data[i + 1][3])
    #         lower_tolerance = float(sink_csv_data[i + 1][5]) / 100
    #         if sinkpin[sink_csv_data[i][0]] != "":
    #             for j in range(len(sinkpin[sink_csv_data[i + 1][0]]) - 1):
    #                 if j == 0:
    #                     header.append(
    #                         [
    #                             net[i],
    #                             refdes[i],
    #                             sinkpin[sink_csv_data[i + 1][0]][0][1],
    #                             sinkpin[sink_csv_data[i + 1][0]][0][3],
    #                             sink_csv_data[i + 1][3],
    #                             sink_csv_data[i + 1][5],
    #                         ]
    #                     )
    #                 else:
    #                     header.append(
    #                         [
    #                             "",
    #                             "",
    #                             sinkpin[sink_csv_data[i + 1][0]][j][1],
    #                             sinkpin[sink_csv_data[i + 1][0]][j][3],
    #                             sink_csv_data[i + 1][3],
    #                             sink_csv_data[i + 1][5],
    #                         ]
    #                     )
    #                 # avoid empty cells in sinkpin.csv for unequal current
    #                 if (not sinkpin[sink_csv_data[i + 1][0]][j][2].strip()) or (
    #                     not sinkpin[sink_csv_data[i + 1][0]][-1][2].strip()
    #                 ):  # empty is true
    #                     actual_vol = -9999
    #                     margin = -9.999
    #                 else:
    #                     actual_vol = float(
    #                         sinkpin[sink_csv_data[i + 1][0]][j][2]
    #                     ) - float(sinkpin[sink_csv_data[i + 1][0]][-1][2])
    #                     margin = actual_vol - nominal_vol * (1 - lower_tolerance)
    #                 # data.append([round(actual_vol,4), round(margin*1e3,1)])
    #                 data.append([str(actual_vol), str(margin)])
    #         elif (
    #             sinkpin[sink_csv_data[i + 1][0]].strip() == ""
    #             and sink_csv_data[i + 1][9].strip() != ""
    #         ):
    #             if sink_csv_data[i + 1][0] == sink_csv_data[i][0]:
    #                 header.append(
    #                     [
    #                         "",
    #                         "",
    #                         "",
    #                         sink_csv_data[i + 1][2],
    #                         sink_csv_data[i + 1][3],
    #                         sink_csv_data[i + 1][5],
    #                     ]
    #                 )
    #             else:
    #                 header.append(
    #                     [
    #                         net[i],
    #                         refdes[i],
    #                         sinkpin[sink_csv_data[i + 1][0]],
    #                         sink_csv_data[i + 1][2],
    #                         sink_csv_data[i + 1][3],
    #                         sink_csv_data[i + 1][5],
    #                     ]
    #                 )
    #             # sinkpin info is missing, but have lumped result for the unequal current rail
    #             data.append([sink_csv_data[i + 1][6], sink_csv_data[i + 1][9]])
    # # will be removed in the future: fill in column A and B to use sort
    # for i in range(len(header)):
    #     if not header[i][0]:  # is empty
    #         header[i][0] = header[i - 1][0]
    #         header[i][1] = header[i - 1][1]

    # header_full = header
    # for i in range(len(header)):
    #     if not header[i][0]:
    #         header_full[i][0] = header_full[i - 1][0]
    #         header_full[i][1] = header_full[i - 1][1]

    # # check the index of each new data
    # temp_index = []
    # for i in range(len(data)):
    #     if (
    #         header_full[i][0] in existing_net
    #         and header_full[i][1] in existing_ref
    #         and header_full[i][2] in existing_pin
    #     ):
    #         index1 = existing_net.index(header_full[i][0])
    #         index2 = existing_ref.index(header_full[i][1])
    #         index3 = existing_pin.index(header_full[i][2])
    #         if index1 == index2 and index1 == index3:
    #             temp_index.append(index1)
    #         else:  # maybe because still havn't find the matching one or it doesn't exist
    #             flag = 0
    #             while (
    #                 index1 <= len(existing_net)
    #                 and index2 <= len(existing_ref)
    #                 and flag == 0
    #                 and index3 <= len(existing_pin)
    #                 and header_full[i][0] in existing_net[index2:]
    #                 and header_full[i][1] in existing_ref[index1:]
    #                 and header_full[i][2] in existing_pin[index2:]
    #             ):
    #                 index_max = max([index1, index2, index3])
    #                 if index2 == index_max:
    #                     index1 = existing_net[index2:].index(header_full[i][0]) + index2
    #                     index3 = existing_pin[index2:].index(header_full[i][2]) + index2
    #                 elif index1 == index_max:
    #                     index2 = existing_ref[index1:].index(header_full[i][1]) + index1
    #                     index3 = existing_pin[index1:].index(header_full[i][2]) + index1
    #                 else:
    #                     index2 = existing_ref[index3:].index(header_full[i][1]) + index3
    #                     index1 = existing_net[index3:].index(header_full[i][0]) + index3
    #                 if index1 == index2 and index1 == index3:
    #                     temp_index.append(index1)
    #                     flag = 1
    #             if flag == 0:  # doesn't find in the existing one
    #                 temp_index.append(-1)
    #     else:  # the data doesn't exist previously
    #         index1 = -1
    #         temp_index.append(-1)
    #     if temp_index.count(index1) > 1:
    #         zxc = 1

    # # check the current temp_index with the previous occupied_row
    # # if there is any overlap, then must creat a new tab
    # check = any(item in occupied_row for item in temp_index)
    # if check is True:  # some items exist in both occupied_row and temp_index
    #     case_num = 1  # don't merge
    #     print("!" * 80)
    #     print(
    #         "The results of some nets already exist in the current column. "
    #         "Merging is not performed. The results are exported to new columns!"
    #     )
    #     print("!" * 80)

    # if case_num == 1:  # a new column need to be created
    #     request_body = {
    #         "requests": [
    #             {
    #                 "insertDimension": {
    #                     "range": {
    #                         "sheetId": sheet_id,
    #                         "dimension": "COLUMNS",
    #                         "startIndex": 6,
    #                         "endIndex": 8,
    #                     },
    #                     "inheritFromBefore": True,
    #                 }
    #             }
    #         ]
    #     }
    #     service.spreadsheets().batchUpdate(
    #         spreadsheetId=spreadsheet_id, body=request_body
    #     ).execute()
    #     # add_col_flag = 1

    # if -1 in temp_index:
    #     # 3.2.1 need to add new rows to "simulation_result"
    #     # new_net_num = temp_index.count(-1)
    #     new_net = []
    #     new_ref = []
    #     new_pin = []
    #     current = []
    #     voltage = []
    #     tolerance = []
    #     for i in range(len(header)):
    #         if temp_index[i] == -1:
    #             new_net.append(header[i][0])
    #             new_ref.append(header[i][1])
    #             new_pin.append(header[i][2])
    #             current.append(header[i][3])
    #             voltage.append(header[i][4])
    #             tolerance.append(header[i][5])
    #     new_header = [new_net, new_ref, new_pin, current, voltage, tolerance]

    #     # 3.2.2 write the new net name to the spreadsheet
    #     existing_rows = len(existing_net) + 1  # the number of exsiting columns
    #     worksheet_name = tab_name + "!"
    #     cell_range_insert = "A" + str(
    #         existing_rows + 1
    #     )  # the position of the first cell

    #     value_range_body = {"majorDimension": "COLUMNS", "values": new_header}

    #     service.spreadsheets().values().append(
    #         spreadsheetId=spreadsheet_id,
    #         valueInputOption="USER_ENTERED",
    #         range=worksheet_name + cell_range_insert,
    #         body=value_range_body,
    #     ).execute()

    # response3 = (
    #     service.spreadsheets()
    #     .values()
    #     .get(spreadsheetId=spreadsheet_id, majorDimension="COLUMNS", range=tab_name)
    #     .execute()
    # )
    # existing_net = response3["values"][0][header_rows + title_rows:]
    # existing_ref = response3["values"][1][header_rows + title_rows:]
    # existing_pin = response3["values"][2][header_rows + title_rows:]

    # # some cells of existing_net and existing_ref can be empty
    # # it's because there are multiple sinkpins
    # row_num = max(len(existing_pin), len(existing_net), len(existing_ref))
    # if len(existing_net) < row_num:
    #     for i in range(row_num - len(existing_net)):
    #         existing_net.append("")
    # for i in range(row_num):
    #     if not existing_net[i]:  # empty
    #         existing_net[i] = existing_net[i - 1]
    # if len(existing_ref) < row_num:
    #     for i in range(row_num - len(existing_ref)):
    #         existing_ref.append("")
    # for i in range(row_num):
    #     if not existing_ref[i]:
    #         existing_ref[i] = existing_ref[i - 1]
    # if len(existing_pin) < row_num:
    #     for i in range(row_num - len(existing_pin)):
    #         existing_pin.append("")

    # # update the temp_index
    # for i in range(len(data)):
    #     if temp_index[i] == -1:
    #         index1 = existing_net.index(header_full[i][0])
    #         index2 = existing_ref.index(header_full[i][1])
    #         index3 = existing_pin.index(header_full[i][2])
    #         if index1 == index2 and index1 == index3:
    #             temp_index[i] = index1
    #         else:  # maybe because still havn't find the matching one or it doesn't exist
    #             flag = 0
    #             while (
    #                 index1 <= len(existing_net)
    #                 and index2 <= len(existing_ref)
    #                 and flag == 0
    #                 and index3 <= len(existing_pin)
    #             ):
    #                 index_max = max([index1, index2, index3])
    #                 if index2 == index_max:
    #                     index1 = existing_net[index2:].index(header_full[i][0]) + index2
    #                     index3 = existing_pin[index2:].index(header_full[i][2]) + index2
    #                 elif index1 == index_max:
    #                     index2 = existing_ref[index1:].index(header_full[i][1]) + index1
    #                     index3 = existing_pin[index1:].index(header_full[i][2]) + index1
    #                 else:
    #                     index2 = existing_ref[index3:].index(header_full[i][1]) + index3
    #                     index1 = existing_net[index3:].index(header_full[i][0]) + index3
    #                 if index1 == index2 and index1 == index3:
    #                     temp_index[i] = index1
    #                     flag = 1

    # # start to write data into the page
    # if case_num == 1:
    #     avg_vol = [""] * (len(existing_net) + title_rows)
    #     margin = [""] * (len(existing_net) + title_rows)
    #     avg_vol[0] = ti
    #     avg_vol[1] = sink_path
    #     avg_vol[2] = sink_csv_data[0][6]
    #     margin[2] = "Margin (mV)"
    #     for i in range(len(data)):
    #         if data[i][1].strip() != "":
    #             # if margin is not empty
    #             avg_vol[temp_index[i] + title_rows] = round(float(data[i][0]), 4)
    #             margin[temp_index[i] + title_rows] = round(float(data[i][1]) * 1000, 1)
    #         else:
    #             avg_vol[temp_index[i] + title_rows] = ""
    #             margin[temp_index[i] + title_rows] = ""
    #     data_s = [avg_vol, margin]

    #     range1 = tab_name + "!" + "G" + str(header_rows + 1)

    #     value_range_body = {"majorDimension": "COLUMNS", "values": data_s}
    #     service.spreadsheets().values().append(
    #         spreadsheetId=spreadsheet_id,
    #         valueInputOption="USER_ENTERED",
    #         range=range1,
    #         body=value_range_body,
    #     ).execute()
    # elif case_num == 2:
    #     avg_vol = [""] * len(data)
    #     margin = [""] * len(data)
    #     min_index = min(temp_index)
    #     start_row = min(temp_index) + header_rows + title_rows + 1
    #     for i in range(len(data)):
    #         if data[i][0].strip():
    #             avg_vol[temp_index[i] - min_index] = round(float(data[i][0]), 4)
    #             margin[temp_index[i] - min_index] = round(float(data[i][1]) * 1000, 1)
    #         else:
    #             avg_vol[temp_index[i] - min_index] = ""
    #             margin[temp_index[i] - min_index] = ""
    #     data_s = [avg_vol, margin]
    #     range1 = tab_name + "!" + "G" + str(start_row)

    #     value_range_body = {"majorDimension": "COLUMNS", "values": data_s}
    #     service.spreadsheets().values().append(
    #         spreadsheetId=spreadsheet_id,
    #         valueInputOption="USER_ENTERED",
    #         range=range1,
    #         body=value_range_body,
    #     ).execute()

    # # change the color according to conditional formatting
    # my_range = {
    #     "sheetId": sheet_id,
    #     "startRowIndex": header_rows + title_rows,
    #     "endRowIndex": len(existing_net) + header_rows + title_rows,
    #     "startColumnIndex": 7,
    #     "endColumnIndex": 8,
    # }

    # if (
    #     list(cell_color.keys())[0] == "percentage"
    # ):  # change color according to percentage
    #     criteria = cell_color["percentage"]
    #     red_rule = (
    #         "=LT( (G"
    #         + str(header_rows + title_rows + 1)
    #         + "-E"
    #         + str(header_rows + title_rows + 1)
    #         + ")/"
    #         + "E"
    #         + str(header_rows + title_rows + 1)
    #         + ","
    #         + str(-1 * criteria)
    #         + ")"
    #     )
    #     orange_rule = (
    #         "=AND(GT( (G"
    #         + str(header_rows + title_rows + 1)
    #         + "-E"
    #         + str(header_rows + title_rows + 1)
    #         + ")/"
    #         + "E"
    #         + str(header_rows + title_rows + 1)
    #         + ","
    #         + str(-1 * criteria)
    #         + "), LTE( (G"
    #         + str(header_rows + title_rows + 1)
    #         + "-E"
    #         + str(header_rows + title_rows + 1)
    #         + ")/"
    #         + "E"
    #         + str(header_rows + title_rows + 1)
    #         + ","
    #         + str(0)
    #         + "))"
    #     )
    #     yellow_rule = (
    #         "=AND(GT( (G"
    #         + str(header_rows + title_rows + 1)
    #         + "-E"
    #         + str(header_rows + title_rows + 1)
    #         + ")/"
    #         + "E"
    #         + str(header_rows + title_rows + 1)
    #         + ","
    #         + str(0)
    #         + "), LTE( (G"
    #         + str(header_rows + title_rows + 1)
    #         + "-E"
    #         + str(header_rows + title_rows + 1)
    #         + ")/"
    #         + "E"
    #         + str(header_rows + title_rows + 1)
    #         + ","
    #         + str(criteria)
    #         + "))"
    #     )
    #     green_rule = (
    #         "=AND(GT( (G"
    #         + str(header_rows + title_rows + 1)
    #         + "-E"
    #         + str(header_rows + title_rows + 1)
    #         + ")/"
    #         + "E"
    #         + str(header_rows + title_rows + 1)
    #         + ","
    #         + str(criteria)
    #         + "), NOT(ISBLANK(G"
    #         + str(header_rows + title_rows + 1)
    #         + ")))"
    #     )
    # else:
    #     criteria = cell_color["absolute"]
    #     red_rule = (
    #         "=LT(H" + str(header_rows + title_rows + 1) + "," + str(-1 * criteria) + ")"
    #     )
    #     orange_rule = (
    #         "=AND(GT(H"
    #         + str(header_rows + title_rows + 1)
    #         + ","
    #         + str(-1 * criteria)
    #         + ")*NOT(ISBLANK(H"
    #         + str(header_rows + title_rows + 1)
    #         + ")), LTE(H"
    #         + str(header_rows + title_rows + 1)
    #         + ","
    #         + str(0)
    #         + "))"
    #     )
    #     yellow_rule = (
    #         "=AND(GT(H"
    #         + str(header_rows + title_rows + 1)
    #         + ","
    #         + str(0)
    #         + "), LTE(H"
    #         + str(header_rows + title_rows + 1)
    #         + ","
    #         + str(criteria)
    #         + "))"
    #     )
    #     green_rule = (
    #         "=GT(H" + str(header_rows + title_rows + 1) + "," + str(criteria) + ")"
    #     )
    #     blue_rule = "=NOT(F" + str(header_rows + title_rows + 1) + ")"

    # requests = [
    #     {
    #         "addConditionalFormatRule": {
    #             "rule": {
    #                 "ranges": [my_range],
    #                 "booleanRule": {
    #                     "condition": {
    #                         "type": "CUSTOM_FORMULA",
    #                         "values": [{"userEnteredValue": red_rule}],
    #                     },
    #                     "format": {
    #                         "backgroundColor": {
    #                             "red": 0.918,
    #                             "green": 0.6,
    #                             "blue": 0.6,
    #                         }  # red
    #                     },
    #                 },
    #             },
    #             "index": 0,
    #         }
    #     },
    #     {
    #         "addConditionalFormatRule": {
    #             "rule": {
    #                 "ranges": [my_range],
    #                 "booleanRule": {
    #                     "condition": {
    #                         "type": "CUSTOM_FORMULA",
    #                         "values": [{"userEnteredValue": orange_rule}],
    #                     },
    #                     "format": {
    #                         "backgroundColor": {
    #                             "red": 1,
    #                             "green": 0.74,
    #                             "blue": 0.02,
    #                         }  # orange
    #                     },
    #                 },
    #             },
    #             "index": 0,
    #         }
    #     },
    #     {
    #         "addConditionalFormatRule": {
    #             "rule": {
    #                 "ranges": [my_range],
    #                 "booleanRule": {
    #                     "condition": {
    #                         "type": "CUSTOM_FORMULA",
    #                         "values": [{"userEnteredValue": yellow_rule}],
    #                     },
    #                     "format": {
    #                         "backgroundColor": {
    #                             "red": 1,
    #                             "green": 0.898,
    #                             "blue": 0.6,
    #                         }  # light yellow
    #                     },
    #                 },
    #             },
    #             "index": 0,
    #         }
    #     },
    #     {
    #         "addConditionalFormatRule": {
    #             "rule": {
    #                 "ranges": [my_range],
    #                 "booleanRule": {
    #                     "condition": {
    #                         "type": "CUSTOM_FORMULA",
    #                         "values": [{"userEnteredValue": green_rule}],
    #                     },
    #                     "format": {
    #                         "backgroundColor": {
    #                             "red": 0.714,
    #                             "green": 0.843,
    #                             "blue": 0.659,
    #                         }  # light green
    #                     },
    #                 },
    #             },
    #             "index": 0,
    #         }
    #     },
    #     {
    #         "addConditionalFormatRule": {
    #             "rule": {
    #                 "ranges": [my_range],
    #                 "booleanRule": {
    #                     "condition": {
    #                         "type": "CUSTOM_FORMULA",
    #                         "values": [{"userEnteredValue": blue_rule}],
    #                     },
    #                     "format": {
    #                         "backgroundColor": {
    #                             "red": 0.643,
    #                             "green": 0.760,
    #                             "blue": 0.956,
    #                         }  # light blue
    #                     },
    #                 },
    #             },
    #             "index": 0,
    #         }
    #     },
    # ]
    # body = {"requests": requests}
    # service.spreadsheets().batchUpdate(
    #     spreadsheetId=spreadsheet_id, body=body
    # ).execute()

    # # attach PDF report link to the date and time cell
    # # if PDN report url is available, add the hyperlink to the simulation date cell
    # if pdn_report_url != "":
    #     hyperlink_formula = (
    #         f'=HYPERLINK("{pdn_report_url}", "{ti}")'  # ti is the date and time
    #     )
    #     # Build the batch update request
    #     batch_update_body = {
    #         "requests": [
    #             {
    #                 "updateCells": {
    #                     "range": {
    #                         "sheetId": sheet_id,  # Replace with the actual sheet ID if known
    #                         "startRowIndex": header_rows,
    #                         "endRowIndex": header_rows + 1,
    #                         "startColumnIndex": header_col,
    #                         "endColumnIndex": header_col + 1,
    #                     },
    #                     "rows": [
    #                         {
    #                             "values": [
    #                                 {
    #                                     "userEnteredValue": {
    #                                         "formulaValue": hyperlink_formula
    #                                     }
    #                                 }
    #                             ]
    #                         }
    #                     ],
    #                     "fields": "userEnteredValue",
    #                 }
    #             }
    #         ]
    #     }

    #     # Call the Sheets API to update the cell with the hyperlink
    #     service.spreadsheets().batchUpdate(
    #         spreadsheetId=spreadsheet_id, body=batch_update_body
    #     ).execute()

    # # add cell borders, set cell width
    # request_body = {
    #     "requests": [
    #         {
    #             "mergeCells": {
    #                 "mergeType": "MERGE_ROWS",
    #                 "range": {
    #                     "endColumnIndex": 8,
    #                     "endRowIndex": title_rows + header_rows - 1,
    #                     "sheetId": sheet_id,
    #                     "startColumnIndex": 6,
    #                     "startRowIndex": header_rows,
    #                 },
    #             },
    #         },
    #         {
    #             "updateBorders": {
    #                 "range": {
    #                     "sheetId": sheet_id,
    #                     "startRowIndex": header_rows,
    #                     "endRowIndex": len(existing_net) + header_rows + title_rows,
    #                     "startColumnIndex": 0,
    #                     "endColumnIndex": last_col,
    #                 },
    #                 "top": {
    #                     "style": "SOLID",
    #                     "width": 1,
    #                     "color": {"red": 0, "green": 0, "blue": 0},
    #                 },
    #                 "bottom": {
    #                     "style": "SOLID",
    #                     "width": 1,
    #                     "color": {"red": 0, "green": 0, "blue": 0},
    #                 },
    #                 "right": {
    #                     "style": "SOLID",
    #                     "width": 1,
    #                     "color": {"red": 0, "green": 0, "blue": 0},
    #                 },
    #                 "innerHorizontal": {
    #                     "style": "SOLID",
    #                     "width": 1,
    #                     "color": {"red": 0, "green": 0, "blue": 0},
    #                 },
    #                 "innerVertical": {
    #                     "style": "SOLID",
    #                     "width": 1,
    #                     "color": {"red": 0, "green": 0, "blue": 0},
    #                 },
    #             }
    #         },
    #     ]
    # }
    # service.spreadsheets().batchUpdate(
    #     spreadsheetId=spreadsheet_id, body=request_body
    # ).execute()

    # formula = "=("
    # for i in range(len(existing_net)):
    #     formula = (
    #         formula
    #         + "COUNTIF($H"
    #         + str(header_rows + title_rows + 1 + i)
    #         + ',"<0")'
    #         + "+"
    #     )
    # formula = formula[:-1]
    # formula = formula + ')&"/"&('
    # for i in range(len(existing_net)):
    #     formula = (
    #         formula + "NOT(ISBLANK($F" + str(header_rows + title_rows + 1 + i) + ")) +"
    #     )
    # formula = formula[:-1]
    # formula = formula + ")"
    # formula2 = [[formula], [""]]  # if only one cell, the following code will show error

    # worksheet_name = tab_name + "!"
    # cell_range_insert = "E1"  # the position of the first cell
    # value_range_body = {"majorDimension": "ROWS", "values": formula2}
    # service.spreadsheets().values().update(
    #     spreadsheetId=spreadsheet_id,
    #     valueInputOption="USER_ENTERED",
    #     range=worksheet_name + cell_range_insert,
    #     body=value_range_body,
    # ).execute()

    # request_body = {
    #     "requests": [
    #         {
    #             "sortRange": {
    #                 "range": {
    #                     "sheetId": sheet_id,
    #                     "startRowIndex": header_rows + title_rows,
    #                     "startColumnIndex": 0,
    #                 },
    #                 "sortSpecs": [
    #                     {"dimensionIndex": 1, "sortOrder": "ASCENDING"},
    #                     {"dimensionIndex": 0, "sortOrder": "ASCENDING"},
    #                     {"dimensionIndex": 3, "sortOrder": "ASCENDING"},
    #                 ],
    #             }
    #         }
    #     ]
    # }
    # service.spreadsheets().batchUpdate(
    #     spreadsheetId=spreadsheet_id, body=request_body
    # ).execute()

    # # return temp_index

    # # def tab_create_resmeas(tab_name, service,spreadsheet_id,Resis_path,PDN_report_url):
    # # read CSV data ####################################
    # resis_csv_data = []
    # with open(Resis_path, 'r', encoding='utf-8') as csvfile:
    #     csv_data = csv.reader(csvfile, delimiter=",")
    #     for row in csv_data:
    #         resis_csv_data.append(row)
    # t = os.path.getmtime(Resis_path)
    # ti = str(datetime.datetime.fromtimestamp(t))
    # # rail_key=[]
    # # Net = []
    # # RefDes = []
    # # pin_net = []
    # # model=[]
    # # PosPin=[]
    # # NegPin=[]
    # # DCR_moHm=[]
    # Rail_info = []
    # for i in range(len(resis_csv_data) - 1):
    #     row = resis_csv_data[i + 1]
    #     rail_key = row[0].strip()
    #     temp = row[0].split("_")
    #     Sink_refdes = (temp[2]).strip()
    #     model = row[1].strip()
    #     if row[4].strip() == "Positive Pin":
    #         PosPin = "Lumped"
    #     else:
    #         input_string = row[4].strip()
    #         # Define a regular expression pattern to match the desired substring
    #         pattern = r"!!(.*?)::"
    #         # Use re.search to find the first match
    #         match = re.search(pattern, input_string)
    #         if match:
    #             # Extract the matched substring as pos pin node
    #             PosPin = match.group(1)
    #     pin_net = row[5].strip()
    #     if row[6].strip() == "Negative Pin":
    #         NegPin = "Lumped"
    #     else:
    #         input_string = row[6].strip()
    #         # Define a regular expression pattern to match the desired substring
    #         pattern = r"!!(.*?)::"
    #         # Use re.search to find the first match
    #         match = re.search(pattern, input_string)
    #         if match:
    #             # Extract the matched substring as pos pin node
    #             NegPin = match.group(1)
    #     DCR_moHm = float(row[8]) * 1000
    #     rail_info_temp = [
    #         rail_key,
    #         Sink_refdes,
    #         pin_net,
    #         PosPin,
    #         NegPin,
    #         f"{DCR_moHm:.2f}",
    #     ]
    #     Rail_info.append(rail_info_temp)
    # ########################## read CSV data ####################################

    # ######################### add the new tab sheet ####################
    # batchUpdateSpreadsheetBody = {
    #     "requests": [{"addSheet": {"properties": {"title": tab_name}}}]
    # }
    # service.spreadsheets().batchUpdate(
    #     spreadsheetId=spreadsheet_id, body=batchUpdateSpreadsheetBody
    # ).execute()
    # response3 = (
    #     service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    # )  # get sheetID for the newly generated tab
    # for item in response3.get("sheets"):
    #     if item.get("properties").get("title") == tab_name:
    #         sheet_id = str(item.get("properties").get("sheetId"))
    #         sheet_index = item.get("properties").get("index")
    # #######################################################################

    # ###################### add the headers ####################################
    # header_row = 3  # number of rows occupied by header
    # header_col = 5

    # header = [
    #     [
    #         "Unique key for PwrRail",
    #         "Sink",
    #         "Net",
    #         "Positive Pin",
    #         "Negative Pin",
    #         ti,
    #     ],  # first row
    #     ["", "", "", "", "", Resis_path],  # 2nd row
    #     ["", "", "", "", "", "DCR (mOhm)"],
    # ]  # 3rd row
    # worksheet_name = tab_name + "!"
    # cell_range_insert = "A1"  # the position of the first cell
    # value_range_body = {"majorDimension": "ROWS", "values": header}
    # service.spreadsheets().values().update(
    #     spreadsheetId=spreadsheet_id,
    #     valueInputOption="USER_ENTERED",
    #     range=worksheet_name + cell_range_insert,
    #     body=value_range_body,
    # ).execute()
    # ###############################################################

    # # add the data #########################
    # cell_range_insert = "A4"  # the position of the first cell
    # value_range_body = {"majorDimension": "ROWS", "values": Rail_info}
    # service.spreadsheets().values().update(
    #     spreadsheetId=spreadsheet_id,
    #     valueInputOption="USER_ENTERED",
    #     range=worksheet_name + cell_range_insert,
    #     body=value_range_body,
    # ).execute()
    # ###############################################################

    # request_body = {
    #     "requests": [
    #         # {
    #         #     'mergeCells': {
    #         #         'mergeType': 'MERGE_COLUMNS',
    #         #         'range': {
    #         #             'endColumnIndex': header_col,
    #         #             'endRowIndex': header_row,
    #         #             'sheetId': sheet_id,
    #         #             'startColumnIndex': 0,
    #         #             'startRowIndex': header_row
    #         #         }
    #         #     },
    #         # },
    #         {
    #             "mergeCells": {
    #                 "mergeType": "MERGE_COLUMNS",
    #                 "range": {
    #                     "startColumnIndex": 0,
    #                     "endColumnIndex": header_col,
    #                     "startRowIndex": 0,
    #                     "endRowIndex": header_row,
    #                     "sheetId": sheet_id,
    #                 },
    #             },
    #         },
    #         {
    #             "updateBorders": {
    #                 "range": {
    #                     "sheetId": sheet_id,
    #                     "startRowIndex": 0,
    #                     "endRowIndex": len(Rail_info) + header_row,
    #                     "startColumnIndex": 0,
    #                     "endColumnIndex": header_col + 1,
    #                 },
    #                 "top": {
    #                     "style": "SOLID",
    #                     "width": 1,
    #                     "color": {"red": 0, "green": 0, "blue": 0},
    #                 },
    #                 "bottom": {
    #                     "style": "SOLID",
    #                     "width": 1,
    #                     "color": {"red": 0, "green": 0, "blue": 0},
    #                 },
    #                 "right": {
    #                     "style": "SOLID",
    #                     "width": 1,
    #                     "color": {"red": 0, "green": 0, "blue": 0},
    #                 },
    #                 "innerHorizontal": {
    #                     "style": "SOLID",
    #                     "width": 1,
    #                     "color": {"red": 0, "green": 0, "blue": 0},
    #                 },
    #                 "innerVertical": {
    #                     "style": "SOLID",
    #                     "width": 1,
    #                     "color": {"red": 0, "green": 0, "blue": 0},
    #                 },
    #             }
    #         },
    #         {
    #             "updateDimensionProperties": {
    #                 "range": {
    #                     "sheetId": sheet_id,
    #                     "dimension": "COLUMNS",
    #                     "startIndex": 0,
    #                     "endIndex": header_col + 1,
    #                 },
    #                 "properties": {"pixelSize": 100},
    #                 "fields": "pixelSize",
    #             }
    #         },
    #         {
    #             "repeatCell": {  # this is for clipping the text
    #                 "range": {"sheetId": sheet_id},
    #                 "cell": {
    #                     "userEnteredFormat": {
    #                         "wrapStrategy": "CLIP",
    #                         "verticalAlignment": "TOP",
    #                         "horizontalAlignment": "LEFT",
    #                     }
    #                 },
    #                 "fields": "userEnteredFormat.wrapStrategy,userEnteredFormat."
    #                  "verticalAlignment, "
    #                 "userEnteredFormat.horizontalAlignment",
    #             }
    #         },
    #         {
    #             "updateSheetProperties": {
    #                 "properties": {
    #                     "sheetId": sheet_id,
    #                     "gridProperties": {"frozenColumnCount": header_col},
    #                 },
    #                 "fields": "gridProperties.frozenColumnCount",
    #             }
    #         },
    #         {
    #             "updateSheetProperties": {
    #                 "properties": {
    #                     "sheetId": sheet_id,
    #                     "gridProperties": {"frozenRowCount": header_row},
    #                 },
    #                 "fields": "gridProperties.frozenRowCount",
    #             }
    #         },
    #     ]
    # }
    # service.spreadsheets().batchUpdate(
    #     spreadsheetId=spreadsheet_id, body=request_body
    # ).execute()


def tab_upload_resmeas(tab_name, service, spreadsheet_id, resis_path, pdn_report_url):
    """upload resistance measurement result"""

    header_row = 3  # number of rows occupied by header
    header_col = 5
    # 1. read CSV data ####################################
    resis_csv_data = []
    with open(resis_path, encoding="utf-8") as csvfile:
        csv_data = csv.reader(csvfile, delimiter=",")
        for row in csv_data:
            resis_csv_data.append(row)
    t = os.path.getmtime(resis_path)
    ti = str(datetime.datetime.fromtimestamp(t))
    dcr_header = [ti, resis_path, "DCR (mOhm)"]

    rail_info = []
    dcr_info = []  # in mOhm
    pos_pin = ""
    neg_pin = ""
    for i in range(len(resis_csv_data) - 1):
        row = resis_csv_data[i + 1]
        rail_key = row[0].strip()
        temp = row[0].split("_")
        try:
            sink_refdes = (temp[2]).strip()
        except ValueError:
            sink_refdes = ""
        # model = row[1].strip()
        if row[4].strip() == "Positive Pin":
            pos_pin = "Lumped"
        else:
            input_string = row[4].strip()
            # Define a regular expression pattern to match the desired substring
            pattern = r"!!(.*?)::"
            # Use re.search to find the first match
            match = re.search(pattern, input_string)
            if match:
                # Extract the matched substring as pos pin node
                pos_pin = match.group(1)
        pin_net = row[5].strip()
        if row[6].strip() == "Negative Pin":
            neg_pin = "Lumped"
        else:
            input_string = row[6].strip()
            # Define a regular expression pattern to match the desired substring
            pattern = r"!!(.*?)::"
            # Use re.search to find the first match
            match = re.search(pattern, input_string)
            if match:
                # Extract the matched substring as pos pin node
                neg_pin = match.group(1)
        try:
            dcr_mohm = float(row[8]) * 1000
            dcr_info.append(f"{dcr_mohm:.2f}")
        except ValueError:
            dcr_info.append(r"N/A")  # incase there isn't a numeric result
        rail_info_temp = [rail_key, sink_refdes, pin_net, pos_pin, neg_pin]
        rail_info.append(rail_info_temp)

    ##############################################################

    # 2. check if tab is already exists
    # Iterate through the sheets in the spreadsheet and find the sheet with the matching name
    response = (
        service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    )  # get sheetID for the newly generated tab
    sheet_id = None
    for sheet in response.get("sheets", []):
        if sheet["properties"]["title"] == tab_name:
            sheet_id = sheet["properties"]["sheetId"]
            result = (
                service.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range=tab_name)
                .execute()
            )
            values = result.get("values", [])
            last_col = len(values[0]) + 1  # this is for adding border
            break

    if sheet_id is not None:
        read_range = f"{tab_name}!A{header_row+1}:{chr(64+header_col)}"
        # read_range=tab_name
        response2 = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, majorDimension="ROWS", range=read_range)
            .execute()
        )

        existing_rail_info = response2["values"]
        new_rail_info = []
        max_index = len(existing_rail_info)
        write_index = []
        for item in rail_info:
            if item in existing_rail_info:
                index = existing_rail_info.index(item)  # get the rail index from the gsheet info
                write_index.append(index)
            else:
                # if the rail is not found in the existing rails, set the index to the last position
                write_index.append(max_index)
                max_index += 1
                new_rail_info.append(item)

        # add the new rail info #########################
        # first add new rows corresponding to new rails
        if len(new_rail_info) > 0:
            request_body = {
                "requests": [
                    {
                        "appendDimension": {
                            "sheetId": sheet_id,
                            "dimension": "ROWS",
                            "length": len(new_rail_info),
                        }
                    }
                ]
            }
            service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id, body=request_body
            ).execute()
            # add new rail info to the sheet
            # the position of the first cell
            cell_range_insert = f"{tab_name}!A{len(existing_rail_info)+header_row+1}"
            value_range_body = {"majorDimension": "ROWS", "values": new_rail_info}
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                valueInputOption="USER_ENTERED",
                range=cell_range_insert,
                body=value_range_body,
            ).execute()
        # insert a column for new data
        request_body = {
            "requests": [
                {
                    "insertDimension": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": header_col,
                            "endIndex": header_col + 1,
                        },
                        "inheritFromBefore": True,
                    }
                }
            ]
        }

        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=request_body
        ).execute()

        # write data to the new column  ###############################

        dcr_write = [""] * max_index
        for i in range(len(rail_info)):
            dcr_write[write_index[i]] = dcr_info[i]

        dcr_header = [ti, resis_path, "DCR (mOhm)"]
        data_col = [dcr_header + dcr_write]
        range1 = tab_name + "!" + "F1"

        value_range_body = {"majorDimension": "COLUMNS", "values": data_col}
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            valueInputOption="USER_ENTERED",
            range=range1,
            body=value_range_body,
        ).execute()

    else:
        # tab does not exist add the new tab sheet ####################
        batch_update_spreadsheet_body = {
            "requests": [{"addSheet": {"properties": {"title": tab_name}}}]
        }
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=batch_update_spreadsheet_body
        ).execute()
        response3 = (
            service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        )  # get sheetID for the newly generated tab
        for item in response3.get("sheets"):
            if item.get("properties").get("title") == tab_name:
                sheet_id = str(item.get("properties").get("sheetId"))

        # add the headers ####################################
        header = [
            [
                "Unique key for PwrRail",
                "Sink",
                "Net",
                "Positive Pin",
                "Negative Pin",
            ],  # first row
            ["", "", "", "", ""],  # 2nd row
            ["", "", "", "", ""],
        ]  # 3rd row
        worksheet_name = tab_name + "!"
        cell_range_insert = "A1"  # the position of the first cell
        value_range_body = {"majorDimension": "ROWS", "values": header}
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            valueInputOption="USER_ENTERED",
            range=worksheet_name + cell_range_insert,
            body=value_range_body,
        ).execute()
        # add the rail info data #########################
        cell_range_insert = "A4"  # the position of the first cell
        value_range_body = {"majorDimension": "ROWS", "values": rail_info}
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            valueInputOption="USER_ENTERED",
            range=worksheet_name + cell_range_insert,
            body=value_range_body,
        ).execute()
        # add DCR column ############################
        dcr_write = dcr_info
        data_col = [dcr_header + dcr_write]
        range1 = tab_name + "!" + "F1"

        value_range_body = {"majorDimension": "COLUMNS", "values": data_col}
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            valueInputOption="USER_ENTERED",
            range=range1,
            body=value_range_body,
        ).execute()
        last_col = header_col + 1

    # 3.attach PDF report  ################################
    if pdn_report_url != "":
        hyperlink_formula = f'=HYPERLINK("{pdn_report_url}", "{ti}")'  # ti is the date and time
        # Build the batch update request
        batch_update_body = {
            "requests": [
                {
                    "updateCells": {
                        "range": {
                            "sheetId": sheet_id,  # Replace with the actual sheet ID if known
                            "startRowIndex": 0,
                            "endRowIndex": 1,
                            "startColumnIndex": header_col,
                            "endColumnIndex": header_col + 1,
                        },
                        "rows": [
                            {"values": [{"userEnteredValue": {"formulaValue": hyperlink_formula}}]}
                        ],
                        "fields": "userEnteredValue",
                    }
                }
            ]
        }

        # Call the Sheets API to update the cell with the hyperlink
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=batch_update_body
        ).execute()

    # 4. merge rows and add some borders  ################################

    request_body = {
        "requests": [
            # {
            #     'mergeCells': {
            #         'mergeType': 'MERGE_COLUMNS',
            #         'range': {
            #             'endColumnIndex': header_col,
            #             'endRowIndex': header_row,
            #             'sheetId': sheet_id,
            #             'startColumnIndex': 0,
            #             'startRowIndex': header_row
            #         }
            #     },
            # },
            {
                "mergeCells": {
                    "mergeType": "MERGE_COLUMNS",
                    "range": {
                        "startColumnIndex": 0,
                        "endColumnIndex": header_col,
                        "startRowIndex": 0,
                        "endRowIndex": header_row,
                        "sheetId": sheet_id,
                    },
                },
            },
            {
                "updateBorders": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": len(rail_info) + header_row,
                        "startColumnIndex": 0,
                        "endColumnIndex": last_col,
                    },
                    "top": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                    "bottom": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                    "right": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                    "innerHorizontal": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                    "innerVertical": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                }
            },
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": 0,
                        "endIndex": header_col + 1,
                    },
                    "properties": {"pixelSize": 100},
                    "fields": "pixelSize",
                }
            },
            {
                "repeatCell": {  # this is for clipping the text
                    "range": {"sheetId": sheet_id},
                    "cell": {
                        "userEnteredFormat": {
                            "wrapStrategy": "CLIP",
                            "verticalAlignment": "TOP",
                            "horizontalAlignment": "LEFT",
                        }
                    },
                    "fields": "userEnteredFormat.wrapStrategy,userEnteredFormat.verticalAlignment,"
                    "userEnteredFormat.horizontalAlignment",
                }
            },
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": sheet_id,
                        "gridProperties": {"frozenColumnCount": header_col},
                    },
                    "fields": "gridProperties.frozenColumnCount",
                }
            },
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": sheet_id,
                        "gridProperties": {"frozenRowCount": header_row},
                    },
                    "fields": "gridProperties.frozenRowCount",
                }
            },
        ]
    }
    service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=request_body).execute()

    # 5. sort the spreadsheet based on sink name then by net name, then by pos pin , then by neg pin

    request_body = {
        "requests": [
            {
                "sortRange": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": header_row,
                        "startColumnIndex": 0,
                    },
                    "sortSpecs": [
                        {"dimensionIndex": 1, "sortOrder": "ASCENDING"},
                        {"dimensionIndex": 2, "sortOrder": "ASCENDING"},
                        {"dimensionIndex": 3, "sortOrder": "ASCENDING"},
                        {"dimensionIndex": 4, "sortOrder": "ASCENDING"},
                    ],
                }
            }
        ]
    }
    service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=request_body).execute()


def tab_upload_limited_irdrop(
    tab_name, service, spreadsheet_id, result_folder_path, cell_color, pdn_report_url
):
    """upload resut for current limited simulation"""
    # 1. read CSV and xml data ####################################
    # 1.1 read xml data
    sink_path = ""
    if os.path.exists(result_folder_path):
        xml_files = [
            os.path.join(result_folder_path, file)
            for file in os.listdir(result_folder_path)
            if file.endswith(".xml")
        ]
        sink_path = os.path.join(result_folder_path, "OptimizationResult.csv")
        if xml_files:
            result_xml_file = max(xml_files, key=os.path.getctime)
            print(f"The latest XML file is: {os.path.basename(result_xml_file)}")
        else:
            print("No XML files found in the directory.")
            raise FileNotFoundError
    else:
        print("The specified directory does not exist.")

    mytree = ET.parse(result_xml_file)
    myroot = mytree.getroot()
    sink_info = []
    for x in myroot[1]:
        sink_info.append(x.attrib)

    # 1.2.read simulation data from a optmization file

    sink_csv_data_ = []
    with open(sink_path, encoding="utf-8") as csvfile:
        csv_data = csv.reader(csvfile, delimiter=",")
        for row in csv_data:
            sink_csv_data_.append(row)
    sink_csv_data = sink_csv_data_[2:]  # remove the first two rows of header

    gsheet_data = []
    keys = []
    net = {}
    refdes = {}
    max_curr = {}
    worst_ir_drop = {}
    # extract data from optimization csv file
    for i in range(len(sink_csv_data)):
        key = sink_csv_data[i][0].strip()
        keys.append(key)
        temp = sink_csv_data[i][0].split("_")
        refdes[key] = temp[1]
        net[key] = "_".join(temp[2:-1])
        max_curr[key] = (
            str(float(sink_csv_data[i][i + 1])).rstrip("0").rstrip(".")
        )  # Remove trailing zeros and the trailing dot if it exists
        worst_ir_drop[key] = f"{float(sink_csv_data[i][-1]):.2f}"

    # Extracting data from xml:
    nominal_volt = {}
    lower_tolerance = {}
    allowed_volt_drop_mv = {}
    for line in sink_info:
        key = line["Name"].strip()
        nominal_volt[key] = (
            str(float(line["NominalVoltage"])).rstrip("0").rstrip(".")
        )  # Remove trailing zeros and the trailing dot if it exists
        lower_tolerance[key] = (
            str(float(line["LowerTolerance_Percentage"])).rstrip("0").rstrip(".")
        )  # Remove trailing zeros and the trailing dot if it exists
        allowed_volt_drop_mv[key] = (
            f"{float(line['LowerTolerance_Percentage'])*float(line['NominalVoltage'])*10:.2f}"
        )

    # add all the data to the gsheet_data without headers
    for key in keys:
        data_line = [
            net[key],
            refdes[key],
            max_curr[key],
            nominal_volt[key],
            lower_tolerance[key],
            allowed_volt_drop_mv[key],
            worst_ir_drop[key],
        ]
        gsheet_data.append(data_line)

    # 1.3 get the time stamp of the optimization csv file
    t = os.path.getmtime(sink_path)
    ti = str(datetime.datetime.fromtimestamp(t))

    # 2. check if upload gsheet tab is already exists
    # Iterate through the sheets in the spreadsheet and find the sheet with the matching name
    response = (
        service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    )  # get sheetID for the newly generated tab

    header_rows = 5  # number of rows occupied by header
    title_rows = 3
    header_cols = 6  # number of columns occupied by header

    sheet_id = None
    for sheet in response.get("sheets", []):
        if sheet["properties"]["title"] == tab_name:
            sheet_id = sheet["properties"]["sheetId"]
            result = (
                service.spreadsheets()
                .values()
                .get(
                    spreadsheetId=spreadsheet_id,
                    majorDimension="COLUMNS",
                    range=tab_name,
                )
                .execute()
            )
            values = result.get("values", [])
            last_col = len(values) + 1  # get the last column for adding border
            break

    if sheet_id is not None:
        # the tab already exsits, update the result ########################
        read_range = f"{tab_name}!A{header_rows+title_rows+1}:E"
        # read_range=tab_name
        response2 = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, majorDimension="ROWS", range=read_range)
            .execute()
        )

        existing_rail_info = response2["values"]
        new_rail_info = []
        max_index = len(existing_rail_info)
        write_index = []
        for item in gsheet_data:
            if item[0:5] in existing_rail_info:
                index = existing_rail_info.index(
                    item[0:5]
                )  # only match Net, Refdes, sink current and voltage
                write_index.append(index)
            else:
                # if the rail is not found in the existing rails, set the index to the last position
                write_index.append(max_index)
                max_index += 1
                new_rail_info.append(item[:-1])

        # add the new rail info #########################
        # first add new rows corresponding to new rails
        if len(new_rail_info) > 0:
            request_body = {
                "requests": [
                    {
                        "appendDimension": {
                            "sheetId": sheet_id,
                            "dimension": "ROWS",
                            "length": len(new_rail_info),
                        }
                    }
                ]
            }
            service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id, body=request_body
            ).execute()
            # add new rail info to the sheet
            # the position of the first cell
            cell_range_insert = f"{tab_name}!A{len(existing_rail_info)+header_rows+title_rows+1}"
            value_range_body = {"majorDimension": "ROWS", "values": new_rail_info}
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                valueInputOption="USER_ENTERED",
                range=cell_range_insert,
                body=value_range_body,
            ).execute()

        # insert a column for new data
        request_body = {
            "requests": [
                {
                    "insertDimension": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": header_cols,
                            "endIndex": header_cols + 1,
                        },
                        "inheritFromBefore": True,
                    }
                }
            ]
        }

        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=request_body
        ).execute()

        #  write data to the new column  ###############################

        ir_drop_write = [""] * max_index
        for i in range(len(gsheet_data)):
            ir_drop_write[write_index[i]] = gsheet_data[i][-1]

        header = [ti, sink_path, "Worst IR-drop(mV)"]
        data_col = [header + ir_drop_write]

        range1 = (
            tab_name + "!" + chr(64 + header_cols + 1) + str(header_rows + 1)
        )  # STARTING Positing is G6

        value_range_body = {"majorDimension": "COLUMNS", "values": data_col}
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            valueInputOption="USER_ENTERED",
            range=range1,
            body=value_range_body,
        ).execute()

    else:
        # tab does not exist add the new tab sheet ####################
        last_col = header_cols + 1
        batch_update_spreadsheet_body = {
            "requests": [{"addSheet": {"properties": {"title": tab_name}}}]
        }
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=batch_update_spreadsheet_body
        ).execute()
        response3 = (
            service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        )  # get sheetID for the newly generated tab
        for item in response3.get("sheets"):
            if item.get("properties").get("title") == tab_name:
                sheet_id = str(item.get("properties").get("sheetId"))

        # add the headers ####################################
        if list(cell_color.keys())[0] == "absolute":
            header_above = [
                [
                    "",
                    "Pass (Margin>" + str(cell_color["absolute"]) + "mV)",
                    "",
                    "Violations",
                    "",
                    "",
                ],
                [
                    "",
                    "Marginally pass (" + str(cell_color["absolute"]) + "mV" + ">Margin>0)",
                    "",
                    "",
                    "",
                    "",
                ],
                [
                    "",
                    "Marginally violate (0>Margin>" + str(-1 * cell_color["absolute"]) + "mV)",
                    "",
                    "",
                    "",
                    "",
                ],
                [
                    "",
                    "Violate (" + str(-1 * cell_color["absolute"]) + "mV>Margin)",
                    "",
                    "",
                    "",
                    "",
                ],
            ]
        else:
            header_above = [
                [
                    "",
                    "Pass (Margin>" + str(cell_color["percentage"] * 100) + "%)",
                    "",
                    "Violations",
                    "",
                    "",
                ],
                [
                    "",
                    "Marginally pass (" + str(cell_color["percentage"] * 100) + "%" + ">Margin>0)",
                    "",
                    "",
                    "",
                    "",
                ],
                [
                    "",
                    "Marginally violate (0>Margin>"
                    + str(-1 * cell_color["percentage"] * 200)
                    + "%)",
                    "",
                    "",
                    "",
                    "",
                ],
                [
                    "",
                    "Violate (" + str(-1 * cell_color["percentage"] * 200) + "%>Margin)",
                    "",
                    "",
                    "",
                    "",
                ],
            ]
        for i in range(header_rows - len(header_above) + 2):
            header_above.append(["", "", "", "", ""])

        worksheet_name = tab_name + "!"
        cell_range_insert = "A1"  # the position of the first cell
        value_range_body = {"majorDimension": "ROWS", "values": header_above}
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            valueInputOption="USER_ENTERED",
            range=worksheet_name + cell_range_insert,
            body=value_range_body,
        ).execute()

        # add the rail info data #########################
        # insert header data
        header = []

        header.append(
            [
                "Net",
                "RefDes",
                "Max Sink Current(A)",
                "Output Voltage",
                "Allowed Voltage Drop(%) ",
                "Allowed Voltage Drop(mV)",
                ti,
            ]
        )  # headers
        header.append(["", "", "", "", "", "", sink_path])
        header.append(["", "", "", "", "", "", "Worst IR-drop(mV)"])

        cell_range_insert = "A" + str(header_rows + 1)  # the position of the first header cell
        value_range_body = {"majorDimension": "ROWS", "values": header}
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            valueInputOption="USER_ENTERED",
            range=worksheet_name + cell_range_insert,
            body=value_range_body,
        ).execute()
        # print('All data uploaded')

        cell_range_insert = "A" + str(
            header_rows + title_rows + 1
        )  # the position of the first data cell
        value_range_body = {"majorDimension": "ROWS", "values": gsheet_data}
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            valueInputOption="USER_ENTERED",
            range=worksheet_name + cell_range_insert,
            body=value_range_body,
        ).execute()
        print("All data uploaded")

    # 3.attach PDF report  ################################
    if pdn_report_url != "":
        hyperlink_formula = f'=HYPERLINK("{pdn_report_url}", "{ti}")'  # ti is the date and time
        # Build the batch update request
        batch_update_body = {
            "requests": [
                {
                    "updateCells": {
                        "range": {
                            "sheetId": sheet_id,  # Replace with the actual sheet ID if known
                            "startRowIndex": header_rows,
                            "endRowIndex": header_rows + 1,
                            "startColumnIndex": header_cols,
                            "endColumnIndex": header_cols + 1,
                        },
                        "rows": [
                            {"values": [{"userEnteredValue": {"formulaValue": hyperlink_formula}}]}
                        ],
                        "fields": "userEnteredValue",
                    }
                }
            ]
        }

        # Call the Sheets API to update the cell with the hyperlink
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=batch_update_body
        ).execute()

    # 4. change the color according to conditional formatting #####################
    my_range = {
        "sheetId": sheet_id,
        "startRowIndex": header_rows + title_rows,
        "endRowIndex": len(gsheet_data) + header_rows + title_rows,
        "startColumnIndex": header_cols,
        "endColumnIndex": header_cols + 1,
    }

    if list(cell_color.keys())[0] == "percentage":
        # change color according to percentage
        criteria = cell_color["percentage"]
        red_rule = (
            "=LT( (G"
            + str(header_rows + title_rows + 1)
            + "-D"
            + str(header_rows + title_rows + 1)
            + ")/"
            + "D"
            + str(header_rows + title_rows + 1)
            + ","
            + str(-1 * criteria)
            + ")"
        )
        orange_rule = (
            "=AND(GT( (G"
            + str(header_rows + title_rows + 1)
            + "-D"
            + str(header_rows + title_rows + 1)
            + ")/"
            + "D"
            + str(header_rows + title_rows + 1)
            + ","
            + str(-1 * criteria)
            + "), LTE( (G"
            + str(header_rows + title_rows + 1)
            + "-D"
            + str(header_rows + title_rows + 1)
            + ")/"
            + "D"
            + str(header_rows + title_rows + 1)
            + ","
            + str(0)
            + "))"
        )
        yellow_rule = (
            "=AND(GT( (G"
            + str(header_rows + title_rows + 1)
            + "-D"
            + str(header_rows + title_rows + 1)
            + ")/"
            + "D"
            + str(header_rows + title_rows + 1)
            + ","
            + str(0)
            + "), LTE( (G"
            + str(header_rows + title_rows + 1)
            + "-D"
            + str(header_rows + title_rows + 1)
            + ")/"
            + "D"
            + str(header_rows + title_rows + 1)
            + ","
            + str(criteria)
            + "))"
        )
        green_rule = (
            "=AND(GT( (G"
            + str(header_rows + title_rows + 1)
            + "-D"
            + str(header_rows + title_rows + 1)
            + ")/"
            + "D"
            + str(header_rows + title_rows + 1)
            + ","
            + str(criteria)
            + "), NOT(ISBLANK(G"
            + str(header_rows + title_rows + 1)
            + ")))"
        )
    else:

        criteria = cell_color["absolute"]
        red_rule = (
            "=LT((F"
            + str(header_rows + title_rows + 1)
            + "-G"
            + str(header_rows + title_rows + 1)
            + ")"
            + ","
            + str(-1 * criteria)
            + ")"
        )
        orange_rule = (
            "=AND(GT((F"
            + str(header_rows + title_rows + 1)
            + "-G"
            + str(header_rows + title_rows + 1)
            + ")"
            + ","
            + str(-1 * criteria)
            + ")*NOT(ISBLANK(F"
            + str(header_rows + title_rows + 1)
            + ")), LTE((F"
            + str(header_rows + title_rows + 1)
            + "-G"
            + str(header_rows + title_rows + 1)
            + ")"
            + ","
            + str(0)
            + "))"
        )
        yellow_rule = (
            "=AND(GT((F"
            + str(header_rows + title_rows + 1)
            + "-G"
            + str(header_rows + title_rows + 1)
            + ")"
            + ","
            + str(0)
            + ")*NOT(ISBLANK(G"
            + str(header_rows + title_rows + 1)
            + ")), LTE((F"
            + str(header_rows + title_rows + 1)
            + "-G"
            + str(header_rows + title_rows + 1)
            + ")"
            + ","
            + str(criteria)
            + "))"
        )
        green_rule = (
            "=GT((F"
            + str(header_rows + title_rows + 1)
            + "-G"
            + str(header_rows + title_rows + 1)
            + ")"
            + ","
            + str(criteria)
            + ")*NOT(ISBLANK(G"
            + str(header_rows + title_rows + 1)
            + "))"
        )

    requests = [
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [my_range],
                    "booleanRule": {
                        "condition": {
                            "type": "CUSTOM_FORMULA",
                            "values": [{"userEnteredValue": red_rule}],
                        },
                        "format": {
                            "backgroundColor": {
                                "red": 0.918,
                                "green": 0.6,
                                "blue": 0.6,
                            }  # red
                        },
                    },
                },
                "index": 0,
            }
        },
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [my_range],
                    "booleanRule": {
                        "condition": {
                            "type": "CUSTOM_FORMULA",
                            "values": [{"userEnteredValue": orange_rule}],
                        },
                        "format": {
                            "backgroundColor": {
                                "red": 1,
                                "green": 0.74,
                                "blue": 0.02,
                            }  # orange
                        },
                    },
                },
                "index": 0,
            }
        },
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [my_range],
                    "booleanRule": {
                        "condition": {
                            "type": "CUSTOM_FORMULA",
                            "values": [{"userEnteredValue": yellow_rule}],
                        },
                        "format": {
                            "backgroundColor": {
                                "red": 1,
                                "green": 0.898,
                                "blue": 0.6,
                            }  # light yellow
                        },
                    },
                },
                "index": 0,
            }
        },
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [my_range],
                    "booleanRule": {
                        "condition": {
                            "type": "CUSTOM_FORMULA",
                            "values": [{"userEnteredValue": green_rule}],
                        },
                        "format": {
                            "backgroundColor": {
                                "red": 0.714,
                                "green": 0.843,
                                "blue": 0.659,
                            }  # light green
                        },
                    },
                },
                "index": 0,
            }
        },
    ]
    body = {"requests": requests}
    service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()

    # 3.4 change the color of some cells if the simulation result is larger than spec
    start_r_red = []
    end_r_red = []
    start_c_red = []
    end_c_red = []
    start_r_orange = []
    end_r_orange = []
    start_c_orange = []
    end_c_orange = []
    start_r_yellow = []
    end_r_yellow = []
    start_c_yellow = []
    end_c_yellow = []
    start_r_green = []
    end_r_green = []
    start_c_green = []
    end_c_green = []
    start_r_red.append(3)
    start_c_red.append(0)
    end_r_red.append(4)
    end_c_red.append(1)
    start_r_orange.append(2)
    start_c_orange.append(0)
    end_r_orange.append(3)
    end_c_orange.append(1)
    start_r_yellow.append(1)
    start_c_yellow.append(0)
    end_r_yellow.append(2)
    end_c_yellow.append(1)
    start_r_green.append(0)
    start_c_green.append(0)
    end_r_green.append(1)
    end_c_green.append(1)

    # construct request
    if start_r_red != [] or start_r_orange != [] or start_r_green != []:
        request_body = {}
        request_body["requests"] = []
        for i in range(len(start_r_red)):
            updateCells = {}
            temp = {}
            updateCells["range"] = {
                "sheetId": sheet_id,
                "startRowIndex": start_r_red[i],
                "endRowIndex": end_r_red[i],
                "startColumnIndex": start_c_red[i],
                "endColumnIndex": end_c_red[i],
            }
            updateCells["rows"] = [
                {
                    "values": [
                        {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": 0.918,
                                    "green": 0.6,
                                    "blue": 0.6,
                                }  # light red
                            }
                        }
                    ]
                }
            ]
            updateCells["fields"] = "userEnteredFormat.backgroundColor"
            temp["updateCells"] = updateCells
            request_body["requests"].append(temp)

        for i in range(len(start_r_green)):
            updateCells = {}
            temp = {}
            updateCells["range"] = {
                "sheetId": sheet_id,
                "startRowIndex": start_r_green[i],
                "endRowIndex": end_r_green[i],
                "startColumnIndex": start_c_green[i],
                "endColumnIndex": end_c_green[i],
            }
            updateCells["rows"] = [
                {
                    "values": [
                        {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": 0.714,
                                    "green": 0.843,
                                    "blue": 0.659,
                                }  # light green
                            }
                        }
                    ]
                }
            ]
            updateCells["fields"] = "userEnteredFormat.backgroundColor"
            temp["updateCells"] = updateCells
            request_body["requests"].append(temp)

        for i in range(len(start_r_orange)):
            updateCells = {}
            temp = {}
            updateCells["range"] = {
                "sheetId": sheet_id,
                "startRowIndex": start_r_orange[i],
                "endRowIndex": end_r_orange[i],
                "startColumnIndex": start_c_orange[i],
                "endColumnIndex": end_c_orange[i],
            }
            updateCells["rows"] = [
                {
                    "values": [
                        {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": 1,
                                    "green": 0.74,
                                    "blue": 0.02,
                                }  # orange
                            }
                        }
                    ]
                }
            ]
            updateCells["fields"] = "userEnteredFormat.backgroundColor"
            temp["updateCells"] = updateCells
            request_body["requests"].append(temp)

        for i in range(len(start_r_yellow)):
            updateCells = {}
            temp = {}
            updateCells["range"] = {
                "sheetId": sheet_id,
                "startRowIndex": start_r_yellow[i],
                "endRowIndex": end_r_yellow[i],
                "startColumnIndex": start_c_yellow[i],
                "endColumnIndex": end_c_yellow[i],
            }
            updateCells["rows"] = [
                {
                    "values": [
                        {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": 1,
                                    "green": 0.898,
                                    "blue": 0.6,
                                }  # light yellow
                            }
                        }
                    ]
                }
            ]
            updateCells["fields"] = "userEnteredFormat.backgroundColor"
            temp["updateCells"] = updateCells
            request_body["requests"].append(temp)
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=request_body
        ).execute()

    # add cell borders, set cell width
    request_body = {
        "requests": [
            {
                "mergeCells": {
                    "mergeType": "MERGE_COLUMNS",
                    "range": {
                        "endColumnIndex": header_cols,
                        "endRowIndex": header_rows + title_rows,
                        "sheetId": sheet_id,
                        "startColumnIndex": 0,
                        "startRowIndex": header_rows,
                    },
                },
            },
            {
                "mergeCells": {
                    "mergeType": "MERGE_ROWS",
                    "range": {
                        "endColumnIndex": header_cols + 1,
                        "endRowIndex": header_rows + title_rows - 1,
                        "sheetId": sheet_id,
                        "startColumnIndex": header_cols,
                        "startRowIndex": header_rows,
                    },
                },
            },
            {
                "updateBorders": {  # update border for sink info from column A-F
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": len(gsheet_data) + header_rows + title_rows,
                        "startColumnIndex": 0,
                        "endColumnIndex": header_cols,
                    },
                    "top": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                    "bottom": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                    "right": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                    "innerHorizontal": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                    "innerVertical": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                }
            },
            {
                "updateBorders": {  # update boarder for all datas
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": header_rows,
                        "endRowIndex": len(gsheet_data) + header_rows + title_rows,
                        "startColumnIndex": header_cols,
                        "endColumnIndex": last_col,
                    },
                    "top": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                    "bottom": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                    "right": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                    "innerHorizontal": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                    "innerVertical": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                }
            },
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": 0,
                        "endIndex": header_cols + 1,
                    },
                    "properties": {"pixelSize": 100},
                    "fields": "pixelSize",
                }
            },
            {
                "updateCells": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        # "endRowIndex": len(existing_pwr) + 8,
                        "startColumnIndex": 0,  # ,
                        # "endColumnIndex": existing_cols
                    },
                    "rows": [
                        {"values": [{"userEnteredFormat": {"wrapStrategy": "OVERFLOW_CELL"}}]}
                    ],
                    # "fields": "userEnteredFormat(wrapStrategy)"
                    "fields": "userEnteredFormat.wrapStrategy",
                }
            },
            {
                "repeatCell": {  # this is for clipping the text
                    "range": {"sheetId": sheet_id},
                    "cell": {
                        "userEnteredFormat": {
                            "wrapStrategy": "CLIP",
                            "verticalAlignment": "TOP",
                            "horizontalAlignment": "LEFT",
                            # "numberFormat": {
                            #     "type": "TEXT",
                            #     "pattern": "#,##0.00"  # Specify the desired number format
                            # }
                        }
                    },
                    "fields": "userEnteredFormat.wrapStrategy,userEnteredFormat.verticalAlignment,"
                    "userEnteredFormat.horizontalAlignment",
                }
            },
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": sheet_id,
                        "gridProperties": {"frozenColumnCount": header_cols},
                    },
                    "fields": "gridProperties.frozenColumnCount",
                }
            },
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": sheet_id,
                        "gridProperties": {"frozenRowCount": header_rows},
                    },
                    "fields": "gridProperties.frozenRowCount",
                }
            },
        ]
    }
    service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=request_body).execute()


def tab_upload_multibrd_limited_irdrop(
    tab_name, service, spreadsheet_id, result_folder_path, cell_color, pdn_report_url
):
    """upload multibrd current limited simulation result"""
    # 1. read CSV and xml data ####################################
    # read the optimization csv file
    sink_csv_data = ""
    if os.path.exists(result_folder_path):
        sink_path = os.path.join(result_folder_path, "OptimizationResult.csv")
        sink_csv_data_ = []
        if os.path.exists(sink_path):
            with open(sink_path, encoding="utf-8") as csvfile:
                csv_data = csv.reader(csvfile, delimiter=",")
                for row in csv_data:
                    sink_csv_data_.append(row)
            sink_csv_data = sink_csv_data_[2:]  # remove the first two rows of header
        else:
            print("Optimization.CSV does not exist!")

        block_name_list = []
        sink_info = []
        for root, dirs, _ in os.walk(result_folder_path):
            for dir_name in dirs:
                if dir_name.endswith("_Result_Files"):
                    print(os.path.join(root, dir_name))
                    # sink_path=None
                    block_name = dir_name.split("_Result_Files")[0]
                    block_name_list.append(block_name)
                    xml_file_path = os.path.join(
                        result_folder_path,
                        dir_name,
                        block_name + "_SimulationResult.xml",
                    )
                    if os.path.exists(xml_file_path):
                        mytree = ET.parse(xml_file_path)
                        myroot = mytree.getroot()
                        for x in myroot[1]:
                            x.attrib["Name"] = block_name + "." + x.attrib["Name"]
                            sink_info.append(x.attrib)
                    else:
                        print(f"No XML files found in the directory {dir_name}.")
                        # raise Exception
    else:
        print("The specified directory does not exist.")

    # 1.2.read simulation data from a optmization file

    gsheet_data = []
    keys = []
    net = {}
    refdes = {}
    max_curr = {}
    worst_ir_drop = {}
    # extract data from optimization csv file
    for i in range(len(sink_csv_data)):
        key = sink_csv_data[i][0].strip()
        keys.append(key)
        block_name_temp, sink_name_temp = key.split(".")
        temp = sink_name_temp.split("_")
        refdes[key] = block_name_temp + ":" + temp[1]
        net[key] = "_".join(temp[2:-1])
        max_curr[key] = (
            str(float(sink_csv_data[i][i + 1])).rstrip("0").rstrip(".")
        )  # Remove trailing zeros and the trailing dot if it exists
        worst_ir_drop[key] = f"{float(sink_csv_data[i][-1]):.2f}"

    # Extracting data from xml:
    nominal_volt = {}
    lower_tolerance = {}
    allowed_volt_drop_mV = {}
    for line in sink_info:
        key = line["Name"].strip()
        nominal_volt[key] = (
            str(float(line["NominalVoltage"])).rstrip("0").rstrip(".")
        )  # Remove trailing zeros and the trailing dot if it exists
        lower_tolerance[key] = (
            str(float(line["LowerTolerance_Percentage"])).rstrip("0").rstrip(".")
        )  # Remove trailing zeros and the trailing dot if it exists
        allowed_volt_drop_mV[key] = (
            f"{float(line['LowerTolerance_Percentage'])*float(line['NominalVoltage'])*10:.2f}"
        )

    # add all the data to the gsheet_data without headers
    for key in keys:
        data_line = [
            net[key],
            refdes[key],
            max_curr[key],
            nominal_volt[key],
            lower_tolerance[key],
            allowed_volt_drop_mV[key],
            worst_ir_drop[key],
        ]
        gsheet_data.append(data_line)

    # 1.3 get the time stamp of the optimization csv file
    t = os.path.getmtime(sink_path)
    ti = str(datetime.datetime.fromtimestamp(t))

    # 2. check if upload gsheet tab is already exists
    # Iterate through the sheets in the spreadsheet and find the sheet with the matching name
    response = (
        service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    )  # get sheetID for the newly generated tab

    header_rows = 5  # number of rows occupied by header
    title_rows = 3
    header_cols = 6  # number of columns occupied by header

    sheet_id = None
    for sheet in response.get("sheets", []):
        if sheet["properties"]["title"] == tab_name:
            sheet_id = sheet["properties"]["sheetId"]
            result = (
                service.spreadsheets()
                .values()
                .get(
                    spreadsheetId=spreadsheet_id,
                    majorDimension="COLUMNS",
                    range=tab_name,
                )
                .execute()
            )
            values = result.get("values", [])
            last_col = len(values) + 1  # get the last column for adding border
            break

    if sheet_id is not None:
        # the tab already exsits, update the result ########################
        read_range = f"{tab_name}!A{header_rows+title_rows+1}:E"
        # read_range=tab_name
        response2 = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, majorDimension="ROWS", range=read_range)
            .execute()
        )

        existing_rail_info = response2["values"]
        new_rail_info = []
        max_index = len(existing_rail_info)
        write_index = []
        for item in gsheet_data:
            if item[0:5] in existing_rail_info:
                index = existing_rail_info.index(
                    item[0:5]
                )  # only match Net, Refdes, sink current and voltage
                write_index.append(index)
            else:
                # if the rail is not found in the existing rails, set the index to the last position
                write_index.append(max_index)
                max_index += 1
                new_rail_info.append(item[:-1])

        # add the new rail info #########################
        # first add new rows corresponding to new rails
        if len(new_rail_info) > 0:
            request_body = {
                "requests": [
                    {
                        "appendDimension": {
                            "sheetId": sheet_id,
                            "dimension": "ROWS",
                            "length": len(new_rail_info),
                        }
                    }
                ]
            }
            service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id, body=request_body
            ).execute()
            # add new rail info to the sheet
            # the position of the first cell
            cell_range_insert = f"{tab_name}!A{len(existing_rail_info)+header_rows+title_rows+1}"
            value_range_body = {"majorDimension": "ROWS", "values": new_rail_info}
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                valueInputOption="USER_ENTERED",
                range=cell_range_insert,
                body=value_range_body,
            ).execute()

        # insert a column for new data
        request_body = {
            "requests": [
                {
                    "insertDimension": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": header_cols,
                            "endIndex": header_cols + 1,
                        },
                        "inheritFromBefore": True,
                    }
                }
            ]
        }

        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=request_body
        ).execute()

        # write data to the new column  ###############################

        irdrop_write = [""] * max_index
        for i in range(len(gsheet_data)):
            irdrop_write[write_index[i]] = gsheet_data[i][-1]

        header = [ti, sink_path, "Worst IR-drop(mV)"]
        data_col = [header + irdrop_write]

        range1 = (
            tab_name + "!" + chr(64 + header_cols + 1) + str(header_rows + 1)
        )  # STARTING Positing is G6

        value_range_body = {"majorDimension": "COLUMNS", "values": data_col}
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            valueInputOption="USER_ENTERED",
            range=range1,
            body=value_range_body,
        ).execute()

    else:
        # tab does not exist add the new tab sheet ####################
        last_col = header_cols + 1
        batch_update_spreadsheet_body = {
            "requests": [{"addSheet": {"properties": {"title": tab_name}}}]
        }
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=batch_update_spreadsheet_body
        ).execute()
        response3 = (
            service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        )  # get sheetID for the newly generated tab
        for item in response3.get("sheets"):
            if item.get("properties").get("title") == tab_name:
                sheet_id = str(item.get("properties").get("sheetId"))

        # add the headers ####################################
        if list(cell_color.keys())[0] == "absolute":
            header_above = [
                [
                    "",
                    "Pass (Margin>" + str(cell_color["absolute"]) + "mV)",
                    "",
                    "Violations",
                    "",
                    "",
                ],
                [
                    "",
                    "Marginally pass (" + str(cell_color["absolute"]) + "mV" + ">Margin>0)",
                    "",
                    "",
                    "",
                    "",
                ],
                [
                    "",
                    "Marginally violate (0>Margin>" + str(-1 * cell_color["absolute"]) + "mV)",
                    "",
                    "",
                    "",
                    "",
                ],
                [
                    "",
                    "Violate (" + str(-1 * cell_color["absolute"]) + "mV>Margin)",
                    "",
                    "",
                    "",
                    "",
                ],
            ]
        else:
            header_above = [
                [
                    "",
                    "Pass (Margin>" + str(cell_color["percentage"] * 100) + "%)",
                    "",
                    "Violations",
                    "",
                    "",
                ],
                [
                    "",
                    "Marginally pass (" + str(cell_color["percentage"] * 100) + "%" + ">Margin>0)",
                    "",
                    "",
                    "",
                    "",
                ],
                [
                    "",
                    "Marginally violate (0>Margin>"
                    + str(-1 * cell_color["percentage"] * 200)
                    + "%)",
                    "",
                    "",
                    "",
                    "",
                ],
                [
                    "",
                    "Violate (" + str(-1 * cell_color["percentage"] * 200) + "%>Margin)",
                    "",
                    "",
                    "",
                    "",
                ],
            ]
        for i in range(header_rows - len(header_above) + 2):
            header_above.append(["", "", "", "", ""])

        worksheet_name = tab_name + "!"
        cell_range_insert = "A1"  # the position of the first cell
        value_range_body = {"majorDimension": "ROWS", "values": header_above}
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            valueInputOption="USER_ENTERED",
            range=worksheet_name + cell_range_insert,
            body=value_range_body,
        ).execute()

        # add the rail info data #########################
        # insert header data
        header = []

        header.append(
            [
                "Net",
                "RefDes",
                "Max Sink Current(A)",
                "Output Voltage",
                "Allowed Voltage Drop(%) ",
                "Allowed Voltage Drop(mV)",
                ti,
            ]
        )  # headers
        header.append(["", "", "", "", "", "", sink_path])
        header.append(["", "", "", "", "", "", "Worst IR-drop(mV)"])

        cell_range_insert = "A" + str(header_rows + 1)  # the position of the first header cell
        value_range_body = {"majorDimension": "ROWS", "values": header}
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            valueInputOption="USER_ENTERED",
            range=worksheet_name + cell_range_insert,
            body=value_range_body,
        ).execute()
        # print('All data uploaded')

        cell_range_insert = "A" + str(
            header_rows + title_rows + 1
        )  # the position of the first data cell
        value_range_body = {"majorDimension": "ROWS", "values": gsheet_data}
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            valueInputOption="USER_ENTERED",
            range=worksheet_name + cell_range_insert,
            body=value_range_body,
        ).execute()
        max_index = len(gsheet_data)

    print("All data uploaded")

    # 3.attach PDF report  ################################
    if pdn_report_url != "":
        hyperlink_formula = f'=HYPERLINK("{pdn_report_url}", "{ti}")'  # ti is the date and time
        # Build the batch update request
        batch_update_body = {
            "requests": [
                {
                    "updateCells": {
                        "range": {
                            "sheetId": sheet_id,  # Replace with the actual sheet ID if known
                            "startRowIndex": header_rows,
                            "endRowIndex": header_rows + 1,
                            "startColumnIndex": header_cols,
                            "endColumnIndex": header_cols + 1,
                        },
                        "rows": [
                            {"values": [{"userEnteredValue": {"formulaValue": hyperlink_formula}}]}
                        ],
                        "fields": "userEnteredValue",
                    }
                }
            ]
        }

        # Call the Sheets API to update the cell with the hyperlink
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=batch_update_body
        ).execute()

    # 4. change the color according to conditional formatting #####################
    my_range = {
        "sheetId": sheet_id,
        "startRowIndex": header_rows + title_rows,
        "endRowIndex": max_index + header_rows + title_rows,
        "startColumnIndex": header_cols,
        "endColumnIndex": header_cols + 1,
    }

    if list(cell_color.keys())[0] == "percentage":
        # change color according to percentage
        criteria = cell_color["percentage"]
        red_rule = (
            "=LT( (G"
            + str(header_rows + title_rows + 1)
            + "-D"
            + str(header_rows + title_rows + 1)
            + ")/"
            + "D"
            + str(header_rows + title_rows + 1)
            + ","
            + str(-1 * criteria)
            + ")"
        )
        orange_rule = (
            "=AND(GT( (G"
            + str(header_rows + title_rows + 1)
            + "-D"
            + str(header_rows + title_rows + 1)
            + ")/"
            + "D"
            + str(header_rows + title_rows + 1)
            + ","
            + str(-1 * criteria)
            + "), LTE( (G"
            + str(header_rows + title_rows + 1)
            + "-D"
            + str(header_rows + title_rows + 1)
            + ")/"
            + "D"
            + str(header_rows + title_rows + 1)
            + ","
            + str(0)
            + "))"
        )
        yellow_rule = (
            "=AND(GT( (G"
            + str(header_rows + title_rows + 1)
            + "-D"
            + str(header_rows + title_rows + 1)
            + ")/"
            + "D"
            + str(header_rows + title_rows + 1)
            + ","
            + str(0)
            + "), LTE( (G"
            + str(header_rows + title_rows + 1)
            + "-D"
            + str(header_rows + title_rows + 1)
            + ")/"
            + "D"
            + str(header_rows + title_rows + 1)
            + ","
            + str(criteria)
            + "))"
        )
        green_rule = (
            "=AND(GT( (G"
            + str(header_rows + title_rows + 1)
            + "-D"
            + str(header_rows + title_rows + 1)
            + ")/"
            + "D"
            + str(header_rows + title_rows + 1)
            + ","
            + str(criteria)
            + "), NOT(ISBLANK(G"
            + str(header_rows + title_rows + 1)
            + ")))"
        )
    else:

        criteria = cell_color["absolute"]
        red_rule = (
            "=LT((F"
            + str(header_rows + title_rows + 1)
            + "-G"
            + str(header_rows + title_rows + 1)
            + ")"
            + ","
            + str(-1 * criteria)
            + ")"
        )
        orange_rule = (
            "=AND(GT((F"
            + str(header_rows + title_rows + 1)
            + "-G"
            + str(header_rows + title_rows + 1)
            + ")"
            + ","
            + str(-1 * criteria)
            + ")*NOT(ISBLANK(F"
            + str(header_rows + title_rows + 1)
            + ")), LTE((F"
            + str(header_rows + title_rows + 1)
            + "-G"
            + str(header_rows + title_rows + 1)
            + ")"
            + ","
            + str(0)
            + "))"
        )
        yellow_rule = (
            "=AND(GT((F"
            + str(header_rows + title_rows + 1)
            + "-G"
            + str(header_rows + title_rows + 1)
            + ")"
            + ","
            + str(0)
            + ")*NOT(ISBLANK(G"
            + str(header_rows + title_rows + 1)
            + ")), LTE((F"
            + str(header_rows + title_rows + 1)
            + "-G"
            + str(header_rows + title_rows + 1)
            + ")"
            + ","
            + str(criteria)
            + "))"
        )
        green_rule = (
            "=GT((F"
            + str(header_rows + title_rows + 1)
            + "-G"
            + str(header_rows + title_rows + 1)
            + ")"
            + ","
            + str(criteria)
            + ")*NOT(ISBLANK(G"
            + str(header_rows + title_rows + 1)
            + "))"
        )

    requests = [
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [my_range],
                    "booleanRule": {
                        "condition": {
                            "type": "CUSTOM_FORMULA",
                            "values": [{"userEnteredValue": red_rule}],
                        },
                        "format": {
                            "backgroundColor": {
                                "red": 0.918,
                                "green": 0.6,
                                "blue": 0.6,
                            }  # red
                        },
                    },
                },
                "index": 0,
            }
        },
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [my_range],
                    "booleanRule": {
                        "condition": {
                            "type": "CUSTOM_FORMULA",
                            "values": [{"userEnteredValue": orange_rule}],
                        },
                        "format": {
                            "backgroundColor": {
                                "red": 1,
                                "green": 0.74,
                                "blue": 0.02,
                            }  # orange
                        },
                    },
                },
                "index": 0,
            }
        },
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [my_range],
                    "booleanRule": {
                        "condition": {
                            "type": "CUSTOM_FORMULA",
                            "values": [{"userEnteredValue": yellow_rule}],
                        },
                        "format": {
                            "backgroundColor": {
                                "red": 1,
                                "green": 0.898,
                                "blue": 0.6,
                            }  # light yellow
                        },
                    },
                },
                "index": 0,
            }
        },
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [my_range],
                    "booleanRule": {
                        "condition": {
                            "type": "CUSTOM_FORMULA",
                            "values": [{"userEnteredValue": green_rule}],
                        },
                        "format": {
                            "backgroundColor": {
                                "red": 0.714,
                                "green": 0.843,
                                "blue": 0.659,
                            }  # light green
                        },
                    },
                },
                "index": 0,
            }
        },
    ]
    body = {"requests": requests}
    service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()

    # 3.4 change the color of some cells if the simulation result is larger than spec
    start_r_red = []
    end_r_red = []
    start_c_red = []
    end_c_red = []
    start_r_orange = []
    end_r_orange = []
    start_c_orange = []
    end_c_orange = []
    start_r_yellow = []
    end_r_yellow = []
    start_c_yellow = []
    end_c_yellow = []
    start_r_green = []
    end_r_green = []
    start_c_green = []
    end_c_green = []
    start_r_red.append(3)
    start_c_red.append(0)
    end_r_red.append(4)
    end_c_red.append(1)
    start_r_orange.append(2)
    start_c_orange.append(0)
    end_r_orange.append(3)
    end_c_orange.append(1)
    start_r_yellow.append(1)
    start_c_yellow.append(0)
    end_r_yellow.append(2)
    end_c_yellow.append(1)
    start_r_green.append(0)
    start_c_green.append(0)
    end_r_green.append(1)
    end_c_green.append(1)

    # construct request
    if start_r_red != [] or start_r_orange != [] or start_r_green != []:
        request_body = {}
        request_body["requests"] = []
        for i in range(len(start_r_red)):
            updateCells = {}
            temp = {}
            updateCells["range"] = {
                "sheetId": sheet_id,
                "startRowIndex": start_r_red[i],
                "endRowIndex": end_r_red[i],
                "startColumnIndex": start_c_red[i],
                "endColumnIndex": end_c_red[i],
            }
            updateCells["rows"] = [
                {
                    "values": [
                        {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": 0.918,
                                    "green": 0.6,
                                    "blue": 0.6,
                                }  # light red
                            }
                        }
                    ]
                }
            ]
            updateCells["fields"] = "userEnteredFormat.backgroundColor"
            temp["updateCells"] = updateCells
            request_body["requests"].append(temp)

        for i in range(len(start_r_green)):
            updateCells = {}
            temp = {}
            updateCells["range"] = {
                "sheetId": sheet_id,
                "startRowIndex": start_r_green[i],
                "endRowIndex": end_r_green[i],
                "startColumnIndex": start_c_green[i],
                "endColumnIndex": end_c_green[i],
            }
            updateCells["rows"] = [
                {
                    "values": [
                        {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": 0.714,
                                    "green": 0.843,
                                    "blue": 0.659,
                                }  # light green
                            }
                        }
                    ]
                }
            ]
            updateCells["fields"] = "userEnteredFormat.backgroundColor"
            temp["updateCells"] = updateCells
            request_body["requests"].append(temp)

        for i in range(len(start_r_orange)):
            updateCells = {}
            temp = {}
            updateCells["range"] = {
                "sheetId": sheet_id,
                "startRowIndex": start_r_orange[i],
                "endRowIndex": end_r_orange[i],
                "startColumnIndex": start_c_orange[i],
                "endColumnIndex": end_c_orange[i],
            }
            updateCells["rows"] = [
                {
                    "values": [
                        {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": 1,
                                    "green": 0.74,
                                    "blue": 0.02,
                                }  # orange
                            }
                        }
                    ]
                }
            ]
            updateCells["fields"] = "userEnteredFormat.backgroundColor"
            temp["updateCells"] = updateCells
            request_body["requests"].append(temp)

        for i in range(len(start_r_yellow)):
            updateCells = {}
            temp = {}
            updateCells["range"] = {
                "sheetId": sheet_id,
                "startRowIndex": start_r_yellow[i],
                "endRowIndex": end_r_yellow[i],
                "startColumnIndex": start_c_yellow[i],
                "endColumnIndex": end_c_yellow[i],
            }
            updateCells["rows"] = [
                {
                    "values": [
                        {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": 1,
                                    "green": 0.898,
                                    "blue": 0.6,
                                }  # light yellow
                            }
                        }
                    ]
                }
            ]
            updateCells["fields"] = "userEnteredFormat.backgroundColor"
            temp["updateCells"] = updateCells
            request_body["requests"].append(temp)
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=request_body
        ).execute()

    # add cell borders, set cell width
    request_body = {
        "requests": [
            {
                "mergeCells": {
                    "mergeType": "MERGE_COLUMNS",
                    "range": {
                        "endColumnIndex": header_cols,
                        "endRowIndex": header_rows + title_rows,
                        "sheetId": sheet_id,
                        "startColumnIndex": 0,
                        "startRowIndex": header_rows,
                    },
                },
            },
            {
                "mergeCells": {
                    "mergeType": "MERGE_ROWS",
                    "range": {
                        "endColumnIndex": header_cols + 1,
                        "endRowIndex": header_rows + title_rows - 1,
                        "sheetId": sheet_id,
                        "startColumnIndex": header_cols,
                        "startRowIndex": header_rows,
                    },
                },
            },
            {
                "updateBorders": {  # update border for sink info from column A-F
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": len(gsheet_data) + header_rows + title_rows,
                        "startColumnIndex": 0,
                        "endColumnIndex": header_cols,
                    },
                    "top": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                    "bottom": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                    "right": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                    "innerHorizontal": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                    "innerVertical": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                }
            },
            {
                "updateBorders": {  # update boarder for all datas
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": header_rows,
                        "endRowIndex": max_index + header_rows + title_rows,
                        "startColumnIndex": header_cols,
                        "endColumnIndex": last_col,
                    },
                    "top": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                    "bottom": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                    "right": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                    "innerHorizontal": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                    "innerVertical": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                }
            },
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": 0,
                        "endIndex": header_cols + 1,
                    },
                    "properties": {"pixelSize": 100},
                    "fields": "pixelSize",
                }
            },
            {
                "updateCells": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        # "endRowIndex": len(existing_pwr) + 8,
                        "startColumnIndex": 0,  # ,
                        # "endColumnIndex": existing_cols
                    },
                    "rows": [
                        {"values": [{"userEnteredFormat": {"wrapStrategy": "OVERFLOW_CELL"}}]}
                    ],
                    # "fields": "userEnteredFormat(wrapStrategy)"
                    "fields": "userEnteredFormat.wrapStrategy",
                }
            },
            {
                "repeatCell": {  # this is for clipping the text
                    "range": {"sheetId": sheet_id},
                    "cell": {
                        "userEnteredFormat": {
                            "wrapStrategy": "CLIP",
                            "verticalAlignment": "TOP",
                            "horizontalAlignment": "LEFT",
                            # "numberFormat": {
                            #     "type": "TEXT",
                            #     "pattern": "#,##0.00"  # Specify the desired number format
                            # }
                        }
                    },
                    "fields": "userEnteredFormat.wrapStrategy,userEnteredFormat.verticalAlignment,"
                    "userEnteredFormat.horizontalAlignment",
                }
            },
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": sheet_id,
                        "gridProperties": {"frozenColumnCount": header_cols},
                    },
                    "fields": "gridProperties.frozenColumnCount",
                }
            },
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": sheet_id,
                        "gridProperties": {"frozenRowCount": header_rows},
                    },
                    "fields": "gridProperties.frozenRowCount",
                }
            },
        ]
    }
    service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=request_body).execute()


def summary_create(service, spreadsheet_id, tab_name_list):
    """create a summary tab"""
    tab_name = "SUMMARY"
    batch_update_spreadsheet_body = {
        "requests": [{"addSheet": {"properties": {"title": tab_name}}}]
    }
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body=batch_update_spreadsheet_body
    ).execute()

    header = [["Tab Name", "Violations"]]
    for i in range(len(tab_name_list)):
        header.append([tab_name_list[i], "=" + tab_name_list[i] + "!E1"])

    worksheet_name = tab_name + "!"
    cell_range_insert = "A1"  # the position of the first cell
    value_range_body = {"majorDimension": "ROWS", "values": header}
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        valueInputOption="USER_ENTERED",
        range=worksheet_name + cell_range_insert,
        body=value_range_body,
    ).execute()
    sheet_id = ""
    response5 = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    for item in response5.get("sheets"):
        if item.get("properties").get("title").upper() == tab_name:
            sheet_id = str(item.get("properties").get("sheetId"))
    # add cell borders
    request_body = {
        "requests": [
            {
                "updateBorders": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": len(tab_name_list) + 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": 2,
                    },
                    "top": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                    "bottom": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                    "right": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                    "innerHorizontal": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                    "innerVertical": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0, "green": 0, "blue": 0},
                    },
                }
            },
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": 0,
                        "endIndex": 2,
                    },
                    "properties": {"pixelSize": 120},
                    "fields": "pixelSize",
                }
            },
        ]
    }
    service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=request_body).execute()

    # add hyperlink
    sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = sheet_metadata.get("sheets", "")
    sheetid = {}
    for i in range(len(sheets)):
        name_temp = sheets[i]["properties"]["title"]
        url = (
            "https://docs.google.com/spreadsheets/d/"
            + spreadsheet_id
            + "/edit#gid="
            + str(sheets[i]["properties"]["sheetId"])
        )
        sheetid[name_temp] = url

    # construct requirement
    request_body = {}
    request_body["requests"] = []
    for i in range(len(header) - 1):
        url = sheetid[header[i + 1][0]]
        text = header[i + 1][0]
        update_cells = {}
        temp = {}
        update_cells["range"] = {
            "sheetId": sheet_id,
            "startRowIndex": i + 1,
            "endRowIndex": i + 2,
            "startColumnIndex": 0,
            "endColumnIndex": 1,
        }
        update_cells["rows"] = [
            {
                "values": [
                    {
                        "userEnteredValue": {
                            "formulaValue": '=HYPERLINK("' + url + '","' + text + '")'
                        }
                    }
                ]
            }
        ]
        update_cells["fields"] = "userEnteredValue"
        temp["updateCells"] = update_cells
        request_body["requests"].append(temp)
    service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=request_body).execute()

    # change the color according to contional formatting
    my_range = {
        "sheetId": sheet_id,
        "startRowIndex": 1,
        "endRowIndex": len(header),
        "startColumnIndex": 1,
        "endColumnIndex": 3,
    }

    red_rule = "=GT(CODE(B" + str(2) + ")," + str(48) + ")"
    # code: Returns the numeric Unicode map value of the first character in the string provided.

    requests = [
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [my_range],
                    "booleanRule": {
                        "condition": {
                            "type": "CUSTOM_FORMULA",
                            "values": [{"userEnteredValue": red_rule}],
                        },
                        "format": {
                            "backgroundColor": {
                                "red": 0.918,
                                "green": 0.6,
                                "blue": 0.6,
                            }  # red
                        },
                    },
                },
                "index": 0,
            }
        }
    ]
    body = {"requests": requests}
    service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()

    # zxc = 1


def summary_update(service, spreadsheet_id, tab_name_list):
    """update the summary tab"""
    tab_name = "SUMMARY"
    response = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, majorDimension="COLUMNS", range=tab_name)
        .execute()
    )
    if "values" in response:
        existing_tabs = response["values"][0][1:]

        header = []
        for i in range(len(tab_name_list)):
            if tab_name_list[i] not in existing_tabs and tab_name_list[i] != "SUMMARY":
                header.append([tab_name_list[i], "=" + tab_name_list[i] + "!E1"])

        worksheet_name = tab_name + "!"
        cell_range_insert = "A" + str(len(existing_tabs) + 2)  # the position of the first cell
        value_range_body = {"majorDimension": "ROWS", "values": header}
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            valueInputOption="USER_ENTERED",
            range=worksheet_name + cell_range_insert,
            body=value_range_body,
        ).execute()
        sheet_id = ""
        response5 = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        for item in response5.get("sheets"):
            if item.get("properties").get("title").upper() == tab_name:
                sheet_id = str(item.get("properties").get("sheetId"))
        # add cell borders
        request_body = {
            "requests": [
                {
                    "updateBorders": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 0,
                            "endRowIndex": len(existing_tabs) + len(header) + 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": 2,
                        },
                        "top": {
                            "style": "SOLID",
                            "width": 1,
                            "color": {"red": 0, "green": 0, "blue": 0},
                        },
                        "bottom": {
                            "style": "SOLID",
                            "width": 1,
                            "color": {"red": 0, "green": 0, "blue": 0},
                        },
                        "right": {
                            "style": "SOLID",
                            "width": 1,
                            "color": {"red": 0, "green": 0, "blue": 0},
                        },
                        "innerHorizontal": {
                            "style": "SOLID",
                            "width": 1,
                            "color": {"red": 0, "green": 0, "blue": 0},
                        },
                        "innerVertical": {
                            "style": "SOLID",
                            "width": 1,
                            "color": {"red": 0, "green": 0, "blue": 0},
                        },
                    }
                },
                {
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": 0,
                            "endIndex": 2,
                        },
                        "properties": {"pixelSize": 120},
                        "fields": "pixelSize",
                    }
                },
            ]
        }
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=request_body
        ).execute()

        # add hyperlink
        if header:  # header is not empty, new tabs are added
            sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheets = sheet_metadata.get("sheets", "")
            sheetid = {}
            for i in range(len(sheets)):
                if "SUMMARY" not in sheets[i]["properties"]["title"]:
                    name_temp = sheets[i]["properties"]["title"]
                    url = (
                        "https://docs.google.com/spreadsheets/d/"
                        + spreadsheet_id
                        + "/edit#gid="
                        + str(sheets[i]["properties"]["sheetId"])
                    )
                    sheetid[name_temp] = url

            # construct requirement
            request_body = {}
            request_body["requests"] = []
            for i in range(len(header)):
                url = sheetid[header[i][0]]
                text = header[i][0]
                updateCells = {}
                temp = {}
                updateCells["range"] = {
                    "sheetId": sheet_id,
                    "startRowIndex": i + len(existing_tabs) + 1,
                    "endRowIndex": i + 2 + len(existing_tabs),
                    "startColumnIndex": 0,
                    "endColumnIndex": 1,
                }
                updateCells["rows"] = [
                    {
                        "values": [
                            {
                                "userEnteredValue": {
                                    "formulaValue": '=HYPERLINK("' + url + '","' + text + '")'
                                }
                            }
                        ]
                    }
                ]
                updateCells["fields"] = "userEnteredValue"
                temp["updateCells"] = updateCells
                request_body["requests"].append(temp)
            service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id, body=request_body
            ).execute()

            # change the color according to contional formatting
            my_range = {
                "sheetId": sheet_id,
                "startRowIndex": 1,
                "endRowIndex": len(existing_tabs) + len(header) + 1,
                "startColumnIndex": 1,
                "endColumnIndex": 3,
            }

            red_rule = "=GT(CODE(B" + str(2) + ")," + str(48) + ")"
            # code: Returns the numeric Unicode map value of the
            # first character in the string provided.

            requests = [
                {
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [my_range],
                            "booleanRule": {
                                "condition": {
                                    "type": "CUSTOM_FORMULA",
                                    "values": [{"userEnteredValue": red_rule}],
                                },
                                "format": {
                                    "backgroundColor": {
                                        "red": 0.918,
                                        "green": 0.6,
                                        "blue": 0.6,
                                    }  # red
                                },
                            },
                        },
                        "index": 0,
                    }
                }
            ]
            body = {"requests": requests}
            service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
    else:  # there exist an empty summary page
        header = [["Tab Name", "Violations"]]
        for i in range(len(tab_name_list)):
            header.append([tab_name_list[i], "=" + tab_name_list[i] + "!E1"])

        worksheet_name = tab_name + "!"
        cell_range_insert = "A1"  # the position of the first cell
        value_range_body = {"majorDimension": "ROWS", "values": header}
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            valueInputOption="USER_ENTERED",
            range=worksheet_name + cell_range_insert,
            body=value_range_body,
        ).execute()

        response5 = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        for item in response5.get("sheets"):
            if item.get("properties").get("title").upper() == tab_name:
                sheet_id = str(item.get("properties").get("sheetId"))
        # add cell borders
        request_body = {
            "requests": [
                {
                    "updateBorders": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 0,
                            "endRowIndex": len(tab_name_list) + 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": 2,
                        },
                        "top": {
                            "style": "SOLID",
                            "width": 1,
                            "color": {"red": 0, "green": 0, "blue": 0},
                        },
                        "bottom": {
                            "style": "SOLID",
                            "width": 1,
                            "color": {"red": 0, "green": 0, "blue": 0},
                        },
                        "right": {
                            "style": "SOLID",
                            "width": 1,
                            "color": {"red": 0, "green": 0, "blue": 0},
                        },
                        "innerHorizontal": {
                            "style": "SOLID",
                            "width": 1,
                            "color": {"red": 0, "green": 0, "blue": 0},
                        },
                        "innerVertical": {
                            "style": "SOLID",
                            "width": 1,
                            "color": {"red": 0, "green": 0, "blue": 0},
                        },
                    }
                },
                {
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": 0,
                            "endIndex": 2,
                        },
                        "properties": {"pixelSize": 120},
                        "fields": "pixelSize",
                    }
                },
            ]
        }
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=request_body
        ).execute()

        # add hyperlink
        sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = sheet_metadata.get("sheets", "")
        sheetid = {}
        for i in range(len(sheets)):
            if "result" in sheets[i]["properties"]["title"]:
                name_temp = sheets[i]["properties"]["title"]
                url = (
                    "https://docs.google.com/spreadsheets/d/"
                    + spreadsheet_id
                    + "/edit#gid="
                    + str(sheets[i]["properties"]["sheetId"])
                )
                sheetid[name_temp] = url

        # construct requirement
        request_body = {}
        request_body["requests"] = []
        for i in range(len(header) - 1):
            url = sheetid[header[i + 1][0]]
            text = header[i + 1][0]
            updateCells = {}
            temp = {}
            updateCells["range"] = {
                "sheetId": sheet_id,
                "startRowIndex": i + 1,
                "endRowIndex": i + 2,
                "startColumnIndex": 0,
                "endColumnIndex": 1,
            }
            updateCells["rows"] = [
                {
                    "values": [
                        {
                            "userEnteredValue": {
                                "formulaValue": '=HYPERLINK("' + url + '","' + text + '")'
                            }
                        }
                    ]
                }
            ]
            updateCells["fields"] = "userEnteredValue"
            temp["updateCells"] = updateCells
            request_body["requests"].append(temp)
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=request_body
        ).execute()

        # change the color according to contional formatting
        my_range = {
            "sheetId": sheet_id,
            "startRowIndex": 1,
            "endRowIndex": len(header),
            "startColumnIndex": 1,
            "endColumnIndex": 3,
        }

        red_rule = "=GT(CODE(B" + str(2) + ")," + str(48) + ")"
        # code: Returns the numeric Unicode map value of the first character in the string provided.

        requests = [
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [my_range],
                        "booleanRule": {
                            "condition": {
                                "type": "CUSTOM_FORMULA",
                                "values": [{"userEnteredValue": red_rule}],
                            },
                            "format": {
                                "backgroundColor": {
                                    "red": 0.918,
                                    "green": 0.6,
                                    "blue": 0.6,
                                }  # red
                            },
                        },
                    },
                    "index": 0,
                }
            }
        ]
        body = {"requests": requests}
        service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()

    # zxc = 1
