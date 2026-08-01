<!--
SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
SPDX-FileCopyrightText: 2024 Rivos Inc.

SPDX-License-Identifier: Apache-2.0
-->

[← Documentation Home](/docs/Home.md)

# Mid-layer Platform

This page describes the on-disk folder structure the platform creates and the workflow
it walks through on every run.

## Folder Structure

### Project Level

![image](/docs/Figures/Folder_Structure_Top.png)

```text
SIPIProj/                 <- created manually
└── Olympus/              <- created manually
    ├── Script/           <- created manually
    ├── Sim_Input/        <- created manually
    │   └── Sigrity_PDN/
    ├── Dsn/              <- created automatically
    └── Xtract/           <- created automatically
```

**Created manually**

| Folder      | Purpose                                                                                                                                                            |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `SIPIProj`  | The root folder to keep all SIPI simulation files.                                                                                                                 |
| `Olympus`   | The project folder to keep only project-specific files.                                                                                                            |
| `Script`    | The Python scripts to launch applications are stored here.                                                                                                         |
| `Sim_Input` | The simulation input information is kept here, as a set of CSV files. For better arrangement they are typically kept in a sub-folder, e.g. `Sigrity_PDN` above.    |

**Created automatically**

| Folder   | Purpose                                                     |
| -------- | ----------------------------------------------------------- |
| `Dsn`    | The board/package design files are kept here.               |
| `Xtract` | Each run of the simulations and its result files kept here. |

### Each Run

![image](/docs/Figures/Folder_Structure_Run.png)

Each run folder is kept under `Xtract`. All the folders under `Xtract` are created
automatically.

```text
Xtract/
└── Run_[time_stamp]/
    ├── LocalDsn/
    ├── LocalScript/
    ├── Log/
    ├── Report/
    ├── Result/
    └── SimFile/
        └── ModelCheck/
```

| Folder             | Contents                                                                                                                                                          |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `Run_[time_stamp]` | The root folder for each run. The `time_stamp` refers to the application launching time.                                                                          |
| `LocalDsn`         | A local design copy and a parent simulation model. Stackup and material files are stored here, as are the extracted component and net information.                |
| `LocalScript`      | All scripts used to launch the simulation tools, written in tool-specific languages — e.g. Tcl for Sigrity tools.                                                 |
| `Log`              | Log files of each run.                                                                                                                                            |
| `Report`           | Plots of S-parameters and a summary report.                                                                                                                       |
| `Result`           | S-parameters and DCR results.                                                                                                                                     |
| `SimFile`          | Final simulation model files.                                                                                                                                     |
| `SimFile/ModelCheck` | Simulation models are first created by running the scripts and stored here. The details of the generated ports and the capacitor models are exported for review.|

## Workflow

### 1. Instantiate the platform and read the input

Once the class `Platform` is instantiated, the folder structure introduced above is
created automatically. The simulation input information in the CSV files stored in
folder `Sim_Input` is read in and quickly scanned for simple format errors.

If no errors are found, a message pops up prompting the user to drop the PCB or package
design file to be simulated in a specified directory and to type `Y` once done.

### 2. Generate the scripts

In the flow based on Sigrity tools, the Tcl scripts used to launch the simulation
software are created first and kept in `LocalScript`.

### 3. Build the parent simulation model

A parent simulation model file is created first if it doesn't exist yet, converted from
the dropped design file in the simulation software. Stack-up, material information, and
simulation settings are applied to the parent model as well. The parent simulation model
is stored under the run directory, specifically in folder `LocalDsn`.

While creating the parent simulation model, the existing components and nets in the
design are queried and exported to `all_comps.info` and `all_nets.info` respectively.
This information is treated as the golden source to compare against the input
information in the CSV files during Model Check.

### 4. Model Check

The parent model, after applying each simulation's info such as enabled nets and port
definitions, is saved as an individual simulation model. These models are all kept in
the directory `SimFile/ModelCheck/`.

During Model Check, the successfully generated ports and the capacitor models in use are
exported to `Ports__[SheetKey]__[Unique_Key].csv` and `Caps__[SheetKey]__[Unique_Key].csv`
respectively.

- **Port info** determines whether all ports are created as expected. If not, the flow
  stops and the user can debug whichever input info was not provided correctly.
- **Cap info** tells the user whether any SPICE-like models are applied to capacitors
  instead of the simple RLC models, which are typically inaccurate. If any capacitor
  doesn't use a SPICE-like model, a warning is written to the log but the flow continues.

> [!TIP]
> There is a knob to pause here before starting real simulations
> (`op_pause_after_model_check`). By default the flow does **not** pause. The next step
> explains why you may want it to.

### 5. Model Run

The simulation model created during Model Check is copied to the directory `SimFile/`
and the simulation is started based on the newly copied model. Once a simulation is done,
a `[SheetKey]__[Unique_Key].done` file is created.

Because a real simulation is based on a copy of whatever model files are in folder
`ModelCheck`, pausing the flow right after Model Check gives you a chance to modify the
model as desired.

> [!WARNING]
> Only make revisions that are hard to automate, and **never** change port definitions —
> otherwise post-processing may break.

### 6. Collect results and report

Once all simulations are finished, a `sim.done` file is created and the simulation
results are copied to the directory `Result/`. A summary report is then created out of
the simulation results.
