<!--
SPDX-FileCopyrightText: 2024 Rivos Inc.

SPDX-License-Identifier: Apache-2.0
-->

## Class Platform(input_info)

Usage: This class serves as the OpenSIPI platform. It takes input info, parses them into scripts to automate S-para extraction, processes results and generates a report.

Inputs:
- input_info: dict, input related information

	input_type: str, input file type. "csv" or "gsheet".

	input_dir: str, directory of input csv files. This key is mandatory if input_type = "csv".

	input_folder: str, folder name of the input csv files, the specified folder contains the required input info for a specific extraction type like PDN, LSIO, HSIO etc. This key is mandatory if input_type = "csv".

	op_run_name: \[optional\], str, the time stamp of the "Run" folder. It should be omitted or assigned empty string by default. Each time an extraction starts, a folder called "Run_(time stamp)" is created automatically. In order to hack into an existing Run folder, set the existing time stamp to this key.

Example:

```python
input_info = {
    "input_dir": r"C:\SIPIProj\Olympus\Sim_Input" + "\\",
    "input_type": "csv",
    "input_folder": "Sigrity_PDN",
    "op_run_name": "",
}

pf = Platform(input_info)
```

Methods:
- drop_dsn_file()

Usage: The platform requests the user to drop a design file to an automatically created directory. The following design file formats are accepted.

BRD: .brd

ODB++: .tgz, .zip, .gz, .z, .tar, .7z

MCM: .mcm

Example:
```python
pf.drop_dsn_file()
```

- read_inputs()

Usage: Read the input info needed for the extraction setup.

Outpus:
input_data: dict

Example:
```python
input_data = pf.read_inputs()
```

- parser(input_data)

Usage: Parse the input data based on the tool in use. This method must not be called before read_inputs().

Inputs:
input_data

Outputs:
sim_exec

Example:
```python
sim_exec = pf.parser(input_data)
```

- run(sim_exec, mntr_info)
- process_snp(result_config_dir)
- report(result_config_dir, report_config_dir)


