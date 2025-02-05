# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
Author: yanshengw@
Last updated on Jul. 29, 2024

Description:
    This Python3 module contains functions that are commonly used by the
OpenSIPI application.
"""


import base64
import csv
import os
from datetime import datetime
from os.path import expanduser

from ruamel.yaml import YAML


def get_path_separator():
    """get the right symbol to separate the path"""
    if os.name == "nt":  # Windows OS
        symbol = "\\"
    elif os.name == "posix":  # Mac/Linux/BSD
        symbol = "/"
    return symbol


SL = get_path_separator()


def get_root_dir():
    """get the root directory where the tool_config folder is created."""
    if os.name == "nt":  # Windows OS
        root = "C:\\"
    elif os.name == "posix":  # Mac/Linux/BSD
        root = os.getenv("HOME") + SL
    return root


def get_dir():
    """get commonly used dir"""
    real_dir = os.path.dirname(os.path.realpath(__file__))
    # process path
    dir_list = real_dir.split(SL)
    root_dir = SL.join(dir_list[:-3]) + SL
    scripts_dir = SL.join(dir_list[:-2]) + SL
    pkg_dir = SL.join(dir_list[:-1]) + SL
    template_dir = pkg_dir + "templates" + SL
    return root_dir, scripts_dir, template_dir


def make_dir(tgt_dir):
    """make dir if not existing."""
    if not os.path.exists(tgt_dir):
        os.makedirs(tgt_dir)


def slash_ending(dir):
    """add double slash at the end of a dir if not existing."""
    if dir[-1:] != SL:
        dir_slash = dir + SL
    else:
        dir_slash = dir
    return dir_slash


def rectify_dir(dir):
    """correct dir to \\ or / based on the OS"""
    new_dir = dir
    if "\\" in dir:
        new_dir = SL.join(dir.split("\\"))
    elif "/" in dir:
        new_dir = SL.join(dir.split("/"))
    return new_dir


def rectify_data(raw_data):
    """strip white spaces before and after strings in the raw data."""
    rows = len(raw_data)
    rec_data = []
    for i in range(rows):
        rec_data.append([dt.strip() for dt in raw_data[i]])
    return rec_data


def get_run_time():
    """return the run start time in the format of YYMMDD_HHMMSS."""
    cur_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    return cur_time


def rm_list_item(in_list, item):
    """remove a specific string from a list if any."""
    while item in in_list:
        in_list.remove(item)
    return in_list


def txtfile_rd(dir):
    """read a text file"""
    file = open(dir)
    ctnt = file.read()
    file.close()
    return ctnt


def txtfile_wr(dir, ctnt):
    """write a text file"""
    file = open(dir, "w")
    file.write(ctnt)
    file.close()


def list_upper(in_list):
    """convert each item in a list to upper case."""
    out_list = [item.upper() for item in in_list]
    return out_list


def list_strip(in_list):
    """strip the whitespaces before/after each item in a list"""
    out_list = [item.strip() for item in in_list]
    return out_list


def rm_ext(full_name):
    """remove the file extension from a file name"""
    if "." in full_name:
        tmp = full_name.split(".")
        name = ".".join(tmp[:-1])
    else:
        name = full_name
    return name


def unique_list(in_list):
    """remove duplicates in a list"""
    out_list = list(dict.fromkeys(in_list))
    return out_list


def get_cols_out_of_list_of_list(in_list, i_col):
    """get the specified columns out of a list of list"""
    out_list = []
    for i_list in in_list:
        i_row = []
        for index in i_col:
            i_row.extend([i_list[index]])
        out_list.append(i_row)
    return out_list


def get_str_after_last_symbol(in_str, symbol):
    """get the string after the last specific symbol"""
    out_str = in_str.split(symbol)[-1]
    return out_str


def get_str_before_last_symbol(in_str, symbol):
    """get the string before the last specific symbol"""
    out_str = symbol.join(in_str.split(symbol)[:-1])
    return out_str


def get_str_before_last_n_symbol(in_str, symbol, index):
    """get the string before the last n specific symbol"""
    out_str = symbol.join(in_str.split(symbol)[:-index])
    return out_str


def get_str_before_first_symbol(in_str, symbol):
    """get the string before the first specific symbol"""
    out_str = in_str.split(symbol)[0]
    return out_str


def str2dict(in_str, del_high, del_low):
    """Break a string with two-level separators to a dict."""
    out_dict = {}
    if in_str != "":
        list_tmp = in_str.split(del_high)
        for i_list in list_tmp:
            item = list_strip(i_list.split(del_low))
            out_dict[item[0]] = item[1:]
    return out_dict


def str2listoflist(in_str, del_high, del_low):
    """Break a string with two-level separators to a list of list."""
    out_list = []
    if in_str != "":
        list_tmp = in_str.split(del_high)
        for i_list in list_tmp:
            if i_list != "":
                item = list_strip(i_list.split(del_low))
                out_list.append(item)
    return out_list


def exist_dir(dir):
    """Check if a dir/file exists."""
    if os.path.exists(dir):
        print("[Exist]: " + dir)
    else:
        print("[Missing]: " + dir)


def csv2dict(csv_dir, start_row=1):
    """Import a csv file and convert its contents to a dict. The key is
    based on the 1st col contents.
    """
    ctnt = txtfile_rd(csv_dir)
    ctnt_list = ctnt.split("\n")
    col_title = striped_str2list(ctnt_list[0], ",")

    ctnt_dict = {}
    rows = len(ctnt_list)
    for i in range(start_row, rows):
        rec_data = striped_str2list(ctnt_list[i], ",")
        i_key = rec_data[0]
        if i_key != "":
            if i_key not in ctnt_dict:
                ctnt_dict[i_key] = [rec_data]
            else:
                ctnt_dict[i_key].append(rec_data)
    return ctnt_dict, col_title


def striped_str2list(in_str, separator):
    """Split a string to a list based on a certain separator and remove all
    white spaces before and after the list item.
    """
    out_list = list_strip(in_str.split(separator))
    return out_list


def listoflist2dictofdict(in_list):
    """Convert a list of list to a dict of dict.
    The top level dict keys are named after the 1st col from 2nd row.
    The second level dict keys are named after the header from the
    2nd col.
    """
    headers = in_list[0]
    ctnts = in_list[1:]
    headers_len = len(headers)
    # convert to a dict of dict
    out_dict = {}
    for ctnt in ctnts:
        dict_tmp = {}
        for i in range(1, headers_len):
            dict_tmp[headers[i]] = ctnt[i]
        out_dict[ctnt[0]] = dict_tmp
    return out_dict


def listoflist2dictcol(in_list):
    """Convert a list of list to a dict.
    The 1st row/list headers are treated as keys. Each column of the remaining
    rows/lists forms the value to each key.
    The input list of list must be of regular shape. Items in the 1st list must
    be unique.
    """
    # To write checks in the future for regular shape and unique header list
    headers = in_list[0]
    ctnts = transpose_listoflist(in_list[1:])
    out_dict = dict(zip(headers, ctnts))
    return out_dict


def transpose_listoflist(in_list):
    """Transpose the input list of list like a matrix."""
    out_list = [[row[i] for row in in_list] for i in range(len(in_list[0]))]
    return out_list


def split_str_by_guess(in_str):
    """Split a string by trying the delimiters in the following sequence.
    Assume there is only one type of delimiter. White spaces before and
    after each item are removed.
    '\n' > ',' > ';'
    """
    if "\n" in in_str:
        out_list = in_str.split("\n")
    elif "," in in_str:
        out_list = in_str.split(",")
    else:
        out_list = in_str.split(";")
    return list_strip(out_list)


def csv2listoflists(file):
    """Read in a csv file and store the contents as a list of lists."""
    with open(file) as csvfile:
        csv_obj = csv.reader(csvfile)
        raw_data = [item for item in csv_obj]
    return raw_data


def export_dict_to_yaml(data, dir):
    """export the dict as a yaml file."""
    yaml = YAML(typ="safe")
    with open(dir, "w") as yamlfile:
        yaml.dump(data, yamlfile)


def load_yaml_to_dict(dir):
    """load a yaml file to a dict."""
    yaml = YAML(typ="safe")
    with open(dir) as yamlfile:
        out_dict = yaml.load(yamlfile)
    return out_dict


def expand_home_dir(in_dir):
    """expand ~ as the home dir."""
    home = expanduser("~")
    out_dir = in_dir.replace("~", home)
    return out_dir


def either_case(ltr):
    """generate regex for both cases of a letter, skip for nonalpha."""
    out_str = f"[{ltr.lower()}{ltr.upper()}]" if ltr.isalpha() else ltr
    return out_str


def img2str(img_dir):
    """convert an image file to a string."""
    with open(img_dir, "rb") as f:
        img_str = base64.b64encode(f.read()).decode()
    return img_str


class Vividict(dict):
    """Implement nested dict
    Copied from https://stackoverflow.com/questions/635483/what-is-
    the-best-way-to-implement-nested-dictionaries
    """

    def __missing__(self, key):
        value = self[key] = type(self)()  # retain local pointer to value
        return value  # faster to return than dict lookup
