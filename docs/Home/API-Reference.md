<!--
SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
SPDX-FileCopyrightText: 2024 Rivos Inc.

SPDX-License-Identifier: Apache-2.0
-->

# API Reference

> [!NOTE]
> This page is generated from source docstrings. Do not edit it by hand.

## `opensipi.constants.CONSTANTS`

This module contains constants commonly used by OpenSIPI.

These constants are the vocabulary the input sheets are written in, so
changing one changes what users must type in their tables.

**Attributes:**

INPUT_FILE_STARTSWITH (list of str): The four recognized sheet name
    patterns, in the fixed order `[sim, special settings, stackup and
    materials, spec type]`. Consumers index this list positionally, so
    the order matters as much as the values. A sheet name is matched
    upper-cased, by prefix for the sim sheets and exactly for the other
    three.
SIM_INPUT_COL_TITLE (list of str): The upper-cased column titles of a sim
    sheet. Also indexed positionally, e.g. index 1 is `"CHECK_BOX"`, the
    column deciding whether a simulation is enabled.
SPEC_TYPE (dict): The built-in spec types, mapping an upper-cased spec type
    name to its `"FREQ"` and `"POST_PROCESS_KEY"` definition. The
    length of `"FREQ"` follows the extraction type it serves:
    `[FREQ_START, FREQ_END]` for the PDN entries, which sweep
    adaptively; `[..., FREQ_STEP]` for the LSIO entries; and
    `[..., FREQ_STEP, FREQ_SOL]` for the HSIO entries, which also need a
    solution frequency. A user-supplied spec type sheet adds to or
    overrides this mapping.
POST_PROCESS_KEY_ORDER_PDN (dict): Post-processing key to its sort rank,
    used to present PDN results in a stable order regardless of the order
    the keys were written in the input.
POST_PROCESS_KEY_ORDER_IO (dict): The same, for the HSIO and LSIO results.

## `opensipi.file_in`

This module processes input and output files.

The entry point is the class `FileIn`, which reads the simulation input
from either a folder of csv files or a Google Sheet workbook and parses it
into the `input_data` dict consumed by the rest of the platform. Four
kinds of sheets are recognized, keyed off `INPUT_FILE_STARTSWITH`:
`Sim*`, `Special_Settings`, `Stackup_Materials`, and `Spec_Type`.

### `FileIn`

Read and parse the simulation input sheets.

The input is read on instantiation, so the parsed result is available on
the instance right away; there is no separate `read()` step.

**Attributes:**

INPUT_TYPE (str): Upper-cased input file type, `"CSV"` or
    `"GSHEET"`.
INPUT_FILE_STARTSWITH (list of str): The four recognized sheet name
    patterns, in the order `[sim, special settings, stackup and
    materials, spec type]`. Normally `INPUT_FILE_STARTSWITH` from
    `opensipi.constants.CONSTANTS`.
INPUT_DATA (dict): The parsed input, with the keys `"sim_input"`,
    `"all_input"`, `"stackup_info"`, `"settings"`, and
    `"spectype_info"`. See `_read_input_csv` for what each
    one holds.

**Constructor**

```python
def FileIn(info)
```

Read and parse the input sheets described by `info`.

**Args:**

- **info** (*dict*) — Input related information.

  * `input_type` (str): `"CSV"` or `"GSHEET"`, upper case.
  * `input_file_startswith` (list of str): The four recognized
  sheet name patterns.
  * `input_dir` (str): Slash-ending directory holding the input
  csv files. Only used when `input_type` is `"CSV"`.
  * `account_key` (str): Path to the Google account key file.
  Only used when `input_type` is `"GSHEET"`.
  * `account_type` (str): Google account type, e.g.
  `"service"`. Only used when `input_type` is
  `"GSHEET"`.
  * `sheet_url` (str): URL of the input Google Sheet. Only used
  when `input_type` is `"GSHEET"`.

**Raises:**

NoneUniqueKeyDefined: If a sim sheet defines a duplicated
    `Unique_Key`.
MaterialsMustBeDefinedBeforeStackup: If the `Materials` section
    is placed at or below the `Stackup` section.

**Note:**

An unrecognized `input_type` is not an error. Every entry of
`INPUT_DATA` is left as an empty dict instead.

## `opensipi.gdrive_io`

This module handles Google Drive services.

`GdriveIO` authorizes, `Gdrive` wraps the raw Drive API calls, and
`XtractResults2Drive` puts them to work by mirroring a run's output folder
into Drive under `project / sim type / run`.

Creating anything goes through a query-then-create step, so re-uploading a
run reuses the folders and files already there rather than producing
duplicates. A name that turns out to be ambiguous is treated as an error rather
than guessed at, since picking the wrong one would silently scatter a run's
results.

**References:**

1. How to use Google Drive API in Python
https://www.thepythoncode.com/article/using-google-drive--api-in-python

### `list_files`

```python
def list_files(items)
```

Print items returned by the Google Drive API as a table.

A debugging aid. The table is printed rather than returned.

**Args:**

- **items** (*list of dict*) — File resources as returned by the Drive API.
  Each is read for `id`, `name`, `parents`, `size`,
  `mimeType`, and `modifiedTime`.

**Note:**

The two fallbacks for a missing field catch the wrong exception types.
A resource without `parents` or `size` raises `KeyError`, which
neither the `NameError` nor the `TypeError` handler intercepts, so
the `"N/A"` placeholders are only reached when the field is present
but null.

### `get_size_format`

```python
def get_size_format(b, factor=1024, suffix='B')
```

Scale bytes to its proper byte format.

e.g:
    1253656 => '1.20MB'
    1253656678 => '1.17GB'

**Args:**

- **b** (*int or float*) — The size to scale.
- **factor** (*int, optional*) — Step between units. Defaults to `1024`. Pass
  `1000` for decimal units.
- **suffix** (*str, optional*) — Unit suffix. Defaults to `"B"`.

**Returns:**

str: The size with two decimals and a unit prefix, the prefix rising
until the value drops below `factor`, capped at `Y`.

### `GdriveIO`

a class to initialize gdrive service

Holds the credentials and the scopes, and builds an authorized Drive
service from them. Two authorization paths are offered, one interactive and
one unattended.

**Constructor**

```python
def GdriveIO(info)
```

Record the credentials and the scopes to authorize with.

Nothing is authorized here. Call one of the `gdrive_auth_*` methods
to obtain a service.

**Args:**

- **info** (*dict*) — Google Drive access information.

  * `account_key` (str): Path to the credentials file, being a
  service account key or an OAuth client secret depending on
  which authorization path is used.
  * `config_dir` (str): Directory the cached end user token is
  kept in.

**Attributes:**

SCOPES (list of str): The Drive permissions requested. Narrowing
    this list invalidates a cached end user token, so
    `gdrive_token.pickle` must then be deleted by hand.

#### `gdrive_auth_end_user`

```python
def gdrive_auth_end_user(self)
```

Authorize as the end user and return a Drive service.

A token cached from a previous run is reused, and refreshed in place
when it has expired. Only when no usable token exists is the browser
consent flow started, so this is interactive on first use and silent
afterwards. The token is written back to `config_dir` either way.

**Returns:**

googleapiclient.discovery.Resource: An authorized Drive v3 service.

#### `gdrive_auth_service_account`

```python
def gdrive_auth_service_account(self)
```

Authorize as a service account and return a Drive service.

Needs no consent and no cached token, so this is the path used for
unattended runs. The target Drive folders must be shared with the
service account's address.

**Returns:**

googleapiclient.discovery.Resource: An authorized Drive v3 service.

### `Gdrive`

a class of gdrive

Thin wrappers over the Drive API for the operations this application needs:
searching, creating folders and sheets, and uploading and downloading
files.

**Constructor**

```python
def Gdrive(info)
```

Authorize and prepare the download settings.

**Args:**

- **info** (*dict*) — Passed through to `GdriveIO`, plus a `log`
  key holding the run logger.

**Attributes:**

URL (str): Base URL used for downloads, which go through a plain
    HTTP session rather than the API client.
CHUNK_SIZE (int): Download chunk size in bytes.

**Note:**

Authorization is hardwired to the service account path. The end
user path is left commented out just above it.

#### `search`

```python
def search(self, query)
```

Search inside a folder and return queried info.

Paging is followed to the end, so the result is complete rather than
capped at one page.

**Args:**

- **query** (*str*) — A Drive API query string.

**Returns:**

list of tuple: One `(id, name, mimeType)` per match. Empty if
nothing matched.

#### `q_folder_id`

```python
def q_folder_id(self, name, parent_folder_id)
```

Query folder id if exists.

**Args:**

- **name** (*str*) — Folder name to look for.
- **parent_folder_id** (*str*) — ID of the folder to look inside.

**Returns:**

str: The folder ID, or an empty string if there is no such folder.
The caller distinguishes the two to decide whether to create it.

**Raises:**

NoneUniqueFolderInDrive: If more than one folder of that name
    exists in that parent, since there would be no safe way to pick
    one.

#### `q_file_id`

```python
def q_file_id(self, name, parent_folder_id)
```

Query file id if exists.

**Args:**

- **name** (*str*) — File name to look for, with extension.
- **parent_folder_id** (*str*) — ID of the folder to look inside.

**Returns:**

str: The file ID, or an empty string if there is no such file.

**Raises:**

NonUniqueFileInDrive: If more than one file of that name exists in
    that parent.

#### `create_folder`

```python
def create_folder(self, folder_name, parent_folder_id)
```

Create a folder and return its id.

No check is made for an existing folder of the same name. Use
`q_folder_id` first if that matters.

**Args:**

- **folder_name** (*str*) — Name of the folder to create.
- **parent_folder_id** (*str*) — ID of the folder to create it in.

**Returns:**

str: ID of the new folder.

#### `create_gsheet`

```python
def create_gsheet(self, file_name, folder_id)
```

Create a gsheet and return its id.

Creates a native Google Sheet, not an uploaded spreadsheet file.

**Args:**

- **file_name** (*str*) — Title of the sheet to create.
- **folder_id** (*str*) — ID of the folder to create it in.

**Returns:**

str: ID of the new sheet.

#### `upload_file`

```python
def upload_file(self, file_dir, folder_id)
```

Upload a file to a folder.

The upload is resumable, so a large result file survives a transient
interruption. The name in Drive is taken from the local file name.

**Args:**

- **file_dir** (*str*) — Full path of the local file.
- **folder_id** (*str*) — ID of the folder to upload into.

**Returns:**

str: ID of the uploaded file.

#### `download_file`

```python
def download_file(self, query, dir)
```

Download a file from a drive folder.

The first match wins if the query is ambiguous. The file is made
readable by anyone with the link before it is fetched, since the
download goes through a plain HTTP session that carries no credentials.

**Args:**

- **query** (*str*) — A Drive API query string identifying the file.
- **dir** (*str*) — Full path to write the downloaded file to.

**Note:**

The sharing permission is granted permanently and is not revoked
afterwards.

### `XtractResults2Drive`

a class wrapper of GdriveIO

Mirrors one run's output into Google Drive, under a
`project / sim type / run` folder tree that is created on demand.

**Constructor**

```python
def XtractResults2Drive(info)
```

Authorize and ensure this run's folder tree exists in Drive.

The folder tree is created here, so an instance is ready to upload into
as soon as it is built.

**Args:**

- **info** (*dict*) — Upload related information.

  * `root_drive_id` (str): ID of the Drive folder the project
  tree is created under.
  * `proj_name` (str): Project name, the first tree level.
  * `sim_type_name` (str): Simulation type, the second level.
  * `run_time` (str): Run time stamp, part of the run folder
  name.
  * `usr_id` (str): User ID, also part of the run folder name,
  so that runs from different users stay distinct.
  * `log` (logging.Logger): The run logger.
  * `account_key` and `config_dir`: Passed through to
  `Gdrive`.

#### `upload_folder`

```python
def upload_folder(self, root)
```

Upload all files in a local folder.

**Args:**

- **root** (*str*) — Local folder to walk, sub-directories included.

**Returns:**

tuple: A 2-tuple `(file_id_book, uni_file_type)`, as described in
`upload_dir_list`.

#### `upload_folder_tgt_ext`

```python
def upload_folder_tgt_ext(self, root, tgt)
```

Upload all files with a specified extension.

**Args:**

- **root** (*str*) — Local folder to walk, sub-directories included.
- **tgt** (*str*) — Regular expression matched against each file name. It is
  searched for, not anchored, so a bare extension works.

**Returns:**

tuple: A 2-tuple `(file_id_book, uni_file_type)`, as described in
`upload_dir_list`.

#### `upload_dir_list`

```python
def upload_dir_list(self, root, dir_list)
```

Upload all files in the dir_list.

Each file's path relative to `root` is recreated as folders under the
run folder, so the Drive copy mirrors the local layout. Files are
grouped by simulation key, taken from the file name up to the run time
stamp, which is what lets the summary sheet put one simulation per row.

**Args:**

- **root** (*str*) — Local folder the paths are relative to.
- **dir_list** (*list of str*) — Full paths of the files to upload.

**Returns:**

tuple: A 2-tuple `(file_id_book, uni_file_type)`, where
`file_id_book` maps a simulation key to a list of
`[file_name, file_id, folder_name]` entries, and
`uni_file_type` lists the distinct containing folder names in
first-seen order.

**Note:**

Only one level of nesting is recreated. The loop reassigns its
remaining path to a list rather than to a string, so its condition
can never hold a second time and a file nested two or more levels
deep is uploaded one level down, under the folder name of the
level above it. A file sitting directly in `root` raises
`NameError`, or is silently attributed to the previous file's
folder if one was already seen.

#### `upload_report`

```python
def upload_report(self, dir)
```

Upload the pdf report to the drive.

The report goes straight into the run folder rather than into a
sub-folder.

**Args:**

- **dir** (*str*) — Full path of the local report file.

**Returns:**

dict: `{"report": file_id}`, shaped this way so the summary sheet
can look the report up by name.

#### `download_file`

```python
def download_file(self, name, parent_folder_id, dl_file_dir)
```

Download a file from G drive by name.

**Args:**

- **name** (*str*) — File name to look for, with extension.
- **parent_folder_id** (*str*) — ID of the folder to look inside.
- **dl_file_dir** (*str*) — Full path to write the file to.

#### `get_summary_sheet_id`

```python
def get_summary_sheet_id(self, sheet_title, parent_id)
```

Create a gSheet if it doesn't exist.

The sheet lives in a project folder of its own, outside the per-run
tree, so that successive runs of a project accumulate into one summary.

**Args:**

- **sheet_title** (*str*) — Title of the summary sheet.
- **parent_id** (*str*) — ID of the folder the project folder is created
  under.

**Returns:**

str: ID of the existing or newly created sheet.

## `opensipi.gsheet_io`

This module handles gSheet services.

`GsheetIO` opens a workbook, and is used both to read the simulation
input and to write the result summaries. `TS2GSheet` and `DCR2GSheet`
write those summaries: one row per simulation key, one column per result file
type, with the cells linking back to the files uploaded to Google Drive.

Writes go through the Google Sheets API, which is rate limited, so the
per-cell updates are deliberately paced.

### `GsheetIO`

gSheet client initialization and data retrieval using URL

**Constructor**

```python
def GsheetIO(info)
```

Resolve the workbook URL and the credentials to open it with.

Nothing is opened here. Call one of the `get_sheet_*` methods to
authorize and fetch the workbook.

**Args:**

- **info** (*dict*) — Google Sheet access information.

  * `account_key` (str): Path to the Google credentials file.
  * `sheet_url` (str): URL of the workbook. Takes precedence
  over `sheet_id`.
  * `sheet_id` (str): Workbook ID, used to build the URL when
  `sheet_url` is absent.

**Note:**

Supplying neither `sheet_url` nor `sheet_id` is not reported
here. `self.sheet_url` is then left unset and the failure
surfaces as an `AttributeError` when the workbook is opened.

#### `get_sheet_service_account`

```python
def get_sheet_service_account(self)
```

Open the workbook using a service account.

Suited to unattended runs, since a service account needs no
interactive consent. The workbook must be shared with the service
account's address for this to succeed.

**Returns:**

gspread.Spreadsheet: The opened workbook.

#### `get_sheet_end_user`

```python
def get_sheet_end_user(self)
```

Open the workbook using end user authorization.

This may open a browser for consent on first use, so it suits
interactive runs rather than unattended ones.

**Returns:**

gspread.Spreadsheet: The opened workbook.

### `TS2GSheet`

Output a summary of the simulation results to gSheet.

Builds a table of one row per simulation key and one column per result file
type, where every cell is a hyperlink to the corresponding file in Google
Drive.

**Attributes:**

GDRIVE_VIEW_URL (str): Prefix turning a Google Drive file ID into a
    viewable link.
ALPHABET (str): Column letters, indexed to convert a zero-based column
    number into its A1-notation letter. This caps the sheet at 26
    columns.

**Constructor**

```python
def TS2GSheet(info)
```

Open the summary workbook and record what is to be written to it.

**Args:**

- **info** (*dict*) — Export related information.

  * `account_key`, `sheet_url` or `sheet_id`: Passed
  through to `GsheetIO`.
  * `file_id_book` (dict): Simulation key to the list of its
  result files, each entry being
  `[file_name, gdrive_file_id, file_type]`.
  * `uni_file_type` (list of str): The distinct result file
  types, in the order their columns are laid out.
  * `report_id_book` (dict): Holds the `"report"` key, the
  Google Drive ID of the run report.
  * `run_time` (str): Run time stamp, used to label the report.
  * `usr_id` (str): User ID, shown in the header.
  * `log` (logging.Logger): The run logger.

#### `export_results`

```python
def export_results(self)
```

Write the S-parameter result summary to the workbook.

Renames the default first sheet to `Summary`, ensures a `Results`
sheet exists, and fills it in. Repeated runs append to the same
`Results` sheet rather than replacing it, so a simulation key already
present is updated in place.

### `DCR2GSheet`

Export DCR results to GSheet.

The DCR counterpart of `TS2GSheet`. DCR yields a single resistance
number per simulation rather than a set of files, so the summary is one
value column and the cells hold values instead of links.

**Attributes:**

ALPHABET (str): Column letters, indexed to convert a zero-based column
    number into its A1-notation letter.

**Constructor**

```python
def DCR2GSheet(info)
```

Open the summary workbook and record the DCR results to write.

**Args:**

- **info** (*dict*) — Export related information.

  * `account_key`, `sheet_url` or `sheet_id`: Passed
  through to `GsheetIO`.
  * `dcr_dict` (dict): Simulation key to its extracted
  resistance in mOhm.
  * `run_time` (str): Run time stamp, used to label the run.
  * `usr_id` (str): User ID, shown in the header.
  * `log` (logging.Logger): The run logger.

#### `export_results`

```python
def export_results(self)
```

Write the DCR result summary to the workbook.

Renames the default first sheet to `Summary`, ensures a `Results`
sheet exists, and fills it in. Repeated runs append to the same
`Results` sheet, so a simulation key already present is updated in
place.

## `opensipi.integrated_flows`

This module contains all top-level integrated flows.

These are the functions a user calls directly. Each one drives a whole
extraction, from reading the input tables through to the report, by stepping a
`Platform` instance through its methods in the right order. Use `Platform`
directly only when a flow needs to deviate from that sequence.

### `sim2report`

```python
def sim2report(input_info, mntr_info)
```

Run a whole extraction from csv input to a local report.

This function takes csv input info to the Platform, parses them into
scripts to automate S-para extraction, processes results and generates
a report.

The call blocks and prompts twice at the terminal: once to have the design
file dropped in place, and, when `op_pause_after_model_check` is set,
once more before the solver starts.

**Args:**

- **input_info** (*dict*) — Input related information.

  * `input_type` (str): Must be `"csv"`.
  * `input_dir` (str): Directory holding the input csv folders.
  * `input_folder` (str): Name of the folder inside `input_dir`
  holding the csv sheets for this extraction.
  * `op_run_name` (str, optional): Time stamp of an existing
  `Run_...` folder to resume into. Omit or leave empty to start a
  new run.

- **mntr_info** (*dict*) — Monitor related information.

  * `email` (str): Notification address. Not enabled yet.
  * `op_pause_after_model_check` (int, optional): `1` to pause
  after model check so the models can be inspected or hand-edited,
  `0` to run straight through. Defaults to `0`.

**Returns:**

str: Full path to the generated pdf report.

### `sim2report_gsuites`

```python
def sim2report_gsuites(input_info, mntr_info)
```

Run a whole extraction from Google Sheet input, then upload the results.

This function takes gSheet input info to the Platform, parses them into
scripts to automate S-para extraction, processes results and generates
a report.

The Google Suites counterpart of `sim2report`. It runs the same
extraction and reporting steps, then uploads the outcome to Google Drive.

**Args:**

- **input_info** (*dict*) — Input related information.

  * `input_type` (str): Must be `"gsheet"`.
  * `input_url` (str): URL of the Google Sheet holding the input
  tabs.
  * `proj_dir` (str): The project directory. Required here, since
  there is no `input_dir` to derive it from.
  * `output_type` (str, optional): `"gdrive"` to upload the
  results. Defaults to `"local"`.
  * `op_run_name` (str, optional): As in `sim2report`.

- **mntr_info** (*dict*) — Monitor related information, as in
  `sim2report`.

**Returns:**

None: The report path is not returned. The report is written to the run
folder and uploaded to Google Drive.

**Note:**

The Google credentials and target Drive IDs are not passed in here.
They are read from `config_gsuites.yaml` under the `opensipi_config`
folder.

## `opensipi.sigrity_exec`

This module contains all Classes used to execute Cadence Sigrity Tools.

An "executor" owns one extraction from end to end: it builds the tcl
through a matching "modeler" from `opensipi.sigrity_tools`, launches the
solver, watches it, checks the result, and files the output away. The executor
decides what happens and when; the modeler decides what the tcl says.

The four classes form an inheritance chain rather than four independent
implementations, since the extraction types differ only in places.
`PowersiPdnExec` carries the shared machinery, and each subclass overrides the
handful of methods that differ, being which modeler to build, how strict the
port format check is, and where the result files land.

Progress is tracked through `.done` marker files rather than through the
solver's exit status, because the solver is launched detached and runs in its
own process. That is also why the monitor watches the process list to notice a
solver that died, and why an interrupted run can be resumed: whatever already
has a marker is simply not redone.

### `PowersiPdnExec`

This class parses input info as executable tcl scripts, launches
simulations, conducts formality checks and etc. This class is only
for PDN extractions using PowerSI.

Also the base class of the other three executors, holding everything they
share.

**Attributes:**

report_type (str): Which report template the results feed, here
    `"PDN"`. Overridden by the subclasses.
spd_proj (SpdModeler): The modeler that writes the tcl.
run_info (dict): The three run descriptors, being `run_info_parent`,
    `run_info_check`, and `run_info_sim`, one per stage of a run.
result_sub_dirs (dict): Result sub-folders to post-process, by name.

**Constructor**

```python
def PowersiPdnExec(info)
```

Set up the executor and generate the tcl scripts.

The modeler is built here and writes out its tcl immediately, so by the
time this returns the scripts are on disk and the run descriptors point
at them.

**Args:**

- **info** (*dict*) — The `model_info` dict assembled by
  `Platform._Platform__sigrity_parser`, holding the parsed
  input, the run folder paths, the tool config directory, and the
  run logger.

#### `run`

```python
def run(self, mntr_info)
```

Run sigrity simulations.

The whole extraction, in order: build the parent model, check the input
against the real design, build and check the per-simulation models,
optionally pause, run the solver, then collect the results and write
the config files the report stage reads.

**Args:**

- **mntr_info** (*dict*) — Monitor related information.

  * `email` (str): Notification address. An empty string
  disables the notifications.
  * `op_pause_after_model_check` (int, optional): `1` to
  pause after model check. Absent or `0` runs straight
  through.

**Returns:**

tuple: A 2-tuple `(result_config_dir, report_config_dir)`, the
full paths of the two yaml files handing state to the report stage.

**Raises:**

IllegalInputFormat: If the input sheets hold a format error.
NoExistingNames: If a net or component named in the input is absent
    from the design.
UnequalPortCounts: If the solver built a different number of ports
    than the input declared.

### `PowersiIOExec`

This class parses input info as executable tcl scripts, launches
simulations, conducts formality checks and etc. This class is only
for LSIO extractions using PowerSI.

Differs from the PDN base only in the report template it feeds, the modeler
it pairs with, and a stricter port format check.

**Constructor**

```python
def PowersiIOExec(info)
```

Set up the executor and switch the report type to IO.

**Args:**

- **info** (*dict*) — The `model_info` dict, as in
  `PowersiPdnExec.__init__`.

### `ClarityExec`

This class parses input info as executable tcl scripts, launches
simulations, conducts formality checks and etc. This class is only
for HSIO extractions using PowerSI.

Clarity is a 3D FEM solver, so it names its output differently from
PowerSI and produces no DC-fitted variant. Only the modeler and the result
handling differ from the LSIO parent.

**Note:**

The class docstring says PowerSI, but HSIO is run by Clarity.

**Constructor**

```python
def ClarityExec(info)
```

Set up the executor and narrow the results to the S-parameters.

**Args:**

- **info** (*dict*) — The `model_info` dict, as in
  `PowersiPdnExec.__init__`.

### `PowerdcExec`

This class parses input info as executable tcl scripts, launches
simulations. This class is only for DCR extractions using PowerDC.

DCR differs more than the other types do. It yields one resistance per
simulation rather than a touchstone file, so there is no S-parameter
post-processing, no port count check, and the report is a csv.

**Attributes:**

RESIS_CSV (str): Name of the raw resistance csv PowerDC writes.

**Constructor**

```python
def PowerdcExec(info)
```

Set up the executor for a csv result rather than touchstone files.

**Args:**

- **info** (*dict*) — The `model_info` dict, as in
  `PowersiPdnExec.__init__`.

## `opensipi.sigrity_tools`

This module contains all Classes used to parse for Cadence Sigrity Tools.

A "modeler" turns the parsed input into the Tcl the solver actually runs.
Its counterpart in `opensipi.sigrity_exec` decides when to run that Tcl; this
module decides what it says. Between them sits the bulk of the SI/PI domain
knowledge: how a port definition in a spreadsheet cell becomes a set of solver
commands, how nets are enabled and grouped, how the board is cut down, and how
the stackup and materials are applied.

Tcl is produced by string substitution into the `TCL_*` class constants,
each a template with upper-case placeholders. That is why the placeholder names
must not collide with real content, and why substitution order matters in a few
places where one template is embedded in another.

The four modelers form an inheritance chain mirroring the executors.
`SpdModeler` builds the parent model, shared by all extraction types.
`PowersiPdnModeler` adds the per-simulation Tcl and the port machinery, and
the remaining three override the parts that differ, mostly around how ports are
defined and how the frequency sweep is set up.

Every generation step skips a file that already exists, which is what lets
a run be resumed, and also means a hand-edited Tcl survives a re-run.

### `SpdModeler`

This class converts a design file to a spd file for later use.

Produces the "parent" model, being the design with the stackup, materials,
surface roughness, solder, and global cuts applied but no simulation set up
yet. Every per-simulation model is derived from it, so this work is done
once per run.

The Tcl is emitted by substituting into the `TCL_*` class constants.

**Attributes:**

CONNECTIVITY (dict): Per simulation, which ports pair with which for
    each kind of post-processing. Worked out once here and carried
    through to the post-processing stage.
SOLVER (str): Executable name of the solver, `"powersi"` here.
    Overridden by the Clarity and PowerDC subclasses.
EXPORT_PORT (str): Tcl boolean deciding whether the port details are
    exported for checking. False for DCR, which defines no ports.
solder_refdes (dict): Original RefDes to the grown-solder RefDes that
    replaces it in the model.
SHAPE_CUT_TYPE (str): `"CONFORMAL"` or anything else for a plain
    rectangular cut. Read from the Sigrity config, defaulting to
    conformal.

**Constructor**

```python
def SpdModeler(info)
```

Prepare the model inputs and write the parent model Tcl.

Does real work rather than just storing arguments: the materials,
stackup, and BOM files are written out and the parent model Tcl is
generated, so everything needed to build the parent model is on disk
when this returns. Each file is skipped if it already exists.

**Args:**

- **info** (*dict*) — The `model_info` dict assembled by
  `Platform._Platform__sigrity_parser`, holding the parsed
  input sheets, the run folder paths, the tool config directory,
  and the run logger.

**Raises:**

UndefinedSurfaceRoughnessModelType: If a surface roughness model
    names an unknown type.
WrongGrowSolderFormat: If a grow solder setting is not three
    comma-separated fields.
FileNotFoundError: If `config_sigrity.yaml` is missing from the
    tool config directory.

### `PowersiPdnModeler`

A powersi class for PDN extraction.

Adds the per-simulation Tcl to the parent model machinery: enabling and
grouping nets, cutting the board, defining ports, and setting the frequency
sweep. Also the base of the other three modelers, so the port and net
helpers here are shared.

Three Tcl files are produced. `check.tcl` builds each simulation's model
without running it, `run.tcl` runs them, and one `key_*.tcl` per
simulation carries that simulation's own setup. Splitting them is what lets
the models be inspected between the check and the run. A timestamped copy
of the two main scripts is kept alongside, as a record of what a given run
actually executed.

**Constructor**

```python
def PowersiPdnModeler(info)
```

Set up the per-simulation Tcl paths and the keys still to run.

**Args:**

- **info** (*dict*) — The `model_info` dict, as in
  `SpdModeler.__init__`, additionally read for
  `sim_dir`, `key2check`, `key2sim`, `run_key_dir`, and
  `model_check_dir`.

#### `mk_tcl`

```python
def mk_tcl(self)
```

Make all needed tcls.

Writes the check script, the run script, and one script per simulation.
Called by the executor right after construction.

### `PowersiIOModeler`

Extract LSIO S-para using PowerSI.

The ports must be defined using refdes + pins.

Signal extraction differs from PDN in a way that reshapes the whole script.
Each row of the sheet is its own net-and-port context, since a signal port
only makes sense with its own net enabled, so the ports are defined row by
row with the nets toggled around each, and only afterwards are all the nets
enabled together for the actual solve. PDN can enable everything up front
because a rail is one net group throughout.

The positive nets are moved to the `NULL` group rather than to
`PowerNets`, which is how the solver is told to treat them as signals.

**Constructor**

```python
def PowersiIOModeler(info)
```

Set up the modeler, unchanged from the PDN parent.

**Args:**

- **info** (*dict*) — The `model_info` dict, as in
  `SpdModeler.__init__`.

### `ClarityModeler`

Run FEM simulations using Clarity.

Only component ports are supported for both primary and sense ports.

Clarity is a 3D field solver, so the model needs things the 2D flows do
not: coaxial FEM ports with explicit solder ball geometry, multi-terminal
circuits standing in for the components on the outer layers, and a solution
frequency alongside the sweep. It is also far more expensive to run, which
is why the compute resources are configured per simulation.

**Attributes:**

BOT_LAYER_INDEX (int): Layer index of the bottom conductor.
TOP_LAYER_INDEX (int): Layer index of the top conductor, derived from
    the stackup length.
DF_SOLDER (list of float): Default solder height in mm and the solder
    diameter to pad size ratio, used where a component has no explicit
    `FEMPortSolder` entry.
DF_ANTIPAD (float): Default FEM port antipad ratio.
SOLVER (str): `"clarity3dlayout"`, overriding the PowerSI default.

**Constructor**

```python
def ClarityModeler(info)
```

Load the Clarity settings and the extra Tcl templates.

**Args:**

- **info** (*dict*) — The `model_info` dict, as in
  `SpdModeler.__init__`.

**Raises:**

KeyError: If `config_sigrity.yaml` lacks `CLARITY_OPTION`,
    `CORE_NUM`, `DEFAULT_SOLDER`, or `DEFAULT_ANTIPAD`.
FileNotFoundError: If either extra Tcl template is missing from the
    package template folder.

### `PowerdcModeler`

A powerdc class for DCR extraction.

**Assumptions:**

1. All definitions in the same workbook will be simulated together,
i.e. each workbook is a sim key.
2. For each rail key, there can be only 1 sink defined, but multiple
VRMs are allowed.
3. Sinks can be defined using either one refdes or positive/negative
refdes + pins.
4. VRMs can only be defined using positive/negative refdes + pins.
5. Two sink pin group types are supported and are specified using
spec types:
    Rl2l: lumped to lumped (PWR to GND)
    Rm2l: multiple to lumped (PWR to GND)

**Constructor**

```python
def PowerdcModeler(info)
```

Load the PowerDC settings and the per-sheet simulation grouping.

**Args:**

- **info** (*dict*) — The `model_info` dict, as in
  `SpdModeler.__init__`, additionally read for
  `dcr_dict`, the sheet-to-keys grouping.

**Raises:**

KeyError: If `config_sigrity.yaml` lacks `PDC_OPTION`.

## `opensipi.sipi_infra`

This module serves as the platform of the OpenSIPI application.

`Platform` is the spine of the application. It owns the run folder tree,
reads the input, picks the solver executor matching the extraction type, drives
the run, post-processes the results, and builds the report. The integrated
flows in `opensipi.integrated_flows` are thin sequences of its methods.

The methods are order-dependent rather than independent. Construction reads
the input and creates the folders, `drop_dsn_file` settles which design is
being simulated, `parser` chooses the executor, and only then can `run` and
`report` do anything. Between stages the state is handed over through yaml
config files written into the run folder, which is what lets a later stage be
re-run on its own against an existing `Run_...` folder.

### `Platform`

platform class for the opensipi applications.

**Attributes:**

INPUT_TYPE (str): Upper-cased input type, `"CSV"` or `"GSHEET"`.
RUN_NAME (str): Name of this run, being the extraction type and a time
    stamp, or the caller-supplied name when resuming.
input_data (dict): The parsed input sheets. See
    `opensipi.file_in.FileIn`.
lg (logging.Logger): The run logger, writing to the run's `Log`
    folder.
DSN_NAME (str): File name of the design being simulated. Empty until
    `drop_dsn_file` runs.
LOC_DSN_RAW (str): File name of the local design copy. Empty until
    `drop_dsn_file` runs.

**Constructor**

```python
def Platform(info)
```

Build the run folder tree, read the input, and start logging.

A fair amount happens here. The folder tree is created, the input
sheets are read and parsed, and a logger is opened, so an instance is
never in a half-built state. Logging can only start once the log
folder exists, so anything going wrong before that point is reported
by print rather than to the log file.

**Args:**

- **info** (*dict*) — Input related information.

  * `input_type` (str): `"csv"` or `"gsheet"`, matched
  case-insensitively.
  * `input_dir` (str): Directory holding the input csv folders.
  Required when `input_type` is `"csv"`.
  * `input_folder` (str): Name of the folder inside
  `input_dir` holding this extraction's sheets. Required when
  `input_type` is `"csv"`.
  * `input_url` (str): URL of the input Google Sheet. Required
  when `input_type` is `"gsheet"`.
  * `proj_dir` (str): The project directory. Optional when
  `input_dir` is given, since it is then derived from it.
  * `output_type` (str, optional): `"local"` or `"gdrive"`.
  Defaults to `"local"`.
  * `op_run_name` (str, optional): Time stamp of an existing
  `Run_...` folder to resume into. Omit or leave empty to
  start a new run.

**Raises:**

NoProjDirDefined: If neither `proj_dir` nor `input_dir` is
    given.
NoneUniqueKeyDefined: If a sim sheet defines a duplicated
    `Unique_Key`.
MaterialsMustBeDefinedBeforeStackup: If the `Materials` section
    is placed at or below the `Stackup` section.

#### `drop_dsn_file`

```python
def drop_dsn_file(self, xtract_tool=None)
```

Ask the user to drop the design file in a specific dir.

Blocks at the terminal until the user confirms the file is in place,
then looks for design files of an accepted type. Exactly one is used;
if several are found the user is asked to pick. A local working copy is
made at the end, so the original is never touched by the solver.

**Args:**

- **xtract_tool** (*str, optional*) — The extraction tool in use. `.spd`
  is only accepted for `"Sigrity"`, since an spd is already a
  Sigrity simulation model rather than a raw design.

**Raises:**

NoDsnFound: If the design directory holds no file of an accepted
    type.
AttributeError: If `xtract_tool` is left at `None`.

**Note:**

The confirmation loop compares against `("Y" or "YES")`, which
evaluates to `"Y"`, so a typed `yes` is not accepted and the
prompt repeats.

#### `parser`

```python
def parser(self, input_data)
```

Parse the input data based on the tool in use.

Works out which simulation keys still need doing, by looking for the
`.done` markers left by earlier runs, and builds the solver executor
matching the extraction type. Must not be called before the design file
has been settled by `drop_dsn_file`.

**Args:**

- **input_data** (*dict*) — The parsed input, normally `self.input_data`.
  Modified in place, gaining the `"dcr_dict"`, `"key2check"`,
  and `"key2sim"` keys.

**Returns:**

object: The solver executor, being one of `PowersiPdnExec`,
`ClarityExec`, `PowersiIOExec`, or `PowerdcExec`.

**Raises:**

UnboundLocalError: If `ExtractionTool` is not `Sigrity`, or if
    `ExtractionType` is not one of the four supported values.

#### `run`

```python
def run(self, sim_exec, mntr_info)
```

Run sims and return the result info.

Delegates to the executor, which generates the scripts, builds and
checks the models, runs the solver, and collects the results. This is
the long-running step of a flow.

**Args:**

- **sim_exec** (*object*) — The executor returned by `parser`.
- **mntr_info** (*dict*) — Monitor related information.

  * `email` (str): Notification address. Not enabled yet.
  * `op_pause_after_model_check` (int, optional): `1` to
  pause after model check, `0` to run straight through.

**Returns:**

tuple: A 2-tuple `(result_config_dir, report_config_dir)`, the
full paths of the two yaml files handing state to the report stage.

#### `process_snp`

```python
def process_snp(self, result_config_dir)
```

Post-process results and generate plots.

Every touchstone file named by the result config is processed according
to its simulation's spec type, writing the figures into the run's
`Plot` folder.

**Args:**

- **result_config_dir** (*str*) — Full path to the result configuration
  file written by `run`.

**Returns:**

dict: Result sub-folder name to a dict of simulation key to that
simulation's post-processing output. See
`opensipi.touchstone.TouchStone.auto_process`.

#### `report`

```python
def report(self, result_config_dir, report_config_dir)
```

Generate a report out of the processed results.

Post-processes the results, then fills the pdf template matching the
report type recorded in the report config.

**Args:**

- **result_config_dir** (*str*) — Full path to the result configuration
  file.
- **report_config_dir** (*str*) — Full path to the report configuration
  file.

**Returns:**

str: Full path of the pdf report written.

**Note:**

A `DCR` report type produces no report. Both branches for it are
still placeholders, so the path is logged and returned without a
file having been written.

#### `report_html`

```python
def report_html(self, result_config_dir, report_config_dir)
```

Generate a HTML report out of the processed results.

The html alternative to `report`. It renders a jinja2 template
into html and then converts that to pdf, so both formats end up in the
run's `Report` folder. Requires `wkhtmltopdf` to be installed for
the conversion.

**Args:**

- **result_config_dir** (*str*) — Full path to the result configuration
  file.
- **report_config_dir** (*str*) — Full path to the report configuration
  file.

**Returns:**

str: Full path of the pdf report written. The html sits beside it
under the same name.

**Note:**

The integrated flows call `report` rather than this method,
so the html path is only taken when a caller asks for it directly.

#### `export_upload_config`

```python
def export_upload_config(self, report_config_dir)
```

Export the upload config file.

Folds the output settings together with the run details taken from the
report config into one yaml file, so the upload stage needs nothing but
that file.

**Args:**

- **report_config_dir** (*str*) — Full path to the report configuration
  file.

**Returns:**

str: Full path of the upload configuration file written into the
run's `Report` folder.

#### `upload2drive`

```python
def upload2drive(self, upload_config_dir)
```

Upload results and reports to online storage based on the config file.

**Args:**

- **upload_config_dir** (*str*) — Full path to the upload configuration
  file written by `export_upload_config`.

**Note:**

Only `gdrive` is implemented. Any other `output_type`,
including the default `local`, is a no-op.

#### `convert_html_to_pdf_report`

```python
def convert_html_to_pdf_report(self, html_dir, pdf_dir)
```

Convert a html report to a pdf report.

JavaScript and local file access are disabled. Report assets must be
embedded in the HTML, and the converter is invoked without a shell.

**Args:**

- **html_dir** (*str*) — Full path of the html to read.
- **pdf_dir** (*str*) — Full path of the pdf to write.

**Raises:**

OSError: If the `wkhtmltopdf` binary is not installed.
subprocess.CalledProcessError: If conversion fails.

## `opensipi.templates.temp_report`

Created on Nov. 3, 2022

This is a template to create a pdf for PDN report.

The module now holds a template per report type. Each one is a pdf_reports
document skeleton: page style, running header and footer, and three sections,
being the summary, the result tables, and the figures. `Platform` fills them
in at report time by appending rows to the section 1 tables and figure blocks
to section 2, so the templates supply the layout and the headings while the run
supplies the data.

The section 1 blocks are addressed positionally, by the rank a
post-processing key is given in `POST_PROCESS_KEY_ORDER_PDN` or
`POST_PROCESS_KEY_ORDER_IO`. Reordering the blocks, or adding one out of
order, silently sends results to the wrong table.

**Attributes:**

pdn_report (dict): Template for a PDN report. Section 1 holds two table
    blocks, matching the PDN keys `ZOPEN` and `ZSHORT`.
io_report (dict): Template for an HSIO or LSIO report. Section 1 holds six
    table blocks, matching the IO keys `IL`, `RL`, `TDR`, `IL_MM`,
    `RL_MM`, and `TDR_MM` in that rank order.

**Note:**

The headings of the two mixed-mode blocks of `io_report` do not match the
keys that index them. Block 3, filled from `IL_MM`, is headed
`"RL@f0 (dB)"`, and block 4, filled from `RL_MM`, is headed
`"IL@f0 (dB)"`. Only the headings are affected; the rows still land in
distinct blocks.

## `opensipi.touchstone`

Created on Nov. 1, 2022

This module handles one touchstone file.

One `TouchStone` instance wraps one snp file and turns it into the plots
and the extracted figures of merit a report needs. What gets produced is driven
by the `POST_PROCESS_KEY` list of the spec type, so the same class serves PDN
impedance work and IO loss work.

Two port-numbering conventions meet here. The connectivity lists coming
from the input are one-based, matching how ports are numbered in the sheets and
in the touchstone file, while scikit-rf indexes from zero, so the conversion
happens at each point of use.

**Note:**

The `__main__` block at the bottom is a stale demo. Its `info` dict is
missing the `key_name` and `conn_dict` keys the constructor now needs,
so running this module directly fails.

### `TouchStone`

Post-process one touchstone file into plots and extracted values.

**Attributes:**

MM_KEY (list of str): The post-processing keys that require the
    single-ended network to be converted to mixed-mode. Used to decide
    whether to pay for that conversion at construction time.

**Constructor**

```python
def TouchStone(info)
```

Load the touchstone file and prepare the networks to work from.

The file is read here, and the mixed-mode conversion is done up front
when the spec type calls for it, so the plotting methods can assume
both networks already exist.

**Args:**

- **info** (*dict*) — Everything needed to process this one file.

  * `file_dir` (str): Full path of the snp file.
  * `key_name` (str): Simulation key, used to name the figures.
  * `plt_dir` (str): Directory to write the figures into.
  * `spec_type` (dict): The spec type definition, whose
  `POST_PROCESS_KEY` list decides what gets produced.
  * `conn_dict` (dict): Connectivity lists per post-processing
  key, telling each plot which ports to draw. All port numbers
  here are one-based.

**Attributes:**

f (numpy.ndarray): The frequency axis in GHz. The underlying
    network keeps Hz, so this is the axis the plots use.
nw (skrf.Network): The single-ended network read from the file.
nw_mm (skrf.Network): The mixed-mode network, or `nw` itself when
    no mixed-mode post-processing was requested.
port_num (int): Port count of the single-ended network.
short0 (skrf.Network): A one-port short used to terminate ports.

#### `auto_process`

```python
def auto_process(self)
```

Automatically process SNP files based on spect_type.

Each key in the spec type's `POST_PROCESS_KEY` list is dispatched to
the matching plot method. A key with no case here is skipped silently.

**Returns:**

dict: Post-processing key to that key's output. The value is a list
of `[fig_title, fig_dir, ...]` entries for the single-ended keys,
and a dict of mixed-mode type to such a list for the `_MM` keys.

#### `plot_zself`

```python
def plot_zself(self, prockey=None)
```

Plot the self impedance with the sense ports left floating.

Uses the connectivity list to determine the Zin plot. The sense ports,
being the auxiliary ports that follow the main ones, are left open, so
the result is the impedance the sink sees with nothing shorting the
rail. One figure is written per main port.

**Args:**

- **prockey** (*str, optional*) — Post-processing key, folded into the
  figure names to keep the open and shorted variants apart.

**Returns:**

list of list: One entry per main port, being
`[fig_title, fig_dir, "", L_at_100MHz_pH, C_at_10kHz_nF]`. The
resistance slot is left empty, as it is not meaningful with the
sense ports open.

#### `plot_zself_shortsns`

```python
def plot_zself_shortsns(self, prockey=None)
```

Plot the self impedance with the sense ports shorted.

Uses the connectivity list to determine the Zin plot. Every port beyond
the main ones is terminated into a short before the impedance is read,
which models the VRM shorting the rail and makes the DC resistance of
the loop measurable.

**Args:**

- **prockey** (*str, optional*) — Post-processing key, folded into the
  figure names.

**Returns:**

list of list: One entry per remaining port, being
`[fig_title, fig_dir, R_at_1kHz_mOhm, L_at_100MHz_pH, ""]`. The
capacitance slot is left empty, as it is not meaningful with the
sense ports shorted.

#### `plot_il`

```python
def plot_il(self, conn_list, nw_s_db, prockey=None, header='S')
```

Plot insertion loss based on the connectivity dict.

Every requested through path is drawn as one curve on a single figure.

**Args:**

- **conn_list** (*list of list of int*) — One `[input_port, output_port]`
  pair per curve, one-based.
- **nw_s_db** (*numpy.ndarray*) — The S-parameters in dB, indexed
  `[freq, output, input]`.
- **prockey** (*str, optional*) — Post-processing key, folded into the
  figure name.
- **header** (*str, optional*) — Curve label prefix, naming the mode being
  drawn, e.g. `"S"`, `"SDD"`, or `"SDC"`. Defaults to
  `"S"`.

**Returns:**

list of list of str: A single entry `[fig_title, fig_dir]`, since
all the curves share one figure.

#### `plot_rl`

```python
def plot_rl(self, conn_list, nw_s_db, prockey=None, header='S')
```

Plot return loss based on the connectivity dict.

Every requested port is drawn as one reflection curve on a single
figure.

**Args:**

- **conn_list** (*list of int*) — The ports to draw, one-based.
- **nw_s_db** (*numpy.ndarray*) — The S-parameters in dB.
- **prockey** (*str, optional*) — Post-processing key, folded into the
  figure name.
- **header** (*str, optional*) — Curve label prefix. Defaults to `"S"`.

**Returns:**

list of list of str: A single entry `[fig_title, fig_dir]`.

#### `plot_il_mm`

```python
def plot_il_mm(self, conn_list, nw_mm_s_db, prockey=None)
```

Plot mixed-mode insertion loss based on the connectivity dict.

All four quadrants are plotted, so both the wanted differential and
common transmission and the unwanted mode conversion between them are
visible.

**Args:**

- **conn_list** (*list of list of int*) — One `[input_port, output_port]`
  pair per curve, numbered in mixed-mode ports.
- **nw_mm_s_db** (*numpy.ndarray*) — The mixed-mode S-parameters in dB.
- **prockey** (*str, optional*) — Post-processing key, folded into the
  figure names.

**Returns:**

dict: Quadrant name to the output of `plot_il` for it, with
the keys `"DD"`, `"CC"`, `"DC"`, and `"CD"`.

#### `plot_rl_mm`

```python
def plot_rl_mm(self, conn_list, nw_mm_s_db, prockey=None)
```

Plot mixed-mode return loss based on the connectivity dict.

Only the two like-mode quadrants are plotted, as reflection is read
within a mode rather than across modes.

**Args:**

- **conn_list** (*list of int*) — The mixed-mode ports to draw, one-based.
- **nw_mm_s_db** (*numpy.ndarray*) — The mixed-mode S-parameters in dB.
- **prockey** (*str, optional*) — Post-processing key, folded into the
  figure names.

**Returns:**

dict: Quadrant name to the output of `plot_rl` for it, with
the keys `"DD"` and `"CC"`.

#### `plot_zmag`

```python
def plot_zmag(self, fig_data, fig_title, fig_dir)
```

Plot Zmag vs. freq (GHz) and save it to a png.

Both axes are logarithmic, which is how a PDN impedance profile is
conventionally read.

**Args:**

- **fig_data** (*list of list*) — One curve per entry, as
  `[f, Z]` or `[f, Z, option]`, where `option` is a dict of
  matplotlib keyword arguments. A `label` in it turns the
  legend on.
- **fig_title** (*str*) — Title drawn on the figure.
- **fig_dir** (*str*) — Full path of the png to write.

#### `plot_smag`

```python
def plot_smag(self, fig_data, fig_title, fig_dir)
```

Plot Smag vs. freq (GHz) and save it to a png.

The frequency axis is linear here, unlike `plot_zmag`, since loss
curves are read against a linear frequency sweep.

**Args:**

- **fig_data** (*list of list*) — One curve per entry, as
  `[f, S]` or `[f, S, option]`, where `option` is a dict of
  matplotlib keyword arguments.
- **fig_title** (*str*) — Title drawn on the figure.
- **fig_dir** (*str*) — Full path of the png to write.

**Note:**

The y axis is always labelled `"S21 (dB)"`, including on the
return loss figures.

#### `plot_tdr`

```python
def plot_tdr(self, conn_list, nw_raw, prockey=None, header='SE')
```

Plot TDR for given ports.

A time-domain view needs a network that starts at DC and is sampled on
an even frequency grid, so the network is first extrapolated to DC when
it does not already reach it and then resampled onto a 10 MHz linear
step. Two figures are produced, one per end of the link.

**Args:**

- **conn_list** (*list of list of int*) — Two lists, being the left-side and
  the right-side ports, one-based.
- **nw_raw** (*skrf.Network*) — The network to transform. Copied, not
  modified.
- **prockey** (*str, optional*) — Post-processing key, folded into the
  figure names.
- **header** (*str, optional*) — Name of the mode being drawn, e.g.
  `"SE"`, `"DD"`, or `"CC"`. Defaults to `"SE"`.

**Returns:**

list of list of str: Two entries `[fig_title, fig_dir]`, for the
left and the right ports respectively.

#### `plot_tdr_mm`

```python
def plot_tdr_mm(self, conn_list, nw_raw, prockey=None)
```

Plot TDR for Mixed-mode ports.

In a mixed-mode network the differential ports occupy the first half of
the port range and the common ports the second half, so the common-mode
plot reuses the same connectivity list shifted by half the port count.

**Args:**

- **conn_list** (*list of list of int*) — Two lists of differential ports,
  being the left and the right side, one-based.
- **nw_raw** (*skrf.Network*) — The mixed-mode network.
- **prockey** (*str, optional*) — Post-processing key, folded into the
  figure names.

**Returns:**

dict: Mode name to the output of `plot_tdr` for it, with the
keys `"DD"` and `"CC"`.

#### `plot_time_domain`

```python
def plot_time_domain(self, conn_list, fig_data, fig_title, fig_dir)
```

Plot the step-response characteristic impedance and save it to a png.

**Args:**

- **conn_list** (*list of int*) — The ports to draw, one-based.
- **fig_data** (*skrf.Network*) — The network to read the step response
  from. Named for symmetry with the other plot methods, though it
  is a network rather than pre-computed curves.
- **fig_title** (*str*) — Title drawn on the figure.
- **fig_dir** (*str*) — Full path of the png to write.

#### `convert_snp_se2mm`

```python
def convert_snp_se2mm(self)
```

Convert SNP files from single-ended to mixed-mode Spara.

The single-ended ports are first renumbered into the pair order given
by `MM_ORDER_IN_SE`, since the conversion expects each differential
pair to sit in consecutive positions, and the result is written
alongside the input file in a `Mixed_Mode` sub-folder.

**Returns:**

skrf.Network: The mixed-mode network. The differential ports come
first, the common-mode ports second.

#### `from_list`

```python
def from_list(cls, info_list)
```

Input a list of dict and output a list of snp class.

**Args:**

- **info_list** (*list of dict*) — One `info` dict per touchstone file, as
  described in `__init__`.

**Returns:**

list of TouchStone: One instance per input dict, in order. Every
file is read as its instance is built, so the mixed-mode
conversions all happen here.

## `opensipi.util.common`

This Python3 module contains functions that are commonly used by the
OpenSIPI application.

The helpers fall into a few groups: path handling, which keeps the
application portable between Windows and Linux; text and file IO; and small
list, string, and dict reshaping utilities used to massage the input tables
into the structures the platform works with.

The reshaping helpers are deliberately unguarded. They assume the caller
already validated the shape of the data, so a malformed input sheet tends to
surface here as an `IndexError` rather than as a domain exception.

**Attributes:**

SL (str): The path separator for the current OS, `"\\"` on Windows and
    `"/"` elsewhere. Paths across the application are built by joining on
    this constant rather than by hardcoding a separator.

### `get_path_separator`

```python
def get_path_separator()
```

Get the right symbol to separate the path.

**Returns:**

str: `"\\"` on Windows, `"/"` on Mac, Linux, and BSD.

**Raises:**

UnboundLocalError: On an OS that is neither `nt` nor `posix`.

### `get_root_dir`

```python
def get_root_dir()
```

Get the root directory where the tool_config folder is created.

This is where the application looks for the `opensipi_config` folder.

**Returns:**

str: `"C:\\"` on Windows, the value of `$HOME` elsewhere, always
separator-ending.

**Raises:**

UnboundLocalError: On an OS that is neither `nt` nor `posix`.

### `get_dir`

```python
def get_dir()
```

Get commonly used dir.

The directories are derived from the location of this source file, so they
follow the installed package wherever it lives.

**Returns:**

tuple: A 3-tuple `(root_dir, scripts_dir, template_dir)` of
separator-ending paths, being respectively the grandparent of the
package, its parent, and the `templates` folder inside the package.

### `make_dir`

```python
def make_dir(tgt_dir)
```

Make dir if not existing.

Intermediate directories are created as needed, and an already existing
directory is left untouched.

**Args:**

- **tgt_dir** (*str*) — Directory path to create.

### `slash_ending`

```python
def slash_ending(dir)
```

Add a path separator at the end of a dir if not existing.

**Args:**

- **dir** (*str*) — Directory path, with or without a trailing separator.

**Returns:**

str: The path, guaranteed to end with the OS path separator, so that
a file name can be concatenated onto it directly.

### `rectify_dir`

```python
def rectify_dir(dir)
```

Correct dir separators to the ones the current OS uses.

Lets a path written on one OS, such as a Windows path pasted into an input
sheet, be used on another.

**Args:**

- **dir** (*str*) — Directory path using either separator.

**Returns:**

str: The path with its separators replaced by `SL`.

**Note:**

Only one separator style is converted. A path mixing `\\` and `/`
has its backslashes converted and its forward slashes left as they are.

### `rectify_data`

```python
def rectify_data(raw_data)
```

Strip white spaces before and after strings in the raw data.

Applied to every input sheet as it is read, so that the rest of the
application never has to worry about stray spacing a user left in a cell.

**Args:**

- **raw_data** (*list of list of str*) — The raw sheet contents.

**Returns:**

list of list of str: A new list of lists with every cell stripped.

### `get_run_time`

```python
def get_run_time()
```

Return the run start time in the format of YYMMDD_HHMMSS.

**Returns:**

str: The current local time, e.g. `"20240109_104753"`. Used to name
the `Run_...` folder and the simulation files of a run.

### `rm_list_item`

```python
def rm_list_item(in_list, item)
```

Remove a specific string from a list if any.

Every occurrence is removed, not just the first.

**Args:**

- **in_list** (*list*) — The list to remove from.
- **item** — The value to remove.

**Returns:**

list: The same list object, for convenience.

**Note:**

`in_list` is modified in place, so the caller's list changes too.

### `txtfile_rd`

```python
def txtfile_rd(dir)
```

Read a text file.

**Args:**

- **dir** (*str*) — Full path of the file to read.

**Returns:**

str: The whole file content.

### `txtfile_wr`

```python
def txtfile_wr(dir, ctnt)
```

Write a text file, replacing any existing content.

**Args:**

- **dir** (*str*) — Full path of the file to write.
- **ctnt** (*str*) — The content to write.

### `list_upper`

```python
def list_upper(in_list)
```

Convert each item in a list to upper case.

**Args:**

- **in_list** (*list of str*) — The strings to convert.

**Returns:**

list of str: The upper-cased strings.

### `list_strip`

```python
def list_strip(in_list)
```

Strip the whitespaces before/after each item in a list.

**Args:**

- **in_list** (*list of str*) — The strings to strip.

**Returns:**

list of str: The stripped strings.

### `lol_numerical_add_list`

```python
def lol_numerical_add_list(in_lol, in_list)
```

Add an offset list to each item of the list of list.

The offsets are applied element-wise, so `in_list` acts as a per-column
offset applied to every row.

**Args:**

- **in_lol** (*list of list of numbers*) — The rows to offset.
- **in_list** (*list of numbers*) — One offset per column.

**Returns:**

list of list of int: The offset rows, each value truncated to int.
A row longer than `in_list` is silently cut short to its length.

### `lol_numerical_add_num`

```python
def lol_numerical_add_num(in_lol, in_num)
```

Add an offset number to each item of the list of list.

**Args:**

- **in_lol** (*list of list of numbers*) — The rows to offset.
- **in_num** (*number*) — The offset applied to every value.

**Returns:**

list of list of int: The offset rows, each value truncated to int.

### `rm_ext`

```python
def rm_ext(full_name)
```

Remove the file extension from a file name.

**Args:**

- **full_name** (*str*) — File name, with or without an extension.

**Returns:**

str: The name up to the last dot, or the name unchanged if it holds no
dot at all.

### `unique_list`

```python
def unique_list(in_list)
```

Remove duplicates in a list.

**Args:**

- **in_list** (*list*) — The list to deduplicate. Items must be hashable.

**Returns:**

list: The items with duplicates dropped, first occurrence order kept.

### `intfy_list`

```python
def intfy_list(in_list)
```

Apply int to each item of a list of number string.

The conversion goes through float first, so exponent notation such as
`"1e6"` is accepted as well as plain digits.

**Args:**

- **in_list** (*list of str*) — The number strings to convert.

**Returns:**

list of int: The converted numbers, truncated toward zero.

**Raises:**

ValueError: If an item is not parsable as a number.

### `get_cols_out_of_list_of_list`

```python
def get_cols_out_of_list_of_list(in_list, i_col)
```

Get the specified columns out of a list of list.

**Args:**

- **in_list** (*list of list*) — The rows to select from.
- **i_col** (*list of int*) — Zero-based column indices to keep, in the order
  they should appear in the result.

**Returns:**

list of list: One row per input row, holding only the selected columns.

**Raises:**

IndexError: If a row is shorter than the largest requested index.

### `get_str_after_last_symbol`

```python
def get_str_after_last_symbol(in_str, symbol)
```

Get the string after the last specific symbol.

**Args:**

- **in_str** (*str*) — The string to split.
- **symbol** (*str*) — The separator to look for.

**Returns:**

str: The trailing part, or the whole string if the symbol is absent.

### `get_str_before_last_symbol`

```python
def get_str_before_last_symbol(in_str, symbol)
```

Get the string before the last specific symbol.

**Args:**

- **in_str** (*str*) — The string to split.
- **symbol** (*str*) — The separator to look for.

**Returns:**

str: The leading part, with any earlier occurrence of the symbol kept.
An empty string if the symbol is absent.

### `split_str_at_last_symbol`

```python
def split_str_at_last_symbol(in_str, symbol)
```

Split the string at the last specific symbol.

**Args:**

- **in_str** (*str*) — The string to split.
- **symbol** (*str*) — The separator to look for.

**Returns:**

tuple: A 2-tuple `(before_symbol_str, after_symbol_str)`. If the
symbol is absent, the first item is empty and the second is the whole
string.

### `get_str_before_last_n_symbol`

```python
def get_str_before_last_n_symbol(in_str, symbol, index)
```

Get the string before the last n specific symbol.

Used to climb a path by a fixed number of levels.

**Args:**

- **in_str** (*str*) — The string to split.
- **symbol** (*str*) — The separator to look for.
- **index** (*int*) — How many trailing segments to drop.

**Returns:**

str: The leading part with `index` trailing segments removed.

### `get_str_before_first_symbol`

```python
def get_str_before_first_symbol(in_str, symbol)
```

Get the string before the first specific symbol.

**Args:**

- **in_str** (*str*) — The string to split.
- **symbol** (*str*) — The separator to look for.

**Returns:**

str: The leading part, or the whole string if the symbol is absent.

### `str2dict`

```python
def str2dict(in_str, del_high, del_low)
```

Break a string with two-level separators to a dict.

The high-level separator splits the string into entries; within an entry,
the low-level separator splits off the key from its values. This is the
shape several input cells use, e.g. `"U1, 1, 2; U2, 5"`.

**Args:**

- **in_str** (*str*) — The string to break up. An empty string yields an empty
  dict.
- **del_high** (*str*) — The separator between entries.
- **del_low** (*str*) — The separator between an entry's key and its values.

**Returns:**

dict: First item of each entry to the list of that entry's remaining
items, which is empty when the entry holds a key alone. A repeated key
keeps only its last entry.

### `str2listoflist`

```python
def str2listoflist(in_str, del_high, del_low)
```

Break a string with two-level separators to a list of list.

The list counterpart of `str2dict`, keeping the entries in order and
tolerating repeated first items.

**Args:**

- **in_str** (*str*) — The string to break up. An empty string yields an empty
  list.
- **del_high** (*str*) — The separator between entries.
- **del_low** (*str*) — The separator within an entry.

**Returns:**

list of list of str: One inner list per non-empty entry, items
stripped.

### `exist_dir`

```python
def exist_dir(dir)
```

Check if a dir/file exists and print the verdict.

A debugging aid. The result is printed rather than returned, so this is not
usable as a condition.

**Args:**

- **dir** (*str*) — The path to check.

### `csv2dict`

```python
def csv2dict(csv_dir, start_row=1)
```

Import a csv file and convert its contents to a dict.

The key is based on the 1st col contents. Rows sharing a first column are
grouped under that key, which is how a multi-row record is kept together.
Rows with an empty first column are dropped.

**Args:**

- **csv_dir** (*str*) — Full path of the csv file.
- **start_row** (*int, optional*) — Zero-based index of the first data row.
  Defaults to `1`, skipping the header.

**Returns:**

tuple: A 2-tuple `(ctnt_dict, col_title)`, where `ctnt_dict` maps
the first column value to the list of its rows, each row being a list
of stripped cell strings, and `col_title` is the header row.

**Note:**

The file is split on commas rather than parsed as csv, so a quoted
cell holding a comma is split apart. Use `csv2listoflists` where
that matters.

### `striped_str2list`

```python
def striped_str2list(in_str, separator)
```

Split a string to a list and strip each item.

Splits on a certain separator and removes all white spaces before and after
each list item.

**Args:**

- **in_str** (*str*) — The string to split.
- **separator** (*str*) — The separator to split on.

**Returns:**

list of str: The stripped items. An empty input yields `[""]`.

### `listoflist2dictofdict`

```python
def listoflist2dictofdict(in_list)
```

Convert a list of list to a dict of dict.

The top level dict keys are named after the 1st col from 2nd row. The
second level dict keys are named after the header from the 2nd col, so the
first column acts as the record name and is not repeated inside the record.

**Args:**

- **in_list** (*list of list*) — The rows, first row being the header.

**Returns:**

dict: First column value to a dict of the remaining columns, keyed by
their header. A repeated first column value keeps only its last row.

**Raises:**

IndexError: If a row is shorter than the header.

### `listoflist2dictcol`

```python
def listoflist2dictcol(in_list)
```

Convert a list of list to a column-oriented dict.

The 1st row/list headers are treated as keys. Each column of the remaining
rows/lists forms the value to each key. The input list of list must be of
regular shape. Items in the 1st list must be unique.

**Args:**

- **in_list** (*list of list*) — The rows, first row being the header.

**Returns:**

dict: Header to the list of that column's values, one item per data
row.

**Raises:**

IndexError: If the rows are not all the same length.

### `transpose_listoflist`

```python
def transpose_listoflist(in_list)
```

Transpose the input list of list like a matrix.

**Args:**

- **in_list** (*list of list*) — The rows to transpose. Must be non-empty and of
  regular shape.

**Returns:**

list of list: The columns of the input, as rows.

**Raises:**

IndexError: If the input is empty or its rows differ in length.

### `split_str_by_guess`

```python
def split_str_by_guess(in_str)
```

Split a string by guessing which delimiter was used.

The delimiters are tried in the sequence `'\n'` > `','` > `';'` and
the first one present wins, so only one type of delimiter is assumed. This
lets a user list items in an input cell however they find natural. White
spaces before and after each item are removed.

**Args:**

- **in_str** (*str*) — The string to split.

**Returns:**

list of str: The stripped items. A string holding none of the three
delimiters yields a single-item list.

### `csv2listoflists`

```python
def csv2listoflists(file)
```

Read in a csv file and store the contents as a list of lists.

Unlike `csv2dict`, this goes through the csv module, so quoted cells
holding commas survive intact.

**Args:**

- **file** (*str*) — Full path of the csv file.

**Returns:**

list of list of str: One inner list per row, cells unstripped.

### `export_dict_to_yaml`

```python
def export_dict_to_yaml(data, dir)
```

Export the dict as a yaml file.

Used to hand configuration between the stages of a run, so that a later
stage can pick up where an earlier one left off.

**Args:**

- **data** (*dict*) — The data to write. Must hold only plain types, as the safe
  dumper is used.
- **dir** (*str*) — Full path of the yaml file to write.

### `load_yaml_to_dict`

```python
def load_yaml_to_dict(dir)
```

Load a yaml file to a dict.

**Args:**

- **dir** (*str*) — Full path of the yaml file to read.

**Returns:**

dict: The parsed content.

### `expand_home_dir`

```python
def expand_home_dir(in_dir)
```

Expand ~ as the home dir.

**Args:**

- **in_dir** (*str*) — A path possibly holding `~`.

**Returns:**

str: The path with every `~` replaced by the home directory, not just
a leading one.

### `either_case`

```python
def either_case(ltr)
```

Generate a regex matching both cases of a letter, skip for nonalpha.

Joined over a word, this builds a case-insensitive glob pattern, which is
how input files are matched regardless of how their extension is cased.

**Args:**

- **ltr** (*str*) — A single character.

**Returns:**

str: `"[aA]"` style bracket expression for a letter, or the character
unchanged if it is not alphabetic.

### `img2str`

```python
def img2str(img_dir)
```

Convert an image file to a string.

Lets a figure be embedded directly in an html report instead of being
referenced as a separate file.

**Args:**

- **img_dir** (*str*) — Full path of the image file.

**Returns:**

str: The file content, base64 encoded and decoded to ascii text.

### `Vividict`

Implement nested dict

Copied from https://stackoverflow.com/questions/635483/what-is-
the-best-way-to-implement-nested-dictionaries

Reading a missing key creates an empty `Vividict` at that key instead of
raising, so an arbitrarily deep path can be assigned in one statement
without creating each level first.

## `opensipi.util.docgen`

Generate a deterministic Markdown API reference from source docstrings.

### `DocGen`

Render the public Python API as Markdown without importing the package.

**Args:**

- **pkg_dir** (*str or pathlib.Path*) — Package directory to scan.
- **out_path** (*str or pathlib.Path*) — Markdown file to write.
- **exclude** (*tuple of str*) — Package directory names to skip.

**Constructor**

```python
def DocGen(pkg_dir='opensipi', out_path='docs/Home/API-Reference.md', exclude=('autopwt',))
```

Initialize the generator paths and exclusions.

**Args:**

- **pkg_dir** (*str or pathlib.Path*) — Package directory to scan.
- **out_path** (*str or pathlib.Path*) — Markdown file to write.
- **exclude** (*tuple of str*) — Package directory names to skip.

#### `build`

```python
def build(self) -> str
```

Render the complete API reference without writing it.

**Returns:**

str: Deterministic Markdown ending in exactly one newline.

#### `write`

```python
def write(self) -> bool
```

Write the reference only when its content has changed.

**Returns:**

bool: `True` when the output file was changed, otherwise `False`.

### `main`

```python
def main() -> int
```

Regenerate the API reference and fail when the file was stale.

## `opensipi.util.exceptions`

This Python3 module contains exceptions that are commonly used by the
OpenSIPI application.

Every exception here reports its own message as a side effect of being
constructed, either by printing it or, once a run logger exists, by writing it
to that logger. The classes taking a logger are therefore only usable after
`Platform` has set logging up.

Note none of these classes forwards a message to `Exception.__init__`, so
the raised object itself carries no text. The explanation reaches the user
through the print or the log record, not through `str(exc)`.

### `NoLegalSimWbFound`

Raised when no legal sim workbook titles is found.

**Constructor**

```python
def NoLegalSimWbFound()
```

Report that no sheet name matched the expected sim prefix.

### `NoSimRowFound`

Raised when no sim row is found in the sim workbook.

**Constructor**

```python
def NoSimRowFound()
```

Report that the sim sheet holds a header but no data rows.

### `NoneUniqueKeyDefined`

Raised when none unique key is defined for power rails
in the same workbook.

**Constructor**

```python
def NoneUniqueKeyDefined()
```

Report that a `Unique_Key` is duplicated within one sim sheet.

### `MaterialsMustBeDefinedBeforeStackup`

Raised when materials are not defined before stackup in the Workbook
'Stackup_Materials'.

**Constructor**

```python
def MaterialsMustBeDefinedBeforeStackup()
```

Report that the `Materials` section is not above `Stackup`.

### `NoProjNameFound`

Raised when no project name is specified in the gSheet
Special_Settings tab.

**Constructor**

```python
def NoProjNameFound()
```

Report that `ProjectName` is missing from the special settings.

### `NoDsnFound`

Raised when no design files is found in the directory.

**Constructor**

```python
def NoDsnFound(lg)
```

Report that the design directory holds no file of an accepted type.

**Args:**

- **lg** (*logging.Logger*) — The run logger to report through.

### `NoExistingNames`

Raised when names in gSheet don't exist.

**Constructor**

```python
def NoExistingNames(lg, name)
```

Report input net or component names absent from the design file.

**Args:**

- **lg** (*logging.Logger*) — The run logger to report through.
- **name** (*list of str*) — The offending net or component names, listed
  one per line in the log record.

### `IllegalInputFormat`

Raised when illegal input format is found.

**Constructor**

```python
def IllegalInputFormat(lg, errors)
```

Report the format errors found while scanning the input sheets.

**Args:**

- **lg** (*logging.Logger*) — The run logger to report through.
- **errors** (*list of str*) — The error descriptions, logged one per line.

### `ImproperCountOfComp`

Raise when the counts of the component in the gSheet are
improperly given.

**Constructor**

```python
def ImproperCountOfComp(lg)
```

Report that a component count in the input is not usable.

**Args:**

- **lg** (*logging.Logger*) — The run logger to report through.

### `UnequalPortCounts`

Raised when port counts don't match between defined and actually
generated in the spd.

**Constructor**

```python
def UnequalPortCounts(lg, name)
```

Report simulations whose generated port count is off.

A mismatch means the solver did not build every port the input asked
for, so the extraction would produce results that cannot be
post-processed as expected.

**Args:**

- **lg** (*logging.Logger*) — The run logger to report through.
- **name** (*list of str*) — The affected simulation keys, listed one per
  line in the log record.

### `NoneUniqueFolderInDrive`

Raised when more than one folder with the same name is found in
a single G drive path.

**Constructor**

```python
def NoneUniqueFolderInDrive(lg)
```

Report a duplicated folder name in one Google Drive path.

**Args:**

- **lg** (*logging.Logger*) — The run logger to report through.

### `NonUniqueFileInDrive`

Raised when more than one file with the same name is found
in a single G drive path.

**Constructor**

```python
def NonUniqueFileInDrive(lg)
```

Report a duplicated file name in one Google Drive path.

**Args:**

- **lg** (*logging.Logger*) — The run logger to report through.

### `WrongGrowSolderFormat`

Raised when the input format of the grow solder settings is wrong

**Constructor**

```python
def WrongGrowSolderFormat(lg, error)
```

Report a malformed `GrowTopSolder` or `GrowBotSolder` setting.

**Args:**

- **lg** (*logging.Logger*) — The run logger to report through.
- **error** (*str*) — The ready-to-log description of what is wrong.

### `UndefinedSurfaceRoughnessModelType`

Raised when the input surface roughness model type is undefined

**Constructor**

```python
def UndefinedSurfaceRoughnessModelType(lg, error)
```

Report a surface roughness model type that is not recognized.

**Args:**

- **lg** (*logging.Logger*) — The run logger to report through.
- **error** (*str*) — The ready-to-log description of what is wrong.

### `NoSpecialSettingsFound`

Raised when no special settings are found.

**Constructor**

```python
def NoSpecialSettingsFound()
```

Report that the mandatory special settings sheet is missing.

### `NoProjDirDefined`

Raised when no proj dir was defined.

**Constructor**

```python
def NoProjDirDefined()
```

Report that neither `proj_dir` nor `input_dir` was supplied.

### `WrongAreaPortDef`

Raised when area port definition was wrong.

**Constructor**

```python
def WrongAreaPortDef(lg)
```

Report a malformed `Rec{...}` area port definition.

**Args:**

- **lg** (*logging.Logger*) — The run logger to report through.

## `opensipi.util.logs`

This Python3 module provides utilities for test logging and result saving.

### `setup_logger`

```python
def setup_logger(log_dir, log_header)
```

Create a logger writing to both a log file and the console.

Propagation to the root logger is disabled, so records emitted here do not
reach handlers installed by the application embedding OpenSIPI.

**Args:**

- **log_dir** (*str*) — Full path of the log file to write, including the file
  name.
- **log_header** (*str*) — Logger name, shown in each record and used to
  retrieve the same logger again through `logging.getLogger`.

**Returns:**

logging.Logger: The configured logger, at level `DEBUG`.

**Note:**

If the log file cannot be opened, the error is printed and the logger
is returned with no handlers attached rather than raising, so a
failure to log never aborts an extraction.
