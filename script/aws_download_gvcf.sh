#!/bin/bash

set -euo pipefail

# Configuration
BUCKET="cac1-emg-prd-s3-auto-results"
BASE_PATH="vitalite-genmol_6cb572b1-386c-3305-82ab-f05a82a5233a"
AWS_PROFILE="vitalite"

# Déterminer le répertoire de base du projet (parent du répertoire script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
LAB_RUNS_DIR="${PROJECT_DIR}/data/lab_runs"

# Créer le répertoire lab_runs s'il n'existe pas
mkdir -p "${LAB_RUNS_DIR}"

# Récupération du paramètre optionnel sample_ID
SAMPLE_ID_ARG="${1:-}"

# Vérification que AWS CLI est installé
if ! command -v aws &> /dev/null; then
    echo "Erreur: AWS CLI n'est pas installé. Veuillez l'installer d'abord."
    exit 1
fi

# Génération de la date au format AAAAMMJJ
DATE_TODAY=$(date +%Y%m%d)

# Liste des patterns CSV de métriques à télécharger (basés sur l'image fournie)
CSV_PATTERNS=(
    "*sv_metrics.csv"
    "*roh_metrics.csv"
    "*ploidy_estimation_metrics.csv"
    "*cnv_metrics.csv"
    "*bed_coverage_metrics.csv"
    "*wgs_contig_mean_cov.csv"
    "*vc_metrics.csv"
    "*vc_hethom_ratio_metrics.csv"
    "*mapping_metrics.csv"
)

# Fonction pour vérifier si un fichier correspond à un des patterns CSV requis
matches_csv_pattern() {
    local file="$1"
    for pattern in "${CSV_PATTERNS[@]}"; do
        if [[ "$file" == $pattern ]]; then
            return 0
        fi
    done
    return 1
}

# Fonction pour ajouter _R001 après le sample_ID dans le nom du fichier
add_r001_to_filename() {
    local file="$1"
    local sample_id="$2"
    # Remplacer sample_ID. par sample_ID_R001. dans le nom du fichier
    echo "${file}" | sed "s/^${sample_id}\\./${sample_id}_R001./"
}

echo "Début du téléchargement des fichiers GVCF et CSV de métriques..."
echo "Date du jour: ${DATE_TODAY}"
echo "Répertoire de destination: ${LAB_RUNS_DIR}"
echo ""

# Compteurs
total_samples=0
total_ids=0
total_gvcf=0
total_csv=0
downloaded_gvcf=0
downloaded_csv=0
skipped_gvcf=0
skipped_csv=0

# Déterminer la liste des sample_ID à traiter
if [ -n "$SAMPLE_ID_ARG" ]; then
    # Si un sample_ID est fourni en paramètre, ne traiter que celui-ci (recherche exacte)
    echo "Traitement du sample_ID spécifié: ${SAMPLE_ID_ARG}"
    sample_ids="${SAMPLE_ID_ARG}"
else
    # Sinon, récupérer tous les sample_ID disponibles
    echo "Recherche de tous les sample_ID..."
    sample_ids=$(aws --profile vitalite s3 ls "s3://${BUCKET}/${BASE_PATH}/" | awk '{print $NF}' | sed 's|/$||')
    
    if [ -z "$sample_ids" ]; then
        echo "Aucun sample_ID trouvé dans s3://${BUCKET}/${BASE_PATH}/"
        exit 1
    fi
fi

# Traiter chaque sample_ID
while IFS= read -r sample_id; do
    if [ -z "$sample_id" ]; then
        continue
    fi
    
    total_samples=$((total_samples + 1))
    echo ""
    echo "Traitement du sample_ID: ${sample_id}"
    
    # Créer le répertoire de sortie pour ce sample_ID: sample_ID_R001 dans lab_runs
    output_dir="${LAB_RUNS_DIR}/${sample_id}_R001"
    mkdir -p "${output_dir}"
    
    echo "  Répertoire de sortie: ${output_dir}"
    
    # Chemin vers vcf/dragen pour ce sample_ID
    dragen_path="${BASE_PATH}/${sample_id}/vcf/dragen"
    
    # Vérifier si le répertoire existe
    if ! aws --profile vitalite s3 ls "s3://${BUCKET}/${dragen_path}/" &> /dev/null; then
        echo "  ⚠️  Répertoire vcf/dragen non trouvé pour ${sample_id}, passage au suivant..."
        continue
    fi
    
    # Parcourir tous les id dans vcf/dragen
    ids=$(aws --profile vitalite s3 ls "s3://${BUCKET}/${dragen_path}/" | awk '{print $NF}' | sed 's|/$||')
    
    if [ -z "$ids" ]; then
        echo "  ⚠️  Aucun id trouvé dans vcf/dragen pour ${sample_id}"
        continue
    fi
    
    # Traiter chaque id
    while IFS= read -r id; do
        if [ -z "$id" ]; then
            continue
        fi
        
        total_ids=$((total_ids + 1))
        echo "  Traitement de l'id: ${id}"
        
        # Chemin vers varcaller
        varcaller_path="${dragen_path}/${id}/varcaller"
        
        # Vérifier si le répertoire varcaller existe
        if ! aws --profile vitalite s3 ls "s3://${BUCKET}/${varcaller_path}/" &> /dev/null; then
            echo "    ⚠️  Répertoire varcaller non trouvé pour ${sample_id}/${id}, passage au suivant..."
            continue
        fi
        
        # Lister tous les fichiers dans varcaller
        files=$(aws --profile vitalite s3 ls "s3://${BUCKET}/${varcaller_path}/" | awk '{print $NF}')
        
        if [ -z "$files" ]; then
            echo "    ⚠️  Aucun fichier trouvé dans varcaller pour ${sample_id}/${id}"
            continue
        fi
        
        # Filtrer et télécharger les fichiers .gvcf.gz et .csv
        gvcf_found=false
        csv_found=false
        
        while IFS= read -r file; do
            if [ -z "$file" ]; then
                continue
            fi
            
            # Chemin source complet
            source_path="s3://${BUCKET}/${varcaller_path}/${file}"
            
            # Générer le nom de fichier de destination avec _R001 après le sample_ID
            dest_filename=$(add_r001_to_filename "$file" "$sample_id")
            
            # Chemin de destination local (structure plate dans sample_ID_R001)
            dest_path="${output_dir}/${dest_filename}"
            
            # Traiter les fichiers .gvcf.gz
            if [[ "$file" == *.gvcf.gz ]]; then
                total_gvcf=$((total_gvcf + 1))
                gvcf_found=true
                
                # Vérifier si le fichier existe déjà localement
                if [ -f "${dest_path}" ]; then
                    echo "    ⏭️  ${dest_filename} (GVCF) existe déjà, ignoré"
                    skipped_gvcf=$((skipped_gvcf + 1))
                else
                    echo "    ⬇️  Téléchargement de ${file} → ${dest_filename} (GVCF)..."
                    if aws --profile vitalite s3 cp "${source_path}" "${dest_path}"; then
                        downloaded_gvcf=$((downloaded_gvcf + 1))
                        echo "    ✅ ${dest_filename} téléchargé avec succès"
                    else
                        echo "    ❌ Erreur lors du téléchargement de ${dest_filename}"
                    fi
                fi
            fi
            
            # Traiter les fichiers .csv (uniquement ceux correspondant aux patterns de métriques)
            if [[ "$file" == *.csv ]]; then
                if matches_csv_pattern "$file"; then
                    total_csv=$((total_csv + 1))
                    csv_found=true
                    
                    # Vérifier si le fichier existe déjà localement
                    if [ -f "${dest_path}" ]; then
                        echo "    ⏭️  ${dest_filename} (CSV métriques) existe déjà, ignoré"
                        skipped_csv=$((skipped_csv + 1))
                    else
                        echo "    ⬇️  Téléchargement de ${file} → ${dest_filename} (CSV métriques)..."
                        if aws --profile vitalite s3 cp "${source_path}" "${dest_path}"; then
                            downloaded_csv=$((downloaded_csv + 1))
                            echo "    ✅ ${dest_filename} téléchargé avec succès"
                        else
                            echo "    ❌ Erreur lors du téléchargement de ${dest_filename}"
                        fi
                    fi
                else
                    echo "    ⏭️  ${file} (CSV ignoré - ne correspond pas aux patterns de métriques)"
                fi
            fi
            
        done <<< "$files"
        
        if [ "$gvcf_found" = false ] && [ "$csv_found" = false ]; then
            echo "    ℹ️  Aucun fichier .gvcf.gz ou CSV de métriques trouvé pour ${sample_id}/${id}"
        fi
        
    done <<< "$ids"
    
done <<< "$sample_ids"

echo ""
echo "=========================================="
echo "Résumé du téléchargement:"
echo "  Sample_ID traités: ${total_samples}"
echo "  ID traités: ${total_ids}"
echo ""
echo "  Fichiers GVCF:"
echo "    Trouvés: ${total_gvcf}"
echo "    Téléchargés: ${downloaded_gvcf}"
echo "    Ignorés (déjà présents): ${skipped_gvcf}"
echo ""
echo "  Fichiers CSV de métriques:"
echo "    Trouvés: ${total_csv}"
echo "    Téléchargés: ${downloaded_csv}"
echo "    Ignorés (déjà présents): ${skipped_csv}"
echo "=========================================="
echo ""
echo "Téléchargement terminé."
