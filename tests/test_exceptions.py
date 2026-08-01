# SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Characterization tests for reporting exception side effects."""

from unittest.mock import Mock

import pytest

from opensipi.util import exceptions


@pytest.mark.parametrize(
    ("exception_type", "message"),
    [
        (
            exceptions.NoLegalSimWbFound,
            "No legal sim workbook is found! Check if the workbook title is correct.",
        ),
        (exceptions.NoSimRowFound, "No sim row is found in the sim workbook!"),
        (
            exceptions.NoneUniqueKeyDefined,
            "None unique key is defined for power rails in the same workbook!",
        ),
        (
            exceptions.MaterialsMustBeDefinedBeforeStackup,
            'Materials must be defined before stackup in the workbook "Stackup_Materials"!',
        ),
        (
            exceptions.NoProjNameFound,
            "No project name is specified in the gSheet Special_Settings tab!",
        ),
        (exceptions.NoSpecialSettingsFound, "No special settings are found!"),
        (exceptions.NoProjDirDefined, "No proj dir was defined!"),
    ],
)
def test_printing_exceptions_report_to_stdout_and_have_empty_strings(
    exception_type, message, capsys
):
    error = exception_type()
    assert capsys.readouterr().out == f"{message}\n"
    assert str(error) == ""


@pytest.mark.parametrize(
    ("exception_type", "args", "message"),
    [
        (exceptions.NoDsnFound, (), "No design file is found in the directory!"),
        (
            exceptions.NoExistingNames,
            (["NET_A", "U1"],),
            "The following net/component names do not exist:\nNET_A\nU1",
        ),
        (exceptions.IllegalInputFormat, (["bad row", "bad port"],), "\nbad row\nbad port"),
        (exceptions.ImproperCountOfComp, (), "Improper counts of components were found!"),
        (
            exceptions.UnequalPortCounts,
            (["SIM_A", "SIM_B"],),
            "Port counts don't match for the following keys:\nSIM_A\nSIM_B",
        ),
        (
            exceptions.NoneUniqueFolderInDrive,
            (),
            "More than one folder with the same name is found in a single G drive path, which is not allowed!",
        ),
        (
            exceptions.NonUniqueFileInDrive,
            (),
            "More than one file with the same name is found in a single G drive path, which is not allowed!",
        ),
        (exceptions.WrongGrowSolderFormat, ("bad solder",), "bad solder"),
        (
            exceptions.UndefinedSurfaceRoughnessModelType,
            ("bad roughness",),
            "bad roughness",
        ),
        (exceptions.WrongAreaPortDef, (), "Area port definition was wrong!"),
    ],
)
def test_logging_exceptions_emit_debug_diagnostics_and_have_empty_strings(
    exception_type, args, message
):
    logger = Mock()
    exception_type(logger, *args)
    logger.debug.assert_called_once_with(message)


@pytest.mark.parametrize(
    ("exception_type", "args"),
    [
        (exceptions.NoDsnFound, ()),
        (exceptions.NoExistingNames, (["NET_A", "U1"],)),
        (exceptions.IllegalInputFormat, (["bad row", "bad port"],)),
        (exceptions.ImproperCountOfComp, ()),
        (exceptions.UnequalPortCounts, (["SIM_A", "SIM_B"],)),
        (exceptions.NoneUniqueFolderInDrive, ()),
        (exceptions.NonUniqueFileInDrive, ()),
        (exceptions.WrongGrowSolderFormat, ("bad solder",)),
        (exceptions.UndefinedSurfaceRoughnessModelType, ("bad roughness",)),
        (exceptions.WrongAreaPortDef, ()),
    ],
)
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "BUG: logger-taking exceptions retain constructor arguments in "
        "BaseException.args, so str(exception) leaks the logger and payload"
    ),
)
def test_logging_exception_string_representations_are_empty(exception_type, args):
    assert str(exception_type(Mock(), *args)) == ""
