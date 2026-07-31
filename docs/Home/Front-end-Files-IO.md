<!--
SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
SPDX-FileCopyrightText: 2024 Rivos Inc.

SPDX-License-Identifier: Apache-2.0
-->

[← Documentation Home](/docs/Home.md)

# Front-end Files IO

## Introduction

The simulation input information is maintained in tables. The users can edit it in Excel,
Google Sheets, or an equivalent tool.

The simulation results are either touchstone (`.sNp`) files for S-parameters or CSV files
for DCR results. A summary report in PDF format is typically created for the output
results.

**On this page**

- [Simulation Input](#simulation-input)
  - [File Formats](#file-formats)
  - [Input Sheets](#input-sheets)
  - [Sim Sheets (Mandatory)](#sim-sheets-mandatory)
  - [Stackup and Materials (Mandatory)](#stackup-and-materials-mandatory)
  - [Special Settings (Mandatory)](#special-settings-mandatory)
  - [Spec Type (Optional)](#spec-type-optional)
- [Simulation Output](#simulation-output)

---

## Simulation Input

### File Formats

The input tables can be supplied in either of two ways.

| Input type | How it is read                                                        | Entry point             |
| ---------- | --------------------------------------------------------------------- | ----------------------- |
| `csv`      | A folder of CSV files, one file per sheet.                            | `sim2report()`          |
| `gsheet`   | A Google Sheet workbook, one tab per sheet.                           | `sim2report_gsuites()`  |

The allowed **design** file formats are listed below.

| Design file | Extension                          | Description                                                                                                                                                                                                                                    |
| ----------- | ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `brd`       | `.brd`                             | PCB design files exported by Cadence Allegro.                                                                                                                                                                                                  |
| `odb`       | `.tgz`, `.zip`, `.gz`, `.z`, `.tar`, `.7z` | PCB design files in ODB++ format.                                                                                                                                                                                                      |
| `mcm`       | `.mcm`                             | PKG design files exported by Cadence APD.                                                                                                                                                                                                      |
| `spd`       | `.spd`                             | PCB or PKG simulation files exported by Cadence Sigrity tool sets. Accepted only when `ExtractionTool` is set to `Sigrity` in the `Special_Settings` sheet. The `spd` file is loaded **as is** — no stack-up/material change and no solder growing. |

### Input Sheets

Four different types of sheets can be read into the platform as simulation input. Three
are mandatory and one is optional.

| Sheet                | Type      | Purpose                                                                     |
| -------------------- | --------- | --------------------------------------------------------------------------- |
| `Sim1`, `Sim2`, …    | Mandatory | Simulation setup and post-processing info. As many sheets as you like.      |
| `Stackup_Materials`  | Mandatory | Layer stack-up, materials, and surface roughness models. Exactly one sheet. |
| `Special_Settings`   | Mandatory | Global run settings such as tool, extraction type, BOM. Exactly one sheet.  |
| `Spec_Type`          | Optional  | User-defined spec types (frequency ranges + post-processing keys).          |

### Sim Sheets (Mandatory)

These sheets contain all the information needed to set up simulations and post-process
the results. Their names start with `Sim` followed by an integer — `Sim1`, `Sim2`, … —
so you can group simulations however you like.

The simulation file will be created with the name
`Sim[x]_[Unique_Key]_[Run_Time]_[...].[File_Extension]`, where `Run_Time` is assigned
automatically when the simulations start (unless specified by the user) and
`File_Extension` refers to `spd` if using Sigrity tools.

#### Column Reference

| Column                | Type      | Description                                                                                                                                                                                                                                                                                                          |
| --------------------- | --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Unique_Key`          | Mandatory | Simulation identifier. Each name represents an individual simulation. Any meaningful name works, but it must be unique within the sheet. For 1-port or 2-port simulations, one row holds everything. For simulations with more than 2 ports, use multiple rows: only the first row carries a `Unique_Key`, and subsequent rows with a blank Col A belong to the same simulation. |
| `Check_Box`           | Mandatory | Simulation enable pin — `True` or `False`. It can be presented as a check box in Excel or Google Sheets.                                                                                                                                                                                                             |
| `Spec_Type`           | Mandatory | Indicates the simulation frequency and how to post-process the data. Assign it only on the first row of a simulation. See the per-extraction-type sections below for the available values. **Lowest frequency priority** — see [Frequency priority](#frequency-priority).                                             |
| `Positive_Nets`       | Mandatory | Positive nets to be included in the simulation. Use `,` to separate multiple nets.                                                                                                                                                                                                                                   |
| `Negative_Nets`       | Mandatory | Negative nets to be included in the simulation. Use `,` to separate multiple nets.                                                                                                                                                                                                                                   |
| `Positive_Main_Ports` | Mandatory | RefDes and its pins defining the positive side of a port. Use `,` to separate the RefDes and its pins. Area ports are also supported in PDN and LSIO extraction: `Rec{LLx, LLy, URx, URy, LayerName[, Net_Pos, Net_Neg]}`, where the contents in `[]` are optional and the unit is m. If `Net_Pos`/`Net_Neg` are omitted, the first net in `Positive_Nets` and `Negative_Nets` is used — so net order matters in that case. |
| `Negative_Main_Ports` | Mandatory | RefDes and its pins defining the negative side of a port. Use `,` to separate the RefDes and its pins.                                                                                                                                                                                                               |
| `Positive_Aux_Ports`  | Mandatory | RefDes and its pins defining the positive side of an auxiliary port. Area ports are also supported in PDN extraction: `Rec{LLx, LLy, URx, URy, LayerName}`, unit m. Aux ports of the obtained S-/Z-parameters may be shorted or opened during post-processing based on `Spec_Type`.                                   |
| `Negative_Aux_Ports`  | Mandatory | RefDes and its pins defining the negative side of an auxiliary port. Aux ports may be shorted or opened during post-processing based on `Spec_Type`.                                                                                                                                                                 |
| `Op_Freq`             | Optional  | Simulation frequency for this `Unique_Key`. **Highest frequency priority.** Format: `FREQ_START, FREQ_END, FREQ_STEP, FREQ_SOL`.                                                                                                                                                                                     |
| `Op_DiffPair`         | Optional  | Differential pairs, for the `LSIO` and `HSIO` extraction types.                                                                                                                                                                                                                                                      |
| `Op_DisAllCaps`       | Optional  | Cap models are included automatically when this is empty. Any non-empty value disables caps for that simulation.                                                                                                                                                                                                     |
| `Op_PreCut`           | Optional  | Precut the board to the rectangle `LLX, LLY, URX, URY` in mm. This per-design precut is applied on top of `GlobalPreCut`.                                                                                                                                                                                            |

> [!NOTE]
> Ports are indexed top to bottom of the main ports, then top to bottom of the auxiliary
> ports.

#### Frequency Priority

The simulation frequency can be set in three places. The first one defined wins.

| Priority | Where                          | Scope           |
| -------- | ------------------------------ | --------------- |
| 1        | `Op_Freq` in a Sim sheet       | Per `Unique_Key`|
| 2        | `GlobalFreq` in `Special_Settings` | Whole run   |
| 3        | `Spec_Type`                    | Per spec type   |

The format is `FREQ_START, FREQ_END, FREQ_STEP, FREQ_SOL`, where:

| Extraction type | Mandatory items                                   |
| --------------- | ------------------------------------------------- |
| `PDN`           | `FREQ_START`, `FREQ_END`                          |
| `LSIO`          | `FREQ_START`, `FREQ_END`, `FREQ_STEP`             |
| `HSIO`          | all four                                          |

---

#### Allowed Formats per Extraction Type

The best way to explain the allowed formats is through examples.

##### PDN

Let's start with a PDN example. Say I want to simulate the PDN response of a few power
planes in a PCB, i.e. P0V9 and P1V8.

**Case 1 — one port at the sink, one port at the VRM.** Looking at the schematic, PP0V9
starts from inductor pin 2 of PL11 and ends at multiple BGA pins (R11, R13, R15 etc.) of
U1. I want one port at U1 and one port at the inductor PL11. The right way to implement
it is shown in row 2 of the table below:

- I only put a RefDes in `Positive_Main_Ports` and leave `Negative_Main_Ports` blank.
  This sets up a port at U1 whose positive pins are all U1 pins connected to
  `Positive_Nets` and whose negative pins are all U1 pins connected to `Negative_Nets`.
- I put `PL11, 2; C173; PC598` in `Positive_Aux_Ports` and `PC592, 2; PC1600` in
  `Negative_Aux_Ports`. This creates a port whose positive pins are pin 2 of PL11, the
  C173 pins touching the positive net P0V9, and the PC598 pins touching the positive net
  P0V9; and whose negative pins are pin 2 of PC592 and the PC1600 pins touching the
  negative net GND.

![image](/docs/Figures/P0V9_VRM.png)

![image](/docs/Figures/P1V8_VRM.png)

![image](/docs/Figures/SoC_PDN.png)

**Case 2 — two ports at the sink, one port at the VRM.** The P1V8 power rail starts from
pin 2 of PL8 and ends at multiple pins (N6, T7, N18 etc.) of U1. I want two ports at U1
and one port at PL8. The two ports at U1 cover two groups of pins:

- Group 1: N6, T7, N18
- Group 2: U12, T17, J17, J12, K7

The right way to set it up is shown in rows 3–4 of the table below.

- **Port 1** — I put `U1, N6, T7, N18` in row 3 `Positive_Main_Ports`, making the group 1
  pins the positive pins. You can list multiple U1 pins connected to `Negative_Nets` in
  `Negative_Main_Ports` in the form `RefDes, Pin# ...`. But if you simply want all U1 pins
  connected to `Negative_Nets` as the negative pins, just put `U1` there.
- **Port 2** — the group 2 equivalent, easy to understand from row 4.
- **Port 3** — defined by `PL8, 2` in `Positive_Aux_Ports` and
  `PC551, 2; PR375, RAD{0.005, Signal$TOP}` in `Negative_Aux_Ports`. The
  `RAD{}` term detects ground nodes within a given radius of the positive nodes of a
  component and adds them to the port's negative side. Here `PR375` is the RefDes,
  `RAD{}` is a fixed keyword, the radius is `0.005` m, and `Signal$TOP` is the target
  layer where ground nodes shall be detected.

![image](/docs/Figures/input_sheet_PDN.png)

**Area ports.** Rectangular area ports are also supported for PDN extraction. Put the
definition in `Positive_Main_Ports` or `Positive_Aux_Ports` and leave its negative
counterpart blank.

```text
Rec{LLx, LLy, URx, URy, LayerName[, Net_Pos, Net_Neg]}
```

| Field       | Meaning                                                              |
| ----------- | -------------------------------------------------------------------- |
| `Rec`       | Fixed keyword — cannot be changed.                                   |
| `LLx`,`LLy` | x/y coordinate of the lower-left corner, in m.                       |
| `URx`,`URy` | x/y coordinate of the upper-right corner, in m.                      |
| `LayerName` | The actual layer name where the area port is defined.                |
| `Net_Pos`, `Net_Neg` | *Optional.* The single positive and single negative nets for the area port. If omitted, the area port is defined between the **first** listed positive and negative nets. |

**Column formats for PDN**

| Column                | Allowed values                                                                                                                                                                                                              |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Spec_Type`           | `Zpdn`: default simulation frequency 0 to 1 GHz with automatic frequency sweeping; Z-para post-processing includes open **and** shorted auxiliary ports. <br> `Zl`: default simulation frequency 0 to 1 GHz with automatic frequency sweeping; Z-para post-processing includes shorted auxiliary ports. |
| `Positive_Nets`       | The first row lists all positive nets included in the extraction. Use `,` to separate multiple nets.                                                                                                                        |
| `Negative_Nets`       | The first row lists all negative nets included in the extraction. Use `,` to separate multiple nets.                                                                                                                        |
| `Positive_Main_Ports` | Diff port: `RefDes0[, Positive pins; RefDes1, Positive pins; ...]` — contents in `[]` are optional, so even the pins are optional. <br> Component port: `RefDes` <br> Area port: `Rec{LLx, LLy, URx, URy, LayerName[, Net_Pos, Net_Neg]}`, unit m. |
| `Negative_Main_Ports` | Diff port: `RefDes0[, Negative pins; RefDes2, Negative pins; RefDes3, RAD{radius, target_layer}; ...]` <br> Component port: blank <br> Area port: blank                                                                      |
| `Positive_Aux_Ports`  | Diff port: `RefDes0[, Positive pins; RefDes1, Positive pins; ...]` <br> Component port: `RefDes` <br> Area port: `Rec{LLx, LLy, URx, URy, LayerName[, Net_Pos, Net_Neg]}`, unit m.                                           |
| `Negative_Aux_Ports`  | Diff port: `RefDes0[, Negative pins; RefDes2, Negative pins; ...]` <br> Component port: blank <br> Area port: blank                                                                                                          |

##### LSIO

**Column formats for LSIO**

| Column                | Allowed values                                                                                                                                                            |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Spec_Type`           | `Sls`: default simulation frequency 1 MHz to 5 GHz with a step size of 5 MHz.                                                                                             |
| `Positive_Nets`       | Each row lists all positive nets connected to the ports defined in the same row. Use `,` to separate nets. Rows in the same Sim key cannot be merged. Nets can be duplicated across rows in the same Sim key. |
| `Negative_Nets`       | Each row lists all negative nets connected to the ports defined in the same row. Use `,` to separate nets. Rows in the same Sim key cannot be merged. Nets can be duplicated across rows in the same Sim key. |
| `Positive_Main_Ports` | Diff port: `RefDes, Positive pins` <br> Area port: `Rec{LLx, LLy, URx, URy, LayerName[, Net_Pos, Net_Neg]}`, unit m.                                                       |
| `Negative_Main_Ports` | Diff port: `RefDes, Negative pins` <br> Area port: blank                                                                                                                  |
| `Positive_Aux_Ports`  | Diff port: `RefDes, Positive pins` <br> Area port: `Rec{LLx, LLy, URx, URy, LayerName[, Net_Pos, Net_Neg]}`, unit m.                                                       |
| `Negative_Aux_Ports`  | Diff port: `RefDes, Negative pins` <br> Area port: blank                                                                                                                  |

The port definition takes two forms.

1. `RefDes + pins` for both the positive and the negative side.
2. An area port `Rec{LLx, LLy, URx, URy, LayerName[, Net_Pos, Net_Neg]}` — put the
   definition only on the positive side and leave the negative side blank.

**Port indexing.** The ports are indexed from main to aux, top to bottom. For example,
the port sequence in the second test case shown below, `I2C_PCA9548_SC6`, is:

| Port | Positive  | Negative  |
| ---- | --------- | --------- |
| 1    | `U2, 18`  | `U2, 12`  |
| 2    | `U2, 17`  | `U2, 12`  |
| 3    | `U4, 8`   | `U4, 5`   |
| 4    | `U10, 10` | `U10, 6`  |
| 5    | `U7, 6`   | `U7, 4`   |
| 6    | `U9, 9`   | `U9, 4`   |
| 7    | `U4, 7`   | `U4, 5`   |
| 8    | `U10, 9`  | `U10, 6`  |
| 9    | `U7, 5`   | `U7, 4`   |
| 10   | `U9, 8`   | `U9, 4`   |

![image](/docs/Figures/input_sheet_LSIO.png)

Changing the above port 1 and port 3 definitions to the area port format, they would look
like this:

```text
Port1: Rec{0.162, 0.0337, 0.167, 0.041, Signal$TOP}
Port3: Rec{0.171, 0.0775, 0.1726, 0.080, Signal$BOTTOM, I2C_PCA9548_SC6_EMC1412_SCL}
```

**Mixed-mode ports.** `Op_DiffPair` uses `P#` and `N#` to indicate the positive and
negative pins of a mixed-mode (MM) port `#`.

> [!IMPORTANT]
> Port numbers must start from 1 and be continuous. Mixing MM and single-ended (SE) ports
> is not allowed.

The example in the picture above defines the following MM ports.

| MM port | Positive SE port | Negative SE port |
| ------- | ---------------- | ---------------- |
| 1       | 1                | 2                |
| 2       | 3                | 7                |
| 3       | 4                | 8                |
| 4       | 5                | 9                |
| 5       | 6                | 10               |

##### HSIO

**Column formats for HSIO**

| Column                | Allowed values                                                                                                                                                                                                    |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Spec_Type`           | `Sddr5`: default simulation frequency 1 MHz to 15 GHz, step size 100 MHz, solution frequency 5 GHz. <br> `Spcie6`: default simulation frequency 1 MHz to 50 GHz, step size 100 MHz, solution frequency 16 GHz.     |
| `Positive_Nets`       | Each row lists all positive nets connected to the ports defined in the same row. Use `,` to separate nets. Rows in the same Sim key cannot be merged. Nets can be duplicated across rows in the same Sim key.      |
| `Negative_Nets`       | Each row lists all negative nets connected to the ports defined in the same row. Use `,` to separate nets. Rows in the same Sim key cannot be merged. Nets can be duplicated across rows in the same Sim key.      |
| `Positive_Main_Ports` | RefDes only                                                                                                                                                                                                       |
| `Negative_Main_Ports` | Blank                                                                                                                                                                                                             |
| `Positive_Aux_Ports`  | RefDes only                                                                                                                                                                                                       |
| `Negative_Aux_Ports`  | Blank                                                                                                                                                                                                             |

> [!WARNING]
> The port setup currently only takes a RefDes. This assumes the component has only one
> pin connecting to the enabled nets, which is typically true — but there is a loophole if
> the assumption doesn't hold. This will be looked into in the future.

![image](/docs/Figures/input_sheet_HSIO.png)

##### DCR

**Column formats for DCR**

| Column                | Allowed values          |
| --------------------- | ----------------------- |
| `Spec_Type`           | `Rm2l`, `Rl2l`          |
| `Positive_Main_Ports` | Sink positive pins      |
| `Negative_Main_Ports` | Sink negative pins      |
| `Positive_Aux_Ports`  | "VRM" positive pins     |
| `Negative_Aux_Ports`  | "VRM" negative pins     |

For DCR extraction, only two spec types are supported so far.

| `Spec_Type` | Meaning                                                                                                                                            |
| ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Rm2l`      | Multiple sink pins to lumped VRM pins. The resistance is extracted from each selected sink pin to a VRM with all its pins lumped together.          |
| `Rl2l`      | Lumped sink pins to lumped VRM pins. The resistance is extracted from the sink with all its selected pins lumped together to the lumped VRM.        |

A **sink** is where resistance is measured. It can be defined in either of two ways:

- Specify one single RefDes in `Positive_Main_Ports` and leave `Negative_Main_Ports`
  blank; or
- Specify a RefDes with its positive and negative pins in `Positive_Main_Ports` and
  `Negative_Main_Ports` respectively.

A **"VRM"** is a virtual concept here — it's the location where the power rail is shorted
to the ground rail so that the resistance can be measured for the whole loop. It must be
defined by specifying a RefDes with its positive and negative pins in
`Positive_Aux_Ports` and `Negative_Aux_Ports` respectively.

![image](/docs/Figures/input_sheet_DCR.png)

---

### Stackup and Materials (Mandatory)

Only one sheet, called `Stackup_Materials`, is needed. Its sections are explained below.

| Section            | Type      | Description                                                                                                                                                                                                                                                                                     |
| ------------------ | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Materials`        | Mandatory | The keyword `Materials` must be placed in Col A. The following row must be `Name`, `Type`, `Conductivity (S/m)`, `Frequency (MHz)`, `Dk`, `Df` — **the sequence is critical!** Materials are defined from the second row after the keyword. `Type` can only be `Metal` or `Dielectric`.          |
| `SurfaceRoughness` | Optional  | The keyword `SurfaceRoughness` must be placed in Col A. The following row must be `Name`, `Type`, `SurfaceRatio/RoughnessFactor`, `SnowballRadius/RMSValue (um)` — **the sequence is critical!** Models are defined from the second row after the keyword. `Type` must be one of `Huray`, `ModifiedHammerstad`, or `ModifiedGroisse`. Model names are insignificant. |
| `Stackup`          | Mandatory | The layer stack-up. See the keyword table below.                                                                                                                                                                                                                                                |

> [!TIP]
> Material names should not matter in principle, but some weird issues have been observed
> when the solver reads the material info. Prefer names that differ from those already
> existing in the design file.

**`Stackup` keywords**

| Keyword                    | Type      | Description                                                                     |
| -------------------------- | --------- | ------------------------------------------------------------------------------- |
| `Layer_Name`               | Mandatory | Unique layer names.                                                             |
| `Thickness_mm`             | Mandatory | Layer thickness in mm.                                                          |
| `Material`                 | Mandatory | Material names defined in section `Materials`.                                  |
| `Op_Layer_Number`          | Optional  | Layer number, for display only.                                                 |
| `Op_Fillin_Dielectric`     | Optional  | Material names defined in section `Materials`.                                  |
| `Op_Roughness_Upper`       | Optional  | Upper surface roughness defined in section `SurfaceRoughness`.                  |
| `Op_Roughness_Lower`       | Optional  | Lower surface roughness defined in section `SurfaceRoughness`.                  |
| `Op_Roughness_Side`        | Optional  | Side surface roughness defined in section `SurfaceRoughness`.                   |
| `Op_Trapezoidal_Angle_deg` | Optional  | Trapezoidal angle of the trace cross-section. Omitting a value implies 90 deg.  |

An example is shown below.

![image](/docs/Figures/stackup_materials.png)

### Special Settings (Mandatory)

Only one sheet, called `Special_Settings`, is needed. Its keywords are explained below.

| `Setting_key`       | `Setting_value`                                                                             | Type      | Description                                                                                                                                                                     |
| ------------------- | ------------------------------------------------------------------------------------------- | --------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ExtractionTool`    | `Sigrity`                                                                                   | Mandatory | Plan to support ANSYS in the future.                                                                                                                                            |
| `ExtractionType`    | `PDN` / `HSIO` / `LSIO` / `DCR`                                                             | Mandatory | Four types are available so far.                                                                                                                                                |
| `DesignType`        | `PCB` / `PKG`                                                                               | Mandatory | This affects some tool settings like mesh resolution etc.                                                                                                                       |
| `ProjectName`       | Any name works                                                                              | Mandatory | Preferably the same as the project folder name.                                                                                                                                 |
| `GrowTopSolder`     | RefDes on top layer, solder height in mm, solder radius in mm                               | Optional  | Only one RefDes is allowed.                                                                                                                                                     |
| `GrowBotSolder`     | RefDes on bottom layer, solder height in mm, solder radius in mm                            | Optional  | Only one RefDes is allowed.                                                                                                                                                     |
| `FEMPortSolder`     | `Refdes1, height mm, radius mm; Refdes2, height mm, radius mm; ...`                         | Optional  | Only for HSIO extraction.                                                                                                                                                       |
| `RefDesOffsetNodes` | `Refdes1, node offset in mm; Refdes2, node offset in mm; ...`                               | Optional  | Lists the RefDes whose nodes shall be offset in mm.                                                                                                                             |
| `BOM`               | Use `\n`, `,`, or `;` to separate RefDes                                                    | Optional  | BOM lists all stuffed components. Components not included are DNSed and should be disabled during sims.                                                                         |
| `GlobalFreq`        | `FREQ_START, FREQ_END, FREQ_STEP, FREQ_SOL`                                                 | Optional  | Simulation frequency for the whole run. Second-highest priority — it applies only when `Op_Freq` is not defined for the `Unique_Key`. See [Frequency priority](#frequency-priority). |
| `CapRefDes`         | Use `,` to separate them                                                                    | Optional  | The starting RefDes keywords indicating capacitors in a design. `C` is the implied default.                                                                                     |
| `GlobalPreCut`      | Use `,` to separate `LLX, LLY, URX, URY` in mm                                              | Optional  | Precut the board outside the provided rectangle.                                                                                                                                |

### Spec Type (Optional)

If it exists, the sheet called `Spec_Type` provides user-defined spec types. Its keywords
are explained below.

| Name               | Description                                                                                                                | Format                                                                                     |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `Spec_Type`        | User-defined spec type names.                                                                                              | Any continuous string.                                                                     |
| `Freq`             | Frequency info related to the user-defined spec type.                                                                      | `FREQ_START, FREQ_END, FREQ_STEP, FREQ_SOL` — see [Frequency priority](#frequency-priority).|
| `Post_Process_Key` | Post-processing info related to the user-defined spec type. A list of pre-defined keywords identifying the required actions.| Use `,` to separate pre-defined post-processing keywords.                                  |

**Post-processing keywords for PDN**

| Keyword  | Description                                          |
| -------- | ---------------------------------------------------- |
| `ZOPEN`  | Z-para post-processing with auxiliary ports open.    |
| `ZSHORT` | Z-para post-processing with auxiliary ports shorted. |

**Post-processing keywords for HSIO and LSIO**

| Keyword  | Description                                                        |
| -------- | ------------------------------------------------------------------ |
| `IL`     | Insertion loss for single-ended S-para.                            |
| `RL`     | Return loss for single-ended S-para.                               |
| `TDR`    | Time-domain characteristic impedance plot for single-ended S-para. |
| `IL_MM`  | Insertion loss for mixed-mode S-para.                              |
| `RL_MM`  | Return loss for mixed-mode S-para.                                 |
| `TDR_MM` | Time-domain characteristic impedance plot for mixed-mode S-para.   |

An example is shown below.

![image](/docs/Figures/spec_type_tab.png)

---

## Simulation Output

All output of a run lands under `Xtract/Run_[time_stamp]/` — see
[Mid-layer Platform](/docs/Home/Mid-layer-Platform.md) for the full folder structure.

| Output                        | Format            | Location                |
| ----------------------------- | ----------------- | ----------------------- |
| S-parameters                  | Touchstone `.sNp` | `Result/SNP_S/`         |
| S-parameters, DC-fitted       | Touchstone `.sNp` | `Result/SNP_DCfitted/`  |
| DCR results                   | CSV               | `Result/`               |
| Plots and the summary report  | PDF               | `Report/`               |
