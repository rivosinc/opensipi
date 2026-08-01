# SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Characterization tests for pure common helpers."""

import pytest

from opensipi.util import common


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("folder", f"folder{common.SL}"),
        (f"folder{common.SL}", f"folder{common.SL}"),
        ("", common.SL),
    ],
)
def test_slash_ending(raw, expected):
    assert common.slash_ending(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (r"one\two\three", common.SL.join(("one", "two", "three"))),
        ("one/two/three", common.SL.join(("one", "two", "three"))),
        ("plain", "plain"),
    ],
)
def test_rectify_dir_normalizes_path_separators(raw, expected):
    assert common.rectify_dir(raw) == expected


def test_rectify_data_strips_cells_without_mutating_input():
    raw = [[" name ", " Value"], [" keep ", "Mixed Case "]]
    assert common.rectify_data(raw) == [["name", "Value"], ["keep", "Mixed Case"]]
    assert raw[0][0] == " name "


@pytest.mark.parametrize(
    ("values", "expected"),
    [([" a ", "B", " c"], ["A", "B", "C"]), ([], [])],
)
def test_list_whitespace_and_case_helpers(values, expected):
    assert common.list_upper(common.list_strip(values)) == expected


def test_rm_list_item_removes_every_match_in_place():
    values = ["keep", "drop", "drop", "last"]
    result = common.rm_list_item(values, "drop")
    assert result is values
    assert values == ["keep", "last"]


def test_unique_list_preserves_first_occurrence_order():
    values = ["b", "a", "b", "c", "a"]
    result = common.unique_list(values)
    assert result == ["b", "a", "c"]
    assert result is not values


@pytest.mark.parametrize(
    ("function", "args", "expected"),
    [
        (common.lol_numerical_add_list, ([[1.8, 2.2], [-2.5, 4]], [0.5, 1.1]), [[2, 3], [-2, 5]]),
        (common.lol_numerical_add_num, ([[1.8, -2.5]], 0.5), [[2, -2]]),
        (common.intfy_list, (["3.9", "-2.8", "1e2"],), [3, -2, 100]),
    ],
)
def test_numeric_transforms(function, args, expected):
    assert function(*args) == expected


@pytest.mark.parametrize(
    ("name", "expected"),
    [("archive.tar.gz", "archive.tar"), ("README", "README"), (".hidden", "")],
)
def test_remove_extension(name, expected):
    assert common.rm_ext(name) == expected


@pytest.mark.parametrize(
    ("function", "args", "expected"),
    [
        (common.get_str_after_last_symbol, ("a/b/c", "/"), "c"),
        (common.get_str_before_last_symbol, ("a/b/c", "/"), "a/b"),
        (common.get_str_before_last_symbol, ("plain", "/"), ""),
        (common.split_str_at_last_symbol, ("a/b/c", "/"), ("a/b", "c")),
        (common.get_str_before_last_n_symbol, ("a/b/c/d", "/", 2), "a/b"),
        (common.get_str_before_first_symbol, ("a/b/c", "/"), "a"),
    ],
)
def test_string_split_helpers(function, args, expected):
    assert function(*args) == expected


def test_two_level_string_reshaping():
    raw = " U1, 1, 2 ; U2, 5 ; U1, 9 "
    assert common.str2dict(raw, ";", ",") == {"U1": ["9"], "U2": ["5"]}
    assert common.str2listoflist(raw, ";", ",") == [
        ["U1", "1", "2"],
        ["U2", "5"],
        ["U1", "9"],
    ]


def test_table_reshaping_preserves_requested_order():
    table = [["id", "left", "right"], ["a", 1, 2], ["b", 3, 4]]
    assert common.get_cols_out_of_list_of_list(table[1:], [2, 0]) == [[2, "a"], [4, "b"]]
    assert common.listoflist2dictofdict(table) == {
        "a": {"left": 1, "right": 2},
        "b": {"left": 3, "right": 4},
    }
    assert common.listoflist2dictcol(table) == {
        "id": ["a", "b"],
        "left": [1, 3],
        "right": [2, 4],
    }
    assert common.transpose_listoflist(table[1:]) == [["a", "b"], [1, 3], [2, 4]]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (" a\n b,c;d ", ["a", "b,c;d"]),
        (" a, b;c ", ["a", "b;c"]),
        (" a; b ", ["a", "b"]),
        ("single", ["single"]),
    ],
)
def test_split_str_by_guess_uses_documented_delimiter_precedence(raw, expected):
    assert common.split_str_by_guess(raw) == expected


@pytest.mark.parametrize(
    ("character", "expected"),
    [("a", "[aA]"), ("Z", "[zZ]"), ("7", "7"), ("_", "_")],
)
def test_either_case(character, expected):
    assert common.either_case(character) == expected


def test_vividict_creates_and_stores_missing_levels():
    values = common.Vividict()
    values["outer"]["inner"] = 3
    assert values == {"outer": {"inner": 3}}
    assert isinstance(values["outer"], common.Vividict)
