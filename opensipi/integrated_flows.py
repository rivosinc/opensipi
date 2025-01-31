# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
Author: yanshengw@
Last updated on Jan. 5, 2024

Description:
    This module contains all top-level integrated flows.
"""


from opensipi.sipi_infra import Platform


def sim2report(input_info, mntr_info):
    """This function takes csv input info to the Platform, parses them into
    scripts to automate S-para extraction, processes results and generates
    a report.
    """

    pf = Platform(input_info)
    input_data = pf.read_inputs()
    xtract_tool = input_data["settings"]["EXTRACTIONTOOL"]
    pf.drop_dsn_file(xtract_tool)
    sim_exec = pf.parser(input_data)
    result_config_dir, report_config_dir = pf.run(sim_exec, mntr_info)
    report_dir = pf.report(result_config_dir, report_config_dir)
    return report_dir


def sim2report_gsuites(input_info, mntr_info):
    """This function takes gSheet input info to the Platform, parses them into
    scripts to automate S-para extraction, processes results and generates
    a report.
    """
    pf = Platform(input_info)
    input_data = pf.read_inputs()
    xtract_tool = input_data["settings"]["EXTRACTIONTOOL"]
    pf.drop_dsn_file(xtract_tool)
    sim_exec = pf.parser(input_data)
    result_config_dir, report_config_dir = pf.run(sim_exec, mntr_info)
    pf.report(result_config_dir, report_config_dir)
    upload_config_dir = pf.export_upload_config(report_config_dir)
    pf.upload2drive(upload_config_dir)
