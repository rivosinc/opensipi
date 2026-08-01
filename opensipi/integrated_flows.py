# SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
Author: yanshengw@
Last updated on Jan. 5, 2024

Description:
    This module contains all top-level integrated flows.

    These are the functions a user calls directly. Each one drives a whole
extraction, from reading the input tables through to the report, by stepping a
``Platform`` instance through its methods in the right order. Use ``Platform``
directly only when a flow needs to deviate from that sequence.
"""

from opensipi.sipi_infra import Platform


def sim2report(input_info, mntr_info):
    """Run a whole extraction from csv input to a local report.

    This function takes csv input info to the Platform, parses them into
    scripts to automate S-para extraction, processes results and generates
    a report.

    The call blocks and prompts twice at the terminal: once to have the design
    file dropped in place, and, when ``op_pause_after_model_check`` is set,
    once more before the solver starts.

    Args:
        input_info (dict): Input related information.

            * ``input_type`` (str): Must be ``"csv"``.
            * ``input_dir`` (str): Directory holding the input csv folders.
            * ``input_folder`` (str): Name of the folder inside ``input_dir``
              holding the csv sheets for this extraction.
            * ``op_run_name`` (str, optional): Time stamp of an existing
              ``Run_...`` folder to resume into. Omit or leave empty to start a
              new run.

        mntr_info (dict): Monitor related information.

            * ``email`` (str): Notification address. Not enabled yet.
            * ``op_pause_after_model_check`` (int, optional): ``1`` to pause
              after model check so the models can be inspected or hand-edited,
              ``0`` to run straight through. Defaults to ``0``.

    Returns:
        str: Full path to the generated pdf report.
    """

    pf = Platform(input_info)
    xtract_tool = pf.input_data["settings"]["EXTRACTIONTOOL"]
    pf.drop_dsn_file(xtract_tool)
    sim_exec = pf.parser(pf.input_data)
    result_config_dir, report_config_dir = pf.run(sim_exec, mntr_info)
    report_dir = pf.report(result_config_dir, report_config_dir)
    return report_dir


def sim2report_gsuites(input_info, mntr_info):
    """Run a whole extraction from Google Sheet input, then upload the results.

    This function takes gSheet input info to the Platform, parses them into
    scripts to automate S-para extraction, processes results and generates
    a report.

    The Google Suites counterpart of :func:`sim2report`. It runs the same
    extraction and reporting steps, then uploads the outcome to Google Drive.

    Args:
        input_info (dict): Input related information.

            * ``input_type`` (str): Must be ``"gsheet"``.
            * ``input_url`` (str): URL of the Google Sheet holding the input
              tabs.
            * ``proj_dir`` (str): The project directory. Required here, since
              there is no ``input_dir`` to derive it from.
            * ``output_type`` (str, optional): ``"gdrive"`` to upload the
              results. Defaults to ``"local"``.
            * ``op_run_name`` (str, optional): As in :func:`sim2report`.

        mntr_info (dict): Monitor related information, as in
            :func:`sim2report`.

    Returns:
        None: The report path is not returned. The report is written to the run
        folder and uploaded to Google Drive.

    Note:
        The Google credentials and target Drive IDs are not passed in here.
        They are read from ``config_gsuites.yaml`` under the ``opensipi_config``
        folder.
    """
    pf = Platform(input_info)
    xtract_tool = pf.input_data["settings"]["EXTRACTIONTOOL"]
    pf.drop_dsn_file(xtract_tool)
    sim_exec = pf.parser(pf.input_data)
    result_config_dir, report_config_dir = pf.run(sim_exec, mntr_info)
    pf.report(result_config_dir, report_config_dir)
    upload_config_dir = pf.export_upload_config(report_config_dir)
    pf.upload2drive(upload_config_dir)
