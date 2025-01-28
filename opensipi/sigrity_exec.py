# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
Author: yanshengw@
Last updated on Jul. 29, 2024

Description:
    This module contains all Classes used to execute Cadence Sigrity Tools.
"""


import math
import os
import re
import shutil
from time import perf_counter, sleep

import psutil

from opensipi.constants.CONSTANTS import SIM_INPUT_COL_TITLE
from opensipi.sigrity_tools import (
    ClarityModeler,
    PowerdcModeler,
    PowersiIOModeler,
    PowersiPdnModeler,
)
from opensipi.util.common import (
    SL,
    csv2dict,
    expand_home_dir,
    export_dict_to_yaml,
    list_strip,
    load_yaml_to_dict,
    make_dir,
    rm_list_item,
    slash_ending,
    striped_str2list,
    txtfile_rd,
    txtfile_wr,
    unique_list,
)
from opensipi.util.exceptions import (
    IllegalInputFormat,
    NoExistingNames,
    UnequalPortCounts,
)


class PowersiPdnExec:
    """This class parses input info as executable tcl scripts, launches
    simulations, conducts formality checks and etc. This class is only
    for PDN extractions using PowerSI.
    """

    def __init__(self, info):
        self.UNIKEY = SIM_INPUT_COL_TITLE[0]
        self.CKBOX = SIM_INPUT_COL_TITLE[1]
        self.SPECTYPE = SIM_INPUT_COL_TITLE[2]
        self.POSNET = SIM_INPUT_COL_TITLE[3]
        self.NEGNET = SIM_INPUT_COL_TITLE[4]
        self.POSMP = SIM_INPUT_COL_TITLE[5]
        self.NEGMP = SIM_INPUT_COL_TITLE[6]
        self.POSAP = SIM_INPUT_COL_TITLE[7]
        self.NEGAP = SIM_INPUT_COL_TITLE[8]

        FOLDER_SNP_S = "SNP_S" + SL
        FOLDER_SNP_DCFITTED = "SNP_DCfitted" + SL
        FOLDER_SNP_DC = "SNP_DC" + SL

        self.proj_name = info["settings"]["PROJECTNAME"]
        self.xtract_tool = info["settings"]["EXTRACTIONTOOL"]
        self.tool_config_dir = info["tool_config_dir"]
        self.sim_dir = info["sim_dir"]
        self.result_dir = info["result_dir"]
        self.plot_dir = info["plot_dir"]
        self.report_dir = info["report_dir"]
        self.sim_input = info["sim_input"]
        self.all_input = info["all_input"]
        self.lg = info["log"].getChild("/" + __name__)
        # FOLDER_BBS_S = 'BBS_S'+SL
        # FOLDER_BBS_DCFITTED = 'BBS_DCfitted'+SL
        # FOLDER_IDEM_S_HSPICE = 'IDEM_S_HSPICE'+SL
        # FOLDER_IDEM_S_MODH5 = '_IDEM_S_MODH5'+SL
        self.snp_s_dir = self.result_dir + FOLDER_SNP_S
        self.snp_dcfitted_dir = self.result_dir + FOLDER_SNP_DCFITTED
        self.snp_dc_dir = self.result_dir + FOLDER_SNP_DC
        # self.bbs_s_dir = self.result_dir+FOLDER_BBS_S
        # self.bbs_dcfitted_dir = self.result_dir+FOLDER_BBS_DCFITTED
        # self.idem_s_hspice_dir = self.result_dir+FOLDER_IDEM_S_HSPICE
        # self.idem_s_modh5_dir = self.sim_dir+FOLDER_IDEM_S_MODH5
        self.result_sub_dirs = {
            "snp_s_dir": self.snp_s_dir,
            "snp_dcfitted_dir": self.snp_dcfitted_dir,
        }
        self.report_type = "PDN"
        # prepare net and component names in the input sheet
        self.__get_net_comp_names_from_sheet()
        self.spd_proj = self._get_spd_proj(info)
        self.run_info = self.__get_run_info()

    # ==========================================================================
    # Class initialization related method
    # ==========================================================================
    def _get_spd_proj(self, info):
        """initialize spd proj"""
        inst = PowersiPdnModeler(info)
        inst.mk_tcl()
        return inst

    def __get_net_comp_names_from_sheet(self):
        """prepare net and component names in the gSheet."""
        input = self.sim_input
        input_key = list(input.keys())
        nets_pos_all = []
        nets_neg_all = []
        main_comp_pos_all = []
        main_comp_neg_all = []
        sns_comp_pos_all = []
        sns_comp_neg_all = []
        self._port_count_defined = {}
        for i_key in input_key:
            port_count_tmp = 0
            for i_row in input[i_key]:
                # merge nets in all rows
                nets_pos_tmp = i_row[self.POSNET].split(",")
                nets_pos_all.extend(nets_pos_tmp)
                nets_neg_tmp = i_row[self.NEGNET].split(",")
                nets_neg_all.extend(nets_neg_tmp)
                # merge main components in all rows
                main_comp_pos_tmp = self.__get_comp_list(i_row[self.POSMP])
                main_comp_pos_all.extend(main_comp_pos_tmp)
                main_comp_neg_tmp = self.__get_comp_list(i_row[self.NEGMP])
                main_comp_neg_all.extend(main_comp_neg_tmp)
                # merge sense components in all rows
                sns_comp_pos_tmp = self.__get_comp_list(i_row[self.POSAP])
                sns_comp_pos_all.extend(sns_comp_pos_tmp)
                sns_comp_neg_tmp = self.__get_comp_list(i_row[self.NEGAP])
                sns_comp_neg_all.extend(sns_comp_neg_tmp)
                # port counts defined
                if i_row[self.POSMP] != "":
                    port_count_tmp = port_count_tmp + 1
                if i_row[self.POSAP] != "":
                    port_count_tmp = port_count_tmp + 1
            self._port_count_defined[i_key] = port_count_tmp
        # strip whitespaces
        nets_pos_all = [net.strip() for net in nets_pos_all]
        nets_neg_all = [net.strip() for net in nets_neg_all]
        main_comp_pos_all = [comp.strip() for comp in main_comp_pos_all]
        main_comp_neg_all = [comp.strip() for comp in main_comp_neg_all]
        sns_comp_pos_all = [comp.strip() for comp in sns_comp_pos_all]
        sns_comp_neg_all = [comp.strip() for comp in sns_comp_neg_all]
        # remove empty strings if any
        rm_list_item(nets_pos_all, "")
        rm_list_item(nets_neg_all, "")
        rm_list_item(main_comp_pos_all, "")
        rm_list_item(main_comp_neg_all, "")
        rm_list_item(sns_comp_pos_all, "")
        rm_list_item(sns_comp_neg_all, "")
        # remove duplicates
        self._nets_pos = unique_list(nets_pos_all)
        self._nets_neg = unique_list(nets_neg_all)
        self._main_comp_pos = unique_list(main_comp_pos_all)
        self._main_comp_neg = unique_list(main_comp_neg_all)
        self._sns_comp_pos = unique_list(sns_comp_pos_all)
        self._sns_comp_neg = unique_list(sns_comp_neg_all)
        self.lg.debug("Net and component names have been extracted from gSheet.")

    def __get_run_info(self):
        """create run info out of a spd object."""
        spd_proj = self.spd_proj
        run_info_parent = {
            "tool": spd_proj.SOLVER,  # to be verified
            "tool_config": spd_proj.sig_config_dict,
            "tcl_dir": spd_proj.parent_spd_tcl_dir,
            "run_dir": spd_proj.loc_dsn_dir,
            "key2sim": [],
            "done_file": spd_proj.SPD_DONE_FILENAME,
        }
        run_info_check = {
            "tool": spd_proj.SOLVER,
            "tool_config": spd_proj.sig_config_dict,
            "tcl_dir": spd_proj.check_tcl_dir,
            "run_dir": spd_proj.model_check_dir,
            "key2sim": spd_proj.key2check,
            "done_file": spd_proj.CHECK_DONE_FILENAME,
        }
        run_info_sim = {
            "tool": spd_proj.SOLVER,
            "tool_config": spd_proj.sig_config_dict,
            "tcl_dir": spd_proj.sim_tcl_dir,
            "run_dir": spd_proj.sim_dir,
            "key2sim": spd_proj.key2sim,
            "done_file": spd_proj.SIM_DONE_FILENAME,
        }
        run_info = {
            "run_info_parent": run_info_parent,
            "run_info_check": run_info_check,
            "run_info_sim": run_info_sim,
        }
        return run_info

    # ==========================================================================
    # Externally available methods
    # ==========================================================================
    def run(self, mntr_info):
        """run sigrity simulations."""
        # create the parent spd file
        self.__mk_parent_spd(mntr_info)
        # initial check for the input formats and existence of the comps/nets
        self.__init_check()
        # check for the port setups and cap SPICE models
        self._model_check(mntr_info)
        if "op_pause_after_model_check" not in mntr_info:
            pass
        elif mntr_info["op_pause_after_model_check"] == 1:
            self.__pause_for_user_inputs()
        # extract S-parameters
        self.__model_xtract(mntr_info)
        # relocate result files
        self._relocate_results()
        # export result config yaml
        result_config_dir = self._export_result_config()
        report_config_dir = self._export_report_config()
        return result_config_dir, report_config_dir

    # ==========================================================================
    # run() related methods
    # ==========================================================================
    def __mk_parent_spd(self, mntr_info):
        """build the parent spd, extract necessary info to compare against
        the input info.
        """
        # create parent spd first if unavailable
        if not os.path.exists(self.spd_proj.parent_spd_dir):
            self._run_monitor(mntr_info, self.run_info["run_info_parent"])
            self.lg.debug("The parent .spd file is created.")
        else:
            self.lg.debug("The parent .spd already exists. " + "No action is taken.")

    def _model_check(self, mntr_info):
        """check the model port setup, cap model etc."""
        key2sim = self.run_info["run_info_check"]["key2sim"]
        # create model check spd files for each sim
        if key2sim != []:
            self._run_monitor(mntr_info, self.run_info["run_info_check"])
            # compare port counts
            self.__compare_port_count()
            # detect cap SPICE models
            self.__check_cap_model()
        else:
            self.lg.debug("Key is empty! No check is conducted!")

    def __model_xtract(self, mntr_info):
        """extract S parameters and relocate results."""
        key2sim = self.run_info["run_info_sim"]["key2sim"]
        if key2sim != []:
            self._run_monitor(mntr_info, self.run_info["run_info_sim"])
        else:
            self.lg.debug("Key is empty! No sim is conducted!")

    def _run_monitor(self, mntr_info, run_info):
        """monitor the scripts running process."""
        # define variables from external inputs
        email = mntr_info["email"]

        tool = run_info["tool"]
        run_dir = run_info["run_dir"]
        done_file = run_info["done_file"]
        key2sim = run_info["key2sim"]
        key_total = len(key2sim)
        time_elapse = [0] * key_total  # list of used time for each key
        email_sent = [0] * key_total  # list of sent email for each key
        run_type = (done_file.split(".")[0]).capitalize()  # Sim or Check

        if email == "":
            KNOB_EMAIL = 0
        else:
            KNOB_EMAIL = 1
        # internal contants
        CHECK_TIMES = 3
        MAX_RESTART = 3

        # execute scripts
        command = self.__run_tcl(run_info)

        done = run_dir + done_file
        if key2sim == []:
            while not os.path.exists(done):
                self.lg.debug("Waiting for " + done_file + " ...")
                sleep(5)
        else:
            i = 0
            for i_key in key2sim:
                self.lg.debug(run_type + " is running for " + i_key + " ...")
                tic = perf_counter()
                key_done = run_dir + i_key + ".done"
                restart_times = 0
                sample_counter = 0
                while not os.path.exists(key_done):
                    sleep(1)
                    # check every 2 mins
                    if math.floor((perf_counter() - tic) % 120) == 0:
                        # if solver is not running
                        if not (
                            (tool + ".exe").upper()
                            in (p.name().upper() for p in psutil.process_iter())
                        ):
                            sample_counter += 1
                            self.lg.debug(
                                tool
                                + ".exe is not running! Detected for "
                                + str(sample_counter)
                                + " times. Will retry in 2 mins."
                            )
                        else:
                            sample_counter = 0
                        # if solver is found not running for max times
                        if sample_counter == CHECK_TIMES:
                            # if solver is restarted for max times
                            if restart_times == MAX_RESTART:
                                spd_done = run_dir + i_key + ".done"
                                txtfile_wr(spd_done, "")
                                self.lg.debug(
                                    (
                                        "{0}.exe has been restarted {1} "
                                        + "times and still cannot finish "
                                        + "sims for {2}. The {3} will be "
                                        + "skipped!"
                                    ).format(tool, str(MAX_RESTART), i_key, i_key)
                                )
                            os.system(command)
                            if restart_times == MAX_RESTART:
                                break
                            restart_times += 1
                            self.lg.debug(
                                tool
                                + ".exe is not running in the past "
                                + str(2 * sample_counter)
                                + " mins. Restart the tool "
                                + str(restart_times)
                                + " times."
                            )
                            sample_counter = 0

                    # send attention email after 1 hour
                    if KNOB_EMAIL and (perf_counter() - tic > 3600) and (email_sent[i] == 0):
                        email_sent[i] = 1
                        msg = {
                            "recipients": email.usr_gmail,
                            "title": "[Warning] A Single Model Extraction "
                            + "Lasts More Than 1 Hour",
                            "body": "The model extraction for "
                            + i_key
                            + " already takes more than 1 hour "
                            + "and is still running.\n"
                            + "Please check if anything is wrong "
                            + "with the extraction!",
                        }
                        email.send_message(msg)

                toc = perf_counter()
                time_elapse[i] = toc - tic
                if sample_counter == 0:
                    status = "done"
                else:
                    status = "SKIPPED"
                self.lg.debug(
                    ("{} is {} for {} after {} mins and {} secs!").format(
                        run_type,
                        status,
                        i_key,
                        str(math.floor(time_elapse[i] / 60)),
                        str(math.floor(time_elapse[i] % 60)),
                    )
                )
                i = i + 1
                self.lg.debug(f"{run_type} is done for {str(i)} out of total {str(key_total)}!")

            while not os.path.exists(done):
                sleep(1)
            self.lg.debug("Successfully finished all runs!")
            time_total = sum(time_elapse)
            self.lg.debug(
                ("Total elapsed time is {} hours, {} mins, and {} secs!").format(
                    str(math.floor(time_total / 3600)),
                    str(math.floor(time_total / 60)),
                    str(math.floor(time_total % 60)),
                )
            )

    def __run_tcl(self, info):
        """run tcl scripts."""
        # define variables from external inputs
        tool = info["tool"]
        tool_config = info["tool_config"]
        tcl_dir = info["tcl_dir"]

        KNOB_BG_RUN = tool_config["KNOB_BACKGND_RUN"]
        if KNOB_BG_RUN == 1:
            bg_run = "-b "
        else:
            bg_run = ""
        sig_lic = tool_config["SIG_LIC"][tool.upper()]
        lic_in_use = " ".join(["-PS" + tmp for tmp in list_strip(sig_lic)])
        # internal contants
        wait_time = "-wait:1 "  # wait time for licenses

        self.lg.debug(tool + " solver will be launched soon!")
        # run tcl
        if os.name == "nt":  # Windows OS
            sig_dir = slash_ending(os.environ.get("SIGRITY_EDA_DIR")).replace(SL, "/")
            command = (
                "cmd /c start "
                + sig_dir
                + "tools/bin/"
                + tool
                + ".exe "
                + wait_time
                + bg_run
                + lic_in_use
                + ' -tcl "'
                + tcl_dir.replace(SL, "/")
                + '"'
            )
        elif os.name == "posix":  # Mac/Linux/BSD
            linux_settings = load_yaml_to_dict(self.tool_config_dir + "config_linux.yaml")
            command = (
                linux_settings["CMD_HEADER"]
                + tool
                + " "
                + lic_in_use
                + " -tcl "
                + tcl_dir.replace(SL, "/")
            )
        self.lg.debug("The following command will be run: " + command)
        os.system(command)
        self.lg.debug("The above command has been launched.")
        return command

    def __pause_for_user_inputs(self):
        """Pause the scripts and wait for user's inputs."""
        yorn = ""
        while yorn.upper() != ("Y" or "YES"):
            yorn = input("Do you want to continue with simulations? [y/n]\n")
            if yorn.upper() == ("N" or "NO"):
                exit(0)

    def __init_check(self):
        """initial check of the input data."""
        self.lg.debug("Initial check starts.")
        # check the format of the input info
        format_errors = self.__check_input_format()
        if format_errors:
            raise IllegalInputFormat(self.lg, format_errors)
        else:
            self.lg.debug("No known input format errors found.")

        # check the existence of the input components and nets
        # net and component names in the real design have been exported when
        # initializing the class.
        # compare net and component names between input sheet and .info output
        # and raise errors if mismatches are found.
        unfound_names = self.__compare_net_comp_names()
        # raise error if any
        if unfound_names:
            raise NoExistingNames(self.lg, unfound_names)
        self.lg.debug("Initial check completes successfully.")

    def _export_result_config(self):
        """export result config yaml for easy snp processing."""
        result_config_dir = self.result_dir + "results_config.yaml"
        data = {
            "CONNECTIVITY": self.spd_proj.CONNECTIVITY,
            "checked_keys": list(self.spd_proj.sim_input.keys()),
            "spectype": self.__get_spectype_dict(),
            "result_sub_dirs": self.result_sub_dirs,
            "plot_dir": self.plot_dir,
        }
        export_dict_to_yaml(data, result_config_dir)
        return result_config_dir

    def _export_report_config(self):
        """export report config yaml for easy report generation."""
        usr_dir = self.tool_config_dir + "usr.yaml"
        usr_info = load_yaml_to_dict(usr_dir)
        # company logo image
        if "COMPANY_LOGO" not in usr_info:
            logoimg_dir = ""
        else:
            logoimg_dir = expand_home_dir(usr_info["COMPANY_LOGO"])
        report_config_dir = self.report_dir + "report_config.yaml"
        data = {
            "sim_date": self.spd_proj.run_name,
            "report_type": self.report_type,
            "dsn_name": self.spd_proj.dsn_name,
            "xtract_tool": self.xtract_tool,
            "xtract_type": self.spd_proj.xtract_type,
            "proj_name": self.proj_name,
            "result_dir": self.result_dir,
            "report_dir": self.report_dir,
            "report_full_path": self.report_dir + "report_" + self.spd_proj.run_name + ".pdf",
            "design_type": self.spd_proj.design_type,
            "usr_id": usr_info["USR_ID"],
            "logoimg_dir": logoimg_dir,
        }
        export_dict_to_yaml(data, report_config_dir)
        return report_config_dir

    # =============================================================================
    # __init_check() related methods
    # =============================================================================

    def __check_input_format(self):
        """check the input format errors"""
        input = self.sim_input
        input_key = list(input.keys())
        error_all = []
        # check the uniqueness of the key
        dup_key = unique_list([ikey for ikey in input_key if input_key.count(ikey) > 1])
        if dup_key:
            dup_key_err = (
                "[Error] Please change the following key names "
                + "to make them unique: \n"
                + "\n".join(dup_key)
            )
            error_all.append(dup_key_err)
        # check other format issues
        for i_key in input_key:
            # key
            error_all.append(self.__check_key_format(i_key))
            # spec type
            error_all.append(self.__check_spec_type_format(input[i_key], i_key, col=self.SPECTYPE))
            # nets
            error_all.append(self.__check_net_format(input[i_key], i_key, col=self.POSNET))
            error_all.append(self.__check_net_format(input[i_key], i_key, col=self.NEGNET))
            # ports
            error_all.append(
                self.__check_port_format(
                    input[i_key], i_key, pos_col=self.POSMP, neg_col=self.NEGMP
                )
            )
            error_all.append(
                self.__check_port_format(
                    input[i_key], i_key, pos_col=self.POSAP, neg_col=self.NEGAP
                )
            )
            # remove empty strings
            error_all = rm_list_item(error_all, "")
        return error_all

    def __check_key_format(self, i_key):
        """check the format of the key"""
        illegal_symbol = [" ", "-", "$"]
        error_list = [
            '[Error] "' + symbol + '"' + " is not allowed in the key: " + i_key
            for symbol in illegal_symbol
            if symbol in i_key
        ]
        error = "\n".join(error_list)
        return error

    def __check_spec_type_format(self, info, i_key, col):
        """check the format for the spec type"""
        error = ""
        if len(info) == 1:
            if info[0][col] == "":
                error = ("{} -> Col {} ->\n{}").format(
                    i_key, col, "\t[Error] No spec type was specified!"
                )
            else:
                error = ""
        else:
            spec_type = [tmp[col] for tmp in info if tmp[col] != ""]
            # remove duplicates
            spec_type = unique_list(spec_type)
            if len(spec_type) == 0:
                error = ("{} -> Col {} ->\n{}").format(
                    i_key, col, "\t[Error] No spec type was specified!"
                )
            elif len(spec_type) == 1:
                error = ""
            else:
                error = ("{} -> Col {} ->\n{}").format(
                    i_key,
                    col,
                    "\t[Error] More than one spec type was specified, " + "which is not allowed!",
                )
        return error

    def __check_net_format(self, info, i_key, col):
        """check if net is empty"""
        net = self._get_unique_items_in_col(info, col)
        if net == []:
            error = ("{} -> Col {} ->\n{}").format(
                i_key, col, "\t[Error] No net was specified, which is not allowed!"
            )
        else:
            error = ""
        return error

    def __check_port_format(self, info, i_key, pos_col, neg_col):
        """check the format of the port input"""
        error = []
        i = 1
        for i_row in info:
            error.extend(self.__check_comp_format(i_row[pos_col], i_row[neg_col], i))
            i = i + 1
        if error:
            error_key = ("{} -> Col {} and {} ->\n{}").format(
                i_key, pos_col, neg_col, "\n".join(error)
            )
        else:
            error_key = ""
        return error_key

    def __check_comp_format(self, col_p, col_n, i):
        """check the input format of the components"""
        error_msg = []
        # lumped ports
        if ("LUMPED" in col_n.upper()) and (";" in col_n):
            error_msg.append(
                "\tRow "
                + str(i)
                + " ()-("
                + col_n
                + "): [Error] There should be only 1 component symbol "
                + "in the negative side when LUMPED appears."
            )
        if "LUMPED" in col_p.upper():
            error_msg.append(
                "\tRow "
                + str(i)
                + " ("
                + col_p
                + ")-(): [Error] The key word LUMPED is only allowed to "
                + "appear in the negative side of a port."
            )
        # component ports
        if (col_n == "") and (col_p != ""):
            # only 1 component is allowed
            if col_p.upper().startswith("REC") & ("{" in col_p):
                # area port skipped
                pass
            elif ("," in col_p) or (";" in col_p):
                error_msg.append(
                    "\tRow "
                    + str(i)
                    + " ("
                    + col_p
                    + ")-(): [Error] There should be only 1 component symbol "
                    + "in the positive side when the negative side is empty."
                )
        if ";" in col_p:
            port_list = list_strip(col_p.split(";"))
            comp_wo_pin = [port for port in port_list if "," not in port]
            if comp_wo_pin:
                error_msg.append(
                    "\tRow "
                    + str(i)
                    + " ("
                    + col_p
                    + ")-(): [Error] The component must come with pins when "
                    + "multi-components are used to define a port. Pins "
                    + "are missing for the following components:\n"
                    + ", ".join(comp_wo_pin)
                )
        if ";" in col_n:
            port_list = list_strip(col_n.split(";"))
            comp_wo_pin = [port for port in port_list if "," not in port]
            if comp_wo_pin:
                error_msg.append(
                    "\tRow "
                    + str(i)
                    + " ()-("
                    + col_n
                    + "): [Error] The component must come with pins when "
                    + "multi-components are used to define a port. Pins "
                    + "are missing for the following components:\n"
                    + ", ".join(comp_wo_pin)
                )
        return error_msg

    def __compare_net_comp_names(self):
        """compare net and component names between gSheet input
        and a real design file.
        """
        # compare net names
        unfound_net = self.__compare_net()
        # compare component names
        unfound_comp = self.__compare_comp()
        return unfound_net + unfound_comp

    def __compare_net(self):
        """compare net names and return the unfound ones"""
        # import net names from all_nets.info
        nets_spd = txtfile_rd(self.spd_proj.netinfo_dir).strip().split(" ")
        # positive
        unfound_net_pos = self.__compare_netname(nets_spd, self._nets_pos, self.POSNET)
        # negative
        unfound_net_neg = self.__compare_netname(nets_spd, self._nets_neg, self.NEGNET)
        self.lg.debug("Netname comparison is done.")
        return unfound_net_pos + unfound_net_neg

    def __compare_netname(self, name_spd, name_gsheet, col):
        """compare net names and return the unfound ones"""
        unfound_item = []
        match_tf = [(item in name_spd) for item in name_gsheet]
        if False in match_tf:
            unfound_name = [item for (item, tf) in zip(name_gsheet, match_tf) if not tf]
            for i_name in unfound_name:
                for key, val in self.sim_input.items():
                    val_all = []
                    for i_val in val:
                        val_all.extend(list_strip(i_val[col].split(",")))
                    if i_name in val_all:
                        unfound_item.extend([key + " -> " + "Col " + col + " -> " + i_name])
        else:
            self.lg.debug("All input net names in Sheet Col " + col + " exist in the design file.")
        return unfound_item

    def __compare_comp(self):
        """compare component names and return the unfound ones"""
        # import component names from all_comps.info
        comps_spd = txtfile_rd(self.spd_proj.compinfo_dir).strip().split(" ")
        # main component positive
        unfound_main_comp_pos = self.__compare_compname(comps_spd, self._main_comp_pos, self.POSMP)
        # main component negative
        unfound_main_comp_neg = self.__compare_compname(comps_spd, self._main_comp_neg, self.NEGMP)
        # sense component positive
        unfound_sns_comp_pos = self.__compare_compname(comps_spd, self._sns_comp_pos, self.POSAP)
        # sense component negative
        unfound_sns_comp_neg = self.__compare_compname(comps_spd, self._sns_comp_neg, self.NEGAP)
        self.lg.debug("Component name comparison is done.")
        return (
            unfound_main_comp_pos
            + unfound_main_comp_neg
            + unfound_sns_comp_pos
            + unfound_sns_comp_neg
        )

    def __compare_compname(self, name_spd, name_gsheet, col):
        """compare component names and return the unfound ones"""
        unfound_item = []
        match_tf = [(item in name_spd) for item in name_gsheet]
        if False in match_tf:
            unfound_name = [item for (item, tf) in zip(name_gsheet, match_tf) if not tf]
            # unfound_name = [
            #     item for item in unfound_name if item.upper() != 'LUMPED']
            for i_name in unfound_name:
                for key, val in self.sim_input.items():
                    val_all = []
                    for i_val in val:
                        tmp = i_val[col].split(";")
                        tmp_comp = [item.split(",")[0].strip() for item in tmp]
                        val_all.extend(tmp_comp)
                    if i_name in val_all:
                        unfound_item.extend([key + " -> " + "Col " + col + " -> " + i_name])
        else:
            self.lg.debug(
                "All input component names in Sheet Col " + col + " exist in the design file."
            )
        return unfound_item

    def __get_comp_list(self, raw_data):
        """get a list of components"""
        comp = []
        comp_grp = raw_data.split(";")
        for i_grp in comp_grp:
            if i_grp.upper().startswith("REC") & ("{" in i_grp):
                pass
            else:
                tmp = i_grp.split(",")
                comp.extend([tmp[0]])
        return comp

    def _get_unique_items_in_col(self, data, col):
        """get unique non-empty item names for the whole column"""
        merged_nets = []
        for i_list in data:
            merged_nets.extend(striped_str2list(i_list[col], ","))
        # remove duplicates
        unique_nets = unique_list(merged_nets)
        # remove empty string
        unique_nets = rm_list_item(unique_nets, "")
        return unique_nets

    def _get_unique_comps_in_col(self, data, col):
        """Get unique non-empty component names for the whole column."""
        merged_comps = []
        for i_list in data:
            refdes, _ = self._get_refdes_n_pins(i_list[col])
            merged_comps.append(refdes)
        unique_comps = unique_list(merged_comps)
        unique_comps = rm_list_item(unique_comps, "")
        return unique_comps

    def _get_refdes_n_pins(self, in_str):
        """Break the input string to refdes string and pin lists"""
        tmp_list = striped_str2list(in_str, ",")
        refdes = tmp_list[0]
        pins = tmp_list[1:]
        return refdes, pins

    # ==========================================================================
    # __model_check() related methods
    # ==========================================================================
    def __compare_port_count(self):
        """compare port counts between defined and the actually generated."""
        # extract the counts of the actually generated ports in a spd
        port_count_spd = self.__get_port_count_spd()
        # compare
        input_key = list(self.sim_input.keys())
        unequal_ports_key = [
            i_key for i_key in input_key if port_count_spd[i_key] != self._port_count_defined[i_key]
        ]
        if unequal_ports_key == []:
            self.lg.debug("Port counts are checked. Everything is correct! ")
        else:
            raise UnequalPortCounts(self.lg, unequal_ports_key)

    def __get_port_count_spd(self):
        """extract the counts of the actually generated ports in spd file"""
        input_key = list(self.sim_input.keys())
        port_count_spd = {}
        for i_key in input_key:
            port_csv_dir = self.spd_proj.model_check_dir + "Ports_" + i_key + ".csv"
            port_info = txtfile_rd(port_csv_dir).split("\n")
            port_count = 0
            for line in port_info:
                if line.startswith("Port_"):
                    port_count = port_count + 1
            port_count_spd[i_key] = port_count
        return port_count_spd

    def __check_cap_model(self):
        """Check if SPICE models are used for a cap. The assumption
        is that a SPICE model will be longer than 10 lines.
        """
        input_key = list(self.sim_input.keys())
        cap_model_lines = {}
        for i_key in input_key:
            cap_csv_dir = self.spd_proj.model_check_dir + "Caps_" + i_key + ".csv"
            cap_info = txtfile_rd(cap_csv_dir)
            COMMA_MATCHER = re.compile(r",(?=(?:[^\"']*[\"'][^\"']*[\"'])*[^\"']*$)")
            split_result = rm_list_item(list_strip(COMMA_MATCHER.split(cap_info)), "")

            i = 0
            tmp_list = []
            while i < len(split_result):
                tmp_list.append([split_result[i], len(split_result[i + 1].split("\n"))])
                i += 2
            cap_model_lines[i_key] = tmp_list

        warning_msg = [
            "The following caps don't adopt SPICE type models. "
            + "Please double check the AMM library!"
        ]
        for key in cap_model_lines:
            val = cap_model_lines[key]
            for i_val in val:
                if i_val[1] <= 10:
                    warning_msg.append(f"Sim Key: {key} -> {i_val[0]}")
        if len(warning_msg) == 1:
            self.lg.debug("Cap models are checked. " + "All uses SPICE type models! ")
        else:
            self.lg.debug("\n".join(warning_msg))

    # ==========================================================================
    # __model_xtract() related methods
    # ==========================================================================
    def _relocate_results(self):
        """relocate sim results to the result directory if unavailable."""
        # make folders in the result directory
        make_dir(self.snp_s_dir)
        make_dir(self.snp_dcfitted_dir)
        # make_dir(self.snp_dc_dir)
        # make_dir(self.bbs_dcfitted_dir)
        # make_dir(self.bbs_s_dir)
        # find and make a copy of SNP files
        items = os.listdir(self.sim_dir)
        for item in items:
            if re.search(r"_S\.S[\d]+P$", item.upper()) is not None:
                self._mk_file_copy(self.sim_dir, self.snp_s_dir, item)
            elif re.search(r"_DCFITTED\.S[\d]+P$", item.upper()) is not None:
                self._mk_file_copy(self.sim_dir, self.snp_dcfitted_dir, item)
            r"""elif re.search('_DC\.S[\d]+P$', item.upper()) is not None:
                self._mk_file_copy(self.sim_dir, self.snp_dc_dir, item)
            elif re.search('BBSRESULT_.+_DCFITTED',
                            item.upper()) is not None:
                bbs_dir = self.sim_dir + item + SL
                bbs_item = item.replace('BBSResult_', '') + '_BBSckt.txt'
                self._mk_file_copy(
                    bbs_dir, self.bbs_dcfitted_dir, bbs_item)
            elif re.search('BBSRESULT_.+_S_BBS', item.upper()) is not None:
                bbs_dir = self.sim_dir + item + SL
                bbs_item = item.replace('BBSResult_', '') + '_BBSckt.txt'
                self._mk_file_copy(bbs_dir, self.bbs_s_dir, bbs_item)"""

    def _mk_file_copy(self, dir_old, dir_new, item):
        """make a copy to a folder if the file doesn't exist there"""
        if not os.path.exists(dir_new + item):
            shutil.copy(dir_old + item, dir_new)
            self.lg.debug(item + " has been copied to " + dir_new)
        else:
            self.lg.debug(item + " already exists in " + dir_new)

    # ==========================================================================
    # __export_result_config() related methods
    # ==========================================================================
    def __get_spectype_dict(self):
        """Output the spectype per sim key."""
        all_input = self.all_input
        out_dict = {}
        for key_name in all_input:
            tmp_value = all_input[key_name]
            spectype = tmp_value[0][self.SPECTYPE]
            out_dict[key_name] = spectype
        return out_dict


class PowersiIOExec(PowersiPdnExec):
    """This class parses input info as executable tcl scripts, launches
    simulations, conducts formality checks and etc. This class is only
    for LSIO extractions using PowerSI.
    """

    def __init__(self, info):
        super().__init__(info)
        self.report_type = "IO"

    # ==========================================================================
    # Class initialization related method
    # ==========================================================================
    def _get_spd_proj(self, info):
        """initialize spd proj"""
        inst = PowersiIOModeler(info)
        inst.mk_tcl()
        return inst


class ClarityExec(PowersiIOExec):
    """This class parses input info as executable tcl scripts, launches
    simulations, conducts formality checks and etc. This class is only
    for HSIO extractions using PowerSI.
    """

    def __init__(self, info):
        super().__init__(info)
        self.result_sub_dirs = {
            "snp_s_dir": self.snp_s_dir,
        }

    # ==========================================================================
    # Class initialization related method
    # ==========================================================================
    def _get_spd_proj(self, info):
        """initialize spd proj"""
        inst = ClarityModeler(info)
        inst.mk_tcl()
        return inst

    def _relocate_results(self):
        """relocate sim results to the result directory"""
        # make folders in the result directory
        make_dir(self.snp_s_dir)
        make_dir(self.snp_dc_dir)
        # find and make a copy of SNP files
        items = os.listdir(self.sim_dir)
        for item in items:
            if re.search(r"_FIT\.S[\d]+P$", item.upper()) is not None:
                self._mk_file_copy(self.sim_dir, self.snp_s_dir, item)
            elif re.search(r"_DC\.S[\d]+P$", item.upper()) is not None:
                self._mk_file_copy(self.sim_dir, self.snp_dc_dir, item)


class PowerdcExec(PowersiPdnExec):
    """This class parses input info as executable tcl scripts, launches
    simulations. This class is only for DCR extractions using PowerDC.
    """

    def __init__(self, info):
        super().__init__(info)
        # define variables
        self.csv_dir = self.sim_dir + "CSVFolder" + SL
        self.RESIS_CSV = "Resis.csv"
        self.result_csv = self.result_dir + self.RESIS_CSV
        self.result_dirs = {
            "result_csv": self.result_csv,
        }
        self.report_type = "DCR"

    # ==========================================================================
    # Class initialization related method
    # ==========================================================================
    def _get_spd_proj(self, info):
        """initialize spd proj"""
        inst = PowerdcModeler(info)
        inst.mk_tcl()
        return inst

    def _model_check(self, mntr_info):
        """check the model port setup, cap model etc."""
        key2sim = self.run_info["run_info_check"]["key2sim"]
        # create model check spd files for each sim
        if key2sim != []:
            self._run_monitor(mntr_info, self.run_info["run_info_check"])
        else:
            self.lg.debug("Key is empty! No check is conducted!")

    def _relocate_results(self):
        """relocate sim results to the result directory"""
        # find and make a copy of resistance measurement csv file
        self._mk_file_copy(self.csv_dir, self.result_dir, self.RESIS_CSV)

    def _export_result_config(self):
        """export result config yaml for easy snp processing."""
        self.__process_dcr()
        result_config_dir = ""
        return result_config_dir

    def _export_report_config(self):
        """export report config yaml for easy report generation."""
        usr_dir = self.tool_config_dir + "usr.yaml"
        usr_info = load_yaml_to_dict(usr_dir)
        report_config_dir = self.report_dir + "report_config.yaml"
        data = {
            "sim_date": self.spd_proj.run_name,
            "report_type": self.report_type,
            "dsn_name": self.spd_proj.dsn_name,
            "xtract_tool": self.xtract_tool,
            "xtract_type": self.spd_proj.xtract_type,
            "proj_name": self.proj_name,
            "result_dir": self.result_dir,
            "report_dir": self.report_dir,
            "report_full_path": self.report_dir + "Report.csv",
            "design_type": self.spd_proj.design_type,
            "usr_id": usr_info["USR_ID"],
        }
        export_dict_to_yaml(data, report_config_dir)
        return report_config_dir

    def __process_dcr(self):
        """process the raw DCR values and save in a new csv file."""
        report_csv = self.report_dir + "Report.csv"
        # rename to sim key, extract the worst DCR in mOhm
        key_net_ckt = self.__get_key_net_ckt()
        # read in results
        old_result, _ = csv2dict(self.result_csv)
        new_result = {}
        for i_list in key_net_ckt:
            rm_name = "RESI_" + i_list[0]
            if rm_name in old_result:
                r_str = self._get_unique_items_in_col(old_result[rm_name], 8)
                r_float = [float(tmp) for tmp in r_str]
                new_result[i_list[0]] = str(max(r_float) * 1e3)  # mOhm
                old_result.pop(rm_name, None)
            else:
                for i_key in old_result:
                    a = any([(tmp in i_key) for tmp in i_list[1]])
                    b = any([(tmp in i_key) for tmp in i_list[2]])
                    c = any([(tmp in i_key) for tmp in i_list[3]])
                    if a and b and c:
                        r_str = self._get_unique_items_in_col(old_result[i_key], 8)
                        r_float = [float(tmp) for tmp in r_str]
                        new_result[i_list[0]] = str(max(r_float) * 1e3)  # mOhm
                        old_result.pop(i_key, None)
                        break
        # export report csv
        new_list = [["Sim Key", "Worst DCR (mOhm)"]]
        for i_key in new_result:
            new_list.append([i_key, new_result[i_key]])
        tmp_list = [",".join(tmp) for tmp in new_list]
        output_str = "\n".join(tmp_list)
        txtfile_wr(report_csv, output_str)
        return new_result

    def __get_key_net_ckt(self):
        """Get a list of key, net, and ckt info."""
        sim_keys = self.sim_input.keys()
        key_net_ckt = []
        for rail_key in sim_keys:
            info = self.sim_input[rail_key]
            net_pos = self._get_unique_items_in_col(info, self.POSNET)
            net_neg = self._get_unique_items_in_col(info, self.NEGNET)
            # Rename is only needed when sink refdes is provided without
            # any pins. Therefore, only Col F is needed to extract sink
            sink = self._get_unique_comps_in_col(info, self.POSMP)
            key_net_ckt.append([rail_key, net_pos, net_neg, sink])
        return key_net_ckt
