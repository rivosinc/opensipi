# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
Author: yanshengw@
Last updated on Dec. 14, 2023

Description:
    This module contains all Classes used to parse for Cadence Sigrity Tools.
"""


import os
import re

from opensipi.constants.CONSTANTS import FREQ_RANGE, SIM_INPUT_COL_TITLE
from opensipi.util.common import (
    SL,
    expand_home_dir,
    get_cols_out_of_list_of_list,
    get_run_time,
    list_strip,
    load_yaml_to_dict,
    rm_ext,
    rm_list_item,
    split_str_by_guess,
    str2dict,
    str2listoflist,
    striped_str2list,
    txtfile_rd,
    txtfile_wr,
    unique_list,
)
from opensipi.util.exceptions import (
    UndefinedSurfaceRoughnessModelType,
    WrongAreaPortDef,
    WrongGrowSolderFormat,
)


class SpdModeler:
    """This class converts a design file to a spd file for later use."""

    TCL_GROW_TOP_SOLDER = (
        "sigrity::import PseudoPCB -ckt REFDES "
        + "-method {SolderBall} -MatchSel {RetainName} -unit {mm} "
        + "-height {HVAL} -radius {RVAL} "
        + "-PackageNotOnTop -Prefix -ApplyTo {PKG&PCB} {!}\n"
    )
    TCL_GROW_BOT_SOLDER = (
        "sigrity::import PseudoPCB -ckt REFDES "
        + "-method {SolderBall} -MatchSel {RetainName} -unit {mm} "
        + "-height {HVAL} -radius {RVAL} "
        + "-Prefix -ApplyTo {PKG&PCB} {!}\n"
    )
    TCL_UPDATE_LAYER_NAME = "sigrity::update layer " + "layer_name {LAYERNAME} {Plane01} {!}\n"
    TCL_UPDATE_LAYER_T = "sigrity::update layer " + "thickness 2e-6 {LAYERNAME} {!}\n"
    TCL_UPDATE_REFDES = "sigrity::update circuit " + "-name {REFDES_solder} {NewEmptyPkgCkt1} {!}\n"
    TCL_CREATE_HURAY_SR_MODEL = (
        "sigrity::add SurfaceRoughness "
        + "-name {SRM_NAME} -type {SRM_TYPE} -SurfaceRatio {SRM_FACTOR} "
        + "-SnowballRadius {SRM_VALUE} {!}\n"
    )
    TCL_CREATE_MODIFIED_SR_MODEL = (
        "sigrity::add SurfaceRoughness "
        + "-name {SRM_NAME} -type {SRM_TYPE} -RoughnessFactor {SRM_FACTOR} "
        + "-RMSValue {SRM_VALUE} {!}\n"
    )

    def __init__(self, info):
        # define variables
        self.stackup = info["stackup_info"]["stackup"]
        self.materials = info["stackup_info"]["materials"]
        self.surface_roughness = info["stackup_info"]["surfaceroughness"]
        self.settings = info["settings"]
        self.xtract_type = self.settings["EXTRACTIONTYPE"].upper()
        self.design_type = self.settings["DESIGNTYPE"].upper()
        self.solder_keys = ["GROWTOPSOLDER", "GROWBOTSOLDER"]
        # define optional keywords
        self.optional_key_list = self.solder_keys + [
            "GLOBALFREQ",
            "BOM",
            "REFDESOFFSETNODES",
            "CAPREFDES",
        ]
        for op_key in self.optional_key_list:
            self._init_optional_setting_key(op_key)
        self.run_name = info["run_name"]
        self.tool_config_dir = info["tool_config_dir"]
        self.dsn_dir = info["dsn_dir"]
        self.dsn_name = info["dsn_name"]
        self.loc_dsn_raw = info["loc_dsn_raw"]
        self.loc_dsn_dir = info["loc_dsn_dir"]
        self.loc_script_dir = info["loc_script_dir"]
        self.template_dir = info["template_dir"]
        self.sim_input = info["sim_input"]
        self.all_input = info["all_input"]
        self.lg = info["log"].getChild("/" + __name__)
        # define constants
        self.sig_config_dict = load_yaml_to_dict(self.tool_config_dir + "config_sigrity.yaml")
        self.sig_lic = self.sig_config_dict["SIG_LIC"]
        self.sig_lib = expand_home_dir(self.sig_config_dict["SIG_LIB"])
        if "SHAPE_CUT_TYPE" not in self.sig_config_dict:
            self.SHAPE_CUT_TYPE = "CONFORMAL"
        else:
            self.SHAPE_CUT_TYPE = self.sig_config_dict["SHAPE_CUT_TYPE"]
        self.SOLVER = "powersi"
        self.UNIKEY = SIM_INPUT_COL_TITLE[0]
        self.CKBOX = SIM_INPUT_COL_TITLE[1]
        self.SPECTYPE = SIM_INPUT_COL_TITLE[2]
        self.POSNET = SIM_INPUT_COL_TITLE[3]
        self.NEGNET = SIM_INPUT_COL_TITLE[4]
        self.POSMP = SIM_INPUT_COL_TITLE[5]
        self.NEGMP = SIM_INPUT_COL_TITLE[6]
        self.POSAP = SIM_INPUT_COL_TITLE[7]
        self.NEGAP = SIM_INPUT_COL_TITLE[8]
        self.OPFREQ = SIM_INPUT_COL_TITLE[9]
        self.OPDIFFPAIR = SIM_INPUT_COL_TITLE[10]
        self.OPDISALLCAPS = SIM_INPUT_COL_TITLE[11]
        # C is the default starting keyword in the cap RefDes
        self.CAP_KEY = unique_list(striped_str2list("C," + self.settings["CAPREFDES"].upper(), ","))
        self.MAT_CMX = "materials.cmx"
        self.TEMP_MAT = "temp_materials.cmx"
        self.STACKUP_CSV = "stackup.csv"
        self.TEMP_PARENT_SPD = "temp_mk_parent_spd.tcl"
        self.MK_PARENT_SPD_TCL = "mk_parent_spd.tcl"
        self.parent_spd_tcl_dir = self.loc_script_dir + self.MK_PARENT_SPD_TCL
        self.parent_spd_dir = self.loc_dsn_dir + rm_ext(self.dsn_name) + ".spd"
        self.SPD_DONE_FILENAME = "spd.done"
        self.netinfo_dir = self.loc_dsn_dir + "all_nets.info"
        self.compinfo_dir = self.loc_dsn_dir + "all_comps.info"
        self.bom_tcl_dir = self.loc_script_dir + "bom.tcl"
        self.PROC_COMMON_TCL_DIR = self.template_dir + "proc_common.tcl"
        self.solder_ext = "_solder"
        self.solder_refdes = self.__get_solder_refdes()
        self.CONNECTIVITY = self.__get_connectivity()
        if self.xtract_type == "DCR":  # determine if port info is exported
            self.EXPORT_PORT = "false"
        else:
            self.EXPORT_PORT = "true"
        # make a material .cmx file
        self.__mk_mat_cmx()
        # make a stackup .csv file
        self.__mk_stackup_csv()
        # make a bom.tcl file
        self.__mk_bom_tcl()
        # create parent spd tcl file
        self.__mk_parent_spd_tcl()

    # ==========================================================================
    # Class initialization related method
    # ==========================================================================
    # define materials
    def __mk_mat_cmx(self):
        """make a project specific materials.cmx file if unavailable."""
        if not os.path.exists(self.loc_dsn_dir + self.MAT_CMX):
            mat_lines = ""
            for i_mat in self.materials:
                if i_mat[1].upper() == "DIELECTRIC":
                    mat_lines = mat_lines + self.__mat_die(i_mat)
                elif i_mat[1].upper() == "METAL":
                    mat_lines = mat_lines + self.__mat_metal(i_mat)
                else:
                    pass
            # read in and revise the template and save it
            temp_mat = txtfile_rd(self.template_dir + self.TEMP_MAT)
            temp_mat = temp_mat.replace("MAT_LINES", mat_lines)
            txtfile_wr(self.loc_dsn_dir + self.MAT_CMX, temp_mat)
            self.lg.debug("A material library file " + "materials.cmx is made.")
        else:
            self.lg.debug("materials.cmx already exists. " + "No action is taken.")

    def __mat_die(self, mat):
        """define each dielectric material"""
        temp_mat = (
            '<Material name="MAT_NAME">\n\t<Dielectric>\n'
            + "\t\t<Model>\n\t\t\tFreq Diek Disf\n"
            + "\t\t</Model>\n\t</Dielectric>\n</Material>\n"
        )
        temp_mat = temp_mat.replace("MAT_NAME", mat[0])
        temp_mat = temp_mat.replace("Freq", mat[3])
        temp_mat = temp_mat.replace("Diek", mat[4])
        temp_mat = temp_mat.replace("Disf", mat[5])
        return temp_mat

    def __mat_metal(self, mat):
        """define each metal material"""
        temp_mat = (
            '<Material name="MAT_NAME">\n\t<Metal>\n'
            + "\t\t<Model>\n\t\t\tTEMP CONDUCTIVITY\n"
            + "\t\t</Model>\n\t</Metal>\n</Material>\n"
        )
        temp_mat = temp_mat.replace("MAT_NAME", mat[0])
        temp_mat = temp_mat.replace("TEMP", "20")
        temp_mat = temp_mat.replace("CONDUCTIVITY", mat[2])
        return temp_mat

    # define stackup
    def __mk_stackup_csv(self):
        """make a project specific stackup.csv file if unavailable"""
        if not os.path.exists(self.loc_dsn_dir + self.STACKUP_CSV):
            stackup_lines = (
                "Layer #,Layer Name,Thickness(mm),Material,Conductivity(S/m),"
                + "Fill-in Dielectric,Er,Loss Tangent,Shape Name,Trace Width(mm),"
                + "Trapezoidal Angle(deg),Roughness Upper,Roughness Lower,Roughness Side,"
                + "Dogleg Hole Threshold(mm),Thermal Hole Threshold(mm),"
                + "Small Hole Threshold(mm),Via Hole Threshold(mm),"
                + "Slender Hole Area Threshold(mm^2),Slender Hole Size Threshold(mm),"
                + "Auto Special Void\n"
            )
            layer_counts = len(self.stackup["LAYER_NAME"])
            for i in range(layer_counts):
                stackup_lines = (
                    stackup_lines
                    + ","
                    + self.stackup["LAYER_NAME"][i]
                    + ","
                    + self.stackup["THICKNESS_MM"][i]
                    + ","
                    + self.stackup["MATERIAL"][i]
                    + ","
                    + ","
                    + self.stackup["OP_FILLIN_DIELECTRIC"][i]
                    + ","
                    + "," * 5
                    + self.stackup["OP_ROUGHNESS_UPPER"][i]
                    + ","
                    + self.stackup["OP_ROUGHNESS_LOWER"][i]
                    + ","
                    + self.stackup["OP_ROUGHNESS_SIDE"][i]
                    + ","
                    + "," * 6
                    + "\n"
                )
            txtfile_wr(self.loc_dsn_dir + self.STACKUP_CSV, stackup_lines)
            self.lg.debug("A stackup file stackup.csv is made.")
        else:
            self.lg.debug("stackup.csv already exists. " + "No action is taken.")

    # create a bom tcl
    def __mk_bom_tcl(self):
        """Make a tcl to create a bom dict if unavailable. This dict is used
        to verify DNS components.
        """
        if not os.path.exists(self.bom_tcl_dir):
            bom_lines = []
            bom_info = self.settings["BOM"]
            if bom_info != "":
                refdes = split_str_by_guess(bom_info)
                bom_lines = [(item + " 0") for item in refdes]
            if bom_lines:
                bom_tcl = "set bom [ dict create " + " ".join(bom_lines) + " ]"
            else:
                bom_tcl = ""
            txtfile_wr(self.bom_tcl_dir, bom_tcl)
            self.lg.debug("A bom.tcl is made.")
        else:
            self.lg.debug("A bom.tcl already exists. No action is taken.")

    # create a tcl for creating the parent spd file
    def __mk_parent_spd_tcl(self):
        """create mk_parent_spd.tcl if not available yet."""
        if not os.path.exists(self.parent_spd_tcl_dir):
            # read in and revise the tcl template
            temp_tcl = txtfile_rd(self.template_dir + self.TEMP_PARENT_SPD)
            temp_tcl = temp_tcl.replace("PROC_COMMON_TCL_DIR", self.PROC_COMMON_TCL_DIR)
            temp_tcl = temp_tcl.replace("DSN_DIR", self.loc_dsn_dir + self.loc_dsn_raw)
            temp_tcl = temp_tcl.replace("CREATESRM", self.__create_surface_roughness_model_tcl())
            temp_tcl = temp_tcl.replace("MAT_DIR", self.loc_dsn_dir + self.MAT_CMX)
            temp_tcl = temp_tcl.replace("STACKUP_DIR", self.loc_dsn_dir + self.STACKUP_CSV)
            temp_tcl = temp_tcl.replace(
                "OPTION_DIR", expand_home_dir(self.sig_config_dict["SIG_OPTION"])
            )
            temp_tcl = temp_tcl.replace("NETINFO", (self.netinfo_dir).replace(SL, "/"))
            temp_tcl = temp_tcl.replace("COMPINFO", (self.compinfo_dir).replace(SL, "/"))
            temp_tcl = temp_tcl.replace("SPD_DIR", self.parent_spd_dir)
            temp_tcl = temp_tcl.replace(
                "RUN_DONE", (self.loc_dsn_dir + self.SPD_DONE_FILENAME).replace(SL, "/")
            )
            temp_tcl = temp_tcl.replace("REFDES_LIST", self.__get_refdes_array_for_offset_nodes())
            temp_tcl = temp_tcl.replace("GRWSOLDER", self.__grow_solder_tcl())
            # export a tcl script
            txtfile_wr(self.parent_spd_tcl_dir, temp_tcl)
            self.lg.debug("mk_parent_spd.tcl is made.")
        else:
            self.lg.debug("mk_parent_spd.tcl already exists. No action is taken.")

    def __create_surface_roughness_model_tcl(self):
        """generate the tcl to create surface roughness models"""
        srm_lines = []
        for srm in self.surface_roughness:
            if srm[1].upper() == "HURAY":
                line = self.TCL_CREATE_HURAY_SR_MODEL
            elif srm[1].upper() == "MODIFIEDHAMMERSTAD":
                line = self.TCL_CREATE_MODIFIED_SR_MODEL
            elif srm[1].upper() == "MODIFIEDGROISSE":
                line = self.TCL_CREATE_MODIFIED_SR_MODEL
            elif srm[1].upper() == "":
                line = ""
            else:
                error_msg = "The input surface roughness model type " + srm[1] + " was undefined!"
                raise UndefinedSurfaceRoughnessModelType(self.lg, error_msg)
            if line != "":
                line = line.replace("SRM_NAME", srm[0])
                line = line.replace("SRM_TYPE", srm[1])
                line = line.replace("SRM_FACTOR", srm[2])
                line = line.replace("SRM_VALUE", srm[3])
                srm_lines.append(line)
        return "".join(srm_lines)

    def __get_solder_refdes(self):
        """define solder refdes out of the original refdes"""
        solder_refdes = {}
        for ss in self.solder_keys:
            grow_solder = self.settings[ss]
            if grow_solder != "":
                solder = grow_solder.split(",")
                solder_refdes[solder[0]] = solder[0] + self.solder_ext
        return solder_refdes

    def __grow_solder_tcl(self):
        """generate the tcl to grow solder"""
        grow_top_solder = self.settings[self.solder_keys[0]]
        grow_bot_solder = self.settings[self.solder_keys[1]]
        solder_tcl = []
        error = []
        # top solder
        if grow_top_solder != "":
            solder = grow_top_solder.split(",")
            if len(solder) == 3:
                tmp_tcl = (
                    "# Grow top solder\n"
                    + self.TCL_GROW_TOP_SOLDER
                    + self.TCL_UPDATE_LAYER_NAME
                    + self.TCL_UPDATE_LAYER_T
                    + self.TCL_UPDATE_REFDES
                )
                tmp_tcl = tmp_tcl.replace("REFDES", solder[0])
                tmp_tcl = tmp_tcl.replace("HVAL", solder[1])
                tmp_tcl = tmp_tcl.replace("RVAL", solder[2])
                tmp_tcl = tmp_tcl.replace("LAYERNAME", "PlaneTop")
                solder_tcl.append(tmp_tcl)
            else:
                error.append(
                    "GrowTopSolder in the Tab Special_Settings is not "
                    + "correctly set. It must be {Refdes on top layer, "
                    + "solder height in mm, solder radius in mm}"
                )
        # bottom solder
        if grow_bot_solder != "":
            solder = grow_bot_solder.split(",")
            if len(solder) == 3:
                tmp_tcl = (
                    "# Grow bottom solder\n"
                    + self.TCL_GROW_BOT_SOLDER
                    + self.TCL_UPDATE_LAYER_NAME
                    + self.TCL_UPDATE_LAYER_T
                    + self.TCL_UPDATE_REFDES
                )
                tmp_tcl = tmp_tcl.replace("REFDES", solder[0])
                tmp_tcl = tmp_tcl.replace("HVAL", solder[1])
                tmp_tcl = tmp_tcl.replace("RVAL", solder[2])
                tmp_tcl = tmp_tcl.replace("LAYERNAME", "PlaneBot")
                solder_tcl.append(tmp_tcl)
            else:
                error.append(
                    "GrowBotSolder in the Tab Special_Settings is not "
                    + "correctly set. It must be {Refdes on bottom layer, "
                    + "solder height in mm, solder radius in mm}"
                )
        if error != []:
            raise WrongGrowSolderFormat(self.lg, "\n".join(error))
        solder_cmd = "".join(solder_tcl)
        return solder_cmd

    def __get_refdes_array_for_offset_nodes(self):
        """Get refdes array with refdes and offset info."""
        refdes_line = []
        refdes_info = self.settings["REFDESOFFSETNODES"]
        if refdes_info != "":
            refdes_lists = str2listoflist(refdes_info, ";", ",")
            for refdes in refdes_lists:
                # unit conversion
                offset_val_in_m = str(float(refdes[1]) * 1e-3)
                refdes_line.append('"' + refdes[0] + " " + offset_val_in_m + '"')
        return "\n".join(refdes_line)

    def __get_connectivity(self):
        """Get the connectivity for SIPI extraction."""
        conn_dict = {}
        all_input = self.all_input
        if self.xtract_type in ["HSIO", "LSIO"]:
            # port connectivity must follow rules below:
            # 1. Row 1 in Col F ang H must not be empty
            # 2. The connectivity can be one to one, one to multiples, and
            #    multiples to one
            # 3. The empty cells in Col G/H starting from Row 2 indicate
            #    adopting the port# from above
            for i_key in all_input:
                temp_list = all_input[i_key]
                # IL
                i = 0
                j = 0
                il_list = []
                for i_list in temp_list:
                    if i_list[self.POSMP]:
                        i += 1
                        if i_list[self.POSAP]:
                            j += 1
                    else:
                        if i_list[self.POSAP]:
                            j += 1
                    il_list.append([i, j])
                port_count_f = il_list[-1][0]
                port_count_h = il_list[-1][1]
                total_port_count = port_count_f + port_count_h
                if port_count_h != 0:
                    for i_row in range(len(il_list)):
                        il_list[i_row][1] += port_count_f
                else:  # no through connections and thus no IL
                    il_list = []
                # RL
                rl_list = list(range(1, total_port_count + 1))
                conn_dict[i_key] = {
                    "IL": il_list,
                    "RL": rl_list,
                }
        elif self.xtract_type in ["PDN"]:
            for i_key in all_input:
                temp_list = all_input[i_key]
                # Zin
                i = 0
                zin_list = []
                for i_list in temp_list:
                    if i_list[self.POSMP]:
                        i += 1
                        zin_list.append(i)
                conn_dict[i_key] = {
                    "ZIN": zin_list,
                }
        return conn_dict

    def _get_refdes_n_pins(self, in_str):
        """Break the input string to refdes string and pin lists"""
        tmp_list = striped_str2list(in_str, ",")
        refdes = tmp_list[0]
        pins = tmp_list[1:]
        return refdes, pins

    def _init_optional_setting_key(self, op_key):
        """Initialize optional setting_key if it's not defined yet."""

        if op_key not in self.settings:
            self.settings[op_key] = ""


class PowersiPdnModeler(SpdModeler):
    """A powersi class for PDN extraction."""

    # define commonly used TCL cmd
    TCL_FREQ_AFS = "sigrity::update freq -start FREQ_START " + "-end FREQ_END -AFS {!}\n"
    TCL_FREQ_LINSTEP = (
        "sigrity::update freq -freq {FREQ_START, FREQ_END, " + "FREQ_STEP, linear, 3} {!}\n"
    )
    TCL_DIS_ALL_NETS = "sigrity::update net selected 0 -all {!}\n"
    TCL_EN_NETS = "sigrity::update net selected 1 NETNAMES {!}\n"
    TCL_MV2GRP = "sigrity::move net {GRPNETS} NETNAMES {!}\n"
    TCL_CUTBYNET = (
        "sigrity::delete area -Net {PowerNets} NETNAMES {!}\n" + "sigrity::process shape {!}\n"
    )
    TCL_DIS_CAP = "sigrity::update circuit -manual {disable} CKT {!}\n"
    TCL_PORT_AREA = (
        "sigrity::add AreaPort -param {Xmin LLX, Ymin LLY, Xmax URX, Ymax URY, "
        + "Rows 1, Cols 1, Layer 'LAYNAME', PNet 'POSNET', NNet 'NEGNET', "
        + "Index NUMBER, Prefix 'Port_', Type '2D Port', IsGroup 0} {!}\n"
    )
    TCL_PORT_COMP = "sigrity::update circuit -manual {disable} CKT {!}\
        \nsigrity::add port -circuit CKT {!}\
        \nset port_info [sigrity::querydetails port -index {SEQ}]\
        \nset port_name [lindex $port_info 0]\
        \nsigrity::update port -name $port_name -NewName {Port_NUMBER} {!}\n"
    TCL_PORT_LUMPED_GND = "sigrity::add port -circuit NCKT {!} \
        \nset port_info [sigrity::querydetails port -index {SEQ}]\
        \nset port_name [lindex $port_info 0]\
        \nset rail [lindex $port_info 3] \
        \nsigrity::update port -name $port_name -NewName {Port_NUMBER} {!}\
        \nsigrity::delete port -PosNode Port_NUMBER,Node*!!*::$rail {!}\n"
    TCL_PORT_DIFF = "sigrity::add port -name {Port_NUMBER} {!}\n"
    TCL_HOOK_PORT_POS = (
        "sigrity::hook -port {Port_NUMBER} -circuit PCKT " + "-PositiveNode PNODE {!}\n"
    )
    TCL_HOOK_PORT_NEG = (
        "sigrity::hook -port {Port_NUMBER} -circuit NCKT " + "-NegativeNode NNODE {!}\n"
    )
    TCL_IMPORT_OPTION = "sigrity::import option {OPTION_DIR} {!}\n"
    TCL_CUTBYNETPOLY = (
        "sigrity::update net selected 0 GNDNETS {!}\n"
        + "sigrity::cut addCuttingPolygon -Auto -IncludeEnabledSignalShapes {1} {!}\n"
        + "sigrity::delete area -NetToBoundary NETNAMES -PreviewResultFile $sim_spd {!}\n"
        + "sigrity::update net selected 1 GNDNETS {!}\n"
        + "sigrity::process shape {!}\n"
        + "sigrity::delete area unPreview -keepResult 1 {!}\n"
    )

    def __init__(self, info):
        super().__init__(info)
        # define variables
        self.sim_dir = info["sim_dir"]
        self.key2check = info["key2check"]
        self.key2sim = info["key2sim"]
        # define constants
        self.SIM_DONE_FILENAME = "sim.done"
        self.CHECK_DONE_FILENAME = "check.done"
        self.TEMP_RUN_TCL = "temp_run.tcl"
        self.TEMP_CHECK_TCL = "temp_check.tcl"
        self.RUN_TCL = "run.tcl"
        self.RUN_COPY_TCL = "run_" + get_run_time() + ".tcl"
        self.sim_tcl_dir = self.loc_script_dir + self.RUN_TCL
        self.CHECK_TCL = "check.tcl"
        self.CHECK_COPY_TCL = "check_" + get_run_time() + ".tcl"
        self.check_tcl_dir = self.loc_script_dir + self.CHECK_TCL
        self.run_key_dir = info["run_key_dir"]
        self.model_check_dir = info["model_check_dir"]

    # ==========================================================================
    # External methods
    # ==========================================================================

    def mk_tcl(self):
        """make all needed tcls."""
        # make the main check.tcl which contains the generally applied
        # model setup info
        self.__mk_check_tcl(self.key2check)
        # make the main run.tcl which contains the generally applied
        # model setup info
        self.__mk_run_tcl(self.key2sim)
        # make the Key_xxx.tcl which contains the run key specific
        # model setup info
        self._mk_key_tcl()

    # ==========================================================================
    # __mk_check_tcl() related methods
    # ==========================================================================
    def __mk_check_tcl(self, key2check):
        """make the model check tcl"""
        temp_tcl = txtfile_rd(self.template_dir + self.TEMP_CHECK_TCL)
        temp_tcl = temp_tcl.replace("PROC_COMMON_TCL_DIR", self.PROC_COMMON_TCL_DIR)
        temp_tcl = temp_tcl.replace("BOM_TCL_DIR", self.bom_tcl_dir)
        temp_tcl = temp_tcl.replace("SIM_KEY", "\n".join(key2check))
        temp_tcl = temp_tcl.replace("CAP_KEY", "\n".join(self.CAP_KEY))
        temp_tcl = temp_tcl.replace("SPD_DIR", self.parent_spd_dir)
        temp_tcl = temp_tcl.replace("AMM_DIR", self.sig_lib)
        temp_tcl = temp_tcl.replace("RUN_KEY_DIR", self.run_key_dir.replace(SL, "/"))
        temp_tcl = temp_tcl.replace("SIM_DIR", self.model_check_dir.replace(SL, "/"))
        temp_tcl = temp_tcl.replace("SIM_DATE", self.run_name)
        temp_tcl = temp_tcl.replace("RUN_SIM", "false")
        temp_tcl = temp_tcl.replace("EXPORT_PORT", self.EXPORT_PORT)
        temp_tcl = temp_tcl.replace(
            "RUN_DONE", (self.model_check_dir + self.CHECK_DONE_FILENAME).replace(SL, "/")
        )
        # export a tcl script
        txtfile_wr(self.check_tcl_dir, temp_tcl)
        txtfile_wr(self.loc_script_dir + self.CHECK_COPY_TCL, temp_tcl)
        self.lg.debug("check.tcl and its real-time copy are created.")

    # ==========================================================================
    # __mk_run_tcl() related methods
    # ==========================================================================
    def __mk_run_tcl(self, key2sim):
        """make the main run.tcl"""
        temp_tcl = txtfile_rd(self.template_dir + self.TEMP_RUN_TCL)
        temp_tcl = temp_tcl.replace("SIM_KEY", "\n".join(key2sim))
        temp_tcl = temp_tcl.replace("CK_DIR", self.model_check_dir.replace(SL, "/"))
        temp_tcl = temp_tcl.replace("SIM_DIR", self.sim_dir.replace(SL, "/"))
        temp_tcl = temp_tcl.replace("SIM_DATE", self.run_name)
        temp_tcl = temp_tcl.replace(
            "RUN_DONE", (self.sim_dir + self.SIM_DONE_FILENAME).replace(SL, "/")
        )
        # export a tcl script
        txtfile_wr(self.sim_tcl_dir, temp_tcl)
        txtfile_wr(self.loc_script_dir + self.RUN_COPY_TCL, temp_tcl)
        self.lg.debug("run.tcl and its real-time copy are created.")

    # ==========================================================================
    # _mk_key_tcl() related methods
    # ==========================================================================
    def _mk_key_tcl(self):
        """make the key specific tcl"""
        # create key tcl iteratively
        for i_key, i_value in self.sim_input.items():
            self._mk_each_pwr_key_tcl(i_key, i_value, self.CONNECTIVITY[i_key])

    def _mk_each_pwr_key_tcl(self, run_key, info, conn):
        """make the key specific tcl file, overwrite existing ones"""
        filename = "key_" + run_key + ".tcl"
        if not os.path.exists(self.run_key_dir + filename):
            # define variables
            spec_type = self._get_unique_items_in_col(info, self.SPECTYPE)[0]
            net_pos = self._get_unique_items_in_col(info, self.POSNET)
            net_neg = self._get_unique_items_in_col(info, self.NEGNET)
            port_main = self.__rm_empty_port(
                get_cols_out_of_list_of_list(info, [self.POSMP, self.NEGMP])
            )
            port_sns = self.__rm_empty_port(
                get_cols_out_of_list_of_list(info, [self.POSAP, self.NEGAP])
            )
            # determine freq
            freq_list = self._def_freq_list(info, spec_type)
            # nets
            ctnt = ["# enabling and grouping nets\n"]
            ctnt.append(self.TCL_DIS_ALL_NETS)
            ctnt.append(self._en_nets(net_pos, "PowerNets"))
            ctnt.append(self._en_nets(net_neg, "GroundNets"))
            ctnt.append(self._pos_nets_list(net_pos))
            # autocut
            ctnt.append(self._cut_shape(net_pos, net_neg))
            # ports
            ctnt.append(self._set_up_ports(port_main, port_sns, net_pos, net_neg))
            # dns components
            ctnt.append(self._turn_off_dns_ckt())
            # freq range
            ctnt.append(self._set_freq_range(freq_list))
            # config all enabled caps
            ctnt.append(self._config_all_enabled_caps(info))
            # create the run key tcl
            txtfile_wr(self.run_key_dir + filename, "".join(ctnt))
            self.lg.debug(filename + " is created!")
        else:
            self.lg.debug(filename + " already exists. No new key tcl is created!")

    def _def_freq_list(self, info, spec_type):
        """define freq list."""

        # local freq
        if self.OPFREQ not in info[0]:
            local_freq = []
        else:
            local_freq = self._get_unique_items_in_col(info, self.OPFREQ)
        # global freq
        freq_tmp = striped_str2list(self.settings["GLOBALFREQ"], ",")
        global_freq = rm_list_item(freq_tmp, "")
        # output
        freq_list = []
        if local_freq:  # not empty list
            freq_list = local_freq
        else:
            if global_freq:  # not empty list
                freq_list = global_freq
            else:
                freq_list = self._set_freq_by_spectype(spec_type)
        return freq_list

    def _pos_nets_list(self, net):
        """Set a list for all positive nets."""
        ctnt = "set pos_nets {\n" + "\n".join(net) + "\n}\n"
        return ctnt

    def _en_nets(self, net, grp):
        """enable nets and move to a certain group, return string"""
        ctnt = self.TCL_EN_NETS + self.TCL_MV2GRP
        ctnt = ctnt.replace("NETNAMES", " ".join(net))
        ctnt = ctnt.replace("GRPNETS", grp)
        return ctnt

    def _cut_shape(self, net_pos, net_neg):
        """automatically cut shape based on selected cut type.
        CONFORMAL: conformal polygon cut shape
        Any other words: the regular rectangular cut shape
        """
        if self.SHAPE_CUT_TYPE == "CONFORMAL":
            line_tmp = self.__cut_shape_conformal(net_pos, net_neg)
        else:
            line_tmp = self.__cut_shape_rect(net_pos)
        return line_tmp

    def __cut_shape_rect(self, net):
        """automatically cut shape in a rectangular shape."""
        line_tmp = "\n# auto cut\n" + self.TCL_CUTBYNET
        line_tmp = line_tmp.replace("NETNAMES", " ".join(net))
        return line_tmp

    def __cut_shape_conformal(self, net_pos, net_neg):
        """automatically cut conformal polygon shape for selected nets."""
        line_tmp = "\n# auto cut\n" + self.TCL_CUTBYNETPOLY
        net_bracket = ["{" + i + "}" for i in net_pos]
        line_tmp = line_tmp.replace("NETNAMES", " ".join(net_bracket))
        line_tmp = line_tmp.replace("GNDNETS", " ".join(net_neg))
        return line_tmp

    def _set_up_ports(self, port_main, port_sns, net_pos, net_neg):
        """set up all ports, return string"""
        port_lines = []
        i = 0  # port sequence
        # set up main ports
        for i_port in port_main:
            port_lines.append(self._set_port(i_port, i, net_pos, net_neg))
            i = i + 1
        # set up sense ports
        for i_port in port_sns:
            port_lines.append(self._set_port(i_port, i, net_pos, net_neg))
            i = i + 1
        return "".join(port_lines)

    def _set_port(self, port_info, seq, net_pos, net_neg):
        """set up each individual port
        one of the following ports is set up:
        1. component port, pos: 1 single comp not starting with 'C',
           neg: empty
        2. diff port with Lumped GND pins
        3. diff port with specific pins
        4. diff port with pos pins from multiple components, neg pins
           from a component with lumped GND pins
        5. diff port with pos pins from multiple components, neg pins
           from multiple components
        """
        port_num = str(seq + 1)  # starting from 1
        port_seq = str(seq)  # starting from 0
        port_lines = "\n# Port_" + port_num + " definition\n"
        # component or area port
        if port_info[1] == "":
            # area port
            if port_info[0].upper().startswith("REC") & ("{" in port_info[0]):
                areaport_info = self._get_areaport_info(port_info[0], net_pos[0], net_neg[0])
                line_tmp = self.TCL_PORT_AREA
                line_tmp = line_tmp.replace("LLX", areaport_info[0])
                line_tmp = line_tmp.replace("LLY", areaport_info[1])
                line_tmp = line_tmp.replace("URX", areaport_info[2])
                line_tmp = line_tmp.replace("URY", areaport_info[3])
                line_tmp = line_tmp.replace("LAYNAME", areaport_info[4])
                line_tmp = line_tmp.replace("POSNET", areaport_info[5])
                line_tmp = line_tmp.replace("NEGNET", areaport_info[6])
            # component port
            else:
                line_tmp = self.TCL_DIS_CAP + self.TCL_PORT_COMP
                comp = self._map_refdes_n_pin(port_info[0])[0]
                line_tmp = line_tmp.replace("CKT", comp)
                line_tmp = line_tmp.replace("SEQ", port_seq)

            line_tmp = line_tmp.replace("NUMBER", port_num)
        # differntial port which requires pos and neg inputs
        else:
            comp_pos, comp_pin_pos = self.__map_refdes_n_pin_list(port_info[0])
            comp_neg, comp_pin_neg = self.__map_refdes_n_pin_list(port_info[1])
            # 'lumped' appears in the neg
            if "LUMPED" in port_info[1].upper():
                line_tmp = self.TCL_PORT_LUMPED_GND
                for comp_tmp, pin_tmp in zip(comp_pos, comp_pin_pos):
                    line_tmp = line_tmp + self.TCL_HOOK_PORT_POS
                    line_tmp = line_tmp.replace("PCKT", comp_tmp)
                    line_tmp = line_tmp.replace("PNODE", pin_tmp)
                line_tmp = line_tmp.replace("NCKT", comp_neg[0])
                line_tmp = line_tmp.replace("NUMBER", port_num)
                line_tmp = line_tmp.replace("SEQ", port_seq)
            else:
                line_tmp = self.TCL_PORT_DIFF
                for comp_tmp, pin_tmp in zip(comp_pos, comp_pin_pos):
                    line_tmp = line_tmp + self.TCL_HOOK_PORT_POS
                    line_tmp = line_tmp.replace("PCKT", comp_tmp)
                    line_tmp = line_tmp.replace("PNODE", pin_tmp)
                for comp_tmp, pin_tmp in zip(comp_neg, comp_pin_neg):
                    line_tmp = line_tmp + self.TCL_HOOK_PORT_NEG
                    line_tmp = line_tmp.replace("NCKT", comp_tmp)
                    line_tmp = line_tmp.replace("NNODE", pin_tmp)
                line_tmp = line_tmp.replace("NUMBER", port_num)
        port_lines = port_lines + line_tmp
        return port_lines

    def _get_areaport_info(self, port_info, net_pos, net_neg):
        """get the area port info."""
        areaport_info = striped_str2list(re.findall(r"\{(.*?)\}", port_info)[0], ",")
        item_counts = len(areaport_info)
        if item_counts == 5:
            areaport_info.extend([net_pos])
            areaport_info.extend([net_neg])
        elif item_counts == 6:
            areaport_info.extend([net_neg])
        elif item_counts == 7:
            pass
        else:
            raise WrongAreaPortDef(self.lg)
        return areaport_info

    def _map_refdes_n_pin(self, raw_port):
        """get the refdes and pins from port input"""
        port = list_strip(raw_port.split(","))
        comp = port[0]
        if comp in self.solder_refdes:
            comp = self.solder_refdes[comp]
        if len(port) > 1:
            comp_pin = " ".join(port[1:])
        else:
            comp_pin = ""
        return comp, comp_pin

    def __map_refdes_n_pin_list(self, raw_port):
        """get lists of the refdes and pins from port input"""
        port_list = list_strip(raw_port.split(";"))
        comp = []
        comp_pin = []
        for port in port_list:
            comp_tmp, comp_pin_tmp = self._map_refdes_n_pin(port)
            comp.append(comp_tmp)
            comp_pin.append(comp_pin_tmp)
        return comp, comp_pin

    def _turn_off_dns_ckt(self):
        """turn off dns components"""
        cmd_tcl = (
            "# turn off DNS components\n"
            + "set bom_exists [info exists bom]\n"
            + "if {$bom_exists} {\n"
            + "    set refdes_en "
            + "[sigrity::query -cktInstance -option {type(good)}]\n"
            + "    turn_off_dns_ckt $refdes_en $bom\n"
            + "}\n"
        )
        return cmd_tcl

    def _set_freq_by_spectype(self, spec_type):
        """determine freq range by spec_type."""
        freq_list = []
        if spec_type.upper().startswith("Z"):
            freq_list = FREQ_RANGE["Z"]
        else:
            freq_list = FREQ_RANGE[spec_type.upper()]
        return freq_list

    def _set_freq_range(self, freq_list):
        """set up freq range."""
        line_header = "\n# set up freq range\n"
        line = ""
        if len(freq_list) == 2:  # PDN freq
            line = self.TCL_FREQ_AFS
            line = line.replace("FREQ_START", str(freq_list[0]))
            line = line.replace("FREQ_END", str(freq_list[1]))
        elif len(freq_list) == 3:  # LSIO freq
            line = self.TCL_FREQ_LINSTEP
            line = line.replace("FREQ_START", str(freq_list[0]))
            line = line.replace("FREQ_END", str(freq_list[1]))
            line = line.replace("FREQ_STEP", str(freq_list[2]))
        return line_header + line

    def _config_all_enabled_caps(self, info):
        """Configurate all enabled caps, on or off."""
        if self.OPDISALLCAPS not in info[0]:
            dis_allcaps = False
        else:
            discaps_list = self._get_unique_items_in_col(info, self.OPDISALLCAPS)
            if discaps_list:
                dis_allcaps = True
            else:
                dis_allcaps = False
        if dis_allcaps:
            line = "\n# turn off all enabled caps." + "\nturn_off_all_enabled_caps\n"
        else:
            line = ""
        return line

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

    def __rm_empty_port(self, in_list):
        """remove a port if its definition is empty"""
        out_list = [tmp for tmp in in_list if tmp[0] != ""]
        return out_list


class PowersiIOModeler(PowersiPdnModeler):
    """Extract LSIO S-para using PowerSI.
    The ports must be defined using refdes + pins.
    """

    TCL_REORDER_PORTS_SIMPLE = (
        "sigrity::Rearrange PortOrder -PortName " + "{PORT_NAME_SEQ} -Index {PORT_NAME_INDEX} {!}\n"
    )

    def __init__(self, info):
        super().__init__(info)

    # ==========================================================================
    # _mk_key_tcl() related methods
    # ==========================================================================
    def _mk_each_pwr_key_tcl(self, run_key, info, conn):
        """make the key specific tcl file, overwrite existing ones"""
        filename = "key_" + run_key + ".tcl"
        if not os.path.exists(self.run_key_dir + filename):
            ctnt = ["# set up port one by one\n"]
            # set up ports
            ctnt.append(self._set_up_ports(info, conn))
            # define variables
            spec_type = self._get_unique_items_in_col(info, self.SPECTYPE)[0]
            net_pos = self._get_unique_items_in_col(info, self.POSNET)
            net_neg = self._get_unique_items_in_col(info, self.NEGNET)
            # determine freq
            freq_list = self._def_freq_list(info, spec_type)
            # enable all nets together
            ctnt.append("# enable and group nets for all\n")
            ctnt.append(self.TCL_DIS_ALL_NETS)
            ctnt.append(self._en_nets(net_pos, "NULL"))  # signal net group
            ctnt.append(self._en_nets(net_neg, "GroundNets"))
            ctnt.append(self._pos_nets_list(net_pos))
            # autocut
            ctnt.append(self._cut_shape(net_pos, net_neg))
            # dns components
            ctnt.append(self._turn_off_dns_ckt())
            # freq range
            ctnt.append(self._set_freq_range(freq_list))
            # config all enabled caps
            ctnt.append(self._config_all_enabled_caps(info))
            # create the run key tcl
            txtfile_wr(self.run_key_dir + filename, "".join(ctnt))
            self.lg.debug(filename + " is created!")
        else:
            self.lg.debug(filename + " already exists. No new key tcl is created!")

    def _set_up_ports(self, info, conn):
        """set up all ports, return string"""
        port_lines = []
        # set up ports
        port_count = 0
        port_status = 1
        for i_info, i_conn in zip(info, conn["IL"]):
            def_port, port_count, port_match = self._set_port(i_info, i_conn, port_count)
            port_lines.append(def_port)
            port_status = port_status & port_match
        # reorder ports
        port_all = []
        for i_port in conn["IL"]:
            port_all.extend(i_port)
        port_total = max(port_all)
        port_name_seq = " ".join(["Port_" + str(i + 1) for i in range(port_total)])
        port_name_index = " ".join([str(i + 1) for i in range(port_total)])
        if not port_status:
            line = self.TCL_REORDER_PORTS_SIMPLE
            line = line.replace("PORT_NAME_SEQ", port_name_seq)
            line = line.replace("PORT_NAME_INDEX", port_name_index)
            port_lines.append(line)
        return "".join(port_lines)

    def _set_port(self, info, port_num_list, port_count):
        """Assume refdes and pins for both positive and negative sides are
        provided to create a port.
        """
        # nets
        net_pos = self._get_unique_items_in_col([info], self.POSNET)
        net_neg = self._get_unique_items_in_col([info], self.NEGNET)
        ctnt = ["# enabling and grouping nets\n"]
        ctnt.append(self.TCL_DIS_ALL_NETS)
        ctnt.append(self._en_nets(net_pos, "NULL"))  # signal net group
        ctnt.append(self._en_nets(net_neg, "GroundNets"))
        # ports
        port_status = 1
        # Main ports
        mp_pos = info[self.POSMP]
        mp_neg = info[self.NEGMP]
        if mp_pos != "":
            port_count = port_count + 1
            port_num = str(port_num_list[0])
            port_status = port_status & (port_count == port_num_list[0])
            # area port
            if mp_pos.upper().startswith("REC") & ("{" in mp_pos):
                areaport_info = self._get_areaport_info(mp_pos, net_pos[0], net_neg[0])
                line_tmp = self.TCL_PORT_AREA
                line_tmp = line_tmp.replace("LLX", areaport_info[0])
                line_tmp = line_tmp.replace("LLY", areaport_info[1])
                line_tmp = line_tmp.replace("URX", areaport_info[2])
                line_tmp = line_tmp.replace("URY", areaport_info[3])
                line_tmp = line_tmp.replace("LAYNAME", areaport_info[4])
                line_tmp = line_tmp.replace("POSNET", areaport_info[5])
                line_tmp = line_tmp.replace("NEGNET", areaport_info[6])
                line_tmp = line_tmp.replace("NUMBER", port_num)
            # component port
            else:
                comp_pos, comp_pin_pos = self._get_refdes_n_pins(mp_pos)
                comp_neg, comp_pin_neg = self._get_refdes_n_pins(mp_neg)

                line_tmp = self.TCL_PORT_DIFF + self.TCL_HOOK_PORT_POS + self.TCL_HOOK_PORT_NEG
                line_tmp = line_tmp.replace("NUMBER", port_num)
                line_tmp = line_tmp.replace("NCKT", comp_neg)
                line_tmp = line_tmp.replace("NNODE", " ".join(comp_pin_neg))
                line_tmp = line_tmp.replace("PCKT", comp_pos)
                line_tmp = line_tmp.replace("PNODE", " ".join(comp_pin_pos))

            ctnt.append("# define Port " + port_num + "\n")
            ctnt.append(line_tmp)
        # Aux ports
        ap_pos = info[self.POSAP]
        ap_neg = info[self.NEGAP]
        if ap_pos != "":
            port_count = port_count + 1
            port_num = str(port_num_list[1])
            port_status = port_status & (port_count == port_num_list[1])
            # area port
            if ap_pos.upper().startswith("REC") & ("{" in ap_pos):
                areaport_info = self._get_areaport_info(ap_pos, net_pos[0], net_neg[0])
                line_tmp = self.TCL_PORT_AREA
                line_tmp = line_tmp.replace("LLX", areaport_info[0])
                line_tmp = line_tmp.replace("LLY", areaport_info[1])
                line_tmp = line_tmp.replace("URX", areaport_info[2])
                line_tmp = line_tmp.replace("URY", areaport_info[3])
                line_tmp = line_tmp.replace("LAYNAME", areaport_info[4])
                line_tmp = line_tmp.replace("POSNET", areaport_info[5])
                line_tmp = line_tmp.replace("NEGNET", areaport_info[6])
                line_tmp = line_tmp.replace("NUMBER", port_num)
            # component port
            else:
                comp_pos, comp_pin_pos = self._get_refdes_n_pins(ap_pos)
                comp_neg, comp_pin_neg = self._get_refdes_n_pins(ap_neg)

                line_tmp = self.TCL_PORT_DIFF + self.TCL_HOOK_PORT_POS + self.TCL_HOOK_PORT_NEG
                line_tmp = line_tmp.replace("NUMBER", port_num)
                line_tmp = line_tmp.replace("NCKT", comp_neg)
                line_tmp = line_tmp.replace("NNODE", " ".join(comp_pin_neg))
                line_tmp = line_tmp.replace("PCKT", comp_pos)
                line_tmp = line_tmp.replace("PNODE", " ".join(comp_pin_pos))

            ctnt.append("# define Port " + port_num + "\n")
            ctnt.append(line_tmp)

        ctnt.append("\n")
        return "".join(ctnt), port_count, port_status


class ClarityModeler(PowersiIOModeler):
    """Run FEM simulations using Clarity.
    Only component ports are supported for both primary and sense ports.
    """

    TCL_PORT_FEM_LISTS = (
        "set refdes_list [split_component SINGLE_REFDES]\n"
        + "foreach refdes $refdes_list {\n"
        + "    TCL_PORT_FEM"
        + "}\n"
    )
    TCL_PORT_FEM = (
        "sigrity::add 3DFEMPort -circuit $refdes "
        + "-PortType {coaxial} -AddSolderBallBump {1} "
        + "-GeneratePortsForEnabledNets {1} -AntipadSize {ASR} "
        + "-LumpPortHeight {0.0003} "
        + "-SolderBallConductivity {7e+06} -SolderBallDiameter {SBD} "
        + "-SolderBallHeight {SBH} -PowerNetsOption {0} "
        + "-RefLayerThickness {0.000002} {!}\n"
    )
    TCL_PORT_FEM_SCALEPAD = (
        "sigrity::add 3DFEMPort -circuit $refdes "
        + "-PortType {coaxial} -AddSolderBallBump {1} "
        + "-GeneratePortsForEnabledNets {1} -AntipadSize {ASR} "
        + "-UsePadSizeAsDiameter {RATIO} -LumpPortHeight {0.0003} "
        + "-SolderBallConductivity {7e+06} "
        + "-SolderBallHeight {SBH} -PowerNetsOption {0} "
        + "-RefLayerThickness {0.000002} {!}\n"
    )
    TCL_FREQ_FULLWAVE = (
        "sigrity::update option -Wave3DSettingsolutionfreq "
        + "{FREQ_SOL} -Wave3DFreqBand "
        + "{{FREQ_START FREQ_END linear FREQ_STEP}} "
        + "-Wave3DRefleshFList {1} {!}\n"
    )
    TCL_COMPUTE_RESOURCE = (
        "sigrity::update DynamicClarity3dResource -smt 0 "
        + "-local -cn localhost -cpus CORENUM -autoresume false "
        + "-resume false -finalonly false {!}\n"
    )
    TCL_UPDATE_3DFEM_FLOW = (
        "sigrity::update workflow -product {Clarity 3D "
        + "Layout} -workflowkey {3DFEMExtraction} {!}\n"
    )

    def __init__(self, info):
        super().__init__(info)
        # define constants
        self.CLARITY_OPTION = expand_home_dir(self.sig_config_dict["CLARITY_OPTION"])
        self.CORE_NUM = self.sig_config_dict["CORE_NUM"]
        # solder height in mm, diameter to pad size ratio
        self.DF_SOLDER = self.sig_config_dict["DEFAULT_SOLDER"]
        # FEM port antipad ratio
        self.DF_ANTIPAD = self.sig_config_dict["DEFAULT_ANTIPAD"]
        self.BOT_LAYER_INDEX = 1
        self.TOP_LAYER_INDEX = len(self.stackup) - 3
        # define optional keywords
        self.optional_key_list.extend(
            [
                "FEMPORTSOLDER",
            ]
        )
        for op_key in self.optional_key_list:
            self._init_optional_setting_key(op_key)
        self.TEMP_REORDER_PORTS_TCL = "temp_reorder_ports.tcl"
        self.TEMP_MULTITERM_CKT_TCL = "temp_multiterm_ckt.tcl"
        self.TCL_REORDER_PORTS = txtfile_rd(self.template_dir + self.TEMP_REORDER_PORTS_TCL)
        self.TCL_MULTITERM_CKT = txtfile_rd(self.template_dir + self.TEMP_MULTITERM_CKT_TCL)
        self.SOLVER = "clarity3dlayout"

    # ==========================================================================
    # _mk_key_tcl() related methods
    # ==========================================================================

    def _mk_each_pwr_key_tcl(self, run_key, info, conn):
        """make the key specific tcl file, overwrite existing ones"""
        filename = "key_" + run_key + ".tcl"
        if not os.path.exists(self.run_key_dir + filename):
            # define variables
            spec_type = self._get_unique_items_in_col(info, self.SPECTYPE)[0]
            net_pos = self._get_unique_items_in_col(info, self.POSNET)
            net_neg = self._get_unique_items_in_col(info, self.NEGNET)
            # determine freq
            freq_list = self._def_freq_list(info, spec_type)
            # switch to clarity3dlayout flow
            ctnt = ["# clarity3dlayout workflow\n"]
            ctnt.append(self.TCL_UPDATE_3DFEM_FLOW)
            # import clarity option
            ctnt.append("\n# import the option from team drive\n")
            ctnt.append(self.TCL_IMPORT_OPTION.replace("OPTION_DIR", self.CLARITY_OPTION))
            # nets
            ctnt.append("\n# enabling and grouping nets\n")
            ctnt.append(self.TCL_DIS_ALL_NETS)
            ctnt.append(self._en_nets(net_pos, "NULL"))  # signal net group
            ctnt.append(self._en_nets(net_neg, "GroundNets"))
            ctnt.append(self._pos_nets_list(net_pos))
            # autocut
            ctnt.append(self._cut_shape(net_pos, net_neg))
            # multi-terminal circuits at bottom
            ctnt.append(self.__add_multiterm_ckt(self.BOT_LAYER_INDEX, "Down"))
            # multi-terminal circuits at top
            ctnt.append(self.__add_multiterm_ckt(self.TOP_LAYER_INDEX, "Up"))
            # ports
            ctnt.append(self._set_up_ports(info))
            # dns components
            ctnt.append(self._turn_off_dns_ckt())
            # freq range
            ctnt.append(self._set_freq_range(freq_list))
            # config all enabled caps
            ctnt.append(self._config_all_enabled_caps(info))
            # set up compute resources
            ctnt.append("\n# set up compute resources\n")
            ctnt.append(self.TCL_COMPUTE_RESOURCE.replace("CORENUM", str(self.CORE_NUM)))
            # create the run key tcl
            txtfile_wr(self.run_key_dir + filename, "".join(ctnt))
            self.lg.debug(filename + " is created!")
        else:
            self.lg.debug(filename + " already exists. No new key tcl is created!")

    def _set_up_ports(self, info):
        """set up ports and re-order them as specified in the gSheet"""
        lines = "\n# define all ports using components\n"
        # create all ports, assume only component ports
        comp = self._get_unique_items_in_col(info, self.POSMP)
        comp.extend(self._get_unique_items_in_col(info, self.POSAP))
        comp = unique_list(comp)
        lines = lines + self.__set_all_sig_ports(comp)
        # reorder all ports
        lines = lines + self.__reorder_ports(info)
        return lines

    def __set_all_sig_ports(self, comp):
        """set up all signal ports using components"""
        # only component port is assumed
        ports = []
        for i_comp in comp:
            ports.append(self.__set_fem_port(i_comp))
        return "".join(ports)

    def __set_fem_port(self, comp):
        """set up FEM port using a component"""
        fem_port_solder = str2dict(self.settings["FEMPORTSOLDER"], ";", ",")
        if comp in fem_port_solder:
            # mm to m
            SBH = str(float(fem_port_solder[comp][0]) * 1e-3)
            # mm to m and radius to diameter
            SBD = str(float(fem_port_solder[comp][1]) * 1e-3 * 2)
            lines = self.TCL_PORT_FEM
            lines = lines.replace("SBD", SBD)
        else:
            SBH = str(self.DF_SOLDER[0] * 1e-3)
            RATIO = str(self.DF_SOLDER[1])
            lines = self.TCL_PORT_FEM_SCALEPAD
            lines = lines.replace("RATIO", RATIO)
        lines = lines.replace("SBH", SBH)
        lines = lines.replace("ASR", str(self.DF_ANTIPAD))
        # netlist lines
        tcl_lines = self.TCL_PORT_FEM_LISTS
        tcl_lines = tcl_lines.replace("TCL_PORT_FEM", lines)
        tcl_lines = tcl_lines.replace("SINGLE_REFDES", comp)
        return tcl_lines

    def __reorder_ports(self, info):
        """rename and reorder ports"""
        # prepare info to insert into the template
        # port list
        port_tmp = []
        for port in info:
            if port[self.POSMP] != "":
                net = " ".join(list_strip(port[self.POSNET].split(",")))
                port_tmp.append("{" + port[self.POSMP] + " " + net + "}")
        for port in info:
            if port[self.POSAP] != "":
                net = " ".join(list_strip(port[self.POSNET].split(",")))
                port_tmp.append("{" + port[self.POSAP] + " " + net + "}")
        port_list = "\n".join(port_tmp)
        # port name amd index
        port_name_tmp = []
        port_index_tmp = []
        for i in range(len(port_tmp)):
            port_name_tmp.append("Port_" + str(i + 1))
            port_index_tmp.append(str(i + 1))
        port_name_seq = " ".join(port_name_tmp)
        port_name_index = " ".join(port_index_tmp)
        # generate lines
        line = self.TCL_REORDER_PORTS
        line = line.replace("COMP_NETS_LISTS", port_list)
        line = line.replace("PORT_NAME_SEQ", port_name_seq)
        line = line.replace("PORT_NAME_INDEX", port_name_index)
        return line

    def _set_freq_range(self, freq_list):
        """set up freq range"""
        line_header = "\n# set up freq range\n"
        line = ""
        if len(freq_list) == 2:  # PDN freq
            line = self.TCL_FREQ_AFS
            line = line.replace("FREQ_START", str(freq_list[0]))
            line = line.replace("FREQ_END", str(freq_list[1]))
        elif len(freq_list) == 3:  # LSIO freq
            line = self.TCL_FREQ_LINSTEP
            line = line.replace("FREQ_START", str(freq_list[0]))
            line = line.replace("FREQ_END", str(freq_list[1]))
            line = line.replace("FREQ_STEP", str(freq_list[2]))
        elif len(freq_list) == 4:  # HSIO freq:
            line = self.TCL_FREQ_FULLWAVE
            line = line.replace("FREQ_START", str(freq_list[0]))
            line = line.replace("FREQ_END", str(freq_list[1]))
            line = line.replace("FREQ_STEP", str(freq_list[2]))
            line = line.replace("FREQ_SOL", str(freq_list[3]))
        return line_header + line

    def __add_multiterm_ckt(self, layer_index, orientation):
        """Add multi-terminal circuit for top or bottom layer
        components.
        """
        SBH = str(self.DF_SOLDER[0] * 1e-3)
        RATIO = str(self.DF_SOLDER[1])
        line = self.TCL_MULTITERM_CKT
        line = line.replace("LAYERINDEX", str(layer_index))
        line = line.replace("ORIENTATION", orientation)
        line = line.replace("RATIO", RATIO)
        line = line.replace("SBH", SBH)
        return line


class PowerdcModeler(PowersiPdnModeler):
    """A powerdc class for DCR extraction.
    Assumptions:
        1. All definitions in the same workbook will be simulated together,
        i.e. each workbook is a sim key.
        2. For each rail key, there can be only 1 sink defined, but multiple
        VRMs are allowed.
        3. Sinks can be defined using either one refdes or positive/negative
        refdes + pins.
        4. VRMs can only be defined using positive/negative refdes + pins.
        5. Two sink pin group types are supported and are specified using
        spec types:
            Rl2l: lumped to lumped (PWR to GND)
            Rm2l: multiple to lumped (PWR to GND)
    """

    TCL_VRM_AUTO = "sigrity::add pdcVRM -auto -net {PWRNET,GNDNET} -ckt {CKT} {!}\n"
    TCL_VRM_MAN = (
        "sigrity::add pdcVRM -manual -name {VRM_KEYNAME} "
        + "-sensevoltage {0} -resistance {0} -tolerance {0} "
        + "-outputCurrent {0} -voltage {0} {!}\n"
        + "sigrity::link pdcElem {VRM_KEYNAME} {Positive Pin}  "
        + "POSPINS -LinkCktNode {!}\n"
        + "sigrity::link pdcElem {VRM_KEYNAME} {Negative Pin}  "
        + "NEGPINS -LinkCktNode {!}\n"
    )
    TCL_RESI_AUTO = (
        "sigrity::add pdcResist -auto -ckt {REFDES} -model "
        + "{PINGRPTYPE} -short {1} -otherCkt {1} {!}\n"
    )
    TCL_RESI_MAN = (
        "sigrity::add pdcResist -manual -name {RESI_KEYNAME} "
        + "-model {PINGRPTYPE} -short {1} -otherCkt {1} {!}\n"
        + "sigrity::link pdcElem {RESI_KEYNAME} {Positive Pin}  "
        + "POSPINS -LinkCktNode {!}\n"
        + "sigrity::link pdcElem {RESI_KEYNAME} {Negative Pin}  "
        + "NEGPINS -LinkCktNode {!}\n"
    )
    TCL_MAN_PINS = "{-Circuit {REFDES} -Node {PIN}}"
    TCL_UPDATE_RESI_FLOW = (
        "sigrity::update workflow -product {PowerDC} "
        + "-workflowkey {ResistanceMeasurement} {!}\n"
        + "sigrity::set pdcSimMode -ResistanceMeasurement {1} {!}\n"
    )

    def __init__(self, info):
        super().__init__(info)
        # define variables
        self.PDC_OPTION = expand_home_dir(self.sig_config_dict["PDC_OPTION"])
        self.dcr_dict = info["dcr_dict"]
        self.SOLVER = "powerdc"

    # ==========================================================================
    # _mk_key_tcl() related methods
    # ==========================================================================

    def _mk_key_tcl(self):
        """make the key specific tcl"""
        # all available keys
        for i_key, i_value in self.dcr_dict.items():
            self._mk_each_pwr_key_tcl(i_key, i_value)

    def _mk_each_pwr_key_tcl(self, run_key, info):
        """make the key specific tcl file, overwrite existing ones"""
        filename = "key_" + run_key + ".tcl"
        if not os.path.exists(self.run_key_dir + filename):
            # switch workflow
            ctnt = ["# powerdc resistance measurement workflow\n"]
            ctnt.append(self.TCL_UPDATE_RESI_FLOW)
            # import the option from team drive
            ctnt.append("# import the option from team drive\n")
            ctnt.append(self.TCL_IMPORT_OPTION.replace("OPTION_DIR", self.PDC_OPTION))
            # set up sink and VRM for each rail
            net_pos = []
            net_neg = []
            for i_key in info:
                rail_cmd, i_net_pos, i_net_neg = self.__set_each_rail_sinknvrm(i_key)
                ctnt.append(rail_cmd)
                net_pos.extend(i_net_pos)
                net_neg.extend(i_net_neg)
            net_pos = unique_list(net_pos)
            net_neg = unique_list(net_neg)
            # enable all nets together
            ctnt.append("# enable and group nets for all\n")
            ctnt.append(self.TCL_DIS_ALL_NETS)
            ctnt.append(self._en_nets(net_pos, "PowerNets"))
            ctnt.append(self._en_nets(net_neg, "GroundNets"))
            ctnt.append(self._pos_nets_list(net_pos))
            # autocut
            ctnt.append(self._cut_shape(net_pos, net_neg))
            # create the run key tcl
            txtfile_wr(self.run_key_dir + filename, "".join(ctnt))
            self.lg.debug(filename + " is created!")
        else:
            self.lg.debug(filename + " already exists. No new key tcl is created!")

    def __set_each_rail_sinknvrm(self, rail_key):
        """Set up sink and VRMs for each rail."""
        info = self.sim_input[rail_key]
        net_pos = self._get_unique_items_in_col(info, self.POSNET)
        net_neg = self._get_unique_items_in_col(info, self.NEGNET)

        ctnt = ["# Set up sink and VRMs for " + rail_key + "\n"]
        # enable and group nets
        ctnt.append("# enable and group nets\n")
        ctnt.append(self.TCL_DIS_ALL_NETS)
        ctnt.append(self._en_nets(net_pos, "PowerNets"))
        ctnt.append(self._en_nets(net_neg, "GroundNets"))
        # set up sink, only 1 sink is allowed per rail
        ctnt.append("# add sink\n")
        sink_info = [info[0][self.POSMP], info[0][self.NEGMP]]
        spec_type = info[0][self.SPECTYPE]
        if spec_type == "Rl2l":
            pin_grp_type = "Lumped to Lumped"
        elif spec_type == "Rm2l":
            pin_grp_type = "Multiple to Lumped"
        else:
            pin_grp_type = "Lumped to Lumped"

        if sink_info[1]:
            tmp_sink = self.TCL_RESI_MAN
            tmp_sink = tmp_sink.replace("KEYNAME", rail_key)
            tmp_sink = tmp_sink.replace("PINGRPTYPE", pin_grp_type)
            tmp_sink = tmp_sink.replace("POSPINS", self.__set_pins_manually(sink_info[0]))
            tmp_sink = tmp_sink.replace("NEGPINS", self.__set_pins_manually(sink_info[1]))
        else:
            tmp_sink = self.TCL_RESI_AUTO
            tmp_sink = tmp_sink.replace("REFDES", sink_info[0])
            tmp_sink = tmp_sink.replace("PINGRPTYPE", pin_grp_type)
        ctnt.append(tmp_sink)
        # set up VRM, multi-VRMs are supported, both pos and neg pins must be
        # provided.
        ctnt.append("# add VRM\n")
        vrm_info = get_cols_out_of_list_of_list(info, [self.POSAP, self.NEGAP])
        all_vrm = []
        i = 1
        for i_vrm in vrm_info:
            tmp_vrm = self.TCL_VRM_MAN
            tmp_vrm = tmp_vrm.replace("KEYNAME", rail_key + str(i))
            tmp_vrm = tmp_vrm.replace("POSPINS", self.__set_pins_manually(i_vrm[0]))
            tmp_vrm = tmp_vrm.replace("NEGPINS", self.__set_pins_manually(i_vrm[1]))
            all_vrm.append(tmp_vrm)
            i += 1
        ctnt.append("".join(all_vrm))
        ctnt.append("\n")
        return "".join(ctnt), net_pos, net_neg

    def __set_pins_manually(self, info):
        """Come up with a string of the selected pins in a format that
        is needed by TCL.
        """
        refdes, pins = self._get_refdes_n_pins(info)
        ctnt = []
        for pin in pins:
            line = self.TCL_MAN_PINS
            line = line.replace("REFDES", refdes)
            line = line.replace("PIN", pin)
            ctnt.append(line)
        return " ".join(ctnt)
