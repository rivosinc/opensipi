# SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Characterization tests for positional report template structure."""

from copy import deepcopy

import pytest

from opensipi.constants.CONSTANTS import (
    POST_PROCESS_KEY_ORDER_IO,
    POST_PROCESS_KEY_ORDER_PDN,
)
from opensipi.templates import temp_report


@pytest.mark.parametrize("template_name", ["pdn_report", "io_report"])
def test_report_templates_have_summary_tables_and_figure_sections(template_name):
    report = deepcopy(getattr(temp_report, template_name))
    assert len(report["sections"]) == 3
    summary, tables, figures = report["sections"]
    assert summary["content"][0]["table"][0][0][".b"] == "Report"
    assert tables["content"]
    assert figures["content"] == []


@pytest.mark.parametrize(
    ("template_name", "order", "expected_headers"),
    [
        (
            "pdn_report",
            POST_PROCESS_KEY_ORDER_PDN,
            {
                "ZOPEN": ["Title", "DCR (mOhm)", "L@100MHz (pH)", "C@10kHz (nF)", "Figure"],
                "ZSHORT": ["Title", "DCR (mOhm)", "L@100MHz (pH)", "C@10kHz (nF)", "Figure"],
            },
        ),
        (
            "io_report",
            POST_PROCESS_KEY_ORDER_IO,
            {
                "IL": ["Title", "IL@f0 (dB)", "IL Figure"],
                "RL": ["Title", "RL@f0 (dB)", "RL Figure"],
                "TDR": ["Title", "Zc (Ohm)", "TDR Figure"],
                "TDR_MM": ["Title", "Zc (Ohm)", "TDR Figure"],
            },
        ),
    ],
)
def test_table_positions_follow_post_process_order(template_name, order, expected_headers):
    report = deepcopy(getattr(temp_report, template_name))
    table_blocks = report["sections"][1]["content"]
    assert len(table_blocks) == len(order)
    for process_key, position in order.items():
        if process_key in expected_headers:
            assert table_blocks[position]["table"][0] == expected_headers[process_key]


@pytest.mark.parametrize(
    ("process_key", "expected_header"),
    [
        ("IL_MM", ["Title", "IL@f0 (dB)", "IL Figure"]),
        ("RL_MM", ["Title", "RL@f0 (dB)", "RL Figure"]),
    ],
)
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="BUG: mixed-mode IL and RL report headings are swapped in the production template",
)
def test_mixed_mode_table_headings_match_their_post_process_keys(process_key, expected_header):
    report = deepcopy(temp_report.io_report)
    position = POST_PROCESS_KEY_ORDER_IO[process_key]
    assert report["sections"][1]["content"][position]["table"][0] == expected_header


def test_mutating_deep_copy_does_not_change_production_template():
    report = deepcopy(temp_report.pdn_report)
    original_rows = len(temp_report.pdn_report["sections"][0]["content"][0]["table"])
    report["sections"][0]["content"][0]["table"].append(["new", "row"])
    assert len(temp_report.pdn_report["sections"][0]["content"][0]["table"]) == original_rows
