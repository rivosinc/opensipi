<!--
SPDX-FileCopyrightText: 2024 Rivos Inc.

SPDX-License-Identifier: Apache-2.0
-->

# Folder Structure Explained
## Project Level
![image](docs/Figures/Folder_Structure_Top.png)

The following folders are created manually.
- SIPIProj: The root folder to keep all SIPI simulation files.
- Olympus: The project folder to keep only project specific files.
- Script: The python scripts to launch applications stored here.
- Sim_Input: The simulation input information is kept here. The simulation input files are a set of csv files. For better arrangement, they are typically kept in a sub-folder, e.g. Sigrity_PDN etc. in the picture.
The following folders are created automatically.
- Dsn: The board/package design files are kept here.
- Xtract: Each run of the simulations and their result files are kept here.

## Each Run
![image](docs/Figures/Folder_Structure_Run.png)

Each run folder is kept under Xtract. All the folders under Xtract are created automatically.

- Run_[time_stamp]: The root folder for each run. The time_stamp refers to the application launching time.
- LocalDsn: A local design copy and a parent simulation model is created here. Stackup and material files are stored here. The extracted component and net information are kept here too.
- LocalScript: All scripts that are used to launch the simulation tools are kept here. These scripts are written in tool-specific languages, e.g. tcl for Sigrity tools.
- Log: Log files of each run are kept here.
- Report: Plots of S-parameters and a summary report are stored here.
- Result: S-parameters and DCR results are kept here.
- SimFile: Final simulation model files are kept here.
- ModelCheck: Simulation models are first created by running the scripts and stored in the ModelCheck folder. The details of the generated ports and the capacitor models are exported here for further check.

# Workflow Explained

Once the Class Platform is instantiated, the folder structure introduced above will be created automatically. The simulation input information in csv files which are stored in Folder Sim_Input are read in and quickly scanned for some simple format errors like ... If no errors found, a message will pop up afterwards prompting the users to drop the PCB or package design file to be simulated in a specified directory and type "Y" once done.

The flow continues. In the flow based on Sigrity tools, tcl scripts used to launch simulation software are created first and kept in LocalScript.

A parent simulation model file is created first if it doesn't exist yet, which is converted from the dropped design file in the simulation software. Meanwhile, stack-up, material information, and simulation settings have been applied to the parent model as well. The parent simulation model is stored under Run directory and specifically in Folder LocalDsn. Besides, when creating the parent simulation model, the existing components and nets in the design are queried and exported in all_comps.info and all_nets.info, respectively. These information will be treated as golden source to compare against the input information in the csv files during Model Check process.

Move on to the next step, Model Check. The parent model after applying each simulation info like enabled nets and port definitions is saved as an individual simulation model. These models are all kept in the directory SimFile/ModelCheck/. During the process of Model Check, the successfully generated ports and capacitor models in use are exported in Ports__[SheetKey]__[Unique_Key].csv and Caps__[SheetKey]__[Unique_Key].csv, respectively. The port info is later used to determine whether all ports are created as expected. If not, the flow will stop and the user can debug if any input info is not provided correctly. The cap info is later used to tell users whether any SPICE-like models are applied to capacitors instead of simple RLC models which are typically inaccurate. If any capacitor doesn't use a SPICE-like model, a warning will be given in the log but the flow will continue. Notice there is a knob to check if users want to pause here before starting real simulations. Be default, the flow will not pause. You'll soon see why you may want to pause the flow in the next paragraph.

In the next step, Model Run, the simulation model created during the process of Model Check is copied to the directory SimFile/ and simulation is started based on the newly copied model. Once a simulation is done, [SheetKey]__[Unique_Key].done file is created. Because a real simulation is based on a copy of whatever model files in the Folder ModelCheck, if the user pause the flow right after the Model Check process, they have a chance to modify the model as desired. It's suggested only having some revisions that are not easy to automate and never changing port definitions otherwise the post-processing may break.

Once all simulations are finished, a sim.done file is created. Simulation results are copied to the directory /Results/.

A summary report is then created out of the simulation results.
