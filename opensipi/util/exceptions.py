# SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
Author: yanshengw@
Last updated on Nov. 20, 2023

Description:
    This Python3 module contains exceptions that are commonly used by the
OpenSIPI application.

    Every exception here reports its own message as a side effect of being
constructed, either by printing it or, once a run logger exists, by writing it
to that logger. The classes taking a logger are therefore only usable after
``Platform`` has set logging up.

    Note none of these classes forwards a message to ``Exception.__init__``, so
the raised object itself carries no text. The explanation reaches the user
through the print or the log record, not through ``str(exc)``.
"""


class NoLegalSimWbFound(Exception):
    """Raised when no legal sim workbook titles is found."""

    def __init__(self):
        """Report that no sheet name matched the expected sim prefix."""
        print("No legal sim workbook is found! " + "Check if the workbook title is correct.")


class NoSimRowFound(Exception):
    """Raised when no sim row is found in the sim workbook."""

    def __init__(self):
        """Report that the sim sheet holds a header but no data rows."""
        print("No sim row is found in the sim workbook!")


class NoneUniqueKeyDefined(Exception):
    """Raised when none unique key is defined for power rails
    in the same workbook.
    """

    def __init__(self):
        """Report that a ``Unique_Key`` is duplicated within one sim sheet."""
        print("None unique key is defined for power rails in the same workbook!")


class MaterialsMustBeDefinedBeforeStackup(Exception):
    """Raised when materials are not defined before stackup in the Workbook
    'Stackup_Materials'.
    """

    def __init__(self):
        """Report that the ``Materials`` section is not above ``Stackup``."""
        print("Materials must be defined before stackup " + 'in the workbook "Stackup_Materials"!')


class NoProjNameFound(Exception):
    """Raised when no project name is specified in the gSheet
    Special_Settings tab.
    """

    def __init__(self):
        """Report that ``ProjectName`` is missing from the special settings."""
        print("No project name is specified in the gSheet Special_Settings tab!")


class NoDsnFound(Exception):
    """Raised when no design files is found in the directory."""

    def __init__(self, lg):
        """Report that the design directory holds no file of an accepted type.

        Args:
            lg (logging.Logger): The run logger to report through.
        """
        lg.debug("No design file is found in the directory!")


class NoExistingNames(Exception):
    """Raised when names in gSheet don't exist."""

    def __init__(self, lg, name):
        """Report input net or component names absent from the design file.

        Args:
            lg (logging.Logger): The run logger to report through.
            name (list of str): The offending net or component names, listed
                one per line in the log record.
        """
        lg.debug("The following net/component names do not exist:\n" + str("\n".join(name)))


class IllegalInputFormat(Exception):
    """Raised when illegal input format is found."""

    def __init__(self, lg, errors):
        """Report the format errors found while scanning the input sheets.

        Args:
            lg (logging.Logger): The run logger to report through.
            errors (list of str): The error descriptions, logged one per line.
        """
        lg.debug("\n" + "\n".join(errors))


class ImproperCountOfComp(Exception):
    """Raise when the counts of the component in the gSheet are
    improperly given.
    """

    def __init__(self, lg):
        """Report that a component count in the input is not usable.

        Args:
            lg (logging.Logger): The run logger to report through.
        """
        lg.debug("Improper counts of components were found!")


class UnequalPortCounts(Exception):
    """Raised when port counts don't match between defined and actually
    generated in the spd.
    """

    def __init__(self, lg, name):
        """Report simulations whose generated port count is off.

        A mismatch means the solver did not build every port the input asked
        for, so the extraction would produce results that cannot be
        post-processed as expected.

        Args:
            lg (logging.Logger): The run logger to report through.
            name (list of str): The affected simulation keys, listed one per
                line in the log record.
        """
        lg.debug("Port counts don't match for the following keys:\n" + str("\n".join(name)))


class NoneUniqueFolderInDrive(Exception):
    """Raised when more than one folder with the same name is found in
    a single G drive path.
    """

    def __init__(self, lg):
        """Report a duplicated folder name in one Google Drive path.

        Args:
            lg (logging.Logger): The run logger to report through.
        """
        lg.debug(
            "More than one folder with the same name is found in "
            + "a single G drive path, which is not allowed!"
        )


class NonUniqueFileInDrive(Exception):
    """Raised when more than one file with the same name is found
    in a single G drive path.
    """

    def __init__(self, lg):
        """Report a duplicated file name in one Google Drive path.

        Args:
            lg (logging.Logger): The run logger to report through.
        """
        lg.debug(
            "More than one file with the same name is found in "
            + "a single G drive path, which is not allowed!"
        )


class WrongGrowSolderFormat(Exception):
    """Raised when the input format of the grow solder settings is wrong"""

    def __init__(self, lg, error):
        """Report a malformed ``GrowTopSolder`` or ``GrowBotSolder`` setting.

        Args:
            lg (logging.Logger): The run logger to report through.
            error (str): The ready-to-log description of what is wrong.
        """
        lg.debug(error)


class UndefinedSurfaceRoughnessModelType(Exception):
    """Raised when the input surface roughness model type is undefined"""

    def __init__(self, lg, error):
        """Report a surface roughness model type that is not recognized.

        Args:
            lg (logging.Logger): The run logger to report through.
            error (str): The ready-to-log description of what is wrong.
        """
        lg.debug(error)


class NoSpecialSettingsFound(Exception):
    """Raised when no special settings are found."""

    def __init__(self):
        """Report that the mandatory special settings sheet is missing."""
        print("No special settings are found!")


class NoProjDirDefined(Exception):
    """Raised when no proj dir was defined."""

    def __init__(self):
        """Report that neither ``proj_dir`` nor ``input_dir`` was supplied."""
        print("No proj dir was defined!")


class WrongAreaPortDef(Exception):
    """Raised when area port definition was wrong."""

    def __init__(self, lg):
        """Report a malformed ``Rec{...}`` area port definition.

        Args:
            lg (logging.Logger): The run logger to report through.
        """
        lg.debug("Area port definition was wrong!")
