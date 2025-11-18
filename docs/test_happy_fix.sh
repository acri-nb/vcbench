#!/bin/bash

# Script de test rapide pour vérifier les corrections hap.py

set -e

echo "=================================================="
echo "Test des corrections hap.py"
echo "=================================================="
echo ""

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PROJECT_DIR="/mnt/acri4_2/gth/project/vcbench"
cd "$PROJECT_DIR/qc-dashboard"

echo "1. Test de la fonction extract_base_sample..."
python3 << 'EOF'
import sys
sys.path.insert(0, '.')
from api.tasks.setup_reference import extract_base_sample

tests = [
    ("NA24143_Lib3_Rep1", "NA24143"),
    ("NA24143_Lib3_Rep1_R001", "NA24143"),
    ("NA12878_R001", "NA12878"),
    ("HG004", "HG004"),
]

all_passed = True
for input_val, expected in tests:
    result = extract_base_sample(input_val)
    if result == expected:
        print(f"  ✓ {input_val:30} -> {result:15} (expected: {expected})")
    else:
        print(f"  ✗ {input_val:30} -> {result:15} (expected: {expected})")
        all_passed = False

if all_passed:
    print("\n✅ Tous les tests d'extraction passés")
    sys.exit(0)
else:
    print("\n❌ Certains tests ont échoué")
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Test 1 réussi${NC}"
else
    echo -e "${RED}❌ Test 1 échoué${NC}"
    exit 1
fi

echo ""
echo "2. Test de la logique de parsing du run_name..."
python3 << 'EOF'
import sys

def parse_run_name(run_name):
    parts = run_name.split("_")
    if len(parts) < 2:
        raise ValueError(f"Invalid run name format: {run_name}")
    
    run_idx = -1
    for i in range(len(parts) - 1, -1, -1):
        if parts[i].startswith('R') and parts[i][1:].isdigit():
            run_idx = i
            break
    
    if run_idx == -1:
        sample = "_".join(parts[:-1])
        run = parts[-1]
    else:
        sample = "_".join(parts[:run_idx])
        run = "_".join(parts[run_idx:])
    
    return sample, run

tests = [
    ("NA24143_Lib3_Rep1_R001", "NA24143_Lib3_Rep1", "R001"),
    ("NA12878_R001", "NA12878", "R001"),
    ("HG004_test_R002", "HG004_test", "R002"),
]

all_passed = True
for run_name, expected_sample, expected_run in tests:
    sample, run = parse_run_name(run_name)
    if sample == expected_sample and run == expected_run:
        print(f"  ✓ {run_name:30} -> sample={sample:20} run={run}")
    else:
        print(f"  ✗ {run_name:30} -> sample={sample:20} run={run}")
        print(f"    Expected: sample={expected_sample:20} run={expected_run}")
        all_passed = False

if all_passed:
    print("\n✅ Tous les tests de parsing passés")
    sys.exit(0)
else:
    print("\n❌ Certains tests ont échoué")
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Test 2 réussi${NC}"
else
    echo -e "${RED}❌ Test 2 échoué${NC}"
    exit 1
fi

echo ""
echo "3. Vérification des fichiers de référence pour NA24143..."
if [ -f "$PROJECT_DIR/data/reference/NA24143/NA24143_truth.vcf.gz" ]; then
    echo -e "  ${GREEN}✓${NC} Truth VCF existe"
else
    echo -e "  ${RED}✗${NC} Truth VCF manquant"
    exit 1
fi

if [ -f "$PROJECT_DIR/data/reference/NA24143/NA24143_confident_regions.bed" ]; then
    echo -e "  ${GREEN}✓${NC} Confident regions BED existe"
else
    echo -e "  ${RED}✗${NC} Confident regions BED manquant"
    exit 1
fi

if [ -f "$PROJECT_DIR/data/reference/GCA_000001405.15_GRCh38_no_alt_analysis_set.fasta" ]; then
    echo -e "  ${GREEN}✓${NC} Genome FASTA existe"
else
    echo -e "  ${RED}✗${NC} Genome FASTA manquant"
    exit 1
fi

if [ -d "$PROJECT_DIR/data/reference/GRCh38.sdf" ]; then
    echo -e "  ${GREEN}✓${NC} SDF directory existe"
else
    echo -e "  ${YELLOW}⚠${NC}  SDF directory manquant (optionnel)"
fi

echo -e "${GREEN}✅ Test 3 réussi${NC}"

echo ""
echo "4. Vérification de la syntaxe Python..."
cd "$PROJECT_DIR/qc-dashboard"
python3 -m py_compile api/tasks/process_run.py 2>&1 >/dev/null
if [ $? -eq 0 ]; then
    echo -e "  ${GREEN}✓${NC} process_run.py: OK"
else
    echo -e "  ${RED}✗${NC} process_run.py: ERREUR"
    exit 1
fi

python3 -m py_compile api/app/api_v1/endpoints/runs.py 2>&1 >/dev/null
if [ $? -eq 0 ]; then
    echo -e "  ${GREEN}✓${NC} runs.py: OK"
else
    echo -e "  ${RED}✗${NC} runs.py: ERREUR"
    exit 1
fi

python3 -m py_compile api/tasks/setup_reference.py 2>&1 >/dev/null
if [ $? -eq 0 ]; then
    echo -e "  ${GREEN}✓${NC} setup_reference.py: OK"
else
    echo -e "  ${RED}✗${NC} setup_reference.py: ERREUR"
    exit 1
fi

echo -e "${GREEN}✅ Test 4 réussi${NC}"

echo ""
echo "5. Vérification du script happy.sh..."
if ! grep -q "convert-gvcf-query" "$PROJECT_DIR/pipeline/happy.sh"; then
    echo -e "  ${GREEN}✓${NC} Option --convert-gvcf-query supprimée"
else
    echo -e "  ${RED}✗${NC} Option --convert-gvcf-query encore présente"
    exit 1
fi

if grep -q "pass-only" "$PROJECT_DIR/pipeline/happy.sh"; then
    echo -e "  ${GREEN}✓${NC} Option --pass-only ajoutée"
else
    echo -e "  ${YELLOW}⚠${NC}  Option --pass-only non trouvée"
fi

echo -e "${GREEN}✅ Test 5 réussi${NC}"

echo ""
echo "=================================================="
echo -e "${GREEN}✅ TOUS LES TESTS PASSÉS !${NC}"
echo "=================================================="
echo ""
echo "Vous pouvez maintenant:"
echo "  1. Aller sur le dashboard: http://localhost:8002"
echo "  2. Sélectionner le run: NA24143_Lib3_Rep1_R001"
echo "  3. Cocher 'hap.py (Happy benchmarking)'"
echo "  4. Cliquer sur 'Launch Selected Benchmarking'"
echo ""
echo "Le serveur devrait se recharger automatiquement."
echo "Si ce n'est pas le cas, redémarrez avec:"
echo "  cd $PROJECT_DIR/qc-dashboard && bash start_app.sh"
echo ""

