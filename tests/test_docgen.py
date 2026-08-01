# SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for the docstring-based API reference generator."""

import os
import subprocess
import sys
from types import SimpleNamespace

import pytest

from opensipi.util.docgen import DocGen


@pytest.fixture
def docgen_workspace(tmp_path):
    """Create an isolated source package and API reference path."""
    package = tmp_path / "samplepkg"
    package.mkdir()
    output = tmp_path / "API-Reference.md"

    def write_module(relative_path, source):
        path = package / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
        return path

    def build():
        return DocGen(pkg_dir=package, out_path=output).build()

    return SimpleNamespace(
        root=tmp_path,
        package=package,
        output=output,
        write_module=write_module,
        build=build,
    )


def test_build_renders_public_api_in_source_order_without_importing(docgen_workspace):
    docgen_workspace.write_module(
        "module.py",
        '''"""Module summary mentioning ``literal`` and :class:`Thing`."""

raise RuntimeError("this module must not be imported")


def first(value: int = 3) -> int:
    """Return the first value.

    Args:
        value (int): Value to return.

    Returns:
        int: The supplied value.
    """


def _hidden():
    """Do not render this function."""


class Thing:
    """Represent a public thing.

    Attributes:
        value (int): Stored value.
    """

    def __init__(self, value: int = 3):
        """Initialize the thing.

        Args:
            value (int): Stored value.
        """

    def run(self, enabled: bool = True):
        """Run the thing.

        Returns:
            bool: Whether it ran.
        """

    def _helper(self):
        """Do not render this method."""

    def __repr__(self):
        """Do not render other dunder methods."""
''',
    )

    rendered = docgen_workspace.build()

    assert "# API Reference" in rendered
    assert "`samplepkg.module`" in rendered
    assert rendered.index("### `first`") < rendered.index("### `Thing`")
    assert "def first(value: int=3) -> int" in rendered
    assert "**Returns:**" in rendered
    assert "### `Thing`" in rendered
    assert "**Constructor**" in rendered
    assert "Thing(value: int=3)" in rendered
    assert "Thing(self, value: int=3)" not in rendered
    assert "run(self, enabled: bool=True)" in rendered
    assert "_hidden" not in rendered
    assert "_helper" not in rendered
    assert "__repr__" not in rendered
    assert "`literal`" in rendered
    assert "`Thing`" in rendered


def test_build_renders_nested_args_metadata_rst_and_fallback_sections(docgen_workspace):
    docgen_workspace.write_module(
        "flows.py",
        '''"""
Author: owner@
Last updated on Jan. 1, 2026

Description:
    Run integrated flows.

References:
    See ``the guide`` and :func:`~samplepkg.flows.sim2report`.
"""


def sim2report(input_info, mntr_info):
    """Run an extraction.

    Args:
        input_info (dict): Input information.

            * ``input_type`` (str): Must be ``"csv"``.
            * ``input_dir`` (str): Input directory.

        mntr_info (dict): Monitor information.

    Raises:
        ValueError: If input is invalid.
    """
''',
    )

    rendered = docgen_workspace.build()

    assert "Run integrated flows." in rendered
    assert "Author:" not in rendered
    assert "Last updated on" not in rendered
    assert "**Description:**" not in rendered
    assert "**References:**" in rendered
    assert "See `the guide` and `samplepkg.flows.sim2report`." in rendered
    assert "- **input_info** (*dict*) — Input information." in rendered
    assert '  * `input_type` (str): Must be `"csv"`.' in rendered
    assert "- **mntr_info** (*dict*) — Monitor information." in rendered
    assert "**Raises:**" in rendered


def test_build_keeps_module_only_docs_and_skips_empty_init(docgen_workspace):
    docgen_workspace.write_module("__init__.py", "")
    docgen_workspace.write_module(
        "constants.py",
        '''"""Constants used by callers.

Attributes:
    VALUE (int): Stable public value.
"""

VALUE = 1
''',
    )
    docgen_workspace.write_module("empty.py", '"""A documented empty module."""\n')

    rendered = docgen_workspace.build()

    assert "`samplepkg.constants`" in rendered
    assert "**Attributes:**" in rendered
    assert "VALUE (int): Stable public value." in rendered
    assert "`samplepkg.empty`" in rendered
    assert "`samplepkg.__init__`" not in rendered
    assert "`samplepkg`" not in rendered


def test_write_only_replaces_changed_content_and_normalizes_newlines(docgen_workspace):
    source = docgen_workspace.write_module(
        "public.py",
        '''"""A public module."""


def api():
    """Expose an API."""
''',
    )
    generator = DocGen(pkg_dir=docgen_workspace.package, out_path=docgen_workspace.output)

    assert generator.write() is True
    first_content = docgen_workspace.output.read_bytes()
    assert first_content.endswith(b"\n")
    assert not first_content.endswith(b"\n\n")
    assert b"\r" not in first_content
    assert generator.write() is False
    assert docgen_workspace.output.read_bytes() == first_content

    source.write_text(
        source.read_text(encoding="utf-8").replace("Expose", "Publish"),
        encoding="utf-8",
    )
    assert generator.write() is True
    assert "Publish an API." in docgen_workspace.output.read_text(encoding="utf-8")


def test_build_excludes_autopwt_tree_by_default(docgen_workspace):
    docgen_workspace.write_module(
        "public.py",
        'def visible():\n    """Render this function."""\n',
    )
    docgen_workspace.write_module(
        "autopwt/generated.py",
        'def excluded():\n    """Never render this function."""\n',
    )

    rendered = docgen_workspace.build()

    assert "visible" in rendered
    assert "autopwt" not in rendered
    assert "excluded" not in rendered


def test_build_renders_async_positional_only_and_keyword_only_signatures(docgen_workspace):
    docgen_workspace.write_module(
        "signatures.py",
        '''async def fetch(item: str, /, count: int = 2, *, strict: bool = True) -> list[str]:
    """Fetch items asynchronously."""


class Client:
    """Provide a client."""

    def __init__(self, endpoint: str, /, *, timeout: float = 1.5):
        """Initialize the client."""
''',
    )

    rendered = docgen_workspace.build()

    assert (
        "async def fetch(item: str, /, count: int=2, *, strict: bool=True) -> list[str]" in rendered
    )
    assert "Client(endpoint: str, /, *, timeout: float=1.5)" in rendered
    assert "Client(self" not in rendered


def test_build_selects_public_definitions_and_rejects_protected_and_private_ones(
    docgen_workspace,
):
    docgen_workspace.write_module(
        "selection.py",
        '''def public_function():
    """Render this function."""


def _protected_function():
    """Do not render this function."""


def __private_function():
    """Do not render this function."""


class PublicClass:
    """Render this class."""

    def public_method(self):
        """Render this method."""

    def _protected_method(self):
        """Do not render this method."""

    def __private_method(self):
        """Do not render this method."""


class _ProtectedClass:
    """Do not render this class."""


class __PrivateClass:
    """Do not render this class."""
''',
    )

    rendered = docgen_workspace.build()

    assert "### `public_function`" in rendered
    assert "### `PublicClass`" in rendered
    assert "#### `public_method`" in rendered
    assert "protected" not in rendered.lower()
    assert "private" not in rendered.lower()


def test_repeated_builds_and_writes_are_byte_identical(docgen_workspace):
    docgen_workspace.write_module(
        "stable.py",
        'def stable(value=1):\n    """Return a stable value."""\n',
    )
    generator = DocGen(pkg_dir=docgen_workspace.package, out_path=docgen_workspace.output)

    first_render = generator.build().encode("utf-8")
    second_render = generator.build().encode("utf-8")
    assert second_render == first_render

    assert generator.write() is True
    first_write = docgen_workspace.output.read_bytes()
    assert generator.write() is False
    assert docgen_workspace.output.read_bytes() == first_write == first_render


def test_cli_rewrites_stale_content_then_reports_current_content(tmp_path, repo_root):
    package = tmp_path / "opensipi"
    package.mkdir()
    (package / "public.py").write_text(
        'def api():\n    """Expose the API."""\n',
        encoding="utf-8",
    )
    output = tmp_path / "docs" / "Home" / "API-Reference.md"
    output.parent.mkdir(parents=True)
    output.write_text("stale\r\ncontent\r\n", encoding="utf-8")
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join([str(repo_root), environment.get("PYTHONPATH", "")])
    command = [sys.executable, "-m", "opensipi.util.docgen"]

    stale = subprocess.run(command, cwd=tmp_path, env=environment, check=False)
    rewritten = output.read_bytes()
    current = subprocess.run(command, cwd=tmp_path, env=environment, check=False)

    assert stale.returncode == 1
    assert rewritten != b"stale\r\ncontent\r\n"
    assert rewritten.endswith(b"\n")
    assert b"\r" not in rewritten
    assert current.returncode == 0
    assert output.read_bytes() == rewritten
