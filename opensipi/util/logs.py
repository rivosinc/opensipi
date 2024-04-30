# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
Author: yanshengw@
Last updated on Nov. 20, 2023

Description:
    This Python3 module provides utilities for test logging and result saving.
"""


import logging
import sys


def setup_logger(log_dir, log_header):
    """This will create sipi_log with output to a log file and to the
    concole.
    """

    sipi_log = logging.getLogger(log_header)
    sipi_log.propagate = False
    sipi_log.setLevel(logging.DEBUG)
    formatter = logging.Formatter("[%(asctime)s] - [%(name)s] - %(message)s")

    try:
        # export a log file
        file_handler = logging.FileHandler(log_dir)
        file_handler.setFormatter(formatter)
        file_handler.setLevel("DEBUG")
        sipi_log.addHandler(file_handler)
        # print log in the console
        console_handler = logging.StreamHandler(stream=sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel("DEBUG")
        sipi_log.addHandler(console_handler)
    except OSError as exception:
        print(f"Failed to set up log file due to error: {exception}. Continuing anyway.")

    return sipi_log
