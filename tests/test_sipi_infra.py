# SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Hermetic characterization tests for Platform orchestration."""

import logging
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock, call, sentinel

import pytest

from opensipi import sipi_infra
from opensipi.sipi_infra import Platform
from opensipi.templates import temp_report
from opensipi.util.common import SL
from opensipi.util.exceptions import NoDsnFound, NoProjDirDefined


def _constructor_paths():
    return tuple(f"/run/path_{index}{SL}" for index in range(10))


def _patch_platform_constructor(monkeypatch, run_time="STAMP"):
    logger = Mock(spec=logging.Logger)
    get_run_time = Mock(return_value=run_time)
    monkeypatch.setattr(sipi_infra, "get_dir", lambda: ("/install/", "/scripts/", "/templates/"))
    monkeypatch.setattr(sipi_infra, "get_root_dir", lambda: "/root/")
    monkeypatch.setattr(sipi_infra, "make_dir", Mock())
    monkeypatch.setattr(sipi_infra, "get_run_time", get_run_time)
    monkeypatch.setattr(sipi_infra, "setup_logger", Mock(return_value=logger))
    monkeypatch.setattr(Platform, "_get_filein_info", lambda self, info: {"input_type": "CSV"})
    monkeypatch.setattr(Platform, "_get_fileout_info", lambda self, info: {"output_type": "local"})
    monkeypatch.setattr(
        Platform,
        "_read_inputs",
        lambda self: {"settings": {"EXTRACTIONTYPE": "pdn"}},
    )
    monkeypatch.setattr(Platform, "_get_proj_dir", lambda self, info: ("/project/", "project"))
    monkeypatch.setattr(Platform, "_mk_proj_dir", lambda self, proj_dir, name: _constructor_paths())
    return get_run_time, logger


@pytest.mark.parametrize(
    ("extra_info", "expected_name", "expected_time_calls"),
    [
        ({}, "PDN_STAMP", 2),
        ({"op_run_name": ""}, "PDN_STAMP", 2),
        ({"op_run_name": "PDN_20250101_120000"}, "PDN_20250101_120000", 1),
    ],
)
def test_platform_selects_new_or_resumed_run_name(
    monkeypatch, extra_info, expected_name, expected_time_calls
):
    get_run_time, logger = _patch_platform_constructor(monkeypatch)

    platform = Platform({"input_type": "csv", **extra_info})

    assert platform.RUN_NAME == expected_name
    assert get_run_time.call_count == expected_time_calls
    assert platform.DSN_NAME == ""
    assert platform.LOC_DSN_RAW == ""
    logger.debug.assert_any_call("Log file for Run_STAMP is created.")


def test_get_proj_dir_prefers_explicit_project_directory(platform_factory, tmp_path):
    project = tmp_path / "Apollo"
    project.mkdir()
    platform = platform_factory()

    assert platform._get_proj_dir({"proj_dir": f"{project}{SL}"}) == (
        f"{project}{SL}",
        "Apollo",
    )


def test_get_proj_dir_derives_project_from_sim_input_directory(platform_factory, tmp_path):
    project = tmp_path / "Apollo"
    input_dir = project / "Sim_Input"
    input_dir.mkdir(parents=True)
    platform = platform_factory()

    assert platform._get_proj_dir({"input_dir": str(input_dir)}) == (
        f"{project}{SL}",
        "Apollo",
    )


def test_get_proj_dir_requires_explicit_or_derived_directory(platform_factory):
    platform = platform_factory()

    with pytest.raises(NoProjDirDefined):
        platform._get_proj_dir({})


def test_get_filein_info_builds_csv_input_location(platform_factory, tmp_path):
    platform = platform_factory(INPUT_TYPE="CSV")

    info = platform._get_filein_info(
        {"input_dir": str(tmp_path / "Sim_Input"), "input_folder": "Sigrity_PDN"}
    )

    assert info == {
        "input_type": "CSV",
        "input_dir": f"{tmp_path / 'Sim_Input' / 'Sigrity_PDN'}{SL}",
        "input_file_startswith": sipi_infra.INPUT_FILE_STARTSWITH,
    }


def test_get_filein_info_builds_gsheet_input_from_config(monkeypatch, platform_factory, tmp_path):
    config_dir = f"{tmp_path}{SL}"
    config = {
        "ACCOUNT_KEY_DIR": "~/credentials/account.json",
        "ACCOUNT_TYPE": "service_account",
    }
    load_config = Mock(return_value=config)
    monkeypatch.setattr(sipi_infra, "load_yaml_to_dict", load_config)
    monkeypatch.setattr(sipi_infra, "expand_home_dir", lambda path: f"EXPANDED:{path}")
    platform = platform_factory(INPUT_TYPE="GSHEET", TOOL_CONFIG_DIR=config_dir)

    info = platform._get_filein_info({"input_url": "https://sheet.invalid/input"})

    load_config.assert_called_once_with(f"{config_dir}config_gsuites.yaml")
    assert info == {
        "input_type": "GSHEET",
        "account_key": "EXPANDED:~/credentials/account.json",
        "account_type": "service_account",
        "sheet_url": "https://sheet.invalid/input",
        "input_file_startswith": sipi_infra.INPUT_FILE_STARTSWITH,
    }


def test_get_fileout_info_defaults_to_local_without_reading_google_config(
    monkeypatch, platform_factory
):
    load_config = Mock()
    monkeypatch.setattr(sipi_infra, "load_yaml_to_dict", load_config)
    platform = platform_factory()

    assert platform._get_fileout_info({}) == {"output_type": "local"}
    load_config.assert_not_called()


def test_get_fileout_info_builds_gdrive_output_from_config(monkeypatch, platform_factory, tmp_path):
    config_dir = f"{tmp_path}{SL}"
    config = {
        "ACCOUNT_KEY_DIR": "~/credentials/account.json",
        "ACCOUNT_TYPE": "service_account",
        "ROOT_GDRIVE_ID": "root-drive",
        "OUT_SHEET_GDRIVE_ID": "summary-drive",
    }
    monkeypatch.setattr(sipi_infra, "load_yaml_to_dict", Mock(return_value=config))
    monkeypatch.setattr(sipi_infra, "expand_home_dir", lambda path: f"EXPANDED:{path}")
    platform = platform_factory(TOOL_CONFIG_DIR=config_dir)

    assert platform._get_fileout_info({"output_type": "gdrive"}) == {
        "output_type": "gdrive",
        "account_key": "EXPANDED:~/credentials/account.json",
        "account_type": "service_account",
        "root_drive_id": "root-drive",
        "out_sheet_gdrive_id": "summary-drive",
    }


def test_mk_proj_dir_creates_deterministic_run_tree(platform_factory, tmp_path):
    platform = platform_factory()
    project_dir = f"{tmp_path}{SL}"

    paths = platform._mk_proj_dir(project_dir, "PDN_TEST")

    run_dir = tmp_path / "Xtract" / "Run_PDN_TEST"
    expected_return = (
        f"{tmp_path / 'Dsn'}{SL}",
        f"{run_dir / 'LocalDsn'}{SL}",
        f"{run_dir / 'LocalScript'}{SL}",
        f"{run_dir / 'SimFile'}{SL}",
        f"{run_dir / 'Result'}{SL}",
        f"{run_dir / 'Report'}{SL}",
        f"{run_dir / 'Log'}{SL}",
        f"{run_dir / 'Report' / 'Plot'}{SL}",
        f"{run_dir / 'LocalScript' / 'RunKey'}{SL}",
        f"{run_dir / 'SimFile' / 'ModelCheck'}{SL}",
    )
    assert paths == expected_return
    expected_directories = {
        Path("Dsn"),
        Path("Dsn/Archive"),
        Path("Xtract"),
        Path("Xtract/Run_PDN_TEST"),
        Path("Xtract/Run_PDN_TEST/LocalDsn"),
        Path("Xtract/Run_PDN_TEST/LocalScript"),
        Path("Xtract/Run_PDN_TEST/LocalScript/RunKey"),
        Path("Xtract/Run_PDN_TEST/SimFile"),
        Path("Xtract/Run_PDN_TEST/SimFile/ModelCheck"),
        Path("Xtract/Run_PDN_TEST/Result"),
        Path("Xtract/Run_PDN_TEST/Report"),
        Path("Xtract/Run_PDN_TEST/Report/Plot"),
        Path("Xtract/Run_PDN_TEST/Log"),
    }
    assert {path.relative_to(tmp_path) for path in tmp_path.rglob("*") if path.is_dir()} == (
        expected_directories
    )


def _design_platform(platform_factory, tmp_path):
    design_dir = tmp_path / "Dsn"
    local_dir = tmp_path / "LocalDsn"
    design_dir.mkdir()
    local_dir.mkdir()
    return platform_factory(
        DSN_DIR=f"{design_dir}{SL}",
        LOC_DSN_DIR=f"{local_dir}{SL}",
        lg=Mock(spec=logging.Logger),
    )


def test_make_local_design_copy_preserves_existing_resumed_copy(platform_factory, tmp_path):
    platform = _design_platform(platform_factory, tmp_path)
    platform.DSN_NAME = "board.brd"
    platform.LOC_DSN_RAW = "board.brd"
    source = Path(platform.DSN_DIR) / platform.DSN_NAME
    destination = Path(platform.LOC_DSN_DIR) / platform.LOC_DSN_RAW
    source.write_text("original", encoding="utf-8")

    platform._Platform__mk_local_dsn_copy()
    source.write_text("changed source", encoding="utf-8")
    platform._Platform__mk_local_dsn_copy()

    assert destination.read_text(encoding="utf-8") == "original"


def test_drop_dsn_file_selects_single_design_and_copies_it(monkeypatch, platform_factory, tmp_path):
    platform = _design_platform(platform_factory, tmp_path)
    source = Path(platform.DSN_DIR) / "board.brd"
    source.write_text("design", encoding="utf-8")
    user_input = Mock(return_value="y")
    monkeypatch.setattr("builtins.input", user_input)

    platform.drop_dsn_file("Sigrity")

    assert platform.DSN_NAME == "board.brd"
    assert platform.LOC_DSN_RAW == "board.brd"
    assert (Path(platform.LOC_DSN_DIR) / "board.brd").read_text(encoding="utf-8") == "design"
    user_input.assert_called_once()


def test_drop_dsn_file_raises_when_no_design_exists(monkeypatch, platform_factory, tmp_path):
    platform = _design_platform(platform_factory, tmp_path)
    monkeypatch.setattr("builtins.input", Mock(return_value="y"))

    with pytest.raises(NoDsnFound):
        platform.drop_dsn_file("Sigrity")


def test_drop_dsn_file_uses_numeric_selection_for_multiple_designs(
    monkeypatch, platform_factory, tmp_path
):
    platform = _design_platform(platform_factory, tmp_path)
    (Path(platform.DSN_DIR) / "first.brd").write_text("first", encoding="utf-8")
    (Path(platform.DSN_DIR) / "second.mcm").write_text("second", encoding="utf-8")
    user_input = Mock(side_effect=["y", "2"])
    monkeypatch.setattr("builtins.input", user_input)

    platform.drop_dsn_file("Sigrity")

    assert platform.DSN_NAME == "second.mcm"
    assert platform.LOC_DSN_RAW == "second.mcm"
    assert (Path(platform.LOC_DSN_DIR) / "second.mcm").read_text(encoding="utf-8") == "second"
    assert user_input.call_count == 2


def test_get_key2sim_filters_completed_done_markers(platform_factory, tmp_path):
    platform = platform_factory(lg=Mock(spec=logging.Logger))
    (tmp_path / "rail_done.done").write_text("", encoding="utf-8")
    (tmp_path / "unrelated.txt").write_text("", encoding="utf-8")

    remaining = platform._Platform__get_key2sim(
        f"{tmp_path}{SL}", ["rail_done", "rail_pending", "rail_other"]
    )

    assert remaining == ["rail_pending", "rail_other"]


def test_get_all_dcr_dict_groups_only_non_ambiguous_sheet_keys(platform_factory):
    platform = platform_factory()
    sim_input = {
        "[POWER]_VDD": [],
        "[POWER]_VDDQ": [],
        "[IO]_VTT": [],
    }

    grouped, sheet_keys = platform._Platform__get_all_dcr_dict(sim_input)

    assert sheet_keys == ["[POWER]", "[IO]"]
    assert grouped == {
        "[POWER]": ["[POWER]_VDD", "[POWER]_VDDQ"],
        "[IO]": ["[IO]_VTT"],
    }


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="BUG: DCR grouping uses substring matching and cross-contaminates sheet prefixes",
)
def test_get_all_dcr_dict_keeps_ambiguous_sheet_prefixes_separate(platform_factory):
    platform = platform_factory()
    sim_input = {"[A]_x": [], "[A][B]_y": []}

    grouped, _ = platform._Platform__get_all_dcr_dict(sim_input)

    assert grouped == {"[A]": ["[A]_x"], "[A][B]": ["[A][B]_y"]}


def _parser_platform(platform_factory, tmp_path):
    run_dirs = {}
    for name in [
        "dsn",
        "local_dsn",
        "local_script",
        "sim",
        "result",
        "plot",
        "report",
        "template",
        "run_key",
        "model_check",
        "tool_config",
    ]:
        path = tmp_path / name
        path.mkdir()
        run_dirs[name] = f"{path}{SL}"
    return platform_factory(
        RUN_NAME="RUN_TEST",
        TOOL_CONFIG_DIR=run_dirs["tool_config"],
        DSN_DIR=run_dirs["dsn"],
        DSN_NAME="board.brd",
        LOC_DSN_RAW="board.brd",
        LOC_DSN_DIR=run_dirs["local_dsn"],
        LOC_SCRIPT_DIR=run_dirs["local_script"],
        SIM_DIR=run_dirs["sim"],
        RESULT_DIR=run_dirs["result"],
        PLT_DIR=run_dirs["plot"],
        REPORT_DIR=run_dirs["report"],
        TEMPLATE_DIR=run_dirs["template"],
        RUN_KEY_DIR=run_dirs["run_key"],
        MODEL_CHECK_DIR=run_dirs["model_check"],
        lg=Mock(spec=logging.Logger),
    )


@pytest.mark.parametrize(
    ("extraction_type", "executor_name"),
    [
        ("PDN", "PowersiPdnExec"),
        ("HSIO", "ClarityExec"),
        ("LSIO", "PowersiIOExec"),
        ("DCR", "PowerdcExec"),
    ],
)
def test_parser_maps_each_sigrity_extraction_to_its_executor(
    monkeypatch, platform_factory, tmp_path, extraction_type, executor_name
):
    platform = _parser_platform(platform_factory, tmp_path)
    executor_factory = Mock(return_value=sentinel.executor)
    monkeypatch.setattr(sipi_infra, executor_name, executor_factory)
    sim_input = (
        {"[POWER]_VDD": [{}], "[IO]_VTT": [{}]}
        if extraction_type == "DCR"
        else {"SIM_A": [{}], "SIM_B": [{}]}
    )
    input_data = {
        "settings": {
            "EXTRACTIONTOOL": "Sigrity",
            "EXTRACTIONTYPE": extraction_type,
        },
        "sim_input": sim_input,
        "all_input": deepcopy(sim_input),
        "stackup_info": {"layers": []},
        "spectype_info": {"ZPDN": {"POST_PROCESS_KEY": ["ZOPEN"]}},
    }

    result = platform.parser(input_data)

    assert result is sentinel.executor
    executor_factory.assert_called_once()
    model_info = executor_factory.call_args.args[0]
    expected_keys = ["[POWER]", "[IO]"] if extraction_type == "DCR" else ["SIM_A", "SIM_B"]
    assert model_info["key2check"] == expected_keys
    assert model_info["key2sim"] == expected_keys
    assert model_info["settings"] is input_data["settings"]
    assert model_info["log"] is platform.lg
    if extraction_type == "DCR":
        assert model_info["dcr_dict"] == {
            "[POWER]": ["[POWER]_VDD"],
            "[IO]": ["[IO]_VTT"],
        }
    else:
        assert model_info["dcr_dict"] == {}


def test_run_delegates_to_executor_and_returns_config_paths(platform_factory):
    platform = platform_factory()
    executor = Mock()
    executor.run.return_value = ("result.yaml", "report.yaml")
    monitor_info = {"email": "owner@example.com", "op_pause_after_model_check": 0}

    assert platform.run(executor, monitor_info) == ("result.yaml", "report.yaml")
    executor.run.assert_called_once_with(monitor_info)


def test_get_plt_list_filters_unchecked_snp_files_and_builds_touchstone_info(
    platform_factory, tmp_path
):
    result_dir = tmp_path / "SNP_S"
    plot_dir = tmp_path / "Plot"
    result_dir.mkdir()
    plot_dir.mkdir()
    checked = result_dir / "SIM_A__S.s2p"
    checked.write_text("touchstone", encoding="utf-8")
    (result_dir / "SIM_OLD__S.S4P").write_text("stale", encoding="utf-8")
    (result_dir / "notes.txt").write_text("ignore", encoding="utf-8")
    platform = platform_factory(lg=Mock(spec=logging.Logger))
    spec_type = {"POST_PROCESS_KEY": ["IL"]}
    connectivity = {"IL": [[1, 2]]}
    result_config = {
        "result_sub_dirs": {"SNP_S": f"{result_dir}{SL}"},
        "plot_dir": f"{plot_dir}{SL}",
        "checked_keys": ["SIM_A"],
        "spectype": {"SIM_A": spec_type, "SIM_OLD": spec_type},
        "CONNECTIVITY": {"SIM_A": connectivity, "SIM_OLD": connectivity},
    }

    assert platform._get_plt_list("SNP_S", result_config) == [
        {
            "file_dir": str(checked),
            "key_name": "SNP_S__SIM_A",
            "plt_dir": f"{plot_dir}{SL}",
            "spec_type": spec_type,
            "snp_name": "SIM_A__S.s2p",
            "conn_dict": connectivity,
        }
    ]


def test_snp_plot_xtract_processes_touchstones_and_keys_output_by_touchstone_name(
    monkeypatch, platform_factory
):
    platform = platform_factory()
    plot_list = [{"file_dir": "first.s2p"}, {"file_dir": "second.s4p"}]
    monkeypatch.setattr(platform, "_get_plt_list", Mock(return_value=plot_list))
    first = Mock(key_name="SNP_S__SIM_A")
    first.auto_process.return_value = {"IL": [["a", "a.png"]]}
    second = Mock(key_name="SNP_S__SIM_B")
    second.auto_process.return_value = {"RL": [["b", "b.png"]]}
    from_list = Mock(return_value=[first, second])
    monkeypatch.setattr(sipi_infra.TouchStone, "from_list", from_list)

    output = platform._Platform__snp_plot_xtract("SNP_S", {"result_sub_dirs": {}})

    from_list.assert_called_once_with(plot_list)
    assert output == {
        "SNP_S__SIM_A": {"IL": [["a", "a.png"]]},
        "SNP_S__SIM_B": {"RL": [["b", "b.png"]]},
    }
    first.auto_process.assert_called_once_with()
    second.auto_process.assert_called_once_with()


def test_process_snp_loads_config_and_processes_each_result_subdirectory(
    monkeypatch, platform_factory
):
    platform = platform_factory()
    result_config = {"result_sub_dirs": {"SNP_S": "/s/", "SNP_DC": "/dc/"}}
    load_config = Mock(return_value=result_config)
    process_folder = Mock(side_effect=[{"a": 1}, {"b": 2}])
    monkeypatch.setattr(sipi_infra, "load_yaml_to_dict", load_config)
    monkeypatch.setattr(sipi_infra, "expand_home_dir", lambda path: path)
    monkeypatch.setattr(platform, "_Platform__snp_plot_xtract", process_folder)

    assert platform.process_snp("result.yaml") == {
        "SNP_S": {"a": 1},
        "SNP_DC": {"b": 2},
    }
    load_config.assert_called_once_with("result.yaml")
    assert process_folder.call_args_list == [
        call("SNP_S", result_config),
        call("SNP_DC", result_config),
    ]


def _report_config(report_type, output_path):
    return {
        "report_type": report_type,
        "sim_date": "2025-01-02 03:04:05",
        "usr_id": "engineer",
        "proj_name": "Apollo",
        "xtract_tool": "Sigrity",
        "xtract_type": report_type,
        "dsn_name": "board.brd",
        "report_full_path": str(output_path),
        "logoimg_dir": "logo.png",
    }


@pytest.mark.parametrize(
    ("report_type", "template_name", "generator_name"),
    [
        ("PDN", "pdn_report", "_Platform__gen_pdn_report"),
        ("IO", "io_report", "_Platform__gen_io_report"),
    ],
)
def test_report_dispatches_pdn_and_io_to_matching_deep_copied_template(
    monkeypatch,
    platform_factory,
    tmp_path,
    report_type,
    template_name,
    generator_name,
):
    output_path = tmp_path / f"{report_type.lower()}.pdf"
    config = _report_config(report_type, output_path)
    result_dict = {"SNP_S": {}}
    platform = platform_factory(lg=Mock(spec=logging.Logger))
    generator = Mock()
    copied_template = deepcopy(getattr(temp_report, template_name))
    monkeypatch.setattr(sipi_infra, template_name, copied_template)
    monkeypatch.setattr(sipi_infra, "load_yaml_to_dict", Mock(return_value=config))
    monkeypatch.setattr(sipi_infra, "expand_home_dir", lambda path: path)
    monkeypatch.setattr(platform, "process_snp", Mock(return_value=result_dict))
    monkeypatch.setattr(platform, generator_name, generator)

    assert platform.report("result.yaml", "report.yaml") == str(output_path)

    summary = [
        ["Simulation Start Time", "2025-01-02 03:04:05"],
        ["Author", "engineer"],
        ["Project Name", "Apollo"],
        ["Extraction Tool", "Sigrity"],
        ["Extraction Type", report_type],
        ["Design File", "board.brd"],
    ]
    generator.assert_called_once_with(copied_template, summary, result_dict, str(output_path))


@pytest.mark.parametrize(
    ("generator_name", "template", "result_dict"),
    [
        (
            "_Platform__gen_pdn_report",
            temp_report.pdn_report,
            {"SNP_S": {"SNP_S__SIM_A": {"ZOPEN": [["zin", "zin.png", "", "12.3", "4.5"]]}}},
        ),
        (
            "_Platform__gen_io_report",
            temp_report.io_report,
            {"SNP_S": {"SNP_S__SIM_A": {"IL": [["loss", "loss.png"]]}}},
        ),
    ],
)
def test_pdf_report_generation_uses_isolated_template_and_mocked_pdfme(
    monkeypatch, platform_factory, tmp_path, generator_name, template, result_dict
):
    platform = platform_factory()
    report_copy = deepcopy(template)
    production_snapshot = deepcopy(template)
    build_pdf = Mock()
    monkeypatch.setattr(sipi_infra, "build_pdf", build_pdf)
    output_path = tmp_path / "report.pdf"
    summary = [["Project Name", "Apollo"]]

    getattr(platform, generator_name)(report_copy, summary, result_dict, str(output_path))

    assert template == production_snapshot
    assert summary[-1] in report_copy["sections"][0]["content"][0]["table"]
    assert build_pdf.call_count == 1
    assert build_pdf.call_args.args[0] is report_copy
    assert output_path.exists()


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="BUG: report() mutates module-level templates and accumulates data across calls",
)
def test_repeated_report_calls_leave_module_template_unchanged(
    monkeypatch, platform_factory, tmp_path
):
    platform = platform_factory(lg=Mock(spec=logging.Logger))
    output_path = tmp_path / "pdn.pdf"
    config = _report_config("PDN", output_path)
    result_dict = {"SNP_S": {"SIM_A": {"ZOPEN": [["zin", "zin.png", "", "12.3", "4.5"]]}}}
    original = deepcopy(sipi_infra.pdn_report)
    monkeypatch.setattr(sipi_infra, "load_yaml_to_dict", Mock(return_value=config))
    monkeypatch.setattr(sipi_infra, "expand_home_dir", lambda path: path)
    monkeypatch.setattr(platform, "process_snp", Mock(return_value=result_dict))
    monkeypatch.setattr(sipi_infra, "build_pdf", Mock())

    try:
        platform.report("result.yaml", "report.yaml")
        platform.report("result.yaml", "report.yaml")
        assert sipi_infra.pdn_report == original
    finally:
        sipi_infra.pdn_report.clear()
        sipi_infra.pdn_report.update(original)


@pytest.mark.parametrize(
    ("report_type", "generator_name"),
    [
        ("PDN", "_Platform__gen_pdn_html_report"),
        ("IO", "_Platform__gen_io_html_report"),
    ],
)
def test_report_html_dispatches_with_jinja_and_pdf_conversion_boundaries_mocked(
    monkeypatch, platform_factory, tmp_path, report_type, generator_name
):
    output_path = tmp_path / f"{report_type.lower()}.pdf"
    config = _report_config(report_type, output_path)
    result_dict = {"SNP_S": {}}
    platform = platform_factory(lg=Mock(spec=logging.Logger))
    generator = Mock()
    converter = Mock()
    monkeypatch.setattr(sipi_infra, "load_yaml_to_dict", Mock(return_value=config))
    monkeypatch.setattr(sipi_infra, "expand_home_dir", lambda path: path)
    monkeypatch.setattr(sipi_infra, "img2str", Mock(return_value="encoded-logo"))
    monkeypatch.setattr(platform, "process_snp", Mock(return_value=result_dict))
    monkeypatch.setattr(platform, generator_name, generator)
    monkeypatch.setattr(platform, "convert_html_to_pdf_report", converter)

    assert platform.report_html("result.yaml", "report.yaml") == str(output_path)

    html_path = str(output_path).replace(".pdf", ".html")
    summary = [
        ["Simulation Start Time", "2025-01-02 03:04:05"],
        ["Author", "engineer"],
        ["Project Name", "Apollo"],
        ["Extraction Tool", "Sigrity"],
        ["Extraction Type", report_type],
        ["Design File", "board.brd"],
    ]
    generator.assert_called_once_with(
        summary,
        result_dict,
        {"company_logo": "encoded-logo"},
        html_path,
    )
    converter.assert_called_once_with(html_path, str(output_path))


def test_html_generator_renders_through_mocked_jinja_environment(
    monkeypatch, platform_factory, tmp_path
):
    platform = platform_factory(TEMPLATE_DIR=f"{tmp_path}{SL}")
    template = Mock()
    template.render.return_value = "<html>report</html>"
    environment = Mock()
    environment.get_template.return_value = template
    monkeypatch.setattr(sipi_infra.jinja2, "Environment", Mock(return_value=environment))
    output_path = tmp_path / "report.html"
    summary = [["Project Name", "Apollo"]]
    result_dict = {"SNP_S": {}}
    misc_dict = {"company_logo": "encoded-logo"}

    platform._Platform__gen_pdn_html_report(summary, result_dict, misc_dict, str(output_path))

    environment.get_template.assert_called_once_with("PDN_Type1.html")
    template.render.assert_called_once_with(
        {
            "summary_list": summary,
            "logo_img": "encoded-logo",
            "result_dict": result_dict,
        }
    )
    assert output_path.read_text(encoding="utf-8") == "<html>report</html>"


def test_convert_html_to_pdf_uses_expected_options_without_running_wkhtmltopdf(
    monkeypatch, platform_factory, tmp_path
):
    html_path = tmp_path / "report.html"
    pdf_path = tmp_path / "report.pdf"
    html_path.write_text("<html>report</html>", encoding="utf-8")
    from_file = Mock(return_value=True)
    monkeypatch.setattr(sipi_infra.pdfkit, "from_file", from_file)
    platform = platform_factory()

    platform.convert_html_to_pdf_report(str(html_path), str(pdf_path))

    from_file.assert_called_once()
    html_file, passed_pdf = from_file.call_args.args
    assert Path(html_file.name) == html_path
    assert passed_pdf == str(pdf_path)
    assert from_file.call_args.kwargs == {
        "options": {"page-size": "A4", "enable-local-file-access": True}
    }


def test_export_upload_config_combines_fresh_output_and_report_data(
    monkeypatch, platform_factory, tmp_path
):
    report_dir = tmp_path / "Report"
    report_dir.mkdir()
    platform = platform_factory(
        fileout_info={
            "output_type": "gdrive",
            "account_key": "account.json",
            "root_drive_id": "root",
        },
        TOOL_CONFIG_DIR=f"{tmp_path / 'config'}{SL}",
        REPORT_DIR=f"{report_dir}{SL}",
    )
    report_config = {
        "proj_name": "Apollo",
        "xtract_type": "PDN",
        "sim_date": "2025-01-02",
        "usr_id": "engineer",
        "design_type": "PACKAGE",
        "report_full_path": "~/report.pdf",
        "report_dir": "~/Report/",
        "result_dir": "~/Result/",
    }
    export_yaml = Mock()
    monkeypatch.setattr(sipi_infra, "load_yaml_to_dict", Mock(return_value=report_config))
    monkeypatch.setattr(sipi_infra, "expand_home_dir", lambda path: f"EXPANDED:{path}")
    monkeypatch.setattr(sipi_infra, "export_dict_to_yaml", export_yaml)

    output = platform.export_upload_config("report_config.yaml")

    expected_path = f"{report_dir}{SL}upload_config.yaml"
    assert output == expected_path
    export_yaml.assert_called_once_with(
        {
            "output_type": "gdrive",
            "account_key": "account.json",
            "root_drive_id": "root",
            "proj_name": "Apollo",
            "xtract_type": "PDN",
            "sim_type_name": "Xtract",
            "run_time": "2025-01-02",
            "usr_id": "engineer",
            "design_type": "PACKAGE",
            "report_full_path": "EXPANDED:~/report.pdf",
            "report_dir": "EXPANDED:~/Report/",
            "result_dir": "EXPANDED:~/Result/",
            "tool_config_dir": f"{tmp_path / 'config'}{SL}",
        },
        expected_path,
    )


@pytest.mark.parametrize(("output_type", "delegates"), [("local", False), ("gdrive", True)])
def test_upload2drive_is_local_noop_or_delegates_to_mocked_google_boundary(
    monkeypatch, platform_factory, output_type, delegates
):
    upload_config = {"output_type": output_type, "complete": "fake"}
    upload_to_google = Mock()
    monkeypatch.setattr(sipi_infra, "load_yaml_to_dict", Mock(return_value=upload_config))
    platform = platform_factory()
    monkeypatch.setattr(platform, "_Platform__upload2gdrive", upload_to_google)

    assert platform.upload2drive("upload.yaml") is None

    if delegates:
        upload_to_google.assert_called_once_with(upload_config)
    else:
        upload_to_google.assert_not_called()
