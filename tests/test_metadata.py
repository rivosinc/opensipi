# SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Characterization tests for package metadata."""

from importlib.metadata import version

import opensipi


def test_package_version_matches_installed_metadata():
    assert opensipi.__version__ == version("opensipi")
