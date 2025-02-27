# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

# Template created by Yansheng Wang
# Sep. 14, 2022
# Last updated on Feb. 5, 2025

source {PROC_COMMON_TCL_DIR}
source {BOM_TCL_DIR}
#==============================================================================
#
#==============================================================================
set run_key_array {
SIM_KEY
}

set capkeys {
CAP_KEY
}

foreach run_key $run_key_array {
	set run_done "SIM_DIR"
	append run_done $run_key ".done"
	if {[file exists $run_done] == 0} {
		# open the parent .spd file
		sigrity::open document {SPD_DIR} {!}
		# assign components from the amm library
		sigrity::open ammLibrary {AMM_DIR} {!}
		sigrity::assign -all {!}
		# sim directory
		set sim_spd "SIM_DIR"
		append sim_spd $run_key "__SIM_DATE" ".spd"
		# enable nets and set up ports for each run_key
		set run_key_file "RUN_KEY_DIR"
		append run_key_file "key_" $run_key ".tcl"
		source $run_key_file
		# save file to SimFile directory
		sigrity::save $sim_spd {!}
		# real sims: RUN_SIM will be changed to true
		# model check: RUN_SIM will be changed to false
		if {RUN_SIM} {
			sigrity::begin simulation {!}
			sigrity::save $sim_spd {!}
		}
		# export port and cap info
		if {EXPORT_PORT} {
			set port_info "SIM_DIR"
			append port_info "Ports_" $run_key ".csv"
			sigrity::export Ports -FileName $port_info {!}

			set refdes_all ""
			foreach posnet $pos_nets {
				append refdes_all " " [sigrity::query -cktinstance -option "ConnNet($posnet)"]
			}
			set good_comps [sigrity::query -CktInstance -option {type(Good)}]

			set cap_all ""
			set good_caps ""
			foreach ckey $capkeys {
				append cap_all " " [lsearch -all -inline -nocase $refdes_all $ckey*]
				append good_caps " " [lsearch -all -inline -nocase $good_comps $ckey*]
			}

			set cap_info ""
			foreach cap $cap_all {
				if {$cap in $good_caps} {
					set cap_details [sigrity::querydetails ckt -name $cap]
					set cap_model_info [sigrity::querydetails cktModel -name [lindex $cap_details 1]]
					set cap_model [lindex $cap_model_info 4]
					append cap_info "$cap,\"$cap_model\","
				} else {
					append cap_info "$cap,No Models,"
				}
			}

			set cap_csv "SIM_DIR"
			append cap_csv "Caps_" $run_key ".csv"
			set outfile [open $cap_csv w]
			puts $outfile $cap_info
			close $outfile
		}
		# flag run_key is done
		set done_file [open $run_done w]
		close $done_file
	}
}
# export a log file to show the whole process is done
set done_file [open "RUN_DONE" w]
close $done_file
# exit
sigrity::exit -nosave {!}
