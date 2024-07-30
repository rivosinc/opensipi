<!--
SPDX-FileCopyrightText: 2024 Rivos Inc.

SPDX-License-Identifier: Apache-2.0
-->

# Overview
Here is the flow to evaluate the OpenSIPI platform with the provided examples.
- Download the specified design files
- Install OpenSIPI
- Download and revise the example configuration files and place the whole folder in the HOME directory.
- Create a folder "SIPIProj" in any working directory
- Download the example Olympus input files and place them in the folder "SIPIProj"
- Run the main function

## Download the design files
The design files used to demonstrate the application are obtained from Open Compute Project (OCP). In the [OCP Contributions](https://www.opencompute.org/contributions) webpage, search for "Intel Olympus ZTSystems" and download the board design package to work with the provided input info.
![image](/docs/Figures/OCP_testcase.png)

Unzip the downloaded design package. Choose the following layout and schematic files to work on.

![image](/docs/Figures/test_layout_sch.png)

Since the project is codenamed as Olympus, why not name the simulation project as Olympus. Later you'll see Olympus is used to name the directory where your simulation files are kept.

## Install OpenSIPI
Open a terminal or command window. Install or update the tool using the following command.

```
pip3 install git+https://github.com/rivosinc/opensipi
```

## Download and revise the exmaple configuration files
After downloading the example configuraiton files in [a zipped package](/examples/Linux/opensipi_config.zip), unzip it and place the whole folder "opensipi_config" in the HOME directory.

Detailed descriptions of the configuration files can be found [here](/docs/Home/Installation-and-Configuration.md). For this specific test case, the following parameters in the "config_sigrity.yaml" file have to be revised based on your available tool version and licenses.
- SIG_VER

    e.g. Sigrity2024.0
- SIG_LIC

    One way to obtain the available license names is to check in the utility tool "Cadence Sigrity Suite Manager". One example is given here to demo the process. Assume that Clarity3dlayout licenses are to be queried. As shown below, launch the utility and select Clarity3DLayout. On the right side, there are three suite licenses available for 24.0 version, i.e. Clarity 3D, Clarity IC Package Extraction Suite, and Clarity PCB Extraction Suite. But these are not the exact license names used to launch the tool. Select Clarity IC Package Extraction Suite and click the below button "Who is using". In the pop-up dialog, "ICP_Extract_20" is the exact license name for Clarity IC Package Extraction Suite. Repeat the flow for the other two available licenses to get their exact names.

![image](/docs/Figures/LicMng.png)

Notice: The example AMM library file and Cadence Sigrity option files are provided as a starting point for users. They are supposed to be revised based on needs.

## Create Folder "SIPIProj"
In any working directory, create a new directory "SIPIProj" if not exist.

## Download the input Files
After downloading the example Olympus input files in [a zipped package](/examples/Linux/Olympus.zip), unzip it and place the whole folder "Olympus" under Folder "SIPIProj".

Inside Folder "Olympus", main functions are stored under Folder "Script" and input files are stored under Folder "Sim_Input". Choose one set of files to try out the OpenSIPI platform for a specific extraction goal.

The folder structure will be created as shown below. The picture is taken from Windows OS. But the folder structure is the same.

![image](/docs/Figures/Folder_Structure_SimInput.png)

The online version of the input files and main funcitons are listed below.
- PDN

[Input Files](/examples/Olympus/Sim_Input/Sigrity_PDN)

[Main Function](/examples/Olympus/Script/Olympus_PCB_xtractPDN.py)

- LSIO

[Input Files](/examples/Olympus/Sim_Input/Sigrity_LSIO)

[Main Function](/examples/Olympus/Script/Olympus_PCB_xtractLSIO.py)

- HSIO

[Input Files](/examples/Olympus/Sim_Input/Sigrity_HSIO)

[Main Function](/examples/Olympus/Script/Olympus_PCB_xtractHSIO.py)

- DCR

[Input Files](/examples/Olympus/Sim_Input/Sigrity_DCR)

[Main Function](/examples/Olympus/Script/Olympus_PCB_xtractDCR.py)

## Run the Main Function
Use the PDN extraction test case as an example here.

Find the main function python file under "xxx/SIPIProj/Olympus/Script/Olympus_PCB_xtractPDN.py". Before running Olympus_PCB_xtractPDN.py, make sure your input information is correct. The contents of Olympus_PCB_xtractPDN.py is shown below. Make sure config_dir, input_type, input_folder all specified correctly.
```python
from opensipi.integrated_flows import sim2report


input_info = {
    'config_dir': r'xxx/SIPIProj/Olympus/Sim_Input/',
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

Open a command window in the folder "Script" and launch Olympus_PCB_xtractPDN.py.
```
python Olympus_PCB_xtractPDN.py
```

You'll be asked to drop a design file to the specified directory.
```
[2024-01-09 10:47:53,437] - [opensipi.sipi_infra] - opensipi version: 0.1.0
[2024-01-09 10:47:53,437] - [opensipi.sipi_infra] - Log file for Run_20240109_104753 is created.
[2024-01-09 10:47:53,437] - [opensipi.sipi_infra] - Please put the design file to be simulated in the following directory:
C:\SIPIProj\Olympus\Dsn\
Has the board been put in the directory? [y/n]
```
A Dsn folder has been created under Olympus. Drop the brd file there. Type "y" in the command window and press Enter.

![image](/docs/Figures/drop_a_design.png)

Check the logs, you'll see initial check completes successfully.
```
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

You'll also find model check completes successfully.
```
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

Because 'op_pause_after_model_check' in 'mntr_info' was set to '1', the application pauses the flow and prompts the user to decide when to continue with simulations.
```
Do you want to continue with simulations? [y/n]
```

If no changes are needed to the simulation files, type in 'y' and press 'Enter' to continue. You'll see the simulation log shown as below.
```
[2024-01-09 11:18:18,079] - [opensipi.sipi_infra./opensipi.sigrity_exec] - Sim is running for SIM1_P0V9 ...
[2024-01-09 11:22:29,812] - [opensipi.sipi_infra./opensipi.sigrity_exec] - Sim is done for SIM1_P0V9 after 4 mins and 11 secs!
[2024-01-09 11:22:29,813] - [opensipi.sipi_infra./opensipi.sigrity_exec] - Sim is done for 1 out of total 2!
[2024-01-09 11:22:29,813] - [opensipi.sipi_infra./opensipi.sigrity_exec] - Sim is running for SIM1_P1V8 ...
[2024-01-09 11:26:20,454] - [opensipi.sipi_infra./opensipi.sigrity_exec] - Sim is done for SIM1_P1V8 after 3 mins and 50 secs!
[2024-01-09 11:26:20,454] - [opensipi.sipi_infra./opensipi.sigrity_exec] - Sim is done for 2 out of total 2!
[2024-01-09 11:26:20,454] - [opensipi.sipi_infra./opensipi.sigrity_exec] - Successfully finished all runs!
[2024-01-09 11:26:20,454] - [opensipi.sipi_infra./opensipi.sigrity_exec] - Total elapsed time is 0 hours, 8 mins, and 2 secs!
```

Once simulations are done, results like snp files and DCR csv files are copied to the folder Results.
```
[2024-01-09 11:26:20,454] - [opensipi.sipi_infra./opensipi.sigrity_exec] - SIM1_P0V9__20240109_110029_010924_112229_34756_DCfitted.s2p has been copied to C:\SIPIProj\Olympus\Xtract\Run_20240109_110029\Result\SNP_DCfitted\
[2024-01-09 11:26:20,454] - [opensipi.sipi_infra./opensipi.sigrity_exec] - SIM1_P0V9__20240109_110029_010924_112229_34756_S.s2p has been copied to C:\SIPIProj\Olympus\Xtract\Run_20240109_110029\Result\SNP_S\
[2024-01-09 11:26:20,454] - [opensipi.sipi_infra./opensipi.sigrity_exec] - SIM1_P1V8__20240109_110029_010924_112619_34756_DCfitted.s3p has been copied to C:\SIPIProj\Olympus\Xtract\Run_20240109_110029\Result\SNP_DCfitted\
[2024-01-09 11:26:20,454] - [opensipi.sipi_infra./opensipi.sigrity_exec] - SIM1_P1V8__20240109_110029_010924_112619_34756_S.s3p has been copied to C:\SIPIProj\Olympus\Xtract\Run_20240109_110029\Result\SNP_S\
```
Figures and a report is created subsequently.
```
[2024-01-09 11:26:20,481] - [opensipi.sipi_infra] - SIM1_P0V9__20240109_110029_010924_112229_34756_DCfitted.s2p is included for plotting!
[2024-01-09 11:26:20,490] - [opensipi.sipi_infra] - SIM1_P1V8__20240109_110029_010924_112619_34756_DCfitted.s3p is included for plotting!
[2024-01-09 11:26:22,025] - [opensipi.sipi_infra] - SIM1_P0V9__20240109_110029_010924_112229_34756_S.s2p is included for plotting!
[2024-01-09 11:26:22,025] - [opensipi.sipi_infra] - SIM1_P1V8__20240109_110029_010924_112619_34756_S.s3p is included for plotting!
```
