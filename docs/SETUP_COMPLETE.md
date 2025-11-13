# ✅ Configuration complète - NA24143 (HG004) prêt pour le benchmarking

## ⚠️ Corrections critiques appliquées (2025-11-13)

### Problème résolu: Image Docker Truvari manquante
**Erreur initiale:** `docker: Error response from daemon: pull access denied for truvari`

**Cause:** Le script `pipeline/truvari.sh` utilisait une image inexistante `truvari` au lieu de l'image officielle biocontainers.

**Solution:**
- Image Docker corrigée: `quay.io/biocontainers/truvari:4.0.0--pyhdfd78af_0`
- Commande mise à jour: `truvari bench` (ajout du sous-commande "bench")

### Problème résolu: Incompatibilité des noms de chromosomes
**Erreur initiale:** `WARNING: Unable to fetch 1 from [...].sv.filtered.vcf.gz`

**Cause:** 
- Référence HG002 utilise: `1`, `2`, `3`, ..., `X`, `Y`
- Run DRAGEN utilise: `chr1`, `chr2`, `chr3`, ..., `chrX`, `chrY`

**Solution:**
- Normalisation automatique des VCF de référence (ajout préfixe "chr")
- Normalisation automatique des fichiers BED (ajout préfixe "chr")
- Utilisation de `bcftools annotate --rename-chrs` pour les VCF
- Fichiers générés: `*.normalized.vcf.gz` et `*.normalized.bed`

# ✅ Configuration complète - NA24143 (HG004) prêt pour le benchmarking

## État actuel

Tous les fichiers de référence sont maintenant en place pour NA24143 :

### Génome de référence (GRCh38)
- ✅ `GCA_000001405.15_GRCh38_no_alt_analysis_set.fasta` (3.0 GB)
- ✅ `GCA_000001405.15_GRCh38_no_alt_analysis_set.fasta.fai`
- ⚠️ `GRCh38.sdf` - OPTIONNEL (requis uniquement pour hap.py)

### Références NA24143
- ✅ `NA24143_truth.vcf.gz` (149 MB) - Truth set small variants
- ✅ `NA24143_truth.vcf.gz.tbi` - Index
- ✅ `NA24143_confident_regions.bed` (13 MB) - Régions de confiance

### Références SV (⚠️ TEMPORAIRE - HG002 utilisé)
- ⚠️ `NA24143_sv_truth.vcf.gz` (25 MB) - **SOURCE: HG002**
- ⚠️ `NA24143_sv_confident_regions.bed` (709 KB) - **SOURCE: HG002**

**IMPORTANT:** Les fichiers SV proviennent de HG002 car HG004 n'est pas encore disponible sur GIAB.
Les résultats Truvari ne seront pas valides scientifiquement mais permettent de tester le pipeline.

### Fichiers de run téléchargés depuis AWS
- ✅ `NA24143_Lib3_Rep1_R001.dragen.hard-filtered.gvcf.gz` (8.0 GB)
- ✅ `NA24143_Lib3_Rep1_R001.dragen.sv.vcf.gz` (4.4 MB)
- ✅ 9 fichiers CSV de métriques

## Corrections appliquées

### 1. Code Python (`setup_reference.py`)
```python
# Avant: Ne reconnaissait pas NA24143
# Après: Vérifie d'abord si base_name est dans GIAB_SAMPLES
def extract_base_sample(sample_name: str) -> str:
    base_name = sample_name.split('_')[0]
    if base_name in GIAB_SAMPLES:
        return base_name
    ...
```

### 2. Script Bash (`setup_reference.sh`)
```bash
# Avant: [[ ! -f "$sample_dir"/*.vcf.gz ]] <- Erreur syntaxe
# Après: if ! compgen -G "$sample_dir/*.vcf.gz" > /dev/null 2>&1
```

### 3. URLs GIAB corrigées
```bash
# Avant: data/AshkenazimTrio/analysis/NIST_HG004...
# Après: release/AshkenazimTrio/HG004_NA24143_mother/NISTv4.2.1/GRCh38/...
```

### 4. Script AWS - Téléchargement SV ajouté
```bash
# Avant: Téléchargeait uniquement .gvcf.gz et .csv
# Après: Télécharge aussi .sv.vcf.gz pour Truvari
```

### 5. Fichiers optionnels
```python
# SDF et SV references marqués comme "(optional)"
# Le système ne crash plus s'ils sont absents
```

## Pipeline maintenant fonctionnel

Le système peut maintenant:
1. ✅ Télécharger depuis AWS (GVCF + SV VCF + CSV)
2. ✅ Vérifier les références automatiquement
3. ✅ Télécharger les références GIAB manquantes
4. ✅ Traiter les CSV de métriques
5. ⚠️ Exécuter Truvari (avec référence HG002 temporaire)
6. ✅ Compléter le pipeline avec succès

## Utilisation

```bash
# Interface web
http://localhost:8000/runs
→ Onglet "Upload Run"
→ Section "Import from AWS S3"
→ Sample ID: NA24143_Lib3_Rep1
→ Options: ☑️ csv, ☑️ truvari
→ Cliquer "Import from AWS"
→ Observer les logs en temps réel! 🎬
```

## Avertissements

### ⚠️ Résultats Truvari pour NA24143
Les métriques Truvari NE SONT PAS VALIDES car elles comparent:
- **Query:** NA24143 (HG004 - mère)
- **Truth:** HG002 (fils)

Ces individus sont génétiquement différents!

**À utiliser uniquement pour:**
- ✅ Tester que le pipeline fonctionne
- ✅ Valider l'infrastructure technique
- ❌ PAS pour de vraies analyses scientifiques

### Solution à long terme
1. **Option A:** Attendre que GIAB publie HG004 SV truth sets
2. **Option B:** Désactiver Truvari pour NA24143
3. **Option C:** Utiliser NA24385 (HG002) ou NA24149 (HG003) qui ont des SV valides

## Prochaine étape

**Relancez le téléchargement AWS depuis l'interface web!**

Tout devrait maintenant fonctionner de bout en bout:
- Download AWS → Verify References → Process CSV → Run Truvari → Success ✅

Date: $(date)
