<!--
SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
SPDX-FileCopyrightText: 2024 Rivos Inc.

SPDX-License-Identifier: Apache-2.0
-->

[← Documentation Home](/docs/Home.md)

# Starter Kit for Windows Users

> Using Linux? See the [Starter Kit for Linux Users](/docs/Home/Starter-Kit-for-Linux-Users.md).

## Overview

Here is the flow to evaluate the OpenSIPI platform with the provided examples.

1. [Download the design files](#1-download-the-design-files)
2. [Install OpenSIPI](#2-install-opensipi)
3. [Download and revise the example configuration files](#3-download-and-revise-the-example-configuration-files) — place the whole folder in the root directory, i.e. `C:\`
4. [Create the folder `SIPIProj`](#4-create-folder-sipiproj) in the root directory
5. [Download the input files](#5-download-the-input-files) — the example Olympus input files, placed in `SIPIProj`
6. [Run the main function](#6-run-the-main-function)

> [!IMPORTANT]
> A licensed installation of the Cadence Sigrity tools is required to actually run the
> extraction. OpenSIPI does not ship a solver.

---

## 1. Download the design files

The design files used to demonstrate the application are obtained from the Open Compute
Project (OCP). On the [OCP Contributions](https://www.opencompute.org/contributions) page,
search for "Intel Olympus ZTSystems" and download the board design package to work with
the provided input info.

![image](/docs/Figures/OCP_testcase.png)

Unzip the downloaded design package. Choose the following layout and schematic files to
work on.

![image](/docs/Figures/test_layout_sch.png)

Since the project is codenamed Olympus, why not name the simulation project Olympus too.
Later you'll see Olympus used to name the directory where your simulation files are kept.

## 2. Install OpenSIPI

Open a terminal or command window. Install or update the tool using the following command.

```shell
pip3 install git+https://github.com/rivosinc/opensipi
```

## 3. Download and revise the example configuration files

Download the example configuration files as
[a zipped package](/examples/WinOS/opensipi_config.zip), unzip it, and place the whole
folder `opensipi_config` in the root directory `C:\`.

Detailed descriptions of the configuration files can be found in
[Installation and Configuration](/docs/Home/Installation-and-Configuration.md). For this
specific test case, the following parameters in `config_sigrity.yaml` have to be revised
based on your available tool version and licenses.

- **`SIG_VER`** — e.g. `Sigrity2024.0`
- **`SIG_LIC`** — the exact license names

<details>
<summary>How to find the exact license names</summary>

One way to obtain the available license names is to check the utility tool "Cadence
Sigrity Suite Manager". Here is an example, assuming Clarity3DLayout licenses are to be
queried.

1. Launch the utility and select **Clarity3DLayout**. On the right side there are three
   suite licenses available for version 24.0: Clarity 3D, Clarity IC Package Extraction
   Suite, and Clarity PCB Extraction Suite. These are **not** the exact license names used
   to launch the tool.
2. Select **Clarity IC Package Extraction Suite** and click the **Who is using** button
   below.
3. In the pop-up dialog, `ICP_Extract_20` is the exact license name for Clarity IC Package
   Extraction Suite.
4. Repeat for the other two available licenses to get their exact names.

![image](/docs/Figures/LicMng.png)

</details>

> [!NOTE]
> The example AMM library file and Cadence Sigrity option files are provided as a starting
> point. They are supposed to be revised based on your needs.

## 4. Create folder `SIPIProj`

In the root directory `C:\`, create a new directory `SIPIProj` if it does not exist.

## 5. Download the input files

Download the example Olympus input files as
[a zipped package](/examples/WinOS/Olympus.zip), unzip it, and place the whole folder
`Olympus` under folder `SIPIProj`.

Inside folder `Olympus`, the main functions are stored under folder `Script` and the input
files under folder `Sim_Input`. Choose one set of files to try out the OpenSIPI platform
for a specific extraction goal.

The folder structure will be created as shown below.

![image](/docs/Figures/Folder_Structure_SimInput.png)

The online versions of the input files and main functions are listed below.

| Extraction | Input files                                              | Main function                                                            |
| ---------- | -------------------------------------------------------- | ------------------------------------------------------------------------ |
| PDN        | [Sigrity_PDN](/examples/Olympus/Sim_Input/Sigrity_PDN)   | [Olympus_PCB_xtractPDN.py](/examples/Olympus/Script/Olympus_PCB_xtractPDN.py)  |
| LSIO       | [Sigrity_LSIO](/examples/Olympus/Sim_Input/Sigrity_LSIO) | [Olympus_PCB_xtractLSIO.py](/examples/Olympus/Script/Olympus_PCB_xtractLSIO.py) |
| HSIO       | [Sigrity_HSIO](/examples/Olympus/Sim_Input/Sigrity_HSIO) | [Olympus_PCB_xtractHSIO.py](/examples/Olympus/Script/Olympus_PCB_xtractHSIO.py) |
| DCR        | [Sigrity_DCR](/examples/Olympus/Sim_Input/Sigrity_DCR)   | [Olympus_PCB_xtractDCR.py](/examples/Olympus/Script/Olympus_PCB_xtractDCR.py)  |

## 6. Run the main function

The PDN extraction test case is used as the example here.

### 6.1 Check the main function

Find the main function at `C:\SIPIProj\Olympus\Script\Olympus_PCB_xtractPDN.py`. Before
running it, make sure your input information is correct — in particular that `input_dir`,
`input_type`, and `input_folder` are all specified correctly.

```python
from opensipi.integrated_flows import sim2report


input_info = {
    'input_dir': r'C:\SIPIProj\Olympus\Sim_Input'+'\\',
    'input_type': 'csv',
    'input_folder': 'Sigrity_PDN',
    'op_run_name': '',
}

mntr_info = {
    'email': '',
    'op_pause_after_model_check': 1,
}

sim2report(input_info, mntr_info)
```

### 6.2 Launch it

Open a command window in the folder `Script` and launch the script.

```shell
python Olympus_PCB_xtractPDN.py
```

### 6.3 Drop the design file

You'll be asked to drop a design file into the specified directory.

```log
[2024-01-09 10:47:53,437] - [opensipi.sipi_infra] - opensipi version: 0.1.0
[2024-01-09 10:47:53,437] - [opensipi.sipi_infra] - Log file for Run_20240109_104753 is created.
[2024-01-09 10:47:53,437] - [opensipi.sipi_infra] - Please put the design file to be simulated in the following directory:
C:\SIPIProj\Olympus\Dsn\
Has the board been put in the directory? [y/n]
```

A `Dsn` folder has been created under `Olympus`. Drop the `.brd` file there, then type
`y` in the command window and press <kbd>Enter</kbd>.

![image](/docs/Figures/drop_a_design.png)

### 6.4 Initial check

Check the logs — you'll see the initial check complete successfully.

```log
[2024-01-09 11:00:42,967] - [opensipi.sipi_infra./opensipi.sigrity_exec] - Initial check starts.
[2024-01-09 11:00:42,968] - [opensipi.sipi_infra./opensipi.sigrity_exec] - No known input format errors found.
[2024-01-09 11:00:42,969] - [opensipi.sipi_infra./opensipi.sigrity_exec] - All input net names in Sheet Col POSITIVE_NETS exist in the design file.
[2024-01-09 11:00:42,970] - [opensipi.sipi_infra./opensipi.sigrity_exec] - All input net names in Sheet Col NEGATIVE_NETS exist in the design file.
[2024-01-09 11:00:42,971] - [opensipi.sipi_infra./opensipi.sigrity_exec] - Netname comparison is done.
[2024-01-09 11:00:42,972] - [opensipi.sipi_infra./opensipi.sigrity_exec] - All input component names in Sheet Col POSITIVE_MAIN_PORTS exist in the design file.
[2024-01-09 11:00:42,973] - [opensipi.sipi_infra./opensipi.sigrity_exec] - All input component names in Sheet Col NEGATIVE_MAIN_PORTS exist in the design file.
[2024-01-09 11:00:42,974] - [opensipi.sipi_infra./opensipi.sigrity_exec] - All input component names in Sheet Col POSITIVE_AUX_PORTS exist in the design file.
[2024-01-09 11:00:42,974] - [opensipi.sipi_infra./opensipi.sigrity_exec] - All input component names in Sheet Col NEGATIVE_AUX_PORTS exist in the design file.
[2024-01-09 11:00:42,975] - [opensipi.sipi_infra./opensipi.sigrity_exec] - Component name comparison is done.
[2024-01-09 11:00:42,975] - [opensipi.sipi_infra./opensipi.sigrity_exec] - Initial check completes successfully.
```

### 6.5 Model check

You'll also find that the model check completes successfully.

```log
[2024-01-09 11:00:43,045] - [opensipi.sipi_infra./opensipi.sigrity_exec] - Check is running for SIM1_P0V9 ...
[2024-01-09 11:00:52,112] - [opensipi.sipi_infra./opensipi.sigrity_exec] - Check is done for SIM1_P0V9 after 0 mins and 9 secs!
[2024-01-09 11:00:52,112] - [opensipi.sipi_infra./opensipi.sigrity_exec] - Check is done for 1 out of total 2!
[2024-01-09 11:00:52,112] - [opensipi.sipi_infra./opensipi.sigrity_exec] - Check is running for SIM1_P1V8 ...
[2024-01-09 11:00:57,180] - [opensipi.sipi_infra./opensipi.sigrity_exec] - Check is done for SIM1_P1V8 after 0 mins and 5 secs!
[2024-01-09 11:00:57,180] - [opensipi.sipi_infra./opensipi.sigrity_exec] - Check is done for 2 out of total 2!
[2024-01-09 11:00:57,180] - [opensipi.sipi_infra./opensipi.sigrity_exec] - Successfully finished all runs!
[2024-01-09 11:00:57,180] - [opensipi.sipi_infra./opensipi.sigrity_exec] - Total elapsed time is 0 hours, 0 mins, and 14 secs!
[2024-01-09 11:00:57,180] - [opensipi.sipi_infra./opensipi.sigrity_exec] - Port counts are checked. Everything is correct!
[2024-01-09 11:00:57,180] - [opensipi.sipi_infra./opensipi.sigrity_exec] - Cap models are checked. All uses SPICE type models!
```

Because `op_pause_after_model_check` in `mntr_info` was set to `1`, the application pauses
the flow and prompts you to decide when to continue with the simulations.

```
Do you want to continue with simulations? [y/n]
```

### 6.6 Run the simulations

If no changes are needed to the simulation files, type `y` and press <kbd>Enter</kbd> to
continue. You'll see the simulation log shown below.

```log
[2024-01-09 11:18:18,079] - [opensipi.sipi_infra./opensipi.sigrity_exec] - Sim is running for SIM1_P0V9 ...
[2024-01-09 11:22:29,812] - [opensipi.sipi_infra./opensipi.sigrity_exec] - Sim is done for SIM1_P0V9 after 4 mins and 11 secs!
[2024-01-09 11:22:29,813] - [opensipi.sipi_infra./opensipi.sigrity_exec] - Sim is done for 1 out of total 2!
[2024-01-09 11:22:29,813] - [opensipi.sipi_infra./opensipi.sigrity_exec] - Sim is running for SIM1_P1V8 ...
[2024-01-09 11:26:20,454] - [opensipi.sipi_infra./opensipi.sigrity_exec] - Sim is done for SIM1_P1V8 after 3 mins and 50 secs!
[2024-01-09 11:26:20,454] - [opensipi.sipi_infra./opensipi.sigrity_exec] - Sim is done for 2 out of total 2!
[2024-01-09 11:26:20,454] - [opensipi.sipi_infra./opensipi.sigrity_exec] - Successfully finished all runs!
[2024-01-09 11:26:20,454] - [opensipi.sipi_infra./opensipi.sigrity_exec] - Total elapsed time is 0 hours, 8 mins, and 2 secs!
```

### 6.7 Collect the results

Once the simulations are done, results such as `.sNp` files and DCR CSV files are copied
to the folder `Result`.

```log
[2024-01-09 11:26:20,454] - [opensipi.sipi_infra./opensipi.sigrity_exec] - SIM1_P0V9__20240109_110029_010924_112229_34756_DCfitted.s2p has been copied to C:\SIPIProj\Olympus\Xtract\Run_20240109_110029\Result\SNP_DCfitted\
[2024-01-09 11:26:20,454] - [opensipi.sipi_infra./opensipi.sigrity_exec] - SIM1_P0V9__20240109_110029_010924_112229_34756_S.s2p has been copied to C:\SIPIProj\Olympus\Xtract\Run_20240109_110029\Result\SNP_S\
[2024-01-09 11:26:20,454] - [opensipi.sipi_infra./opensipi.sigrity_exec] - SIM1_P1V8__20240109_110029_010924_112619_34756_DCfitted.s3p has been copied to C:\SIPIProj\Olympus\Xtract\Run_20240109_110029\Result\SNP_DCfitted\
[2024-01-09 11:26:20,454] - [opensipi.sipi_infra./opensipi.sigrity_exec] - SIM1_P1V8__20240109_110029_010924_112619_34756_S.s3p has been copied to C:\SIPIProj\Olympus\Xtract\Run_20240109_110029\Result\SNP_S\
```

Figures and a report are created subsequently.

```log
[2024-01-09 11:26:20,481] - [opensipi.sipi_infra] - SIM1_P0V9__20240109_110029_010924_112229_34756_DCfitted.s2p is included for plotting!
[2024-01-09 11:26:20,490] - [opensipi.sipi_infra] - SIM1_P1V8__20240109_110029_010924_112619_34756_DCfitted.s3p is included for plotting!
[2024-01-09 11:26:22,025] - [opensipi.sipi_infra] - SIM1_P0V9__20240109_110029_010924_112229_34756_S.s2p is included for plotting!
[2024-01-09 11:26:22,025] - [opensipi.sipi_infra] - SIM1_P1V8__20240109_110029_010924_112619_34756_S.s3p is included for plotting!
```

## Next Steps

- Adapt the input tables to your own design — see
  [Front-end Files IO](/docs/Home/Front-end-Files-IO.md).
- Understand what the platform creates on disk and when — see
  [Mid-layer Platform](/docs/Home/Mid-layer-Platform.md).
