<!--
SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
SPDX-FileCopyrightText: 2024 Rivos Inc.

SPDX-License-Identifier: Apache-2.0
-->

[← Documentation Home](/docs/Home.md)

# User Manual

## OpenSIPI Configuration Files

See [Installation and Configuration](/docs/Home/Installation-and-Configuration.md) for
the `opensipi_config` folder and the YAML files it must contain.

## OpenSIPI Functions and Classes Reference

| Page                                               | What it covers                                                          |
| -------------------------------------------------- | ------------------------------------------------------------------------ |
| [Integrated Flows](/docs/Home/Integrated-Flows.md) | The top-level entry points that run an extraction end to end.           |
| [Classes](/docs/Home/Classes.md)                   | The `Platform` class and its methods, for building a custom flow.       |
| [API Reference](/docs/Home/API-Reference.md)       | Generated from docstrings for every public module, class, and function. |

Most users only need an integrated flow. Reach for `Platform` directly when you want to
drive the individual steps yourself.
