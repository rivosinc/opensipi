# SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Characterization tests for OpenSIPI logger setup."""

import logging

from opensipi.util import logs


def test_setup_logger_configures_file_and_stdout_handlers(tmp_path, capsys, logger_cleanup):
    log_path = tmp_path / "run.log"
    logger = logger_cleanup(logs.setup_logger(log_path, f"opensipi.test.{tmp_path.name}"))

    assert logger.level == logging.DEBUG
    assert logger.propagate is False
    assert len(logger.handlers) == 2
    assert sum(isinstance(handler, logging.FileHandler) for handler in logger.handlers) == 1
    assert (
        sum(
            isinstance(handler, logging.StreamHandler)
            and not isinstance(handler, logging.FileHandler)
            for handler in logger.handlers
        )
        == 1
    )
    assert all(handler.level == logging.DEBUG for handler in logger.handlers)

    logger.debug("characterized output")
    for handler in logger.handlers:
        handler.flush()

    stdout = capsys.readouterr().out
    file_output = log_path.read_text(encoding="utf-8")
    assert "[opensipi.test." in stdout
    assert "characterized output" in stdout
    assert "[opensipi.test." in file_output
    assert "characterized output" in file_output


def test_setup_logger_prints_oserror_and_returns_unhandled_logger(
    tmp_path, monkeypatch, capsys, logger_cleanup
):
    def fail_file_handler(path):
        raise OSError("read-only filesystem")

    monkeypatch.setattr(logs.logging, "FileHandler", fail_file_handler)
    logger = logger_cleanup(
        logs.setup_logger(tmp_path / "unwritable.log", f"opensipi.test.fallback.{tmp_path.name}")
    )

    assert logger.level == logging.DEBUG
    assert logger.propagate is False
    assert logger.handlers == []
    assert capsys.readouterr().out == (
        "Failed to set up log file due to error: read-only filesystem. Continuing anyway.\n"
    )
