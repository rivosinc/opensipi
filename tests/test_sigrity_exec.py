# SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Offline characterization tests for Sigrity executor domain logic."""

import logging
from unittest.mock import Mock

import pytest

from opensipi.constants.CONSTANTS import SIM_INPUT_COL_TITLE
from opensipi.sigrity_exec import (
    ClarityExec,
    PowerdcExec,
    PowersiIOExec,
    PowersiPdnExec,
)
from opensipi.util.common import SL

UNIKEY, CKBOX, SPECTYPE, POSNET, NEGNET, POSMP, NEGMP, POSAP, NEGAP = SIM_INPUT_COL_TITLE[:9]


def _sim_row(**values):
    row = dict.fromkeys(SIM_INPUT_COL_TITLE, "")
    row.update(values)
    return row


def _executor(executor_factory, executor_cls=PowersiPdnExec, **attrs):
    return executor_factory(
        executor_cls=executor_cls,
        UNIKEY=UNIKEY,
        CKBOX=CKBOX,
        SPECTYPE=SPECTYPE,
        POSNET=POSNET,
        NEGNET=NEGNET,
        POSMP=POSMP,
        NEGMP=NEGMP,
        POSAP=POSAP,
        NEGAP=NEGAP,
        lg=Mock(spec=logging.Logger),
        **attrs,
    )


def _valid_row(**overrides):
    values = {
        SPECTYPE: "ZPDN",
        POSNET: "VDD",
        NEGNET: "VSS",
        POSMP: "U1",
        NEGMP: "U2",
        POSAP: "",
        NEGAP: "",
    }
    values.update(overrides)
    return _sim_row(**values)


def _write_files(directory, files):
    directory.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (directory / name).write_text(content, encoding="utf-8")


def _relocation_executor(executor_factory, executor_cls, tmp_path):
    sim_dir = tmp_path / "sim"
    result_dir = tmp_path / "results"
    sim_dir.mkdir()
    result_dir.mkdir()
    return _executor(
        executor_factory,
        executor_cls,
        sim_dir=f"{sim_dir}{SL}",
        result_dir=f"{result_dir}{SL}",
        snp_s_dir=f"{result_dir / 'SNP_S'}{SL}",
        snp_dcfitted_dir=f"{result_dir / 'SNP_DCfitted'}{SL}",
        snp_dc_dir=f"{result_dir / 'SNP_DC'}{SL}",
    )


def test_check_input_format_accepts_valid_pdn_input(executor_factory):
    executor = _executor(
        executor_factory,
        sim_input={"rail_a": [_valid_row()]},
    )

    assert executor._check_input_format() == []


def test_check_input_format_aggregates_key_spec_net_and_component_errors(
    executor_factory,
):
    executor = _executor(
        executor_factory,
        sim_input={
            "bad key-$": [
                _valid_row(
                    **{
                        SPECTYPE: "",
                        POSNET: "",
                        NEGNET: "",
                        POSMP: "U1; U2",
                        NEGMP: "",
                        POSAP: "LUMPED",
                        NEGAP: "R1; LUMPED",
                    }
                )
            ]
        },
    )

    errors = executor._check_input_format()

    assert len(errors) == 6
    assert any('" " is not allowed in the key: bad key-$' in error for error in errors)
    assert any('"-" is not allowed in the key: bad key-$' in error for error in errors)
    assert any('"$" is not allowed in the key: bad key-$' in error for error in errors)
    assert any("No spec type was specified" in error for error in errors)
    assert sum("No net was specified" in error for error in errors) == 2
    component_errors = "\n".join(error for error in errors if "Row 1" in error)
    assert "only 1 component symbol in the positive side" in component_errors
    assert "LUMPED is only allowed" in component_errors
    assert "only 1 component symbol in the negative side" in component_errors


@pytest.mark.parametrize("symbol", [" ", "-", "$"])
def test_check_input_format_rejects_each_illegal_unique_key_character(executor_factory, symbol):
    key = f"rail{symbol}a"
    executor = _executor(executor_factory, sim_input={key: [_valid_row()]})

    errors = executor._check_input_format()

    assert errors == [f'[Error] "{symbol}" is not allowed in the key: {key}']


def test_check_input_format_rejects_multiple_spec_types_in_one_simulation(
    executor_factory,
):
    executor = _executor(
        executor_factory,
        sim_input={
            "rail_a": [
                _valid_row(),
                _valid_row(**{SPECTYPE: "ZL", POSMP: "U3", NEGMP: "U4"}),
            ]
        },
    )

    errors = executor._check_input_format()

    assert len(errors) == 1
    assert "rail_a" in errors[0]
    assert f"Col {SPECTYPE}" in errors[0]
    assert "More than one spec type was specified" in errors[0]


@pytest.mark.parametrize("empty_col", [POSNET, NEGNET])
def test_check_input_format_requires_positive_and_negative_nets(executor_factory, empty_col):
    executor = _executor(
        executor_factory,
        sim_input={"rail_a": [_valid_row(**{empty_col: ""})]},
    )

    errors = executor._check_input_format()

    assert len(errors) == 1
    assert f"Col {empty_col}" in errors[0]
    assert "No net was specified" in errors[0]


@pytest.mark.parametrize(
    ("positive", "negative", "message"),
    [
        ("U1; U2", "", "only 1 component symbol in the positive side"),
        ("U1", "R1; LUMPED", "only 1 component symbol in the negative side"),
        ("LUMPED", "R1", "LUMPED is only allowed"),
    ],
)
def test_pdn_component_rules_reject_invalid_port_shapes(
    executor_factory, positive, negative, message
):
    executor = _executor(executor_factory)

    errors = executor._check_comp_format(positive, negative, 3)

    assert len(errors) == 1
    assert "Row 3" in errors[0]
    assert message in errors[0]


def test_pdn_component_rules_allow_single_component_area_and_valid_lumped_ports(
    executor_factory,
):
    executor = _executor(executor_factory)

    assert executor._check_comp_format("U1", "", 1) == []
    assert executor._check_comp_format("Rec{0, 0, 1, 1}", "", 1) == []
    assert executor._check_comp_format("U1", "LUMPED", 1) == []


@pytest.mark.parametrize(
    ("positive", "negative", "missing"),
    [
        ("U1, 1; U2", "R1, 1; R2, 2", "U2"),
        ("U1, 1; U2, 2", "R1; R2, 2", "R1"),
    ],
)
def test_io_component_rules_require_pins_for_each_multi_component_side(
    executor_factory, positive, negative, missing
):
    executor = _executor(executor_factory, PowersiIOExec)

    errors = executor._check_comp_format(positive, negative, 4)

    assert len(errors) == 1
    assert "Row 4" in errors[0]
    assert "component must come with pins" in errors[0]
    assert errors[0].endswith(missing)


def test_io_component_rules_allow_pinned_multi_component_ports(executor_factory):
    executor = _executor(executor_factory, PowersiIOExec)

    assert executor._check_comp_format("U1, 1; U2, 2", "R1, 3; R2, 4", 1) == []


def test_get_unique_items_in_col_strips_deduplicates_and_preserves_order(
    executor_factory,
):
    executor = _executor(executor_factory)
    rows = [
        _sim_row(**{POSNET: " VDD, VSS, VDD "}),
        _sim_row(**{POSNET: "VSS, AUX, "}),
        _sim_row(**{POSNET: ""}),
    ]

    assert executor._get_unique_items_in_col(rows, POSNET) == ["VDD", "VSS", "AUX"]


def test_get_unique_items_in_col_supports_list_rows(executor_factory):
    executor = _executor(executor_factory)
    rows = [["name", " A, B "], ["other", "B, C"]]

    assert executor._get_unique_items_in_col(rows, 1) == ["A", "B", "C"]


def test_get_unique_comps_in_col_extracts_refdes_and_preserves_order(
    executor_factory,
):
    executor = _executor(executor_factory)
    rows = [
        _sim_row(**{POSMP: " U1, A1, A2 "}),
        _sim_row(**{POSMP: "U2, B1"}),
        _sim_row(**{POSMP: "U1, A3"}),
        _sim_row(**{POSMP: ""}),
    ]

    assert executor._get_unique_comps_in_col(rows, POSMP) == ["U1", "U2"]


@pytest.mark.parametrize(
    ("cell", "expected"),
    [
        (" U1, A1, A2 ", ("U1", ["A1", "A2"])),
        ("U2", ("U2", [])),
        ("", ("", [])),
    ],
)
def test_get_refdes_n_pins_splits_and_strips_component_cells(executor_factory, cell, expected):
    executor = _executor(executor_factory)

    assert executor._get_refdes_n_pins(cell) == expected


def test_pdn_relocate_results_copies_only_supported_touchstone_files(executor_factory, tmp_path):
    executor = _relocation_executor(executor_factory, PowersiPdnExec, tmp_path)
    sim_dir = tmp_path / "sim"
    _write_files(
        sim_dir,
        {
            "rail_S.s2p": "raw-s",
            "rail_DCfitted.S2P": "dc-fitted",
            "rail_DC.s2p": "dc-not-currently-relocated",
            "notes.txt": "ignore-me",
        },
    )

    executor._relocate_results()

    assert (tmp_path / "results" / "SNP_S" / "rail_S.s2p").read_text() == "raw-s"
    assert (tmp_path / "results" / "SNP_DCfitted" / "rail_DCfitted.S2P").read_text() == "dc-fitted"
    assert (sim_dir / "rail_S.s2p").read_text() == "raw-s"
    assert (sim_dir / "rail_DCfitted.S2P").read_text() == "dc-fitted"
    assert not (tmp_path / "results" / "SNP_S" / "rail_DC.s2p").exists()
    assert not (tmp_path / "results" / "SNP_DCfitted" / "rail_DC.s2p").exists()
    assert not (tmp_path / "results" / "SNP_S" / "notes.txt").exists()


def test_pdn_relocate_results_preserves_existing_destination_file(executor_factory, tmp_path):
    executor = _relocation_executor(executor_factory, PowersiPdnExec, tmp_path)
    sim_dir = tmp_path / "sim"
    source = sim_dir / "rail_S.s2p"
    source.write_text("new-source", encoding="utf-8")
    destination_dir = tmp_path / "results" / "SNP_S"
    destination_dir.mkdir()
    destination = destination_dir / source.name
    destination.write_text("existing-result", encoding="utf-8")

    executor._relocate_results()

    assert destination.read_text(encoding="utf-8") == "existing-result"


def test_clarity_relocate_results_copies_fit_and_dc_files(executor_factory, tmp_path):
    executor = _relocation_executor(executor_factory, ClarityExec, tmp_path)
    sim_dir = tmp_path / "sim"
    _write_files(
        sim_dir,
        {
            "channel_FIT.s4p": "fit-result",
            "channel_DC.S4P": "dc-result",
            "channel_S.s4p": "ignore-power-si-name",
        },
    )

    executor._relocate_results()

    assert (tmp_path / "results" / "SNP_S" / "channel_FIT.s4p").read_text() == "fit-result"
    assert (tmp_path / "results" / "SNP_DC" / "channel_DC.S4P").read_text() == "dc-result"
    assert (sim_dir / "channel_FIT.s4p").read_text() == "fit-result"
    assert (sim_dir / "channel_DC.S4P").read_text() == "dc-result"
    assert not (tmp_path / "results" / "SNP_S" / "channel_S.s4p").exists()


def test_dcr_relocate_results_copies_resistance_csv(executor_factory, tmp_path):
    executor = _relocation_executor(executor_factory, PowerdcExec, tmp_path)
    csv_dir = tmp_path / "sim" / "CSVFolder"
    _write_files(csv_dir, {"Resis.csv": "name,resistance\nrail_a,0.001\n"})
    executor.csv_dir = f"{csv_dir}{SL}"
    executor.RESIS_CSV = "Resis.csv"

    executor._relocate_results()

    relocated = tmp_path / "results" / "Resis.csv"
    assert relocated == tmp_path / "results" / executor.RESIS_CSV
    assert relocated.read_text(encoding="utf-8") == "name,resistance\nrail_a,0.001\n"
    assert (csv_dir / "Resis.csv").read_text(encoding="utf-8") == (
        "name,resistance\nrail_a,0.001\n"
    )
