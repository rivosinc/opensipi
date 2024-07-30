# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
Author: yanshengw@
Last updated on Jan. 5, 2024

Description:
    This is the main function for Project Olympus to auto extract PCB
    S-para for PDN purposes.
"""


from opensipi.integrated_flows import sim2report

input_info = {
    "input_dir": r"C:\SIPIProj\Olympus\Sim_Input" + "\\",
    "input_type": "csv",
    "input_folder": "Sigrity_LSIO",
    "op_run_name": "",
}

mntr_info = {
    "email": "",
    "op_pause_after_model_check": 1,
}

sim2report(input_info, mntr_info)
