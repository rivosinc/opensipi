<!--
SPDX-FileCopyrightText: 2024 Rivos Inc.

SPDX-License-Identifier: Apache-2.0
-->

# Integrated Flows

## sim2report(input_info, mntr_info)

**Usage**:

This function takes csv input info to the Platform, parses them into scripts to automate S-para extraction, processes results and generates a report.

**Inputs**:
- **input_info**: dict, input related information

	**_input_type_**: str, input file type. "csv" or "gsheet".

	**_input_dir_**: str, directory of input csv files. This key is mandatory if *input_type* = "csv".

	**_input_folder_**: str, folder name of the input csv files, the specified folder contains the required input info for a specific extraction type like PDN, LSIO, HSIO etc. This key is mandatory if *input_type* = "csv".

	**_op_run_name_**: \[optional\], str, the time stamp of the "Run" folder. It should be omitted or assigned empty string by default. Each time an extraction starts, a folder called "Run_(time stamp)" is created automatically. In order to hack into an existing Run folder, set the existing time stamp to this key.

- **mntr_info**: dict, monitor related information

	**_email_**: str, email address to receive notifications. NOT ENABLED YET!

	**_op_pause_after_model_check_**: int, 1-> flow pauses after model check is done, 0-> flow doesn't pause. If the key is omitted, 0 is applied by default.

**Example**:

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

sim2report(input_info, mntr_info)
```
