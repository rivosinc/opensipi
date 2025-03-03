# SPDX-FileCopyrightText: © 2025 Google LLC
#
# SPDX-License-Identifier: Apache-2.0
"""prepare simulation files"""
import os
import shutil
import subprocess
import re
import glob
# from PyCode.utility import PWT_msgbox_print


# sim_run_path=os.getcwd()
def create_mat_lib(sim_run_folder_path, material, material_filename="material.cmx"):
    """Create material library."""
    # sim_run_folder_path=sim_info.sim_run_folder_path
    # material=sim_info.material
    # msg_box_display_logs=sim_info.msg_box_display_logs
    material_file_path = os.path.join(sim_run_folder_path, material_filename)

    try:
        with open(material_file_path, "w", encoding='utf-8') as file:
            # Write the preamles for cmx file
            file.write(r'<?xml version="1.0" encoding="UTF-8"?>' + "\n")
            file.write(r'<Cadence_Material_Lib Version="1.02">' + "\n")
            file.write(r"<DataDescriptions>" + "\n")
            file.write(r"<Material>" + "\n")
            file.write(
                r'<Column name="Default Thickness" unit="um" />	</Material>' + "\n"
            )
            file.write(r"<Metal>" + "\n")
            file.write(r'<Column name="Temperature" unit="C" />' + "\n")
            file.write(r'<Column name="Conductivity" unit="S/m" />' + "\n")
            file.write(r"</Metal>" + "\n")
            file.write(r"<Dielectric>" + "\n")
            file.write(r'<Column name="Temperature" unit="C" />' + "\n")
            file.write(r'<Column name="Frequency" unit="MHz" />' + "\n")
            file.write(r'<Column name="Relative Permittivity" />' + "\n")
            file.write(r'<Column name="LossTangent" />' + "\n")
            file.write(r"</Dielectric>" + "\n")
            file.write(r"<Thermal>" + "\n")
            file.write(r'<Column name="Temperature" unit="C" />' + "\n")
            file.write(r'<Column name="Conductivity" unit="W/(m*K)" />' + "\n")
            file.write(r'<Column name="Density" unit="kg/m^3" />' + "\n")
            file.write(r'<Column name="Specific heat" unit="J/(kg*K)" />' + "\n")
            file.write(r"</Thermal>" + "\n")
            file.write(r"<Magnetic>" + "\n")
            file.write(r'<Column name="Frequency" unit="MHz" />' + "\n")
            file.write(r'<Column name="ur(real)" />' + "\n")
            file.write(r'<Column name="ur(-imag)" />' + "\n")
            file.write(r"</Magnetic>" + "\n")
            file.write(r"<SurfaceRoughness>" + "\n")
            file.write(r"<Huray>" + "\n")
            file.write(r'<Column name="Surface Ratio" />' + "\n")
            file.write(r'<Column name="Snowball Radius" unit="um" />' + "\n")
            file.write(r"</Huray>" + "\n")
            file.write(r"<ModHammerstad>" + "\n")
            file.write(r'<Column name="Roughness Factor" />' + "\n")
            file.write(r'<Column name="RMS value" unit="um" />' + "\n")
            file.write(r"</ModHammerstad>" + "\n")
            file.write(r"</SurfaceRoughness>" + "\n")
            file.write(r"<Structural>" + "\n")
            file.write(r"<Elasticity>" + "\n")
            file.write(r'<Column name="Temperature" unit="C" />' + "\n")
            file.write(r'<Column name="Youngs Modulus" unit="Pa" />' + "\n")
            file.write(r'<Column name="Poissons Ratio" />' + "\n")
            file.write(r"</Elasticity>" + "\n")
            file.write(r"<CTE>" + "\n")
            file.write(r'<Column name="Reference Temperature" unit="C" />' + "\n")
            file.write(r'<Column name="Temperature" unit="C" />' + "\n")
            file.write(r'<Column name="CTE" unit="1/C" />' + "\n")
            file.write(r"</CTE>" + "\n")
            file.write(r"</Structural>" + "\n")
            file.write(r"</DataDescriptions>" + "\n")
            # end of preamble
            for i_row in range(len(material)):
                if material[i_row][1] == "Dielectric":
                    file.write(r'<Material name="' + material[i_row][0] + r'">' + "\n")
                    file.write(r"<Dielectric>" + "\n")
                    file.write(r"<Model>" + "\n")
                    file.write(
                        material[i_row][3]
                        + " "
                        + material[i_row][4]
                        + " "
                        + material[i_row][5]
                        + " "
                        + "\n"
                    )
                    file.write(r"</Model>" + "\n")
                    file.write(r"</Dielectric>" + "\n")
                    file.write(r"</Material>" + "\n")

                elif material[i_row][1] == "Metal":
                    file.write(r'<Material name="' + material[i_row][0] + r'">' + "\n")
                    file.write(r"<Metal>" + "\n")
                    file.write(r"<Model>" + "\n")
                    file.write("20 " + material[i_row][2] + "\n")
                    file.write(r"</Model>" + "\n")
                    file.write(r"</Metal>" + "\n")
                    file.write(r"</Material>" + "\n")
                else:
                    pass
            file.write(r"</Cadence_Material_Lib>" + "\n")
            # Read the template
            # material_info = self.txtfile_r( \
            #     self.ROOT_DIR+'\\Scripts\\Templates\\tempMaterial.cmx')
            # # Find and replace a pattern
            # material_info = material_info.replace('ADD_MATERIAL', material_lines)
            # # Export the .cmx material lib file
            # self.txtfile_w(self.SIMBRD_PATH+'Material.cmx', material_info)
            # self.__logger('Material.cmx is created!')

        print("material.cmx is created successfully.")
        return material_file_path
    except FileExistsError as e:
        print(f"An error occurred: {str(e)}")


def create_stackup(sim_run_folder_path, stackup, stackup_name="StackUp.csv"):
    """Create a stackup file based on input."""
    # sim_run_folder_path=sim_info.sim_run_folder_path
    # stackup=sim_info.stackup
    # msg_box_display_logs=sim_info.msg_box_display_logs

    rows = len(stackup)
    contents = ""
    for row_i in range(rows):
        contents = contents + ",".join(stackup[row_i]) + "\n"
    # Create a csv file to store the stackup info
    stackup_file_path = os.path.join(sim_run_folder_path, stackup_name)
    try:
        # Open the file in write mode ('w')
        with open(stackup_file_path, "w", encoding='utf-8') as file:
            # Write each line with a newline character
            for line in contents:
                file.write(line)
        print("StackUp.csv is created successfully.")
        return stackup_file_path
    except RuntimeError as e:
        print(f"An error occurred: {str(e)}")


def generate_dns_list(
    sim_run_folder_path, brd_file_path, extracta_path, DNS_filter_list
):
    """generated DNS list"""
    retain_list = [item.strip() for item in DNS_filter_list.split(",")]

    brd_path = brd_file_path
    brd_name = os.path.basename(brd_path).split(".")[0]
    dnscsv_path = os.path.join(sim_run_folder_path, brd_name + "_DNS.csv")

    # wd = os.path.dirname(dnscsv_path)
    # os.chdir(wd)

    dns_config_path = os.path.join(sim_run_folder_path, "BOM_config.txt")
    with open(dns_config_path, "w", encoding='utf-8') as f:
        f.write("COMPONENT\n")
        f.write(r"BOM_IGNORE !=''" + "\n")
        f.write("REFDES\n")
        f.write("END\n")

    temp_dns_file_path = os.path.join(sim_run_folder_path, "tempfile.txt")

    args = [
        extracta_path,
        "-c",
        brd_path,
        "-c",
        dns_config_path,
        "-c",
        temp_dns_file_path,
    ]
    process = subprocess.Popen(
        args
    )  # execute extracta.exe to generate a temp DNS list file
    process.wait()
    with open(temp_dns_file_path, "r", encoding='utf-8') as f:
        data = f.readlines()
        data = data[2:]  # remove the first two lines in the temp file

    with open(dnscsv_path, "w", encoding='utf-8') as g:
        g.truncate(0)  # empty the file first
        # write DNS compoenents to each line
        for line in data:
            result = line.split("!")
            refdes = result[1]
            for retain_pattern in retain_list:
                if re.match(retain_pattern.replace("*", ".*"), refdes):
                    print(f"Matched: {refdes} against {retain_pattern}")
                    g.write(refdes + ";")

        print(f"{dnscsv_path} is generated!")
    try:
        os.remove(temp_dns_file_path)
    except FileExistsError as e:
        print(f"Error removing tempDNS file: {str(e)}")
    try:
        # files = glob.glob(os.path.join(wd, 'extract.log*'))
        files = glob.glob("extract.log*")
        for file in files:
            os.remove(file)
    except FileExistsError as e:
        print(f"Error removing extract.log file: {str(e)}")
    try:
        # shutil.rmtree(os.path.join(wd,'signoise.run'))
        shutil.rmtree("signoise.run")
    except FileExistsError as e:
        print(f"Error removing signoise.run folder: {str(e)}")

    return dnscsv_path


def read_sim_options(simulation_option, input_info):
    """read input jason file for settings"""
    # simulation_option is single string list separeted by ';', not a dictionary
    sim_run_key_folder_path = input_info["sim_run_key_folder_path"]
    brd_file_path = input_info["brd_file_path"]
    extracta_path = input_info["extracta_path"]
    option_values = {}
    dns_csv_file_path = ''
    option_list = simulation_option.split(";")
    for option in option_list:
        if option:
            option_type = option.split(":")[0].strip()
            if option_type.lower() == "DNS_filter".lower():
                dns_filter_list = option.split(":")[1].strip()
                dns_csv_file_path = generate_dns_list(
                    sim_run_key_folder_path,
                    brd_file_path,
                    extracta_path,
                    dns_filter_list,
                )

            if option_type.lower() == "DNS_CSV".lower():
                dns_csv_file_path = (
                    option.split(":")[1].strip() + ":" + option.split(":")[2].strip()
                )

    if dns_csv_file_path:
        option_values["DNS_csv_file_path"] = dns_csv_file_path

    return option_values
