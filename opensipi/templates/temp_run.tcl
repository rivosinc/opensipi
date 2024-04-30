# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

# Template created by Yansheng Wang
# Sep. 14, 2022

#==============================================================================
#
#==============================================================================
set run_key_array {
SIM_KEY
}

foreach run_key $run_key_array {
	set run_done "SIM_DIR"
	append run_done $run_key ".done"
	if {[file exists $run_done] == 0} {
		# open the .spd file created during model check process
		set spd_path "CK_DIR"
		append spd_path $run_key "__SIM_DATE.spd"
		sigrity::open document $spd_path {!}
		# save file to SimFile directory
		set sim_spd "SIM_DIR"
		append sim_spd $run_key "__SIM_DATE.spd"
		sigrity::save $sim_spd {!}
		sigrity::begin simulation {!}
		sigrity::save $sim_spd {!}
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
