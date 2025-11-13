import os
import csv
from sys import argv


def main():
    #Get filepaths
    filepath = argv[1]
    summary_txt = os.path.join(filepath, "summary.txt")
    summary_csv = os.path.join(filepath, "summary.csv")
    # Read data from summary.txt
    with open(summary_txt) as file:
        header = file.readline().strip().split()[1:]
        next(file)
        data = file.readline().strip().split()[1:]
    # Write data to summary.csv
    if len(data) == len(header):
        with open(summary_csv, "w", newline="") as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow(["Parameter", "Value"])
            for i in range(len(header)):
                csv_writer.writerow([header[i], data[i]])


if __name__ == "__main__":
    main()