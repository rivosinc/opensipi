# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
Author: yanshengw@
Last updated on Nov. 21, 2023

Description:
    This module contains constants commonly used by OpenSIPI.
"""


INPUT_FILE_STARTSWITH = [
    "SIM",
    "SPECIAL_SETTINGS",
    "STACKUP_MATERIALS",
]

SIM_INPUT_COL_TITLE = [
    "UNIQUE_KEY",
    "CHECK_BOX",
    "SPEC_TYPE",
    "POSITIVE_NETS",
    "NEGATIVE_NETS",
    "POSITIVE_MAIN_PORTS",
    "NEGATIVE_MAIN_PORTS",
    "POSITIVE_AUX_PORTS",
    "NEGATIVE_AUX_PORTS",
    "OP_FREQ",
    "OP_DIFFPAIR",
]

FREQ_RANGE = {
    # PDN, PowerSI
    # AFS [FREQ_START, FREQ_END]
    "Z": [0, 1e9],
    # LSIO, PowerSI
    # linear step [FREQ_START, FREQ_END, FREQ_STEP]
    "SLS": [1e6, 5e9, 5e6],
    # HSIO, Clarity
    # linear step [FREQ_START, FREQ_END, FREQ_STEP, FREQ_SOL]
    "SDDR5": [1e6, 15e9, 100e6, 5e9],
    # linear step [FREQ_START, FREQ_END, FREQ_STEP, FREQ_SOL]
    "SPCIE6": [1e6, 50e9, 100e6, 16e9],
}
