# SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Characterization tests for simulation input parsing."""

from copy import deepcopy
from unittest.mock import Mock

import pytest

from opensipi.constants.CONSTANTS import (
    INPUT_FILE_STARTSWITH,
    SIM_INPUT_COL_TITLE,
    SPEC_TYPE,
)
from opensipi.file_in import FileIn
from opensipi.util.exceptions import (
    MaterialsMustBeDefinedBeforeStackup,
    NoneUniqueKeyDefined,
)

OPTIONAL_STACKUP_KEYS = {
    "OP_FILLIN_DIELECTRIC",
    "OP_ROUGHNESS_UPPER",
    "OP_ROUGHNESS_LOWER",
    "OP_ROUGHNESS_SIDE",
    "OP_TRAPEZOIDAL_ANGLE_DEG",
}


@pytest.fixture(autouse=True)
def restore_spec_type():
    """Prevent mutable built-in spec definitions from leaking between tests."""
    original = deepcopy(SPEC_TYPE)
    yield
    SPEC_TYPE.clear()
    SPEC_TYPE.update(original)
    FakeGsheetIO.workbook = None
    FakeGsheetIO.received_info = None


def _sim_row(unique_key="", checked="", **values):
    row = dict.fromkeys(SIM_INPUT_COL_TITLE, "")
    row.update(UNIQUE_KEY=unique_key, CHECK_BOX=checked, **values)
    return [row[title] for title in SIM_INPUT_COL_TITLE]


def _sim_table(*rows):
    return [list(SIM_INPUT_COL_TITLE), *rows]


def _special_settings_table():
    return [
        ["Setting", "Value", "Format", "Descriptions"],
        [" ExtractionTool ", " Sigrity ", "choice", "documentation only"],
        ["projectname", " Demo Board ", "text", "documentation only"],
    ]


def _stackup_table(include_surface_roughness=True):
    rows = [
        ["Materials", ""],
        ["NAME", "PERMITTIVITY"],
        [" FR4 ", " 4.2 "],
    ]
    if include_surface_roughness:
        rows.extend(
            [
                ["SurfaceRoughness", ""],
                ["NAME", "MODEL"],
                [" Copper ", " Huray "],
            ]
        )
    rows.extend(
        [
            ["Stackup", ""],
            [" layer_name ", " material "],
            [" Top ", " Copper "],
            [" Core ", " FR4 "],
        ]
    )
    return rows


def _spec_type_table():
    return [
        ["Spec Type", "Freq", "Post_Process_Key"],
        [" custom ", " 1, 20, 3 ", " il, rl_mm "],
        [" zpdn ", " 5, 500 ", " zshort "],
    ]


def _expected_input_data(parts):
    return dict(
        zip(
            ["sim_input", "all_input", "stackup_info", "settings", "spectype_info"],
            parts,
        )
    )


class FakeWorksheet:
    def __init__(self, title, values):
        self.title = title
        self._values = deepcopy(values)

    def get_all_values(self):
        return deepcopy(self._values)


class FakeWorkbook:
    def __init__(self, sheets):
        self._worksheets = [FakeWorksheet(title, values) for title, values in sheets]
        self._by_title = {worksheet.title: worksheet for worksheet in self._worksheets}

    def worksheets(self):
        return list(self._worksheets)

    def worksheet(self, title):
        return self._by_title[title]


class FakeGsheetIO:
    workbook = None
    received_info = None

    def __init__(self, info):
        type(self).received_info = info

    def get_sheet_service_account(self):
        return type(self).workbook


@pytest.mark.parametrize("input_type", ["CSV", "GSHEET"])
def test_init_dispatches_reader_and_assigns_input_data(monkeypatch, input_type, tmp_path):
    parsed = (
        {"enabled": [1]},
        {"all": [1, 2]},
        {"stackup": {}},
        {"SETTING": "value"},
        {"CUSTOM": {}},
    )
    csv_reader = Mock(return_value=parsed)
    gsheet_reader = Mock(return_value=parsed)
    monkeypatch.setattr(FileIn, "_read_input_csv", csv_reader)
    monkeypatch.setattr(FileIn, "_read_input_gsheet", gsheet_reader)
    info = {
        "input_type": input_type,
        "input_file_startswith": list(INPUT_FILE_STARTSWITH),
        "input_dir": f"{tmp_path}/",
        "account_key": "unused.json",
        "account_type": "SERVICE",
        "sheet_url": "https://example.invalid/sheet",
    }

    file_in = FileIn(info)

    assert file_in.INPUT_DATA == _expected_input_data(parsed)
    if input_type == "CSV":
        csv_reader.assert_called_once()
        query = csv_reader.call_args.args[0]
        assert query.startswith(f"{tmp_path}/")
        assert query.endswith("*.[cC][sS][vV]")
        gsheet_reader.assert_not_called()
    else:
        gsheet_reader.assert_called_once_with(info)
        csv_reader.assert_not_called()


def test_init_unknown_input_type_returns_empty_input_data(monkeypatch):
    csv_reader = Mock()
    gsheet_reader = Mock()
    monkeypatch.setattr(FileIn, "_read_input_csv", csv_reader)
    monkeypatch.setattr(FileIn, "_read_input_gsheet", gsheet_reader)

    file_in = FileIn(
        {
            "input_type": "UNKNOWN",
            "input_file_startswith": list(INPUT_FILE_STARTSWITH),
        }
    )

    assert file_in.INPUT_DATA == {
        "sim_input": {},
        "all_input": {},
        "stackup_info": {},
        "settings": {},
        "spectype_info": {},
    }
    csv_reader.assert_not_called()
    gsheet_reader.assert_not_called()


def test_parse_sim_inputs_strips_namespaces_groups_and_filters_literal_true(
    file_in_factory,
):
    file_in = file_in_factory()
    raw_data = _sim_table(
        _sim_row(" rail_a ", " TRUE ", POSITIVE_NETS=" VDD "),
        _sim_row("", "false", POSITIVE_NETS=" VDD_SENSE "),
        _sim_row("rail_b", "true", POSITIVE_NETS=" VSS "),
        _sim_row("rail_c", "FALSE", POSITIVE_NETS=" AUX "),
    )

    enabled, all_data = file_in._FileIn__parse_sim_inputs(raw_data, "SIM")

    assert list(all_data) == ["SIM_rail_a", "SIM_rail_b", "SIM_rail_c"]
    assert set(enabled) == {"SIM_rail_a"}
    assert enabled["SIM_rail_a"] == all_data["SIM_rail_a"]
    assert len(enabled["SIM_rail_a"]) == 2
    assert all_data["SIM_rail_a"] == [
        {
            **dict.fromkeys(SIM_INPUT_COL_TITLE, ""),
            "UNIQUE_KEY": "rail_a",
            "CHECK_BOX": "TRUE",
            "POSITIVE_NETS": "VDD",
        },
        {
            **dict.fromkeys(SIM_INPUT_COL_TITLE, ""),
            "CHECK_BOX": "false",
            "POSITIVE_NETS": "VDD_SENSE",
        },
    ]
    assert all_data["SIM_rail_b"][0]["CHECK_BOX"] == "true"
    assert all_data["SIM_rail_c"][0]["CHECK_BOX"] == "FALSE"
    assert raw_data[1][0] == " rail_a "


def test_parse_sim_inputs_rejects_duplicate_unique_keys(file_in_factory):
    file_in = file_in_factory()
    raw_data = _sim_table(
        _sim_row("duplicate", "TRUE"),
        _sim_row("duplicate", "FALSE"),
    )

    with pytest.raises(NoneUniqueKeyDefined):
        file_in._FileIn__parse_sim_inputs(raw_data, "SIM")


def test_parse_special_settings_discards_documentation_and_preserves_values(
    file_in_factory,
):
    file_in = file_in_factory()

    settings = file_in._FileIn__parse_special_settings(_special_settings_table())

    assert settings == {
        "EXTRACTIONTOOL": "Sigrity",
        "PROJECTNAME": "Demo Board",
    }
    assert set(settings) == {"EXTRACTIONTOOL", "PROJECTNAME"}
    assert len(settings) == 2


def test_parse_spec_type_adds_overrides_and_normalizes_without_global_mutation(
    file_in_factory,
):
    file_in = file_in_factory()
    original = deepcopy(SPEC_TYPE)

    parsed = file_in._FileIn__parse_spec_type(_spec_type_table())

    assert parsed["CUSTOM"] == {
        "FREQ": [1, 20, 3],
        "POST_PROCESS_KEY": ["IL", "RL_MM"],
    }
    assert parsed["ZPDN"] == {
        "FREQ": [5, 500],
        "POST_PROCESS_KEY": ["ZSHORT"],
    }
    for built_in in set(original) - {"ZPDN"}:
        assert parsed[built_in] == original[built_in]
    assert SPEC_TYPE == original
    assert parsed is not SPEC_TYPE


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="BUG: parsed spec types shallow-copy nested built-ins and leak mutations to SPEC_TYPE",
)
def test_parse_spec_type_result_is_deeply_isolated_from_built_in_spec_types(file_in_factory):
    file_in = file_in_factory()
    original = deepcopy(SPEC_TYPE)
    parsed = file_in._FileIn__parse_spec_type(_spec_type_table())

    parsed["SLS"]["FREQ"].append(999)

    assert SPEC_TYPE == original


def test_parse_stackup_info_parses_all_sections_and_injects_optional_columns(
    file_in_factory,
):
    file_in = file_in_factory()

    parsed = file_in._FileIn__parse_stackup_info(_stackup_table())

    assert parsed["materials"] == [["FR4", "4.2"]]
    assert parsed["surfaceroughness"] == [["Copper", "Huray"]]
    assert parsed["stackup"]["LAYER_NAME"] == ["Top", "Core"]
    assert parsed["stackup"]["MATERIAL"] == ["Copper", "FR4"]
    assert OPTIONAL_STACKUP_KEYS <= parsed["stackup"].keys()
    for key in OPTIONAL_STACKUP_KEYS:
        assert parsed["stackup"][key] == ["", ""]


def test_parse_stackup_info_preserves_supplied_optional_columns(file_in_factory):
    file_in = file_in_factory()
    raw_data = [
        ["Materials", ""],
        ["NAME", "PERMITTIVITY"],
        ["FR4", "4.2"],
        ["Stackup", ""],
        [
            "LAYER_NAME",
            "MATERIAL",
            "OP_FILLIN_DIELECTRIC",
            "OP_ROUGHNESS_UPPER",
            "OP_ROUGHNESS_LOWER",
            "OP_ROUGHNESS_SIDE",
            "OP_TRAPEZOIDAL_ANGLE_DEG",
        ],
        ["Top", "Copper", "FillTop", "RoughU1", "RoughL1", "RoughS1", "45"],
        ["Core", "FR4", "FillCore", "RoughU2", "RoughL2", "RoughS2", "60"],
    ]

    parsed = file_in._FileIn__parse_stackup_info(raw_data)

    assert parsed["stackup"]["OP_FILLIN_DIELECTRIC"] == ["FillTop", "FillCore"]
    assert parsed["stackup"]["OP_ROUGHNESS_UPPER"] == ["RoughU1", "RoughU2"]
    assert parsed["stackup"]["OP_ROUGHNESS_LOWER"] == ["RoughL1", "RoughL2"]
    assert parsed["stackup"]["OP_ROUGHNESS_SIDE"] == ["RoughS1", "RoughS2"]
    assert parsed["stackup"]["OP_TRAPEZOIDAL_ANGLE_DEG"] == ["45", "60"]


def test_parse_stackup_info_uses_empty_surface_roughness_when_section_is_missing(
    file_in_factory,
):
    file_in = file_in_factory()

    parsed = file_in._FileIn__parse_stackup_info(_stackup_table(include_surface_roughness=False))

    assert parsed["surfaceroughness"] == [["", ""]]
    assert parsed["materials"] == [["FR4", "4.2"]]
    assert parsed["stackup"]["LAYER_NAME"] == ["Top", "Core"]


def test_parse_stackup_info_requires_materials_before_stackup(file_in_factory):
    file_in = file_in_factory()
    raw_data = [
        ["Stackup", ""],
        ["LAYER_NAME", "MATERIAL"],
        ["Top", "Copper"],
        ["Materials", ""],
        ["NAME", "PERMITTIVITY"],
        ["FR4", "4.2"],
    ]

    with pytest.raises(MaterialsMustBeDefinedBeforeStackup):
        file_in._FileIn__parse_stackup_info(raw_data)


def test_read_input_csv_combines_sim_sheets_and_ignores_unrelated_files(
    file_in_factory, temp_csv_builder, tmp_path
):
    file_in = file_in_factory()
    temp_csv_builder(
        _sim_table(_sim_row("alpha", "TRUE", POSITIVE_NETS="VDD")),
        "Sim_Pdn.CsV",
    )
    temp_csv_builder(
        _sim_table(_sim_row("beta", "FALSE", POSITIVE_NETS="VSS")),
        "SIM_IO.csv",
    )
    temp_csv_builder(_special_settings_table(), "special_settings.CSV")
    temp_csv_builder(_stackup_table(), "STACKUP_MATERIALS.csv")
    temp_csv_builder([["ignored"], ["value"]], "notes.csv")
    original = deepcopy(SPEC_TYPE)

    parsed = file_in._read_input_csv(str(tmp_path / "*.[cC][sS][vV]"))
    sim_input, all_input, stackup_info, settings, spectype_info = parsed

    assert set(sim_input) == {"SIM_alpha"}
    assert set(all_input) == {"SIM_alpha", "SIM_beta"}
    assert all_input["SIM_beta"][0]["POSITIVE_NETS"] == "VSS"
    assert settings == {
        "EXTRACTIONTOOL": "Sigrity",
        "PROJECTNAME": "Demo Board",
    }
    assert stackup_info["stackup"]["LAYER_NAME"] == ["Top", "Core"]
    assert spectype_info == original
    assert spectype_info is not SPEC_TYPE


def test_read_input_gsheet_uses_service_account_fake_and_matches_parser_results(
    monkeypatch, file_in_factory
):
    sheets = [
        ("Sim_Pdn", _sim_table(_sim_row("alpha", "TRUE", POSITIVE_NETS="VDD"))),
        ("SIM_IO", _sim_table(_sim_row("beta", "FALSE", POSITIVE_NETS="VSS"))),
        ("Special_Settings", _special_settings_table()),
        ("Stackup_Materials", _stackup_table()),
        ("Spec_Type", _spec_type_table()),
        ("Notes", [["ignored"], ["value"]]),
    ]
    FakeGsheetIO.workbook = FakeWorkbook(sheets)
    FakeGsheetIO.received_info = None
    monkeypatch.setattr("opensipi.file_in.GsheetIO", FakeGsheetIO)
    file_in = file_in_factory(INPUT_TYPE="GSHEET")
    info = {
        "account_key": "not-used.json",
        "account_type": "SERVICE",
        "sheet_url": "https://example.invalid/sheet",
    }

    parsed = file_in._read_input_gsheet(info)
    sim_input, all_input, stackup_info, settings, spectype_info = parsed

    assert FakeGsheetIO.received_info is info
    assert set(sim_input) == {"SIM_alpha"}
    assert set(all_input) == {"SIM_alpha", "SIM_beta"}
    assert all_input["SIM_alpha"][0]["POSITIVE_NETS"] == "VDD"
    assert settings["PROJECTNAME"] == "Demo Board"
    assert stackup_info["materials"] == [["FR4", "4.2"]]
    assert stackup_info["stackup"]["LAYER_NAME"] == ["Top", "Core"]
    assert spectype_info["CUSTOM"]["FREQ"] == [1, 20, 3]
    assert spectype_info["CUSTOM"]["POST_PROCESS_KEY"] == ["IL", "RL_MM"]
    assert spectype_info["ZPDN"]["FREQ"] == [5, 500]
    assert SPEC_TYPE["ZPDN"] != spectype_info["ZPDN"]
