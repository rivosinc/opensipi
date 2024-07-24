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

Create a new directory "opensipi_config" under the root directory if not existing. The direcotyr name must be exact.

## Mandatory Files
Create a "config_sigrity.yaml" in the directory "opensipi_config". This YAML file contains information to configure the simulation software settings. The mandatory key words are explained as below.

| Key Word | Value | Description |
| -------- | ----- | ----------- |
| SIG_LIB | string | The directory of a Sigrity component library file. |
| SIG_OPTION | string | The directory of a PowerSI option file. |
| CLARITY_OPTION | string | The directory of a Clarity option file. |
| PDC_OPTION | string | The directory of a PowerDC option file. |
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
    - 0.8  # solder diamater to pad size ratio
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

In the folder "opensipi_config", create a new folder "AMMLib" to store the Sigrity AMM component library files. This amm file can be exported from Sigrity tools.

Next in the folder "opensipi_config", create a new folder "SigOptions" to store the Sigrity setting option XML files. These option files can be configured and exported from Sigrity tools.
