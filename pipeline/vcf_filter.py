import os
import subprocess
import csv

PROCESSED_DIR = "../data/processed/"
VARIANT_TYPES = ["snp", "mnp", "ins", "del", "indel", "sym"]
VCFEVAL_FILES = ["tp", "fp", "fn"]

output_path = os.path.join(PROCESSED_DIR, "variant_summary.tsv")
header = ["Sample", "TP", "FP", "FN", "Precision", "Sensitivity", "F1"]

def count_variants_by_type(vcf_path, vtype):
    if not os.path.exists(vcf_path):
        return 0
    # Try to annotate TYPE if missing
    cmd = f'bcftools query -f "%TYPE\\n" {vcf_path} | grep -w "{vtype}" | wc -l'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    try:
        return int(result.stdout.strip())
    except ValueError:
        return 0

with open(output_path, "w", newline="") as outfile:
    writer = csv.writer(outfile, delimiter='\t')
    writer.writerow(header)

    for sample_dir in os.listdir(PROCESSED_DIR):
        full_dir = os.path.join(PROCESSED_DIR, sample_dir)
        if not os.path.isdir(full_dir):
            continue

        sample_name = sample_dir
        total = {"tp": 0, "fp": 0, "fn": 0}

        for eval_type in VCFEVAL_FILES:
            # Try both .vcf.gz and .vcf
            vcf_path_gz = os.path.join(full_dir, f"{eval_type}.vcf.gz")
            vcf_path = os.path.join(full_dir, f"{eval_type}.vcf")
            vcf_file = vcf_path_gz if os.path.exists(vcf_path_gz) else vcf_path if os.path.exists(vcf_path) else None
            if not vcf_file:
                continue

            for vtype in VARIANT_TYPES:
                count = count_variants_by_type(vcf_file, vtype)
                total[eval_type] += count

        tp = total["tp"]
        fp = total["fp"]
        fn = total["fn"]

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * sensitivity / (precision + sensitivity) if (precision + sensitivity) > 0 else 0

        writer.writerow([
            sample_name, tp, fp, fn,
            round(precision, 4),
            round(sensitivity, 4),
            round(f1, 4)
        ])

print(f"✅ Summary saved to: {output_path}")

