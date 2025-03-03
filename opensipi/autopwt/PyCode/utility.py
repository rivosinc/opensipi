# SPDX-FileCopyrightText: © 2025 Google LLC
#
# SPDX-License-Identifier: Apache-2.0


"""utility functions"""

import datetime
import tkinter as tk


def get_timestamp():
    """get current time and format it"""
    current_time = datetime.datetime.now()
    formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
    return formatted_time


def pwt_msgbox_print(tk_msg_box, log_msg):
    """pass the msg box"""
    time = get_timestamp()
    tk_msg_box.configure(state=tk.NORMAL)
    tk_msg_box.insert("end", time+": "+log_msg+"\n")
    tk_msg_box.configure(state=tk.DISABLED)
