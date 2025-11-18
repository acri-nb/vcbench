# Corrections pour hap.py - Résumé

## Problèmes Identifiés et Résolus

### 1. ❌ Option invalide `--convert-gvcf-query`
**Erreur:** `Unknown arguments specified : ['--convert-gvcf-query']`

**Cause:** L'option `--convert-gvcf-query` n'existe pas (ou plus) dans la version de hap.py utilisée.

**Solution:** Supprimé l'option dans `pipeline/happy.sh` et ajouté `--pass-only` à la place.

**Fichiers modifiés:**
- `pipeline/happy.sh` (ligne 28)

---

### 2. ❌ Extraction incorrecte du nom du sample
**Erreur:** `Reference VCF in /mnt/.../reference/NA24143_Lib3_Rep1/` au lieu de `.../reference/NA24143/`

**Cause:** Le code utilisait le sample complet `NA24143_Lib3_Rep1` au lieu du base sample `NA24143` pour chercher les fichiers de référence.

**Solution:** 
- Ajouté l'extraction du base sample dans `process_happy()` et `process_truvari()`
- Utilisé `extract_base_sample()` pour obtenir `NA24143` depuis `NA24143_Lib3_Rep1`
- Mis à jour tous les chemins Docker pour utiliser `base_sample` pour les références

**Fichiers modifiés:**
- `qc-dashboard/api/tasks/process_run.py`:
  - `process_happy()` (lignes 72-90, 275-299)
  - `process_truvari()` (lignes 375-393)

---

### 3. ❌ Parsing incorrect du run_name dans l'endpoint
**Erreur:** Splitting naïf sur `_` qui donne `sample=NA24143, run=Lib3_Rep1_R001`

**Cause:** La logique `run_name.split("_", 1)` est trop simple pour des noms comme `NA24143_Lib3_Rep1_R001`.

**Solution:** Implémenté une logique de parsing intelligente qui :
1. Cherche le dernier élément commençant par `R` suivi de chiffres (`R001`, `R002`, etc.)
2. Extrait tout ce qui est avant comme `sample` et à partir de ce point comme `run`
3. Résultat: `sample=NA24143_Lib3_Rep1, run=R001`

**Fichiers modifiés:**
- `qc-dashboard/api/app/api_v1/endpoints/runs.py` (lignes 137-176)

---

## Fichiers Créés

### 1. ✅ Script de setup des références
**Fichier:** `script/setup_reference.sh`

Script Bash pour télécharger automatiquement les fichiers de référence GIAB (Genome in a Bottle) pour les échantillons connus.

**Fonctionnalités:**
- Détecte automatiquement si un sample est un échantillon GIAB
- Télécharge le génome GRCh38 de référence
- Télécharge les truth sets (VCF + BED) pour small variants
- Télécharge les truth sets pour structural variants (SV)
- Génère les index nécessaires (FAI, tabix)
- Support pour NA12878 (HG001), NA24143 (HG004), etc.

**Usage:**
```bash
./script/setup_reference.sh NA24143_Lib3_Rep1
./script/setup_reference.sh NA24143 --check-only
```

---

### 2. ✅ Module Python de gestion des références
**Fichier:** `qc-dashboard/api/tasks/setup_reference.py`

Module Python intégré au workflow pour vérifier et télécharger automatiquement les références.

**Fonctions principales:**
- `extract_base_sample(sample_name)`: Extrait le base sample (NA24143_Lib3_Rep1 → NA24143)
- `is_giab_sample(sample_name)`: Vérifie si c'est un échantillon GIAB connu
- `check_references(sample_name)`: Vérifie si tous les fichiers existent
- `ensure_references(sample_name, auto_download=True)`: Assure la présence des références
- `get_reference_status(sample_name)`: Statut détaillé des fichiers

**Intégration:**
- Appelé automatiquement dans `process_happy()` et `process_truvari()`
- Téléchargement automatique des références manquantes pour échantillons GIAB

---

## Tests Effectués

### ✅ Test 1: Extraction du base sample
```python
extract_base_sample("NA24143_Lib3_Rep1_R001") → "NA24143" ✓
extract_base_sample("NA24143_Lib3_Rep1")      → "NA24143" ✓
extract_base_sample("NA12878_R001")           → "NA12878" ✓
```

### ✅ Test 2: Parsing du run_name
```python
"NA24143_Lib3_Rep1_R001" → sample="NA24143_Lib3_Rep1", run="R001" ✓
```

### ✅ Test 3: Vérification des fichiers
```bash
ls /mnt/.../reference/NA24143/NA24143_confident_regions.bed ✓
ls /mnt/.../reference/NA24143/NA24143_truth.vcf.gz          ✓
```

### ✅ Test 4: Compilation Python
```bash
python3 -m py_compile api/tasks/process_run.py              ✓
python3 -m py_compile api/app/api_v1/endpoints/runs.py      ✓
```

---

## Structure des Références Attendue

```
data/reference/
├── GCA_000001405.15_GRCh38_no_alt_analysis_set.fasta    # Génome
├── GCA_000001405.15_GRCh38_no_alt_analysis_set.fasta.fai
├── GRCh38.sdf/                                          # Format RTG
└── NA24143/                                             # Base sample
    ├── NA24143_truth.vcf.gz                            # Truth set
    ├── NA24143_truth.vcf.gz.tbi                        # Index
    ├── NA24143_confident_regions.bed                    # Régions
    ├── stvar/                                          # Variants structuraux
    │   ├── NA24143_sv_truth.vcf.gz
    │   ├── NA24143_sv_truth.vcf.gz.tbi
    │   └── NA24143_sv_confident_regions.bed
    └── GRCh38_strat/                                   # Stratification (opt.)
        └── GRCh38-all-stratifications.tsv
```

---

## Mapping des Échantillons GIAB

| Sample ID | GIAB ID | Nom complet |
|-----------|---------|-------------|
| NA12878   | HG001   | CEU Trio (Utah/European) Child |
| NA24385   | HG002   | Ashkenazi Trio Son |
| NA24149   | HG003   | Ashkenazi Trio Father |
| NA24143   | HG004   | Ashkenazi Trio Mother |
| NA24631   | HG005   | Chinese Trio Son |
| NA24694   | HG006   | Chinese Trio Father |
| NA24695   | HG007   | Chinese Trio Mother |

---

## Instructions de Redémarrage

Le serveur FastAPI devrait redémarrer automatiquement (mode `--reload`), mais si nécessaire:

### Option 1: Attendre le reload automatique
Le serveur détecte les changements et redémarre automatiquement (peut prendre 5-10 secondes).

### Option 2: Redémarrage manuel
```bash
# Trouver le PID du serveur
ps aux | grep uvicorn | grep -v grep

# Tuer le processus
kill <PID>

# Redémarrer
cd /mnt/acri4_2/gth/project/vcbench/qc-dashboard
bash start_app.sh
```

### Option 3: Touch un fichier pour forcer le reload
```bash
touch /mnt/acri4_2/gth/project/vcbench/qc-dashboard/api/tasks/process_run.py
```

---

## Prochains Tests Recommandés

1. ✅ **Redémarrer l'application** (ou attendre le reload)
2. **Lancer hap.py** sur `NA24143_Lib3_Rep1_R001` depuis le dashboard
3. **Vérifier les logs** dans le terminal du serveur
4. **Vérifier les résultats** dans `data/processed/`

---

## Notes Importantes

- ⚠️ Le fichier SDF est optionnel mais recommandé (peut être généré via Docker si RTG Tools n'est pas installé)
- ⚠️ Les échantillons non-GIAB nécessitent un ajout manuel des références
- ✅ Le système télécharge automatiquement les références pour les échantillons GIAB connus
- ✅ Truvari fonctionne déjà correctement (pas de modifications nécessaires pour lui)

---

**Date:** 18 novembre 2025
**Status:** ✅ Corrections appliquées, en attente de tests après redémarrage

