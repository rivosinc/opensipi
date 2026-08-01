# SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Hermetic characterization tests for Sigrity modeler domain logic."""

import pytest

from opensipi.constants.CONSTANTS import SIM_INPUT_COL_TITLE
from opensipi.sigrity_tools import ClarityModeler, PowersiPdnModeler, SpdModeler
from opensipi.util.exceptions import WrongAreaPortDef, WrongGrowSolderFormat

POSITIVE_MAIN_PORTS = SIM_INPUT_COL_TITLE[5]
NEGATIVE_MAIN_PORTS = SIM_INPUT_COL_TITLE[6]
POSITIVE_AUX_PORTS = SIM_INPUT_COL_TITLE[7]
NEGATIVE_AUX_PORTS = SIM_INPUT_COL_TITLE[8]
OP_FREQ = SIM_INPUT_COL_TITLE[9]
OP_DIFFPAIR = SIM_INPUT_COL_TITLE[10]
OP_DISALLCAPS = SIM_INPUT_COL_TITLE[11]
OP_MIXEDMODETERM = SIM_INPUT_COL_TITLE[12]
OP_PRECUT = SIM_INPUT_COL_TITLE[13]


def _sim_row(**values):
    row = dict.fromkeys(SIM_INPUT_COL_TITLE, "")
    row.update(values)
    return row


def _connectivity_modeler(modeler_factory, extraction_type, rows):
    return modeler_factory(
        modeler_cls=SpdModeler,
        xtract_type=extraction_type,
        all_input={"SIM_TEST": rows},
        POSMP=POSITIVE_MAIN_PORTS,
        NEGMP=NEGATIVE_MAIN_PORTS,
        POSAP=POSITIVE_AUX_PORTS,
        NEGAP=NEGATIVE_AUX_PORTS,
        OPDIFFPAIR=OP_DIFFPAIR,
        OPMIXEDMODETERM=OP_MIXEDMODETERM,
    )


def _frequency_modeler(modeler_factory, modeler_cls=PowersiPdnModeler, **attrs):
    defaults = {
        "settings": {"GLOBALFREQ": ""},
        "SPECTYPE_INFO": {"ZPDN": {"FREQ": [0, 1_000_000_000]}},
        "OPFREQ": OP_FREQ,
    }
    return modeler_factory(modeler_cls=modeler_cls, **{**defaults, **attrs})


def test_pdn_connectivity_numbers_only_defined_main_ports(modeler_factory):
    rows = [
        _sim_row(**{POSITIVE_MAIN_PORTS: "U1"}),
        _sim_row(**{POSITIVE_MAIN_PORTS: ""}),
        _sim_row(**{POSITIVE_MAIN_PORTS: "U2"}),
    ]
    modeler = _connectivity_modeler(modeler_factory, "PDN", rows)

    connectivity = modeler._SpdModeler__get_connectivity()

    assert connectivity == {"SIM_TEST": {"ZIN": [1, 2]}}


def test_io_connectivity_reuses_blank_main_and_aux_ports(modeler_factory):
    rows = [
        _sim_row(
            **{
                POSITIVE_MAIN_PORTS: "U1",
                POSITIVE_AUX_PORTS: "J1",
            }
        ),
        _sim_row(),
        _sim_row(
            **{
                POSITIVE_MAIN_PORTS: "U2",
                POSITIVE_AUX_PORTS: "J2",
            }
        ),
    ]
    modeler = _connectivity_modeler(modeler_factory, "LSIO", rows)

    connectivity = modeler._SpdModeler__get_connectivity()["SIM_TEST"]

    assert connectivity["IL"] == [[1, 3], [1, 3], [2, 4]]
    assert connectivity["RL"] == [1, 2, 3, 4]
    assert connectivity["TDR"] == [[1, 2], [3, 4]]


def test_io_connectivity_without_aux_ports_has_no_insertion_loss(modeler_factory):
    rows = [
        _sim_row(**{POSITIVE_MAIN_PORTS: "U1"}),
        _sim_row(**{POSITIVE_MAIN_PORTS: "U2"}),
    ]
    modeler = _connectivity_modeler(modeler_factory, "HSIO", rows)

    connectivity = modeler._SpdModeler__get_connectivity()["SIM_TEST"]

    assert connectivity["IL"] == []
    assert connectivity["RL"] == [1, 2]
    assert connectivity["TDR"] == [[], []]
    assert connectivity["IL_MM"] == []
    assert connectivity["RL_MM"] == []
    assert connectivity["TDR_MM"] == [[], []]


def test_io_connectivity_builds_mixed_mode_order_and_tdr_sides(modeler_factory):
    rows = [
        _sim_row(
            **{
                POSITIVE_MAIN_PORTS: "U1",
                POSITIVE_AUX_PORTS: "J1",
                OP_DIFFPAIR: "P1,P2",
            }
        ),
        _sim_row(
            **{
                POSITIVE_MAIN_PORTS: "U2",
                POSITIVE_AUX_PORTS: "J2",
                OP_DIFFPAIR: "N1,N2",
            }
        ),
    ]
    modeler = _connectivity_modeler(modeler_factory, "HSIO", rows)

    connectivity = modeler._SpdModeler__get_connectivity()["SIM_TEST"]

    assert connectivity["IL"] == [[1, 3], [2, 4]]
    assert connectivity["MM_ORDER_IN_SE"] == [0, 1, 2, 3]
    assert connectivity["IL_MM"] == [[1, 2]]
    assert connectivity["RL_MM"] == [1, 2]
    assert connectivity["TDR"] == [[1, 2], [3, 4]]
    assert connectivity["TDR_MM"] == [[1], [2]]


@pytest.mark.parametrize(
    ("term_value", "expected"),
    [
        ("", [100, 25]),
        ("200, 50", [200, 50]),
    ],
)
def test_io_connectivity_uses_default_or_overridden_mixed_mode_termination(
    modeler_factory, term_value, expected
):
    rows = [
        _sim_row(
            **{
                POSITIVE_MAIN_PORTS: "U1",
                POSITIVE_AUX_PORTS: "J1",
                OP_MIXEDMODETERM: term_value,
            }
        )
    ]
    modeler = _connectivity_modeler(modeler_factory, "LSIO", rows)

    connectivity = modeler._SpdModeler__get_connectivity()["SIM_TEST"]

    assert connectivity["TERM_MM"] == expected


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("U1", ("U1", [])),
        (" U1, A1, B2 ", ("U1", ["A1", "B2"])),
    ],
)
def test_get_refdes_n_pins_splits_and_strips_values(modeler_factory, raw_value, expected):
    modeler = modeler_factory(modeler_cls=SpdModeler)

    assert modeler._get_refdes_n_pins(raw_value) == expected


def test_refdes_and_pin_mapping_expands_groups_and_redirects_grown_solder(
    modeler_factory,
):
    modeler = modeler_factory(
        modeler_cls=PowersiPdnModeler,
        solder_refdes={"U1": "U1_solder"},
    )

    components, pins = modeler._PowersiPdnModeler__map_refdes_n_pin_list("U1, A1, A2; U2, B1")

    assert components == ["U1_solder", "U2"]
    assert pins == ["A1 A2", "B1"]


def test_refdes_pin_expansion_tcl_substitutes_component_and_net(modeler_factory):
    modeler = modeler_factory(modeler_cls=PowersiPdnModeler)

    pin_name, tcl = modeler._get_refdes_pins_per_net("U17", "VDD_CPU")

    assert pin_name == "refdes_pins"
    assert "set refdes_pins" in tcl
    assert "get_refdes_pins_per_net U17 VDD_CPU" in tcl
    assert not {"PINNAME", "COMP", "NETNAME"}.intersection(tcl.split())


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="BUG: documented comma-separated RAD input leaves a comma on the Tcl radius",
)
def test_nearby_ground_pin_tcl_substitutes_documented_radius_and_layer(modeler_factory):
    modeler = modeler_factory(modeler_cls=PowersiPdnModeler)

    pin_name, tcl = modeler._get_nearby_gndpins_per_refdes_n_net(
        "U17", "VDD_CPU", "GND", "RAD{0.0005, TOP}"
    )

    assert pin_name == "gnd_nodes"
    assert "get_nearby_gnd_pins_per_refdes_n_posnet U17 VDD_CPU GND 0.0005 {TOP}" in tcl
    assert "RADIUS" not in tcl
    assert "TGTLAYER" not in tcl


def test_optional_setting_initialization_adds_missing_and_preserves_existing(
    modeler_factory,
):
    settings = {"GLOBALFREQ": "1, 2"}
    modeler = modeler_factory(modeler_cls=SpdModeler, settings=settings)

    modeler._init_optional_setting_key("GLOBALFREQ")
    modeler._init_optional_setting_key("FEMPORTSOLDER")

    assert settings == {"GLOBALFREQ": "1, 2", "FEMPORTSOLDER": ""}


@pytest.mark.parametrize(
    ("local_freq", "global_freq", "expected"),
    [
        ("1, 2, 3", "4, 5", ["1", "2", "3"]),
        ("", "4, 5", ["4", "5"]),
        ("", "", [0, 1_000_000_000]),
    ],
)
def test_frequency_list_precedence_is_local_then_global_then_spec_type(
    modeler_factory, local_freq, global_freq, expected
):
    modeler = _frequency_modeler(
        modeler_factory,
        settings={"GLOBALFREQ": global_freq},
    )
    info = [_sim_row(**{OP_FREQ: local_freq})]

    assert modeler._def_freq_list(info, "zpdn") == expected


@pytest.mark.parametrize(
    ("frequencies", "required_fragments", "absent_placeholders"),
    [
        (
            [0, 1_000_000_000],
            ["sigrity::update freq", "-start 0", "-end 1000000000", "-AFS"],
            ["FREQ_START", "FREQ_END"],
        ),
        (
            [1_000_000, 5_000_000_000, 5_000_000],
            [
                "sigrity::update freq",
                "{1000000, 5000000000, 5000000, linear, 3}",
            ],
            ["FREQ_START", "FREQ_END", "FREQ_STEP"],
        ),
    ],
)
def test_powersi_frequency_range_generates_supported_sweeps(
    modeler_factory, frequencies, required_fragments, absent_placeholders
):
    modeler = _frequency_modeler(modeler_factory)

    tcl = modeler._set_freq_range(frequencies)

    assert "# set up freq range" in tcl
    for fragment in required_fragments:
        assert fragment in tcl
    for placeholder in absent_placeholders:
        assert placeholder not in tcl


@pytest.mark.parametrize(
    ("frequencies", "required_fragment"),
    [
        ([0, 1_000_000_000], "-start 0 -end 1000000000 -AFS"),
        (
            [1_000_000, 5_000_000_000, 5_000_000],
            "{1000000, 5000000000, 5000000, linear, 3}",
        ),
        (
            [1_000_000, 50_000_000_000, 100_000_000, 16_000_000_000],
            "{{1000000 50000000000 linear 100000000}}",
        ),
    ],
)
def test_clarity_frequency_range_generates_supported_sweeps(
    modeler_factory, frequencies, required_fragment
):
    modeler = _frequency_modeler(modeler_factory, modeler_cls=ClarityModeler)

    tcl = modeler._set_freq_range(frequencies)

    assert required_fragment in tcl
    if len(frequencies) == 4:
        assert "-Wave3DSettingsolutionfreq {16000000000}" in tcl
        assert "-Wave3DRefleshFList {1}" in tcl
    for placeholder in ("FREQ_START", "FREQ_END", "FREQ_STEP", "FREQ_SOL"):
        assert placeholder not in tcl


@pytest.mark.parametrize(
    ("definition", "expected"),
    [
        (
            "Rec{0.001, 0.002, 0.003, 0.004, TOP}",
            ["0.001", "0.002", "0.003", "0.004", "TOP", "VDD", "GND"],
        ),
        (
            "Rec{0.001, 0.002, 0.003, 0.004, TOP, VDD_IO}",
            ["0.001", "0.002", "0.003", "0.004", "TOP", "VDD_IO", "GND"],
        ),
        (
            "Rec{0.001, 0.002, 0.003, 0.004, TOP, VDD_IO, VSS_IO}",
            ["0.001", "0.002", "0.003", "0.004", "TOP", "VDD_IO", "VSS_IO"],
        ),
    ],
)
def test_area_port_information_accepts_five_six_or_seven_fields(
    modeler_factory, definition, expected
):
    modeler = modeler_factory(modeler_cls=PowersiPdnModeler)

    assert modeler._get_areaport_info(definition, "VDD", "GND") == expected


@pytest.mark.parametrize(
    "definition",
    [
        "Rec{0, 0, 1, 1}",
        "Rec{0, 0, 1, 1, TOP, VDD, GND, EXTRA}",
    ],
)
def test_area_port_information_rejects_unsupported_field_counts(
    caplog, modeler_factory, definition
):
    modeler = modeler_factory(modeler_cls=PowersiPdnModeler)

    with caplog.at_level("DEBUG", logger=modeler.lg.name):
        with pytest.raises(WrongAreaPortDef):
            modeler._get_areaport_info(definition, "VDD", "GND")

    assert "Area port definition was wrong!" in caplog.messages


def test_area_port_tcl_substitutes_geometry_nets_layer_and_number(modeler_factory):
    modeler = modeler_factory(
        modeler_cls=PowersiPdnModeler,
        solder_refdes={},
    )

    tcl = modeler._set_port(
        ["Rec{0.001, 0.002, 0.003, 0.004, TOP}", ""],
        2,
        ["VDD"],
        ["GND"],
    )

    for fragment in (
        "# Port_3 definition",
        "Xmin 0.001",
        "Ymin 0.002",
        "Xmax 0.003",
        "Ymax 0.004",
        "Layer 'TOP'",
        "PNet 'VDD'",
        "NNet 'GND'",
        "Index 3",
    ):
        assert fragment in tcl
    for placeholder in ("LLX", "LLY", "URX", "URY", "LAYNAME", "NUMBER"):
        assert placeholder not in tcl


@pytest.mark.parametrize(
    ("top_setting", "bottom_setting", "required_fragments"),
    [
        (
            "U1,0.3,0.15",
            "",
            [
                "# Grow top solder",
                "-ckt U1",
                "-height {0.3}",
                "-radius {0.15}",
                "-PackageNotOnTop",
                "layer_name {PlaneTop}",
                "-name {U1_solder}",
            ],
        ),
        (
            "",
            "J1,0.25,0.1",
            [
                "# Grow bottom solder",
                "-ckt J1",
                "-height {0.25}",
                "-radius {0.1}",
                "layer_name {PlaneBot}",
                "-name {J1_solder}",
            ],
        ),
    ],
)
def test_solder_growth_tcl_substitutes_supported_top_and_bottom_settings(
    modeler_factory, top_setting, bottom_setting, required_fragments
):
    modeler = modeler_factory(
        modeler_cls=SpdModeler,
        settings={
            "GROWTOPSOLDER": top_setting,
            "GROWBOTSOLDER": bottom_setting,
        },
        solder_keys=["GROWTOPSOLDER", "GROWBOTSOLDER"],
    )

    tcl = modeler._SpdModeler__grow_solder_tcl()

    for fragment in required_fragments:
        assert fragment in tcl
    for placeholder in ("REFDES", "HVAL", "RVAL", "LAYERNAME"):
        assert placeholder not in tcl


def test_solder_growth_rejects_all_malformed_settings_with_diagnostics(caplog, modeler_factory):
    modeler = modeler_factory(
        modeler_cls=SpdModeler,
        settings={
            "GROWTOPSOLDER": "U1,0.3",
            "GROWBOTSOLDER": "J1,0.2,0.1,EXTRA",
        },
        solder_keys=["GROWTOPSOLDER", "GROWBOTSOLDER"],
    )

    with caplog.at_level("DEBUG", logger=modeler.lg.name):
        with pytest.raises(WrongGrowSolderFormat):
            modeler._SpdModeler__grow_solder_tcl()

    diagnostic = "\n".join(caplog.messages)
    assert "GrowTopSolder in the Tab Special_Settings" in diagnostic
    assert "GrowBotSolder in the Tab Special_Settings" in diagnostic
    assert "Refdes on top layer" in diagnostic
    assert "Refdes on bottom layer" in diagnostic


def test_net_group_tcl_substitutes_names_and_group(modeler_factory):
    modeler = modeler_factory(modeler_cls=PowersiPdnModeler)

    tcl = modeler._en_nets(["VDD_CPU", "VDD_SOC"], "PowerNets")

    assert "selected 1 VDD_CPU VDD_SOC" in tcl
    assert "move net {PowerNets} VDD_CPU VDD_SOC" in tcl
    assert "NETNAMES" not in tcl
    assert "GRPNETS" not in tcl


def test_pre_cut_tcl_converts_millimeters_to_meters(modeler_factory):
    modeler = modeler_factory(modeler_cls=PowersiPdnModeler, OPPRECUT=OP_PRECUT)

    tcl = modeler._precut([_sim_row(**{OP_PRECUT: "1, 2, 3, 4"})])

    assert "# precut" in tcl
    assert "-LeftPoint {0.001, 0.002}" in tcl
    assert "-RightPoint {0.003, 0.004}" in tcl
    assert "sigrity::process shape" in tcl
    for placeholder in ("LLX", "LLY", "URX", "URY"):
        assert placeholder not in tcl


def test_optional_disable_all_caps_emits_command_only_when_requested(modeler_factory):
    modeler = modeler_factory(modeler_cls=PowersiPdnModeler, OPDISALLCAPS=OP_DISALLCAPS)

    enabled_tcl = modeler._config_all_enabled_caps([_sim_row()])
    disabled_tcl = modeler._config_all_enabled_caps([_sim_row(**{OP_DISALLCAPS: "TRUE"})])

    assert enabled_tcl == ""
    assert "turn_off_all_enabled_caps" in disabled_tcl
