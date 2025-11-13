import os
import csv
from io import StringIO
import pandas as pd

format_csv = os.path.join(os.path.dirname(__file__), "reformat_csv.csv")

def reformat_csv(input_filepath, output_filepath):
    file_format = get_file_format(format_csv, input_filepath)
    if not file_format:
        print(f"No format found for {input_filepath}, skipping.")
        return
    rows = file_to_list(input_filepath)
    field_positions = get_field_positions(file_format["format"])
    fields = [file_format["format"][x] for x in field_positions]
    with open(output_filepath, "w", newline="") as output_csv:
        writer = csv.DictWriter(output_csv, fieldnames=fields)
        writer.writeheader()
        if file_format["lines_count"] == "all":
            rows_to_write = rows
        else:
            begin, end = file_format["lines_count"].split(':')
            rows_to_write = rows[int(begin)-1:int(end)]
        for row in rows_to_write:
            values = [
                row[i] if i < len(row) else "None"
                for i in field_positions
            ]
            writer.writerow(dict(zip(fields, values)))

def get_file_format(formats_file, input_filepath):
    filename = os.path.basename(input_filepath)
    with open(formats_file) as file:
        lines = [line.strip() for line in file if line.strip()]
    for i in range(len(lines)):
        if filename.endswith(lines[i]):
            if i + 2 >= len(lines):
                return {}
            current_file = {
                "filename": filename,
                "format": lines[i+1].split(","),
                "lines_count": lines[i+2]
            }
            if not (current_file["format"] and current_file["lines_count"]):
                return {}
            return current_file
    return {}


def file_to_list(filepath):
    rows = []
    with open(filepath) as file:
        reader = csv.reader(file)
        for row in reader:
            rows.append(row)
    return rows


def get_field_positions(format):
    positions = []
    for i, val in enumerate(format):
        if val != "D":
            positions.append(i)
    return positions


def summary_to_csv(input_filepath, output_filepath):
    # Read data from summary.txt
    with open(input_filepath) as file:
        header = file.readline().strip().split()[1:]
        next(file)
        data = file.readline().strip().split()[1:]
    # Write data to summary.csv
    if len(data) == len(header):
        with open(output_filepath, "w", newline="") as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow(["Parameter", "Value"])
            for i in range(len(header)):
                csv_writer.writerow([header[i], data[i]])
                
def parse_summary(input_filepath):
    """
    Parse the summary file and return a dictionary of metrics.
    """
    with open(input_filepath, newline='') as file:
        reader = csv.DictReader(file, delimiter=',')
        for row in reader:
            if row.get("Type") == "SNP" and row.get("Filter") == "ALL":
                return row
    return None

def read_metrics_csv(path_metrics: str) -> pd.Series:
    """
    Lit un fichier *_sv_metrics.csv (colonnes 'parameter', 'value', 'percentage')
    et renvoie une Series indexée par 'parameter' contenant les valeurs numériques de 'value'.

    :param path_metrics: Chemin vers le fichier CSV des metrics
    :return: pd.Series indexée sur les paramètres avec type numérique
    """
    df = pd.read_csv(path_metrics)

    # Cas standard : colonnes 'parameter' et 'value'
    if 'parameter' in df.columns and 'value' in df.columns:
        series = df.set_index('parameter')['value']
    else:
        # Fallback générique : première colonne → index, deuxième colonne → valeurs
        idx_col, val_col = df.columns[0], df.columns[1]
        series = df.set_index(idx_col)[val_col]

    # Conversion en numérique : les valeurs impossibles deviennent NaN
    series = pd.to_numeric(series, errors='coerce')
    return series