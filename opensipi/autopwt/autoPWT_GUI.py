# SPDX-FileCopyrightText: © 2025 Google LLC
#
# SPDX-License-Identifier: Apache-2.0
"""main GUI """

# from traceback import print_stack
# from PyCode.utility import PWT_msgbox_print as msgbox
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog, messagebox

# from tkinter import StringVar
import os
import glob
import json
import subprocess
import threading

# import shutil
# import sys
# import logging
import time
import re
from PyCode import google_io
from PyCode import sim_prepare
from PyCode import generate_tcl
from PyCode.utility import get_timestamp

# import concurrent.futures
# import atexit
# import queue
# import shlex


# self.current_process = None # global variable to keep track of the process


class MainGUI:
    """create GUI class"""

    def __init__(self, root):
        self.window = root
        # self.window  = tk.Tk()
        self.window.title("Pixel SIPI Automation")
        # self.window.iconbitmap("pixel_7_pro_BASELINE_P900_FILL0_wght400_GRAD0_opsz48.ico"

        # Register the on_closing method to run when the window is closed
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Create style object and set the theme to "clam"
        self.style = ttk.Style()
        self.style.theme_use("vista")

        # Set minimum size of window
        self.window.minsize(800, 500)

        # create the notebook widget
        self.simulation_tabs = ttk.Notebook(self.window)
        self.simulation_tabs.pack(expand=1, fill="both")
        # -----create PDN tab------

        # --------------------------

        # -----create PWT tab------
        self.pwt_tab = ttk.Frame(self.simulation_tabs)  # create powertree tab
        self.simulation_tabs.add(self.pwt_tab, text="Powertree")
        # create a grid with two columns and configure resize weight
        self.pwt_tab.grid_columnconfigure(0, minsize=200)
        self.pwt_tab.grid_columnconfigure(1, weight=1)
        self.pwt_tab.grid_rowconfigure(1, weight=1)
        # --------------------------
        # -----create PWT tab------
        self.upload_tab = ttk.Frame(self.simulation_tabs)  # create powertree tab
        self.simulation_tabs.add(self.upload_tab, text="Upload")
        # create a grid with two columns and configure resize weight
        self.upload_tab.grid_columnconfigure(0, minsize=200)
        self.upload_tab.grid_columnconfigure(1, weight=1)
        self.upload_tab.grid_rowconfigure(1, weight=1)

        # create SI tab
        # self.SI_tab = ttk.Frame(self.SimulationTabs)#create SI tab
        # self.SimulationTabs.add(self.SI_tab, text ='SI')

        # ==========define some init variables==================
        self.autopwt_setting_path = None
        self.brd_file_path = None
        self.pdn_prj_settings = None
        self.material = None
        self.stackup = None
        self.autopwt_setting_path = None
        self.autopwt_settings = None
        self.pdn_run_button_state = None
        self.sim_date = None
        self.single_brd_workflow = None
        self.multi_brd_workflow = None
        self.upload_workflow = None
        self.result_folder_path = None
        self.script_ver = "1.3"
        self.sig_dir = None
        self.proj_main_path = None
        self.library_path = None
        self.htm2pdf_tool_path = None
        self.in_gsheet_url = None
        self.extracta_path = None
        self.sim_list = None
        self.num_of_simulations = None
        self.current_process = None
        self.stop_processing = False
        self.simulation_finished = False
        self.sim_run_folder_path = None
        self.thread = None
        self.thread2 = None

        # create the tab GUIs
        self.create_pwt_tab()
        self.create_upload_tab()
        self.msg_box_display_logs(
            "Current Auto powertree script is Ver." + self.script_ver
        )

        # Start the GUI
        self.window.mainloop()

    def on_closing(self):
        """functions for closing the autopwt"""
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            if self.current_process:
                self.current_process.terminate()
            if self.thread and self.thread.is_alive():
                self.thread.join()
            self.window.destroy()

    def msg_box_display_logs(self, log_msg):
        """print messages in the GUI simulation tab message box"""
        get_time = get_timestamp()
        self.pwt_msg_box.configure(state=tk.NORMAL)
        self.pwt_msg_box.insert("end", get_time + ": " + log_msg + "\n")
        self.pwt_msg_box.configure(state=tk.DISABLED)

    def upload_msg_box_display_logs(self, log_msg):
        """print messages in the GUI upload tab message box"""
        get_time = get_timestamp()
        self.upload_msg_box.configure(state=tk.NORMAL)
        self.upload_msg_box.insert("end", get_time + ": " + log_msg + "\n")
        self.upload_msg_box.configure(state=tk.DISABLED)

    # ===========================================================
    #   start of PWT tab GUI creation
    # ============================================================
    def create_pwt_tab(self):
        """create a powertree simulation tab GUI"""
        # 1. create a frame for brd and prj_setting button and path box
        # this is at the top of the window
        self.frame_top = tk.Frame(self.pwt_tab, borderwidth=2, relief="groove")
        self.frame_top.grid(
            row=0, column=0, columnspan=2, padx=10, pady=10, sticky="nsew"
        )
        # Create button to load project setting file
        self.pwt_load_file_button = ttk.Button(
            self.frame_top,
            text="Load Project Setting File",
            command=self.pwt_load_setting_file,
        )
        self.pwt_load_file_button.grid(
            row=0, column=0, padx=(10, 10), pady=10, sticky="w"
        )
        # Create Entry box to show the setting filepath
        self.pwt_setting_path_box = ttk.Entry(self.frame_top, width=50)
        self.pwt_setting_path_box.grid(
            row=0, column=1, padx=(10, 10), pady=10, sticky="ew"
        )

        # Create button to just apply stackup
        self.pwt_apply_stackup = ttk.Button(
            self.frame_top, text="Pre-processing", command=self.preprocessing
        )
        self.pwt_apply_stackup.grid(
            row=1, column=0, padx=(10, 10), pady=(0, 10), sticky="w"
        )
        self.pwt_apply_stackup.configure(state="disabled")

        # Configure resizable columns and rows in this top frame
        self.frame_top.grid_columnconfigure(0, minsize=80)
        self.frame_top.grid_columnconfigure(1, weight=1)
        # self.frame_top.grid_columnconfigure(2, minsize=80)

        # 2. create a frame for displaying prj_setting details in msg box
        # this is in the middle of the window
        self.frame_msgbox = tk.Frame(
            self.pwt_tab, height=300, borderwidth=2, relief="groove"
        )
        self.frame_msgbox.grid(
            row=1, column=0, columnspan=2, padx=(5, 10), pady=10, sticky="nsew"
        )

        # construct the message box frame
        pwt_msg_box_label = tk.Label(self.frame_msgbox, text="Output Messages")
        self.pwt_msg_box = tk.Text(self.frame_msgbox, wrap=tk.WORD)
        pwt_msg_box_label.grid(row=0, padx=10, pady=0, sticky="w")
        self.pwt_msg_box.grid(row=1, padx=10, pady=10, sticky="nsew")
        msgbox_scrollbar = tk.Scrollbar(self.frame_msgbox)
        self.pwt_msg_box.config(yscrollcommand=msgbox_scrollbar.set)
        msgbox_scrollbar.config(command=self.pwt_msg_box.yview)
        msgbox_scrollbar.grid(row=1, column=1, padx=(0, 10), pady=0, sticky="nsew")
        self.frame_msgbox.grid_rowconfigure(1, weight=1)
        self.frame_msgbox.grid_columnconfigure(0, weight=1)

        # 3. create a frame for validate, run buttons, and a progress bar
        self.frame1_bot = tk.Frame(self.pwt_tab, borderwidth=2, relief="groove")
        self.frame1_bot.grid(row=3, column=0, padx=(10, 5), pady=10, sticky="nsew")
        self.frame2_bot = tk.Frame(self.pwt_tab, borderwidth=2, relief="groove")
        self.frame2_bot.grid(row=3, column=1, padx=(5, 10), pady=10, sticky="nsew")

        self.pdn_run_button = tk.Button(
            self.frame1_bot, text="RUN", padx=50, pady=15, command=self.pwt_run_toggle
        )
        self.pdn_run_button_state = "RUN"
        self.pdn_run_button.grid(row=0, column=0, padx=10, pady=5, sticky="nse")

    # ====================   end of PWT tab GUI creation ===================

    # ===========================================================
    #   start of upload  tab GUI creation
    # ============================================================

    def create_upload_tab(self):
        """create a upload tab GUI"""
        # 1. create a frame for brd and prj_setting button and path box
        # this is at the top of the window
        frame_top = tk.Frame(self.upload_tab, borderwidth=2, relief="groove")
        frame_top.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        # Create button to load project setting file
        loadfile_button = ttk.Button(
            frame_top,
            text="Load Project Setting File",
            command=self.upload_load_setting_file,
        )
        loadfile_button.grid(row=0, column=0, padx=(10, 10), pady=10, sticky="w")
        # Create Entry box to show the setting filepath
        self.upload_setting_path_box = ttk.Entry(frame_top, width=50)
        self.upload_setting_path_box.grid(
            row=0, column=1, padx=(10, 10), pady=10, sticky="ew"
        )

        # Configure resizable columns and rows in this top frame
        frame_top.grid_columnconfigure(0, minsize=80)
        frame_top.grid_columnconfigure(1, weight=1)
        # self.frame_top.grid_columnconfigure(2, minsize=80)

        # 2. create a frame for displaying prj_setting details in msg box
        # this is in the middle of the window
        self.frame_msgbox = tk.Frame(
            self.upload_tab, height=300, borderwidth=2, relief="groove"
        )
        self.frame_msgbox.grid(
            row=1, column=0, columnspan=2, padx=(5, 10), pady=10, sticky="nsew"
        )

        # construct the message box frame
        pwt_msg_box_label = tk.Label(self.frame_msgbox, text="Output Messages")
        self.upload_msg_box = tk.Text(self.frame_msgbox, wrap=tk.WORD)
        pwt_msg_box_label.grid(row=0, padx=10, pady=0, sticky="w")
        self.upload_msg_box.grid(row=1, padx=10, pady=10, sticky="nsew")
        msgbox_scrollbar = tk.Scrollbar(self.frame_msgbox)
        self.upload_msg_box.config(yscrollcommand=msgbox_scrollbar.set)
        msgbox_scrollbar.config(command=self.upload_msg_box.yview)
        msgbox_scrollbar.grid(row=1, column=1, padx=(0, 10), pady=0, sticky="nsew")
        self.frame_msgbox.grid_rowconfigure(1, weight=1)
        self.frame_msgbox.grid_columnconfigure(0, weight=1)

        # 3. create a frame for validate, run buttons, and a progress bar
        frame1_bot = tk.Frame(self.upload_tab, borderwidth=2, relief="groove")
        frame1_bot.grid(row=3, column=0, padx=(10, 5), pady=10, sticky="nsew")
        frame2_bot = tk.Frame(self.upload_tab, borderwidth=2, relief="groove")
        frame2_bot.grid(row=3, column=1, padx=(5, 10), pady=10, sticky="nsew")

        self.upload_button = tk.Button(
            frame1_bot, text="UPLOAD", padx=50, pady=15, command=self.upload_result
        )
        self.upload_button_button_state = "RUN"
        self.upload_button.grid(row=0, column=0, padx=10, pady=5, sticky="nse")

    # ================================================================================
    #  other functions
    # ================================================================================
    # ===============================================
    # apply stackup function
    # ===============================================

    def preprocessing(self):
        """preocessing function"""
        #   create project folder
        ################################################
        try:
            if not os.path.exists(self.proj_main_path):
                os.makedirs(self.proj_main_path)
        except RuntimeError as e:
            self.msg_box_display_logs(f"Error creating folder: {str(e)}")

        # create the folder path for each PDN run
        self.sim_run_folder_path = os.path.join(self.proj_main_path, "stackup")
        try:
            if not os.path.exists(self.sim_run_folder_path):
                os.makedirs(self.sim_run_folder_path)
                self.msg_box_display_logs(
                    "Simulation run folder is created succesfully"
                )
        except RuntimeError as e:
            self.msg_box_display_logs(f"Error creating folder: {str(e)}")

        #########################################################
        #   create stackup, material file
        #########################################################

        if self.autopwt_settings["stackup_tab_name"]:
            self.material, self.stackup = google_io.stackup_settings_reader(
                self.autopwt_settings["in_gsheet_url"],
                self.autopwt_settings["stackup_tab_name"],
            )
            self.msg_box_display_logs("Stackup info is read!")
            sim_prepare.create_mat_lib(self.sim_run_folder_path, self.material)
            sim_prepare.create_stackup(self.sim_run_folder_path, self.stackup)
        else:
            self.msg_box_display_logs(
                "Stackup info is missing and stack up will not be applied!"
            )

        #########################################################
        #   generate tcl file
        #########################################################
        main_tcl_path = generate_tcl.generate_apply_stackup_tcl(self)

        # if self.Workflow.lower()=='single_IR'.lower():
        #     main_tcl_path=generate_tcl.generate_single_IR_tcl(self)
        # elif self.Workflow.lower()=='single_ResMeas'.lower():
        #     main_tcl_path=generate_tcl.generate_single_ResMeas_tcl(self)

        #########################################################
        #   start simulation
        #########################################################

        sig_dir = os.environ.get("SIGRITY_EDA_DIR").replace("\\", "/")
        if sig_dir[-1] != "/":
            sig_dir = (
                "/".join(sig_dir.split("/")[:-1])
                + "/"
                + self.autopwt_settings["SIG_VER"]
                + "/"
            )
        else:
            sig_dir = (
                "/".join(sig_dir.split("/")[:-2])
                + "/"
                + self.autopwt_settings["SIG_VER"]
                + "/"
            )

        pdc_cmd = (
            os.path.join(sig_dir, "tools/bin/powerdc.exe")
            + ' -PSPowerDC -tcl "'
            + main_tcl_path
            + '"'
        )
        # this is the command to convert the htm report to pdf report

        process = subprocess.Popen(pdc_cmd, shell=False)
        self.msg_box_display_logs("Pre-processing of the board file started!")
        self.msg_box_display_logs("Stackup, amm library will be applied")
        self.msg_box_display_logs("Net-alias info will be removed")
        # Wait for the process to complete
        return_code = process.wait()

        if return_code == 0:
            self.msg_box_display_logs(
                "Pre-process of the brd file completed successfully"
            )
        else:
            self.msg_box_display_logs("Pre-process failed with a non-zero return code")

    # ===============================================
    # load json setting file in PWT tab
    # ===============================================
    def pwt_load_setting_file(self):
        """load the .json file in the GUI"""
        # ====load all the project settings==========================
        try:
            self.autopwt_setting_path = filedialog.askopenfilename(
                filetypes=[("JSON files", "*.json")]
            )
        except FileNotFoundError as e:
            self.msg_box_display_logs(f"Error loading JSON file: {str(e)}")

        if self.autopwt_setting_path:
            self.pwt_setting_path_box.configure(state="normal")
            self.pwt_setting_path_box.delete(0, tk.END)
            self.pwt_setting_path_box.insert(0, self.autopwt_setting_path)
            # self.PWT_setting_path_box.configure(state='disabled')
            with open(self.autopwt_setting_path, "r", encoding="utf-8") as prj_json:
                try:
                    self.autopwt_settings = json.load(prj_json)
                    self.msg_box_display_logs(f"{self.autopwt_setting_path} is read!")

                except FileNotFoundError as e:
                    self.msg_box_display_logs(f"Error reading JSON file: {str(e)}")

            # make it all lower case
            self.single_brd_workflow = [
                item.lower() for item in self.autopwt_settings["single_brd_workflow"]
            ]
            self.multi_brd_workflow = [
                item.lower() for item in self.autopwt_settings["multi_brd_workflow"]
            ]

            self.msg_box_display_logs(
                "PowerDC version is: " + self.autopwt_settings["SIG_VER"]
            )
            # get the sigrity directory
            self.sig_dir = os.environ.get("SIGRITY_EDA_DIR").replace("\\", "/")
            if self.sig_dir[-1] != "/":
                self.sig_dir = (
                    "/".join(self.sig_dir.split("/")[:-1])
                    + "/"
                    + self.autopwt_settings["SIG_VER"]
                    + "/"
                )
            else:
                self.sig_dir = (
                    "/".join(self.sig_dir.split("/")[:-2])
                    + "/"
                    + self.autopwt_settings["SIG_VER"]
                    + "/"
                )

            self.proj_main_path = os.path.join(
                self.autopwt_settings["op_proj_path"],
                self.autopwt_settings["PROJ_FOLDER"],
            )
            self.library_path = self.autopwt_settings["library_path"]
            self.htm2pdf_tool_path = self.autopwt_settings["htm2PDF_tool_path"]
            self.in_gsheet_url = self.autopwt_settings["in_gsheet_url"]
            self.extracta_path = self.autopwt_settings["extracta_path"]

            if self.proj_main_path:
                self.msg_box_display_logs(
                    "PDN Project path is: \n" + self.proj_main_path
                )

            try:
                self.sim_list = google_io.simulation_setting_reader(
                    self.in_gsheet_url,
                    self.autopwt_settings["sim_setup_tab"],
                    self.pwt_msg_box,
                    self.single_brd_workflow,
                    self.multi_brd_workflow,
                )
                self.msg_box_display_logs("Input gsheet is read!")
            except RuntimeError as e:
                self.msg_box_display_logs(f"Error reading input gsheet: {str(e)}")
                raise RuntimeError from e

            self.num_of_simulations = len(self.sim_list)
            if self.num_of_simulations > 0:
                self.msg_box_display_logs(
                    f"No of simulations enabled: {self.num_of_simulations}"
                )
                for i in range(0, self.num_of_simulations):
                    self.msg_box_display_logs(
                        f"{self.sim_list[i]['workflow'].upper()} is enabled for key: "
                        f"{self.sim_list[i]['unique_key']}"
                    )

            # self.PWT_apply_stackup.configure(state='normal')

    # ===============================================
    # load json setting file in upload tab
    # ===============================================

    def upload_load_setting_file(self):
        """load json setting file in upload tab"""
        try:
            self.autopwt_setting_path = filedialog.askopenfilename(
                filetypes=[("JSON files", "*.json")]
            )
        except FileNotFoundError as e:
            self.msg_box_display_logs(f"Error loading JSON file: {str(e)}")

        if self.autopwt_setting_path:
            self.upload_setting_path_box.configure(state="normal")
            self.upload_setting_path_box.delete(0, tk.END)
            self.upload_setting_path_box.insert(0, self.autopwt_setting_path)
            # self.PWT_setting_path_box.configure(state='disabled')
            with open(self.autopwt_setting_path, "r", encoding='utf-8') as prj_json:
                try:
                    self.autopwt_settings = json.load(prj_json)
                    self.upload_msg_box_display_logs(
                        f"{self.autopwt_setting_path} is read!"
                    )

                except FileNotFoundError as e:
                    self.upload_msg_box_display_logs(
                        f"Error reading JSON file: {str(e)}"
                    )

            # make it all lower case
            self.single_brd_workflow = [
                item.lower() for item in self.autopwt_settings["single_brd_workflow"]
            ]
            self.multi_brd_workflow = [
                item.lower() for item in self.autopwt_settings["multi_brd_workflow"]
            ]
            defined_workflows = self.single_brd_workflow + self.multi_brd_workflow

            self.upload_workflow = self.autopwt_settings["Upload_Workflow"].lower()
            self.result_folder_path = self.autopwt_settings["Result_folder_path"]
            self.htm2pdf_tool_path = self.autopwt_settings["htm2PDF_tool_path"]

            if self.upload_workflow.lower() not in defined_workflows:
                self.upload_msg_box_display_logs(
                    "Wrong work flow is defined. Please check"
                )
                raise ValueError
            else:
                self.upload_msg_box_display_logs(
                    f"{self.upload_workflow} result will be uploaded"
                )

    # ===============================================
    # upload result function
    # ===============================================
    def upload_result(self):
        """upload result function"""
        # find the simulation report file
        sim_info = {}
        result_folder_path = self.autopwt_settings["Result_folder_path"]
        sim_info["Result_folder_path"] = self.autopwt_settings["Result_folder_path"]
        sim_info["out_gsheet_url"] = self.autopwt_settings["out_gsheet_url"]
        sim_info["out_gsheet_tab"] = self.autopwt_settings["out_gsheet_tab"]
        sim_info["workflow"] = self.autopwt_settings["Upload_Workflow"]
        sim_info["report_in_PDF"] = self.autopwt_settings["report_in_PDF"]
        pdn_report_url = ""
        report_htm_path = None
        report_pdf_path = None

        # List all PDF and htm files in the folder that start with "Simulation"
        pdf_pattern = re.compile(r".*report.*\.pdf", re.IGNORECASE)
        pdf_files = [
            file
            for file in glob.glob(os.path.join(result_folder_path, "*"))
            if pdf_pattern.search(file)
        ]
        htm_pattern = re.compile(r".*report.*\.htm", re.IGNORECASE)
        htm_files = [
            file
            for file in glob.glob(os.path.join(result_folder_path, "*"))
            if htm_pattern.search(file)
        ]

        # pdf_files = glob.glob(os.path.join(Result_folder_path, "Simulation*report*.pdf"))
        # htm_files = glob.glob(os.path.join(Result_folder_path, "Simulation*report*.htm"))

        if sim_info["report_in_PDF"].lower() == "yes":
            # Check if any PDF files were found
            if pdf_files:
                # Sort the PDF files by modification time in descending order (most recent first)
                pdf_files.sort(key=os.path.getmtime, reverse=True)
                # Get the path of the most recent PDF file and upload to drive
                report_pdf_path = pdf_files[0]
                try:
                    pdn_report_url = google_io.pdf_drive_upload(
                        self.autopwt_settings["drive_folder_url"], report_pdf_path
                    )  # upload PDF report to drive
                    self.upload_msg_box_display_logs(
                        "PDF report is uploaded to Google Drive"
                    )
                except RuntimeError as e:
                    self.upload_msg_box_display_logs(
                        f"Error uploading PDF report: {str(e)}"
                    )

            # check if any htm files are there and convert to pdf file
            else:
                if htm_files:
                    # Sort the PDF files by modification time
                    # in descending order (most recent first)
                    htm_files.sort(key=os.path.getmtime, reverse=True)
                    # Get the path of the most recent htm file and upload to drive
                    report_htm_path = htm_files[0]

                    # if tool conversion path exists, conver to pdf and upload to drive
                    if self.htm2pdf_tool_path:
                        directory, file_name_with_extension = os.path.split(
                            report_htm_path
                        )
                        file_name_without_extension, _ = os.path.splitext(
                            file_name_with_extension
                        )
                        # Create the new file path with the ".htm" extension
                        report_pdf_path = os.path.join(
                            directory, file_name_without_extension + ".pdf"
                        )
                        # pdf_conversion_cmd=self.htm2PDF_tool_path + r'
                        # --image-dpi 1200 --image-quality 100 --page-width 500mm
                        # --page-height 800mm -B 0 -T 0 --enable-local-file-access '
                        # + shlex.quote(Report_htm_path) + ' ' + shlex.quote(Report_pdf_path)

                        pdf_conversion_cmd = [
                            self.htm2pdf_tool_path,
                            "--image-dpi",
                            "1200",
                            "--image-quality",
                            "100",
                            "--page-width",
                            "500mm",
                            "--page-height",
                            "800mm",
                            "-B",
                            "0",
                            "-T",
                            "0",
                            "--enable-local-file-access",
                            report_htm_path,
                            report_pdf_path,
                        ]
                        # pdf_conversion_cmd = [shlex.quote(arg) for arg in pdf_conversion_cmd]
                        # PDF_gen_process=subprocess.Popen(pdf_conversion_cmd)

                        try:
                            # subprocess.run(' '.join(pdf_conversion_cmd), shell=True)
                            # convert htm report to PDF report
                            pdf_gen_process = subprocess.Popen(pdf_conversion_cmd)
                            # wait fo the process to finish before attemtping uploading the file
                            pdf_gen_process.wait()
                            self.upload_msg_box_display_logs(
                                "Simulation report file is generated"
                            )
                        except RuntimeError as e:
                            self.upload_msg_box_display_logs(
                                f"Error creating PDF report: {str(e)}"
                            )
                        # uploading the PDF report to drive
                        try:
                            pdn_report_url = google_io.pdf_drive_upload(
                                self.autopwt_settings["drive_folder_url"],
                                report_pdf_path,
                            )  # upload PDF report to drive
                            self.upload_msg_box_display_logs(
                                "PDF report is uploaded to Google Drive"
                            )
                        except RuntimeError as e:
                            self.upload_msg_box_display_logs(
                                f"Error uploading PDF report: {str(e)}"
                            )
        else:
            # uploading the htm report to drive
            try:
                # if sim_info['workflow'].lower() in self.AutoPWT_settings['single_brd_workflow']:
                pdn_report_url = google_io.pdf_drive_upload(
                    self.autopwt_settings["drive_folder_url"], report_htm_path
                )  # upload PDF report to drive
                self.msg_box_display_logs("Html report is uploaded to Google Drive")
            except RuntimeError as e:
                self.msg_box_display_logs(f"Error uploading Html report: {str(e)}")

        sim_info["PDN_report_url"] = pdn_report_url

        try:
            # write result to google spreadsheet
            google_io.brd_result_writter(sim_info, self.pwt_msg_box)
            self.upload_msg_box_display_logs("Simulation result is uploaded to Gsheet")
        except RuntimeError as e:
            self.upload_msg_box_display_logs(
                f"Error uploading result to Gsheet {str(e)}"
            )

    # ===============================================
    #  powertree RUN button action
    # ===============================================

    def pwt_run_toggle(self):
        """start or stop when press the run buttom"""
        if self.pdn_run_button_state == "RUN":
            # self.start_function()
            self.pdn_run_button_state = "STOP"
            self.pdn_run_button.config(text="STOP")
            # -----freeze GUI widgets to prevent settings changes
            self.pwt_load_file_button.config(state="disabled")
            self.pwt_setting_path_box.config(state="disabled")
            # -----freeze GUI widgets to prevent settings changes
            # start simulation
            self.pwt_sim_start()

        else:
            # self.PDN_RUN_button_state == "STOP"
            # self.start_function()
            self.stop_processing = True
            self.kill_process()

            # -----un freeze GUI widgets
            self.pdn_run_button_state = "RUN"
            self.pdn_run_button.config(text="RUN")
            self.pwt_load_file_button.config(state="normal")
            self.pwt_setting_path_box.config(state="normal")
            self.msg_box_display_logs("Simulation Terminated!")

    # ===============================================
    #  action when run button is pressed
    # ===============================================

    def pwt_sim_start(self):
        """start the powertree simulation"""
        # get simulation time
        t = time.localtime()
        if t.tm_mon < 10:
            t_mon = "".join(["0", str(t.tm_mon)])
        else:
            t_mon = str(t.tm_mon)
        if t.tm_mday < 10:
            t_day = "".join(["0", str(t.tm_mday)])
        else:
            t_day = str(t.tm_mday)
        if t.tm_hour < 10:
            t_hour = "".join(["0", str(t.tm_hour)])
        else:
            t_hour = str(t.tm_hour)
        if t.tm_min < 10:
            t_min = "".join(["0", str(t.tm_min)])
        else:
            t_min = str(t.tm_min)
        self.sim_date = "".join([str(t.tm_year), t_mon, t_day, "_", t_hour, t_min])

        ################################################
        #   create project folder based on date
        ################################################
        try:
            if not os.path.exists(self.proj_main_path):
                os.makedirs(self.proj_main_path)
        except RuntimeError as e:
            self.msg_box_display_logs(f"Error creating folder: {str(e)}")

        # create the folder path for each PDN run
        self.sim_run_folder_path = os.path.join(self.proj_main_path, self.sim_date)
        try:
            if not os.path.exists(self.sim_run_folder_path):
                os.makedirs(self.sim_run_folder_path)
                self.msg_box_display_logs(
                    "Simulation run folder is created succesfully"
                )
        except RuntimeError as e:
            self.msg_box_display_logs(f"Error creating folder: {str(e)}")

        ################################################
        #   create folder for each simulation key
        ################################################
        command_list = []  # command list to run tcl file
        for item in self.sim_list:
            workflow = item["workflow"].lower()
            if workflow in self.single_brd_workflow:
                sim_run_key_folder_path = os.path.join(
                    self.sim_run_folder_path, item["unique_key"]
                )
                if not os.path.exists(sim_run_key_folder_path):
                    os.makedirs(sim_run_key_folder_path)

                # define result  folder and report path

                # Result_folder_path=os.path.join(sim_run_key_folder_path, 'Result_folder')
                report_htm_path = os.path.join(
                    sim_run_key_folder_path,
                    f"Simulation_report_{item['unique_key']}_{self.sim_date}.htm",
                )
                #########################################################
                #   create stackup, material file
                #########################################################

                if item["Stackup_info"]:
                    material, stackup = google_io.stackup_settings_reader(
                        self.in_gsheet_url, item["Stackup_info"]["Stackup_info"]
                    )
                    self.msg_box_display_logs(
                        f"Stackup info is read for key: {item['unique_key']}!"
                    )
                    sim_prepare.create_mat_lib(sim_run_key_folder_path, material)
                    sim_prepare.create_stackup(sim_run_key_folder_path, stackup)
                    self.msg_box_display_logs(
                        f"Stackup.csv and material.cmx is created for key: {item['unique_key']}!"
                    )
                else:
                    self.msg_box_display_logs(
                        "Stackup info is missing and stack up will not be applied"
                    )

                #########################################################
                #   check simulation options
                #########################################################
                dns_list_file = ""
                if item["simulation_options"]:
                    option_list = item["simulation_options"].split(";")
                    for option in option_list:
                        if option:
                            option_type, argument = option.split(":")
                            if option_type == "DNS_filter":
                                dns_list_file = sim_prepare.generate_dns_list(
                                    sim_run_key_folder_path,
                                    item["Brd_path"]["Brd_path"],
                                    self.extracta_path,
                                    argument,
                                )

                #########################################################
                #   generate tcl file
                #########################################################
                sim_info = {}
                sim_info["sim_run_folder_path"] = sim_run_key_folder_path
                # sim_info['Result_folder_path']=Result_folder_path
                sim_info["brd_file_path"] = item["Brd_path"]["Brd_path"]
                sim_info["PWT_path"] = item["PWT_path"]
                sim_info["library_path"] = self.library_path
                sim_info["msgbox"] = self.pwt_msg_box
                sim_info["Report_htm_path"] = report_htm_path
                sim_info["sim_date"] = self.sim_date
                pdc_cmd = ''
                if dns_list_file:
                    sim_info["DNS_list_file"] = dns_list_file

                if workflow.lower() == "single_IR".lower():
                    main_tcl_path = generate_tcl.generate_single_ir_tcl(sim_info)
                    pdc_cmd = (
                        os.path.join(self.sig_dir, "tools/bin/powerdc.exe")
                        + ' -PSPowerDC -tcl "'
                        + main_tcl_path
                        + '"'
                    )
                elif workflow.lower() == "single_ResMeas".lower():
                    main_tcl_path = generate_tcl.generate_single_resmeas_tcl(sim_info)
                    pdc_cmd = (
                        os.path.join(self.sig_dir, "tools/bin/powerdc.exe")
                        + ' -PSPowerDC -tcl "'
                        + main_tcl_path
                        + '"'
                    )
                elif workflow.lower() == "single_limitedIR".lower():
                    main_tcl_path = generate_tcl.generate_single_limitedir_tcl(sim_info)
                    pdc_cmd = (
                        os.path.join(self.sig_dir, "tools/bin/powerdc.exe")
                        + ' -PSCelsiusDC_G -tcl "'
                        + main_tcl_path
                        + '"'
                    )

                command_list.append(pdc_cmd)

            if workflow in self.multi_brd_workflow:
                # define result  folder and report path
                sim_run_key_folder_path = os.path.join(
                    self.sim_run_folder_path, item["unique_key"]
                )
                if not os.path.exists(sim_run_key_folder_path):
                    os.makedirs(sim_run_key_folder_path)

                # change sigrity to 2023.1
                self.sig_dir = os.environ.get("SIGRITY_EDA_DIR").replace("\\", "/")
                sig_ver = self.autopwt_settings["SIG_VER"]
                # SIG_VER='Sigrity2023.1'
                if self.sig_dir[-1] != "/":
                    self.sig_dir = (
                        "/".join(self.sig_dir.split("/")[:-1]) + "/" + sig_ver + "/"
                    )
                else:
                    self.sig_dir = (
                        "/".join(self.sig_dir.split("/")[:-2]) + "/" + sig_ver + "/"
                    )

                # Result_folder_path=os.path.join(sim_run_key_folder_path, 'Result_folder')
                report_htm_path = os.path.join(
                    sim_run_key_folder_path,
                    f"Simulation_report_{item['unique_key']}_{self.sim_date}.htm",
                )

                #########################################################
                #   create stackup, material file for each brd file
                #########################################################

                block_keys = item["Stackup_info"].keys()
                stackup_path = {}
                material_path = {}
                list_dns_files = {}
                # simulation_options_multi = {}
                apply_stackup_key = []
                # apply_sim_options_key = []
                for key in block_keys:
                    block_stackup = item["Stackup_info"][key]
                    simulation_brd_option = item["simulation_options"][key]
                    # --- generate stackup files for each brd if the stackup info is provided----
                    if block_stackup:

                        material, stackup = google_io.stackup_settings_reader(
                            self.in_gsheet_url, block_stackup
                        )
                        stackup_path[key] = sim_prepare.create_mat_lib(
                            sim_run_key_folder_path, material, f"{key}_material.cmx"
                        )
                        material_path[key] = sim_prepare.create_stackup(
                            sim_run_key_folder_path, stackup, f"{key}_stackup.csv"
                        )
                        apply_stackup_key.append(key)
                        self.msg_box_display_logs(
                            f"Stackup.csv and material.cmx is created for key: "
                            f"{item['unique_key']}, block:{key}!"
                        )

                    # --- check simulations for each board----

                    if simulation_brd_option:
                        read_option_input_info = {}
                        read_option_input_info["sim_run_key_folder_path"] = (
                            sim_run_key_folder_path
                        )
                        read_option_input_info["brd_file_path"] = item["Brd_path"][key]
                        read_option_input_info["extracta_path"] = self.extracta_path
                        read_options = sim_prepare.read_sim_options(
                            simulation_brd_option, read_option_input_info
                        )
                        try:
                            dns_list_file = read_options["DNS_csv_file_path"]
                            list_dns_files[key] = dns_list_file
                        except FileNotFoundError:
                            list_dns_files[key] = ""

                self.msg_box_display_logs(
                    f"All stackup info is read for key: {item['unique_key']}!"
                )
                sim_info = {}
                sim_info["sim_run_folder_path"] = sim_run_key_folder_path
                # Result_folder_path=sim_info['Result_folder_path']
                sim_info["brd_file_path"] = item["Brd_path"]
                sim_info["PWT_path"] = item["PWT_path"]
                sim_info["stackup_path"] = stackup_path
                sim_info["material_path"] = material_path
                sim_info["library_path"] = self.library_path
                sim_info["msgbox"] = self.pwt_msg_box
                sim_info["Report_htm_path"] = report_htm_path
                sim_info["apply_stackup_key"] = apply_stackup_key
                sim_info["list_DNS_files"] = list_dns_files

                if workflow.lower() == "multibrd_IR".lower():
                    main_tcl_path = generate_tcl.generate_multibrd_ir_tcl(sim_info)
                    pdc_cmd = (
                        os.path.join(self.sig_dir, "tools/bin/powerdc.exe")
                        + ' -PSPowerDC -tcl "'
                        + main_tcl_path
                        + '"'
                    )
                elif workflow.lower() == "multibrd_limitedIR".lower():
                    main_tcl_path = generate_tcl.generate_multibrd_limitedir_tcl(
                        sim_info
                    )
                    pdc_cmd = (
                        os.path.join(self.sig_dir, "tools/bin/powerdc.exe")
                        + ' -PSCelsiusDC_G -tcl "'
                        + main_tcl_path
                        + '"'
                    )

                command_list.append(pdc_cmd)

        self.thread = threading.Thread(
            target=self.sequential_sim_run, args=(command_list,)
        )
        self.thread.start()
        self.msg_box_display_logs(
            f"Simulation started! Total of simulations: {len(self.sim_list)}"
        )

        # Check if the process has completed or stoped in a separate thread
        self.thread2 = threading.Thread(target=self.check_process_completion)
        self.thread2.start()

    def sequential_sim_run(self, cmd_list):
        """start sequential simulatoin runs"""
        # global self.current_process
        for cmd in cmd_list:
            if self.stop_processing:
                break

            self.current_process = subprocess.Popen(cmd, shell=False)
            return_code = self.current_process.wait()

            if return_code == 0:
                print(f"Command '{cmd}' completed successfully.")
            else:
                print(f"Command '{cmd}' failed with return code {return_code}")

        if self.stop_processing is False:
            self.simulation_finished = True

        else:
            self.simulation_finished = False
            self.current_process = None
            self.stop_processing = False

        # self.msg_box_display_logs("Power DC simulation is finished!")
        # #unfreeze the GUI
        # self.PDN_RUN_button_state = "RUN"
        # self.PDN_RUN_button.config(text="RUN")
        # self.PWT_loadfile_button.config(state='normal')
        # self.PWT_setting_path_box.config(state='normal')
        # self.msg_box_display_logs("Begin post-processing...")
        # self.Post_processing()

    # ===============================================
    #  action when stop button is pressed
    # ===============================================

    def kill_process(self):
        """stop simulation process"""
        if self.current_process:
            self.current_process.kill()
            self.stop_processing = True
            self.current_process = None
        if self.thread and self.thread.is_alive():
            self.thread.join()  # Wait for the thread to finish

        #########################################################
        #   start parallel simulation
        #########################################################

        # if sim_status==0:
        #     self.msg_box_display_logs('All simulations are completed')
        # if sim_status==1:
        #     self.msg_box_display_logs('Some simulations are completed')

        # Get the result from the queue
        # result = result_queue.get()
        # result_queue.task_done()

        # Perform another function or use the result as needed
        # print(f"Result: {result}")

        # begin post processing#
        # self.Post_processing()

    # ===============================================
    #  check simulation process
    # ===============================================

    def check_process_completion(self):
        """check if simulation is completed"""
        count = 0
        # simdone_file_path=os.path.join(self.sim_run_folder_path,'spddone.out')
        while self.thread.is_alive():
            if count % 60 == 0:
                # print msg every 300 seconds
                self.msg_box_display_logs("In progress...")
            time.sleep(5)
            count += 1
        if self.simulation_finished is True:
            self.msg_box_display_logs("Power DC simulation is finished!")
            self.pdn_run_button_state = "RUN"
            self.pdn_run_button.config(text="RUN")
            self.pwt_load_file_button.config(state="normal")
            self.pwt_setting_path_box.config(state="normal")
            self.post_processing()

        #

    # ===============================================
    #  post processing function
    # ===============================================

    def post_processing(self):
        """start post processing after simulation is done"""
        for item in self.sim_list:
            workflow = item["workflow"].lower()
            if (
                workflow in self.single_brd_workflow
                or workflow in self.multi_brd_workflow
            ):
                sim_run_key_folder_path = os.path.join(
                    self.sim_run_folder_path, item["unique_key"]
                )
                if not os.path.exists(sim_run_key_folder_path):
                    os.makedirs(sim_run_key_folder_path)

                report_htm_path = os.path.join(
                    sim_run_key_folder_path,
                    f"Simulation_report_{item['unique_key']}_{self.sim_date}.htm",
                )
                report_pdf_path = os.path.join(
                    sim_run_key_folder_path,
                    f"Simulation_report_{item['unique_key']}_{self.sim_date}.pdf",
                )

                # find the latest auto generated folder that contains the csv folder
                if os.path.exists(sim_run_key_folder_path):
                    folder_paths = [
                        os.path.join(sim_run_key_folder_path, folder)
                        for folder in os.listdir(sim_run_key_folder_path)
                        if os.path.isdir(os.path.join(sim_run_key_folder_path, folder))
                    ]

                    if folder_paths:
                        result_folder_path = max(
                            folder_paths, key=lambda f: os.path.getctime(f)
                        )
                        print(
                            f"The latest folder is: {os.path.basename(result_folder_path)}"
                        )
                    else:
                        print("No folders found in the directory.")
                else:
                    print("The specified directory does not exist.")

                pdn_report_url = ""
                sim_info = {}
                try:
                    sim_info["Result_folder_path"] = result_folder_path
                except FileNotFoundError:
                    print(
                        f"Result folder is not found in {folder_paths}, "
                        "please check the simulation folder"
                    )
                sim_info["out_gsheet_url"] = item["out_gsheet_url"]
                sim_info["out_gsheet_tab"] = item["out_gsheet_tab"]
                sim_info["workflow"] = workflow

                if os.path.exists(report_htm_path):
                    # convert the htm report to pdf report if c
                    # onversion tool exe path is provided and option is yes
                    if (
                        self.htm2pdf_tool_path != ""
                        and self.autopwt_settings["report_in_PDF"].lower() == "yes"
                    ):
                        pdf_conversion_cmd = [
                            self.htm2pdf_tool_path,
                            "--image-dpi",
                            "1200",
                            "--image-quality",
                            "100",
                            "--page-width",
                            "500mm",
                            "--page-height",
                            "800mm",
                            "-B",
                            "0",
                            "-T",
                            "0",
                            "--enable-local-file-access",
                            report_htm_path,
                            report_pdf_path,
                        ]
                        try:
                            # convert htm report to PDF report
                            pdf_gen_process = subprocess.Popen(pdf_conversion_cmd)
                            # wait fo the process to finish before attemtping uploading the file
                            pdf_gen_process.wait()
                        except RuntimeError as e:
                            self.msg_box_display_logs(
                                f"Error creating PD report for key {item['unique_key']}: {str(e)}"
                            )
                        # uploading the PDF report to drive
                        try:
                            pdn_report_url = google_io.pdf_drive_upload(
                                item["drive_folder_url"], report_pdf_path
                            )  # upload PDF report to drive
                            self.msg_box_display_logs(
                                f"PDF report is uploaded to Google Drive for {item['unique_key']}"
                            )
                            sim_info["PDN_report_url"] = pdn_report_url
                        except RuntimeError as e:
                            self.msg_box_display_logs(
                                f"Error uploading PDF report for key {item['unique_key']}: {str(e)}"
                            )
                    else:
                        # uploading the htm report to drive
                        try:
                            pdn_report_url = google_io.pdf_drive_upload(
                                item["drive_folder_url"], report_htm_path
                            )  # upload PDF report to drive
                            self.msg_box_display_logs(
                                f"Html report is uploaded to Google Drive for {item['unique_key']}"
                            )
                            sim_info["PDN_report_url"] = pdn_report_url
                        except RuntimeError as e:
                            self.msg_box_display_logs(
                                f"Error uploading Html report for key {item['unique_key']}: "
                                f"{str(e)}"
                            )

                else:
                    # no report found
                    self.msg_box_display_logs(
                        "Report file is not found! No report will be uploaded"
                    )

                try:
                    # write result to google spreadsheet
                    google_io.brd_result_writter(sim_info, self.pwt_msg_box)
                    self.msg_box_display_logs(
                        f"Simulation result is uploaded to Gsheet for {item['unique_key']}"
                    )
                except RuntimeError as e:
                    self.msg_box_display_logs(
                        f"Error uploading result to Gsheet for key {item['unique_key']}: {str(e)}"
                    )

            # elif workflow in self.multi_brd_workflow:
            #     pass

        self.msg_box_display_logs("All post processing is complete")
        self.msg_box_display_logs("Simulation Done!")


if __name__ == "__main__":
    root = tk.Tk()
    app = MainGUI(root)
    root.mainloop()
