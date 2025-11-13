import glob
import os
import re
import csv

# Get the absolute path to the project root (assumes this script is in wgs/pipeline)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
processed_dir = os.path.join(project_root, "data", "processed")
stats_files = glob.glob(os.path.join(processed_dir, "Lib*_Rep*/Lib*_Rep*_stats.txt"))
output_file = os.path.join(processed_dir, "stat_avg.txt")
csv_output_file = os.path.join(processed_dir, "stat_avg.csv")

# Patterns for extracting numbers (including percentages and ratios)
number_pattern = re.compile(r"([-+]?\d*\.\d+|\d+)")
percent_pattern = re.compile(r"(\d+\.?\d*)%\s+\((\d+)/(\d+)\)")
ratio_pattern = re.compile(r"([-+]?\d*\.\d+|\d+)\s+\((\d+)/(\d+)\)")

# Store all values for each key
stats = {}

for fname in stats_files:
    with open(fname) as f:
        for line in f:
            if ':' not in line:
                continue
            key, val = line.split(':', 1)
            key = key.strip()
            val = val.strip()
            # Handle percentages with counts
            if '%' in val and '(' in val and '/' in val:
                m = percent_pattern.match(val)
                if m:
                    percent, num, denom = map(float, m.groups())
                    stats.setdefault(key, []).append((percent, num, denom))
                continue
            # Handle ratios with counts
            if '(' in val and '/' in val:
                m = ratio_pattern.match(val)
                if m:
                    ratio, num, denom = map(float, m.groups())
                    stats.setdefault(key, []).append((ratio, num, denom))
                continue
            # Handle plain numbers
            m = number_pattern.match(val)
            if m:
                stats.setdefault(key, []).append(float(m.group(1)))
                continue
            # Otherwise, skip (e.g., file paths)
            continue

# Compute averages
averages = {}
for key, values in stats.items():
    # For percentages and ratios with counts, average the numerator and denominator, then recompute
    if isinstance(values[0], tuple):
        avg_percent = sum(v[0] for v in values) / len(values)
        avg_num = sum(v[1] for v in values) / len(values)
        avg_denom = sum(v[2] for v in values) / len(values)
        if '%' in key:
            averages[key] = f"{avg_percent:.2f}% ({int(round(avg_num))}/{int(round(avg_denom))})"
        else:
            # For ratios
            if avg_denom != 0:
                avg_ratio = avg_num / avg_denom
                averages[key] = f"{avg_ratio:.2f} ({int(round(avg_num))}/{int(round(avg_denom))})"
            else:
                averages[key] = f"- ({int(round(avg_num))}/{int(round(avg_denom))})"
    else:
        avg = sum(values) / len(values)
        if avg.is_integer():
            averages[key] = f"{int(avg)}"
        else:
            averages[key] = f"{avg:.2f}"

# Ensure the output directory exists
os.makedirs(processed_dir, exist_ok=True)

# Write output in the same format as the input
with open(output_file, "w") as out:
    for key in sorted(averages.keys()):
        out.write(f"{key:<30}: {averages[key]}\n")

# Write output as CSV
with open(csv_output_file, "w", newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["Metric", "Average"])
    for key in sorted(averages.keys()):
        writer.writerow([key, averages[key]])