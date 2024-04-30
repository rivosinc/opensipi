# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
Author: yanshengw@
Last updated on Nov. 20, 2023

Description:
    This Python3 module contains exceptions that are commonly used by the
OpenSIPI application.
"""


class NoLegalSimWbFound(Exception):
    """Raised when no legal sim workbook titles is found."""

    def __init__(self):
        print("No legal sim workbook is found! " + "Check if the workbook title is correct.")


class NoSimRowFound(Exception):
    """Raised when no sim row is found in the sim workbook."""

    def __init__(self):
        print("No sim row is found in the sim workbook!")


class NoneUniqueKeyDefined(Exception):
    """Raised when none unique key is defined for power rails
    in the same workbook.
    """

    def __init__(self):
        print("None unique key is defined for power rails in the same workbook!")


class MaterialsMustBeDefinedBeforeStackup(Exception):
    """Raised when materials are not defined before stackup in the Workbook
    'Stackup_Materials'.
    """

    def __init__(self):
        print("Materials must be defined before stackup " + 'in the workbook "Stackup_Materials"!')


class NoProjNameFound(Exception):
    """Raised when no project name is specified in the gSheet
    Special_Settings tab.
    """

    def __init__(self):
        print("No project name is specified in the gSheet Special_Settings tab!")


class NoDsnFound(Exception):
    """Raised when no design files is found in the directory."""

    def __init__(self, lg):
        lg.debug("No design file is found in the directory!")


class NoExistingNames(Exception):
    """Raised when names in gSheet don't exist."""

    def __init__(self, lg, name):
        lg.debug("The following net/component names do not exist:\n" + str("\n".join(name)))


class IllegalInputFormat(Exception):
    """Raised when illegal input format is found."""

    def __init__(self, lg, errors):
        lg.debug("\n" + "\n".join(errors))


class ImproperCountOfComp(Exception):
    """Raise when the counts of the component in the gSheet are
    improperly given.
    """

    def __init__(self, lg):
        lg.debug("Improper counts of components were found!")


class UnequalPortCounts(Exception):
    """Raised when port counts don't match between defined and actually
    generated in the spd.
    """

    def __init__(self, lg, name):
        lg.debug("Port counts don't match for the following keys:\n" + str("\n".join(name)))


class NoneUniqueFolderInDrive(Exception):
    """Raised when more than one folder with the same name is found in
    a single G drive path.
    """

    def __init__(self, lg):
        lg.debug(
            "More than one folder with the same name is found in "
            + "a single G drive path, which is not allowed!"
        )


class NonUniqueFileInDrive(Exception):
    """Raised when more than one file with the same name is found
    in a single G drive path.
    """

    def __init__(self, lg):
        lg.debug(
            "More than one file with the same name is found in "
            + "a single G drive path, which is not allowed!"
        )


class WrongGrowSolderFormat(Exception):
    """Raised when the input format of the grow solder settings is wrong"""

    def __init__(self, lg, error):
        lg.debug(error)


class UndefinedSurfaceRoughnessModelType(Exception):
    """Raised when the input surface roughness model type is undefined"""

    def __init__(self, lg, error):
        lg.debug(error)


class NoSpecialSettingsFound(Exception):
    """Raised when no special settings are found."""

    def __init__(self):
        print("No special settings are found!")


class NoProjDirDefined(Exception):
    """Raised when no proj dir was defined."""

    def __init__(self):
        print("No proj dir was defined!")
