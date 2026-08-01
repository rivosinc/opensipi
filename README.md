<!--
SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
SPDX-FileCopyrightText: © 2024 Rivos Inc.

SPDX-License-Identifier: Apache-2.0
-->

# OpenSIPI

[![REUSE status](https://api.reuse.software/badge/github.com/rivosinc/opensipi)](https://api.reuse.software/info/github.com/rivosinc/opensipi)

**An open-source platform that automates signal integrity (SI) and power
integrity (PI) extractions.**

Describe your simulations in a set of tables, and OpenSIPI does the rest: it
parses the input, generates the scripts your EDA tool runs, launches and
monitors the simulations, post-processes the extracted results, and writes a
report. The focus so far is S-parameter and DCR extraction.

![OpenSIPI Overview](/docs/Figures/OpenSIPI_Overview.png)

> [!IMPORTANT]
> OpenSIPI is free and open source, but the back-end solvers it drives are
> commercial tools. Extracting anything requires the appropriate commercial
> licenses, which are **not** included here.

## What It Extracts

| Extraction | Solver          | Purpose                          | Result              |
| ---------- | --------------- | -------------------------------- | ------------------- |
| `PDN`      | Cadence PowerSI | Power delivery network (Z-param) | Touchstone (`.sNp`) |
| `LSIO`     | Cadence PowerSI | Low-speed IO (S-param)           | Touchstone (`.sNp`) |
| `HSIO`     | Cadence Clarity | High-speed IO (S-param, 3D FEM)  | Touchstone (`.sNp`) |
| `DCR`      | Cadence PowerDC | DC resistance                    | CSV                 |

## Requirements

- Python 3.10 or newer
- A licensed installation of the Cadence Sigrity tools

## Installation

Open a terminal or command window. Install or update the tool using the
following command.

```shell
pip3 install git+https://github.com/rivosinc/opensipi
```

## Quick Start

The starter kits walk you through a complete extraction on a real open-source
board, from downloading the design to reading the report.

- [Starter Kit for Windows Users](/docs/Home/Starter-Kit-for-Windows-Users.md)
- [Starter Kit for Linux Users](/docs/Home/Starter-Kit-for-Linux-Users.md)

Once your input tables and `opensipi_config` folder are in place, a run is a
handful of lines:

```python
from opensipi.integrated_flows import sim2report

input_info = {
    "input_dir": r"C:\SIPIProj\Olympus\Sim_Input" + "\\",
    "input_type": "csv",
    "input_folder": "Sigrity_PDN",
    "op_run_name": "",
}

mntr_info = {
    "email": "",
    "op_pause_after_model_check": 1,
}

report_dir = sim2report(input_info, mntr_info)
```

## Documentation

Full documentation lives in [`docs/Home.md`](/docs/Home.md).

| Page                                                                           | What it covers                                          |
| ------------------------------------------------------------------------------ | -------------------------------------------------------- |
| [Overview of the Application](/docs/Home/Overview-of-the-Application.md)       | The three layers OpenSIPI is built from.                |
| [Installation and Configuration](/docs/Home/Installation-and-Configuration.md) | The `opensipi_config` folder and its YAML files.        |
| [Front-end Files IO](/docs/Home/Front-end-Files-IO.md)                         | Every input sheet and keyword, with worked examples.    |
| [Mid-layer Platform](/docs/Home/Mid-layer-Platform.md)                         | The run folder structure and the extraction workflow.   |
| [Back-end Simulation Solvers](/docs/Home/Back-end-Simulation-Solvers.md)       | Which solver is used for which extraction type.         |
| [User Manual](/docs/Home/User-Manual.md)                                       | API reference for the flows and the `Platform` class.   |

## Example

[`examples/Olympus/`](/examples/Olympus) is a full worked example built on the
Intel Olympus board from the Open Compute Project: input CSVs, launch scripts,
and sample output reports for all four extraction types.

## Roadmap

Contributions in these areas are especially welcome:

- Enable back-end extraction tools from more vendors.
- Include more options for S-parameter post-processing.
- Beautify reports.

## Contributing

Fork the repo, make your changes, and open a pull request. See
[CONTRIBUTING.md](CONTRIBUTING.md) to get set up, and
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for the ground rules.

You can also support the project as a **user**: integrate the platform into your
workflow, report bugs, and tell us which features would help.

## Authors

Created and maintained by Yansheng Wang. See the
[contributors](https://github.com/rivosinc/opensipi/graphs/contributors) for the
full list.

## License

Apache-2.0. Before using this application for any purpose, you MUST read and
understand the terms put forward in the accompanying [LICENSE](LICENSE) file.

## Project Status

The project is at its early stage and is actively under development.
