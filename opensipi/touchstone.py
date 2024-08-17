# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
Author: yanshengw@
Created on Nov. 1, 2022
Last updated on Nov. 1, 2022

Description:
    This module handles touchstone files.
"""


from math import log10

import matplotlib.pyplot as plt
import skrf as rf


class TouchStone:
    """"""

    def __init__(self, info):
        # define constants
        self.All_SPEC_TYPE = [
            ["Zpdn"],  # 0, No need to short sns port
            ["Zl"],  # 1, short sns port
            ["Spcie6", "Sddr5"],  # 2, HSIO
            ["Sls"],  # 3, LSIO
        ]
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

    def auto_plot(self):
        """Automatically select the right way to plot figures based on
        the spec_type.
        """
        output_list = []
        if self.spec_type in self.All_SPEC_TYPE[0]:
            output_list = self.plot_zself()
        elif self.spec_type in self.All_SPEC_TYPE[1]:
            output_list = self.plot_zself_shortsns()
        elif self.spec_type in self.All_SPEC_TYPE[2]:
            temp_list1 = self.plot_il()
            temp_list2 = self.plot_rl()
            output_list = [temp_list1, temp_list2]
        elif self.spec_type in self.All_SPEC_TYPE[3]:
            temp_list1 = self.plot_il()
            temp_list2 = self.plot_rl()
            output_list = [temp_list1, temp_list2]
        return output_list

    def plot_zself(self):
        """Use connectivity list to determine Zin plot. Leave the sense ports
        floating and plot the self Zs for the rest ports.
        """
        output_list = []
        last_plot_port_index = len(self.conn_dict["ZIN"])  # starting from 1
        nw = self.nw
        for i_port in range(last_plot_port_index):  # starting from 0
            zself = nw.z_mag[:, i_port, i_port]
            fig_data = [[self.f, zself]]
            fig_title = self.key_name + "_Port" + str(i_port + 1)
            fig_dir = self.plt_dir + fig_title + ".png"
            self.plot_zmag(fig_data, fig_title, fig_dir)
            # extract LC
            snp_dir = self.file_dir
            _, l_hf, c_lf = self.__get_rlc(nw, i_port, snp_dir)
            output_list.append([fig_title, fig_dir, "", f"{l_hf:.2f}", f"{c_lf:.2f}"])
        return output_list

    def plot_zself_shortsns(self):
        """Use connectivity list to determine Zin plot. Short the sense ports
        and plot the self Zs for the rest ports.
        """
        output_list = []
        last_plot_port_index = len(self.conn_dict["ZIN"])  # starting from 1
        short_port_number = self.nw.number_of_ports - last_plot_port_index
        nw_red = self.nw
        # short all sns ports
        while short_port_number > 0:
            # from 0
            last_short_port = last_plot_port_index + short_port_number - 1
            nw_red = rf.connect(nw_red, last_short_port, self.short0, 0)
            short_port_number -= 1

        for i_port in range(nw_red.number_of_ports):
            zself = nw_red.z_mag[:, i_port, i_port]
            fig_data = [[self.f, zself]]
            fig_title = self.key_name + "_Port" + str(i_port + 1)
            fig_dir = self.plt_dir + fig_title + ".png"
            self.plot_zmag(fig_data, fig_title, fig_dir)

            # extract RL
            snp_dir = self.file_dir
            r_dc, l_hf, _ = self.__get_rlc(nw_red, i_port, snp_dir)
            output_list.append([fig_title, fig_dir, f"{r_dc:.2f}", f"{l_hf:.2f}", ""])
        return output_list

    def plot_il(self):
        """Plot insertion loss based on the connectivity dict."""
        output_list = []
        fig_data = []
        for i_conn in self.conn_dict["IL"]:
            sil = self.nw.s_db[:, i_conn[0] - 1, i_conn[1] - 1]
            label = "Port" + str(i_conn[0]) + "to" + str(i_conn[1])
            fig_data.append([self.f, sil, {"label": label}])
        fig_title = self.key_name + "_IL"
        fig_dir = self.plt_dir + fig_title + ".png"
        self.plot_smag(fig_data, fig_title, fig_dir)
        output_list.append([fig_title, fig_dir])
        return output_list

    def plot_rl(self):
        """Plot return loss based on the connectivity dict."""
        output_list = []
        fig_data = []
        for i_conn in self.conn_dict["RL"]:
            srl = self.nw.s_db[:, i_conn - 1, i_conn - 1]
            label = "Port" + str(i_conn)
            fig_data.append([self.f, srl, {"label": label}])
        fig_title = self.key_name + "_RL"
        fig_dir = self.plt_dir + fig_title + ".png"
        self.plot_smag(fig_data, fig_title, fig_dir)
        output_list.append([fig_title, fig_dir])
        return output_list

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
        c_lf = 1 / z_lf / (2 * 3.14 * freq_tgt) * 1e6  # uF
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
