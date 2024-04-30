# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

# port list info from gSheet
set port_list {
COMP_NETS_LISTS
}
# rename ports
set wrong_port_seq 0
for {set i 0} {$i < [llength $port_list]} {incr i} {
	set port_info [sigrity::querydetails port -index $i]
	set port_name [lindex $port_info 0]
	set net_name [lindex $port_info 3]
	set port_name_parts [split $port_name _]
	set comp_name [lindex $port_name_parts 1]
	set port_index 1
	foreach list $port_list {
		if {($comp_name in $list)&&($net_name in $list)} {
			set port_new_name "Port_"
			append port_new_name $port_index
			set port_new_index $port_index
			sigrity::update port -name $port_name -NewName $port_new_name {!}
			continue
		}
		incr port_index
	}
	if {$port_new_index!=[expr $i+1]} {
		set wrong_port_seq 1
	}
}
# re-order port indices
if {$wrong_port_seq} {
	sigrity::Rearrange PortOrder -PortName {PORT_NAME_SEQ} -Index {PORT_NAME_INDEX} {!}
}
