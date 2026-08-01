<!--
SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
SPDX-FileCopyrightText: 2024 Rivos Inc.

SPDX-License-Identifier: Apache-2.0
-->

# OpenSIPI Documentation

OpenSIPI is an open-source platform that automates signal integrity (SI) and power
integrity (PI) extractions. You describe the simulations in a set of tables, and the
platform drives a commercial EDA solver, post-processes the results, and writes a report.

> [!NOTE]
> OpenSIPI itself is free and open source, but the back-end solvers it drives are
> commercial tools. A successful extraction requires a valid solver license.

## Getting Started

Start here if you are new to OpenSIPI.

| Page                                                                    | What it covers                                                        |
| ----------------------------------------------------------------------- | --------------------------------------------------------------------- |
| [Overview of the Application](/docs/Home/Overview-of-the-Application.md) | The three layers OpenSIPI is built from, and how they fit together.   |
| [Installation and Configuration](/docs/Home/Installation-and-Configuration.md) | How to install the package and set up the `opensipi_config` folder. |
| [Starter Kit (Windows)](/docs/Home/Starter-Kit-for-Windows-Users.md)    | End-to-end walkthrough of the Olympus example on Windows.             |
| [Starter Kit (Linux)](/docs/Home/Starter-Kit-for-Linux-Users.md)        | End-to-end walkthrough of the Olympus example on Linux.               |

## Reference

Details of the input format, the platform internals, and the public API.

| Page                                                                       | What it covers                                                            |
| -------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| [Front-end Files IO](/docs/Home/Front-end-Files-IO.md)                     | Every input sheet and keyword, with worked examples per extraction type.  |
| [Mid-layer Platform](/docs/Home/Mid-layer-Platform.md)                     | The run folder structure and the step-by-step extraction workflow.        |
| [Back-end Simulation Solvers](/docs/Home/Back-end-Simulation-Solvers.md)   | Which solver is used for which extraction type.                           |
| [User Manual](/docs/Home/User-Manual.md)                                   | API reference index.                                                      |
| [API Reference](/docs/Home/API-Reference.md)                               | Generated reference for public modules, classes, methods, and functions.  |
| [Integrated Flows](/docs/Home/Integrated-Flows.md)                         | The top-level entry points, e.g. `sim2report()`.                          |
| [Classes](/docs/Home/Classes.md)                                           | The `Platform` class and its methods.                                     |

## Extraction Types at a Glance

| Type   | Solver        | Purpose                            | Result format          |
| ------ | ------------- | ---------------------------------- | ---------------------- |
| `PDN`  | PowerSI       | Power delivery network (Z-param)   | Touchstone (`.sNp`)    |
| `LSIO` | PowerSI       | Low-speed IO (S-param)             | Touchstone (`.sNp`)    |
| `HSIO` | Clarity (FEM) | High-speed IO (S-param)            | Touchstone (`.sNp`)    |
| `DCR`  | PowerDC       | DC resistance                      | CSV                    |
