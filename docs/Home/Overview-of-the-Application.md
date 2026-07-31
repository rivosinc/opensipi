<!--
SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
SPDX-FileCopyrightText: 2024 Rivos Inc.

SPDX-License-Identifier: Apache-2.0
-->

[← Documentation Home](/docs/Home.md)

# Overview of the Application

![OpenSIPI_Overview](/docs/Figures/OpenSIPI_Overview.png)

The complete application can be treated as three layers.

## 1. Front-end Files IO

The information used to set up simulations and guide post-processing has to be provided
in tables following specific formats.

- **Input** — tables (CSV files or Google Sheet tabs) describing the simulations.
  See [Front-end Files IO](/docs/Home/Front-end-Files-IO.md) for the full schema.
- **Output** — touchstone files (S-parameter `.sNp`) or CSV (DCR), plus a summary
  report in PDF format.

## 2. Mid-layer Platform

This is all about this package, OpenSIPI. It reads the input, generates tool-specific
scripts, drives the solver, post-processes the results, and builds the report.

See [Mid-layer Platform](/docs/Home/Mid-layer-Platform.md).

## 3. Back-end Simulation Solvers

The actual field solving is done by commercial EDA tools.

> [!IMPORTANT]
> The users have to install and purchase licenses for the desired simulation solvers
> separately. Nothing in this repository runs an extraction on its own.

See [Back-end Simulation Solvers](/docs/Home/Back-end-Simulation-Solvers.md).
