import pandas as pd
import requests
import numpy as np
from .config import API_BASE_URL

# URL complète vers l'API FastAPI exposée
API_BASE = f"{API_BASE_URL}/dash"

def list_files(file_type: str) -> list[str]:
    """
    Appelle GET /samples/{file_type} et renvoie la liste des échantillons.
    """
    url = f"{API_BASE}/samples/{file_type}"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        return resp.json().get("samples", [])
    except Exception as e:
        print(f"[ERREUR] Impossible de récupérer les échantillons : {e}")
        return []


def load_data(file_type: str) -> pd.DataFrame:
    """
    Appelle GET /data/{file_type}, reconstruit et renvoie un DataFrame
    (index=metrics, colonnes=samples), en nettoyant inf/-inf/NaN.
    """
    url = f"{API_BASE}/data/{file_type}"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        payload = resp.json()
        data = payload["data"]  # Access nested data object
        df = pd.DataFrame(
            data["values"],
            index=data["metrics"],
            columns=data["samples"],
        )
        # remplacer inf/-inf par NaN puis laisser Pandas gérer
        df = df.replace([None], np.nan)
        return df
    except Exception as e:
        print(f"[ERREUR] Impossible de charger les données : {e}")
        return pd.DataFrame()
