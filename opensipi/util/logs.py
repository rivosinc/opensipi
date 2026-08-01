# SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
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
    """Create a logger writing to both a log file and the console.

    Propagation to the root logger is disabled, so records emitted here do not
    reach handlers installed by the application embedding OpenSIPI.

    Args:
        log_dir (str): Full path of the log file to write, including the file
            name.
        log_header (str): Logger name, shown in each record and used to
            retrieve the same logger again through ``logging.getLogger``.

    Returns:
        logging.Logger: The configured logger, at level ``DEBUG``.

    Note:
        If the log file cannot be opened, the error is printed and the logger
        is returned with no handlers attached rather than raising, so a
        failure to log never aborts an extraction.
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
