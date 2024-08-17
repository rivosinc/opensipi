# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
Author: yanshengw@
Last updated on Nov. 20, 2023

Description:
    This module serves as the platform of the OpenSIPI application.
"""


import glob
import os
import shutil

import jinja2
from pdfme import build_pdf

from opensipi import __version__
from opensipi.constants.CONSTANTS import INPUT_FILE_STARTSWITH
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
    slash_ending,
    unique_list,
)
from opensipi.util.exceptions import NoDsnFound, NoProjDirDefined
from opensipi.util.logs import setup_logger


class Platform:
    """platform class for the opensipi applications."""

    def __init__(self, info):
        self.INPUT_TYPE = info["input_type"].upper()
        # module internal dir
        self.INSTALL_ROOT_DIR, self.SCRIPTS_DIR, self.TEMPLATE_DIR = get_dir()
        self.TOOL_CONFIG_DIR = get_root_dir() + "opensipi_config" + SL
        make_dir(self.TOOL_CONFIG_DIR)
        # get run name through run time
        if "op_run_name" not in info:
            self.RUN_NAME = get_run_time()
        elif info["op_run_name"] == "":
            self.RUN_NAME = get_run_time()
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
        # file I/O info
        self.filein_info = self._get_filein_info(info)
        self.fileout_info = self._get_fileout_info(info)
        # Class properties that will be assigned after running certain methods
        self.DSN_NAME = ""

    # ==========================================================================
    # Class initialization related method
    # ==========================================================================
    def _get_proj_dir(self, info):
        """get the project directory."""
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
        """get the dict used to query input data."""
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
                "account_key": gsuites_config["ACCOUNT_KEY_DIR"],
                "account_type": gsuites_config["ACCOUNT_TYPE"],
                "sheet_url": info["input_url"],
                "input_file_startswith": INPUT_FILE_STARTSWITH,
            }
        return input_info

    def _get_fileout_info(self, info):
        """get the dict used to store output data."""
        if "output_type" in info:
            output_type = info["output_type"]
        else:
            output_type = "local"

        if output_type.upper() == "GDRIVE":
            gsuites_config = load_yaml_to_dict(self.TOOL_CONFIG_DIR + "config_gsuites.yaml")
            drive_info = {
                "output_type": output_type,
                "account_key": gsuites_config["ACCOUNT_KEY_DIR"],
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
        """create project folders and get critical dir"""
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
    def read_inputs(self):
        """read input data based on input_type"""
        input_data = FileIn(self.filein_info).INPUT_DATA
        return input_data

    def drop_dsn_file(self):
        """ask the user to drop the design file in a specific dir"""
        # define variables
        dsn_dir = self.DSN_DIR
        # accepted design file types
        FILE_TYPE = {
            "brd": [".brd"],
            "odb": [".tgz", ".zip", ".gz", ".z", ".tar", ".7z"],
            "mcm": [".mcm"],
        }
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
        # make a local copy of the design file
        self.__mk_local_dsn_copy()

    def parser(self, input_data):
        """Parse the input data based on the tool in use."""
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
        """Run sims and return the result info."""
        result_config_dir, report_config_dir = sim_exec.run(mntr_info)
        return result_config_dir, report_config_dir

    def process_snp(self, result_config_dir):
        """Post-process results and generate plots."""
        result_config = load_yaml_to_dict(expand_home_dir(result_config_dir))
        result_dict = {}
        for key in result_config["result_sub_dirs"].keys():
            result_dict[key] = self.__snp_plot_xtract(key, result_config)
        return result_dict

    def report(self, result_config_dir, report_config_dir):
        """Generate a report out of the processed results."""
        # load report config file
        report_config = load_yaml_to_dict(expand_home_dir(report_config_dir))
        # pdf template selection based on report type
        report_type = report_config["report_type"]

        # snp figures
        output_list = []
        if report_type in ["PDN", "IO"]:
            result_dict = self.process_snp(expand_home_dir(result_config_dir))
            for key, val in result_dict.items():
                output_list.extend(val)
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
            self.__gen_pdn_report(pdn_report, summary_list, output_list, dir)
        elif report_type == "IO":
            self.__gen_io_report(io_report, summary_list, output_list, dir)
        elif report_type == "DCR":
            pass  # pending to include DCR report
        self.lg.debug("A summary report is created at " + dir)
        return dir

    def report_html(self, result_config_dir, report_config_dir):
        """Generate a HTML report out of the processed results."""
        # load report config file
        report_config = load_yaml_to_dict(expand_home_dir(report_config_dir))
        # pdf template selection based on report type
        report_type = report_config["report_type"]

        # snp figures
        output_list = []
        if report_type in ["PDN", "IO"]:
            result_dict = self.process_snp(expand_home_dir(result_config_dir))
            for key, val in result_dict.items():
                output_list.extend(val)
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

        dir = expand_home_dir(report_config["report_full_path"])
        dir = dir.replace(".pdf", ".html")
        if report_type == "PDN":
            self.__gen_pdn_html_report(summary_list, output_list, misc_dict, dir)
        elif report_type == "IO":
            pass
        elif report_type == "DCR":
            pass  # pending to include DCR report
        self.lg.debug("A summary report is created at " + dir)
        return dir

    def export_upload_config(self, report_config_dir):
        """export the upload config file."""
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
        """upload results and reports to online storage based on the
        config file
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
        """Parse the input data into the format of simulations running
        in Cadence Sigrity tools.
        """
        model_info = {
            "stackup_info": input_data["stackup_info"],
            "settings": input_data["settings"],
            "sim_input": input_data["sim_input"],
            "all_input": input_data["all_input"],
            "key2check": input_data["key2check"],
            "key2sim": input_data["key2sim"],
            "dcr_dict": input_data["dcr_dict"],
            "run_name": self.RUN_NAME,
            "tool_config_dir": self.TOOL_CONFIG_DIR,
            "dsn_dir": self.DSN_DIR,
            "dsn_name": self.DSN_NAME,
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
        """get the run key to be simulated"""
        # keys already done
        done_dir = glob.glob(run_dir + "*.done")
        keys_done = [item.replace(run_dir, "").replace(".done", "") for item in done_dir]
        # remained keys to be run
        key2sim = [item for item in keys_all if item not in keys_done]
        self.lg.debug("The following keys are detected to be run:\n" + "\n".join(key2sim))
        return key2sim

    def __get_all_dcr_dict(self, sim_input):
        """Get all workbook names before ."""
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
        """make a local copy of the design file"""
        if not os.path.exists(self.LOC_DSN_DIR + self.DSN_NAME):
            shutil.copyfile(self.DSN_DIR + self.DSN_NAME, self.LOC_DSN_DIR + self.DSN_NAME)
            self.lg.debug("A local copy of the design file is made.")
        else:
            self.lg.debug(
                "A local copy of the design file already " + "exists. No action is taken."
            )

    # ==========================================================================
    # process_snp() related methods
    # ==========================================================================
    def __snp_plot_xtract(self, key, result_config):
        """"""
        plt_list = self._get_plt_list(key, result_config)
        ts_list = TouchStone.from_list(plt_list)
        output_list = []
        for ts in ts_list:
            output_list.extend(ts.auto_plot())
        return output_list

    def _get_plt_list(self, key, result_config):
        """Get the plot list out of a given directory."""
        plt_list = []
        snp_dir = expand_home_dir(result_config["result_sub_dirs"][key])
        plot_dir = expand_home_dir(result_config["plot_dir"])
        checked_keys = result_config["checked_keys"]
        spectype = result_config["spectype"]
        conn = result_config["CONNECTIVITY"]
        snp_list = glob.glob(snp_dir + "*.s*p")
        for i_snp in snp_list:
            file_dir = i_snp
            snp_name = i_snp.replace(snp_dir, "")
            key_name = snp_name[: snp_name.index("__")]
            if key_name in checked_keys:
                spec_type = spectype[key_name]
                temp_dict = {
                    "file_dir": file_dir,
                    "key_name": key + "__" + key_name,
                    "plt_dir": plot_dir,
                    "spec_type": spec_type,
                    "snp_name": snp_name,
                    "conn_dict": conn[key_name],
                }
                plt_list.append(temp_dict)
                self.lg.debug(snp_name + " is included for plotting!")
            else:
                self.lg.debug(snp_name + " is skipped since it is not queried!")
        return plt_list

    # ==========================================================================
    # report() related methods
    # ==========================================================================
    def __gen_pdn_report(self, pdf_report, summary_list, output_list, dir):
        """Generate a PDF report for PDN."""
        pdf_report["sections"][0]["content"][0]["table"].extend(summary_list)
        # table and figures
        i = 1
        for i_list in output_list:
            # table
            pdf_report["sections"][1]["content"][0]["table"].append(
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

    def __gen_io_report(self, pdf_report, summary_list, output_list, dir):
        """Generate a PDF report for IO."""
        pdf_report["sections"][0]["content"][0]["table"].extend(summary_list)
        # table and figures
        i = 1
        ctnt_index = 0
        for sub_list in output_list:
            for i_list in sub_list:
                # table
                index_mod = ctnt_index % 2
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
            ctnt_index += 1
        with open(dir, "wb") as f:
            build_pdf(pdf_report, f)

    def __gen_pdn_html_report(
        self, summary_list, output_list, misc_dict, dir, pdn_report_temp="PDN_Type1.html"
    ):
        """Generate a HTML report for PDN."""
        # prepare result list
        result_list = []
        for item in output_list:
            img_str = img2str(item[1])
            temp = [item[0], item[2], item[3], item[4], img_str]
            result_list.append(temp)
        report_dict = {
            "summary_list": summary_list,
            "logo_img": misc_dict["company_logo"],
            "result_list": result_list,
        }
        template = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.TEMPLATE_DIR + "reports" + SL),
            autoescape=jinja2.select_autoescape,
        ).get_template(pdn_report_temp)
        report_ctnt = template.render(report_dict)
        with open(dir, "w") as f:
            f.write(report_ctnt)

    # ==========================================================================
    # upload2drive() related methods
    # ==========================================================================

    def __upload2gdrive(self, upload_config):
        """upload results and reports to Google drive based on the
        config file
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
