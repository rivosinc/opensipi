<!--
SPDX-FileCopyrightText: 2024 Rivos Inc.

SPDX-License-Identifier: Apache-2.0
-->

# Introduction
The simulation input information is maintained in tables. The users can edit it in Excel, Google Sheet or equivalent tools.
The simulation results are either touchstone (snp) files for S-parameters or csv files for DCR results. A summary report in PDF format is typically created for the output results.
# Simulation Input
## File Formats
Currently only csv files can be read directly by the package. Plan to enable reading Google Sheet directly next step.
## Required Sheet Explained
Three different types of sheets are required as the simulation input files. They are introduced below.
### Simulation Setup and Post-Processing Info
These files contains all necessary information needed to set up simulations and post-process simulation results. The files' name starts with "Simx_" where x refers to integers 0, 1, 2 ... The user can have as many Sim sheets as possible. Sim sheets benefit the users to group simulations as desired.
#### Keyword Explained
| Key Words | Type | Descriptions |
| --------- | ---- | ------------ |
| Unique_Key | Mandatory | Simulation identifier. Each name given represents an individual simulation to be run. Any meaningful name can be assigned to this column but it must be unique in this sheet. The simulation file will be created with the name "Sim[x]_[Unique_Key]_[Run_Time]_[...].[File_Extension]". "Run_Time" is automatically assigned when the simulations start unless otherwise specified by the users. "File_Extension" refers to spd if using Sigrity tools. For 1-port or 2-port simulations, one row can store all the information needed to complete that simulations. For 2+ port simulations, multiple rows are needed to store all port information. Only the beginning row has to be assigned with a "Unique_Key". The subsequent rows with blank cells in Col A will be treated as for the same simulation. |
| Check_Box | Mandatory | Simulation enable pin. "True" or "False". It could be presented as a check box in Excel or Google Sheets. |
| Spec_Type | Mandatory | It indicates the simulation frequency and the way to post-process simulation data. Only one spec type needs to be assigned at the beginning row of a simulation info. Currently, the available spec type will be introduced in the next section. Note that the indicated simulation frequency takes the lowest priority, i.e. it works only when "Op_Freq" is not defined per "Unique_Key" and "GlobalFreq" is not defined in the "Special_Settings" Tab. |
| Positive_Nets | Mandatory | Positive nets to be included in the simulation. Use "," to separate multiple nets. |
| Negative_Nets| Mandatory | Negative nets to be included in the simulation. Use "," to separate multiple nets. |
| Positive_Main_Ports | Mandatory | Refdes and its pins to set up the positive side of a port. Use "," to separate the refdes and its multiple pins. Area ports are also supported in PDN extraction: Rec{LLx, LLy, URx, URy, LayerName}. |
| Negative_Main_Ports | Mandatory | Refdes and its pins to set up the negative side of a port. Use "," to separate the refdes and its multiple pins. |
| Positive_Aux_Ports | Mandatory | Refdes and its pins to set up the positive side of a port. Use "," to separate the refdes and its multiple pins.  Area ports are also supported in PDN extraction: Rec{LLx, LLy, URx, URy, LayerName}. Aux ports of the obtained S-/Z-parameters may be shorted or open during post-processing based on the specified "Spec_Type". |
| Negative_Aux_Ports | Mandatory | Refdes and its pins to set up the negative side of a port. Use "," to separate the refdes and its multiple pins. Aux ports of the obtained S-/Z-parameters may be shorted or open during post-processing based on the specified "Spec_Type". |
| Op_Freq | Optional | Specify the simulation frequency per "Unique_Key". Once defined, it takes the highest priority. The format is "FREQ_START, FREQ_END, FREQ_STEP, FREQ_SOL", where first two items are mandatory for PDN, first three items are mandatory for LSIO, and all are mandatory for HSIO "ExtractionType". |
| Op_DiffPair | Optional | Specify the differential pairs for LSIO and HSIO "ExtractionType". |
| Op_DisAllCaps | Optional | Cap models are automatically included in extractions without specifying any characters for this keyword. By providing any non-empty characters for this keyword per "Unique_Key", caps are disabled for simulations. |

Ports are indexed top to bottom of main ports and then top to bottom of auxiliary ports.

#### Allowed Formats per Extraction Type
The best way to explain the allowed formats is through examples.

- PDN

Let's start with a PDN example. I want to simulate the PDN response of a few power planes in a PCB, i.e. P0V9 and P1V8. Looking at its schematic, PP0V9 starts from the inductor Pin 2 of PL11 and ends at multiple BGA pins (R11, R13, R15 etc.) of U1. I want to set up one port at U1 and one port at the inductor PL11. The right way to implement it is shown in the 2nd row of the table below. I only put a refdes in the "Postive_Main_Ports" and leave "Negative_Main_Ports" blank. This means I will set up a port at U1 with positive pins defined by all U1's pins connected to the "Positive_Nets" and negative pins defined by all U1's pins connected to the "Negative_Nets". I put "PL11, 2" in "Positive_Aux_Ports" and "PC592, 2" in "Negative_Aux_Ports". This means I  will create a port with its positive pins defined by Pin 2 of PL11 and its negative pins defined by Pin 2 of PC592.

![image](/docs/Figures/P0V9_VRM.png)

![image](/docs/Figures/P1V8_VRM.png)

![image](/docs/Figures/SoC_PDN.png)

In another case with P1V8 power rail, which starts from Pin 2 of PL8 and ends at multiple pins (N6, T7, N18 etc.) of U1, I want to set up two ports at U1 and one port at PL8. The two ports at U1 are for two groups of pins, i.e. Group 1 containing N6, T7, N18 and Group 2 containing U12, T17, J17, J12, K7. The right way to set it up is shown in the table below from Row 3 to 4. I put "U1, N6, T7, N18" in Row 3 Col "Positive_Main_Ports". Group 1 pins N6, T7 and N18 of the RefDes U1 are set to be the positive pins of Port 1. You can define multiple pins of U1 which are connected to the "Negative_Nets" in "Negative_Main_Ports" in a format as "RefDes, Pin# ...". But if you want to easily set all U1 pins connected to the "Negative_Nets" as the negative pins of Port 1, you can simply put "U1, Lumped" in "Negative_Main_Ports". Port 2 and 3 are easy to understand.

![image](/docs/Figures/input_sheet_PDN.png)

Rectangle area port is also supported for PDN extraction. To define an area port, use the following format "Rec{LLx, LLy, URx, URy, LayerName}" and put it in "Positive_Main_Ports" or "Positive_Aux_Ports", meanwhile leaving its negative counterpart blank. "Rec" is a keyword that cannot be changed. "LLx": x-coordinate of the lower-left corner; "LLy": y-coordinate of the lower-left corner; "URx": x-coordinate of the upper-right corner; "URy": y-coordinate of the upper-right corner; "LayerName": the actual layer name where the area port is defined. Notice the area port is only defined between the FIRST listed positive and negative nets.

- LSIO

| Key Words | Descriptions |
| --------- | ------------ |
| Spec_Type | Sls: default simulation frequency ranges from 1 MHz to 5 GHz with a step size of 5 MHz. |
| Positive_Nets | Each row lists all positive nets that are connected to the ports defined in the same row. Use "," to separate nets. The rows in the same Sim_Key cannot be merged. The nets can be duplicated among different rows in the same Sim_Key. |
|Negative_Nets | Each row lists all negative nets that are connected to the ports defined in the same row. Use "," to separate nets. The rows in the same Sim_Key cannot be merged. The nets can be duplicated among different rows in the same Sim_Key. |
| Positive_Main_Ports | RefDes, Positive pins |
| Negative_Main_Ports | RefDes, Negative pins |
| Positive_Aux_Ports | RefDes, Positive pins |
| Negative_Aux_Ports | RefDes, Negative pins |

Notice the port definition must be "RefDes+Pins" for both positive and negative sides.

The ports are indexed from "Main" to "Aux" and top to bottom. For example, the port sequence in the 2nd test case as shown below, "I2C_PCA9548_SC6", is

Port1: +(U2, 18) -(U2, 12)

Port2: +(U2, 17) -(U2, 12)

Port3: +(U4, 8) -(U4, 5)

Port4: +(U10, 10) -(U10, 6)

Port5: +(U7, 6) -(U7, 4)

Port6: +(U9, 9) -(U9, 4)

Port7: +(U4, 7) -(U4, 5)

Port8: +(U10, 9) -(U10, 6)

Port9: +(U7, 5) -(U7, 4)

Port10: +(U9, 8) -(U9, 4)

![image](/docs/Figures/input_sheet_LSIO.png)

- HSIO

| Key Words | Descriptions |
| --------- | ------------ |
| Spec_Type | Sddr5: default simulation frequency ranges from 1 MHz to 15 GHz with a step size of 100 MHz. The solution frequency is set to 5 GHz. <br> Spcie6: default simulation frequency ranges from 1 MHz to 50 GHz with a step size of 100 MHz. The solution frequency is set to 16 GHz. |
| Positive_Nets | Each row lists all positive nets that are connected to the ports defined in the same row. Use "," to separate nets. The rows in the same Sim_Key cannot be merged. The nets can be duplicated among different rows in the same Sim_Key. |
|Negative_Nets | Each row lists all negative nets that are connected to the ports defined in the same row. Use "," to separate nets. The rows in the same Sim_Key cannot be merged. The nets can be duplicated among different rows in the same Sim_Key. |
| Positive_Main_Ports | RefDes only |
| Negative_Main_Ports | Blank |
| Positive_Aux_Ports | RefDes only |
| Negative_Aux_Ports | Blank |

The port setup currently only takes RefDes. This assumes the component only has one pin connecting to the enabled nets, which is typically true. But there is a loophole if the assumption doesn't hold. Will look into this in the future.

![image](/docs/Figures/input_sheet_HSIO.png)

- DCR

| Key Words | Descriptions |
| --------- | ------------ |
| Spec_Type | Rm2l, Rl2l |
| Positive_Main_Ports | Sink positive pins |
| Negative_Main_Ports | Sink negative pins |
| Positive_Aux_Ports | "VRM" positive pins |
| Negative_Aux_Ports | "VRM" negative pins |

For DCR extraction, currently only two "Spec_Type" are supported, i.e. "Rm2l" and "Rl2l". "Rm2l" refers to a setup of multiple sink pins to lumped VRM pins. The resulting resistance is extracted from each of selected sink pins to a VRM with all its pins lumped together. "Rl2l" refers to a setup of lumped sink pins to lumped VRM pins. The resulting resistance is extracted from the sink with all its selected pins lumped together to VRM with all its pins lumped together.

A sink is where resistance is measured. The sink can be defined either of the following ways. You can specify one single RefDes in "Positive_Main_Ports" and leave "Negative_Main_Ports" blank. Or you can specify RefDes with its positive and negative pins in "Positive_Main_Ports" and "Negative_Main_Ports", respectively.

A "VRM" is a virtual concept here. It's the location where power rail is shorted to ground rail so that the resistance can be measured for the whole loop. The "VRM" must be defined as follows. The user has to specify RefDes with its positive and negative pins in "Positive_Aux_Ports" and "Negative_Aux_Ports", respectively.

![image](/docs/Figures/input_sheet_DCR.png)

### Stackup and Materials
Only one file called stackup_material is needed. The keywords in this sheet is explained below.
| Section Name | Type | Descriptions |
| ------------ | ---- | ------------ |
| Materials | Mandatory | The key word "Materials" must be place in Col A. The following row should be "Name", "Type", "Conductivity (S/m)", "Frequency (MHz)", "Dk", and "Df". The sequence is critical here! Materials are defined from the second row after the key word. The material names should not be critical ideally. But I do see some weird issues happened when the solver reading the material info. It's preferred to use names differing from those already existing in the design files. "Type" can only be "Metal" or "Dielectric" |
| SurfaceRoughness | Optional | The key word "SurfaceRoughness" must be placed in Col A. The following row should be "Name", "Type", "SurfaceRatio/RoughnessFactor", and "SnowballRadius/RMSValue (um)". The sequence is critical here! Surface roughness models are defined from the second row after the key word. The model names are insignificant. The Type has to be one of the three, "Huray", "ModifiedHammerstad", or "ModifiedGroisse". |
| Stackup | Mandatory | Available keywords are:<br><ul><li>Layer_Name: (mandatory) unique layer names</li><li>Thickness_mm: (mandatory) layer thickness in mm</li><li>Material: (mandatory) matertial names defined in Section "Materials"</li><li>Op_Layer_Number: (optional) layer number for display only</li><li>Op_Fillin_Dielectric: (optional) material names defined in Section "Materials"</li><li>Op_Roughness_Upper: (optional) upper surface roughness defined in Section "SurfaceRoughness"</li><li>Op_Roughness_Lower: (optional) lower surface roughness defined in Section "SurfaceRoughness"</li><li>Op_Roughness_Side: (optional) side surface roughness defined in Section "SurfaceRoughness"</li></ul>|

An example is shown below.
![image](/docs/Figures/stackup_materials.png)

### Special Settings
Only one file called special_settings is needed. The keywords in this sheet is explained below.
| Setting_key| Setting_value | Type | Descriptions |
| ---------- | ------------- | ---- | ------------ |
| ExtractionTool | Sigrity | Mandatory | Plan to support ANSYS in the future |
| ExtractionType | PDN/HSIO/LSIO/DCR | Mandatory | Four types are available so far |
| DesignType | PCB/PKG | Mandatory | This affects some tool settings like mesh resolution etc. |
| ProjectName | Any name works | Mandatory | But preferably to be the same as the project folder name. |
| GrowTopSolder | Refdes on top layer, solder height in mm, solder radius in mm | Optional | Only one refdes is allowed. |
| GrowTopSolder | Refdes on top layer, solder height in mm, solder radius in mm | Optional | Only one refdes is allowed. |
| FEMPortSolder | Refdes1, solder height in mm, solder radius in mm; Refdes2, solder height in mm, solder radius in mm ... | Optional | Only for HSIO extraction. |
| RefDesOffsetNodes | Refdes1, node offset in mm; Refdes2, node offset in mm ... | Optional | It lists the RefDes whose nodes shall be offset in mm. |
| BOM | Use '\n', ',', or ';' to separate refdes | Optional | BOM lists all stuffed components. Those not included components are DNSed and should be disabled during sims. |
| GlobalFreq | FREQ_START, FREQ_END, FREQ_STEP, FREQ_SOL | Optional | Specify the simulation frequency globally. Once defined, it takes the 2nd priority, i.e. it works only when "Op_Freq" is not defined per "Unique_Key". The format is "FREQ_START, FREQ_END, FREQ_STEP, FREQ_SOL", where first two items are mandatory for PDN, first three items are mandatory for LSIO, and all are mandatory for HSIO "ExtractionType". |
| CapRefDes | Use ',' to separate them | Optional | The starting RefDes keywords to indicate capacitors in a design. "C" is the implied default one. |

# Simulation Output
