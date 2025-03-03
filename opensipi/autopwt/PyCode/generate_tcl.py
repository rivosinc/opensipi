# SPDX-FileCopyrightText: © 2025 Google LLC
#
# SPDX-License-Identifier: Apache-2.0

"""generate simulation tcl files"""
import os
import shutil
from PyCode.utility import pwt_msgbox_print as msgbox


def generate_apply_stackup_tcl(sim_info):
    """ Create material library. """
    sim_run_folder_path = sim_info['sim_run_folder_path']
    # Result_folder_path=sim_info.Result_folder_path
    brd_file_path = sim_info['brd_file_path']
    # PWT_path=sim_info.PWT_path
    library_path = sim_info['library_path']
    pwt_msgbox = sim_info['msgbox']
    stackupfile_path = sim_info['stackupfile_path']
    materialfile_path = sim_info['materialfile_path']

    brd_name = os.path.splitext(os.path.basename(brd_file_path))[0]
    save_spd_name = os.path.join(sim_run_folder_path, brd_name+'.spd')
    tcl_file_path = os.path.join(sim_run_folder_path, '_', brd_name, '_apply_stackup.tcl')

    try:
        with open(tcl_file_path, 'w', encoding='utf-8') as file:
            # generate the tcl file

            file.write(r'#==================set folder path variable==============' + '\n')
            file.write(f'set sim_run_path {{{sim_run_folder_path}}}' + '\n')

            file.write(
                r'#==================OPEN PowerDC before running scripts===========' + '\n')
            file.write(r'sigrity::open document {!}' + '\n')

            file.write(
                r'#==================applying some powerDC sim settings============' + '\n')
            file.write(r'sigrity::set pdcAccuracyMode {1} {!}' + '\n')
            file.write(r'sigrity::update option -AutoSaveSignOffReport {0} {!}' + '\n')
            file.write(r'sigrity::update option -AutoSaveExcelResult {1} {!}' + '\n')
            file.write(r'sigrity::set pdcAutoSaveExcelResult -fileFormat {.csv} {!}' + '\n')
            file.write(r'sigrity::update option -MaxCPUPer {90} {!}' + '\n')
            file.write(r'#Translator options' + '\n')  # translator options
            file.write(r'sigrity::spdif_option TranslateAntipadsAsVoids {1} {!}' + '\n')
            file.write(r'sigrity::spdif_option CreateModelByPartNumber {1} {!}' + '\n')
            file.write(r'sigrity::spdif_option ConvertStaticShape {1} {!}' + '\n')
            file.write(r'sigrity::spdif_option RemoveNonFunctionalPads {0} {!}' + '\n')
            file.write(r'sigrity::debug SetMsgWarnByTimer {FALSE}' + '\n')  # ignore the warning

            file.write(r'#==================OPEN brd file==========================' + '\n')
            file.write(f"sigrity::open document {{{brd_file_path}}}" + r' {!}' + '\n')

            file.write(r'#==========apply Mesh options==============' + '\n')  # mesh options
            file.write(
                r'sigrity::update option -DoglegHoleThreshold {0.0001} '
                r'-ThermalHoleThreshold {0.0001} {!}' + '\n')
            file.write(
                r'sigrity::update option -SmallHoleThreshold {0.0001} '
                r'-ViaHoleThreshold {0.0001} {!}' + '\n')
            file.write(r'sigrity::update option -MaxEdgeLength {0.002000} {!}' + '\n')
            file.write(r'sigrity::process shape {!}' + '\n')

            if os.path.exists(stackupfile_path):
                file.write(
                    r'#==================apply stackup and material================' + '\n')
                file.write(f"sigrity::import material {{{materialfile_path}}}" + r' {!}' + '\n')
                file.write(
                    f"sigrity::update material {{{materialfile_path}}}" + r' -all {!}' + '\n')
                file.write(f"sigrity::import stackup {{{stackupfile_path}}}" + r' {!}' + '\n')

            file.write(r'# ======================Remove all net alias=================' + '\n')
            file.write(r'set all_nets [sigrity::query -net]' + '\n')
            file.write(r'set catch_count 0' + '\n')
            file.write(r'foreach net $all_nets {' + '\n')
            file.write(
                '\t'+r'if {[catch {[eval "sigrity::update net NotAsAlias {$net}"]}]} '
                r'{incr catch_count}}' + '\n')

            file.write(r'#==================load and apply amm library===============' + '\n')
            file.write(f"sigrity::open ammLibrary {{{library_path}}}" + r' {!}' + '\n')
            file.write(r'sigrity::assign -all {!}' + '\n')

            file.write(
                r'#==================save spd file and results file================' + '\n')
            file.write(f"sigrity::save {{{save_spd_name}}}" + r' {!}' + '\n')

            file.write(r'#==================exit PowerSI==================' + '\n')
            file.write(r'sigrity::exit -nosave | -n {!}' + '\n')
            msgbox(pwt_msgbox, "Main tcl script is generated successfully")
            return tcl_file_path, save_spd_name
    except RuntimeError as e:
        msgbox(pwt_msgbox, f"An error occurred when generating the tcl script: {str(e)}")


def generate_single_ir_tcl(sim_info):
    """ Create material library. """
    sim_run_folder_path = sim_info['sim_run_folder_path']
    # Result_folder_path=sim_info['Result_folder_path']
    brd_file_path = sim_info['brd_file_path']
    pwt_path = sim_info['PWT_path']
    library_path = sim_info['library_path']
    pwt_msgbox = sim_info['msgbox']
    report_htm_path = sim_info['Report_htm_path']
    # Report_htm_path='Simulation_report.htm'
    # sim_date = sim_info['sim_date']
    # htm2PDF_tool_path=sim_info.htm2PDF_tool_path

    brd_name = os.path.splitext(os.path.basename(brd_file_path))[0]
    save_spd_name = os.path.join(sim_run_folder_path, brd_name+'.spd')
    tcl_file_path = os.path.join(sim_run_folder_path, 'AutoPWT.tcl')
    stackupfile_path = os.path.join(sim_run_folder_path, 'StackUp.csv')
    materialfile_path = os.path.join(sim_run_folder_path, 'Material.cmx')
    try:
        with open(sim_info['DNS_list_file'], 'r', encoding='utf-8') as f:
            dns_list_ = f.readline()
            dns_list = dns_list_.replace(';', ' ').rstrip()
    except FileExistsError:
        dns_list = ''
        print('DNS list file is not present, no DNS will be applied!')

    # Construct the destination file path
    try:
        shutil.copy2(pwt_path, sim_run_folder_path)  # copy the powertree to the local directory
        source_pwt_name = os.path.basename(pwt_path)
        local_pwt_name = os.path.join(sim_run_folder_path, source_pwt_name)
    except FileExistsError:
        print('No powertree will be applied!')

    try:
        with open(tcl_file_path, 'w', encoding='utf-8') as file:
            # generate the tcl file

            file.write(r'#==================set folder path variable============' + '\n')
            file.write(f'set sim_run_path {{{sim_run_folder_path}}}' + '\n')

            file.write(
                r'#==================OPEN PowerDC before running scripts================' + '\n')
            file.write(r'sigrity::open document {!}' + '\n')

            log_file_path = os.path.join(sim_run_folder_path, 'simulation_log.log')
            file.write(r'#==================set debug log file===================' + '\n')
            file.write(f"sigrity::debug -log {{{log_file_path}}}" + r' {!}' + '\n')

            file.write(
                r'#==================applying some powerDC sim settings============' + '\n')
            file.write(r'sigrity::set pdcAccuracyMode {1} {!}' + '\n')
            file.write(r'sigrity::update option -AutoSaveSignOffReport {0} {!}' + '\n')
            file.write(r'sigrity::update option -AutoSaveExcelResult {1} {!}' + '\n')
            file.write(r'sigrity::set pdcAutoSaveExcelResult -fileFormat {.csv} {!}' + '\n')
            file.write(r'sigrity::update option -MaxCPUPer {90} {!}' + '\n')
            file.write(r'#Translator options' + '\n')  # translator options
            file.write(r'sigrity::spdif_option TranslateAntipadsAsVoids {1} {!}' + '\n')
            file.write(r'sigrity::spdif_option CreateModelByPartNumber {1} {!}' + '\n')
            file.write(r'sigrity::spdif_option ConvertStaticShape {1} {!}' + '\n')
            file.write(r'sigrity::spdif_option RemoveNonFunctionalPads {0} {!}' + '\n')
            file.write(r'sigrity::debug SetMsgWarnByTimer {FALSE}' + '\n')  # ignore the warning

            file.write(r'#==================OPEN brd file==========================' + '\n')
            file.write(f"sigrity::open document {{{brd_file_path}}}" + r' {!}' + '\n')
            file.write(r'#==================save spd file' + '\n')
            file.write(f"sigrity::save {{{save_spd_name}}}" + r' {!}' + '\n')

            file.write(r'#==========apply Mesh options==============' + '\n')  # mesh options
            file.write(
                r'sigrity::update option -DoglegHoleThreshold {0.0001} '
                r'-ThermalHoleThreshold {0.0001} {!}' + '\n')
            file.write(
                r'sigrity::update option -SmallHoleThreshold {0.0001} '
                r'-ViaHoleThreshold {0.0001} {!}' + '\n')
            file.write(r'sigrity::update option -MaxEdgeLength {0.002000} {!}' + '\n')
            file.write(r'sigrity::process shape {!}' + '\n')

            if os.path.exists(stackupfile_path):
                file.write(
                    r'#==================apply stackup and material==============' + '\n')
                file.write(f"sigrity::import material {{{materialfile_path}}}" + r' {!}' + '\n')
                file.write(
                    f"sigrity::update material {{{materialfile_path}}}" + r' -all {!}' + '\n')
                file.write(f"sigrity::import stackup {{{stackupfile_path}}}" + r' {!}' + '\n')

            file.write(
                r'#==================setup simulation mode to IRdrop===============' + '\n')
            file.write(r'sigrity::set pdcSimMode -irDropAnalysis {1}' + '\n')

            file.write(
                r'#==================update max via current to 0.25 ===============' + '\n')
            file.write(r'sigrity::update pdcConGlobal -viaCurrent {0.25}' + '\n')

            file.write(r'# ======================Remove all net alias============' + '\n')
            file.write(r'set all_nets [sigrity::query -net]' + '\n')
            file.write(r'set catch_count 0' + '\n')
            file.write(r'foreach net $all_nets {' + '\n')
            file.write(
                '\t'+r'if {[catch {[eval "sigrity::update net NotAsAlias {$net}"]}]} '
                r'{incr catch_count}}' + '\n')

            file.write(r'# ======================GND net selection===============' + '\n')
            file.write(r'sigrity::update net selected 0 -all {!}' + '\n')
            file.write(r'# determine if the net name GND exists' + '\n')
            file.write(r'set tmp [sigrity::querydetails net -name {GND}]' + '\n')
            file.write(r'set GND_value [lindex $tmp 0]' + '\n')
            file.write(r'if {$GND_value != "UnnamedNets"} {' + '\n')
            file.write(r'sigrity::update net selected 1 {GND} {!}' + '\n')
            file.write(r'sigrity::move net {GroundNets} GND {!}' + '\n')
            file.write(r'sigrity::update net selected 1 {GroundNets} {!}}' + '\n')

            if dns_list:
                file.write(r'# Disable DNS components' + '\n')
                file.write(f"set DNS_list \"{dns_list}\"" + '\n')
                file.write(r'eval "sigrity::update circuit -manual {disable} $DNS_list"' + '\n')
                file.write(r'puts "DNS components are disabled!"' + '\n')

            if not os.path.exists(pwt_path):
                file.write(
                    r'#==================load and apply amm library=============' + '\n')
                file.write(f"sigrity::open ammLibrary {{{library_path}}}" + r' {!}' + '\n')
                file.write(r'sigrity::assign -all {!}' + '\n')
            else:
                file.write(r'#==================apply powertree==========================' + '\n')
                file.write(f"sigrity::load powerTree {{{local_pwt_name}}}" + r' {!}' + '\n')
                file.write(r'sigrity::apply powerTree {!}' + '\n')

            file.write(
                r'#==================delete area based on enabled nets==============' + '\n')
            file.write(r'set enablednets [sigrity::query -net -option {type(selected)}]' + '\n')
            file.write(r'eval "sigrity::delete area -Net $enablednets" {!}' + '\n')
            file.write(r'sigrity::process shape {!}' + '\n')
            file.write(r'puts "Cut based on the enabled nets"' + '\n')

            file.write(r'sigrity::save {!}' + '\n')
            file.write(r'#==================start simulation==========================' + '\n')
            file.write(r'sigrity::begin simulation {!}' + '\n')

            file.write(
                r'#==================save spd file and results file=============' + '\n')
            file.write(r'sigrity::save {!}' + '\n')
            # file.write(f"sigrity::save pdcResults {{{result_file_path}}}" + r' {!}'+ '\n')
            file.write(
                f"sigrity::do pdcReport -spdFile -boardStackup -layoutView -simulationSetup "
                f"-resultTable -diagramPlot -imageResolution {{large}} "
                f"-sortViaCurrentViolationByValue -viaInformation -planeInformation "
                f"-traceInformation -planeCurrentDensityPlot -onePlotEachPowerGround "
                f"-filename {{{report_htm_path}}}" + r' {!}' + '\n')
            # convert htm file to pdf file
            file.write(r'#==========Export a log file to show all sims are done=======' + '\n')
            file.write(r'set simdone $sim_run_path' + '\n')
            file.write(r'append simdone {\spddone.out}' + '\n')
            file.write(r'set outfile [open $simdone w]' + '\n')
            file.write(r'close $outfile' + '\n')

            file.write(r'#==================exit PowerSI==================' + '\n')
            file.write(r'sigrity::exit -nosave | -n {!}' + '\n')

        msgbox(pwt_msgbox, "Main tcl script is generated successfully")
        return tcl_file_path
    except RuntimeError as e:
        msgbox(pwt_msgbox, f"An error occurred when generating the tcl script: {str(e)}")


def generate_single_limitedir_tcl(sim_info):
    """ Create material library. """
    sim_run_folder_path = sim_info['sim_run_folder_path']
    # Result_folder_path=sim_info['Result_folder_path']
    brd_file_path = sim_info['brd_file_path']
    pwt_path = sim_info['PWT_path']
    library_path = sim_info['library_path']
    pwt_msgbox = sim_info['msgbox']
    report_htm_path = sim_info['Report_htm_path']
    # Report_htm_path='Simulation_report.htm'
    # sim_date = sim_info['sim_date']
    # htm2PDF_tool_path=sim_info.htm2PDF_tool_path

    brd_name = os.path.splitext(os.path.basename(brd_file_path))[0]
    save_spd_name = os.path.join(sim_run_folder_path, brd_name+'.spd')
    tcl_file_path = os.path.join(sim_run_folder_path, 'AutoPWT.tcl')
    stackupfile_path = os.path.join(sim_run_folder_path, 'StackUp.csv')
    materialfile_path = os.path.join(sim_run_folder_path, 'Material.cmx')
    # result_file_path=os.path.join(Result_folder_path,f"Simulation_results_{sim_date}.xml")
    # result_file_path=f"Simulation_results_{sim_date}.xml"

    # Construct the destination file path

    try:
        with open(sim_info['DNS_list_file'], 'r', encoding='utf-8') as f:
            dns_list_ = f.readline()
            dns_list = dns_list_.replace(';', ' ').rstrip()
    except FileExistsError:
        dns_list = ''
        print('DNS list file is not present, no DNS will be applied!')

    try:
        shutil.copy2(pwt_path, sim_run_folder_path)  # copy the powertree to the local directory
        source_pwt_name = os.path.basename(pwt_path)
        local_pwt_name = os.path.join(sim_run_folder_path, source_pwt_name)
    except FileExistsError:
        print('No powertree will be applied!')

    try:
        with open(tcl_file_path, 'w', encoding='utf-8') as file:
            # generate the tcl file

            file.write(r'#==================set folder path variable=============' + '\n')
            file.write(f'set sim_run_path {{{sim_run_folder_path}}}' + '\n')

            file.write(
                r'#==================OPEN PowerDC before running scripts==============' + '\n')
            file.write(r'sigrity::open document {!}' + '\n')

            log_file_path = os.path.join(sim_run_folder_path, 'simulation_log.log')
            file.write(r'#==================set debug log file==========================' + '\n')
            file.write(f"sigrity::debug -log {{{log_file_path}}}" + r' {!}' + '\n')

            file.write(
                r'#==================applying some powerDC sim settings============' + '\n')
            file.write(r'sigrity::set pdcAccuracyMode {1} {!}' + '\n')
            file.write(r'sigrity::update option -AutoSaveSignOffReport {0} {!}' + '\n')
            file.write(r'sigrity::update option -AutoSaveExcelResult {1} {!}' + '\n')
            file.write(r'sigrity::set pdcAutoSaveExcelResult -fileFormat {.csv} {!}' + '\n')
            file.write(r'sigrity::update option -MaxCPUPer {90} {!}' + '\n')
            file.write(r'#Translator options' + '\n')  # translator options
            file.write(r'sigrity::spdif_option TranslateAntipadsAsVoids {1} {!}' + '\n')
            file.write(r'sigrity::spdif_option CreateModelByPartNumber {1} {!}' + '\n')
            file.write(r'sigrity::spdif_option ConvertStaticShape {1} {!}' + '\n')
            file.write(r'sigrity::spdif_option RemoveNonFunctionalPads {0} {!}' + '\n')
            file.write(r'sigrity::debug SetMsgWarnByTimer {FALSE}' + '\n')  # ignore the warning

            file.write(r'#==================OPEN brd file==========================' + '\n')
            file.write(f"sigrity::open document {{{brd_file_path}}}" + r' {!}' + '\n')
            file.write(r'#==================save spd file' + '\n')
            file.write(f"sigrity::save {{{save_spd_name}}}" + r' {!}' + '\n')

            file.write(r'#==========apply Mesh options==============' + '\n')  # mesh options
            file.write(
                r'sigrity::update option -DoglegHoleThreshold {0.0001} '
                r'-ThermalHoleThreshold {0.0001} {!}' + '\n')
            file.write(
                r'sigrity::update option -SmallHoleThreshold {0.0001} '
                r'-ViaHoleThreshold {0.0001} {!}' + '\n')
            file.write(r'sigrity::update option -MaxEdgeLength {0.002000} {!}' + '\n')
            file.write(r'sigrity::process shape {!}' + '\n')

            if os.path.exists(stackupfile_path):
                file.write(
                    r'#==================apply stackup and material==========' + '\n')
                file.write(f"sigrity::import material {{{materialfile_path}}}" + r' {!}' + '\n')
                file.write(
                    f"sigrity::update material {{{materialfile_path}}}" + r' -all {!}' + '\n')
                file.write(f"sigrity::import stackup {{{stackupfile_path}}}" + r' {!}' + '\n')

            file.write(
                r'#==================setup simulation mode to IRdrop============' + '\n')
            file.write(
                r'sigrity::update workflow -product {PowerDC} -workflowkey '
                r'{CurrentLimitedIRDropAnalysis} {!}' + '\n')
            file.write(r'sigrity::set pdcSimMode -CurrentLimitedIRDropAnalysis {1} {!}' + '\n')
            file.write(r'sigrity::set pdcSimMode -irDropAnalysis {0}' + '\n')

            file.write(
                r'#==================update max via current to 0.25A =================' + '\n')
            file.write(r'sigrity::update pdcConGlobal -viaCurrent {0.25}' + '\n')

            file.write(r'# ======================Remove all net alias============' + '\n')
            file.write(r'set all_nets [sigrity::query -net]' + '\n')
            file.write(r'set catch_count 0' + '\n')
            file.write(r'foreach net $all_nets {' + '\n')
            file.write(
                '\t'+r'if {[catch {[eval "sigrity::update net NotAsAlias {$net}"]}]} '
                r'{incr catch_count}}' + '\n')

            file.write(r'# ======================GND net selection=============' + '\n')
            file.write(r'sigrity::update net selected 0 -all {!}' + '\n')
            file.write(r'# determine if the net name GND exists' + '\n')
            file.write(r'set tmp [sigrity::querydetails net -name {GND}]' + '\n')
            file.write(r'set GND_value [lindex $tmp 0]' + '\n')
            file.write(r'if {$GND_value != "UnnamedNets"} {' + '\n')
            file.write(r'sigrity::update net selected 1 {GND} {!}' + '\n')
            file.write(r'sigrity::move net {GroundNets} GND {!}' + '\n')
            file.write(r'sigrity::update net selected 1 {GroundNets} {!}}' + '\n')

            if dns_list:
                file.write(r'# Disable DNS components' + '\n')
                file.write(f"set DNS_list \"{dns_list}\"" + '\n')
                file.write(r'eval "sigrity::update circuit -manual {disable} $DNS_list"' + '\n')
                file.write(r'puts "DNS components are disabled!"' + '\n')

            if not os.path.exists(pwt_path):
                file.write(
                    r'#==================load and apply amm library================' + '\n')
                file.write(f"sigrity::open ammLibrary {{{library_path}}}" + r' {!}' + '\n')
                file.write(r'sigrity::assign -all {!}' + '\n')
            else:
                file.write(r'#==================apply powertree=============' + '\n')
                file.write(f"sigrity::load powerTree {{{local_pwt_name}}}" + r' {!}' + '\n')
                file.write(r'sigrity::apply powerTree {!}' + '\n')

            file.write(
                r'#==================delete area based on enabled nets==============' + '\n')
            file.write(r'set enablednets [sigrity::query -net -option {type(selected)}]' + '\n')
            file.write(r'eval "sigrity::delete area -Net $enablednets" {!}' + '\n')
            file.write(r'sigrity::process shape {!}' + '\n')
            file.write(r'puts "Cut based on the enabled nets"' + '\n')

            file.write(r'sigrity::save {!}' + '\n')
            file.write(r'#==================start simulation==========================' + '\n')
            file.write(r'sigrity::begin simulation {!}' + '\n')

            file.write(
                r'#==================save spd file and results file============' + '\n')
            file.write(r'sigrity::save {!}' + '\n')
            # file.write(f"sigrity::save pdcResults {{{result_file_path}}}" + r' {!}'+ '\n')
            file.write(
                f"sigrity::do pdcReport -spdFile -boardStackup -layoutView -simulationSetup "
                f"-resultTable -diagramPlot -imageResolution {{large}} "
                f"-sortViaCurrentViolationByValue -viaInformation -planeInformation "
                f"-traceInformation -planeCurrentDensityPlot -onePlotEachPowerGround "
                f"-filename {{{report_htm_path}}}" + r' {!}' + '\n')
            # convert htm file to pdf file

            file.write(r'#==========Export a log file to show all sims are done=======' + '\n')
            file.write(r'set simdone $sim_run_path' + '\n')
            file.write(r'append simdone {\spddone.out}' + '\n')
            file.write(r'set outfile [open $simdone w]' + '\n')
            file.write(r'close $outfile' + '\n')

            file.write(r'#==================exit PowerSI==================' + '\n')
            file.write(r'sigrity::exit -nosave | -n {!}' + '\n')

        msgbox(pwt_msgbox, "Main tcl script is generated successfully")
        return tcl_file_path
    except RuntimeError as e:
        msgbox(pwt_msgbox, f"An error occurred when generating the tcl script: {str(e)}")


def generate_single_resmeas_tcl(sim_info):
    """generate tcl file for single board resistnace measurement"""
    # generate resistance measurement based on the powertree file
    sim_run_folder_path = sim_info['sim_run_folder_path']
    # Result_folder_path=sim_info['Result_folder_path']
    brd_file_path = sim_info['brd_file_path']
    pwt_path = sim_info['PWT_path']
    library_path = sim_info['library_path']
    pwt_msgbox = sim_info['msgbox']
    report_htm_path = sim_info['Report_htm_path']
    # sim_date=sim_info['sim_date']
    # htm2PDF_tool_path=sim_info.htm2PDF_tool_path

    brd_name = os.path.splitext(os.path.basename(brd_file_path))[0]
    save_spd_name = os.path.join(sim_run_folder_path, brd_name+'.spd')
    tcl_file_path = os.path.join(sim_run_folder_path, 'AutoPWT.tcl')
    stackupfile_path = os.path.join(sim_run_folder_path, 'StackUp.csv')
    materialfile_path = os.path.join(sim_run_folder_path, 'Material.cmx')

    try:
        with open(sim_info['DNS_list_file'], 'r', encoding='utf-8') as f:
            dns_list_ = f.readline()
            dns_list = dns_list_.replace(';', ' ').rstrip()
    except FileExistsError:
        dns_list = ''
        print('DNS list file is not present, no DNS will be applied!')

    # Construct the destination file path
    try:
        shutil.copy2(pwt_path, sim_run_folder_path)  # copy the powertree to the local directory
        source_pwt_name = os.path.basename(pwt_path)
        local_pwt_name = os.path.join(sim_run_folder_path, source_pwt_name)
    except FileExistsError:
        print('No powertree will be applied!')

    try:
        with open(tcl_file_path, 'w', encoding='utf-8') as file:
            # generate the tcl file
            file.write(r'#==================set folder path variable===========' + '\n')
            file.write(f'set sim_run_path {{{sim_run_folder_path}}}' + '\n')

            file.write(
                r'#==================OPEN PowerDC before running scripts=========' + '\n')
            file.write(r'sigrity::open document {!}' + '\n')

            log_file_path = os.path.join(sim_run_folder_path, 'simulation_log.log')
            file.write(r'#==================set debug log file==========================' + '\n')
            file.write(f"sigrity::debug -log {{{log_file_path}}}" + r' {!}' + '\n')

            file.write(
                r'#==================applying some powerDC sim settings===========' + '\n')
            file.write(r'sigrity::set pdcAccuracyMode {1} {!}' + '\n')
            file.write(r'sigrity::update option -AutoSaveSignOffReport {0} {!}' + '\n')
            file.write(r'sigrity::update option -AutoSaveExcelResult {1} {!}' + '\n')
            file.write(r'sigrity::set pdcAutoSaveExcelResult -fileFormat {.csv} {!}' + '\n')
            file.write(r'sigrity::update option -MaxCPUPer {90} {!}' + '\n')
            file.write(r'#Translator options' + '\n')  # translator options
            file.write(r'sigrity::spdif_option TranslateAntipadsAsVoids {1} {!}' + '\n')
            file.write(r'sigrity::spdif_option CreateModelByPartNumber {1} {!}' + '\n')
            file.write(r'sigrity::spdif_option ConvertStaticShape {1} {!}' + '\n')
            file.write(r'sigrity::spdif_option RemoveNonFunctionalPads {0} {!}' + '\n')
            file.write(r'sigrity::debug SetMsgWarnByTimer {FALSE}' + '\n')  # ignore the warning

            file.write(r'#==================OPEN brd file==========================' + '\n')
            file.write(f"sigrity::open document {{{brd_file_path}}}" + r' {!}' + '\n')

            file.write(r'#==================save spd file==========================' + '\n')
            file.write(f"sigrity::save {{{save_spd_name}}}" + r' {!}' + '\n')

            file.write(r'#==========apply Mesh options==============' + '\n')  # mesh options
            file.write(
                r'sigrity::update option -DoglegHoleThreshold {0.0001} '
                r'-ThermalHoleThreshold {0.0001} {!}' + '\n')
            file.write(
                r'sigrity::update option -SmallHoleThreshold {0.0001} '
                r'-ViaHoleThreshold {0.0001} {!}' + '\n')
            file.write(r'sigrity::update option -MaxEdgeLength {0.002000} {!}' + '\n')
            file.write(r'sigrity::process shape {!}' + '\n')

            if os.path.exists(stackupfile_path):
                file.write(
                    r'#==========apply stackup and material==============' + '\n')
                file.write(f"sigrity::import material {{{materialfile_path}}}" + r' {!}' + '\n')
                file.write(
                    f"sigrity::update material {{{materialfile_path}}}" + r' -all {!}' + '\n')
                file.write(f"sigrity::import stackup {{{stackupfile_path}}}" + r' {!}' + '\n')

            file.write(r'#==================update max via current to 1A ===========' + '\n')
            file.write(r'sigrity::update pdcConGlobal -viaCurrent {1}' + '\n')

            file.write(r'# ======================Remove all net alias===========' + '\n')
            file.write(r'set all_nets [sigrity::query -net]' + '\n')
            file.write(r'set catch_count 0' + '\n')
            file.write(r'foreach net $all_nets {' + '\n')
            file.write(
                '\t'+r'if {[catch {[eval "sigrity::update net NotAsAlias {$net}"]}]} '
                r'{incr catch_count}}' + '\n')

            file.write(r'# ===============GND net selection============' + '\n')
            file.write(r'sigrity::update net selected 0 -all {!}' + '\n')
            file.write(r'# determine if the net name GND exists' + '\n')
            file.write(r'set tmp [sigrity::querydetails net -name {GND}]' + '\n')
            file.write(r'set GND_value [lindex $tmp 0]' + '\n')
            file.write(r'if {$GND_value != "UnnamedNets"} {' + '\n')
            file.write(r'sigrity::update net selected 1 {GND} {!}' + '\n')
            file.write(r'sigrity::move net {GroundNets} GND {!}' + '\n')
            file.write(r'sigrity::update net selected 1 {GroundNets} {!}}' + '\n')

            if dns_list:
                file.write(r'# Disable DNS components' + '\n')
                file.write(f"set DNS_list \"{dns_list}\"" + '\n')
                file.write(r'eval "sigrity::update circuit -manual {disable} $DNS_list"' + '\n')
                file.write(r'puts "DNS components are disabled!"' + '\n')

            if not os.path.exists(pwt_path):
                file.write(
                    r'#==================load and apply amm library==========' + '\n')
                file.write(f"sigrity::open ammLibrary {{{library_path}}}" + r' {!}' + '\n')
                file.write(r'sigrity::assign -all {!}' + '\n')
                file.write(r'sigrity::update net selected 1 -all {!}' + '\n')
            else:
                file.write(r'#==================apply powertree==========================' + '\n')
                file.write(f"sigrity::load powerTree {{{local_pwt_name}}}" + r' {!}' + '\n')
                file.write(r'sigrity::apply powerTree {!}' + '\n')
                file.write(
                    r'#==================use sinks as resistance measurement============' + '\n')
                file.write(r'set all_sinks [sigrity::query -pdcSink]' + '\n')
                file.write(
                    r'foreach sink $all_sinks {eval "sigrity::add pdcResist -vrmSinkLocation '
                    r'-mode {Loop} -model {Lumped to Lumped} -name $sink"}' + '\n')

            file.write(
                r'#==================delete area based on enabled nets==============' + '\n')
            file.write(r'set enablednets [sigrity::query -net -option {type(selected)}]' + '\n')
            file.write(r'eval "sigrity::delete area -Net $enablednets" {!}' + '\n')
            file.write(r'sigrity::process shape {!}' + '\n')
            file.write(r'puts "Cut based on the enabled nets"' + '\n')

            file.write(
                r'#=======setup simulation mode to resistance measurement==========' + '\n')
            file.write(
                r'sigrity::update workflow -product {PowerDC} -workflowkey '
                r'{ResistanceMeasurement} {!}' + '\n')
            file.write(r'sigrity::set pdcSimMode -resistanceMeasurement {1}' + '\n')
            file.write(r'sigrity::set pdcSimMode -irDropAnalysis {0}' + '\n')  # disable IR drop

            file.write(r'sigrity::save {!}' + '\n')

            file.write(r'#==================start simulation==========================' + '\n')
            file.write(r'sigrity::begin simulation {!}' + '\n')

            file.write(
                r'#==================save spd file and results file=========' + '\n')
            file.write(r'sigrity::save {!}' + '\n')
            # file.write(f"sigrity::save pdcResults {{{result_file_path}}}" + r' {!}'+ '\n')
            file.write(
                f"sigrity::do pdcReport -spdFile -boardStackup -layoutView -simulationSetup "
                f"-resultTable -resistanceMeasurement -diagramPlot -imageResolution {{large}} "
                f"-filename {{{report_htm_path}}}" + r' {!}' + '\n')
            file.write(r'#============Export a log file to show all sims are done====' + '\n')
            file.write(r'set simdone $sim_run_path' + '\n')
            file.write(r'append simdone {\spddone.out}' + '\n')
            file.write(r'set outfile [open $simdone w]' + '\n')
            file.write(r'close $outfile' + '\n')

            file.write(r'#==================exit PowerSI==================' + '\n')
            file.write(r'sigrity::exit -nosave | -n {!}' + '\n')

        msgbox(pwt_msgbox, "Main tcl script is generated successfully")
        return tcl_file_path
    except RuntimeError as e:
        msgbox(pwt_msgbox, f"An error occurred when generating the tcl script: {str(e)}")


def generate_multibrd_ir_tcl(sim_info):
    """ Create material library. """
    sim_run_folder_path = sim_info['sim_run_folder_path']
    # Result_folder_path=sim_info['Result_folder_path']
    brd_path = sim_info['brd_file_path']
    pwt_path = sim_info['PWT_path']
    stackup_path = sim_info['stackup_path']
    material_path = sim_info['material_path']
    library_path = sim_info['library_path']
    pwt_msgbox = sim_info['msgbox']
    report_htm_path = sim_info['Report_htm_path']
    apply_stackup_key = sim_info['apply_stackup_key']
    # list_DNS_files = sim_info['list_DNS_files']

    # Report_htm_path='Simulation_report.htm'
    # sim_date=sim_info['sim_date']
    # htm2PDF_tool_path=sim_info.htm2PDF_tool_path

    # Construct the destination file path
    try:
        shutil.copy2(pwt_path, sim_run_folder_path)  # copy the powertree to the local directory
        source_pwt_name = os.path.basename(pwt_path)
        local_pwt_name = os.path.join(sim_run_folder_path, source_pwt_name)
    except FileExistsError:
        print('No powertree will be applied!')

    tcl_file_path = os.path.join(sim_run_folder_path, 'AutoPWT.tcl')
    workspace_path = os.path.join(sim_run_folder_path, 'multibrd_IR.sdc')
    try:
        with open(tcl_file_path, 'w', encoding='utf-8') as file:
            # generate the tcl file

            file.write(r'#==================set folder path variable==========' + '\n')
            file.write(f'set sim_run_path {{{sim_run_folder_path}}}' + '\n')

            file.write(
                r'#==================OPEN PowerDC before running scripts=======' + '\n')
            file.write(r'sigrity::open document {!}' + '\n')

            log_file_path = os.path.join(sim_run_folder_path, 'simulation_log.log')
            file.write(r'#==================set debug log file====================' + '\n')
            file.write(f"sigrity::debug -log {{{log_file_path}}}" + r' {!}' + '\n')

            file.write(
                r'#==================applying some powerDC sim settings=========' + '\n')
            file.write(r'sigrity::set pdcAccuracyMode {1} {!}' + '\n')
            file.write(r'sigrity::update option -AutoSaveSignOffReport {0} {!}' + '\n')
            file.write(r'sigrity::update option -AutoSaveExcelResult {1} {!}' + '\n')
            file.write(r'sigrity::set pdcAutoSaveExcelResult -fileFormat {.csv} {!}' + '\n')
            file.write(r'sigrity::update option -MaxCPUPer {90} {!}' + '\n')
            file.write(r'#Translator options' + '\n')  # translator options
            file.write(r'sigrity::spdif_option TranslateAntipadsAsVoids {1} {!}' + '\n')
            file.write(r'sigrity::spdif_option CreateModelByPartNumber {1} {!}' + '\n')
            file.write(r'sigrity::spdif_option ConvertStaticShape {1} {!}' + '\n')
            file.write(r'sigrity::spdif_option RemoveNonFunctionalPads {0} {!}' + '\n')
            file.write(r'sigrity::debug SetMsgWarnByTimer {FALSE}' + '\n')  # ignore the warning

            spd_paths = {}
            for key in brd_path.keys():
                file.write(
                    f"#=======OPEN {key} brd file, do some processing save as spd ======" + '\n')
                brd_file_path = brd_path[key]
                brd_name = os.path.splitext(os.path.basename(brd_file_path))[0]
                save_spd_name = os.path.join(sim_run_folder_path, brd_name+'.spd')

                file.write(f"sigrity::open document {{{brd_file_path}}}" + r' {!}' + '\n')
                file.write(r'#==================save spd file' + '\n')
                file.write(f"sigrity::save {{{save_spd_name}}}" + r' {!}' + '\n')
                spd_paths[key] = save_spd_name

                if key in apply_stackup_key:
                    materialfile_path = stackup_path[key]
                    stackupfile_path = material_path[key]
                    file.write(
                        r'#==================apply stackup and material=============' + '\n')
                    file.write(f"sigrity::import material {{{materialfile_path}}}" + r' {!}' + '\n')
                    file.write(
                        f"sigrity::update material {{{materialfile_path}}}" + r' -all {!}' + '\n')
                    file.write(f"sigrity::import stackup {{{stackupfile_path}}}" + r' {!}' + '\n')

                file.write(r'#==========apply Mesh options==============' + '\n')  # mesh options
                file.write(
                    r'sigrity::update option -DoglegHoleThreshold {0.0001} '
                    r'-ThermalHoleThreshold {0.0001} {!}' + '\n')
                file.write(
                    r'sigrity::update option -SmallHoleThreshold {0.0001} '
                    r'-ViaHoleThreshold {0.0001} {!}' + '\n')
                file.write(r'sigrity::update option -MaxEdgeLength {0.002000} {!}' + '\n')
                file.write(r'sigrity::process shape {!}' + '\n')

                file.write(
                    r'# ======================Remove all net alias================' + '\n')
                file.write(r'set all_nets [sigrity::query -net]' + '\n')
                file.write(r'set catch_count 0' + '\n')
                file.write(r'foreach net $all_nets {' + '\n')
                file.write(
                    '\t'+r'if {[catch {[eval "sigrity::update net NotAsAlias {$net}"]}]} '
                    r'{incr catch_count}}' + '\n')

                # apply DNS to each board
                try:
                    with open(sim_info['list_DNS_files'][key], 'r', encoding='utf-8') as f:
                        dns_list_ = f.readline()
                        if dns_list_ != '':
                            dns_list = dns_list_.replace(';', ' ').rstrip()
                            file.write(r'# Disable DNS components' + '\n')
                            file.write(f"set DNS_list \"{dns_list}\"" + '\n')
                            file.write(
                                r'eval "sigrity::update circuit -manual {disable} '
                                r'$DNS_list"' + '\n')
                            file.write(r'puts "DNS components are disabled!"' + '\n')
                        else:
                            print(
                                f'DNS CSV file is generated, but it is empty. '
                                f'The BOM_IGNORE property maybe missing in {key} board file!')
                except FileExistsError:
                    # DNS_list=''
                    print(
                        f"DNS list file is not present, no DNS will be applied to block {key}!")

                file.write(
                    r'#==================update max via current to 1A =============' + '\n')
                file.write(r'sigrity::update pdcConGlobal -viaCurrent {1}' + '\n')
                file.write(r'#==================save spd file again==========' + '\n')
                file.write(f"sigrity::save {{{save_spd_name}}}" + r' {!}' + '\n')

            file.write(
                r'#==================setup and save multibrd_workspace=======' + '\n')
            file.write(
                r'sigrity::update workflow -product {PowerDC} '
                r'-workflowkey {MultiBoardIRDropAnalysis} {!}' + '\n')
            file.write(r'sigrity::open multiBoard {!}' + '\n')
            file.write(f"sigrity::save -workspace {{{workspace_path}}}" + r' {!}' + '\n')

            if not os.path.exists(local_pwt_name):
                file.write(
                    r'#==================load and apply amm library============' + '\n')
                file.write(f"sigrity::open ammLibrary {{{library_path}}}" + r' {!}' + '\n')
                file.write(r'sigrity::assign -all {!}' + '\n')
                file.write(r'sigrity::save {!}' + '\n')

            else:
                file.write(r'#==================apply powertree==========================' + '\n')
                file.write(f"sigrity::load powerTree {{{local_pwt_name}}}" + r' {!}' + '\n')
                # update the file path for the powertree
                for key in spd_paths.keys():
                    file.write(
                        f"sigrity::pwt::design update -type {{block}} -block {{{key}}} "
                        f"-path {{{spd_paths[key]}}}" + r' {!}' + '\n')

            file.write(r'sigrity::apply powerTree {!}' + '\n')

            file.write(r'sigrity::save {!}' + '\n')
            file.write(r'sigrity::save -workspace -all {!}' + '\n')

            file.write(r'#==================start simulation================' + '\n')
            file.write(r'sigrity::begin simulation {!}' + '\n')

            file.write(
                r'#============save workspace file and results file==========' + '\n')

            file.write(r'sigrity::save -workspace -all {!}' + '\n')
            file.write(
                f"sigrity::do pdcReport -spdFile -boardStackup -simulationSetup -resultTable "
                f"-diagramPlot -sortViaCurrentViolationByValue "
                f"-filename {{{report_htm_path}}}" + r' {!}' + '\n')

            file.write(r'#===========Export a log file to show all sims are done========' + '\n')
            file.write(r'set simdone $sim_run_path' + '\n')
            file.write(r'append simdone {\spddone.out}' + '\n')
            file.write(r'set outfile [open $simdone w]' + '\n')
            file.write(r'close $outfile' + '\n')

            file.write(r'#==================exit PowerDC==================' + '\n')
            file.write(r'sigrity::exit -nosave | -n {!}' + '\n')

        msgbox(pwt_msgbox, "Main tcl script is generated successfully")
        return tcl_file_path
    except RuntimeError as e:
        msgbox(pwt_msgbox, f"An error occurred when generating the tcl script: {str(e)}")


def generate_multibrd_limitedir_tcl(sim_info):
    """ create tcl file for multibrd current limited ir drop simulation """
    sim_run_folder_path = sim_info['sim_run_folder_path']
    # Result_folder_path=sim_info['Result_folder_path']
    brd_path = sim_info['brd_file_path']
    pwt_path = sim_info['PWT_path']
    stackup_path = sim_info['stackup_path']
    material_path = sim_info['material_path']
    library_path = sim_info['library_path']
    pwt_msgbox = sim_info['msgbox']
    report_htm_path = sim_info['Report_htm_path']
    apply_stackup_key = sim_info['apply_stackup_key']
    # list_DNS_files = sim_info['list_DNS_files']
    # Report_htm_path='Simulation_report.htm'
    # sim_date=sim_info['sim_date']
    # htm2PDF_tool_path=sim_info.htm2PDF_tool_path

    # Construct the destination file path
    try:
        shutil.copy2(pwt_path, sim_run_folder_path)  # copy the powertree to the local directory
        source_pwt_name = os.path.basename(pwt_path)
        local_pwt_name = os.path.join(sim_run_folder_path, source_pwt_name)
    except FileExistsError:
        print('No powertree will be applied!')

    tcl_file_path = os.path.join(sim_run_folder_path, 'AutoPWT.tcl')
    workspace_path = os.path.join(sim_run_folder_path, 'multibrd_IR.sdc')
    try:
        with open(tcl_file_path, 'w', encoding='utf-8') as file:
            # generate the tcl file

            file.write(r'#==================set folder path variable======' + '\n')
            file.write(f'set sim_run_path {{{sim_run_folder_path}}}' + '\n')

            log_file_path = os.path.join(sim_run_folder_path, 'simulation_log.log')
            file.write(r'#==================set debug log file==========================' + '\n')
            file.write(f"sigrity::debug -log {{{log_file_path}}}" + r' {!}' + '\n')

            file.write(
                r'#==================OPEN PowerDC before running scripts=========' + '\n')
            file.write(r'sigrity::open document {!}' + '\n')

            file.write(
                r'#==================applying some powerDC sim settings========' + '\n')
            file.write(r'sigrity::set pdcAccuracyMode {1} {!}' + '\n')
            file.write(r'sigrity::update option -AutoSaveSignOffReport {0} {!}' + '\n')
            file.write(r'sigrity::update option -AutoSaveExcelResult {1} {!}' + '\n')
            file.write(r'sigrity::set pdcAutoSaveExcelResult -fileFormat {.csv} {!}' + '\n')
            file.write(r'sigrity::update option -MaxCPUPer {90} {!}' + '\n')
            file.write(r'#Translator options' + '\n')  # translator options
            file.write(r'sigrity::spdif_option TranslateAntipadsAsVoids {1} {!}' + '\n')
            file.write(r'sigrity::spdif_option CreateModelByPartNumber {1} {!}' + '\n')
            file.write(r'sigrity::spdif_option ConvertStaticShape {1} {!}' + '\n')
            file.write(r'sigrity::spdif_option RemoveNonFunctionalPads {0} {!}' + '\n')
            file.write(r'sigrity::debug SetMsgWarnByTimer {FALSE}' + '\n')  # ignore the warning

            file.write(
                r'#==================OPEN brd file, do some processing save as spd ========' + '\n')
            spd_paths = {}
            for key in brd_path.keys():
                brd_file_path = brd_path[key]
                brd_name = os.path.splitext(os.path.basename(brd_file_path))[0]
                save_spd_name = os.path.join(sim_run_folder_path, brd_name+'.spd')

                file.write(f"sigrity::open document {{{brd_file_path}}}" + r' {!}' + '\n')
                file.write(r'#==================save spd file' + '\n')
                file.write(f"sigrity::save {{{save_spd_name}}}" + r' {!}' + '\n')
                spd_paths[key] = save_spd_name

                if key in apply_stackup_key:
                    materialfile_path = stackup_path[key]
                    stackupfile_path = material_path[key]
                    file.write(
                        r'#==================apply stackup and material=============' + '\n')
                    file.write(f"sigrity::import material {{{materialfile_path}}}" + r' {!}' + '\n')
                    file.write(
                        f"sigrity::update material {{{materialfile_path}}}" + r' -all {!}' + '\n')
                    file.write(f"sigrity::import stackup {{{stackupfile_path}}}" + r' {!}' + '\n')

                file.write(r'#==========apply Mesh options==============' + '\n')  # mesh options
                file.write(
                    r'sigrity::update option -DoglegHoleThreshold {0.0001} '
                    r'-ThermalHoleThreshold {0.0001} {!}' + '\n')
                file.write(
                    r'sigrity::update option -SmallHoleThreshold {0.0001} '
                    r'-ViaHoleThreshold {0.0001} {!}' + '\n')
                file.write(r'sigrity::update option -MaxEdgeLength {0.002000} {!}' + '\n')
                file.write(r'sigrity::process shape {!}' + '\n')

                file.write(
                    r'# ======================Remove all net alias============' + '\n')
                file.write(r'set all_nets [sigrity::query -net]' + '\n')
                file.write(r'set catch_count 0' + '\n')
                file.write(r'foreach net $all_nets {' + '\n')
                file.write(
                    '\t'+r'if {[catch {[eval "sigrity::update net NotAsAlias {$net}"]}]} '
                    r'{incr catch_count}}' + '\n')

                # apply DNS to each board
                try:
                    with open(sim_info['list_DNS_files'][key], 'r', encoding='utf-8') as f:
                        DNS_list_ = f.readline()
                        if DNS_list_ != '':
                            DNS_list = DNS_list_.replace(';', ' ').rstrip()
                            file.write(r'# Disable DNS components' + '\n')
                            file.write(f"set DNS_list \"{DNS_list}\"" + '\n')
                            file.write(
                                r'eval "sigrity::update circuit -manual {disable} '
                                r'$DNS_list"' + '\n')
                            file.write(r'puts "DNS components are disabled!"' + '\n')
                        else:
                            print(
                                f'DNS CSV file is generated, but it is empty. '
                                f'The BOM_IGNORE property maybe missing in {key} board file!')
                except FileExistsError:
                    # DNS_list=''
                    print(f"DNS list file is not present, no DNS will be applied to block {key}!")

                file.write(
                    r'#==================update max via current to 1A ==============' + '\n')
                file.write(r'sigrity::update pdcConGlobal -viaCurrent {1}' + '\n')
                file.write(r'#==================save spd file again================' + '\n')
                file.write(f"sigrity::save {{{save_spd_name}}}" + r' {!}' + '\n')

            file.write(
                r'#==================setup and save multibrd_workspace==============' + '\n')
            file.write(r'sigrity::open multiBoard {!}' + '\n')
            file.write(
                r'sigrity::update workflow -product {PowerDC} -workflowkey '
                r'{MultiBoardWorstIRDropAnalysis} {!}' + '\n')
            file.write(f"sigrity::save -workspace {{{workspace_path}}}" + r' {!}' + '\n')

            if not os.path.exists(local_pwt_name):
                file.write(
                    r'#==================load and apply amm library============' + '\n')
                file.write(f"sigrity::open ammLibrary {{{library_path}}}" + r' {!}' + '\n')
                file.write(r'sigrity::assign -all {!}' + '\n')
                file.write(r'sigrity::save {!}' + '\n')

            else:
                file.write(r'#==================apply powertree==================' + '\n')
                file.write(f"sigrity::load powerTree {{{local_pwt_name}}}" + r' {!}' + '\n')
                # update the file path for the powertree
                for key in spd_paths.keys():
                    file.write(
                        f"sigrity::pwt::design update -type {{block}} -block {{{key}}} "
                        f"-path {{{spd_paths[key]}}}" + r' {!}' + '\n')

            file.write(r'sigrity::apply powerTree {!}' + '\n')
            file.write(r'sigrity::save {!}' + '\n')
            file.write(r'sigrity::save -workspace -all {!}' + '\n')

            file.write(r'#==================start simulation==========================' + '\n')
            file.write(r'sigrity::begin simulation {!}' + '\n')

            file.write(
                r'#==================save workspace file and results file==============' + '\n')

            file.write(r'sigrity::save -workspace -all {!}' + '\n')
            file.write(
                f"sigrity::do pdcReport -spdFile -boardStackup -layoutView -simulationSetup "
                f"-resultTable -diagramPlot -sortViaCurrentViolationByValue "
                f"-filename {{{report_htm_path}}}" + r' {!}' + '\n')

            file.write(r'#=========Export a log file to show all sims are done======' + '\n')
            file.write(r'set simdone $sim_run_path' + '\n')
            file.write(r'append simdone {\spddone.out}' + '\n')
            file.write(r'set outfile [open $simdone w]' + '\n')
            file.write(r'close $outfile' + '\n')

            file.write(r'#==================exit PowerDC==================' + '\n')
            file.write(r'sigrity::exit -nosave | -n {!}' + '\n')

        msgbox(pwt_msgbox, "Main tcl script is generated successfully")
        return tcl_file_path
    except RuntimeError as e:
        msgbox(pwt_msgbox, f"An error occurred when generating the tcl script: {str(e)}")
