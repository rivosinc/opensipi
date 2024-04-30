# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
Author: yanshengw@
Last updated on Jan. 24, 2024

Description:
    This module handles gSheet services.
"""


import random
from time import sleep

import gspread
from gspread_formatting import set_frozen


class GsheetIO:
    """gSheet client initialization and data retrieval using URL"""

    def __init__(self, info):
        self.account_key = info["account_key"]
        if "sheet_url" in info:
            self.sheet_url = info["sheet_url"]
        elif "sheet_id" in info:
            self.sheet_url = "https://docs.google.com/spreadsheets/d" + "/{}/edit#gid=0".format(
                info["sheet_id"]
            )

    def get_sheet_service_account(self):
        # gSheet client initialization through service account
        gc = gspread.service_account(filename=self.account_key)
        # gSheet data retrieval using URL
        sh = gc.open_by_url(self.sheet_url)
        return sh

    def get_sheet_end_user(self):
        # gSheet client initialization through end user authorization
        gc = gspread.oauth(credentials_filename=self.account_key)
        # gSheet data retrieval using URL
        sh = gc.open_by_url(self.sheet_url)
        return sh


class TS2GSheet:
    """Output a summary of the simulation results to gSheet."""

    GDRIVE_VIEW_URL = "https://docs.google.com/open?id="
    ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    def __init__(self, info):
        self.sh = GsheetIO(info).get_sheet_service_account()
        self.file_id_book = info["file_id_book"]
        self.uni_file_type = info["uni_file_type"]
        self.report_id_book = info["report_id_book"]
        self.run_time = info["run_time"]
        self.usr_id = info["usr_id"]
        self.lg = info["log"]

    def export_results(self):
        """"""
        # rename the default 1st sheet
        self.sh.sheet1.update_title("Summary")

        # add new sheet if it doesn't exist
        new_sheet_name = "Results"
        self.__add_sheet(new_sheet_name)
        # update gSheet
        self._update_sheet(new_sheet_name)

    def __add_sheet(self, wb_name):
        """Add a new sheet if it doesn't exist."""
        wb_info = self.sh.worksheets()
        wb_title = [wb_info[i].title for i in range(len(wb_info))]
        if wb_name not in wb_title:
            self.sh.add_worksheet(title=wb_name, rows=100, cols=20)
            self.lg.debug("Workbook " + wb_name + " is successfully created!")
        else:
            self.lg.debug("Workbook " + wb_name + " already exists!")

    def _update_sheet(self, wb_name):
        """Update gSheet."""
        wb = self.sh.worksheet(wb_name)
        fixed_cols = 1
        # row 1 and 2 are headers
        header = self._get_header()
        wb.insert_cols(values=header, col=2)
        last_header_row = len(header[0])
        wb.update("A" + str(last_header_row), "Sim Key")
        # merge report row
        report_cell_id = "B1"
        report_cell_str = "Report_" + self.run_time
        report_url = self.GDRIVE_VIEW_URL + self.report_id_book["report"]
        wb.update_acell(
            report_cell_id, '=HYPERLINK("' + report_url + '","' + report_cell_str + '")'
        )
        last_header_col = self.ALPHABET[len(header) - 1 + fixed_cols]
        merge_range = report_cell_id + ":" + last_header_col + "1"
        wb.merge_cells(merge_range)
        wb.format(
            merge_range,
            {
                "horizontalAlignment": "CENTER",
                "backgroundColorStyle": {
                    "rgbColor": {
                        "red": random.uniform(0, 1),
                        "green": random.uniform(0, 1),
                        "blue": random.uniform(0, 1),
                    }
                },
            },
        )
        # merge author row
        author_cell_id = "B2"
        merge_range = author_cell_id + ":" + last_header_col + "2"
        wb.merge_cells(merge_range)
        # freeze rows and cols
        set_frozen(wb, rows=last_header_row, cols=fixed_cols)
        # attach results
        for i_key in self.file_id_book:
            ex_sim_key = wb.col_values(1)
            if i_key in ex_sim_key:
                row_index = ex_sim_key.index(i_key) + 1
                self.__attach_results(wb, i_key, row_index)
            else:
                row_index = len(ex_sim_key) + 1
                cell_id = "A" + str(row_index)
                wb.update(cell_id, i_key)
                wb.format(cell_id, {"wrapStrategy": "WRAP"})
                self.__attach_results(wb, i_key, row_index)
        # add border
        border_range = last_header_col + "1:" + last_header_col + str(len(wb.col_values(1)))
        wb.format(border_range, {"borders": {"right": {"style": "DOUBLE"}}})

    def __attach_results(self, wb, i_key, row_index):
        """Attach result links to the summary gSheet."""
        val = self.file_id_book[i_key]
        for i_val in val:
            i = self.uni_file_type.index(i_val[2]) + 1
            cell_id = self.ALPHABET[i] + str(row_index)
            tgt_url = self.GDRIVE_VIEW_URL + i_val[1]
            sleep(1.1)
            wb.update_acell(cell_id, '=HYPERLINK("' + tgt_url + '","' + i_val[0] + '")')
            sleep(1.1)
            wb.format(cell_id, {"wrapStrategy": "WRAP"})

    def _get_header(self):
        """Get the header list of list."""
        header = [["Report_" + self.run_time, self.usr_id, self.uni_file_type[0]]]
        type_count = len(self.uni_file_type)
        if type_count > 1:
            for i in range(1, type_count):
                header.append(["", "", self.uni_file_type[i]])
        return header


class DCR2GSheet:
    """Export DCR results to GSheet."""

    ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    def __init__(self, info):
        self.sh = GsheetIO(info).get_sheet_service_account()
        self.dcr_dict = info["dcr_dict"]
        self.run_time = info["run_time"]
        self.usr_id = info["usr_id"]
        self.lg = info["log"]

    def export_results(self):
        """"""
        # rename the default 1st sheet
        self.sh.sheet1.update_title("Summary")

        # add new sheet if it doesn't exist
        new_sheet_name = "Results"
        self.__add_sheet(new_sheet_name)
        # update gSheet
        self._update_sheet(new_sheet_name)

    def __add_sheet(self, wb_name):
        """Add a new sheet if it doesn't exist."""
        wb_info = self.sh.worksheets()
        wb_title = [wb_info[i].title for i in range(len(wb_info))]
        if wb_name not in wb_title:
            self.sh.add_worksheet(title=wb_name, rows=100, cols=20)
            self.lg.debug("Workbook " + wb_name + " is successfully created!")
        else:
            self.lg.debug("Workbook " + wb_name + " already exists!")

    def _update_sheet(self, wb_name):
        """Update gSheet."""
        wb = self.sh.worksheet(wb_name)
        fixed_cols = 1
        # row 1 and 2 are headers
        header = self._get_header()
        wb.insert_cols(values=header, col=2)
        last_header_row = len(header[0])
        wb.update("A" + str(last_header_row), "Sim Key")
        # merge report row
        report_cell_id = "B1"
        last_header_col = self.ALPHABET[len(header) - 1 + fixed_cols]
        merge_range = report_cell_id + ":" + last_header_col + "1"
        wb.merge_cells(merge_range)
        wb.format(
            merge_range,
            {
                "horizontalAlignment": "CENTER",
                "backgroundColorStyle": {
                    "rgbColor": {
                        "red": random.uniform(0, 1),
                        "green": random.uniform(0, 1),
                        "blue": random.uniform(0, 1),
                    }
                },
            },
        )
        # freeze rows and cols
        set_frozen(wb, rows=last_header_row, cols=fixed_cols)
        # attach results
        for i_key in self.dcr_dict:
            ex_sim_key = wb.col_values(1)
            if i_key in ex_sim_key:
                row_index = ex_sim_key.index(i_key) + 1
                self.__attach_results(wb, i_key, row_index)
            else:
                row_index = len(ex_sim_key) + 1
                cell_id = "A" + str(row_index)
                wb.update(cell_id, i_key)
                wb.format(cell_id, {"wrapStrategy": "WRAP"})
                self.__attach_results(wb, i_key, row_index)
        # add border
        border_range = last_header_col + "1:" + last_header_col + str(len(wb.col_values(1)))
        wb.format(border_range, {"borders": {"right": {"style": "DOUBLE"}}})

    def __attach_results(self, wb, i_key, row_index):
        """Attach result to the summary gSheet."""
        val = self.dcr_dict[i_key]
        i = 1
        cell_id = self.ALPHABET[i] + str(row_index)
        wb.update(cell_id, val)
        wb.format(cell_id, {"wrapStrategy": "WRAP"})

    def _get_header(self):
        """Get the header list of list."""
        header = [["Report_" + self.run_time, self.usr_id, "DCR (mOhm)"]]
        return header
