# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

# multi-terminal circuits
set layer_info [sigrity::querydetails layer -index {LAYERINDEX}]
set layer_name [lindex $layer_info 0]
set comp [sigrity::query -CktInstance -option "Type(good) Layer($layer_name)"]
if {$comp != ""} {
	foreach i_comp $comp {
		sigrity::add multiTerminal -circuit $i_comp -direction {ORIENTATION} -UsePadSizeAsDiameter {RATIO} -height {SBH} -conductivity {7e+06} -RefLayerThickness {0.000002} {!}
	}
}
