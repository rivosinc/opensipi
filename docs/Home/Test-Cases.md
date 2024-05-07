<!--
SPDX-FileCopyrightText: 2024 Rivos Inc.

SPDX-License-Identifier: Apache-2.0
-->

# Design Files
The design files used to demonstrate the application can be obtained from Open Compute Project (OCP). I just randomly picked up one collateral package from [here](https://www.opencompute.org/contributions?refinementList%5Bproject%5D%5B0%5D=Server&refinementList%5Bcontributor%5D%5B0%5D=ZT%20Systems&configure%5BfacetFilters%5D%5B0%5D=archived%3Afalse). Please make sure you download the right files (see pictures below) to work with the provided input sheets. Choose the project based on the Intel chip.
![image](/docs/Figures/OCP_testcase.png)

Choose the following layout and schematic files to work with.

![image](/docs/Figures/test_layout_sch.png)

Since the project is codenamed as Olympus, why not name the simulation project as Olympus then. Later you'll see Olympus is used as the directory name where you keep your simulation files.

# Component Library
In Cadence Sigrity tools, a component will be automatically included for simulations if all the nets connected to the component's pins are enabled. It's the users' responsibility to assign the right models for each component included for simulations. The component model assignment is stored in the .amm file. Please make sure the .amm file directory is provided in the "config_sigrity.yaml" file.

# Solver Setting Options

Make sure the .xml option file directories are provided in the "config_sigrity.yaml" file.

# Input Files
Choose one of the following sets of files to try out the application for a specific extraction goal.
- PDN

[Input Sheets](examples/Olympus/Sim_Input/Sigrity_PDN)

[Main Function](examples/Olympus/Script/Olympus_PCB_xtractPDN.py)

- LSIO

[Input Sheets](examples/Olympus/Sim_Input/Sigrity_LSIO)

[Main Function](examples/Olympus/Script/Olympus_PCB_xtractLSIO.py)

- HSIO

[Input Sheets](examples/Olympus/Sim_Input/Sigrity_HSIO)

[Main Function](examples/Olympus/Script/Olympus_PCB_xtractHSIO.py)

- DCR

[Input Sheets](examples/Olympus/Sim_Input/Sigrity_DCR)

[Main Function](examples/Olympus/Script/Olympus_PCB_xtractDCR.py)

# Simulation Configurations
The folder structure will be created as shown below.

![image](/docs/Figures/Folder_Structure_SimInput.png)

Let's start with creating a new folder anywhere you like. I'll just put it in the root of C Drive. Rename it to SIPIProj. Actually any folder name will do.

Create a new folder under SIPIProj. This will be your project folder. Name the folder with a project name, e.g. Olympus in this test case. The folder name is not critical to use the codes. It simply helps differentiate the projects you are working on.

Create a folder under Olympus and rename it to Script to store the simulation launching python script. Copy Olympus_PCB_xtractPDN.py to the above-mentioned folder Script.

Under the project folder, i.e. Olympus, create a new folder to store the simulation input information. Give the new folder a meaningful name, e.g. Sim_Input.

Under the folder Sim_Input, create a new folder to store the set of simulation input information. In this test case, a folder named Sigrity_PDN is created.

Put the csv files containing the simulation input to the folder Sigrity_PDN.

# Run the Application
Before running Olympus_PCB_xtractPDN.py, make sure your input information is correct. The contents of Olympus_PCB_xtractPDN.py is shown below. Make sure config_dir, input_type, input_folder all specified correctly.
```python
from opensipi.integrated_flows import sim2report


input_info = {
    'config_dir': r'C:\SIPIProj\Olympus\Sim_Input'+'\\',
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

Open a command window in the folder Script and launch Olympus_PCB_xtractPDN.py.

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
