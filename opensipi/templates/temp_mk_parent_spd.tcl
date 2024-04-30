# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

# Template created by Yansheng Wang
# Sep. 14, 2022
# Last updated on Nov. 16, 2023

source {PROC_COMMON_TCL_DIR}
#==============================================================================
# Prepare the parent spd file
#==============================================================================
# do not automatically add bumps when importing mcm files
sigrity::spdif_option AddDefaultBumps {None} {!}
# load the design file
sigrity::open document {DSN_DIR} {!}
# create surface roughness models if any
CREATESRM
# import the materials.cmx file
sigrity::import material {MAT_DIR} {!}
# import the stackup.csv file
sigrity::import stackup {STACKUP_DIR} {!}
# import the option from team drive
sigrity::import option {OPTION_DIR} {!}
#==============================================================================
# Query nets
#==============================================================================
set all_nets [sigrity::query -net]
set outfile1 [open "NETINFO" w]
puts $outfile1 $all_nets
close $outfile1
#==============================================================================
# Query cktInstance(component) refdes
#==============================================================================
set all_comps [sigrity::query -cktInstance]
set outfile2 [open "COMPINFO" w]
puts $outfile2 $all_comps
close $outfile2
#==============================================================================
# Create new refdes for two-row pads with offset nodes
#==============================================================================
set refdes_array {REFDES_LIST}
foreach refdes_info $refdes_array {
    set refdes [lindex $refdes_info 0]
    set offset [lindex $refdes_info 1]
    create_refdes_for_two_row_pads_w_shifted_nodes $refdes $offset
}
#==============================================================================
# Grow solders
#==============================================================================
GRWSOLDER
#==============================================================================
# Save and exit
#==============================================================================
# save the parent spd file
sigrity::save {SPD_DIR} {!}
# export a log file to show the process is done
set done_file [open "RUN_DONE" w]
close $done_file
# exit PowerSI
sigrity::exit -nosave {!}
