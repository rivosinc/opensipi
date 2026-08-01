# SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Hermetic characterization tests for Touchstone post-processing."""

import math
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock, call

import matplotlib
import numpy as np
import pytest

import opensipi.touchstone as touchstone_module
from opensipi.touchstone import TouchStone
from opensipi.util.common import SL


class FakeNetwork:
    """Small, complete network double for the interfaces TouchStone consumes."""

    def __init__(self, f, s_db=None, z_mag=None, z_rad_unwrap=None):
        self.f = np.asarray(f, dtype=float)
        port_count = 1
        for values in (s_db, z_mag, z_rad_unwrap):
            if values is not None:
                port_count = np.asarray(values).shape[1]
                break
        shape = (len(self.f), port_count, port_count)
        self.s_db = np.asarray(s_db if s_db is not None else np.zeros(shape), dtype=float)
        self.z_mag = np.asarray(z_mag if z_mag is not None else np.ones(shape), dtype=float)
        self.z_rad_unwrap = np.asarray(
            z_rad_unwrap if z_rad_unwrap is not None else np.zeros(shape), dtype=float
        )
        self.number_of_ports = port_count
        self.frequency = SimpleNamespace(npoints=len(self.f))
        self.time_step_calls = []

    def copy(self):
        return deepcopy(self)

    def without_port(self, port_index):
        reduced = self.copy()
        reduced.s_db = np.delete(np.delete(reduced.s_db, port_index, axis=1), port_index, axis=2)
        reduced.z_mag = np.delete(np.delete(reduced.z_mag, port_index, axis=1), port_index, axis=2)
        reduced.z_rad_unwrap = np.delete(
            np.delete(reduced.z_rad_unwrap, port_index, axis=1), port_index, axis=2
        )
        reduced.number_of_ports -= 1
        return reduced

    def plot_z_time_step(self, output_port, input_port, label):
        self.time_step_calls.append((output_port, input_port, label))


class FakeConversionNetwork(FakeNetwork):
    def __init__(self, f, port_count=4):
        values = np.zeros((len(f), port_count, port_count))
        super().__init__(f, s_db=values)
        self.renumber_calls = []
        self.se2gmm_calls = []
        self.write_calls = []

    def renumber(self, old_order, new_order):
        self.renumber_calls.append((list(old_order), list(new_order)))

    def se2gmm(self, p):
        self.se2gmm_calls.append(p)

    def write_touchstone(self, **kwargs):
        self.write_calls.append(kwargs)


class FakeTdrNetwork(FakeNetwork):
    def __init__(self, f, port_count=4):
        values = np.zeros((len(f), port_count, port_count))
        super().__init__(f, s_db=values)
        self.extrapolate_calls = []
        self.resample_calls = []

    def extrapolate_to_dc(self, kind):
        extrapolated = self.copy()
        extrapolated.extrapolate_calls.append(kind)
        if extrapolated.f[0] > 0:
            extrapolated.f = np.insert(extrapolated.f, 0, 0.0)
            extrapolated.frequency = SimpleNamespace(npoints=len(extrapolated.f))
        return extrapolated

    def resample(self, frequencies):
        self.resample_calls.append(list(frequencies))
        self.f = np.asarray(frequencies, dtype=float)
        self.frequency = SimpleNamespace(npoints=len(self.f))


class LookupNetwork:
    """Network double implementing scikit-rf's nearest-frequency string lookup."""

    def __init__(self, frequencies, magnitudes, angles):
        self.frequencies = np.asarray(frequencies, dtype=float)
        self.magnitudes = np.asarray(magnitudes, dtype=float)
        self.angles = np.asarray(angles, dtype=float)

    def __getitem__(self, frequency):
        target = float(frequency)
        index = int(np.argmin(np.abs(self.frequencies - target)))
        return SimpleNamespace(
            f=np.asarray([self.frequencies[index]]),
            z_mag=np.asarray([[[self.magnitudes[index]]]]),
            z_rad_unwrap=np.asarray([[[self.angles[index]]]]),
        )


class SparseLookupNetwork:
    """Return two same-side samples to exercise the interpolation warning path."""

    def __getitem__(self, frequency):
        if float(frequency) == 100.0:
            sample = (80.0, 8.0, 0.8)
        else:
            sample = (90.0, 9.0, 0.9)
        return SimpleNamespace(
            f=np.asarray([sample[0]]),
            z_mag=np.asarray([[[sample[1]]]]),
            z_rad_unwrap=np.asarray([[[sample[2]]]]),
        )


class PyplotRecorder:
    """Record plot semantics without creating GUI windows or image files."""

    def __init__(self):
        self.figures = []
        self.plots = []
        self.legend_count = 0
        self.titles = []
        self.xscales = []
        self.yscales = []
        self.xlabels = []
        self.ylabels = []
        self.grids = []
        self.saved = []
        self.close_count = 0

    def figure(self, **kwargs):
        self.figures.append(kwargs)

    def plot(self, *args, **kwargs):
        self.plots.append((args, kwargs))

    def legend(self):
        self.legend_count += 1

    def title(self, value):
        self.titles.append(value)

    def xscale(self, value):
        self.xscales.append(value)

    def yscale(self, value):
        self.yscales.append(value)

    def xlabel(self, value):
        self.xlabels.append(value)

    def ylabel(self, value):
        self.ylabels.append(value)

    def grid(self, **kwargs):
        self.grids.append(kwargs)

    def savefig(self, path):
        self.saved.append(path)

    def close(self):
        self.close_count += 1


def test_touchstone_tests_use_headless_agg_backend():
    assert matplotlib.get_backend().lower() == "agg"


def _diagonal_values(frequency_count, port_count):
    values = np.zeros((frequency_count, port_count, port_count), dtype=float)
    for frequency in range(frequency_count):
        for port in range(port_count):
            values[frequency, port, port] = 100 * frequency + port + 1
    return values


def _log_interpolate(target, first_frequency, first_value, second_frequency, second_value):
    return 10 ** (
        np.log10(first_value)
        + (np.log10(target) - np.log10(first_frequency))
        / (np.log10(second_frequency) - np.log10(first_frequency))
        * (np.log10(second_value) - np.log10(first_value))
    )


@pytest.mark.parametrize(
    ("post_process_keys", "expects_conversion"),
    [([], False), (["IL"], False), (["IL_MM"], True), (["RL_MM", "IL"], True)],
)
def test_init_loads_network_and_selects_supported_mixed_mode_processing(
    monkeypatch, post_process_keys, expects_conversion, tmp_path
):
    single_ended = FakeConversionNetwork([1e9, 2e9])
    mixed_mode = FakeConversionNetwork([1e9, 2e9])
    short = object()
    converter = Mock(return_value=mixed_mode)
    monkeypatch.setattr(touchstone_module.rf, "Network", Mock(return_value=single_ended))
    monkeypatch.setattr(TouchStone, "_TouchStone__get_short_block", Mock(return_value=short))
    monkeypatch.setattr(TouchStone, "convert_snp_se2mm", converter)
    info = {
        "file_dir": str(tmp_path / "input.s4p"),
        "key_name": "SIM_A",
        "plt_dir": f"{tmp_path}{SL}",
        "spec_type": {"POST_PROCESS_KEY": post_process_keys},
        "conn_dict": {"MM_ORDER_IN_SE": [0, 1, 2, 3]},
    }

    touchstone = TouchStone(info)

    touchstone_module.rf.Network.assert_called_once_with(info["file_dir"])
    np.testing.assert_array_equal(touchstone.f, np.asarray([1.0, 2.0]))
    assert touchstone.nw is single_ended
    assert touchstone.short0 is short
    assert touchstone.port_num == 4
    assert touchstone.MM_KEY == ["IL_MM", "RL_MM"]
    assert touchstone.nw_mm is (mixed_mode if expects_conversion else single_ended)
    assert converter.call_count == int(expects_conversion)


def test_auto_process_dispatches_every_supported_key_with_network_data(touchstone_factory):
    se_db = np.full((2, 4, 4), 11.0)
    mm_db = np.full((2, 4, 4), 22.0)
    single_ended = SimpleNamespace(s_db=se_db)
    mixed_mode = SimpleNamespace(s_db=mm_db)
    keys = ["ZOPEN", "ZSHORT", "IL", "RL", "IL_MM", "RL_MM", "TDR", "TDR_MM"]
    connectivity = {
        "IL": [[1, 2]],
        "RL": [1],
        "IL_MM": [[1, 2]],
        "RL_MM": [1],
        "TDR": [[1], [2]],
        "TDR_MM": [[1], [2]],
    }
    touchstone = touchstone_factory(
        spec_type={"POST_PROCESS_KEY": [*keys, "UNSUPPORTED"]},
        conn_dict=connectivity,
        nw=single_ended,
        nw_mm=mixed_mode,
    )
    methods = {
        "ZOPEN": Mock(return_value="zopen"),
        "ZSHORT": Mock(return_value="zshort"),
        "IL": Mock(return_value="il"),
        "RL": Mock(return_value="rl"),
        "IL_MM": Mock(return_value="il_mm"),
        "RL_MM": Mock(return_value="rl_mm"),
        "TDR": Mock(return_value="tdr"),
        "TDR_MM": Mock(return_value="tdr_mm"),
    }
    touchstone.plot_zself = methods["ZOPEN"]
    touchstone.plot_zself_shortsns = methods["ZSHORT"]
    touchstone.plot_il = methods["IL"]
    touchstone.plot_rl = methods["RL"]
    touchstone.plot_il_mm = methods["IL_MM"]
    touchstone.plot_rl_mm = methods["RL_MM"]
    touchstone.plot_tdr = methods["TDR"]
    touchstone.plot_tdr_mm = methods["TDR_MM"]

    result = touchstone.auto_process()

    assert result == {
        "ZOPEN": "zopen",
        "ZSHORT": "zshort",
        "IL": "il",
        "RL": "rl",
        "IL_MM": "il_mm",
        "RL_MM": "rl_mm",
        "TDR": "tdr",
        "TDR_MM": "tdr_mm",
    }
    methods["ZOPEN"].assert_called_once_with("ZOPEN")
    methods["ZSHORT"].assert_called_once_with("ZSHORT")
    methods["IL"].assert_called_once_with(connectivity["IL"], se_db, "IL")
    methods["RL"].assert_called_once_with(connectivity["RL"], se_db, "RL")
    methods["IL_MM"].assert_called_once_with(connectivity["IL_MM"], mm_db, "IL_MM")
    methods["RL_MM"].assert_called_once_with(connectivity["RL_MM"], mm_db, "RL_MM")
    methods["TDR"].assert_called_once_with(connectivity["TDR"], single_ended, "TDR")
    methods["TDR_MM"].assert_called_once_with(connectivity["TDR_MM"], mixed_mode, "TDR_MM")


def test_plot_zopen_uses_main_port_diagonals_and_formats_lc(touchstone_factory, tmp_path):
    z_mag = _diagonal_values(2, 4)
    network = FakeNetwork([1e6, 1e8], z_mag=z_mag)
    plot_zmag = Mock()
    get_rlc = Mock(side_effect=[(1.0, 2.345, 3.456), (4.0, 5.678, 6.789)])
    touchstone = touchstone_factory(
        file_dir="source.s4p",
        key_name="SIM",
        plt_dir=f"{tmp_path}{SL}",
        conn_dict={"ZIN": [1, 2]},
        nw=network,
        f=np.asarray([0.001, 0.1]),
    )
    touchstone.plot_zmag = plot_zmag
    touchstone._TouchStone__get_rlc = get_rlc

    result = touchstone.plot_zself("ZOPEN")

    assert result == [
        ["SIM__ZOPEN__Port1", str(tmp_path / "SIM__ZOPEN__Port1.png"), "", "2.35", "3.46"],
        ["SIM__ZOPEN__Port2", str(tmp_path / "SIM__ZOPEN__Port2.png"), "", "5.68", "6.79"],
    ]
    np.testing.assert_array_equal(plot_zmag.call_args_list[0].args[0][0][1], z_mag[:, 0, 0])
    np.testing.assert_array_equal(plot_zmag.call_args_list[1].args[0][0][1], z_mag[:, 1, 1])
    assert get_rlc.call_args_list == [
        call(get_rlc.call_args_list[0].args[0], 0, "source.s4p"),
        call(get_rlc.call_args_list[1].args[0], 1, "source.s4p"),
    ]
    assert all(args.args[0].number_of_ports == 4 for args in get_rlc.call_args_list)


def test_plot_zshort_terminates_aux_ports_from_last_to_first(
    monkeypatch, touchstone_factory, tmp_path
):
    z_mag = _diagonal_values(2, 4)
    network = FakeNetwork([1e6, 1e8], z_mag=z_mag)
    short = object()
    connections = []

    def connect(network_to_reduce, port_index, short_block, short_port):
        connections.append((network_to_reduce.number_of_ports, port_index, short_block, short_port))
        return network_to_reduce.without_port(port_index)

    monkeypatch.setattr(touchstone_module.rf, "connect", connect)
    plot_zmag = Mock()
    get_rlc = Mock(side_effect=[(1.234, 2.345, 3.0), (4.567, 5.678, 6.0)])
    touchstone = touchstone_factory(
        file_dir="source.s4p",
        key_name="SIM",
        plt_dir=f"{tmp_path}{SL}",
        conn_dict={"ZIN": [1, 2]},
        nw=network,
        short0=short,
        f=np.asarray([0.001, 0.1]),
    )
    touchstone.plot_zmag = plot_zmag
    touchstone._TouchStone__get_rlc = get_rlc

    result = touchstone.plot_zself_shortsns("ZSHORT")

    assert connections == [(4, 3, short, 0), (3, 2, short, 0)]
    assert result == [
        ["SIM__ZSHORT__Port1", str(tmp_path / "SIM__ZSHORT__Port1.png"), "1.23", "2.35", ""],
        ["SIM__ZSHORT__Port2", str(tmp_path / "SIM__ZSHORT__Port2.png"), "4.57", "5.68", ""],
    ]
    assert all(args.args[0].number_of_ports == 2 for args in get_rlc.call_args_list)
    assert plot_zmag.call_count == 2


def test_plot_il_selects_output_input_paths_and_labels(touchstone_factory, tmp_path):
    s_db = np.arange(3 * 3 * 3, dtype=float).reshape(3, 3, 3)
    plot_smag = Mock()
    touchstone = touchstone_factory(
        key_name="SIM", plt_dir=f"{tmp_path}{SL}", f=np.asarray([1.0, 2.0, 3.0])
    )
    touchstone.plot_smag = plot_smag

    result = touchstone.plot_il([[1, 2], [3, 1]], s_db, "IL", "S")

    assert result == [["SIM__IL__S", str(tmp_path / "SIM__IL__S.png")]]
    curves = plot_smag.call_args.args[0]
    np.testing.assert_array_equal(curves[0][1], s_db[:, 1, 0])
    np.testing.assert_array_equal(curves[1][1], s_db[:, 0, 2])
    assert [curve[2]["label"] for curve in curves] == ["S21", "S13"]
    assert plot_smag.call_args.args[1:] == (
        "SIM__IL__S",
        str(tmp_path / "SIM__IL__S.png"),
    )


def test_plot_rl_selects_reflections_and_labels(touchstone_factory, tmp_path):
    s_db = np.arange(3 * 3 * 3, dtype=float).reshape(3, 3, 3)
    plot_smag = Mock()
    touchstone = touchstone_factory(
        key_name="SIM", plt_dir=f"{tmp_path}{SL}", f=np.asarray([1.0, 2.0, 3.0])
    )
    touchstone.plot_smag = plot_smag

    result = touchstone.plot_rl([1, 3], s_db, "RL", "S")

    assert result == [["SIM__RL__S", str(tmp_path / "SIM__RL__S.png")]]
    curves = plot_smag.call_args.args[0]
    np.testing.assert_array_equal(curves[0][1], s_db[:, 0, 0])
    np.testing.assert_array_equal(curves[1][1], s_db[:, 2, 2])
    assert [curve[2]["label"] for curve in curves] == ["S11", "S33"]


def test_split_mixedmode_network_returns_dd_dc_cd_cc_quadrants(touchstone_factory):
    mixed_mode = np.arange(2 * 4 * 4).reshape(2, 4, 4)
    touchstone = touchstone_factory(port_num=4)

    dd, dc, cd, cc = touchstone._TouchStone__split_mixedmode_network(mixed_mode)

    np.testing.assert_array_equal(dd, mixed_mode[:, :2, :2])
    np.testing.assert_array_equal(dc, mixed_mode[:, :2, 2:])
    np.testing.assert_array_equal(cd, mixed_mode[:, 2:, :2])
    np.testing.assert_array_equal(cc, mixed_mode[:, 2:, 2:])


def test_plot_il_mm_dispatches_all_quadrants_with_mode_headers(touchstone_factory):
    mixed_mode = np.arange(2 * 4 * 4).reshape(2, 4, 4)
    touchstone = touchstone_factory(port_num=4)
    calls = []

    def plot_il(connectivity, values, process_key, header):
        calls.append((connectivity, values.copy(), process_key, header))
        return [[header]]

    touchstone.plot_il = plot_il
    connectivity = [[1, 2]]

    result = touchstone.plot_il_mm(connectivity, mixed_mode, "IL_MM")

    assert result == {"DD": [["SDD"]], "CC": [["SCC"]], "DC": [["SDC"]], "CD": [["SCD"]]}
    assert [(item[0], item[2], item[3]) for item in calls] == [
        (connectivity, "IL_MM", "SDD"),
        (connectivity, "IL_MM", "SCC"),
        (connectivity, "IL_MM", "SDC"),
        (connectivity, "IL_MM", "SCD"),
    ]
    np.testing.assert_array_equal(calls[0][1], mixed_mode[:, :2, :2])
    np.testing.assert_array_equal(calls[1][1], mixed_mode[:, 2:, 2:])
    np.testing.assert_array_equal(calls[2][1], mixed_mode[:, :2, 2:])
    np.testing.assert_array_equal(calls[3][1], mixed_mode[:, 2:, :2])


def test_plot_rl_mm_dispatches_like_mode_quadrants_only(touchstone_factory):
    mixed_mode = np.arange(2 * 4 * 4).reshape(2, 4, 4)
    touchstone = touchstone_factory(port_num=4)
    calls = []

    def plot_rl(connectivity, values, process_key, header):
        calls.append((connectivity, values.copy(), process_key, header))
        return [[header]]

    touchstone.plot_rl = plot_rl
    connectivity = [1, 2]

    result = touchstone.plot_rl_mm(connectivity, mixed_mode, "RL_MM")

    assert result == {"DD": [["SDD"]], "CC": [["SCC"]]}
    assert [(item[0], item[2], item[3]) for item in calls] == [
        (connectivity, "RL_MM", "SDD"),
        (connectivity, "RL_MM", "SCC"),
    ]
    np.testing.assert_array_equal(calls[0][1], mixed_mode[:, :2, :2])
    np.testing.assert_array_equal(calls[1][1], mixed_mode[:, 2:, 2:])


def test_plot_tdr_extrapolates_resamples_and_plots_both_sides(touchstone_factory, tmp_path):
    network = FakeTdrNetwork([5e6, 20e6])
    touchstone = touchstone_factory(key_name="SIM", plt_dir=f"{tmp_path}{SL}")
    plotted = []

    def plot_time_domain(connectivity, transformed, title, path):
        plotted.append((list(connectivity), transformed, title, path))

    touchstone.plot_time_domain = plot_time_domain

    result = touchstone.plot_tdr([[1, 2], [3, 4]], network, "TDR", "SE")

    assert result == [
        ["SIM__TDR__SE_Left", str(tmp_path / "SIM__TDR__SE_Left.png")],
        ["SIM__TDR__SE_Right", str(tmp_path / "SIM__TDR__SE_Right.png")],
    ]
    assert network.extrapolate_calls == []
    assert network.resample_calls == []
    assert plotted[0][0] == [1, 2]
    assert plotted[1][0] == [3, 4]
    assert plotted[0][1] is plotted[1][1]
    assert plotted[0][1] is not network
    assert plotted[0][1].extrapolate_calls == ["linear"]
    assert plotted[0][1].resample_calls == [[0, 10_000_000, 20_000_000]]
    np.testing.assert_array_equal(plotted[0][1].f, [0, 10_000_000, 20_000_000])


def test_plot_tdr_skips_dc_extrapolation_when_network_already_starts_at_zero(touchstone_factory):
    network = FakeTdrNetwork([0, 20e6])
    touchstone = touchstone_factory()
    plotted = []
    touchstone.plot_time_domain = lambda _, transformed, __, ___: plotted.append(transformed)

    touchstone.plot_tdr([[1], [2]], network, "TDR")

    assert plotted[0] is plotted[1]
    assert plotted[0].extrapolate_calls == []
    assert plotted[0].resample_calls == [[0, 10_000_000, 20_000_000]]


def test_plot_tdr_mm_offsets_common_mode_ports_without_mutating_input(touchstone_factory):
    network = FakeTdrNetwork([0, 10e6], port_count=4)
    touchstone = touchstone_factory(port_num=4)
    calls = []

    def plot_tdr(connectivity, raw_network, process_key, header):
        calls.append((deepcopy(connectivity), raw_network, process_key, header))
        return [[header]]

    touchstone.plot_tdr = plot_tdr
    connectivity = [[1], [2]]

    result = touchstone.plot_tdr_mm(connectivity, network, "TDR_MM")

    assert result == {"DD": [["DD"]], "CC": [["CC"]]}
    assert calls == [
        ([[1], [2]], network, "TDR_MM", "DD"),
        ([[3], [4]], network, "TDR_MM", "CC"),
    ]
    assert connectivity == [[1], [2]]


def test_convert_snp_se2mm_renumbers_converts_and_writes_next_to_source(
    touchstone_factory, tmp_path
):
    network = FakeConversionNetwork([1e9, 2e9])
    source = tmp_path / "source.s4p"
    touchstone = touchstone_factory(
        nw=network,
        port_num=4,
        file_dir=str(source),
        conn_dict={"MM_ORDER_IN_SE": [2, 3, 0, 1]},
    )

    converted = touchstone.convert_snp_se2mm()

    assert converted is not network
    assert network.renumber_calls == []
    assert converted.renumber_calls == [([0, 1, 2, 3], [2, 3, 0, 1])]
    assert converted.se2gmm_calls == [2]
    assert converted.write_calls == [
        {
            "filename": "source_mm",
            "dir": f"{tmp_path / 'Mixed_Mode'}{SL}",
            "write_z0": True,
        }
    ]
    assert (tmp_path / "Mixed_Mode").is_dir()


@pytest.mark.parametrize(
    ("post_process_keys", "expects_conversion"),
    [(["ZOPEN", "IL"], False), (["IL_MM"], True), (["RL_MM", "TDR"], True)],
)
def test_mixedmode_network_is_conditional_for_supported_keys(
    touchstone_factory, post_process_keys, expects_conversion
):
    single_ended = object()
    mixed_mode = object()
    converter = Mock(return_value=mixed_mode)
    touchstone = touchstone_factory(
        MM_KEY=["IL_MM", "RL_MM"],
        spec_type={"POST_PROCESS_KEY": post_process_keys},
        nw=single_ended,
    )
    touchstone.convert_snp_se2mm = converter

    result = touchstone._TouchStone__get_mixedmode_network()

    assert result is (mixed_mode if expects_conversion else single_ended)
    assert converter.call_count == int(expects_conversion)


def test_get_rlc_extracts_and_converts_resistance_inductance_capacitance(touchstone_factory):
    touchstone = touchstone_factory()
    interpolate = Mock(
        side_effect=[
            (0.002, 0.0),
            (10.0, 0.0),
            (0.628, 0.0),
        ]
    )
    touchstone._TouchStone__get_z_interp = interpolate
    network = object()

    resistance, inductance, capacitance = touchstone._TouchStone__get_rlc(network, 2, "source.s4p")

    assert resistance == pytest.approx(2.0)
    assert inductance > 0
    assert capacitance > 0
    assert interpolate.call_args_list == [
        call(network, 1e3, 2, 2, "source.s4p"),
        call(network, 1e4, 2, 2, "source.s4p"),
        call(network, 1e8, 2, 2, "source.s4p"),
    ]


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="BUG: RLC reactance conversion uses 3.14 instead of math.pi",
)
def test_get_rlc_uses_math_pi_for_inductance_and_capacitance(touchstone_factory):
    touchstone = touchstone_factory()
    touchstone._TouchStone__get_z_interp = Mock(
        side_effect=[(0.002, 0.0), (10.0, 0.0), (0.628, 0.0)]
    )

    _, inductance, capacitance = touchstone._TouchStone__get_rlc(object(), 0, "source.s1p")

    assert inductance == pytest.approx(0.628 / (2 * math.pi * 1e8) * 1e12)
    assert capacitance == pytest.approx(1 / 10 / (2 * math.pi * 1e4) * 1e9)


def test_get_z_interp_returns_exact_frequency_sample(touchstone_factory):
    network = LookupNetwork([50, 100, 200], [5, 10, 20], [0.5, 1.0, 2.0])
    touchstone = touchstone_factory()

    magnitude, angle = touchstone._TouchStone__get_z_interp(network, 100, 0, 0, "source.s1p")

    assert magnitude == 10
    assert angle == 1.0


@pytest.mark.parametrize(
    ("frequencies", "magnitudes", "angles", "expected_frequency_pair"),
    [
        ([90, 110], [9, 22], [0.9, 1.1], (90, 110)),
        ([90, 105], [9, 21], [0.9, 1.05], (105, 90)),
    ],
)
def test_get_z_interp_uses_log_magnitude_and_linear_angle_between_brackets(
    touchstone_factory, frequencies, magnitudes, angles, expected_frequency_pair
):
    network = LookupNetwork(frequencies, magnitudes, angles)
    touchstone = touchstone_factory()

    magnitude, angle = touchstone._TouchStone__get_z_interp(network, 100, 0, 0, "source.s1p")

    first_frequency, second_frequency = expected_frequency_pair
    first_index = frequencies.index(first_frequency)
    second_index = frequencies.index(second_frequency)
    expected_magnitude = _log_interpolate(
        100,
        first_frequency,
        magnitudes[first_index],
        second_frequency,
        magnitudes[second_index],
    )
    expected_angle = angles[first_index] + (100 - first_frequency) / (
        second_frequency - first_frequency
    ) * (angles[second_index] - angles[first_index])
    assert magnitude == pytest.approx(expected_magnitude)
    assert angle == pytest.approx(expected_angle)


def test_get_z_interp_warns_when_search_never_finds_a_bracket(touchstone_factory, capsys):
    touchstone = touchstone_factory()

    magnitude, angle = touchstone._TouchStone__get_z_interp(
        SparseLookupNetwork(), 100, 0, 0, "sparse.s1p"
    )

    output = capsys.readouterr().out
    assert "Frequency samples are not sufficiently dense for interpolation in sparse.s1p" in output
    assert "The results may not be accurate!" in output
    assert "Please raise frequency points and rerun simulations!" in output
    assert magnitude == pytest.approx(_log_interpolate(100, 80, 8, 90, 9))
    assert angle == pytest.approx(1.0)


def test_from_list_constructs_instances_in_input_order():
    class RecordingTouchStone(TouchStone):
        def __init__(self, info):
            self.info = info

    infos = [{"file_dir": "first.s1p"}, {"file_dir": "second.s2p"}]

    result = RecordingTouchStone.from_list(infos)

    assert [item.info for item in result] == infos
    assert all(isinstance(item, RecordingTouchStone) for item in result)


def test_plot_zmag_uses_log_axes_impedance_labels_and_target_path(monkeypatch, touchstone_factory):
    pyplot = PyplotRecorder()
    monkeypatch.setattr(touchstone_module, "plt", pyplot)
    touchstone = touchstone_factory()
    frequency = np.asarray([0.001, 0.01])
    first = np.asarray([1.0, 2.0])
    second = np.asarray([3.0, 4.0])

    touchstone.plot_zmag(
        [[frequency, first], [frequency, second, {"label": "Z22", "color": "red"}]],
        "Impedance",
        "plot.png",
    )

    assert pyplot.figures == [{"figsize": (8, 5)}]
    np.testing.assert_array_equal(pyplot.plots[0][0][0], frequency)
    np.testing.assert_array_equal(pyplot.plots[0][0][1], first)
    np.testing.assert_array_equal(pyplot.plots[1][0][1], second)
    assert pyplot.plots[0][1] == {}
    assert pyplot.plots[1][1] == {"label": "Z22", "color": "red"}
    assert pyplot.legend_count == 1
    assert pyplot.titles == ["Impedance"]
    assert pyplot.xscales == ["log"]
    assert pyplot.yscales == ["log"]
    assert pyplot.xlabels == ["Frequency (GHz)"]
    assert pyplot.ylabels == ["Z(Ohm)"]
    assert pyplot.grids == [
        {"which": "major", "linestyle": "-"},
        {"which": "minor", "linestyle": "--"},
    ]
    assert pyplot.saved == ["plot.png"]
    assert pyplot.close_count == 1


def test_plot_smag_uses_linear_frequency_axis_db_label_and_target_path(
    monkeypatch, touchstone_factory
):
    pyplot = PyplotRecorder()
    monkeypatch.setattr(touchstone_module, "plt", pyplot)
    touchstone = touchstone_factory()
    frequency = np.asarray([1.0, 2.0])
    loss = np.asarray([-1.0, -2.0])

    touchstone.plot_smag([[frequency, loss, {"label": "S21"}]], "Insertion Loss", "loss.png")

    assert pyplot.plots[0][1] == {"label": "S21"}
    assert pyplot.legend_count == 1
    assert pyplot.titles == ["Insertion Loss"]
    assert pyplot.xscales == []
    assert pyplot.yscales == []
    assert pyplot.xlabels == ["Frequency (GHz)"]
    assert pyplot.ylabels == ["S21 (dB)"]
    assert pyplot.saved == ["loss.png"]
    assert pyplot.close_count == 1


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="BUG: return-loss plots are always labeled S21 instead of reflection loss",
)
def test_plot_smag_labels_return_loss_as_reflection_loss(monkeypatch, touchstone_factory):
    pyplot = PyplotRecorder()
    monkeypatch.setattr(touchstone_module, "plt", pyplot)
    touchstone = touchstone_factory()

    touchstone.plot_smag(
        [[np.asarray([1.0]), np.asarray([-10.0]), {"label": "S11"}]],
        "SIM__RL__S",
        "rl.png",
    )

    assert pyplot.ylabels == ["S11 (dB)"]


def test_plot_time_domain_uses_one_based_labels_and_characteristic_impedance_axes(
    monkeypatch, touchstone_factory
):
    pyplot = PyplotRecorder()
    monkeypatch.setattr(touchstone_module, "plt", pyplot)
    network = FakeTdrNetwork([0, 10e6], port_count=3)
    touchstone = touchstone_factory()

    touchstone.plot_time_domain([1, 3], network, "TDR Left", "tdr.png")

    assert network.time_step_calls == [(0, 0, "Port_1"), (2, 2, "Port_3")]
    assert pyplot.titles == ["TDR Left"]
    assert pyplot.xlabels == ["Time (ns)"]
    assert pyplot.ylabels == ["Zc (Ohm)"]
    assert pyplot.saved == ["tdr.png"]
    assert pyplot.close_count == 1


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "BUG: TDR_MM is absent from TouchStone.MM_KEY, so a TDR_MM-only spec uses the "
        "single-ended network instead of converting it"
    ),
)
def test_tdr_mm_alone_initializes_a_mixed_mode_network(touchstone_factory):
    single_ended = object()
    mixed_mode = object()
    touchstone = touchstone_factory(
        MM_KEY=["IL_MM", "RL_MM"],
        spec_type={"POST_PROCESS_KEY": ["TDR_MM"]},
        nw=single_ended,
    )
    touchstone.convert_snp_se2mm = Mock(return_value=mixed_mode)

    assert touchstone._TouchStone__get_mixedmode_network() is mixed_mode
