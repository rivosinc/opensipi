# SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
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


# querying RefDes NetName pins
proc get_refdes_pins_per_net {refdes netname} {
    set qryopt ""
    append qryopt "{object("
    append qryopt $refdes
    append qryopt ") ConnNet("
    append qryopt $netname
    append qryopt ")}"
    set pinname [eval sigrity::query -cktNode -option $qryopt]
    return $pinname
}


# querying nearby gnd pins within a certain radius of RefDes+PosNet pins
proc get_nearby_gnd_pins_per_refdes_n_posnet {refdes posnet negnet radius tgtlayer} {
	set node_name ""
    set refdes_net_pin [get_refdes_pins_per_net $refdes $posnet]
    foreach current_pin $refdes_net_pin {
        set node_name_temp [eval sigrity::querydetails node -refcircuit {$refdes} -refpin {$current_pin}]
        lappend node_name $node_name_temp
    }
    foreach node $node_name {
		set node_details [eval sigrity::querydetails node -name $node]
		lappend x_coord [lindex $node_details 1]
		lappend y_coord [lindex $node_details 2]
	}

    set x_min_temp [heapsort $x_coord]
	set y_min_temp [heapsort $y_coord]

	set x_max_temp [heapsort $x_coord]
	set y_max_temp [heapsort $y_coord]

	set x_min [lindex $x_min_temp 0]
	set y_min [lindex $y_min_temp 0]

	set index_max_x ""
	set index_max_x [llength $x_max_temp]
	set index_max_x [expr ($index_max_x - 1)]

	set index_max_y ""
	set index_max_y [llength $y_max_temp]
	set index_max_y [expr ($index_max_y - 1)]

	set x_max [lindex $x_max_temp $index_max_x]
	set y_max [lindex $y_max_temp $index_max_y]

	set x_center ""
	set y_center ""

	set x_center [expr {($x_max + $x_min)/2}]
	set y_center [expr {($y_max + $y_min)/2}]

    set center ""
	append center $x_center "m, " $y_center "m"
	set center_node [eval "sigrity::add node -P \{$center\} -LY \{$tgtlayer\}"]
	eval "sigrity::add circuit -byPinBased -node $center_node"
	eval "sigrity::add -portName \{Dummy\} -posCktNode \{NewEmptyCkt1::1\} -negNodeDistance $radius -refNet $negnet"
	set port_details [sigrity::querydetails port -name {Dummy}]
	set gnd_node_index ""
	set gnd_node_index [llength $port_details]
	set gnd_node_index [expr $gnd_node_index - 1]
	set number_gnd_nodes [lindex $port_details $gnd_node_index]
	set number_gnd_nodes [expr $number_gnd_nodes - 1]
	set nodes_list ""
	set gnd_node_index 1
	while {$gnd_node_index <= $number_gnd_nodes} {
		set current_node [eval "sigrity::querydetails port -name \{Dummy\} -nodeindex $gnd_node_index"]
		set current_node [lindex $current_node 0]
		lappend nodes_list $current_node
		incr gnd_node_index
	}

	sigrity::delete port -port {Dummy}
    sigrity::delete cktlink -cktlink {NewEmptyCkt1}

    return $nodes_list
}


proc heapsort {list {count ""}} {
    if {$count eq ""} {
	set count [llength $list]
    }
    for {set i [expr {$count/2 - 1}]} {$i >= 0} {incr i -1} {
	siftDown list $i [expr {$count - 1}]
    }
    for {set i [expr {$count - 1}]} {$i > 0} {} {
	swap list $i 0
	incr i -1
	siftDown list 0 $i
    }
    return $list
}


proc siftDown {varName i j} {
    upvar 1 $varName a
    while true {
	set child [expr {$i*2 + 1}]
	if {$child > $j} {
	    break
	}
	if {$child+1 <= $j && [lindex $a $child] < [lindex $a $child+1]} {
	    incr child
	}
	if {[lindex $a $i] >= [lindex $a $child]} {
	    break
	}
	swap a $i $child
	set i $child
    }
}


proc swap {varName x y} {
    upvar 1 $varName a
    set tmp [lindex $a $x]
    lset a $x [lindex $a $y]
    lset a $y $tmp
}
