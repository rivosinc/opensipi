<!--
SPDX-FileCopyrightText: 2024 Rivos Inc.

SPDX-License-Identifier: Apache-2.0
-->

# Class Platform()

**Usage**:

This class serves as the OpenSIPI platform. It takes input info, parses them into scripts to automate S-para extraction, processes results and generates a report.

**Inputs**:

- **input_info**: dict, input related information

  **Keys**:

	**_input_type_**: str, input file type. "csv" or "gsheet".

	**_input_dir_**: str, directory of input csv files. This key is mandatory if _input_type_ = "csv".

	**_input_folder_**: str, folder name of the input csv files, the specified folder contains the required input info for a specific extraction type like PDN, LSIO, HSIO etc. This key is mandatory if _input_type_ = "csv".

	**_op_run_name_**: \[optional\], str, the time stamp of the "Run" folder. It should be omitted or assigned empty string by default. Each time an extraction starts, a folder called "Run_(time stamp)" is created automatically. In order to hack into an existing Run folder, set the existing time stamp to this key.

**Example**:

```python
input_info = {
    "input_dir": r"C:\SIPIProj\Olympus\Sim_Input" + "\\",
    "input_type": "csv",
    "input_folder": "Sigrity_PDN",
    "op_run_name": "",
}

pf = Platform(input_info)
```

## Methods

- **drop_dsn_file()**

**Usage**:

The platform requests the user to drop a design file to an automatically created directory. The following design file formats are accepted.

BRD: .brd

ODB++: .tgz, .zip, .gz, .z, .tar, .7z

MCM: .mcm

SPD: .spd (only works when the ExtractionTools is set to "Sigrity")

**Example**:

```python
pf.drop_dsn_file()
```

- **read_inputs()**

**Usage**:

Read the input info needed for the extraction setup.

**Outputs**:

**_input_data_**: dict

**Example**:

```python
input_data = pf.read_inputs()
```

- **parser(input_data)**

**Usage**:

Parse the input data based on the tool in use. This method must not be called before **read_inputs()**.

**Inputs**:

**_input_data_**: dict

**Outputs**:

**_sim_exec_**: dict

**Example**:

```python
sim_exec = pf.parser(input_data)
```

- run(sim_exec, mntr_info)

**Usage**:

Run sims and return the result info.

**Inputs**:

**_sim_exec_**: dict

**_mntr_info_**: dict, monitor related information

**Outputs**:

**_result_config_dir_**: str, the full path to the result configuration file.

**_report_config_dir_**: str, the full path to the report configuration file.

**Example**:

```python
mntr_info = {
    "email": "",
    "op_pause_after_model_check": 1,
}

result_config_dir, report_config_dir = pf.run(sim_exec, mntr_info)
```

- process_snp(result_config_dir)

**Usage**:

Post-process results and generate plots.

**Inputs**:

**_result_config_dir_**: str, the full path to the result configuration file.

**Outputs**:

**_result_dict_**: dict, post-processing results are kept in a dictionary.

**Example**:

```python
result_dict = pf.process_snp(result_config_dir)
```

- report(result_config_dir, report_config_dir)

**Usage**:

Generate a report out of the processed results.

**Inputs**:

**_result_config_dir_**: str, the full path to the result configuration file.

**_report_config_dir_**: str, the full path to the report configuration file.

**Outputs**:

**_report_dir_**: str, a full path to the report.

**Example**:

```python
report_dir = pf.report(result_config_dir, report_config_dir)
```
