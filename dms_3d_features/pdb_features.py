import glob
import numpy as np
import pandas as pd
import os
from typing import List, Dict, Tuple, Optional
import subprocess
import shutil
import glob
import regex as re

from dms_3d_features.logger import get_logger

log = get_logger("pdb-features")


# dssr features #####################################################################


def calculate_structural_parameters_with_dssr(pdb_dir: str) -> None:
    """
    Calculate structural parameters for PDB structures using DSSR.

    This function processes all PDB files in the specified directory and
    subdirectories. For each PDB file, it creates a corresponding directory,
    moves the PDB file into this directory, and runs DSSR to calculate
    structural parameters. The results are stored in output files named after
    the original PDB file, with an additional extension '.out'. All output
    files are moved to 'data/dssr-output'.

    Args:
        pdb_dir (str): The directory containing the PDB files.

    Returns:
        None
    """
    output_base_dir = os.path.join("data", "dssr-output")
    os.makedirs(output_base_dir, exist_ok=True)
    pdb_paths = glob.glob(f"{pdb_dir}/*/*.pdb")
    log.info(f"Found {len(pdb_paths)} PDB files in {pdb_dir}")
    for pdb_path in pdb_paths:
        log.info(f"running dssr on: {pdb_path}")
        pdb_filename = os.path.basename(pdb_path)
        subprocess.call(
            [
                "x3dna-dssr",
                f"-i={pdb_path}",
                f"-o={output_base_dir}/{pdb_filename[:-4]}.out",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        torsion_file_src = "dssr-torsions.txt"
        torsion_file_dst = os.path.join(
            output_base_dir, f"{pdb_filename[:-4]}_torsions.txt"
        )
        shutil.move(torsion_file_src, torsion_file_dst)
        for temp_file in glob.glob(f"dssr-*"):
            os.remove(temp_file)


class DSSRTorsionFileProcessor:
    """
    A class to process DSSR torsion files and extract structural data.

    Attributes:
        output_dir (str): The directory to store the output files. Defaults to
                          'dssr-output' in the given pdb_dir if not provided.
    """

    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize the DSSRTorsionFileProcessor with specified directories.
        """
        self.output_dir = (
            output_dir if output_dir else os.path.join("data", "dssr-output")
        )
        os.makedirs(self.output_dir, exist_ok=True)

    def process_file(
        self, dssr_torsion_file: str, name: str, motif: str
    ) -> pd.DataFrame:
        """
        Process a DSSR torsion file to extract structural data.

        Args:
            dssr_torsion_file (str): The path to the DSSR torsion file.
            name (str): The name identifier for the data.
            motif (str): The motif identifier for the data.

        Returns:
            pd.DataFrame: A DataFrame containing the extracted structural data.
        """
        lines = self.__read_file_lines(dssr_torsion_file)
        start_indices = self.__find_start_indices(lines)

        column_headers = self.__get_column_headers()
        col_ranges = self.__get_column_ranges()

        all_data = []
        for i in range(len(motif) - 1):
            row_data = self.__extract_row_data(lines, col_ranges, start_indices, i)
            data = [name, motif] + row_data
            all_data.append(data)

        return pd.DataFrame(all_data, columns=column_headers)

    # Helper functions ##############################################################
    def __extract_substrings(
        self, lines: List[str], indices: Dict[str, Tuple[int, int]], offset: int
    ) -> List[str]:
        """
        Extract substrings from lines based on given indices.

        Args:
            lines (List[str]): The list of lines from the file.
            indices (Dict[str, Tuple[int, int]]): A dictionary mapping keys to
                tuples indicating the start and end indices for substring extraction.
            offset (int): The offset line index for data extraction.

        Returns:
            List[str]: Extracted substrings from the specified line.
        """
        data = []
        for _, (col_start, col_end) in indices.items():
            if offset < len(lines):
                line = lines[offset].strip()
                data.append(line[col_start:col_end].strip())
            else:
                data.append("")  # Append an empty string if offset is out of range
        return data

    def __read_file_lines(self, file_path: str) -> List[str]:
        """
        Read all lines from a file.

        Args:
            file_path (str): The path to the file to be read.

        Returns:
            List[str]: A list of lines read from the file.
        """
        try:
            with open(file_path, "r") as f:
                return f.readlines()
        except FileNotFoundError as e:
            log.error(f"File not found: {file_path}")
            return []

    def __find_start_indices(self, lines: List[str]) -> Dict[str, int]:
        """
        Find the starting indices for various data sections in the lines.

        Args:
            lines (List[str]): The list of lines from the file.

        Returns:
            Dict[str, int]: A dictionary mapping section names to their start indices.
        """
        start_indices = {"alpha": -1, "eta": -1, "puckering": -1, "bin": -1}
        for idx, line in enumerate(lines):
            if "nt" in line:
                if "alpha" in line:
                    start_indices["alpha"] = idx + 1
                elif "eta" in line:
                    start_indices["eta"] = idx + 1
                elif "v0" in line:
                    start_indices["puckering"] = idx + 1
                elif "bin" in line:
                    start_indices["bin"] = idx + 1
        if all(v == -1 for v in start_indices.values()):
            log.warning("Not all data sections found in the file.")
        return start_indices

    def __get_column_headers(self) -> List[str]:
        """
        Get the column headers for the DataFrame.

        Returns:
            List[str]: A list of column headers.
        """
        return [
            "pdb_name",
            "m_sequence",
            "r_loc_pos",
            "r_nuc",
            "alpha",
            "beta",
            "gamma",
            "delta",
            "epsilon",
            "zeta",
            "e-z",
            "chi",
            "phase-angle",
            "sugar-type",
            "sszp",
            "dp",
            "splay",
            "eta",
            "theta",
            "eta_1",
            "theta_1",
            "eta_2",
            "theta_2",
            "v0",
            "v1",
            "v2",
            "v3",
            "v4",
            "tm",
            "p",
            "puckering",
            "bin",
            "cluster",
            "suitness",
        ]

    def __get_column_ranges(self) -> Dict[str, Dict[str, Tuple[int, int]]]:
        """
        Get the column ranges for data extraction.

        Returns:
            Dict[str, Dict[str, Tuple[int, int]]]: A dictionary mapping section
            names to their corresponding column range mappings.
        """
        return {
            "alpha": {
                "nt": (8, 9),
                "alpha": (26, 32),
                "beta": (33, 40),
                "gamma": (42, 48),
                "delta": (51, 56),
                "epsilon": (57, 65),
                "zeta": (66, 73),
                "e_z": (75, 83),
                "chi": (85, 98),
                "phase": (101, 116),
                "sugar": (117, 127),
                "ssZp": (130, 135),
                "Dp": (138, 143),
                "splay": (145, 151),
            },
            "eta": {
                "eta": (25, 33),
                "theta": (33, 41),
                "eta_1": (41, 48),
                "theta_1": (49, 56),
                "eta_2": (57, 64),
                "theta_2": (65, 73),
            },
            "puckering": {
                "v0": (27, 33),
                "v1": (34, 41),
                "v2": (43, 49),
                "v3": (50, 57),
                "v4": (59, 64),
                "tm": (67, 72),
                "P": (75, 80),
                "Puck": (81, 90),
            },
            "bin": {"bin": (24, 31), "clus": (33, 38), "suit": (42, 53)},
        }

    def __extract_row_data(
        self,
        lines: List[str],
        col_ranges: Dict[str, Dict[str, Tuple[int, int]]],
        start_indices: Dict[str, int],
        offset: int,
    ) -> List[str]:
        """
        Extract row data for a specific offset.

        Args:
            lines (List[str]): The list of lines from the file.
            col_ranges (Dict[str, Dict[str, Tuple[int, int]]]): The column range mappings.
            start_indices (Dict[str, int]): The starting indices for each section.
            offset (int): The row offset for data extraction.

        Returns:
            List[str]: Extracted data for the specified row.
        """
        data_alpha = self.__extract_substrings(
            lines, col_ranges["alpha"], start_indices["alpha"] + offset
        )
        data_eta = self.__extract_substrings(
            lines, col_ranges["eta"], start_indices["eta"] + offset
        )
        data_puckering = self.__extract_substrings(
            lines, col_ranges["puckering"], start_indices["puckering"] + offset
        )
        data_bin = self.__extract_substrings(
            lines, col_ranges["bin"], start_indices["bin"] + offset
        )
        nt_num = self.__extract_substrings(
            lines, {"nt_num": (9, 11)}, start_indices["alpha"] + offset
        )
        return nt_num + data_alpha + data_eta + data_puckering + data_bin


def get_all_torsional_parameters_from_dssr(pdb_dir: str) -> pd.DataFrame:
    """
    Extract all torsional parameters from DSSR files in the given directory.

    This function iterates through all PDB files in the specified directory and
    processes the corresponding DSSR torsion files to extract structural parameters.

    Args:
        pdb_dir (str): The directory containing the PDB files.

    Returns:
        pd.DataFrame: A concatenated DataFrame containing torsional parameters
                      for all processed PDB files.
    """
    pdb_paths = sorted(glob.glob(f"{pdb_dir}/*/*.pdb"))
    dfs = []
    for pdb_path in pdb_paths:
        base_name = os.path.basename(pdb_path)[:-4]
        motif = os.path.basename(os.path.dirname(pdb_path)).replace("_", "&")
        log.info(f"Processing file: data/dssr-output/{base_name}_torsions.txt")

        torsion_file_path = f"data/dssr-output/{base_name}_torsions.txt"
        if os.path.exists(torsion_file_path):
            processor = DSSRTorsionFileProcessor()
            df = processor.process_file(torsion_file_path, base_name, motif)
            dfs.append(df)
        else:
            log.warning(f"Torsion file not found: {torsion_file_path}")

    if dfs:
        return pd.concat(dfs, ignore_index=True)
    else:
        log.error("No data was processed. Check for missing files or errors.")
        return pd.DataFrame()  # Return an empty DataFrame if no data was processed


# base pair level features #######################################################


def check_command_accessibility(command: str) -> None:
    """
    Check if a command is accessible in the system PATH.

    Args:
        command (str): The command to check.

    Raises:
        RuntimeError: If the command is not accessible or not found.
    """
    try:
        result = subprocess.run(
            ["which", command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        if not result.stdout.strip():
            raise RuntimeError(f"{command} not found in PATH")
    except subprocess.CalledProcessError:
        raise RuntimeError(
            f"{command} is not accessible. Please ensure 3DNA tools are properly installed and in your PATH."
        )


def generate_basepair_details_from_3dna(pdb: str, output_dir: str = None) -> None:
    """
    Generate base-pair details from a given PDB file using 3DNA tools.

    This function uses the 3DNA tools 'find_pair' and 'analyze' to generate base-pair
    details for the given PDB file. The output is saved with the same name as the PDB
    file but with an '.out' extension.

    Args:
        pdb (str): Path to the PDB file.
        output_dir (str): Path to the output directory. Defaults to None.
    """
    if output_dir is None:
        output_dir = os.path.dirname(pdb)

    # Check if required 3DNA tools are accessible
    check_command_accessibility("find_pair")
    check_command_accessibility("analyze")

    pdbname = os.path.basename(pdb)
    subprocess.call(
        f"find_pair {pdb} {pdb[:-4]}.inp",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.call(
        f"analyze {pdb[:-4]}.inp",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    shutil.move(f"{pdbname[:-4]}.out", f"{output_dir}/{pdbname[:-4]}_x3dna.out")
    remove_files = [
        "auxiliary.par",
        "bestpairs.pdb",
        "bp_helical.par",
        "bp_order.dat",
        "bp_step.par",
        "cf_7methods.par",
        "col_chains.scr",
        "col_helices.scr",
        "hel_regions.pdb",
        "ref_frames.dat",
        "stacking.pdb",
        "hstacking.pdb",
    ]
    for file in remove_files:
        os.remove(file)


def extract_bp_type_and_res_num_into_a_table(filename: str) -> list:
    """
    Extract base-pair type and residue numbers from the 3DNA output file.

    This function parses the 3DNA output file to extract the base-pair type (WC or NON-WC)
    and residue numbers for the base pairs.

    Args:
        filename (str): Path to the 3DNA output file.

    Returns:
        list: A list containing three lists: base-pair types, residue numbers for the first base,
              and residue numbers for the second base.
    """
    pattern = re.compile(
        r"\s*(\d*)\s*\((.*?)\)\s+.*?(\d+)_:\[\.\.(.)\](.)[-A-Z\*\+\-]+[A-Z]+\[\.\.(.)\]:\.*(\d+)_:-<.*?\((.*?)\)"
    )

    bp_types = []
    res_nums1 = []
    res_nums2 = []

    with open(filename, "r") as file:
        lines = file.readlines()

        for line in lines:
            match = pattern.search(line)
            if match:
                res_num1 = match.group(3)
                res_num2 = match.group(7)
                bp_type = "WC" if "-----" in line else "NON-WC"

                res_nums1.append(res_num1)
                res_nums2.append(res_num2)
                bp_types.append(bp_type)

    return bp_types, res_nums1, res_nums2


def extract_basepair_details_into_a_table(filename: str) -> pd.DataFrame:
    """
    Extract base-pair details from the 3DNA output file and save them into a DataFrame.

    This function reads the 3DNA output file, extracts the base-pair parameters, and
    saves them into a pandas DataFrame.

    Args:
        filename (str): Path to the 3DNA output file.

    Returns:
        pd.DataFrame: DataFrame containing the extracted base-pair parameters.
    """
    pattern = re.compile(
        r"\s*(\d*)\s*([A-Z]\+[A-Z]|[A-Z]-[A-Z])\s+([-]?\d+\.\d+)\s+([-]?\d+\.\d+)\s+"
        r"([-]?\d+\.\d+)\s+([-]?\d+\.\d+)\s+([-]?\d+\.\d+)\s+([-]?\d+\.\d+)"
    )

    # Extract base-pair types and residue numbers from a separate function
    bp_types, res_nums1, res_nums2 = extract_bp_type_and_res_num_into_a_table(filename)

    # Read file content
    with open(filename, "r") as file:
        lines = file.readlines()

    # Initialize variables
    is_shear_table = False
    motif_index = None
    all_data = []
    j = 0

    # Process each line
    for i, line in enumerate(lines):
        if "Shear    Stretch   Stagger    Buckle  Propeller  Opening" in line:
            is_shear_table = True
            continue

        if line.startswith("File name:"):
            motif_index = i

        if not is_shear_table:
            continue

        match = pattern.search(line)
        if not match:
            break

        motif = lines[motif_index].split("/")[2]
        bp = re.split(r"[-+]", match.group(2))[0] + re.split(r"[-+]", match.group(2))[1]

        data = {
            "name": os.path.basename(filename),
            "motif": motif,
            "r_type": bp_types[j],
            "res_num1": res_nums1[j],
            "res_num2": res_nums2[j],
            "bp": bp,
            "shear": float(match.group(3)),
            "stretch": float(match.group(4)),
            "stagger": float(match.group(5)),
            "buckle": float(match.group(6)),
            "propeller": float(match.group(7)),
            "opening": float(match.group(8)),
        }
        all_data.append(data)
        j += 1

    return pd.DataFrame(all_data)


def kabsch_algorithm(P: list, Q: list) -> list:
    """
    Perform the Kabsch algorithm to find the optimal rotation matrix
    that aligns matrix P to matrix Q.

    Args:
    P (list): A list of coordinates representing the first structure.
    Q (list): A list of coordinates representing the second structure.

    Returns:
    list: The optimal rotation matrix that aligns P to Q.
    """
    P_centered = P - np.mean(P, axis=0)
    Q_centered = Q - np.mean(Q, axis=0)

    C = np.dot(np.transpose(P_centered), Q_centered)

    V, S, W = np.linalg.svd(C)

    d = (np.linalg.det(V) * np.linalg.det(W)) < 0.0
    if d:
        S[-1] = -S[-1]
        V[:, -1] = -V[:, -1]

    U = np.dot(V, W)

    return U


def superimpose_structures(mobile_coords: list, target_coords: list) -> list:
    """
    Superimpose the mobile structure onto the target structure using the Kabsch algorithm.

    Args:
    mobile_coords (list): A list of coordinates for the mobile structure.
    target_coords (list): A list of coordinates for the target structure.

    Returns:
    list: The rotated mobile coordinates that best align with the target structure.
    """
    rotation_matrix = kabsch_algorithm(mobile_coords, target_coords)
    mobile_center = np.mean(mobile_coords, axis=0)
    target_center = np.mean(target_coords, axis=0)

    mobile_coords_aligned = (
        np.dot(mobile_coords - mobile_center, rotation_matrix) + target_center
    )

    return mobile_coords_aligned


def rmsd_calculation_for_bp(
    allowed_atoms: dict,
    bp: str,
    ideal_df: pd.DataFrame,
    selected_pdb_df: pd.DataFrame,
    resi_nums: list,
) -> float:
    """
    Calculate the RMSD (Root Mean Square Deviation) for a base pair.

    Args:
    allowed_atoms (dict): Dictionary of allowed atom names for each base type.
    bp (str): The base pair (e.g., "AU", "GC").
    ideal_df (pd.DataFrame): DataFrame containing the ideal structure coordinates.
    selected_pdb_df (pd.DataFrame): DataFrame containing the selected structure's coordinates.
    resi_nums (list): List of residue numbers for the base pair in the selected structure.

    Returns:
    float: The RMSD value between the ideal and selected structures. Returns None if calculation is not possible.
    """
    total_rmsd = 0
    count = 0

    ideal_coords_list = []
    pdb_code_list = []

    for atom in allowed_atoms[bp[0]]:
        atom_ideal_df = ideal_df[
            (ideal_df["residue_number"] == 1) & (ideal_df["atom_name"] == atom)
        ]
        atom_selected_pdb_df = selected_pdb_df[
            (selected_pdb_df["residue_number"] == resi_nums[0])
            & (selected_pdb_df["atom_name"] == atom)
        ]

        if not atom_ideal_df.empty and not atom_selected_pdb_df.empty:
            ideal_coords_list.append(
                atom_ideal_df[["x_coord", "y_coord", "z_coord"]].values[0]
            )
            pdb_code_list.append(
                atom_selected_pdb_df[["x_coord", "y_coord", "z_coord"]].values[0]
            )

    for atom in allowed_atoms[bp[1]]:
        atom_ideal_df = ideal_df[
            (ideal_df["residue_number"] == 2) & (ideal_df["atom_name"] == atom)
        ]
        atom_selected_pdb_df = selected_pdb_df[
            (selected_pdb_df["residue_number"] == resi_nums[1])
            & (selected_pdb_df["atom_name"] == atom)
        ]

        if not atom_ideal_df.empty and not atom_selected_pdb_df.empty:
            ideal_coords_list.append(
                atom_ideal_df[["x_coord", "y_coord", "z_coord"]].values[0]
            )
            pdb_code_list.append(
                atom_selected_pdb_df[["x_coord", "y_coord", "z_coord"]].values[0]
            )

    if ideal_coords_list and pdb_code_list:
        ideal_coords = np.array(ideal_coords_list)
        selected_coords = np.array(pdb_code_list)

        aligned_selected_coords = superimpose_structures(selected_coords, ideal_coords)

        total_rmsd = np.sum((ideal_coords - aligned_selected_coords) ** 2)
        count = len(ideal_coords)

        if count > 0:
            rmsd_result = np.sqrt(total_rmsd / count)
            return rmsd_result
        else:
            return None
    else:
        return None


def calculate_rmsd_bp(bp: str, filename: str, resi_nums: list) -> float:
    """
    Calculate the RMSD for a given base pair in a PDB structure.
    """
    allowed_atoms = {
        "A": ["N1", "C2", "N3", "C4", "C5", "C6", "N6", "N7", "C8", "N9"],
        "G": ["N1", "C2", "N2", "N3", "C4", "C5", "C6", "O6", "N7", "C8", "N9"],
        "C": ["N1", "C2", "O2", "N3", "C4", "N4", "C5", "C6"],
        "U": ["N1", "C2", "O2", "N3", "C4", "O4", "C5", "C6"],
    }

    try:
        ppdb_ideal = PandasPdb().read_pdb(f"{RESOURCE_PATH}/ideal_pdbs/{bp}.pdb")
        ideal_df = ppdb_ideal.df["ATOM"]
        ppdb_pdb = PandasPdb().read_pdb(filename)
        pdb_df = ppdb_pdb.df["ATOM"]
        selected_pdb_df = pdb_df[pdb_df["residue_number"].isin(resi_nums)]

        if selected_pdb_df.empty:
            print(
                f"Warning: Selected PDB DataFrame is empty for {bp} at residues {resi_nums}"
            )

        rmsd_value = rmsd_calculation_for_bp(
            allowed_atoms, bp, ideal_df, selected_pdb_df, resi_nums
        )

        if rmsd_value is None:
            print(f"RMSD could not be calculated for {bp} at residues {resi_nums}")
        return rmsd_value

    except Exception as e:
        print(f"Error calculating RMSD for {bp} in {filename}: {e}")
        return None


def process_basepair_details():
    pdb_paths = sorted(glob.glob(f"{DATA_PATH}/pdbs/*/*.pdb"))
    output_dir = f"{DATA_PATH}/dssr-output/"

    all_tables = []
    for pdb_path in pdb_paths:
        pdb_name = os.path.basename(pdb_path)[:-4]
        x3dna_out_path = f"{output_dir}/{pdb_name}_x3dna.out"
        if not os.path.exists(x3dna_out_path):
            log.info(f"Generating basepair details for {pdb_name}")
            generate_basepair_details_from_3dna(pdb_path, output_dir)
        extracted_table = extract_basepair_details_into_a_table(x3dna_out_path)
        if not extracted_table.empty:
            all_tables.append(extracted_table)

    combined_df = pd.concat(all_tables, ignore_index=True)
    combined_df.to_csv(f"{RESOURCE_PATH}/csvs/all_bp_details.csv", index=False)
    filtered_df = combined_df[combined_df["r_type"] == "WC"].copy()

    rmsd = []
    for i, row in filtered_df.iterrows():
        res_num1 = int(row["res_num1"])
        res_num2 = int(row["res_num2"])

        pdb_path = f"{DATA_PATH}/pdbs/{row['motif']}/{row['name'][:-10]}.pdb"
        rmsd_val = calculate_rmsd_bp(row["bp"], pdb_path, [res_num1, res_num2])

        if rmsd_val is not None:
            print(
                f"RMSD for {row['bp']} at residues {res_num1}, {res_num2}: {rmsd_val}"
            )
        rmsd.append(rmsd_val)

    filtered_df["rmsd"] = rmsd
    filtered_df.to_csv(f"{RESOURCE_PATH}/csvs/wc_with_rmsd.csv", index=False)
    df_all = pd.read_json(f"{DATA_PATH}/raw-jsons/residues/pdb_library_1_residues.json")

    dms_dict = {}
    for k, all_row in df_all.iterrows():
        key = (all_row["m_sequence"], all_row["r_nuc"], all_row["pdb_r_pos"])
        if key not in dms_dict:
            dms_dict[key] = all_row["r_data"]
        else:
            if isinstance(dms_dict[key], list):
                dms_dict[key].append(all_row["r_data"])
            else:
                dms_dict[key] = [dms_dict[key], all_row["r_data"]]

    all_data = []
    for j, row1 in filtered_df.iterrows():
        key1 = (row1["motif"].replace("_", "&"), row1["bp"][0], int(row1["res_num1"]))
        key2 = (row1["motif"].replace("_", "&"), row1["bp"][1], int(row1["res_num2"]))

        r_data_list = []
        if key1 in dms_dict:
            r_data_list = dms_dict.get(key1, ["None"])
        elif key2 in dms_dict:
            r_data_list = dms_dict.get(key2, ["None"])
        else:
            print(f"No match found for {key1} or {key2}, skipping...")
            continue
        strand_1_length = len(row1["motif"].split("_")[0])

        if (int(row1["res_num1"]) == 3 or int(row1["res_num2"]) == 3) and (
            int(row1["res_num1"]) == (len(row1["motif"]) + 5)
            or int(row1["res_num2"]) == (len(row1["motif"]) + 5)
        ):
            flanking_pair = "YES"
        elif (
            int(row1["res_num1"]) == (strand_1_length + 2)
            or int(row1["res_num2"]) == (strand_1_length + 2)
        ) and (
            int(row1["res_num1"]) == (strand_1_length + 7)
            or int(row1["res_num2"]) == (strand_1_length + 7)
        ):
            flanking_pair = "YES"
        else:
            flanking_pair = "NO"

        for r_data in r_data_list:
            data = {
                "m_sequence": row1["motif"].replace("_", "&"),
                "bp": row1["bp"],
                "pdb_r_pos1": row1["res_num1"],
                "pdb_r_pos2": row1["res_num2"],
                "rmsd_from_ideal": row1["rmsd"],
                "shear": row1["shear"],
                "stretch": row1["stretch"],
                "stagger": row1["stagger"],
                "buckle": row1["buckle"],
                "propeller": row1["propeller"],
                "opening": row1["opening"],
                "r_data": r_data,
                "flanking_pairs": flanking_pair,
            }
            all_data.append(data)

    df_fin = pd.DataFrame(all_data)
    df_fin.to_json(f"{RESOURCE_PATH}/jsons/wc_details.json", orient="records")
