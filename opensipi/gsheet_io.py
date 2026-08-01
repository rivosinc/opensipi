# SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
Author: yanshengw@
Last updated on Jan. 24, 2024

Description:
    This module handles gSheet services.

    ``GsheetIO`` opens a workbook, and is used both to read the simulation
input and to write the result summaries. ``TS2GSheet`` and ``DCR2GSheet``
write those summaries: one row per simulation key, one column per result file
type, with the cells linking back to the files uploaded to Google Drive.

    Writes go through the Google Sheets API, which is rate limited, so the
per-cell updates are deliberately paced.
"""

import random
from time import sleep

import gspread
from gspread_formatting import set_frozen


class GsheetIO:
    """gSheet client initialization and data retrieval using URL"""

    def __init__(self, info):
        """Resolve the workbook URL and the credentials to open it with.

        Nothing is opened here. Call one of the ``get_sheet_*`` methods to
        authorize and fetch the workbook.

        Args:
            info (dict): Google Sheet access information.

                * ``account_key`` (str): Path to the Google credentials file.
                * ``sheet_url`` (str): URL of the workbook. Takes precedence
                  over ``sheet_id``.
                * ``sheet_id`` (str): Workbook ID, used to build the URL when
                  ``sheet_url`` is absent.

        Note:
            Supplying neither ``sheet_url`` nor ``sheet_id`` is not reported
            here. ``self.sheet_url`` is then left unset and the failure
            surfaces as an ``AttributeError`` when the workbook is opened.
        """
        self.account_key = info["account_key"]
        if "sheet_url" in info:
            self.sheet_url = info["sheet_url"]
        elif "sheet_id" in info:
            self.sheet_url = "https://docs.google.com/spreadsheets/d" + "/{}/edit#gid=0".format(
                info["sheet_id"]
            )

    def get_sheet_service_account(self):
        """Open the workbook using a service account.

        Suited to unattended runs, since a service account needs no
        interactive consent. The workbook must be shared with the service
        account's address for this to succeed.

        Returns:
            gspread.Spreadsheet: The opened workbook.
        """
        # gSheet client initialization through service account
        gc = gspread.service_account(filename=self.account_key)
        # gSheet data retrieval using URL
        sh = gc.open_by_url(self.sheet_url)
        return sh

    def get_sheet_end_user(self):
        """Open the workbook using end user authorization.

        This may open a browser for consent on first use, so it suits
        interactive runs rather than unattended ones.

        Returns:
            gspread.Spreadsheet: The opened workbook.
        """
        # gSheet client initialization through end user authorization
        gc = gspread.oauth(credentials_filename=self.account_key)
        # gSheet data retrieval using URL
        sh = gc.open_by_url(self.sheet_url)
        return sh


class TS2GSheet:
    """Output a summary of the simulation results to gSheet.

    Builds a table of one row per simulation key and one column per result file
    type, where every cell is a hyperlink to the corresponding file in Google
    Drive.

    Attributes:
        GDRIVE_VIEW_URL (str): Prefix turning a Google Drive file ID into a
            viewable link.
        ALPHABET (str): Column letters, indexed to convert a zero-based column
            number into its A1-notation letter. This caps the sheet at 26
            columns.
    """

    GDRIVE_VIEW_URL = "https://docs.google.com/open?id="
    ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    def __init__(self, info):
        """Open the summary workbook and record what is to be written to it.

        Args:
            info (dict): Export related information.

                * ``account_key``, ``sheet_url`` or ``sheet_id``: Passed
                  through to :class:`GsheetIO`.
                * ``file_id_book`` (dict): Simulation key to the list of its
                  result files, each entry being
                  ``[file_name, gdrive_file_id, file_type]``.
                * ``uni_file_type`` (list of str): The distinct result file
                  types, in the order their columns are laid out.
                * ``report_id_book`` (dict): Holds the ``"report"`` key, the
                  Google Drive ID of the run report.
                * ``run_time`` (str): Run time stamp, used to label the report.
                * ``usr_id`` (str): User ID, shown in the header.
                * ``log`` (logging.Logger): The run logger.
        """
        self.sh = GsheetIO(info).get_sheet_service_account()
        self.file_id_book = info["file_id_book"]
        self.uni_file_type = info["uni_file_type"]
        self.report_id_book = info["report_id_book"]
        self.run_time = info["run_time"]
        self.usr_id = info["usr_id"]
        self.lg = info["log"]

    def export_results(self):
        """Write the S-parameter result summary to the workbook.

        Renames the default first sheet to ``Summary``, ensures a ``Results``
        sheet exists, and fills it in. Repeated runs append to the same
        ``Results`` sheet rather than replacing it, so a simulation key already
        present is updated in place.
        """
        # rename the default 1st sheet
        self.sh.sheet1.update_title("Summary")

        # add new sheet if it doesn't exist
        new_sheet_name = "Results"
        self.__add_sheet(new_sheet_name)
        # update gSheet
        self._update_sheet(new_sheet_name)

    def __add_sheet(self, wb_name):
        """Add a new sheet if it doesn't exist.

        Args:
            wb_name (str): Sheet title to create.
        """
        wb_info = self.sh.worksheets()
        wb_title = [wb_info[i].title for i in range(len(wb_info))]
        if wb_name not in wb_title:
            self.sh.add_worksheet(title=wb_name, rows=100, cols=20)
            self.lg.debug("Workbook " + wb_name + " is successfully created!")
        else:
            self.lg.debug("Workbook " + wb_name + " already exists!")

    def _update_sheet(self, wb_name):
        """Update gSheet.

        Inserts this run's header columns, links the run report from the merged
        top row, freezes the header, and then writes one row per simulation
        key. The header row is given a random background color so that runs
        stacked side by side in the same sheet stay visually separable.

        Args:
            wb_name (str): Title of the sheet to update.
        """
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
        """Attach result links to the summary gSheet.

        One cell is written per result file of this simulation, each placed in
        the column matching its file type.

        Args:
            wb (gspread.Worksheet): The sheet to write to.
            i_key (str): Simulation key whose row is being filled.
            row_index (int): One-based row number of that key.

        Note:
            The calls are paced by a short sleep on either side of each write
            to stay under the Google Sheets API rate limit, so a summary with
            many result files takes a while to write.
        """
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
        """Get the header list of list.

        Returns:
            list of list of str: One inner list per result file type, each
            holding ``[report label, user ID, file type]``. Only the first
            column carries the label and the user ID; the rest leave those
            cells empty so they can be merged across.
        """
        header = [["Report_" + self.run_time, self.usr_id, self.uni_file_type[0]]]
        type_count = len(self.uni_file_type)
        if type_count > 1:
            for i in range(1, type_count):
                header.append(["", "", self.uni_file_type[i]])
        return header


class DCR2GSheet:
    """Export DCR results to GSheet.

    The DCR counterpart of :class:`TS2GSheet`. DCR yields a single resistance
    number per simulation rather than a set of files, so the summary is one
    value column and the cells hold values instead of links.

    Attributes:
        ALPHABET (str): Column letters, indexed to convert a zero-based column
            number into its A1-notation letter.
    """

    ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    def __init__(self, info):
        """Open the summary workbook and record the DCR results to write.

        Args:
            info (dict): Export related information.

                * ``account_key``, ``sheet_url`` or ``sheet_id``: Passed
                  through to :class:`GsheetIO`.
                * ``dcr_dict`` (dict): Simulation key to its extracted
                  resistance in mOhm.
                * ``run_time`` (str): Run time stamp, used to label the run.
                * ``usr_id`` (str): User ID, shown in the header.
                * ``log`` (logging.Logger): The run logger.
        """
        self.sh = GsheetIO(info).get_sheet_service_account()
        self.dcr_dict = info["dcr_dict"]
        self.run_time = info["run_time"]
        self.usr_id = info["usr_id"]
        self.lg = info["log"]

    def export_results(self):
        """Write the DCR result summary to the workbook.

        Renames the default first sheet to ``Summary``, ensures a ``Results``
        sheet exists, and fills it in. Repeated runs append to the same
        ``Results`` sheet, so a simulation key already present is updated in
        place.
        """
        # rename the default 1st sheet
        self.sh.sheet1.update_title("Summary")

        # add new sheet if it doesn't exist
        new_sheet_name = "Results"
        self.__add_sheet(new_sheet_name)
        # update gSheet
        self._update_sheet(new_sheet_name)

    def __add_sheet(self, wb_name):
        """Add a new sheet if it doesn't exist.

        Args:
            wb_name (str): Sheet title to create.
        """
        wb_info = self.sh.worksheets()
        wb_title = [wb_info[i].title for i in range(len(wb_info))]
        if wb_name not in wb_title:
            self.sh.add_worksheet(title=wb_name, rows=100, cols=20)
            self.lg.debug("Workbook " + wb_name + " is successfully created!")
        else:
            self.lg.debug("Workbook " + wb_name + " already exists!")

    def _update_sheet(self, wb_name):
        """Update gSheet.

        The same layout as :meth:`TS2GSheet._update_sheet`, minus the report
        hyperlink, since a DCR run summarizes to values rather than to files.

        Args:
            wb_name (str): Title of the sheet to update.
        """
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
        """Attach result to the summary gSheet.

        Args:
            wb (gspread.Worksheet): The sheet to write to.
            i_key (str): Simulation key whose row is being filled.
            row_index (int): One-based row number of that key.
        """
        val = self.dcr_dict[i_key]
        i = 1
        cell_id = self.ALPHABET[i] + str(row_index)
        wb.update(cell_id, val)
        wb.format(cell_id, {"wrapStrategy": "WRAP"})

    def _get_header(self):
        """Get the header list of list.

        Returns:
            list of list of str: A single inner list holding
            ``[report label, user ID, "DCR (mOhm)"]``, since DCR summarizes to
            one value column.
        """
        header = [["Report_" + self.run_time, self.usr_id, "DCR (mOhm)"]]
        return header
