import os
import csv
from sys import argv

def main():
    # Get directory, files and formats
    run_name = argv[1]
    format_csv = argv[2]
    input_directory = argv[3]
    output_directory = argv[4]
    file_formats = get_file_formats(format_csv)
    # Reformat each csv file
    for file_format in file_formats: 
        # Get filepath to current file
        filename = f"NA12878_{run_name}.dragen.{file_format['filename']}"
        input_filepath = os.path.join(input_directory, filename)
        output_filepath = os.path.join(output_directory, filename)
        # Check if input file exists
        if not os.path.exists(input_filepath):
            print(f"File {input_filepath} does not exist, skipping.")
            continue
        # Check if converted file already exists
        if os.path.exists(output_filepath):
            print(f"File {output_filepath} already exists, skipping.")
            continue
        # Read file into list
        rows = file_to_list(input_filepath)
        # Get header for reformated csv
        field_positions = get_field_positions(file_format["format"])
        fields = [file_format["format"][x] for x in field_positions]
        with open(output_filepath, "w", newline="") as output_csv:
            writer = csv.DictWriter(output_csv, fieldnames=fields)
            writer.writeheader()
            for row in rows:
                values = [
                    row[i] if i < len(row) else "None"
                    for i in field_positions
                ]
                writer.writerow(dict(zip(fields, values)))



def get_file_formats(formats_file):
    file_formats = []
    with open(formats_file) as file:
        while True:
            current_file = {}
            current_file["filename"] = file.readline().strip()
            # Check for EOF
            if not current_file["filename"]:
                break
            current_file["format"] = file.readline().strip().split(",")
            current_file["lines"] = file.readline().strip()
            # Check for missing lines
            if not (current_file["format"] and current_file["lines"]):
                break
            file_formats.append(current_file)
    return file_formats


def file_to_list(filepath):
    rows = []
    with open(filepath) as file:
        reader = csv.reader(file)
        for row in reader:
            rows.append(row)
    return rows


def get_field_positions(format):
    positions = []
    for i in range(len(format)):
        if format[i] != "D":
            positions.append(int(i))
    return positions


if __name__ == "__main__":
    main()