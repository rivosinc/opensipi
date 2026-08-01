<!--
SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
SPDX-FileCopyrightText: © 2024 Rivos Inc.

SPDX-License-Identifier: Apache-2.0
-->

# Contributing

Thanks for your interest in OpenSIPI! This page gets you from a fresh clone to
an open pull request.

By participating, you agree to abide by the
[Code of Conduct](CODE_OF_CONDUCT.md).

**Contents**

- [Prerequisites](#prerequisites)
- [Set Up Your Fork](#set-up-your-fork)
- [Install the Environment](#install-the-environment)
- [Configure Visual Studio Code](#configure-visual-studio-code-optional)
- [Make Your Changes](#make-your-changes)
- [Before You Commit](#before-you-commit)
- [Open a Pull Request](#open-a-pull-request)

## Prerequisites

Three tools need to be installed first.

| Tool         | Why it is needed                                                                                                                                          | Install                                                                                                             |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `poetry`     | Establishes the virtual environment. This simplifies installing OpenSIPI and ensures every developer uses exactly the same Python, module, and package versions, so compatibility is not a concern. | [python-poetry.org](https://python-poetry.org/docs/)                                                                |
| `reuse`      | Manages the licensing header of each file in the project.                                                                                                 | [reuse.software](https://reuse.software/faq/#install-tool)                                                          |
| `pre-commit` | Runs the basic commit checks locally, the same ones CI runs on your pull request.                                                                         | [instructions](https://github.com/riscv/docs-spec-template?tab=readme-ov-file#enabling-pre-commit-checks-locally)   |

## Set Up Your Fork

This guide assumes you are familiar with the basics of git and GitHub.

1. [Fork the repo](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo)
   to your own GitHub account.
2. Clone your fork to your local computer.
3. Configure git to sync your fork with the upstream repo.

You push updates to your own fork and then open a pull request to merge them
into the original repo.

## Install the Environment

From the `opensipi` root directory, where `pyproject.toml` lives:

```shell
poetry install --with dev
```

> [!TIP]
> Re-run `poetry install` each time you sync your fork with the upstream repo,
> so your environment picks up any dependency changes.

Run project commands through Poetry so they use the managed virtual environment:

```shell
poetry run python --version
```

## Configure Visual Studio Code (optional)

There are various ways to work on the project. If you use
[Visual Studio Code](https://code.visualstudio.com/) as your IDE, here is how to
point it at the `poetry` virtual environment.

1. Open the `opensipi` root directory in VS Code and run
   `poetry install --with dev` in its terminal, as above.
2. Click the current interpreter in the bottom right corner.

   ![Interpreter selector in the VS Code status bar](/docs/Figures/VSC_BR.png)

3. A dialog pops up in the top center. Choose the interpreter with `opensipi` in
   its name.

   ![Interpreter list at the top of VS Code](/docs/Figures/VSC_top.png)

You're all set to make changes!

## Make Your Changes

A few conventions worth knowing before you start:

- **Formatting is automated.** `black` (line length 100), `isort`, `flake8`,
  `flynt`, and `pyupgrade` run as pre-commit hooks, so match the surrounding
  style and let the tools handle the rest.
- **Every file needs an SPDX license header.** `reuse` enforces this. Copy the
  header from a neighbouring file when you add a new one.
- **Bump the version in two places.** `version` in `pyproject.toml` and
  `__version__` in `opensipi/__init__.py` must stay in sync.
- **Add tests for new behavior.** Tests live under `tests/` and use pytest.
  Keep normal tests hermetic: mock licensed solvers, Google services, interactive
  prompts, and external PDF processes rather than requiring them locally or in CI.

## Before You Commit

Check that every file under the `opensipi` root directory carries a license.
This is only necessary if you added files.

```shell
reuse lint
```

Run the automated tests and, when changing covered behavior, review the coverage
report:

```shell
poetry run pytest -m "not slow"
poetry run pytest --cov=opensipi --cov-report=term-missing
```

Tests marked `slow` are excluded from the normal command and can be run separately
with `poetry run pytest -m slow`. Coverage is currently reported as a baseline;
there is no minimum threshold.

Then run the pre-commit checks.

```shell
poetry run pre-commit run
```

`pre-commit run` only checks staged files. To check everything:

```shell
poetry run pre-commit run --all-files
```

## Open a Pull Request

Push your branch to your fork and open a pull request against `main`. The
`pre-commit` and `pytest` workflows run automatically on every pull request, so
run both local checks before pushing.

In the description, say what changed, why, and how you verified it.
