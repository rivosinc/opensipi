# SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Shared pytest fixtures for OpenSIPI characterization tests."""

import csv
import logging
import os
from pathlib import Path

import pytest
from ruamel.yaml import YAML

os.environ["MPLBACKEND"] = "Agg"


@pytest.fixture
def repo_root() -> Path:
    """Return the repository root as an absolute path."""
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def temp_csv_builder(tmp_path):
    """Return a builder that writes CSV rows below ``tmp_path``."""

    def build(rows, name="input.csv"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as csv_file:
            csv.writer(csv_file).writerows(rows)
        return path

    return build


@pytest.fixture
def table_builder(tmp_path):
    """Return a builder that writes regular header-plus-body CSV tables."""

    def build(headers=None, rows=None, name="table.csv"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        table = [list(headers or ["NAME", "VALUE"]), *[list(row) for row in (rows or [])]]
        with path.open("w", encoding="utf-8", newline="") as table_file:
            csv.writer(table_file).writerows(table)
        return path

    return build


@pytest.fixture
def temp_config_builder(tmp_path):
    """Return a builder that writes plain YAML configuration data."""

    def build(data=None, name="config.yaml"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        yaml = YAML(typ="safe")
        with path.open("w", encoding="utf-8") as config_file:
            yaml.dump(data or {}, config_file)
        return path

    return build


@pytest.fixture
def mock_logger():
    """Return a minimal logger double for domain diagnostics."""
    from unittest.mock import Mock

    return Mock(spec=logging.Logger)


@pytest.fixture
def logger_cleanup():
    """Track loggers and close and remove their handlers after a test."""
    tracked = []

    def track(logger):
        tracked.append(logger)
        return logger

    yield track

    for logger in tracked:
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()


def _bare_instance(cls, defaults, overrides):
    instance = object.__new__(cls)
    for name, value in {**defaults, **overrides}.items():
        setattr(instance, name, value)
    return instance


@pytest.fixture
def file_in_factory():
    """Create a ``FileIn`` without reading CSV files or Google Sheets."""

    def build(**attrs):
        from opensipi.constants.CONSTANTS import INPUT_FILE_STARTSWITH
        from opensipi.file_in import FileIn

        return _bare_instance(
            FileIn,
            {
                "INPUT_TYPE": "CSV",
                "INPUT_FILE_STARTSWITH": list(INPUT_FILE_STARTSWITH),
                "INPUT_DATA": {
                    "sim_input": {},
                    "all_input": {},
                    "stackup_info": {},
                    "settings": {},
                    "spectype_info": {},
                },
            },
            attrs,
        )

    return build


@pytest.fixture
def modeler_factory():
    """Create a modeler without writing Tcl or launching solver behavior."""

    def build(modeler_cls=None, **attrs):
        if modeler_cls is None:
            from opensipi.sigrity_tools import PowersiPdnModeler

            modeler_cls = PowersiPdnModeler
        return _bare_instance(
            modeler_cls,
            {
                "settings": {},
                "sim_input": {},
                "all_input": {},
                "SPECTYPE_INFO": {},
                "CONNECTIVITY": {},
                "lg": logging.getLogger("opensipi.tests.modeler"),
            },
            attrs,
        )

    return build


@pytest.fixture
def executor_factory():
    """Create an executor without generating Tcl or starting processes."""

    def build(executor_cls=None, **attrs):
        if executor_cls is None:
            from opensipi.sigrity_exec import PowersiPdnExec

            executor_cls = PowersiPdnExec
        return _bare_instance(
            executor_cls,
            {
                "sim_input": {},
                "all_input": {},
                "run_info": {},
                "result_sub_dirs": {},
                "lg": logging.getLogger("opensipi.tests.executor"),
            },
            attrs,
        )

    return build


@pytest.fixture
def touchstone_factory():
    """Create a ``TouchStone`` without reading a network file."""

    def build(**attrs):
        from opensipi.touchstone import TouchStone

        return _bare_instance(
            TouchStone,
            {
                "MM_KEY": ["IL_MM", "RL_MM"],
                "file_dir": "",
                "key_name": "test_key",
                "plt_dir": "",
                "spec_type": {"POST_PROCESS_KEY": []},
                "conn_dict": {},
                "nw": None,
                "nw_mm": None,
                "f": [],
                "port_num": 0,
                "short0": None,
            },
            attrs,
        )

    return build


@pytest.fixture
def platform_factory():
    """Create a ``Platform`` without creating folders or external clients."""

    def build(**attrs):
        from opensipi.sipi_infra import Platform

        return _bare_instance(
            Platform,
            {
                "INPUT_TYPE": "CSV",
                "RUN_NAME": "TEST_RUN",
                "input_data": {},
                "filein_info": {},
                "fileout_info": {"output_type": "local"},
                "DSN_NAME": "",
                "LOC_DSN_RAW": "",
                "lg": logging.getLogger("opensipi.tests.platform"),
            },
            attrs,
        )

    return build
