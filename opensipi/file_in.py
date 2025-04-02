# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
Author: yanshengw@
Last updated on Jul. 29, 2024

Description:
    This module processes input and output files.
"""


import glob

from opensipi.constants.CONSTANTS import SIM_INPUT_COL_TITLE, SPEC_TYPE
from opensipi.gsheet_io import GsheetIO
from opensipi.util.common import (
    SL,
    csv2listoflists,
    either_case,
    get_str_after_last_symbol,
    get_str_before_first_symbol,
    get_str_before_last_symbol,
    intfy_list,
    list_upper,
    listoflist2dictcol,
    rectify_data,
    rm_list_item,
    striped_str2list,
)
from opensipi.util.exceptions import (
    MaterialsMustBeDefinedBeforeStackup,
    NoneUniqueKeyDefined,
    NoSpecialSettingsFound,
)


class FileIn:
    def __init__(self, info):
        self.INPUT_TYPE = info["input_type"]
        self.INPUT_FILE_STARTSWITH = info["input_file_startswith"]
        if self.INPUT_TYPE == "CSV":
            ext = "".join([either_case(ltr) for ltr in self.INPUT_TYPE])
            tgt_query = info["input_dir"] + "*." + ext
            sim_input, all_input, stackup_info, settings, spectype_info = self._read_input_csv(
                tgt_query
            )
        elif self.INPUT_TYPE == "GSHEET":
            sim_input, all_input, stackup_info, settings, spectype_info = self._read_input_gsheet(
                info
            )
        else:
            sim_input = {}
            all_input = {}
            stackup_info = {}
            settings = {}
            spectype_info = {}
        self.INPUT_DATA = {
            "sim_input": sim_input,
            "all_input": all_input,
            "stackup_info": stackup_info,
            "settings": settings,
            "spectype_info": spectype_info,
        }

    def _read_input_csv(self, tgt_query):
        """read input csv files and parse them accordingly."""

        tgt_files = glob.glob(tgt_query)
        sim_input = {}
        all_input = {}
        settings = {}
        stackup_info = {}
        spectype_info = SPEC_TYPE.copy()
        for file in tgt_files:
            file_name = get_str_before_last_symbol(get_str_after_last_symbol(file, SL), ".").upper()
            raw_data = csv2listoflists(file)
            # sim inputs
            if file_name.startswith(self.INPUT_FILE_STARTSWITH[0]):
                wb_abbr = get_str_before_first_symbol(file_name, "_").upper()
                sim_data, all_data = self.__parse_sim_inputs(raw_data, wb_abbr)
                sim_input = {**sim_input, **sim_data}
                all_input = {**all_input, **all_data}
            # special settings
            elif file_name == self.INPUT_FILE_STARTSWITH[1]:
                settings = self.__parse_special_settings(raw_data)
            # stackup and materials
            elif file_name == self.INPUT_FILE_STARTSWITH[2]:
                stackup_info = self.__parse_stackup_info(raw_data)
            # spec type definitions
            elif file_name == self.INPUT_FILE_STARTSWITH[3]:
                spectype_info = self.__parse_spec_type(raw_data)
        if stackup_info is None:
            print(
                "Warning: No stackup and material is defined. The default "
                + "ones in the design file will be used for sims!"
            )
        if settings is None:
            raise NoSpecialSettingsFound()
        if spectype_info is None:
            print(
                "Warning: No spec type is defined. The default "
                + "ones in the opensipi platform will be used for sims!"
            )
        return sim_input, all_input, stackup_info, settings, spectype_info

    def _read_input_gsheet(self, info):
        """read input gsheets and parse them accordingly."""

        if info["account_type"].upper() == "SERVICE":
            sh = GsheetIO(info).get_sheet_service_account()
        else:
            pass  # to be improved
        # workbook info
        wb_info = sh.worksheets()
        wb_title = [wb_info[i].title for i in range(len(wb_info))]
        # read input and parse them
        sim_input = {}
        all_input = {}
        settings = {}
        stackup_info = {}
        spectype_info = SPEC_TYPE.copy()
        for title in wb_title:
            raw_data = sh.worksheet(title).get_all_values()
            file_name = title.upper()
            # sim inputs
            if file_name.startswith(self.INPUT_FILE_STARTSWITH[0]):
                wb_abbr = get_str_before_first_symbol(file_name, "_").upper()
                sim_data, all_data = self.__parse_sim_inputs(raw_data, wb_abbr)
                sim_input = {**sim_input, **sim_data}
                all_input = {**all_input, **all_data}
            # special settings
            elif file_name == self.INPUT_FILE_STARTSWITH[1]:
                settings = self.__parse_special_settings(raw_data)
            # stackup and materials
            elif file_name == self.INPUT_FILE_STARTSWITH[2]:
                stackup_info = self.__parse_stackup_info(raw_data)
            # spec type definitions
            elif file_name == self.INPUT_FILE_STARTSWITH[3]:
                spectype_info = self.__parse_spec_type(raw_data)
        if stackup_info is None:
            print(
                "Warning: No stackup and material is defined. The default "
                + "ones in the design file will be used for sims!"
            )
        if settings is None:
            raise NoSpecialSettingsFound()
        if spectype_info is None:
            print(
                "Warning: No spec type is defined. The default "
                + "ones in the opensipi platform will be used for sims!"
            )
        return sim_input, all_input, stackup_info, settings, spectype_info

    def __parse_sim_inputs(self, raw_data, wb_abbr):
        """Prepare the input data in the sim workbook:
        Strip all whitespaces before and after the strings.
        Check the uniqueness of the key.
        Merge sim inputs to dict.
        Output only the checked keys.
        """
        rows = len(raw_data)
        # strip white spaces before and after strings in the raw data
        rec_data = rectify_data(raw_data)
        # column title list
        col_title = list_upper(rec_data[0])
        # ?????????????????????????????????
        # To add a function to check if the col titles are legal
        # ?????????????????????????????????
        # check the uniqueness of the key
        all_key = rm_list_item([tmp[0] for tmp in rec_data[1:]], "")
        uni_key = [*set(all_key)]  # remove duplicates
        if len(all_key) != len(uni_key):
            raise NoneUniqueKeyDefined()
        # Merge sim inputs to dict by using the unique name of the power rails
        # as the key
        # col_title_dict = {wb_abbr+'_col_title': col_title}
        data = {}
        for i in range(1, rows):
            tmp_key = rec_data[i][0]
            dict_data = dict(zip(col_title, rec_data[i]))
            if tmp_key != "":
                i_key = wb_abbr + "_" + tmp_key
                i_value = [dict_data]
            else:
                i_value.append(dict_data)

            if (i + 1) < rows:
                if rec_data[i + 1][0] != "":
                    data[i_key] = i_value
            else:
                data[i_key] = i_value
        # pick up only the checked keys
        col_title_check = SIM_INPUT_COL_TITLE[1]
        checked_keys = {}
        data_keys = data.keys()
        for j_key in data_keys:
            check_status = [tmp[col_title_check] for tmp in data[j_key]]
            # as long as there is one 'TRUE' for the checked boxes ..
            if "TRUE" in check_status:
                checked_keys[j_key] = data[j_key]
        return checked_keys, data

    def __parse_special_settings(self, raw_data):
        """Prepare speciall settings."""
        # strip white spaces before and after strings in the raw data
        rec_data = rectify_data(raw_data)
        ss_key = [tmp[0].upper() for tmp in rec_data]
        ss_value = []
        for tmp in rec_data:
            ss_value.append(tmp[1])
        settings = dict(zip(ss_key[1:], ss_value[1:]))
        return settings

    def __parse_spec_type(self, raw_data):
        """Prepare spec types."""
        # strip white spaces before and after strings in the raw data
        rec_data = rectify_data(raw_data)
        header = rec_data[0]
        sub_key = [header[1].upper(), header[2].upper()]
        body = rec_data[1:]
        spectype = SPEC_TYPE.copy()
        for tmp in body:
            st_key = tmp[0].upper()
            spectype[st_key] = {
                sub_key[0]: intfy_list(striped_str2list(tmp[1], ",")),
                sub_key[1]: striped_str2list(tmp[2].upper(), ","),
            }
        return spectype

    def __parse_stackup_info(self, raw_data):
        """Prepare material, surface roughness and stackup info."""
        # strip white spaces before and after strings in the raw data
        rec_data = rectify_data(raw_data)
        # figure out which line is the start of material or stackup
        i = 0
        mark_sr = 0
        for line in rec_data:
            if line[0].upper() == "MATERIALS":
                mark_m = i
            elif line[0].upper() == "SURFACEROUGHNESS":
                mark_sr = i
            elif line[0].upper() == "STACKUP":
                mark_s = i
            i = i + 1
        # output stackup info
        stackup_info = {}
        if mark_sr == 0:  # if SurfaceRoughness is missing
            mark_sr = mark_s
            stackup_info["surfaceroughness"] = [[""] * len(rec_data[(mark_s + 1)])]
        else:
            stackup_info["surfaceroughness"] = rec_data[(mark_sr + 2) : mark_s]
        # check possible exceptions
        if mark_m >= mark_s:
            raise MaterialsMustBeDefinedBeforeStackup()
        # material info
        stackup_info["materials"] = rec_data[(mark_m + 2) : mark_sr]
        # stackup info
        stackup_list = rec_data[(mark_s + 1) :]
        stackup_key = [item.upper() for item in stackup_list[0]]
        stackup_list[0] = stackup_key  # Change keys to upper cases
        stackup_info["stackup"] = listoflist2dictcol(stackup_list)
        # add optional keywords in the stackup
        optional_key_list = [
            "OP_FILLIN_DIELECTRIC",
            "OP_ROUGHNESS_UPPER",
            "OP_ROUGHNESS_LOWER",
            "OP_ROUGHNESS_SIDE",
            "OP_TRAPEZOIDAL_ANGLE_DEG",
        ]
        for op_key in optional_key_list:
            if op_key not in stackup_key:
                stackup_info["stackup"][op_key] = [
                    "" for _ in stackup_info["stackup"]["LAYER_NAME"]
                ]
        return stackup_info
