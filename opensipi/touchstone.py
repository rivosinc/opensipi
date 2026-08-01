# SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
Author: yanshengw@
Created on Nov. 1, 2022
Last updated on Mar. 20, 2025

Description:
    This module handles one touchstone file.

    One ``TouchStone`` instance wraps one snp file and turns it into the plots
and the extracted figures of merit a report needs. What gets produced is driven
by the ``POST_PROCESS_KEY`` list of the spec type, so the same class serves PDN
impedance work and IO loss work.

    Two port-numbering conventions meet here. The connectivity lists coming
from the input are one-based, matching how ports are numbered in the sheets and
in the touchstone file, while scikit-rf indexes from zero, so the conversion
happens at each point of use.

Note:
    The ``__main__`` block at the bottom is a stale demo. Its ``info`` dict is
    missing the ``key_name`` and ``conn_dict`` keys the constructor now needs,
    so running this module directly fails.
"""

from math import log10

import matplotlib.pyplot as plt
import skrf as rf

from opensipi.util.common import (
    SL,
    lol_numerical_add_num,
    make_dir,
    split_str_at_last_symbol,
)


class TouchStone:
    """Post-process one touchstone file into plots and extracted values.

    Attributes:
        MM_KEY (list of str): The post-processing keys that require the
            single-ended network to be converted to mixed-mode. Used to decide
            whether to pay for that conversion at construction time.
    """

    def __init__(self, info):
        """Load the touchstone file and prepare the networks to work from.

        The file is read here, and the mixed-mode conversion is done up front
        when the spec type calls for it, so the plotting methods can assume
        both networks already exist.

        Args:
            info (dict): Everything needed to process this one file.

                * ``file_dir`` (str): Full path of the snp file.
                * ``key_name`` (str): Simulation key, used to name the figures.
                * ``plt_dir`` (str): Directory to write the figures into.
                * ``spec_type`` (dict): The spec type definition, whose
                  ``POST_PROCESS_KEY`` list decides what gets produced.
                * ``conn_dict`` (dict): Connectivity lists per post-processing
                  key, telling each plot which ports to draw. All port numbers
                  here are one-based.

        Attributes:
            f (numpy.ndarray): The frequency axis in GHz. The underlying
                network keeps Hz, so this is the axis the plots use.
            nw (skrf.Network): The single-ended network read from the file.
            nw_mm (skrf.Network): The mixed-mode network, or ``nw`` itself when
                no mixed-mode post-processing was requested.
            port_num (int): Port count of the single-ended network.
            short0 (skrf.Network): A one-port short used to terminate ports.
        """
        # define constants
        self.MM_KEY = ["IL_MM", "RL_MM"]
        # define variables
        self.file_dir = info["file_dir"]
        self.key_name = info["key_name"]
        self.plt_dir = info["plt_dir"]
        self.spec_type = info["spec_type"]
        self.conn_dict = info["conn_dict"]
        self.nw = rf.Network(self.file_dir)
        self.f = self.nw.f / 1e9  # GHz
        self.short0 = self.__get_short_block()
        self.port_num = self.nw.number_of_ports
        self.nw_mm = self.__get_mixedmode_network()

    def auto_process(self):
        """Automatically process SNP files based on spect_type.

        Each key in the spec type's ``POST_PROCESS_KEY`` list is dispatched to
        the matching plot method. A key with no case here is skipped silently.

        Returns:
            dict: Post-processing key to that key's output. The value is a list
            of ``[fig_title, fig_dir, ...]`` entries for the single-ended keys,
            and a dict of mixed-mode type to such a list for the ``_MM`` keys.
        """
        output_dict = {}
        process_key = self.spec_type["POST_PROCESS_KEY"]
        for key in process_key:
            match key:
                case "ZOPEN":
                    output_dict[key] = self.plot_zself(key)
                case "ZSHORT":
                    output_dict[key] = self.plot_zself_shortsns(key)
                case "IL":
                    output_dict[key] = self.plot_il(self.conn_dict[key], self.nw.s_db, key)
                case "RL":
                    output_dict[key] = self.plot_rl(self.conn_dict[key], self.nw.s_db, key)
                case "IL_MM":
                    output_dict[key] = self.plot_il_mm(self.conn_dict[key], self.nw_mm.s_db, key)
                case "RL_MM":
                    output_dict[key] = self.plot_rl_mm(self.conn_dict[key], self.nw_mm.s_db, key)
                case "TDR":
                    output_dict[key] = self.plot_tdr(self.conn_dict[key], self.nw, key)
                case "TDR_MM":
                    output_dict[key] = self.plot_tdr_mm(self.conn_dict[key], self.nw_mm, key)
        return output_dict

    def plot_zself(self, prockey=None):
        """Plot the self impedance with the sense ports left floating.

        Uses the connectivity list to determine the Zin plot. The sense ports,
        being the auxiliary ports that follow the main ones, are left open, so
        the result is the impedance the sink sees with nothing shorting the
        rail. One figure is written per main port.

        Args:
            prockey (str, optional): Post-processing key, folded into the
                figure names to keep the open and shorted variants apart.

        Returns:
            list of list: One entry per main port, being
            ``[fig_title, fig_dir, "", L_at_100MHz_pH, C_at_10kHz_nF]``. The
            resistance slot is left empty, as it is not meaningful with the
            sense ports open.
        """
        output_list = []
        if prockey:
            proc_key_name = "__" + prockey + "_"
        else:
            proc_key_name = ""
        last_plot_port_index = len(self.conn_dict["ZIN"])  # starting from 1
        nw = self.nw.copy()
        for i_port in range(last_plot_port_index):  # starting from 0
            zself = nw.z_mag[:, i_port, i_port]
            fig_data = [[self.f, zself]]
            fig_title = self.key_name + proc_key_name + "_Port" + str(i_port + 1)
            fig_dir = self.plt_dir + fig_title + ".png"
            self.plot_zmag(fig_data, fig_title, fig_dir)
            # extract LC
            snp_dir = self.file_dir
            _, l_hf, c_lf = self.__get_rlc(nw, i_port, snp_dir)
            output_list.append([fig_title, fig_dir, "", f"{l_hf:.2f}", f"{c_lf:.2f}"])
        return output_list

    def plot_zself_shortsns(self, prockey=None):
        """Plot the self impedance with the sense ports shorted.

        Uses the connectivity list to determine the Zin plot. Every port beyond
        the main ones is terminated into a short before the impedance is read,
        which models the VRM shorting the rail and makes the DC resistance of
        the loop measurable.

        Args:
            prockey (str, optional): Post-processing key, folded into the
                figure names.

        Returns:
            list of list: One entry per remaining port, being
            ``[fig_title, fig_dir, R_at_1kHz_mOhm, L_at_100MHz_pH, ""]``. The
            capacitance slot is left empty, as it is not meaningful with the
            sense ports shorted.
        """
        output_list = []
        if prockey:
            proc_key_name = "__" + prockey + "_"
        else:
            proc_key_name = ""
        last_plot_port_index = len(self.conn_dict["ZIN"])  # starting from 1
        short_port_number = self.nw.number_of_ports - last_plot_port_index
        nw_red = self.nw.copy()
        # short all sns ports
        while short_port_number > 0:
            # from 0
            last_short_port = last_plot_port_index + short_port_number - 1
            nw_red = rf.connect(nw_red, last_short_port, self.short0, 0)
            short_port_number -= 1

        for i_port in range(nw_red.number_of_ports):
            zself = nw_red.z_mag[:, i_port, i_port]
            fig_data = [[self.f, zself]]
            fig_title = self.key_name + proc_key_name + "_Port" + str(i_port + 1)
            fig_dir = self.plt_dir + fig_title + ".png"
            self.plot_zmag(fig_data, fig_title, fig_dir)

            # extract RL
            snp_dir = self.file_dir
            r_dc, l_hf, _ = self.__get_rlc(nw_red, i_port, snp_dir)
            output_list.append([fig_title, fig_dir, f"{r_dc:.2f}", f"{l_hf:.2f}", ""])
        return output_list

    def plot_il(self, conn_list, nw_s_db, prockey=None, header="S"):
        """Plot insertion loss based on the connectivity dict.

        Every requested through path is drawn as one curve on a single figure.

        Args:
            conn_list (list of list of int): One ``[input_port, output_port]``
                pair per curve, one-based.
            nw_s_db (numpy.ndarray): The S-parameters in dB, indexed
                ``[freq, output, input]``.
            prockey (str, optional): Post-processing key, folded into the
                figure name.
            header (str, optional): Curve label prefix, naming the mode being
                drawn, e.g. ``"S"``, ``"SDD"``, or ``"SDC"``. Defaults to
                ``"S"``.

        Returns:
            list of list of str: A single entry ``[fig_title, fig_dir]``, since
            all the curves share one figure.
        """
        if prockey:
            proc_key_name = "__" + prockey + "__" + header
        else:
            proc_key_name = "__" + header
        output_list = []
        fig_data = []
        for i_conn in conn_list:
            sil = nw_s_db[:, i_conn[1] - 1, i_conn[0] - 1]  # freq, output, input
            label = header + str(i_conn[1]) + str(i_conn[0])
            fig_data.append([self.f, sil, {"label": label}])
        fig_title = self.key_name + proc_key_name
        fig_dir = self.plt_dir + fig_title + ".png"
        self.plot_smag(fig_data, fig_title, fig_dir)
        output_list.append([fig_title, fig_dir])
        return output_list

    def plot_rl(self, conn_list, nw_s_db, prockey=None, header="S"):
        """Plot return loss based on the connectivity dict.

        Every requested port is drawn as one reflection curve on a single
        figure.

        Args:
            conn_list (list of int): The ports to draw, one-based.
            nw_s_db (numpy.ndarray): The S-parameters in dB.
            prockey (str, optional): Post-processing key, folded into the
                figure name.
            header (str, optional): Curve label prefix. Defaults to ``"S"``.

        Returns:
            list of list of str: A single entry ``[fig_title, fig_dir]``.
        """
        if prockey:
            proc_key_name = "__" + prockey + "__" + header
        else:
            proc_key_name = "__" + header
        output_list = []
        fig_data = []
        for i_conn in conn_list:
            srl = nw_s_db[:, i_conn - 1, i_conn - 1]
            label = header + str(i_conn) + str(i_conn)
            fig_data.append([self.f, srl, {"label": label}])
        fig_title = self.key_name + proc_key_name
        fig_dir = self.plt_dir + fig_title + ".png"
        self.plot_smag(fig_data, fig_title, fig_dir)
        output_list.append([fig_title, fig_dir])
        return output_list

    def plot_il_mm(self, conn_list, nw_mm_s_db, prockey=None):
        """Plot mixed-mode insertion loss based on the connectivity dict.

        All four quadrants are plotted, so both the wanted differential and
        common transmission and the unwanted mode conversion between them are
        visible.

        Args:
            conn_list (list of list of int): One ``[input_port, output_port]``
                pair per curve, numbered in mixed-mode ports.
            nw_mm_s_db (numpy.ndarray): The mixed-mode S-parameters in dB.
            prockey (str, optional): Post-processing key, folded into the
                figure names.

        Returns:
            dict: Quadrant name to the output of :meth:`plot_il` for it, with
            the keys ``"DD"``, ``"CC"``, ``"DC"``, and ``"CD"``.
        """
        nw_dd, nw_dc, nw_cd, nw_cc = self.__split_mixedmode_network(nw_mm_s_db)
        out_dict = {}
        # Diff_Diff
        out_dict["DD"] = self.plot_il(conn_list, nw_dd, prockey, "SDD")
        # Comm_Comm
        out_dict["CC"] = self.plot_il(conn_list, nw_cc, prockey, "SCC")
        # Diff_Comm: Diff output from Comm input
        out_dict["DC"] = self.plot_il(conn_list, nw_dc, prockey, "SDC")
        # Comm_Diff: Comm output from Diff input
        out_dict["CD"] = self.plot_il(conn_list, nw_cd, prockey, "SCD")
        return out_dict

    def plot_rl_mm(self, conn_list, nw_mm_s_db, prockey=None):
        """Plot mixed-mode return loss based on the connectivity dict.

        Only the two like-mode quadrants are plotted, as reflection is read
        within a mode rather than across modes.

        Args:
            conn_list (list of int): The mixed-mode ports to draw, one-based.
            nw_mm_s_db (numpy.ndarray): The mixed-mode S-parameters in dB.
            prockey (str, optional): Post-processing key, folded into the
                figure names.

        Returns:
            dict: Quadrant name to the output of :meth:`plot_rl` for it, with
            the keys ``"DD"`` and ``"CC"``.
        """
        nw_dd, _, _, nw_cc = self.__split_mixedmode_network(nw_mm_s_db)
        out_dict = {}
        # Diff_Diff
        out_dict["DD"] = self.plot_rl(conn_list, nw_dd, prockey, "SDD")
        # Comm_Comm
        out_dict["CC"] = self.plot_rl(conn_list, nw_cc, prockey, "SCC")
        return out_dict

    def plot_zmag(self, fig_data, fig_title, fig_dir):
        """Plot Zmag vs. freq (GHz) and save it to a png.

        Both axes are logarithmic, which is how a PDN impedance profile is
        conventionally read.

        Args:
            fig_data (list of list): One curve per entry, as
                ``[f, Z]`` or ``[f, Z, option]``, where ``option`` is a dict of
                matplotlib keyword arguments. A ``label`` in it turns the
                legend on.
            fig_title (str): Title drawn on the figure.
            fig_dir (str): Full path of the png to write.
        """
        plt.figure(figsize=(8, 5))
        for i_curve in fig_data:
            data_col = len(i_curve)
            if data_col == 2:
                plt.plot(i_curve[0], i_curve[1])
            elif data_col == 3:
                plt.plot(i_curve[0], i_curve[1], **i_curve[2])
                if "label" in i_curve[2]:
                    plt.legend()
        plt.title(fig_title)
        plt.xscale("log")
        plt.yscale("log")
        plt.xlabel("Frequency (GHz)")
        plt.ylabel("Z(Ohm)")
        plt.grid(which="major", linestyle="-")
        plt.grid(which="minor", linestyle="--")
        plt.savefig(fig_dir)
        plt.close()

    def plot_smag(self, fig_data, fig_title, fig_dir):
        """Plot Smag vs. freq (GHz) and save it to a png.

        The frequency axis is linear here, unlike :meth:`plot_zmag`, since loss
        curves are read against a linear frequency sweep.

        Args:
            fig_data (list of list): One curve per entry, as
                ``[f, S]`` or ``[f, S, option]``, where ``option`` is a dict of
                matplotlib keyword arguments.
            fig_title (str): Title drawn on the figure.
            fig_dir (str): Full path of the png to write.

        Note:
            The y axis is always labelled ``"S21 (dB)"``, including on the
            return loss figures.
        """
        plt.figure(figsize=(8, 5))
        for i_curve in fig_data:
            data_col = len(i_curve)
            if data_col == 2:
                plt.plot(i_curve[0], i_curve[1])
            elif data_col == 3:
                plt.plot(i_curve[0], i_curve[1], **i_curve[2])
                if "label" in i_curve[2]:
                    plt.legend()
        plt.title(fig_title)
        plt.xlabel("Frequency (GHz)")
        plt.ylabel("S21 (dB)")
        plt.grid(which="major", linestyle="-")
        plt.grid(which="minor", linestyle="--")
        plt.savefig(fig_dir)
        plt.close()

    def plot_tdr(self, conn_list, nw_raw, prockey=None, header="SE"):
        """Plot TDR for given ports.

        A time-domain view needs a network that starts at DC and is sampled on
        an even frequency grid, so the network is first extrapolated to DC when
        it does not already reach it and then resampled onto a 10 MHz linear
        step. Two figures are produced, one per end of the link.

        Args:
            conn_list (list of list of int): Two lists, being the left-side and
                the right-side ports, one-based.
            nw_raw (skrf.Network): The network to transform. Copied, not
                modified.
            prockey (str, optional): Post-processing key, folded into the
                figure names.
            header (str, optional): Name of the mode being drawn, e.g.
                ``"SE"``, ``"DD"``, or ``"CC"``. Defaults to ``"SE"``.

        Returns:
            list of list of str: Two entries ``[fig_title, fig_dir]``, for the
            left and the right ports respectively.
        """
        if prockey:
            proc_key_name = "__" + prockey + "__" + header
        else:
            proc_key_name = "__" + header
        nw = nw_raw.copy()
        # DC point extrapolation
        if nw.f[0] > 0:
            nw = nw.extrapolate_to_dc(kind="linear")
        lin_step = int(10e6)
        lin_freq_list = list(range(0, int(nw.f[-1]) + lin_step, lin_step))
        nw.resample(lin_freq_list)
        output_list = []
        # left ports
        fig_title_l = self.key_name + proc_key_name + "_Left"
        fig_dir_l = self.plt_dir + fig_title_l + ".png"
        self.plot_time_domain(conn_list[0], nw, fig_title_l, fig_dir_l)
        output_list.append([fig_title_l, fig_dir_l])
        # right ports
        fig_title_r = self.key_name + proc_key_name + "_Right"
        fig_dir_r = self.plt_dir + fig_title_r + ".png"
        self.plot_time_domain(conn_list[1], nw, fig_title_r, fig_dir_r)
        output_list.append([fig_title_r, fig_dir_r])
        return output_list

    def plot_tdr_mm(self, conn_list, nw_raw, prockey=None):
        """Plot TDR for Mixed-mode ports.

        In a mixed-mode network the differential ports occupy the first half of
        the port range and the common ports the second half, so the common-mode
        plot reuses the same connectivity list shifted by half the port count.

        Args:
            conn_list (list of list of int): Two lists of differential ports,
                being the left and the right side, one-based.
            nw_raw (skrf.Network): The mixed-mode network.
            prockey (str, optional): Post-processing key, folded into the
                figure names.

        Returns:
            dict: Mode name to the output of :meth:`plot_tdr` for it, with the
            keys ``"DD"`` and ``"CC"``.
        """
        out_dict = {}
        # Diff_Diff
        out_dict["DD"] = self.plot_tdr(conn_list, nw_raw, prockey, "DD")
        # Comm_Comm
        mm_port_num = int(self.port_num / 2)
        conn_list_cc = lol_numerical_add_num(conn_list, mm_port_num)
        out_dict["CC"] = self.plot_tdr(conn_list_cc, nw_raw, prockey, "CC")
        return out_dict

    def plot_time_domain(self, conn_list, fig_data, fig_title, fig_dir):
        """Plot the step-response characteristic impedance and save it to a png.

        Args:
            conn_list (list of int): The ports to draw, one-based.
            fig_data (skrf.Network): The network to read the step response
                from. Named for symmetry with the other plot methods, though it
                is a network rather than pre-computed curves.
            fig_title (str): Title drawn on the figure.
            fig_dir (str): Full path of the png to write.
        """
        plt.figure(figsize=(8, 5))
        for i_conn in conn_list:
            label = "Port_" + str(i_conn)
            fig_data.plot_z_time_step(i_conn - 1, i_conn - 1, label=label)
        plt.title(fig_title)
        plt.xlabel("Time (ns)")
        plt.ylabel("Zc (Ohm)")
        plt.grid(which="major", linestyle="-")
        plt.grid(which="minor", linestyle="--")
        plt.savefig(fig_dir)
        plt.close()

    def convert_snp_se2mm(self):
        """Convert SNP files from single-ended to mixed-mode Spara.

        The single-ended ports are first renumbered into the pair order given
        by ``MM_ORDER_IN_SE``, since the conversion expects each differential
        pair to sit in consecutive positions, and the result is written
        alongside the input file in a ``Mixed_Mode`` sub-folder.

        Returns:
            skrf.Network: The mixed-mode network. The differential ports come
            first, the common-mode ports second.
        """
        sedata = self.nw.copy()
        se_port_index = list(range(self.port_num))
        mm_port_index = self.conn_dict["MM_ORDER_IN_SE"]
        sedata.renumber(se_port_index, mm_port_index)
        sedata.se2gmm(p=int(self.port_num / 2))
        # save mm snp files
        se_snp_dir, se_snp_name = split_str_at_last_symbol(self.file_dir, SL)
        se_snp_dir = se_snp_dir + SL
        mm_snp_dir = se_snp_dir + "Mixed_Mode" + SL
        make_dir(mm_snp_dir)
        file_name, _ = split_str_at_last_symbol(se_snp_name, ".")
        mm_snp_name = file_name + "_mm"
        # sedata is actually mmdata
        sedata.write_touchstone(filename=mm_snp_name, dir=mm_snp_dir, write_z0=True)
        return sedata

    def __get_mixedmode_network(self):
        """Get mixedmode network if necessary.

        The conversion is skipped unless the spec type actually asks for a
        mixed-mode result, so a single-ended run does not pay for it.

        Returns:
            skrf.Network: The converted mixed-mode network, or the untouched
            single-ended network when no conversion was needed.

        Note:
            Only the keys in ``MM_KEY`` trigger the conversion, and ``TDR_MM``
            is not among them. A spec type asking for ``TDR_MM`` without also
            asking for ``IL_MM`` or ``RL_MM`` therefore reaches
            :meth:`plot_tdr_mm` with a single-ended network.
        """
        process_key = self.spec_type["POST_PROCESS_KEY"]
        se2mm = False
        for key in process_key:
            if key in self.MM_KEY:
                se2mm = True
        if se2mm:
            mmdata = self.convert_snp_se2mm()
        else:
            mmdata = self.nw
        return mmdata

    def __split_mixedmode_network(self, nw_mm):
        """Split one mixed-mode network into four sub-networks.

        Slices the S-parameter block into its quadrants, relying on the
        differential ports occupying the first half of the port range and the
        common-mode ports the second half.

        Args:
            nw_mm (numpy.ndarray): The mixed-mode S-parameters, indexed
                ``[freq, output, input]``.

        Returns:
            tuple: A 4-tuple ``(nw_dd, nw_dc, nw_cd, nw_cc)``, being the
            differential, the two mode-conversion, and the common-mode
            quadrants.
        """
        mm_port_num = int(self.port_num / 2)
        nw_dd = nw_mm[:, 0:mm_port_num, 0:mm_port_num]
        nw_dc = nw_mm[:, 0:mm_port_num, mm_port_num:]
        nw_cd = nw_mm[:, mm_port_num:, 0:mm_port_num]
        nw_cc = nw_mm[:, mm_port_num:, mm_port_num:]
        return nw_dd, nw_dc, nw_cd, nw_cc

    def __get_short_block(self):
        """Get a 1-port short block based on the input touchstone file.

        Built from a scikit-rf sample short and resampled onto this file's
        frequency axis, so it can be connected to a port of this network.

        Returns:
            skrf.Network: A one-port short on the same frequency axis.
        """
        short0 = rf.data.wr2p2_short
        short0.resample(self.nw.frequency.npoints)
        short0.f = self.f
        return short0

    def __get_rlc(self, nw, i_port, snp_dir):
        """Return RLC at specified frequencies.

        Each element is read at the frequency where it dominates the impedance:
        resistance low enough to be flat, capacitance where the rail still
        looks capacitive, and inductance where it already looks inductive.

        Args:
            nw (skrf.Network): The network to read.
            i_port (int): Zero-based port index.
            snp_dir (str): Path of the source snp file, quoted in the
                interpolation warnings.

        Returns:
            tuple: A 3-tuple ``(r_dc, l_hf, c_lf)``, being the resistance at
            1 kHz in mOhm, the inductance at 100 MHz in pH, and the capacitance
            at 10 kHz in nF.

        Note:
            The reactance conversions use ``3.14`` for pi, so the reported
            inductance and capacitance carry a systematic error of about
            0.05 percent.
        """
        # extract R@1KHz
        freq_tgt = 1e3
        r_dc, _ = self.__get_z_interp(nw, freq_tgt, i_port, i_port, snp_dir)
        r_dc = r_dc * 1e3  # mOhm
        # extract C@10KHz
        freq_tgt = 1e4
        z_lf, _ = self.__get_z_interp(nw, freq_tgt, i_port, i_port, snp_dir)
        c_lf = 1 / z_lf / (2 * 3.14 * freq_tgt) * 1e9  # nF
        # extract L@100MHz
        freq_tgt = 1e8
        z_hf, _ = self.__get_z_interp(nw, freq_tgt, i_port, i_port, snp_dir)
        l_hf = z_hf / (2 * 3.14 * freq_tgt) * 1e12  # pH
        return r_dc, l_hf, c_lf

    def __get_z_interp(self, nw, freq_tgt, i_port, j_port, snp_name):
        """Interpolate the impedance at a target frequency.

        Input network class, target freq, and target port. Output interpolated
        z in Ohm and angle in unwrapped rad.

        The simulated frequency points rarely land exactly on the target, so a
        bracketing point is searched for by stepping away from the target in
        10 percent increments, up to ten steps, and the value is then
        interpolated between the two. The magnitude is interpolated in log-log
        space, matching how impedance behaves across decades, while the angle
        is interpolated linearly.

        Args:
            nw (skrf.Network): The network to read.
            freq_tgt (float): Target frequency in Hz.
            i_port (int): Zero-based output port index.
            j_port (int): Zero-based input port index.
            snp_name (str): Name quoted in the warnings.

        Returns:
            tuple: A 2-tuple ``(z_interp, ang_interp)``, being the impedance
            magnitude in Ohm and the unwrapped angle in rad.

        Note:
            If no bracketing point is found within ten steps, a warning is
            printed and the value is extrapolated from the two closest points
            instead. The result is still returned, so the caller cannot tell
            this happened.
        """
        z_1 = nw[str(freq_tgt)].z_mag[0, i_port, j_port]
        f_1 = nw[str(freq_tgt)].f[0]
        ang_1 = nw[str(freq_tgt)].z_rad_unwrap[0, i_port, j_port]
        rate = 0.1
        if f_1 == freq_tgt:
            z_interp = z_1
            ang_interp = ang_1
        elif f_1 < freq_tgt:
            z_2 = nw[str(freq_tgt * (1 + rate))].z_mag[0, i_port, j_port]
            f_2 = nw[str(freq_tgt * (1 + rate))].f[0]
            ang_2 = nw[str(freq_tgt * (1 + rate))].z_rad_unwrap[0, i_port, j_port]
            n = 2
            while (f_2 <= freq_tgt) and (n < 11):
                z_2 = nw[str(freq_tgt * (1 + n * rate))].z_mag[0, i_port, j_port]
                f_2 = nw[str(freq_tgt * (1 + n * rate))].f[0]
                ang_2 = nw[str(freq_tgt * (1 + n * rate))].z_rad_unwrap[0, i_port, j_port]
                n = n + 1
            if f_2 <= freq_tgt:
                print(
                    "Warning: Frequency samples are not"
                    + " sufficiently dense for interpolation in "
                    + snp_name
                )
                print("The results may not be accurate!")
                print("Please raise frequency points and rerun simulations!")
            # linear log scale
            z_interp = 10 ** (
                log10(z_1)
                + (log10(freq_tgt) - log10(f_1))
                / (log10(f_2) - log10(f_1))
                * (log10(z_2) - log10(z_1))
            )
            # linear scale
            ang_interp = ang_1 + (freq_tgt - f_1) / (f_2 - f_1) * (ang_2 - ang_1)
        else:
            z_2 = nw[str(freq_tgt * (1 - rate))].z_mag[0, i_port, j_port]
            f_2 = nw[str(freq_tgt * (1 - rate))].f[0]
            ang_2 = nw[str(freq_tgt * (1 - rate))].z_rad_unwrap[0, i_port, j_port]
            n = 2
            while (f_2 >= freq_tgt) and (n < 10):
                z_2 = nw[str(freq_tgt * (1 - n * rate))].z_mag[0, i_port, j_port]
                f_2 = nw[str(freq_tgt * (1 - n * rate))].f[0]
                ang_2 = nw[str(freq_tgt * (1 - n * rate))].z_rad_unwrap[0, i_port, j_port]
                n = n + 1
            if f_2 >= freq_tgt:
                print(
                    "Warning: Frequency samples are not"
                    + " sufficiently dense for interpolation in "
                    + snp_name
                )
                print("The results may not be accurate!")
                print("Please raise frequency points and rerun simulations!")
            # linear log scale
            z_interp = 10 ** (
                log10(z_1)
                + (log10(freq_tgt) - log10(f_1))
                / (log10(f_2) - log10(f_1))
                * (log10(z_2) - log10(z_1))
            )
            # linear scale
            ang_interp = ang_1 + (freq_tgt - f_1) / (f_2 - f_1) * (ang_2 - ang_1)
        return z_interp, ang_interp

    @classmethod
    def from_list(cls, info_list):
        """Input a list of dict and output a list of snp class.

        Args:
            info_list (list of dict): One ``info`` dict per touchstone file, as
                described in :meth:`__init__`.

        Returns:
            list of TouchStone: One instance per input dict, in order. Every
            file is read as its instance is built, so the mixed-mode
            conversions all happen here.
        """
        ts_list = []
        for info in info_list:
            ts_list.append(cls(info))
        return ts_list


if __name__ == "__main__":
    file_dir = r"S.s2p"
    plt_name = r"SIM1_PPVAR"
    plt_dir = r"C:\Study\Xtract\Run_20220926_093539\Report\Plot\\"
    spec_type = r"Zpdn"
    info = {
        "file_dir": file_dir,
        "plt_name": plt_name,
        "plt_dir": plt_dir,
        "spec_type": spec_type,
    }
    # snp = TouchStone(info)
    snp = TouchStone.from_list([info])
    snp[0].plot_zself_shortsns()
