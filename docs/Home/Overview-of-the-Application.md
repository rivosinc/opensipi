<!--
SPDX-FileCopyrightText: 2024 Rivos Inc.

SPDX-License-Identifier: Apache-2.0
-->

![OpenSIPI_Overview](Figures/OpenSIPI_Overview.png)

The complete application can be treated as three layers:
- Front-end files IO

  The input information used to set up simulations and guide post-processing has to be provided in tables following specific formats. Please refer to [Front-end Files IO](Home/Front-end-Files-IO.md) for more details.
  The output results are in touchstone (S-parameter snp files) or csv (DCR) format. A summary report is created in a PDF format.
- Mid-layer platform

  This is all about this package OpenSIPI.
- Back-end simulation solvers

  The users have to install and purchase licenses for the desired simulation solvers separately.
