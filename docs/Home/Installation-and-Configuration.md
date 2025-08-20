<!--
SPDX-FileCopyrightText: 2024 Rivos Inc.

SPDX-License-Identifier: Apache-2.0
-->

# Installation and update
Open a terminal or command window. Install or update the tool using the following command.

```
pip3 install git+https://github.com/rivosinc/opensipi
```

# Configuration

Root directory: "C:/" for windows

Create a new directory "opensipi_config" under the root directory if not existing. The directory name must be exact.

## Files must be under Folder "opensipi_config"
The following files MUST exist in "opensipi_config"
- config_sigrity.yaml: parameters to configure Cadence Sigrity tools.
- config_linux.yaml: parameters related to Linux OS.
- usr.yaml: parameters related to users

### config_sigrity.yaml
The mandatory key words are explained as below.

| Key Word | Value | Description |
| -------- | ----- | ----------- |
| SIG_LIB | string | The directory of a Sigrity component library file *.amm. |
| SIG_OPTION | string | The directory of a PowerSI option file *.xml. |
| CLARITY_OPTION | string | The directory of a Clarity option file *.xml. |
| PDC_OPTION | string | The directory of a PowerDC option file *.xml. |
| CORE_NUM | int | The number of CPU cores used for a simulation. |
| DEFAULT_SOLDER | list of float | First number is solder height in mm. Second number is solder diameter to pad size ratio. |
| DEFAULT_ANTIPAD | float | One number for FEM port antipad ratio. |
| SIG_VER | string | The version of Sigrity |
| SIG_LIC | list of string | License names for each Sigrity tool including POWERSI, CLARITY3DLAYOUT, and POWERDC. |
| KNOB_BACKGND_RUN | 0 or 1 | Disable or enable background run sims. |
| KNOB_EMAIL | 0 or 1 | Disable or enable email delivery. |

An example is given below.

``` yaml
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

### config_linux.yaml
The mandatory key words are explained as below.

| Key Word | Value | Description |
| -------- | ----- | ----------- |
| CMD_HEADER | string | Allow users to customize scheduler info. |

```yaml
# CMD_HEADER, allow users to customize scheduler info
CMD_HEADER: ''
```

### usr.yaml
The mandatory key words are explained as below.

| Key Word | Value | Description |
| -------- | ----- | ----------- |
| USR_ID | string | User ID. |

```yaml
# User ID
USR_ID: user_id
```

## Files can reside any locations
The following files are must-haves but can reside outside Folder "opensipi_config"
- Cadence component library: *.amm

    Set the full path to this amm file to SIG_LIB in config_sigrity.yaml
- Option Files for Cadence Clarity, PowerSI, and PowerDC: *.xml

    Set the full paths to these xml files to SIG_OPTION, CLARITY_OPTION, and PDC_OPTION in config_sigrity.yaml
