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
