<!--
SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
SPDX-FileCopyrightText: 2024 Rivos Inc.

SPDX-License-Identifier: Apache-2.0
-->

[← Documentation Home](/docs/Home.md) · [User Manual](/docs/Home/User-Manual.md)

# Classes

## `Platform`

Defined in `opensipi.sipi_infra`.

### Usage

This class serves as the OpenSIPI platform. It takes input info, parses it into scripts to
automate S-para extraction, processes the results, and generates a report.

Use it directly when you want to drive the individual steps yourself. For the common case,
prefer an [integrated flow](/docs/Home/Integrated-Flows.md).

```python
from opensipi.sipi_infra import Platform
```

### Constructor

`Platform(input_info)`

#### `input_info` — dict, input related information

| Key            | Type | Required                        | Description                                                                                                                                                                                   |
| -------------- | ---- | ------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `input_type`   | str  | Yes                             | Input file type — `"csv"` or `"gsheet"`.                                                                                                                                                      |
| `input_dir`    | str  | Yes, if `input_type` is `"csv"` | Directory of the input CSV files.                                                                                                                                                             |
| `input_folder` | str  | Yes, if `input_type` is `"csv"` | Folder name of the input CSV files. The specified folder contains the required input info for a specific extraction type such as PDN, LSIO, or HSIO.                                          |
| `op_run_name`  | str  | Optional                        | The time stamp of the `Run` folder. Omit it or pass an empty string by default — a folder `Run_(time stamp)` is then created automatically. To hack into an existing `Run` folder, pass that folder's existing time stamp. |

Instantiating `Platform` creates the run folder tree and reads the input immediately. The
parsed input is available on the instance as **`pf.input_data`** (dict).

#### Example

```python
input_info = {
    "input_dir": r"C:\SIPIProj\Olympus\Sim_Input" + "\\",
    "input_type": "csv",
    "input_folder": "Sigrity_PDN",
    "op_run_name": "",
}

pf = Platform(input_info)
```

### Methods

#### `drop_dsn_file(xtract_tool=None)`

Requests the user to drop a design file into an automatically created directory, then
waits for confirmation at the terminal.

**Inputs**

| Name          | Type | Description                                                                                    |
| ------------- | ---- | ------------------------------------------------------------------------------------------------ |
| `xtract_tool` | str  | The extraction tool in use, e.g. `"Sigrity"`. Determines whether `.spd` is an accepted format. |

**Accepted design file formats**

| Format | Extensions                                       |
| ------ | ------------------------------------------------ |
| BRD    | `.brd`                                           |
| ODB++  | `.tgz`, `.zip`, `.gz`, `.z`, `.tar`, `.7z`       |
| MCM    | `.mcm`                                           |
| SPD    | `.spd` — only when `xtract_tool` is `"Sigrity"`  |

**Example**

```python
xtract_tool = pf.input_data["settings"]["EXTRACTIONTOOL"]
pf.drop_dsn_file(xtract_tool)
```

#### `parser(input_data)`

Parses the input data based on the tool in use.

**Inputs**

| Name         | Type | Description                                        |
| ------------ | ---- | -------------------------------------------------- |
| `input_data` | dict | The input info, normally taken from `pf.input_data`. |

**Outputs**

| Name       | Type   | Description                                                              |
| ---------- | ------ | -------------------------------------------------------------------------- |
| `sim_exec` | object | The configured solver executor, e.g. `PowersiPdnExec` for Sigrity + PDN.  |

**Example**

```python
sim_exec = pf.parser(pf.input_data)
```

#### `run(sim_exec, mntr_info)`

Runs the sims and returns the result info.

**Inputs**

| Name        | Type   | Description                  |
| ----------- | ------ | ---------------------------- |
| `sim_exec`  | object | The output of `parser()`.    |
| `mntr_info` | dict   | Monitor related information. |

**Outputs**

| Name                 | Type | Description                                          |
| -------------------- | ---- | ---------------------------------------------------- |
| `result_config_dir`  | str  | The full path to the result configuration file.      |
| `report_config_dir`  | str  | The full path to the report configuration file.      |

**Example**

```python
mntr_info = {
    "email": "",
    "op_pause_after_model_check": 1,
}

result_config_dir, report_config_dir = pf.run(sim_exec, mntr_info)
```

#### `process_snp(result_config_dir)`

Post-processes the results and generates the plots.

**Inputs**

| Name                | Type | Description                                     |
| ------------------- | ---- | ----------------------------------------------- |
| `result_config_dir` | str  | The full path to the result configuration file. |

**Outputs**

| Name          | Type | Description                                        |
| ------------- | ---- | -------------------------------------------------- |
| `result_dict` | dict | The post-processing results, kept in a dictionary. |

**Example**

```python
result_dict = pf.process_snp(result_config_dir)
```

#### `report(result_config_dir, report_config_dir)`

Generates a report out of the processed results.

**Inputs**

| Name                | Type | Description                                     |
| ------------------- | ---- | ----------------------------------------------- |
| `result_config_dir` | str  | The full path to the result configuration file. |
| `report_config_dir` | str  | The full path to the report configuration file. |

**Outputs**

| Name         | Type | Description                    |
| ------------ | ---- | ------------------------------ |
| `report_dir` | str  | The full path to the report.   |

**Example**

```python
report_dir = pf.report(result_config_dir, report_config_dir)
```

### Putting It Together

The sequence below is what [`sim2report()`](/docs/Home/Integrated-Flows.md) does.

```python
pf = Platform(input_info)
xtract_tool = pf.input_data["settings"]["EXTRACTIONTOOL"]
pf.drop_dsn_file(xtract_tool)
sim_exec = pf.parser(pf.input_data)
result_config_dir, report_config_dir = pf.run(sim_exec, mntr_info)
report_dir = pf.report(result_config_dir, report_config_dir)
```
