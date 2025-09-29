from fastapi import APIRouter, HTTPException
import os
import pandas as pd
import numpy as np
from enum import Enum

from dash_app.config import PROCESSED_DIR, LAB_RUNS_DIR, FILE_TYPES
from api.tasks.parsers import read_metrics_csv
from api.app.api_v1.endpoints.happy_metrics import get_happy_metrics


class FileTypeEnum(str, Enum):
    Summary              = "Summary"
    Metrics              = "Metrics"
    VC_metrics           = "VC_metrics"
    CNV_metrics          = "CNV_metrics"
    ROH_metrics          = "ROH_metrics"
    HeThom               = "HeThom"
    Ploidy               = "Ploidy"
    bed_coverage         = "bed_coverage"
    WGS_contig_mean_cov  = "WGS_contig_mean_cov"
    mapping_metrics      = "mapping_metrics"

router = APIRouter()

# FILES --------------------------------------------------------------------------------------------


@router.get(
    "/file-types",
    summary="Liste des types de fichiers disponibles"
)
async def get_file_types():
    return {"file_types": [ft.value for ft in FileTypeEnum]}


@router.get(
    "/samples/{file_type}",
    summary="Liste des échantillons dispos pour un type donné"
)
async def get_samples(file_type: FileTypeEnum):
    suffix = FILE_TYPES[file_type.value].lower()
    base = suffix[:-4] if suffix.lower().endswith(".csv") else suffix

    if not os.path.isdir(PROCESSED_DIR):
        raise HTTPException(status_code=500, detail="Dossier de données introuvable")

    samples = []
    for run in PROCESSED_DIR.iterdir():
        if not run.is_dir():
            continue
        for file in run.iterdir():
            if suffix in file.name.lower():
                name = run.name.split('_', 1)[1]
                samples.append(name)
                break

    if not samples:
        raise HTTPException(
            status_code=404,
            detail=f"Aucun échantillon trouvé pour le type '{file_type.value}'"
        )

    return {"samples": sorted(samples)}


@router.get(
    "/data/{file_type}",
    summary="Renvoie les données JSON pour un type de fichier"
)
async def get_data(file_type: FileTypeEnum):
    # 1) récupérer la liste des samples
    samples_response = await get_samples(file_type)
    samples = samples_response["samples"]
    suffix = FILE_TYPES[file_type.value]
    base = suffix[:-4] if suffix.lower().endswith(".csv") else suffix
    data = {}

    # Find each run directory with prefixed date
    for run in samples:
        # Find the run directory with unknown prefixed date
        run_pattern = f"*_{run}"
        matching_dirs = list(PROCESSED_DIR.glob(run_pattern))
        if not matching_dirs:
            raise HTTPException(
                status_code=404,
                detail=f"No directory found for run '{run}'"
            )
        run_dir = matching_dirs[0]
        matches = [
            f.name for f in run_dir.iterdir()
            if suffix in f.name.lower()
        ]
        if len(matches) == 0:
            continue
        file_path = run_dir / matches[0]

        try:
            if suffix.endswith("_metrics.csv"):
                series = read_metrics_csv(file_path)
            else:
                #TODO
                df_or_series = get_happy_metrics(run)
                df_or_series = df_or_series.model_dump()
                if isinstance(df_or_series, pd.DataFrame):
                    series = df_or_series.set_index("Parameter")["Value"]
                else:
                    series = df_or_series
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Erreur de parsing pour '{file_path}': {e}"
            )

        data[run] = series

    # 3) fusion en DataFrame
    df = pd.DataFrame(data)

    # 4) nettoyer les valeurs non-JSON (inf, -inf, NaN)
    df = df.replace([np.inf, -np.inf], None)
    df = df.where(pd.notnull(df), None)
    

    # 5) construire manuellement la liste des valeurs
    cleaned_values = []
    for row in df.values.tolist():
        cleaned_row = [
            None if (isinstance(v, float) and (pd.isna(v) or v in [np.inf, -np.inf]))
            else v
            for v in row
        ]
        cleaned_values.append(cleaned_row)

    return {
        "data": {
            "metrics": df.index.tolist(),
            "samples": df.columns.tolist(),
            "values": cleaned_values
        }
    }
