import csv
import re
import subprocess
from pathlib import Path

PROCESSED_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"
VARIANT_TYPES = ["snp", "mnp", "ins", "del", "indel", "sym"]
VCFEVAL_FILES = ["tp", "fp", "fn"]

output_path = PROCESSED_DIR / "variant_summary.tsv"
header = ["Sample", "TP", "FP", "FN", "Precision", "Sensitivity", "F1"]


def count_variants_by_type(vcf_path, vtype):
    if not vcf_path.exists():
        return 0

    try:
        result = subprocess.run(
            ["bcftools", "query", "-f", "%TYPE\\n", str(vcf_path)],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return 0

    if result.returncode != 0:
        return 0

    pattern = re.compile(rf"\b{re.escape(vtype)}\b")
    return sum(1 for line in result.stdout.splitlines() if pattern.search(line))


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="") as outfile:
        writer = csv.writer(outfile, delimiter='\t')
        writer.writerow(header)

        for sample_dir in PROCESSED_DIR.iterdir():
            if not sample_dir.is_dir():
                continue

            sample_name = sample_dir.name
            total = {"tp": 0, "fp": 0, "fn": 0}

            for eval_type in VCFEVAL_FILES:
                vcf_path_gz = sample_dir / f"{eval_type}.vcf.gz"
                vcf_path = sample_dir / f"{eval_type}.vcf"
                vcf_file = vcf_path_gz if vcf_path_gz.exists() else vcf_path if vcf_path.exists() else None
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

    print(f"Summary saved to: {output_path}")


if __name__ == "__main__":
    main()
