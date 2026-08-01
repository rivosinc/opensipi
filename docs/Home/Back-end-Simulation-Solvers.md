<!--
SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
SPDX-FileCopyrightText: 2024 Rivos Inc.

SPDX-License-Identifier: Apache-2.0
-->

[← Documentation Home](/docs/Home.md)

# Back-end Simulation Solvers

## Introduction

The ultimate goal of the OpenSIPI package is to support all commonly used EDA tools for
S-parameter and DCR extraction. At present, due to the limited bandwidth of the
developer, only Cadence Sigrity tools are supported.

> [!NOTE]
> **Call for help!** Contributions that enable extraction based on equivalent tools
> offered by ANSYS or other vendors are very welcome.
> See [CONTRIBUTING.md](/CONTRIBUTING.md).

## Supported Solvers

| Solver           | Extraction type          | `ExtractionType` value |
| ---------------- | ------------------------ | ---------------------- |
| Cadence PowerSI  | Power delivery network   | `PDN`                  |
| Cadence PowerSI  | Low-speed IO             | `LSIO`                 |
| Cadence Clarity  | High-speed IO (3D FEM)   | `HSIO`                 |
| Cadence PowerDC  | DC resistance            | `DCR`                  |

The solver is selected automatically from the `ExtractionType` setting in the
`Special_Settings` sheet — see [Front-end Files IO](/docs/Home/Front-end-Files-IO.md).
