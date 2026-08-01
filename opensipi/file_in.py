# SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
Author: yanshengw@
Last updated on Jul. 29, 2024

Description:
    This module processes input and output files.

    The entry point is the class ``FileIn``, which reads the simulation input
    from either a folder of csv files or a Google Sheet workbook and parses it
    into the ``input_data`` dict consumed by the rest of the platform. Four
    kinds of sheets are recognized, keyed off ``INPUT_FILE_STARTSWITH``:
    ``Sim*``, ``Special_Settings``, ``Stackup_Materials``, and ``Spec_Type``.
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
    """Read and parse the simulation input sheets.

    The input is read on instantiation, so the parsed result is available on
    the instance right away; there is no separate ``read()`` step.

    Attributes:
        INPUT_TYPE (str): Upper-cased input file type, ``"CSV"`` or
            ``"GSHEET"``.
        INPUT_FILE_STARTSWITH (list of str): The four recognized sheet name
            patterns, in the order ``[sim, special settings, stackup and
            materials, spec type]``. Normally ``INPUT_FILE_STARTSWITH`` from
            ``opensipi.constants.CONSTANTS``.
        INPUT_DATA (dict): The parsed input, with the keys ``"sim_input"``,
            ``"all_input"``, ``"stackup_info"``, ``"settings"``, and
            ``"spectype_info"``. See :meth:`_read_input_csv` for what each
            one holds.
    """

    def __init__(self, info):
        """Read and parse the input sheets described by ``info``.

        Args:
            info (dict): Input related information.

                * ``input_type`` (str): ``"CSV"`` or ``"GSHEET"``, upper case.
                * ``input_file_startswith`` (list of str): The four recognized
                  sheet name patterns.
                * ``input_dir`` (str): Slash-ending directory holding the input
                  csv files. Only used when ``input_type`` is ``"CSV"``.
                * ``account_key`` (str): Path to the Google account key file.
                  Only used when ``input_type`` is ``"GSHEET"``.
                * ``account_type`` (str): Google account type, e.g.
                  ``"service"``. Only used when ``input_type`` is
                  ``"GSHEET"``.
                * ``sheet_url`` (str): URL of the input Google Sheet. Only used
                  when ``input_type`` is ``"GSHEET"``.

        Raises:
            NoneUniqueKeyDefined: If a sim sheet defines a duplicated
                ``Unique_Key``.
            MaterialsMustBeDefinedBeforeStackup: If the ``Materials`` section
                is placed at or below the ``Stackup`` section.

        Note:
            An unrecognized ``input_type`` is not an error. Every entry of
            ``INPUT_DATA`` is left as an empty dict instead.
        """
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
        """Read the input csv files and parse them accordingly.

        Every csv file matching ``tgt_query`` is read and dispatched to a
        parser based on its file name. Files whose name matches none of
        ``INPUT_FILE_STARTSWITH`` are ignored silently.

        Args:
            tgt_query (str): Glob pattern selecting the input csv files, e.g.
                ``".../Sigrity_PDN/*.[cC][sS][vV]"``.

        Returns:
            tuple: A 5-tuple ``(sim_input, all_input, stackup_info, settings,
            spectype_info)``.

                * ``sim_input`` (dict): The enabled simulations only, keyed by
                  ``"[SHEET]_[Unique_Key]"``.
                * ``all_input`` (dict): Every simulation found, enabled or not,
                  keyed the same way.
                * ``stackup_info`` (dict): Materials, surface roughness, and
                  stackup, as returned by
                  :meth:`_FileIn__parse_stackup_info`. Empty if no stackup
                  sheet was found.
                * ``settings`` (dict): The special settings. Empty if no
                  special settings sheet was found.
                * ``spectype_info`` (dict): The built-in ``SPEC_TYPE`` defaults,
                  replaced wholesale by the user-defined spec types if a spec
                  type sheet was found.

        Raises:
            NoneUniqueKeyDefined: If a sim sheet defines a duplicated
                ``Unique_Key``.
            MaterialsMustBeDefinedBeforeStackup: If the ``Materials`` section
                is placed at or below the ``Stackup`` section.
            NoSpecialSettingsFound: If the special settings parser yields
                ``None``. The parsers never return ``None`` today, so a missing
                special settings sheet currently leaves ``settings`` as an
                empty dict rather than raising.
        """

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
        """Read the input Google Sheet tabs and parse them accordingly.

        The Google Sheet counterpart of :meth:`_read_input_csv`. Every tab of
        the workbook is read and dispatched to a parser based on its tab
        title, so a tab title plays the same role a csv file name does. Tabs
        whose title matches none of ``INPUT_FILE_STARTSWITH`` are ignored
        silently.

        Args:
            info (dict): Input related information.

                * ``account_key`` (str): Path to the Google account key file.
                * ``account_type`` (str): Google account type. Only
                  ``"service"`` is implemented; any other value leaves the
                  workbook unopened.
                * ``sheet_url`` (str): URL of the input Google Sheet.

        Returns:
            tuple: A 5-tuple ``(sim_input, all_input, stackup_info, settings,
            spectype_info)``, exactly as described in :meth:`_read_input_csv`.

        Raises:
            NoneUniqueKeyDefined: If a sim tab defines a duplicated
                ``Unique_Key``.
            MaterialsMustBeDefinedBeforeStackup: If the ``Materials`` section
                is placed at or below the ``Stackup`` section.
            NoSpecialSettingsFound: If the special settings parser yields
                ``None``. See the note in :meth:`_read_input_csv`.
            UnboundLocalError: If ``account_type`` is not ``"service"``, since
                no workbook is then opened.
        """

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
        """Parse one sim sheet into per-simulation row groups.

        Strips the whitespace around every cell, checks that the keys are
        unique, groups the rows into simulations, and reports which of those
        simulations are enabled.

        A simulation spans one or more consecutive rows. The first row of a
        simulation carries the ``Unique_Key`` in Col A; each following row with
        a blank Col A belongs to that same simulation. This is how a
        simulation with more than two ports spreads its port definitions over
        several rows.

        Args:
            raw_data (list of list of str): The sheet contents, first row being
                the column titles.
            wb_abbr (str): Upper-cased sheet abbreviation used to namespace the
                keys, e.g. ``"SIM1"``.

        Returns:
            tuple: A 2-tuple ``(checked_keys, data)``.

                * ``checked_keys`` (dict): The subset of ``data`` for the
                  enabled simulations, i.e. those with at least one row whose
                  ``CHECK_BOX`` cell holds the literal string ``"TRUE"``.
                * ``data`` (dict): Every simulation in the sheet, mapping
                  ``"[wb_abbr]_[Unique_Key]"`` to the list of that
                  simulation's rows. Each row is a dict keyed by the
                  upper-cased column titles.

        Raises:
            NoneUniqueKeyDefined: If the same ``Unique_Key`` appears more than
                once in this sheet.
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
        """Parse the special settings sheet into a flat lookup dict.

        Only the first two columns are used. The remaining columns of the
        sheet, ``Format`` and ``Descriptions``, are documentation for the user
        and are discarded here.

        Args:
            raw_data (list of list of str): The sheet contents. The first row
                is the header and is skipped.

        Returns:
            dict: Setting name to setting value, e.g.
            ``{"EXTRACTIONTOOL": "Sigrity", "EXTRACTIONTYPE": "PDN"}``. The
            names are upper-cased; the values are kept verbatim.
        """
        # strip white spaces before and after strings in the raw data
        rec_data = rectify_data(raw_data)
        ss_key = [tmp[0].upper() for tmp in rec_data]
        ss_value = []
        for tmp in rec_data:
            ss_value.append(tmp[1])
        settings = dict(zip(ss_key[1:], ss_value[1:]))
        return settings

    def __parse_spec_type(self, raw_data):
        """Parse the spec type sheet into the spec type lookup dict.

        The result starts from a copy of the built-in ``SPEC_TYPE`` defaults,
        so a user-defined spec type either adds a new entry or overrides a
        built-in one of the same name.

        Args:
            raw_data (list of list of str): The sheet contents. The first row
                is the header; its second and third cells name the two sub
                keys, normally ``Freq`` and ``Post_Process_Key``. Each
                remaining row defines one spec type as
                ``[name, freq, post_process_keys]``.

        Returns:
            dict: Upper-cased spec type name to its definition, e.g.
            ``{"ZPDN": {"FREQ": [0, 1000000000], "POST_PROCESS_KEY":
            ["ZOPEN", "ZSHORT"]}}``. The frequencies are comma-separated and
            converted to int; the post-processing keys are comma-separated and
            upper-cased.
        """
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
        """Parse the stackup and materials sheet into its three sections.

        The sheet is not a single table. It is a sequence of sections marked by
        the keywords ``Materials``, ``SurfaceRoughness``, and ``Stackup`` in
        Col A, so the sheet is scanned for those markers first and each section
        is then sliced out by row range. ``Materials`` must come before
        ``Stackup``; ``SurfaceRoughness`` is optional and sits between them.

        Args:
            raw_data (list of list of str): The sheet contents, holding the
                marked sections.

        Returns:
            dict: Three entries.

                * ``"materials"`` (list of list of str): The material rows,
                  header excluded.
                * ``"surfaceroughness"`` (list of list of str): The surface
                  roughness rows, header excluded. A single row of empty
                  strings if the section is absent.
                * ``"stackup"`` (dict): Upper-cased stackup column title to the
                  list of that column's values, one item per layer. Every
                  optional column absent from the sheet is added and filled
                  with empty strings, so the caller can index them
                  unconditionally.

        Raises:
            MaterialsMustBeDefinedBeforeStackup: If the ``Materials`` marker is
                at or below the ``Stackup`` marker.
            UnboundLocalError: If the ``Materials`` or the ``Stackup`` marker
                is missing from Col A altogether.
        """
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
