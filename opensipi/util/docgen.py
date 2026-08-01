# SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Generate a deterministic Markdown API reference from source docstrings."""

import ast
import re
import sys
import textwrap
from pathlib import Path


class DocGen:
    """Render the public Python API as Markdown without importing the package.

    Args:
        pkg_dir (str or pathlib.Path): Package directory to scan.
        out_path (str or pathlib.Path): Markdown file to write.
        exclude (tuple of str): Package directory names to skip.
    """

    _SECTION_RE = re.compile(r"^(\w+):$")
    _ARG_RE = re.compile(r"^(\*{0,2}[\w.]+)\s*(?:\((.+)\))?:\s*(.*)$")
    _ROLE_RE = re.compile(r":(?:meth|class|func|data|attr):`~?([^`]+)`")

    def __init__(
        self,
        pkg_dir="opensipi",
        out_path="docs/Home/API-Reference.md",
        exclude=("autopwt",),
    ):
        """Initialize the generator paths and exclusions.

        Args:
            pkg_dir (str or pathlib.Path): Package directory to scan.
            out_path (str or pathlib.Path): Markdown file to write.
            exclude (tuple of str): Package directory names to skip.
        """
        self.pkg_dir = Path(pkg_dir)
        self.out_path = Path(out_path)
        self.exclude = frozenset(exclude)

    def build(self) -> str:
        """Render the complete API reference without writing it.

        Returns:
            str: Deterministic Markdown ending in exactly one newline.
        """
        sections = [
            "<!--",
            "SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.",
            "SPDX-FileCopyrightText: 2024 Rivos Inc.",
            "",
            "SPDX-License-" "Identifier: Apache-2.0",
            "-->",
            "",
            "# API Reference",
            "",
            "> [!NOTE]",
            "> This page is generated from source docstrings. Do not edit it by hand.",
        ]
        for path, tree in self._iter_modules():
            rendered = self._render_module(path, tree)
            if rendered:
                sections.extend(("", rendered))
        return self._normalize("\n".join(sections))

    def write(self) -> bool:
        """Write the reference only when its content has changed.

        Returns:
            bool: ``True`` when the output file was changed, otherwise ``False``.
        """
        content = self.build()
        if self.out_path.exists() and self.out_path.read_text(encoding="utf-8") == content:
            return False
        self.out_path.parent.mkdir(parents=True, exist_ok=True)
        self.out_path.write_text(content, encoding="utf-8", newline="\n")
        return True

    def _iter_modules(self):
        """Yield source paths and parsed ASTs in stable module order."""
        for path in sorted(self.pkg_dir.rglob("*.py")):
            relative = path.relative_to(self.pkg_dir)
            if any(part in self.exclude for part in relative.parts[:-1]):
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            members = [
                node
                for node in tree.body
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                and not node.name.startswith("_")
            ]
            if path.name == "__init__.py" and not members:
                continue
            yield path, tree

    def _render_module(self, path, tree) -> str:
        """Render one module and its public top-level definitions."""
        relative = path.relative_to(self.pkg_dir).with_suffix("")
        parts = list(relative.parts)
        if parts[-1] == "__init__":
            parts.pop()
        module_name = ".".join((self.pkg_dir.name, *parts))
        rendered = [f"## `{module_name}`"]
        docstring = ast.get_docstring(tree, clean=True)
        if docstring:
            rendered.extend(("", self._render_docstring(docstring, is_module=True)))

        for node in sorted(tree.body, key=lambda item: item.lineno):
            if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                rendered.extend(("", self._render_class(node)))
            elif isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef)
            ) and not node.name.startswith("_"):
                rendered.extend(("", self._render_function(node, level=3)))
        return "\n".join(part for part in rendered if part is not None)

    def _render_class(self, node) -> str:
        """Render a public class, constructor, and public methods."""
        rendered = [f"### `{node.name}`"]
        docstring = ast.get_docstring(node, clean=True)
        if docstring:
            rendered.extend(("", self._render_docstring(docstring)))

        constructor = next(
            (
                member
                for member in node.body
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
                and member.name == "__init__"
            ),
            None,
        )
        if constructor is not None:
            rendered.extend(
                (
                    "",
                    "**Constructor**",
                    "",
                    self._signature(constructor, node.name, is_constructor=True),
                )
            )
            constructor_doc = ast.get_docstring(constructor, clean=True)
            if constructor_doc:
                rendered.extend(("", self._render_docstring(constructor_doc)))

        methods = [
            member
            for member in node.body
            if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
            and not member.name.startswith("_")
        ]
        for method in sorted(methods, key=lambda item: item.lineno):
            rendered.extend(("", self._render_function(method, level=4)))
        return "\n".join(rendered)

    def _render_function(self, node, level) -> str:
        """Render a public function or method and its docstring."""
        rendered = [f"{'#' * level} `{node.name}`", "", self._signature(node)]
        docstring = ast.get_docstring(node, clean=True)
        if docstring:
            rendered.extend(("", self._render_docstring(docstring)))
        return "\n".join(rendered)

    def _signature(self, node, name=None, is_constructor=False) -> str:
        """Return a fenced Python signature produced directly from the AST."""
        prefix = "async def " if isinstance(node, ast.AsyncFunctionDef) else "def "
        display_name = name or node.name
        args = node.args
        if is_constructor and args.posonlyargs + args.args:
            args = ast.arguments(
                posonlyargs=args.posonlyargs[1:] if args.posonlyargs else [],
                args=args.args[1:] if not args.posonlyargs else args.args,
                vararg=args.vararg,
                kwonlyargs=args.kwonlyargs,
                kw_defaults=args.kw_defaults,
                kwarg=args.kwarg,
                defaults=args.defaults,
            )
        signature = ast.unparse(args)
        returns = f" -> {ast.unparse(node.returns)}" if node.returns is not None else ""
        return f"```python\n{prefix}{display_name}({signature}){returns}\n```"

    def _render_docstring(self, docstring, is_module=False) -> str:
        """Render prose and supported Google-style sections as Markdown."""
        if is_module:
            lines = [
                line
                for line in docstring.splitlines()
                if not line.strip().startswith("Author:")
                and not line.strip().startswith("Last updated on")
            ]
            docstring = "\n".join(lines)

        rendered = []
        for name, block in self._split_sections(docstring):
            block = self._rst_to_md(self._dedent_block(block))
            if name is None or name == "Description":
                section = block
            elif name == "Args":
                args = self._render_args(block)
                section = f"**Args:**\n\n{args}" if args else "**Args:**"
            else:
                section = f"**{name}:**\n\n{block}" if block else f"**{name}:**"
            if section:
                rendered.append(section)
        return "\n\n".join(rendered)

    @staticmethod
    def _dedent_block(block) -> str:
        """Remove the section body's first indentation level."""
        block = textwrap.dedent(block).strip("\n")
        lines = block.splitlines()
        first = next((line for line in lines if line.strip()), "")
        indent = len(first) - len(first.lstrip())
        if not indent:
            return block
        return "\n".join(line[indent:] if line.startswith(" " * indent) else line for line in lines)

    def _split_sections(self, docstring):
        """Split a cleaned docstring into prose and base-indent sections."""
        lines = docstring.splitlines()
        sections = []
        current_name = None
        current_lines = []
        for line in lines:
            match = self._SECTION_RE.fullmatch(line)
            if match:
                sections.append((current_name, "\n".join(current_lines)))
                current_name = match.group(1)
                current_lines = []
            else:
                current_lines.append(line)
        sections.append((current_name, "\n".join(current_lines)))
        return [(name, block) for name, block in sections if block.strip() or name is not None]

    def _render_args(self, block) -> str:
        """Render argument entries as bullets while preserving nested content."""
        rendered = []
        for line in block.splitlines():
            stripped = line.strip()
            if not stripped:
                if rendered and rendered[-1] != "":
                    rendered.append("")
                continue
            match = self._ARG_RE.fullmatch(stripped) if line == line.lstrip() else None
            if match:
                name, arg_type, description = match.groups()
                label = f"- **{name}**"
                if arg_type:
                    label += f" (*{arg_type}*)"
                label += f" — {description}" if description else ""
                rendered.append(label)
            else:
                rendered.append(f"  {stripped}")
        while rendered and rendered[-1] == "":
            rendered.pop()
        return "\n".join(rendered)

    def _rst_to_md(self, text) -> str:
        """Convert the inline reStructuredText used by the source docstrings."""
        text = self._ROLE_RE.sub(lambda match: f"`{match.group(1)}`", text)
        return re.sub(r"``([^`]+)``", r"`\1`", text)

    @staticmethod
    def _normalize(content) -> str:
        """Normalize line endings, trailing whitespace, and final newline."""
        lines = content.replace("\r\n", "\n").replace("\r", "\n").splitlines()
        return "\n".join(line.rstrip() for line in lines).rstrip() + "\n"


def main() -> int:
    """Regenerate the API reference and fail when the file was stale."""
    return int(DocGen().write())


if __name__ == "__main__":
    sys.exit(main())
