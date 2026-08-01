# SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Characterization tests for OpenSIPI's input vocabulary."""

import pytest

from opensipi.constants.CONSTANTS import (
    INPUT_FILE_STARTSWITH,
    POST_PROCESS_KEY_ORDER_IO,
    POST_PROCESS_KEY_ORDER_PDN,
    SIM_INPUT_COL_TITLE,
    SPEC_TYPE,
)


def test_input_file_prefixes_are_exact_and_positional():
    assert INPUT_FILE_STARTSWITH == [
        "SIM",
        "SPECIAL_SETTINGS",
        "STACKUP_MATERIALS",
        "SPEC_TYPE",
    ]


def test_sim_input_columns_are_exact_and_positional():
    assert SIM_INPUT_COL_TITLE == [
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


@pytest.mark.parametrize(
    ("spec_types", "frequency_count"),
    [
        (("ZPDN", "ZL"), 2),
        (("SLS", "SLS_MM"), 3),
        (("SDDR5", "SPCIE6"), 4),
    ],
)
def test_spec_type_frequency_lengths_match_extraction_kind(spec_types, frequency_count):
    assert {len(SPEC_TYPE[name]["FREQ"]) for name in spec_types} == {frequency_count}


@pytest.mark.parametrize(
    "order",
    [POST_PROCESS_KEY_ORDER_PDN, POST_PROCESS_KEY_ORDER_IO],
    ids=["pdn", "io"],
)
def test_post_process_ranks_are_unique_and_contiguous(order):
    ranks = list(order.values())
    assert len(ranks) == len(set(ranks))
    assert sorted(ranks) == list(range(len(ranks)))
