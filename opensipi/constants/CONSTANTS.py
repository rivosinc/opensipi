# SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
Author: yanshengw@
Last updated on Sep. 9, 2025

Description:
    This module contains constants commonly used by OpenSIPI.

    These constants are the vocabulary the input sheets are written in, so
changing one changes what users must type in their tables.

Attributes:
    INPUT_FILE_STARTSWITH (list of str): The four recognized sheet name
        patterns, in the fixed order ``[sim, special settings, stackup and
        materials, spec type]``. Consumers index this list positionally, so
        the order matters as much as the values. A sheet name is matched
        upper-cased, by prefix for the sim sheets and exactly for the other
        three.
    SIM_INPUT_COL_TITLE (list of str): The upper-cased column titles of a sim
        sheet. Also indexed positionally, e.g. index 1 is ``"CHECK_BOX"``, the
        column deciding whether a simulation is enabled.
    SPEC_TYPE (dict): The built-in spec types, mapping an upper-cased spec type
        name to its ``"FREQ"`` and ``"POST_PROCESS_KEY"`` definition. The
        length of ``"FREQ"`` follows the extraction type it serves:
        ``[FREQ_START, FREQ_END]`` for the PDN entries, which sweep
        adaptively; ``[..., FREQ_STEP]`` for the LSIO entries; and
        ``[..., FREQ_STEP, FREQ_SOL]`` for the HSIO entries, which also need a
        solution frequency. A user-supplied spec type sheet adds to or
        overrides this mapping.
    POST_PROCESS_KEY_ORDER_PDN (dict): Post-processing key to its sort rank,
        used to present PDN results in a stable order regardless of the order
        the keys were written in the input.
    POST_PROCESS_KEY_ORDER_IO (dict): The same, for the HSIO and LSIO results.
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
    "OP_PRECUT",
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
