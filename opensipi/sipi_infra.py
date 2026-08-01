# SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
Author: yanshengw@
Last updated on Nov. 20, 2023

Description:
    This module serves as the platform of the OpenSIPI application.

    ``Platform`` is the spine of the application. It owns the run folder tree,
reads the input, picks the solver executor matching the extraction type, drives
the run, post-processes the results, and builds the report. The integrated
flows in ``opensipi.integrated_flows`` are thin sequences of its methods.

    The methods are order-dependent rather than independent. Construction reads
the input and creates the folders, ``drop_dsn_file`` settles which design is
being simulated, ``parser`` chooses the executor, and only then can ``run`` and
``report`` do anything. Between stages the state is handed over through yaml
config files written into the run folder, which is what lets a later stage be
re-run on its own against an existing ``Run_...`` folder.
"""

import glob
import os
import shutil

import jinja2
import pdfkit
from pdfme import build_pdf

from opensipi import __version__
from opensipi.constants.CONSTANTS import (
    INPUT_FILE_STARTSWITH,
    POST_PROCESS_KEY_ORDER_IO,
    POST_PROCESS_KEY_ORDER_PDN,
)
from opensipi.file_in import FileIn
from opensipi.gdrive_io import XtractResults2Drive
from opensipi.gsheet_io import DCR2GSheet, TS2GSheet
from opensipi.sigrity_exec import (
    ClarityExec,
    PowerdcExec,
    PowersiIOExec,
    PowersiPdnExec,
)
from opensipi.templates.temp_report import io_report, pdn_report
from opensipi.touchstone import TouchStone
from opensipi.util.common import (
    SL,
    csv2dict,
    expand_home_dir,
    export_dict_to_yaml,
    get_dir,
    get_root_dir,
    get_run_time,
    get_str_before_last_n_symbol,
    img2str,
    load_yaml_to_dict,
    make_dir,
    rectify_dir,
    rm_ext,
    slash_ending,
    unique_list,
)
from opensipi.util.exceptions import NoDsnFound, NoProjDirDefined
from opensipi.util.logs import setup_logger


class Platform:
    """platform class for the opensipi applications.

    Attributes:
        INPUT_TYPE (str): Upper-cased input type, ``"CSV"`` or ``"GSHEET"``.
        RUN_NAME (str): Name of this run, being the extraction type and a time
            stamp, or the caller-supplied name when resuming.
        input_data (dict): The parsed input sheets. See
            ``opensipi.file_in.FileIn``.
        lg (logging.Logger): The run logger, writing to the run's ``Log``
            folder.
        DSN_NAME (str): File name of the design being simulated. Empty until
            :meth:`drop_dsn_file` runs.
        LOC_DSN_RAW (str): File name of the local design copy. Empty until
            :meth:`drop_dsn_file` runs.
    """

    def __init__(self, info):
        """Build the run folder tree, read the input, and start logging.

        A fair amount happens here. The folder tree is created, the input
        sheets are read and parsed, and a logger is opened, so an instance is
        never in a half-built state. Logging can only start once the log
        folder exists, so anything going wrong before that point is reported
        by print rather than to the log file.

        Args:
            info (dict): Input related information.

                * ``input_type`` (str): ``"csv"`` or ``"gsheet"``, matched
                  case-insensitively.
                * ``input_dir`` (str): Directory holding the input csv folders.
                  Required when ``input_type`` is ``"csv"``.
                * ``input_folder`` (str): Name of the folder inside
                  ``input_dir`` holding this extraction's sheets. Required when
                  ``input_type`` is ``"csv"``.
                * ``input_url`` (str): URL of the input Google Sheet. Required
                  when ``input_type`` is ``"gsheet"``.
                * ``proj_dir`` (str): The project directory. Optional when
                  ``input_dir`` is given, since it is then derived from it.
                * ``output_type`` (str, optional): ``"local"`` or ``"gdrive"``.
                  Defaults to ``"local"``.
                * ``op_run_name`` (str, optional): Time stamp of an existing
                  ``Run_...`` folder to resume into. Omit or leave empty to
                  start a new run.

        Raises:
            NoProjDirDefined: If neither ``proj_dir`` nor ``input_dir`` is
                given.
            NoneUniqueKeyDefined: If a sim sheet defines a duplicated
                ``Unique_Key``.
            MaterialsMustBeDefinedBeforeStackup: If the ``Materials`` section
                is placed at or below the ``Stackup`` section.
        """
        self.INPUT_TYPE = info["input_type"].upper()
        # module internal dir
        self.INSTALL_ROOT_DIR, self.SCRIPTS_DIR, self.TEMPLATE_DIR = get_dir()
        self.TOOL_CONFIG_DIR = get_root_dir() + "opensipi_config" + SL
        make_dir(self.TOOL_CONFIG_DIR)
        # file I/O info
        self.filein_info = self._get_filein_info(info)
        self.fileout_info = self._get_fileout_info(info)
        self.input_data = self._read_inputs()
        xtract_type = self.input_data["settings"]["EXTRACTIONTYPE"].upper()

        # get run name through run time
        if "op_run_name" not in info:
            self.RUN_NAME = xtract_type + "_" + get_run_time()
        elif info["op_run_name"] == "":
            self.RUN_NAME = xtract_type + "_" + get_run_time()
        else:
            self.RUN_NAME = info["op_run_name"]
        # project dir
        self.PROJ_DIR, self.Loc_proj_name = self._get_proj_dir(info)
        (
            self.DSN_DIR,
            self.LOC_DSN_DIR,
            self.LOC_SCRIPT_DIR,
            self.SIM_DIR,
            self.RESULT_DIR,
            self.REPORT_DIR,
            self.LOG_DIR,
            self.PLT_DIR,
            self.RUN_KEY_DIR,
            self.MODEL_CHECK_DIR,
        ) = self._mk_proj_dir(self.PROJ_DIR, self.RUN_NAME)
        # set up logging, which can only be done after log dir is made
        log_time = get_run_time()  # a new log file is created for each run
        log_name = self.LOG_DIR + "xtract_" + log_time + ".log"
        log_header = __name__
        self.lg = setup_logger(log_name, log_header)
        self.lg.debug("opensipi version: " + __version__)
        self.lg.debug("Log file for Run_" + log_time + " is created.")
        # Class properties that will be assigned after running certain methods
        self.DSN_NAME = ""
        self.LOC_DSN_RAW = ""

    # ==========================================================================
    # Class initialization related method
    # ==========================================================================
    def _read_inputs(self):
        """Read input data based on input_type.

        Returns:
            dict: The parsed input, with the keys ``"sim_input"``,
            ``"all_input"``, ``"stackup_info"``, ``"settings"``, and
            ``"spectype_info"``.
        """
        input_data = FileIn(self.filein_info).INPUT_DATA
        return input_data

    def _get_proj_dir(self, info):
        """Get the project directory.

        An explicit ``proj_dir`` wins. Otherwise the project directory is
        taken to be two levels above ``input_dir``, matching the expected
        ``project / Sim_Input / extraction folder`` layout.

        Args:
            info (dict): The constructor's ``info`` dict.

        Returns:
            tuple: A 2-tuple ``(proj_dir, proj_name)``, the separator-ending
            project directory and its last path component.

        Raises:
            NoProjDirDefined: If neither ``proj_dir`` nor ``input_dir`` is
                given.
        """
        if "proj_dir" in info:
            proj_dir = info["proj_dir"]
        elif "input_dir" in info:
            input_dir = expand_home_dir(slash_ending(rectify_dir(info["input_dir"])))
            proj_dir = get_str_before_last_n_symbol(input_dir, SL, 2) + SL
        else:
            raise NoProjDirDefined()
        proj_name = proj_dir.split(SL)[-2]
        return proj_dir, proj_name

    def _get_filein_info(self, info):
        """Get the dict used to query input data.

        Normalizes the caller's paths and, for the Google Sheet path, folds in
        the credentials read from ``config_gsuites.yaml``, so the reader gets
        one uniform dict either way.

        Args:
            info (dict): The constructor's ``info`` dict.

        Returns:
            dict: The ``info`` dict for ``opensipi.file_in.FileIn``.

        Raises:
            UnboundLocalError: If ``INPUT_TYPE`` is neither ``"CSV"`` nor
                ``"GSHEET"``.
            FileNotFoundError: If the Google Sheet path is taken and
                ``config_gsuites.yaml`` is missing.
        """
        if self.INPUT_TYPE == "CSV":
            input_dir = expand_home_dir(slash_ending(rectify_dir(info["input_dir"])))
            input_dir = input_dir + info["input_folder"] + SL
            input_info = {
                "input_type": self.INPUT_TYPE,
                "input_dir": input_dir,
                "input_file_startswith": INPUT_FILE_STARTSWITH,
            }
        elif self.INPUT_TYPE == "GSHEET":
            gsuites_config = load_yaml_to_dict(self.TOOL_CONFIG_DIR + "config_gsuites.yaml")
            input_info = {
                "input_type": self.INPUT_TYPE,
                "account_key": expand_home_dir(rectify_dir(gsuites_config["ACCOUNT_KEY_DIR"])),
                "account_type": gsuites_config["ACCOUNT_TYPE"],
                "sheet_url": info["input_url"],
                "input_file_startswith": INPUT_FILE_STARTSWITH,
            }
        return input_info

    def _get_fileout_info(self, info):
        """Get the dict used to store output data.

        The Google credentials are only read when an upload is actually
        requested, so a purely local run needs no ``config_gsuites.yaml``.

        Args:
            info (dict): The constructor's ``info`` dict.

        Returns:
            dict: Output settings. Holds ``output_type`` alone for a local run,
            plus the account and Drive IDs for a ``gdrive`` run.
        """
        if "output_type" in info:
            output_type = info["output_type"]
        else:
            output_type = "local"

        if output_type.upper() == "GDRIVE":
            gsuites_config = load_yaml_to_dict(self.TOOL_CONFIG_DIR + "config_gsuites.yaml")
            drive_info = {
                "output_type": output_type,
                "account_key": expand_home_dir(rectify_dir(gsuites_config["ACCOUNT_KEY_DIR"])),
                "account_type": gsuites_config["ACCOUNT_TYPE"],
                "root_drive_id": gsuites_config["ROOT_GDRIVE_ID"],
                "out_sheet_gdrive_id": gsuites_config["OUT_SHEET_GDRIVE_ID"],
            }
        else:
            drive_info = {
                "output_type": output_type,
            }
        return drive_info

    def _mk_proj_dir(self, proj_dir, run_name):
        """Create project folders and get critical dir.

        Every folder of the run tree is created here, so the later stages can
        write without checking. Existing folders are left alone, which is what
        makes resuming into an existing run folder work.

        Args:
            proj_dir (str): Separator-ending project directory.
            run_name (str): Name of this run, used for the ``Run_...`` folder.

        Returns:
            tuple: A 10-tuple of separator-ending paths, being
            ``(dsn_dir, loc_dsn_dir, loc_script_dir, sim_dir, result_dir,
            report_dir, log_dir, plt_dir, run_key_dir, model_check_dir)``.
        """
        # create Sub-folders
        dsn_dir = proj_dir + "Dsn" + SL
        make_dir(dsn_dir)
        xtract_dir = proj_dir + "Xtract" + SL
        make_dir(xtract_dir)
        # create Sub-subfolders
        make_dir(dsn_dir + "Archive" + SL)
        run_dir = xtract_dir + "Run_" + run_name + SL
        make_dir(run_dir)
        # create Sub-sub-subfolders
        loc_dsn_dir = run_dir + "LocalDsn" + SL
        make_dir(loc_dsn_dir)
        loc_script_dir = run_dir + "LocalScript" + SL
        make_dir(loc_script_dir)
        sim_dir = run_dir + "SimFile" + SL
        make_dir(sim_dir)
        result_dir = run_dir + "Result" + SL
        make_dir(result_dir)
        log_dir = run_dir + "Log" + SL
        make_dir(log_dir)
        report_dir = run_dir + "Report" + SL
        make_dir(report_dir)
        # create Sub-sub-sub-sub-folders
        plt_dir = report_dir + "Plot" + SL
        make_dir(plt_dir)
        run_key_dir = loc_script_dir + "RunKey" + SL
        make_dir(run_key_dir)
        model_check_dir = sim_dir + "ModelCheck" + SL
        make_dir(model_check_dir)

        return (
            dsn_dir,
            loc_dsn_dir,
            loc_script_dir,
            sim_dir,
            result_dir,
            report_dir,
            log_dir,
            plt_dir,
            run_key_dir,
            model_check_dir,
        )

    # ==========================================================================
    # Externally available methods
    # ==========================================================================
    def drop_dsn_file(self, xtract_tool=None):
        """Ask the user to drop the design file in a specific dir.

        Blocks at the terminal until the user confirms the file is in place,
        then looks for design files of an accepted type. Exactly one is used;
        if several are found the user is asked to pick. A local working copy is
        made at the end, so the original is never touched by the solver.

        Args:
            xtract_tool (str, optional): The extraction tool in use. ``.spd``
                is only accepted for ``"Sigrity"``, since an spd is already a
                Sigrity simulation model rather than a raw design.

        Raises:
            NoDsnFound: If the design directory holds no file of an accepted
                type.
            AttributeError: If ``xtract_tool`` is left at ``None``.

        Note:
            The confirmation loop compares against ``("Y" or "YES")``, which
            evaluates to ``"Y"``, so a typed ``yes`` is not accepted and the
            prompt repeats.
        """
        # define variables
        dsn_dir = self.DSN_DIR
        # accepted design file types
        FILE_TYPE = {
            "brd": [".brd"],
            "odb": [".tgz", ".zip", ".gz", ".z", ".tar", ".7z"],
            "mcm": [".mcm"],
        }
        # expand legal file types based on extraction tools
        if xtract_tool.upper() == "SIGRITY":
            FILE_TYPE["spd"] = [".spd"]
        # place design file in the specified location
        self.lg.debug(
            "Please put the design file to be simulated "
            + "in the following directory:\n"
            + dsn_dir
        )
        yorn = "n"
        while yorn.upper() != ("Y" or "YES"):
            yorn = input("Has the board been put in the directory? [y/n]\n")
        # obtain all design files
        all_legal_types = [item for sublist in list(FILE_TYPE.values()) for item in sublist]
        dsn_files = []
        for i_type in all_legal_types:
            tmp = glob.glob(dsn_dir + "*" + i_type)
            dsn_files.extend(tmp)
        # actions when 1, 0, or more than 1 design file is found
        tmp_name = ""
        if len(dsn_files) == 1:
            tmp_name = dsn_files[0].replace(dsn_dir, "")
            self.lg.debug("The following design file is found in " + "the directory:\n" + tmp_name)
        elif len(dsn_files) == 0:
            self.lg.debug("No design file is found in the directory!")
            raise NoDsnFound(self.lg)
        else:
            tmp_names = [item.replace(dsn_dir, "") for item in dsn_files]
            num_list = [str(item) for item in range(1, len(dsn_files) + 1)]
            indexed_names = [
                "[" + num_list[i] + "]" + " " + tmp_names[i] for i in range(len(dsn_files))
            ]
            self.lg.debug(
                "There are more than one design file existing in "
                + "the directory:\n"
                + "\n".join(indexed_names)
                + "\n"
            )
            num = "0"
            while num not in num_list:
                num = input(
                    "Please use ("
                    + ", ".join(num_list)
                    + ") to "
                    + "indicate the board to be simulated!\n"
                )
            self.lg.debug("The user selected design file " + num)
            tmp_name = tmp_names[int(num) - 1]
        self.lg.debug("The following design file is used for simulations:\n" + tmp_name)
        self.DSN_NAME = tmp_name
        if tmp_name.upper().endswith(".SPD"):
            self.LOC_DSN_RAW = rm_ext(tmp_name) + "_raw.spd"
        else:
            self.LOC_DSN_RAW = self.DSN_NAME
        # make a local copy of the design file
        self.__mk_local_dsn_copy()

    def parser(self, input_data):
        """Parse the input data based on the tool in use.

        Works out which simulation keys still need doing, by looking for the
        ``.done`` markers left by earlier runs, and builds the solver executor
        matching the extraction type. Must not be called before the design file
        has been settled by :meth:`drop_dsn_file`.

        Args:
            input_data (dict): The parsed input, normally ``self.input_data``.
                Modified in place, gaining the ``"dcr_dict"``, ``"key2check"``,
                and ``"key2sim"`` keys.

        Returns:
            object: The solver executor, being one of ``PowersiPdnExec``,
            ``ClarityExec``, ``PowersiIOExec``, or ``PowerdcExec``.

        Raises:
            UnboundLocalError: If ``ExtractionTool`` is not ``Sigrity``, or if
                ``ExtractionType`` is not one of the four supported values.
        """
        xtract_tool = input_data["settings"]["EXTRACTIONTOOL"].upper()
        xtract_type = input_data["settings"]["EXTRACTIONTYPE"].upper()
        sim_input = input_data["sim_input"]
        if xtract_type == "DCR":
            dcr_dict, keysall = self.__get_all_dcr_dict(sim_input)
            input_data["dcr_dict"] = dcr_dict
        else:
            keysall = sim_input.keys()
            input_data["dcr_dict"] = {}

        input_data["key2check"] = self.__get_key2sim(self.MODEL_CHECK_DIR, keysall)
        input_data["key2sim"] = self.__get_key2sim(self.SIM_DIR, keysall)

        if xtract_tool == "SIGRITY":
            sim_exec = self.__sigrity_parser(input_data)
        return sim_exec

    def run(self, sim_exec, mntr_info):
        """Run sims and return the result info.

        Delegates to the executor, which generates the scripts, builds and
        checks the models, runs the solver, and collects the results. This is
        the long-running step of a flow.

        Args:
            sim_exec (object): The executor returned by :meth:`parser`.
            mntr_info (dict): Monitor related information.

                * ``email`` (str): Notification address. Not enabled yet.
                * ``op_pause_after_model_check`` (int, optional): ``1`` to
                  pause after model check, ``0`` to run straight through.

        Returns:
            tuple: A 2-tuple ``(result_config_dir, report_config_dir)``, the
            full paths of the two yaml files handing state to the report stage.
        """
        result_config_dir, report_config_dir = sim_exec.run(mntr_info)
        return result_config_dir, report_config_dir

    def process_snp(self, result_config_dir):
        """Post-process results and generate plots.

        Every touchstone file named by the result config is processed according
        to its simulation's spec type, writing the figures into the run's
        ``Plot`` folder.

        Args:
            result_config_dir (str): Full path to the result configuration
                file written by :meth:`run`.

        Returns:
            dict: Result sub-folder name to a dict of simulation key to that
            simulation's post-processing output. See
            ``opensipi.touchstone.TouchStone.auto_process``.
        """
        result_config = load_yaml_to_dict(expand_home_dir(result_config_dir))
        result_dict = {}
        for key in result_config["result_sub_dirs"].keys():
            result_dict[key] = self.__snp_plot_xtract(key, result_config)
        return result_dict

    def report(self, result_config_dir, report_config_dir):
        """Generate a report out of the processed results.

        Post-processes the results, then fills the pdf template matching the
        report type recorded in the report config.

        Args:
            result_config_dir (str): Full path to the result configuration
                file.
            report_config_dir (str): Full path to the report configuration
                file.

        Returns:
            str: Full path of the pdf report written.

        Note:
            A ``DCR`` report type produces no report. Both branches for it are
            still placeholders, so the path is logged and returned without a
            file having been written.
        """
        # load report config file
        report_config = load_yaml_to_dict(expand_home_dir(report_config_dir))
        # pdf template selection based on report type
        report_type = report_config["report_type"]

        # snp figures
        if report_type in ["PDN", "IO"]:
            result_dict = self.process_snp(expand_home_dir(result_config_dir))
        elif report_type in ["DCR"]:
            pass

        # summary
        summary_list = [
            ["Simulation Start Time", report_config["sim_date"]],
            ["Author", report_config["usr_id"]],
            ["Project Name", report_config["proj_name"]],
            ["Extraction Tool", report_config["xtract_tool"]],
            ["Extraction Type", report_config["xtract_type"]],
            ["Design File", report_config["dsn_name"]],
        ]

        dir = expand_home_dir(report_config["report_full_path"])
        if report_type == "PDN":
            self.__gen_pdn_report(pdn_report, summary_list, result_dict, dir)
        elif report_type == "IO":
            self.__gen_io_report(io_report, summary_list, result_dict, dir)
        elif report_type == "DCR":
            pass  # pending to include DCR report
        self.lg.debug("A summary report is created at " + dir)
        return dir

    def report_html(self, result_config_dir, report_config_dir):
        """Generate a HTML report out of the processed results.

        The html alternative to :meth:`report`. It renders a jinja2 template
        into html and then converts that to pdf, so both formats end up in the
        run's ``Report`` folder. Requires ``wkhtmltopdf`` to be installed for
        the conversion.

        Args:
            result_config_dir (str): Full path to the result configuration
                file.
            report_config_dir (str): Full path to the report configuration
                file.

        Returns:
            str: Full path of the pdf report written. The html sits beside it
            under the same name.

        Note:
            The integrated flows call :meth:`report` rather than this method,
            so the html path is only taken when a caller asks for it directly.
        """
        # load report config file
        report_config = load_yaml_to_dict(expand_home_dir(report_config_dir))
        # pdf template selection based on report type
        report_type = report_config["report_type"]

        # snp figures
        if report_type in ["PDN", "IO"]:
            result_dict = self.process_snp(expand_home_dir(result_config_dir))
        elif report_type in ["DCR"]:
            pass

        # summary
        summary_list = [
            ["Simulation Start Time", report_config["sim_date"]],
            ["Author", report_config["usr_id"]],
            ["Project Name", report_config["proj_name"]],
            ["Extraction Tool", report_config["xtract_tool"]],
            ["Extraction Type", report_config["xtract_type"]],
            ["Design File", report_config["dsn_name"]],
        ]

        # misc parts for the report
        misc_dict = {
            "company_logo": img2str(report_config["logoimg_dir"]),
        }

        pdf_dir = expand_home_dir(report_config["report_full_path"])
        html_dir = pdf_dir.replace(".pdf", ".html")
        if report_type == "PDN":
            self.__gen_pdn_html_report(summary_list, result_dict, misc_dict, html_dir)
        elif report_type == "IO":
            self.__gen_io_html_report(summary_list, result_dict, misc_dict, html_dir)
        elif report_type == "DCR":
            pass  # pending to include DCR report
        self.convert_html_to_pdf_report(html_dir, pdf_dir)
        self.lg.debug("A summary report is created at " + pdf_dir)
        return pdf_dir

    def export_upload_config(self, report_config_dir):
        """Export the upload config file.

        Folds the output settings together with the run details taken from the
        report config into one yaml file, so the upload stage needs nothing but
        that file.

        Args:
            report_config_dir (str): Full path to the report configuration
                file.

        Returns:
            str: Full path of the upload configuration file written into the
            run's ``Report`` folder.
        """
        report_config = load_yaml_to_dict(report_config_dir)
        upload_config = self.fileout_info
        upload_config["proj_name"] = report_config["proj_name"]
        upload_config["xtract_type"] = report_config["xtract_type"]
        upload_config["sim_type_name"] = "Xtract"
        upload_config["run_time"] = report_config["sim_date"]
        upload_config["usr_id"] = report_config["usr_id"]
        upload_config["design_type"] = report_config["design_type"]
        upload_config["report_full_path"] = expand_home_dir(report_config["report_full_path"])
        upload_config["report_dir"] = expand_home_dir(report_config["report_dir"])
        upload_config["result_dir"] = expand_home_dir(report_config["result_dir"])
        upload_config["tool_config_dir"] = self.TOOL_CONFIG_DIR
        upload_config_dir = self.REPORT_DIR + "upload_config.yaml"
        export_dict_to_yaml(upload_config, upload_config_dir)
        return upload_config_dir

    def upload2drive(self, upload_config_dir):
        """Upload results and reports to online storage based on the config file.

        Args:
            upload_config_dir (str): Full path to the upload configuration
                file written by :meth:`export_upload_config`.

        Note:
            Only ``gdrive`` is implemented. Any other ``output_type``,
            including the default ``local``, is a no-op.
        """
        upload_config = load_yaml_to_dict(upload_config_dir)
        output_type = upload_config["output_type"]
        if output_type.upper() == "GDRIVE":
            self.__upload2gdrive(upload_config)
        else:
            pass

    # ==========================================================================
    # parser() related methods
    # ==========================================================================

    def __sigrity_parser(self, input_data):
        """Build the Sigrity executor for this extraction.

        Parses the input data into the format of simulations running in Cadence
        Sigrity tools. Everything the executor needs, being the parsed input,
        the run folder paths, and the logger, is gathered into one
        ``model_info`` dict, and the extraction type then selects which
        executor class receives it.

        Args:
            input_data (dict): The parsed input, already carrying the
                ``"key2check"`` and ``"key2sim"`` keys.

        Returns:
            object: ``PowersiPdnExec`` for PDN, ``ClarityExec`` for HSIO,
            ``PowersiIOExec`` for LSIO, or ``PowerdcExec`` for DCR.

        Raises:
            UnboundLocalError: If the extraction type is none of those four.
        """
        model_info = {
            "stackup_info": input_data["stackup_info"],
            "settings": input_data["settings"],
            "spectype_info": input_data["spectype_info"],
            "sim_input": input_data["sim_input"],
            "all_input": input_data["all_input"],
            "key2check": input_data["key2check"],
            "key2sim": input_data["key2sim"],
            "dcr_dict": input_data["dcr_dict"],
            "run_name": self.RUN_NAME,
            "tool_config_dir": self.TOOL_CONFIG_DIR,
            "dsn_dir": self.DSN_DIR,
            "dsn_name": self.DSN_NAME,
            "loc_dsn_raw": self.LOC_DSN_RAW,
            "loc_dsn_dir": self.LOC_DSN_DIR,
            "loc_script_dir": self.LOC_SCRIPT_DIR,
            "sim_dir": self.SIM_DIR,
            "result_dir": self.RESULT_DIR,
            "plot_dir": self.PLT_DIR,
            "report_dir": self.REPORT_DIR,
            "template_dir": self.TEMPLATE_DIR,
            "run_key_dir": self.RUN_KEY_DIR,
            "model_check_dir": self.MODEL_CHECK_DIR,
            "log": self.lg,
        }
        xtract_type = input_data["settings"]["EXTRACTIONTYPE"].upper()
        # switch solver based on extraction type
        if xtract_type == "PDN":
            sig_exec = PowersiPdnExec(model_info)
        elif xtract_type == "HSIO":
            sig_exec = ClarityExec(model_info)
        elif xtract_type == "LSIO":
            sig_exec = PowersiIOExec(model_info)
        elif xtract_type == "DCR":
            sig_exec = PowerdcExec(model_info)
        return sig_exec

    def __get_key2sim(self, run_dir, keys_all):
        """Get the run key to be simulated.

        A finished simulation leaves a ``.done`` marker in its folder, so the
        keys still to do are whatever has no marker yet. This is what lets an
        interrupted run be resumed without redoing the finished simulations.

        Args:
            run_dir (str): Folder to look for the ``.done`` markers in.
            keys_all (iterable of str): Every simulation key of this run.

        Returns:
            list of str: The keys with no ``.done`` marker.
        """
        # keys already done
        done_dir = glob.glob(run_dir + "*.done")
        keys_done = [item.replace(run_dir, "").replace(".done", "") for item in done_dir]
        # remained keys to be run
        key2sim = [item for item in keys_all if item not in keys_done]
        self.lg.debug("The following keys are detected to be run:\n" + "\n".join(key2sim))
        return key2sim

    def __get_all_dcr_dict(self, sim_input):
        """Group the DCR simulation keys by their sheet.

        A DCR extraction is run once per sheet rather than once per simulation
        key, since all the sinks of a sheet share one solver setup, so the keys
        are grouped by the sheet prefix they carry.

        Args:
            sim_input (dict): The enabled simulations, keyed
                ``"[SHEET]_[Unique_Key]"``.

        Returns:
            tuple: A 2-tuple ``(keys_dict, keys_all)``, mapping each sheet
            prefix to its simulation keys, and listing the distinct sheet
            prefixes.

        Note:
            The grouping matches with ``in`` rather than by prefix, so a sheet
            name that is a substring of another also collects the other's keys.
        """
        keys_tmp = [i_key.split("_")[0] for i_key in sim_input]
        keys_all = unique_list(keys_tmp)
        keys_dict = {}
        for i_key in keys_all:
            keys_dict[i_key] = [tmp for tmp in sim_input if i_key in tmp]
        return keys_dict, keys_all

    # ==========================================================================
    # drop_dsn_file() related methods
    # ==========================================================================
    def __mk_local_dsn_copy(self):
        """Make a local copy of the design file.

        The solver works on this copy, so the dropped original is left
        untouched. An existing copy is kept as it is, which is what lets a
        resumed run reuse a model that was already built or hand-edited.
        """
        loc_dsn = self.LOC_DSN_DIR + self.LOC_DSN_RAW
        if not os.path.exists(loc_dsn):
            shutil.copyfile(self.DSN_DIR + self.DSN_NAME, loc_dsn)
            self.lg.debug("A local copy of the design file is made.")
        else:
            self.lg.debug("A local copy of the design file already exists. No action is taken.")

    # ==========================================================================
    # process_snp() related methods
    # ==========================================================================
    def __snp_plot_xtract(self, key, result_config):
        """Post-process every touchstone file of one result sub-folder.

        Args:
            key (str): Result sub-folder name, e.g. ``"SNP_S"``.
            result_config (dict): The loaded result configuration.

        Returns:
            dict: Simulation key to that simulation's post-processing output.
        """
        plt_list = self._get_plt_list(key, result_config)
        ts_list = TouchStone.from_list(plt_list)
        output_dict = {}
        for ts in ts_list:
            output_dict[ts.key_name] = ts.auto_process()
        return output_dict

    def _get_plt_list(self, key, result_config):
        """Get the plot list out of a given directory.

        Scans a result sub-folder for touchstone files and builds one
        ``TouchStone`` info dict per file. The simulation key is recovered from
        the file name, being the part before the double underscore, and files
        whose key was not enabled in the input are skipped, so results left
        over from an earlier run do not leak into this report.

        Args:
            key (str): Result sub-folder name, e.g. ``"SNP_S"``.
            result_config (dict): The loaded result configuration.

        Returns:
            list of dict: One info dict per file to process, ready to be passed
            to ``opensipi.touchstone.TouchStone``.
        """
        plt_list = []
        snp_dir = expand_home_dir(result_config["result_sub_dirs"][key])
        plot_dir = expand_home_dir(result_config["plot_dir"])
        checked_keys = result_config["checked_keys"]
        spectype = result_config["spectype"]
        conn = result_config["CONNECTIVITY"]
        snp_list = glob.glob(snp_dir + "*.[sS]*[pP]")
        for i_snp in snp_list:
            file_dir = i_snp
            snp_name = i_snp.replace(snp_dir, "")
            sim_key = snp_name[: snp_name.index("__")]
            if sim_key in checked_keys:
                spec_type = spectype[sim_key]
                temp_dict = {
                    "file_dir": file_dir,
                    "key_name": key + "__" + sim_key,
                    "plt_dir": plot_dir,
                    "spec_type": spec_type,
                    "snp_name": snp_name,
                    "conn_dict": conn[sim_key],
                }
                plt_list.append(temp_dict)
                self.lg.debug(snp_name + " is included for plotting!")
            else:
                self.lg.debug(snp_name + " is skipped since it is not queried!")
        return plt_list

    # ==========================================================================
    # report() related methods
    # ==========================================================================
    def __gen_pdn_report(self, pdf_report, summary_list, result_dict, dir):
        """Generate a PDF report for PDN.

        Extends the template in place: the summary rows go into section 0, one
        result row per figure into the section 1 table matching that
        post-processing key, and the figures themselves into section 2. The
        table cells cross-reference the figures by number.

        Args:
            pdf_report (dict): The ``pdn_report`` template. Modified in place,
                so a second call in the same process appends to the first
                call's content.
            summary_list (list of list of str): Run summary rows.
            result_dict (dict): The output of :meth:`process_snp`.
            dir (str): Full path of the pdf to write.
        """
        pdf_report["sections"][0]["content"][0]["table"].extend(summary_list)
        # table and figures
        i = 1
        for snp_folder, all_key_names in result_dict.items():
            for key_name, all_results in all_key_names.items():
                for process_key, result in all_results.items():
                    index_mod = POST_PROCESS_KEY_ORDER_PDN[process_key]
                    for i_list in result:
                        # table
                        pdf_report["sections"][1]["content"][index_mod]["table"].append(
                            [
                                i_list[0],
                                i_list[2],
                                i_list[3],
                                i_list[4],
                                {".": "Fig." + str(i), "style": "url", "ref": i_list[0]},
                            ]
                        )
                        # figures
                        image_dict = {
                            "group": [
                                {".": "Fig." + str(i) + " " + i_list[0], "label": i_list[0]},
                                {
                                    "image": i_list[1],
                                    "min_height": 100,
                                    "style": {"margin_left": 50, "margin_right": 50},
                                },
                            ]
                        }
                        pdf_report["sections"][2]["content"].append(image_dict)
                        i += 1
        with open(dir, "wb") as f:
            build_pdf(pdf_report, f)

    def __gen_io_report(self, pdf_report, summary_list, result_dict, dir):
        """Generate a PDF report for IO.

        The IO counterpart of :meth:`__gen_pdn_report`. The mixed-mode keys
        carry one more level of nesting, being a dict of mode to results, so
        they are unpacked separately from the single-ended ones.

        Args:
            pdf_report (dict): The ``io_report`` template. Modified in place.
            summary_list (list of list of str): Run summary rows.
            result_dict (dict): The output of :meth:`process_snp`.
            dir (str): Full path of the pdf to write.
        """
        pdf_report["sections"][0]["content"][0]["table"].extend(summary_list)
        # table and figures
        i = 1
        for snp_folder, all_key_names in result_dict.items():
            for key_name, all_results in all_key_names.items():
                for process_key, result in all_results.items():
                    index_mod = POST_PROCESS_KEY_ORDER_IO[process_key]
                    if process_key in ["IL", "RL", "TDR"]:
                        for i_list in result:
                            # table
                            ctnt_dict = {".": "Fig." + str(i), "style": "url", "ref": i_list[0]}
                            pdf_report["sections"][1]["content"][index_mod]["table"].append(
                                [i_list[0], "", ctnt_dict]
                            )
                            # figures
                            image_dict = {
                                "group": [
                                    {".": "Fig." + str(i) + " " + i_list[0], "label": i_list[0]},
                                    {
                                        "image": i_list[1],
                                        "min_height": 100,
                                        "style": {"margin_left": 50, "margin_right": 50},
                                    },
                                ]
                            }
                            pdf_report["sections"][2]["content"].append(image_dict)
                            i += 1
                    elif process_key in ["IL_MM", "RL_MM", "TDR_MM"]:
                        for mm_type, mm_result in result.items():
                            for i_list in mm_result:
                                # table
                                ctnt_dict = {".": "Fig." + str(i), "style": "url", "ref": i_list[0]}
                                pdf_report["sections"][1]["content"][index_mod]["table"].append(
                                    [i_list[0], "", ctnt_dict]
                                )
                                # figures
                                image_dict = {
                                    "group": [
                                        {
                                            ".": "Fig." + str(i) + " " + i_list[0],
                                            "label": i_list[0],
                                        },
                                        {
                                            "image": i_list[1],
                                            "min_height": 100,
                                            "style": {"margin_left": 50, "margin_right": 50},
                                        },
                                    ]
                                }
                                pdf_report["sections"][2]["content"].append(image_dict)
                                i += 1
        with open(dir, "wb") as f:
            build_pdf(pdf_report, f)

    def __gen_pdn_html_report(
        self, summary_list, result_dict, misc_dict, dir, pdn_report_temp="PDN_Type1.html"
    ):
        """Generate a HTML report for PDN.

        Args:
            summary_list (list of list of str): Run summary rows.
            result_dict (dict): The output of :meth:`process_snp`.
            misc_dict (dict): Extra content, holding ``"company_logo"`` as a
                base64 string so the logo is embedded rather than linked.
            dir (str): Full path of the html to write.
            pdn_report_temp (str, optional): Template file name inside the
                package's ``templates/reports`` folder. Defaults to
                ``"PDN_Type1.html"``.
        """
        # prepare result list
        # result_list = []
        # for item in output_list:
        #     img_str = img2str(item[1])
        #     temp = [item[0], item[2], item[3], item[4], img_str]
        #     result_list.append(temp)
        report_dict = {
            "summary_list": summary_list,
            "logo_img": misc_dict["company_logo"],
            "result_dict": result_dict,
        }
        template = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.TEMPLATE_DIR + "reports" + SL),
            autoescape=jinja2.select_autoescape,
        ).get_template(pdn_report_temp)
        report_ctnt = template.render(report_dict)
        with open(dir, "w") as f:
            f.write(report_ctnt)

    def __gen_io_html_report(
        self, summary_list, result_dict, misc_dict, dir, io_report_temp="IO_Type1.html"
    ):
        """Generate a HTML report for IO.

        Args:
            summary_list (list of list of str): Run summary rows.
            result_dict (dict): The output of :meth:`process_snp`.
            misc_dict (dict): Extra content, holding ``"company_logo"`` as a
                base64 string.
            dir (str): Full path of the html to write.
            io_report_temp (str, optional): Template file name inside the
                package's ``templates/reports`` folder. Defaults to
                ``"IO_Type1.html"``.
        """
        # prepare result list
        report_dict = {
            "summary_list": summary_list,
            "logo_img": misc_dict["company_logo"],
            "result_dict": result_dict,
        }
        template = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.TEMPLATE_DIR + "reports" + SL),
            autoescape=jinja2.select_autoescape,
        ).get_template(io_report_temp)
        report_ctnt = template.render(report_dict)
        with open(dir, "w") as f:
            f.write(report_ctnt)

    def convert_html_to_pdf_report(self, html_dir, pdf_dir):
        """Convert a html report to a pdf report.

        Local file access is enabled so the embedded figures resolve.

        Args:
            html_dir (str): Full path of the html to read.
            pdf_dir (str): Full path of the pdf to write.

        Raises:
            OSError: If the ``wkhtmltopdf`` binary that ``pdfkit`` drives is
                not installed.
        """
        options = {"page-size": "A4", "enable-local-file-access": True}
        with open(html_dir) as f:
            pdfkit.from_file(f, pdf_dir, options=options)

    # ==========================================================================
    # upload2drive() related methods
    # ==========================================================================

    def __upload2gdrive(self, upload_config):
        """Upload results and reports to Google drive based on the config file.

        Mirrors the run's results and report into Drive, then writes a row per
        simulation into a per-project summary sheet, so the sheet accumulates
        across runs. What gets uploaded depends on the extraction type: the
        S-parameter types upload the touchstone files and the pdf report, while
        DCR uploads nothing and only writes its resistance values into the
        sheet.

        Args:
            upload_config (dict): The loaded upload configuration.
        """

        proj_name = upload_config["proj_name"]
        xtract_type = upload_config["xtract_type"]
        usr_id = upload_config["usr_id"]
        run_time = upload_config["run_time"]
        account_key = upload_config["account_key"]
        report_full_path = upload_config["report_full_path"]
        drive_info = {
            "account_key": account_key,
            "usr_id": usr_id,
            "config_dir": upload_config["tool_config_dir"],
            "root_drive_id": upload_config["root_drive_id"],
            "proj_name": proj_name,
            "sim_type_name": upload_config["sim_type_name"],
            "run_time": run_time,
            "log": self.lg,
        }
        drive_proj = XtractResults2Drive(drive_info)
        summary_sheet_title = (
            proj_name
            + "_"
            + upload_config["design_type"]
            + "_xtract"
            + xtract_type
            + "_Results_Summary"
        )
        summary_sheet_id = drive_proj.get_summary_sheet_id(
            summary_sheet_title, upload_config["out_sheet_gdrive_id"]
        )
        # report
        if xtract_type in ["PDN", "HSIO", "LSIO"]:
            # upload results to Gdrive
            file_id_book, uni_file_type = drive_proj.upload_folder_tgt_ext(
                upload_config["result_dir"], r".[sS]\d+[pP]$"
            )
            report_id_book = drive_proj.upload_report(report_full_path)
            # Update the output gSheet
            out_gsheet_info = {
                "account_key": account_key,
                "sheet_id": summary_sheet_id,
                "file_id_book": file_id_book,
                "uni_file_type": uni_file_type,
                "report_id_book": report_id_book,
                "run_time": run_time,
                "usr_id": usr_id,
                "log": self.lg,
            }
            out_gsheet_proj = TS2GSheet(out_gsheet_info)
            out_gsheet_proj.export_results()
        elif xtract_type in ["DCR"]:
            # Update the output gSheet
            dcr_dict_tmp, _ = csv2dict(report_full_path)
            dcr_dict = {}
            for key, val in dcr_dict_tmp.items():
                dcr_dict[key] = val[0][1]
            out_gsheet_info = {
                "account_key": account_key,
                "sheet_id": summary_sheet_id,
                "dcr_dict": dcr_dict,
                "run_time": run_time,
                "usr_id": usr_id,
                "log": self.lg,
            }
            out_gsheet_proj = DCR2GSheet(out_gsheet_info)
            out_gsheet_proj.export_results()
