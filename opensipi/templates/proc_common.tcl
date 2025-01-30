# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

# Create a new refdes based on an existing one but with shifted nodes
# The shape of the existing component must be rectangular
# The componet must have two rows of pads
proc create_refdes_for_two_row_pads_w_shifted_nodes {refdes offset} {
    set ckt_info [sigrity::querydetails ckt -name $refdes]
    set ckt_bbox [lindex $ckt_info 5]
    set ckt_center [lindex $ckt_info 4]
    set ckt_center_x [string trim [lindex $ckt_center 0] ","]
    set ckt_center_y [string trim [lindex $ckt_center 1] ","]
    # determine offset direction
    set ckt_bbox_xmax [string trim [lindex $ckt_bbox 2] ","]
    set ckt_bbox_xmin [string trim [lindex $ckt_bbox 0] ","]
    set ckt_bbox_ymax [string trim [lindex $ckt_bbox 3] ","]
    set ckt_bbox_ymin [string trim [lindex $ckt_bbox 1] ","]
    set ckt_size_x [expr $ckt_bbox_xmax-$ckt_bbox_xmin]
    set ckt_size_y [expr $ckt_bbox_ymax-$ckt_bbox_ymin]
    if {$ckt_size_x>$ckt_size_y} {
        set offset_dir y
    } else {
        set offset_dir x
    }
    # add new nodes
    set ckt_nodes [sigrity::querydetails node -refcircuit $refdes]
    set all_new_node_names ""
    foreach node $ckt_nodes {
        set node_info [sigrity::querydetails node -refcircuit $refdes -name $node]
        set node_x [lindex $node_info 1]
        set node_y [lindex $node_info 2]
        set node_layer [lindex $node_info 3]
        if {$offset_dir=="x"} {
            if {$node_x<[expr $ckt_center_x-$offset]} {
                set new_node_x [expr $node_x+$offset]
            } elseif {$node_x>[expr $ckt_center_x+$offset]} {
                set new_node_x [expr $node_x-$offset]
            } else {
                set new_node_x $node_x
            }
            set new_node_y $node_y
        } else {
            if {$node_y<[expr $ckt_center_y-$offset]} {
                set new_node_y [expr $node_y+$offset]
            } elseif {$node_y>[expr $ckt_center_y+$offset]} {
                set new_node_y [expr $node_y-$offset]
            } else {
                set new_node_y $node_y
            }
            set new_node_x $node_x
        }
        set new_node_name [sigrity::add node -point "$new_node_x, $new_node_y" -layer $node_layer]
        append all_new_node_names "\{" $new_node_name "\} "
    }
    # rename the orignal component
    sigrity::update circuit -name "${refdes}_raw" $refdes {!}
    # create a new component
    eval "sigrity::add circuit {} -byPinBased -node $all_new_node_names"
    sigrity::update circuit -name $refdes {NewEmptyCkt1} {!}
}


# Check and turn off the DNS components during sims
# components those are not found in the BOM list are treated as DNSed.
proc turn_off_dns_ckt {refdes_en bom} {
    foreach refdes $refdes_en {
        if {![dict exists $bom $refdes]} {
            sigrity::update circuit -manual {disable} $refdes {!}
        }
    }
}


# split the component if it's double sided
proc split_component { refdes } {
	set refdes_list $refdes
	set comp_details [sigrity::querydetails ckt -name $refdes]
	set model_name [lindex $comp_details 1]
	set layer1 [lindex $comp_details 6]
	set layer2 [lindex $comp_details 7]
	set node_details [sigrity::querydetails node -refcircuit $refdes]
	if { $layer2 != ""} {
		set node_grp1 {}
		set node_grp2 {}
		# separate node groups
		foreach node $node_details {
			set node_name [lindex $node 0]
			set node_layer [lindex [sigrity::querydetails node -name $node] 3]
			set node_pin [lindex [wsplit [lindex [wsplit $node_name "!!"] 1] "::"] 0]
			if { $node_layer == $layer1 } {
				lappend node_grp1 "$node_pin $node_name"
			} else {
				lappend node_grp2 "$node_pin $node_name"
			}
		}
		# create ckt componets
		set refdes1 "${refdes}_Layer_$layer1"
		create_new_ckt $refdes1 $model_name $node_grp1
		set refdes2 "${refdes}_Layer_$layer2"
		create_new_ckt $refdes2 $model_name $node_grp2
		set refdes_list "$refdes1 $refdes2"
	}
	return $refdes_list
}


# create ckt component
proc create_new_ckt {refdes model_name node_grp} {
	sigrity::add circuit $refdes -def $model_name {!}
	sigrity::select $refdes {!}
	foreach node $node_grp {
		sigrity::link $refdes [lindex $node 0] [lindex $node 1] {!}
	}
}


# turn off all enabled caps
proc turn_off_all_enabled_caps {} {
    set good_caps [sigrity::query -CktInstance -option {modeltype(C) type(Good)}]
    eval "sigrity::update circuit -manual {disable} $good_caps"
}


# split a string by a substring
proc wsplit {rawstr substr} {
  split [string map [list $substr \0] $rawstr] \0
}
