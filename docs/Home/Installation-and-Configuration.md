<!--
SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
SPDX-FileCopyrightText: 2024 Rivos Inc.

SPDX-License-Identifier: Apache-2.0
-->

[← Documentation Home](/docs/Home.md)

# Installation and Configuration

## Installation and Update

Open a terminal or command window. Install or update the tool using the following
command.

```shell
pip3 install git+https://github.com/rivosinc/opensipi
```

## Configuration

Create a new directory named `opensipi_config` under the root directory if it does not
already exist.

| OS      | Root directory |
| ------- | -------------- |
| Windows | `C:/`          |
| Linux   | `$HOME`        |

> [!IMPORTANT]
> The directory name must be exactly `opensipi_config`.

### Files That Must Live in `opensipi_config`

| File                  | Required                     | Purpose                                            |
| --------------------- | ---------------------------- | -------------------------------------------------- |
| `config_sigrity.yaml` | Yes                          | Parameters to configure Cadence Sigrity tools      |
| `config_linux.yaml`   | Yes                          | Parameters related to Linux OS                     |
| `usr.yaml`            | Yes                          | Parameters related to users                        |
| `config_gsuites.yaml` | Only for the Google Suites flow | Google account and Drive parameters             |

#### `config_sigrity.yaml`

The mandatory keywords are explained below.

| Keyword             | Value          | Description                                                                                   |
| ------------------- | -------------- | --------------------------------------------------------------------------------------------- |
| `SIG_LIB`           | string         | The directory of a Sigrity component library file `*.amm`.                                    |
| `SIG_OPTION`        | string         | The directory of a PowerSI option file `*.xml`.                                               |
| `CLARITY_OPTION`    | string         | The directory of a Clarity option file `*.xml`.                                               |
| `PDC_OPTION`        | string         | The directory of a PowerDC option file `*.xml`.                                               |
| `CORE_NUM`          | int            | The number of CPU cores used for a simulation.                                                |
| `DEFAULT_SOLDER`    | list of float  | First number is solder height in mm. Second number is solder diameter to pad size ratio.      |
| `DEFAULT_ANTIPAD`   | float          | One number for FEM port antipad ratio.                                                        |
| `SIG_VER`           | string         | The version of Sigrity.                                                                       |
| `SIG_LIC`           | list of string | License names for each Sigrity tool, including `POWERSI`, `CLARITY3DLAYOUT`, and `POWERDC`.   |
| `KNOB_BACKGND_RUN`  | `0` or `1`     | Disable or enable background run sims.                                                        |
| `KNOB_EMAIL`        | `0` or `1`     | Disable or enable email delivery.                                                             |

An example is given below.

```yaml
# TCL Settings
# Notice: Start with r to avoid the escape characters in the directory
# AMM library path
SIG_LIB: 'C:\opensipi_config\AMMLib\test.amm'
# Sim options
SIG_OPTION: 'C:\opensipi_config\SigOptions\PSI_PCB_Options_V0p1.xml'
CLARITY_OPTION: 'C:\opensipi_config\SigOptions\Clarity_PCB_Options_V0p1.xml'
PDC_OPTION: 'C:\opensipi_config\SigOptions\PDC_PCB_Options_V0p1.xml'
# compute resources
CORE_NUM: 16

# Clarity settings
DEFAULT_SOLDER:
    - 0.1  # solder height in mm
    - 0.8  # solder diameter to pad size ratio
DEFAULT_ANTIPAD: 1.5  # FEM port antipad ratio

# Execution Settings
# Sigrity version
SIG_VER: Sigrity2022.1
# Sigrity licenses
SIG_LIC:
    POWERSI:
        - PCB_Extract_20
    CLARITY3DLAYOUT:
        - Clarity_3DSolverG
    POWERDC:
        - PowerDC
# Knobs
KNOB_BACKGND_RUN: 0
KNOB_EMAIL: 0
```

#### `config_linux.yaml`

The mandatory keywords are explained below.

| Keyword      | Value  | Description                              |
| ------------ | ------ | ---------------------------------------- |
| `CMD_HEADER` | string | Allow users to customize scheduler info. |

```yaml
# CMD_HEADER, allow users to customize scheduler info
CMD_HEADER: ''
```

#### `usr.yaml`

The mandatory keywords are explained below.

| Keyword  | Value  | Description |
| -------- | ------ | ----------- |
| `USR_ID` | string | User ID.    |

```yaml
# User ID
USR_ID: user_id
```

#### `config_gsuites.yaml` (only for the Google Suites flow)

This file is read only when the input comes from a Google Sheet or the output is uploaded
to Google Drive — see
[`sim2report_gsuites()`](/docs/Home/Integrated-Flows.md#sim2report_gsuitesinput_info-mntr_info).
It is not needed for the plain CSV flow.

| Keyword               | Value  | Description                                              |
| --------------------- | ------ | ---------------------------------------------------------- |
| `ACCOUNT_KEY_DIR`     | string | Path to the Google account key file.                     |
| `ACCOUNT_TYPE`        | string | Account type, e.g. `service`.                            |
| `ROOT_GDRIVE_ID`      | string | ID of the Google Drive folder to upload the results to.  |
| `OUT_SHEET_GDRIVE_ID` | string | ID of the Google Drive folder for the output sheet.      |

### Files That Can Live Anywhere

The following files are must-haves but can reside outside folder `opensipi_config`.

| File                                                     | How it is found                                                                              |
| -------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Cadence component library `*.amm`                        | Set the full path to `SIG_LIB` in `config_sigrity.yaml`.                                      |
| Option files for Cadence Clarity, PowerSI, and PowerDC `*.xml` | Set the full paths to `SIG_OPTION`, `CLARITY_OPTION`, and `PDC_OPTION` in `config_sigrity.yaml`. |
