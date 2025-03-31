# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
Author: yanshengw@
Created on Nov. 1, 2022
Last updated on Mar. 20, 2025

Description:
    This module handles one touchstone file.
"""


from math import log10

import matplotlib.pyplot as plt
import skrf as rf

from opensipi.util.common import (
    SL,
    lol_numerical_add_list,
    make_dir,
    split_str_at_last_symbol,
)


class TouchStone:
    """"""

    def __init__(self, info):
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
        """Automatically process SNP files based on spect_type."""
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
        """Use connectivity list to determine Zin plot. Leave the sense ports
        floating and plot the self Zs for the rest ports.
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
        """Use connectivity list to determine Zin plot. Short the sense ports
        and plot the self Zs for the rest ports.
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
        """Plot insertion loss based on the connectivity dict."""
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
        """Plot return loss based on the connectivity dict."""
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
        """Plot mixed-mode insertion loss based on the connectivity dict."""
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
        """Plot mixed-mode return loss based on the connectivity dict."""
        nw_dd, _, _, nw_cc = self.__split_mixedmode_network(nw_mm_s_db)
        out_dict = {}
        # Diff_Diff
        out_dict["DD"] = self.plot_rl(conn_list, nw_dd, prockey, "SDD")
        # Comm_Comm
        out_dict["CC"] = self.plot_rl(conn_list, nw_cc, prockey, "SCC")
        return out_dict

    def plot_zmag(self, fig_data, fig_title, fig_dir):
        """Plot Zmag vs. freq (GHz).
        fig_data = [[f1, Z1, option], [f2, Z2, option], ...]
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
        """Plot Smag vs. freq (GHz).
        fig_data = [[f1, S1, option], [f2, S2, option], ...]
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
        """Plot TDR for given ports."""
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
        """Plot TDR for Mixed-mode ports."""
        out_dict = {}
        # Diff_Diff
        out_dict["DD"] = self.plot_tdr(conn_list, nw_raw, prockey, "DD")
        # Comm_Comm
        mm_port_num = int(self.port_num / 2)
        # ???? a bug to fix
        conn_list_cc = lol_numerical_add_list(conn_list, [mm_port_num])
        out_dict["CC"] = self.plot_tdr(conn_list_cc, nw_raw, prockey, "CC")
        return out_dict

    def plot_time_domain(self, conn_list, fig_data, fig_title, fig_dir):
        """Plot time domain response."""
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
        """Convert SNP files from single-ended to mixed-mode Spara."""
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
        """Get mixedmode network if necessary."""
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
        """Split one mixed-mode network into four sub-networks."""
        mm_port_num = int(self.port_num / 2)
        nw_dd = nw_mm[:, 0:mm_port_num, 0:mm_port_num]
        nw_dc = nw_mm[:, 0:mm_port_num, mm_port_num:]
        nw_cd = nw_mm[:, mm_port_num:, 0:mm_port_num]
        nw_cc = nw_mm[:, mm_port_num:, mm_port_num:]
        return nw_dd, nw_dc, nw_cd, nw_cc

    def __get_short_block(self):
        """Get a 1-port short block based on the input touchstone file."""
        short0 = rf.data.wr2p2_short
        short0.resample(self.nw.frequency.npoints)
        short0.f = self.f
        return short0

    def __get_rlc(self, nw, i_port, snp_dir):
        """Return RLC at specified frequencies."""
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
        """Input network class, target freq, and target port.
        Output interpolated z in Ohm and angle in unwrapped rad.
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
        """Input a list of dict and output a list of snp class."""
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
