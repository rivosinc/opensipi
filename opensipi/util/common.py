# SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
Author: yanshengw@
Last updated on Jul. 29, 2024

Description:
    This Python3 module contains functions that are commonly used by the
OpenSIPI application.

    The helpers fall into a few groups: path handling, which keeps the
application portable between Windows and Linux; text and file IO; and small
list, string, and dict reshaping utilities used to massage the input tables
into the structures the platform works with.

    The reshaping helpers are deliberately unguarded. They assume the caller
already validated the shape of the data, so a malformed input sheet tends to
surface here as an ``IndexError`` rather than as a domain exception.

Attributes:
    SL (str): The path separator for the current OS, ``"\\\\"`` on Windows and
        ``"/"`` elsewhere. Paths across the application are built by joining on
        this constant rather than by hardcoding a separator.
"""

import base64
import csv
import os
from datetime import datetime
from os.path import expanduser

from ruamel.yaml import YAML


def get_path_separator():
    """Get the right symbol to separate the path.

    Returns:
        str: ``"\\\\"`` on Windows, ``"/"`` on Mac, Linux, and BSD.

    Raises:
        UnboundLocalError: On an OS that is neither ``nt`` nor ``posix``.
    """
    if os.name == "nt":  # Windows OS
        symbol = "\\"
    elif os.name == "posix":  # Mac/Linux/BSD
        symbol = "/"
    return symbol


SL = get_path_separator()


def get_root_dir():
    """Get the root directory where the tool_config folder is created.

    This is where the application looks for the ``opensipi_config`` folder.

    Returns:
        str: ``"C:\\\\"`` on Windows, the value of ``$HOME`` elsewhere, always
        separator-ending.

    Raises:
        UnboundLocalError: On an OS that is neither ``nt`` nor ``posix``.
    """
    if os.name == "nt":  # Windows OS
        root = "C:\\"
    elif os.name == "posix":  # Mac/Linux/BSD
        root = os.getenv("HOME") + SL
    return root


def get_dir():
    """Get commonly used dir.

    The directories are derived from the location of this source file, so they
    follow the installed package wherever it lives.

    Returns:
        tuple: A 3-tuple ``(root_dir, scripts_dir, template_dir)`` of
        separator-ending paths, being respectively the grandparent of the
        package, its parent, and the ``templates`` folder inside the package.
    """
    real_dir = os.path.dirname(os.path.realpath(__file__))
    # process path
    dir_list = real_dir.split(SL)
    root_dir = SL.join(dir_list[:-3]) + SL
    scripts_dir = SL.join(dir_list[:-2]) + SL
    pkg_dir = SL.join(dir_list[:-1]) + SL
    template_dir = pkg_dir + "templates" + SL
    return root_dir, scripts_dir, template_dir


def make_dir(tgt_dir):
    """Make dir if not existing.

    Intermediate directories are created as needed, and an already existing
    directory is left untouched.

    Args:
        tgt_dir (str): Directory path to create.
    """
    if not os.path.exists(tgt_dir):
        os.makedirs(tgt_dir)


def slash_ending(dir):
    """Add a path separator at the end of a dir if not existing.

    Args:
        dir (str): Directory path, with or without a trailing separator.

    Returns:
        str: The path, guaranteed to end with the OS path separator, so that
        a file name can be concatenated onto it directly.
    """
    if dir[-1:] != SL:
        dir_slash = dir + SL
    else:
        dir_slash = dir
    return dir_slash


def rectify_dir(dir):
    """Correct dir separators to the ones the current OS uses.

    Lets a path written on one OS, such as a Windows path pasted into an input
    sheet, be used on another.

    Args:
        dir (str): Directory path using either separator.

    Returns:
        str: The path with its separators replaced by :data:`SL`.

    Note:
        Only one separator style is converted. A path mixing ``\\\\`` and ``/``
        has its backslashes converted and its forward slashes left as they are.
    """
    new_dir = dir
    if "\\" in dir:
        new_dir = SL.join(dir.split("\\"))
    elif "/" in dir:
        new_dir = SL.join(dir.split("/"))
    return new_dir


def rectify_data(raw_data):
    """Strip white spaces before and after strings in the raw data.

    Applied to every input sheet as it is read, so that the rest of the
    application never has to worry about stray spacing a user left in a cell.

    Args:
        raw_data (list of list of str): The raw sheet contents.

    Returns:
        list of list of str: A new list of lists with every cell stripped.
    """
    rows = len(raw_data)
    rec_data = []
    for i in range(rows):
        rec_data.append([dt.strip() for dt in raw_data[i]])
    return rec_data


def get_run_time():
    """Return the run start time in the format of YYMMDD_HHMMSS.

    Returns:
        str: The current local time, e.g. ``"20240109_104753"``. Used to name
        the ``Run_...`` folder and the simulation files of a run.
    """
    cur_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    return cur_time


def rm_list_item(in_list, item):
    """Remove a specific string from a list if any.

    Every occurrence is removed, not just the first.

    Args:
        in_list (list): The list to remove from.
        item: The value to remove.

    Returns:
        list: The same list object, for convenience.

    Note:
        ``in_list`` is modified in place, so the caller's list changes too.
    """
    while item in in_list:
        in_list.remove(item)
    return in_list


def txtfile_rd(dir):
    """Read a text file.

    Args:
        dir (str): Full path of the file to read.

    Returns:
        str: The whole file content.
    """
    file = open(dir)
    ctnt = file.read()
    file.close()
    return ctnt


def txtfile_wr(dir, ctnt):
    """Write a text file, replacing any existing content.

    Args:
        dir (str): Full path of the file to write.
        ctnt (str): The content to write.
    """
    file = open(dir, "w")
    file.write(ctnt)
    file.close()


def list_upper(in_list):
    """Convert each item in a list to upper case.

    Args:
        in_list (list of str): The strings to convert.

    Returns:
        list of str: The upper-cased strings.
    """
    out_list = [item.upper() for item in in_list]
    return out_list


def list_strip(in_list):
    """Strip the whitespaces before/after each item in a list.

    Args:
        in_list (list of str): The strings to strip.

    Returns:
        list of str: The stripped strings.
    """
    out_list = [item.strip() for item in in_list]
    return out_list


def lol_numerical_add_list(in_lol, in_list):
    """Add an offset list to each item of the list of list.

    The offsets are applied element-wise, so ``in_list`` acts as a per-column
    offset applied to every row.

    Args:
        in_lol (list of list of numbers): The rows to offset.
        in_list (list of numbers): One offset per column.

    Returns:
        list of list of int: The offset rows, each value truncated to int.
        A row longer than ``in_list`` is silently cut short to its length.
    """
    out_lol = []
    for item in in_lol:
        out_lol.append([int(x + y) for x, y in zip(item, in_list)])
    return out_lol


def lol_numerical_add_num(in_lol, in_num):
    """Add an offset number to each item of the list of list.

    Args:
        in_lol (list of list of numbers): The rows to offset.
        in_num (number): The offset applied to every value.

    Returns:
        list of list of int: The offset rows, each value truncated to int.
    """
    out_lol = []
    for item in in_lol:
        out_lol.append([int(x + in_num) for x in item])
    return out_lol


def rm_ext(full_name):
    """Remove the file extension from a file name.

    Args:
        full_name (str): File name, with or without an extension.

    Returns:
        str: The name up to the last dot, or the name unchanged if it holds no
        dot at all.
    """
    if "." in full_name:
        tmp = full_name.split(".")
        name = ".".join(tmp[:-1])
    else:
        name = full_name
    return name


def unique_list(in_list):
    """Remove duplicates in a list.

    Args:
        in_list (list): The list to deduplicate. Items must be hashable.

    Returns:
        list: The items with duplicates dropped, first occurrence order kept.
    """
    out_list = list(dict.fromkeys(in_list))
    return out_list


def intfy_list(in_list):
    """Apply int to each item of a list of number string.

    The conversion goes through float first, so exponent notation such as
    ``"1e6"`` is accepted as well as plain digits.

    Args:
        in_list (list of str): The number strings to convert.

    Returns:
        list of int: The converted numbers, truncated toward zero.

    Raises:
        ValueError: If an item is not parsable as a number.
    """
    out_list = [int(float(item)) for item in in_list]
    return out_list


def get_cols_out_of_list_of_list(in_list, i_col):
    """Get the specified columns out of a list of list.

    Args:
        in_list (list of list): The rows to select from.
        i_col (list of int): Zero-based column indices to keep, in the order
            they should appear in the result.

    Returns:
        list of list: One row per input row, holding only the selected columns.

    Raises:
        IndexError: If a row is shorter than the largest requested index.
    """
    out_list = []
    for i_list in in_list:
        i_row = []
        for index in i_col:
            i_row.extend([i_list[index]])
        out_list.append(i_row)
    return out_list


def get_str_after_last_symbol(in_str, symbol):
    """Get the string after the last specific symbol.

    Args:
        in_str (str): The string to split.
        symbol (str): The separator to look for.

    Returns:
        str: The trailing part, or the whole string if the symbol is absent.
    """
    out_str = in_str.split(symbol)[-1]
    return out_str


def get_str_before_last_symbol(in_str, symbol):
    """Get the string before the last specific symbol.

    Args:
        in_str (str): The string to split.
        symbol (str): The separator to look for.

    Returns:
        str: The leading part, with any earlier occurrence of the symbol kept.
        An empty string if the symbol is absent.
    """
    out_str = symbol.join(in_str.split(symbol)[:-1])
    return out_str


def split_str_at_last_symbol(in_str, symbol):
    """Split the string at the last specific symbol.

    Args:
        in_str (str): The string to split.
        symbol (str): The separator to look for.

    Returns:
        tuple: A 2-tuple ``(before_symbol_str, after_symbol_str)``. If the
        symbol is absent, the first item is empty and the second is the whole
        string.
    """
    str_list = in_str.split(symbol)
    after_symbol_str = str_list[-1]
    before_symbol_str = symbol.join(str_list[:-1])
    return before_symbol_str, after_symbol_str


def get_str_before_last_n_symbol(in_str, symbol, index):
    """Get the string before the last n specific symbol.

    Used to climb a path by a fixed number of levels.

    Args:
        in_str (str): The string to split.
        symbol (str): The separator to look for.
        index (int): How many trailing segments to drop.

    Returns:
        str: The leading part with ``index`` trailing segments removed.
    """
    out_str = symbol.join(in_str.split(symbol)[:-index])
    return out_str


def get_str_before_first_symbol(in_str, symbol):
    """Get the string before the first specific symbol.

    Args:
        in_str (str): The string to split.
        symbol (str): The separator to look for.

    Returns:
        str: The leading part, or the whole string if the symbol is absent.
    """
    out_str = in_str.split(symbol)[0]
    return out_str


def str2dict(in_str, del_high, del_low):
    """Break a string with two-level separators to a dict.

    The high-level separator splits the string into entries; within an entry,
    the low-level separator splits off the key from its values. This is the
    shape several input cells use, e.g. ``"U1, 1, 2; U2, 5"``.

    Args:
        in_str (str): The string to break up. An empty string yields an empty
            dict.
        del_high (str): The separator between entries.
        del_low (str): The separator between an entry's key and its values.

    Returns:
        dict: First item of each entry to the list of that entry's remaining
        items, which is empty when the entry holds a key alone. A repeated key
        keeps only its last entry.
    """
    out_dict = {}
    if in_str != "":
        list_tmp = in_str.split(del_high)
        for i_list in list_tmp:
            item = list_strip(i_list.split(del_low))
            out_dict[item[0]] = item[1:]
    return out_dict


def str2listoflist(in_str, del_high, del_low):
    """Break a string with two-level separators to a list of list.

    The list counterpart of :func:`str2dict`, keeping the entries in order and
    tolerating repeated first items.

    Args:
        in_str (str): The string to break up. An empty string yields an empty
            list.
        del_high (str): The separator between entries.
        del_low (str): The separator within an entry.

    Returns:
        list of list of str: One inner list per non-empty entry, items
        stripped.
    """
    out_list = []
    if in_str != "":
        list_tmp = in_str.split(del_high)
        for i_list in list_tmp:
            if i_list != "":
                item = list_strip(i_list.split(del_low))
                out_list.append(item)
    return out_list


def exist_dir(dir):
    """Check if a dir/file exists and print the verdict.

    A debugging aid. The result is printed rather than returned, so this is not
    usable as a condition.

    Args:
        dir (str): The path to check.
    """
    if os.path.exists(dir):
        print("[Exist]: " + dir)
    else:
        print("[Missing]: " + dir)


def csv2dict(csv_dir, start_row=1):
    """Import a csv file and convert its contents to a dict.

    The key is based on the 1st col contents. Rows sharing a first column are
    grouped under that key, which is how a multi-row record is kept together.
    Rows with an empty first column are dropped.

    Args:
        csv_dir (str): Full path of the csv file.
        start_row (int, optional): Zero-based index of the first data row.
            Defaults to ``1``, skipping the header.

    Returns:
        tuple: A 2-tuple ``(ctnt_dict, col_title)``, where ``ctnt_dict`` maps
        the first column value to the list of its rows, each row being a list
        of stripped cell strings, and ``col_title`` is the header row.

    Note:
        The file is split on commas rather than parsed as csv, so a quoted
        cell holding a comma is split apart. Use :func:`csv2listoflists` where
        that matters.
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
    """Split a string to a list and strip each item.

    Splits on a certain separator and removes all white spaces before and after
    each list item.

    Args:
        in_str (str): The string to split.
        separator (str): The separator to split on.

    Returns:
        list of str: The stripped items. An empty input yields ``[""]``.
    """
    out_list = list_strip(in_str.split(separator))
    return out_list


def listoflist2dictofdict(in_list):
    """Convert a list of list to a dict of dict.

    The top level dict keys are named after the 1st col from 2nd row. The
    second level dict keys are named after the header from the 2nd col, so the
    first column acts as the record name and is not repeated inside the record.

    Args:
        in_list (list of list): The rows, first row being the header.

    Returns:
        dict: First column value to a dict of the remaining columns, keyed by
        their header. A repeated first column value keeps only its last row.

    Raises:
        IndexError: If a row is shorter than the header.
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
    """Convert a list of list to a column-oriented dict.

    The 1st row/list headers are treated as keys. Each column of the remaining
    rows/lists forms the value to each key. The input list of list must be of
    regular shape. Items in the 1st list must be unique.

    Args:
        in_list (list of list): The rows, first row being the header.

    Returns:
        dict: Header to the list of that column's values, one item per data
        row.

    Raises:
        IndexError: If the rows are not all the same length.
    """
    # To write checks in the future for regular shape and unique header list
    headers = in_list[0]
    ctnts = transpose_listoflist(in_list[1:])
    out_dict = dict(zip(headers, ctnts))
    return out_dict


def transpose_listoflist(in_list):
    """Transpose the input list of list like a matrix.

    Args:
        in_list (list of list): The rows to transpose. Must be non-empty and of
            regular shape.

    Returns:
        list of list: The columns of the input, as rows.

    Raises:
        IndexError: If the input is empty or its rows differ in length.
    """
    out_list = [[row[i] for row in in_list] for i in range(len(in_list[0]))]
    return out_list


def split_str_by_guess(in_str):
    r"""Split a string by guessing which delimiter was used.

    The delimiters are tried in the sequence ``'\n'`` > ``','`` > ``';'`` and
    the first one present wins, so only one type of delimiter is assumed. This
    lets a user list items in an input cell however they find natural. White
    spaces before and after each item are removed.

    Args:
        in_str (str): The string to split.

    Returns:
        list of str: The stripped items. A string holding none of the three
        delimiters yields a single-item list.
    """
    if "\n" in in_str:
        out_list = in_str.split("\n")
    elif "," in in_str:
        out_list = in_str.split(",")
    else:
        out_list = in_str.split(";")
    return list_strip(out_list)


def csv2listoflists(file):
    """Read in a csv file and store the contents as a list of lists.

    Unlike :func:`csv2dict`, this goes through the csv module, so quoted cells
    holding commas survive intact.

    Args:
        file (str): Full path of the csv file.

    Returns:
        list of list of str: One inner list per row, cells unstripped.
    """
    with open(file) as csvfile:
        csv_obj = csv.reader(csvfile)
        raw_data = [item for item in csv_obj]
    return raw_data


def export_dict_to_yaml(data, dir):
    """Export the dict as a yaml file.

    Used to hand configuration between the stages of a run, so that a later
    stage can pick up where an earlier one left off.

    Args:
        data (dict): The data to write. Must hold only plain types, as the safe
            dumper is used.
        dir (str): Full path of the yaml file to write.
    """
    yaml = YAML(typ="safe")
    with open(dir, "w") as yamlfile:
        yaml.dump(data, yamlfile)


def load_yaml_to_dict(dir):
    """Load a yaml file to a dict.

    Args:
        dir (str): Full path of the yaml file to read.

    Returns:
        dict: The parsed content.
    """
    yaml = YAML(typ="safe")
    with open(dir) as yamlfile:
        out_dict = yaml.load(yamlfile)
    return out_dict


def expand_home_dir(in_dir):
    """Expand ~ as the home dir.

    Args:
        in_dir (str): A path possibly holding ``~``.

    Returns:
        str: The path with every ``~`` replaced by the home directory, not just
        a leading one.
    """
    home = expanduser("~")
    out_dir = in_dir.replace("~", home)
    return out_dir


def either_case(ltr):
    """Generate a regex matching both cases of a letter, skip for nonalpha.

    Joined over a word, this builds a case-insensitive glob pattern, which is
    how input files are matched regardless of how their extension is cased.

    Args:
        ltr (str): A single character.

    Returns:
        str: ``"[aA]"`` style bracket expression for a letter, or the character
        unchanged if it is not alphabetic.
    """
    out_str = f"[{ltr.lower()}{ltr.upper()}]" if ltr.isalpha() else ltr
    return out_str


def img2str(img_dir):
    """Convert an image file to a string.

    Lets a figure be embedded directly in an html report instead of being
    referenced as a separate file.

    Args:
        img_dir (str): Full path of the image file.

    Returns:
        str: The file content, base64 encoded and decoded to ascii text.
    """
    with open(img_dir, "rb") as f:
        img_str = base64.b64encode(f.read()).decode()
    return img_str


class Vividict(dict):
    """Implement nested dict

    Copied from https://stackoverflow.com/questions/635483/what-is-
    the-best-way-to-implement-nested-dictionaries

    Reading a missing key creates an empty ``Vividict`` at that key instead of
    raising, so an arbitrarily deep path can be assigned in one statement
    without creating each level first.
    """

    def __missing__(self, key):
        """Create and store an empty nested dict for a missing key.

        Args:
            key: The key that was not found.

        Returns:
            Vividict: The newly stored empty nested dict.

        Note:
            Merely reading a missing key inserts it, so this type never raises
            ``KeyError`` and cannot be used to test for a key's presence with
            ``[]``. Use ``in`` for that.
        """
        value = self[key] = type(self)()  # retain local pointer to value
        return value  # faster to return than dict lookup
