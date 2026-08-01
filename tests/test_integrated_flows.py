# SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for exact top-level integrated flow orchestration."""

from unittest.mock import MagicMock, call, sentinel

import pytest

from opensipi import integrated_flows


def _platform_double(monkeypatch):
    platform = MagicMock(spec=integrated_flows.Platform, name="platform")
    platform.input_data = {"settings": {"EXTRACTIONTOOL": sentinel.extraction_tool}}
    platform.parser.return_value = sentinel.executor
    platform.run.return_value = (sentinel.result_config, sentinel.report_config)
    platform.report.return_value = sentinel.report_path
    platform.export_upload_config.return_value = sentinel.upload_config
    constructor = MagicMock(name="Platform", return_value=platform)
    monkeypatch.setattr(integrated_flows, "Platform", constructor)
    return constructor, platform


def test_sim2report_calls_platform_in_exact_order_and_returns_report(
    monkeypatch,
):
    constructor, platform = _platform_double(monkeypatch)
    input_info = {"input_type": "csv", "input_dir": "/project/Sim_Input"}
    monitor_info = {"email": "owner@example.com", "op_pause_after_model_check": 0}

    result = integrated_flows.sim2report(input_info, monitor_info)

    constructor.assert_called_once_with(input_info)
    assert platform.mock_calls == [
        call.drop_dsn_file(sentinel.extraction_tool),
        call.parser(platform.input_data),
        call.run(sentinel.executor, monitor_info),
        call.report(sentinel.result_config, sentinel.report_config),
    ]
    assert result is sentinel.report_path


def test_sim2report_gsuites_calls_report_and_upload_in_exact_order_and_returns_none(
    monkeypatch,
):
    constructor, platform = _platform_double(monkeypatch)
    input_info = {
        "input_type": "gsheet",
        "input_url": "https://sheet.invalid/input",
        "output_type": "gdrive",
    }
    monitor_info = {"email": "owner@example.com", "op_pause_after_model_check": 0}

    result = integrated_flows.sim2report_gsuites(input_info, monitor_info)

    constructor.assert_called_once_with(input_info)
    assert platform.mock_calls == [
        call.drop_dsn_file(sentinel.extraction_tool),
        call.parser(platform.input_data),
        call.run(sentinel.executor, monitor_info),
        call.report(sentinel.result_config, sentinel.report_config),
        call.export_upload_config(sentinel.report_config),
        call.upload2drive(sentinel.upload_config),
    ]
    # The public docstring explicitly defines the Google flow's current contract as None.
    assert result is None


@pytest.mark.parametrize(
    ("flow_name", "failing_stage"),
    [
        ("sim2report", "constructor"),
        ("sim2report", "drop_dsn_file"),
        ("sim2report", "parser"),
        ("sim2report", "run"),
        ("sim2report", "report"),
        ("sim2report_gsuites", "constructor"),
        ("sim2report_gsuites", "drop_dsn_file"),
        ("sim2report_gsuites", "parser"),
        ("sim2report_gsuites", "run"),
        ("sim2report_gsuites", "report"),
        ("sim2report_gsuites", "export_upload_config"),
        ("sim2report_gsuites", "upload2drive"),
    ],
)
def test_integrated_flows_propagate_exceptions_and_stop_at_the_failing_stage(
    monkeypatch, flow_name, failing_stage
):
    constructor, platform = _platform_double(monkeypatch)
    if failing_stage == "constructor":
        constructor.side_effect = RuntimeError("constructor failed")
    else:
        getattr(platform, failing_stage).side_effect = RuntimeError(f"{failing_stage} failed")

    with pytest.raises(RuntimeError, match=f"{failing_stage} failed"):
        getattr(integrated_flows, flow_name)({"input_type": "fake"}, {"email": ""})

    constructor.assert_called_once_with({"input_type": "fake"})
    ordered_calls = [
        ("drop_dsn_file", call.drop_dsn_file(sentinel.extraction_tool)),
        ("parser", call.parser(platform.input_data)),
        ("run", call.run(sentinel.executor, {"email": ""})),
        ("report", call.report(sentinel.result_config, sentinel.report_config)),
    ]
    if flow_name == "sim2report_gsuites":
        ordered_calls.extend(
            [
                (
                    "export_upload_config",
                    call.export_upload_config(sentinel.report_config),
                ),
                ("upload2drive", call.upload2drive(sentinel.upload_config)),
            ]
        )
    if failing_stage == "constructor":
        assert platform.mock_calls == []
    else:
        failing_index = [name for name, _ in ordered_calls].index(failing_stage)
        assert platform.mock_calls == [item for _, item in ordered_calls[: failing_index + 1]]
