# SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Characterization tests for common helpers with external state or I/O."""

from datetime import datetime

import pytest

from opensipi.util import common


def test_make_dir_creates_nested_directory_and_is_idempotent(tmp_path):
    target = tmp_path / "nested" / "directory"
    common.make_dir(target)
    common.make_dir(target)
    assert target.is_dir()


def test_text_io_replaces_and_reads_content(tmp_path):
    path = tmp_path / "sample.txt"
    common.txtfile_wr(path, "first")
    common.txtfile_wr(path, "second\nline")
    assert common.txtfile_rd(path) == "second\nline"


def test_csv_readers_preserve_their_distinct_parsing_behavior(temp_csv_builder):
    path = temp_csv_builder(
        [["key", "value"], ["alpha", "one, two"], ["alpha", "three"], ["", "ignored"]]
    )
    rows = common.csv2listoflists(path)
    grouped, headers = common.csv2dict(path)
    assert rows == [
        ["key", "value"],
        ["alpha", "one, two"],
        ["alpha", "three"],
        ["", "ignored"],
    ]
    assert headers == ["key", "value"]
    assert grouped == {
        "alpha": [["alpha", '"one', 'two"'], ["alpha", "three"]],
    }


def test_yaml_round_trip_plain_data(tmp_path):
    path = tmp_path / "config.yaml"
    data = {"name": "run", "values": [1, 2], "nested": {"enabled": True}}
    common.export_dict_to_yaml(data, path)
    assert common.load_yaml_to_dict(path) == data


def test_img2str_returns_ascii_base64(tmp_path):
    path = tmp_path / "image.bin"
    path.write_bytes(b"\x00OpenSIPI\xff")
    assert common.img2str(path) == "AE9wZW5TSVBJ/w=="


@pytest.mark.parametrize(("os_name", "expected"), [("nt", "\\"), ("posix", "/")])
def test_path_separator_by_os(monkeypatch, os_name, expected):
    monkeypatch.setattr(common.os, "name", os_name)
    assert common.get_path_separator() == expected


def test_path_separator_rejects_unknown_os_by_existing_failure(monkeypatch):
    monkeypatch.setattr(common.os, "name", "other")
    with pytest.raises(UnboundLocalError):
        common.get_path_separator()


def test_root_dir_uses_home_on_posix(monkeypatch):
    monkeypatch.setattr(common.os, "name", "posix")
    monkeypatch.setenv("HOME", "/controlled/home")
    assert common.get_root_dir() == f"/controlled/home{common.SL}"


def test_root_dir_uses_drive_root_on_windows(monkeypatch):
    monkeypatch.setattr(common.os, "name", "nt")
    assert common.get_root_dir() == "C:\\"


def test_expand_home_dir_replaces_every_tilde(monkeypatch):
    monkeypatch.setattr(common, "expanduser", lambda value: "/controlled/home")
    assert (
        common.expand_home_dir("~/project/~cache")
        == "/controlled/home/project//controlled/homecache"
    )


def test_get_run_time_uses_datetime_without_real_clock(monkeypatch):
    class FrozenDateTime:
        @classmethod
        def now(cls):
            return datetime(2025, 3, 4, 5, 6, 7)

    monkeypatch.setattr(common, "datetime", FrozenDateTime)
    assert common.get_run_time() == "20250304_050607"
