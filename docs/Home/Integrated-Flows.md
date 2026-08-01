<!--
SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
SPDX-FileCopyrightText: 2024 Rivos Inc.

SPDX-License-Identifier: Apache-2.0
-->

[← Documentation Home](/docs/Home.md) · [User Manual](/docs/Home/User-Manual.md)

# Integrated Flows

Top-level entry points, defined in `opensipi.integrated_flows`. Each one runs an
extraction from input tables all the way to a report.

| Function                                          | Input source  | Output destination      |
| ------------------------------------------------- | ------------- | ----------------------- |
| [`sim2report`](#sim2reportinput_info-mntr_info)   | CSV files     | Local run folder        |
| `sim2report_gsuites`                              | Google Sheet  | Local folder + Google Drive |

---

## `sim2report(input_info, mntr_info)`

### Usage

This function takes CSV input info to the platform, parses it into scripts to automate
S-para extraction, processes the results, and generates a report.

```python
from opensipi.integrated_flows import sim2report
```

### Inputs

#### `input_info` — dict, input related information

| Key             | Type | Required                        | Description                                                                                                                                                                                   |
| --------------- | ---- | ------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `input_type`    | str  | Yes                             | Input file type — `"csv"` or `"gsheet"`.                                                                                                                                                      |
| `input_dir`     | str  | Yes, if `input_type` is `"csv"` | Directory of the input CSV files.                                                                                                                                                             |
| `input_folder`  | str  | Yes, if `input_type` is `"csv"` | Folder name of the input CSV files. The specified folder contains the required input info for a specific extraction type such as PDN, LSIO, or HSIO.                                          |
| `op_run_name`   | str  | Optional                        | The time stamp of the `Run` folder. Omit it or pass an empty string by default — a folder `Run_(time stamp)` is then created automatically. To hack into an existing `Run` folder, pass that folder's existing time stamp. |

#### `mntr_info` — dict, monitor related information

| Key                          | Type | Required | Description                                                                                       |
| ---------------------------- | ---- | -------- | ------------------------------------------------------------------------------------------------- |
| `email`                      | str  | —        | Email address to receive notifications. **NOT ENABLED YET!**                                      |
| `op_pause_after_model_check` | int  | Optional | `1` — the flow pauses after model check is done. `0` — it doesn't. Defaults to `0` if omitted.    |

### Output

**`report_dir`** — str, the full path to the generated report.

### Example

```python
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

---

## `sim2report_gsuites(input_info, mntr_info)`

### Usage

The Google Suites counterpart of `sim2report`. It reads the simulation input from a
Google Sheet, runs the same extraction and reporting flow, and then uploads the results to
Google Drive.

```python
from opensipi.integrated_flows import sim2report_gsuites
```

### Inputs

`mntr_info` is identical to `sim2report`. `input_info` differs as follows.

| Key            | Type | Required | Description                                                                            |
| -------------- | ---- | -------- | ---------------------------------------------------------------------------------------- |
| `input_type`   | str  | Yes      | Must be `"gsheet"`.                                                                    |
| `input_url`    | str  | Yes      | URL of the Google Sheet holding the input tabs.                                        |
| `proj_dir`     | str  | Yes      | The project directory, e.g. `.../SIPIProj/Olympus/`. There is no `input_dir` to derive it from. |
| `output_type`  | str  | Optional | `"gdrive"` to upload the results to Google Drive. Defaults to `"local"`.               |
| `op_run_name`  | str  | Optional | Same meaning as for `sim2report`.                                                      |

The Google account credentials and target Drive IDs are **not** passed here — they are
read from `config_gsuites.yaml` in the `opensipi_config` folder. See
[Installation and Configuration](/docs/Home/Installation-and-Configuration.md).

### Output

None. The report is written to the run folder and, when `output_type` is `"gdrive"`,
uploaded to Google Drive.
