import os

data_folder = os.path.expanduser("~/dev/wgs/data/rtg_processed/")
LibRep = [(1, 1), (1, 2), (1, 3), (2, 1), (3, 1), (5, 1)]
parameters = ["True-pos-baseline",
              "True-pos-call",
              "False-pos",
              "False-neg",
              "Precision",
              "Sensitivity",
              "F-measure"
]

def main():
    # Initialize data dict
    data_sum = dict()
    for parameter in parameters:
        data_sum[parameter] = 0
    # Iterate through each file
    for lr in LibRep:
        summary = get_data(data_folder + f"lib{lr[0]}rep{lr[1]}/summary.txt")
        for param, val in summary.items():
            data_sum[param] += val
    # Compute averages
    n = len(LibRep)
    averages = [data_sum[param] / n for param in parameters]
    # Output to file
    output_path = os.path.join(data_folder, "eval_avg.txt")
    with open(output_path, "w") as f:
        # First row: parameter names
        f.write("".join(f"{p:<20}" for p in parameters) + "\n")
        # Separator row
        f.write("".join("-" * 20 for _ in parameters) + "\n")
        # Second row: average values
        float_params = {"Precision", "Sensitivity", "F-measure"}
        for param, value in zip(parameters, averages):
            if param in float_params:
                f.write(f"{value:<20.4f}")
            else:
                f.write(f"{round(value):<20}")
        f.write("\n")


        
def get_data(path):
    with open(path) as summary_file:
        # Skip first three lines, read data from None line
        for i in range(2):
            next(summary_file)
        values = summary_file.readline().strip().split()[1:]
        # Link values to parameters
        data = dict(zip(parameters, map(float, values)))
        return data


if __name__ == "__main__":
    main()