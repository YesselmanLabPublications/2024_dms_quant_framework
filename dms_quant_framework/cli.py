import click
import warnings
import pandas as pd
import os

from dms_quant_framework.sasa import generate_sasa_dataframe
from dms_quant_framework.pdb_features import (
    process_basepair_details,
    generate_distance_dataframe,
)
from dms_quant_framework.process_motifs import (
    process_mutation_histograms_to_json,
    GenerateMotifDataFrame,
    GenerateResidueDataFrame,
    generate_pdb_residue_dataframe,
)
from dms_quant_framework.logger import setup_logging, get_logger
from dms_quant_framework.paths import DATA_PATH

warnings.filterwarnings(
    "ignore", message="FreeSASA: warning: Found no matches to resn 'A', typo?"
)

log = get_logger("cli")


# cli functions #################################################################


@click.group()
def cli():
    pass


@cli.command()
def generate_motif_data():
    """
    Takes raw mutation histograms from RNA-MaP and generates a JSON file with motif data.
    """
    setup_logging()

    # Check paths exist
    required_paths = [
        f"{DATA_PATH}/raw-jsons/constructs",
        f"{DATA_PATH}/raw-jsons/motifs",
        f"{DATA_PATH}/raw-jsons/residues",
    ]
    for path in required_paths:
        if not os.path.exists(path):
            raise ValueError(f"Required directory {path} does not exist")

    process_mutation_histograms_to_json()
    construct_file = f"{DATA_PATH}/raw-jsons/constructs/pdb_library_1.json"
    df = pd.read_json(construct_file)
    gen = GenerateMotifDataFrame()
    log.info("Generating motif dataframe")
    gen.run(df, "pdb_library_1")
    motif_file = f"{DATA_PATH}/raw-jsons/motifs/pdb_library_1_motifs_avg.json"
    df = pd.read_json(motif_file)
    log.info("Generating residue dataframe")
    gen = GenerateResidueDataFrame()
    gen.run(df, "pdb_library_1")
    residue_file = f"{DATA_PATH}/raw-jsons/residues/pdb_library_1_residues.json"
    df = pd.read_json(residue_file)
    log.info("Generating pdb residue dataframe")
    df = generate_pdb_residue_dataframe(df)
    df.to_json(
        f"{DATA_PATH}/raw-jsons/residues/pdb_library_1_residues_pdb.json",
        orient="records",
    )


@cli.command()
def get_pdb_features():
    """
    Get pdb features for all PDB files in the pdbs directory.
    """
    setup_logging()
    # get all distances for different max distances
    log.info("Getting all distances")
    df = generate_distance_dataframe(max_distance=1000)
    df.to_csv(f"{DATA_PATH}/pdb-features/distances_all.csv", index=False)
    # get all sasa values for different probe radii
    log.info("Getting all sasa values")
    df_sasa = generate_sasa_dataframe()
    df_sasa.to_csv("data/pdb-features/sasa.csv", index=False)
    log.info("Getting basepair details")
    process_basepair_details()


if __name__ == "__main__":
    cli()
