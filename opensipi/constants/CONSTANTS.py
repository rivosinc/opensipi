# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
Author: yanshengw@
Last updated on Mar. 31, 2025

Description:
    This module contains constants commonly used by OpenSIPI.
"""


INPUT_FILE_STARTSWITH = [
    "SIM",
    "SPECIAL_SETTINGS",
    "STACKUP_MATERIALS",
    "SPEC_TYPE",
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
    "OP_DISALLCAPS",
    "OP_MIXEDMODETERM",
]


SPEC_TYPE = {
    # PDN, PowerSI
    # AFS [FREQ_START, FREQ_END]
    "ZPDN": {
        "FREQ": [0, 1e9],
        "POST_PROCESS_KEY": ["ZOPEN", "ZSHORT"],
    },
    "ZL": {
        "FREQ": [0, 1e9],
        "POST_PROCESS_KEY": ["ZSHORT"],
    },
    # LSIO, PowerSI
    # linear step [FREQ_START, FREQ_END, FREQ_STEP]
    "SLS": {
        "FREQ": [1e6, 5e9, 5e6],
        "POST_PROCESS_KEY": ["IL", "RL"],
    },
    "SLS_MM": {
        "FREQ": [1e6, 5e9, 5e6],
        "POST_PROCESS_KEY": ["IL", "RL", "TDR", "IL_MM", "RL_MM", "TDR_MM"],
    },
    # HSIO, Clarity
    # linear step [FREQ_START, FREQ_END, FREQ_STEP, FREQ_SOL]
    "SDDR5": {
        "FREQ": [1e6, 15e9, 100e6, 5e9],
        "POST_PROCESS_KEY": ["IL", "RL"],
    },
    "SPCIE6": {
        "FREQ": [1e6, 50e9, 100e6, 16e9],
        "POST_PROCESS_KEY": ["IL", "RL", "IL_MM", "RL_MM"],
    },
}


POST_PROCESS_KEY_ORDER_PDN = {
    "ZOPEN": 0,
    "ZSHORT": 1,
}


POST_PROCESS_KEY_ORDER_IO = {
    "IL": 0,
    "RL": 1,
    "TDR": 2,
    "IL_MM": 3,
    "RL_MM": 4,
    "TDR_MM": 5,
}
