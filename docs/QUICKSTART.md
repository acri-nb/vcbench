# 🚀 Démarrage rapide - AWS Download avec logs en temps réel

## Installation

```bash
cd /mnt/acri4_2/gth/project/vcbench

# Installer les nouvelles dépendances
pip install -r requirements.txt
```

## Démarrage

```bash
# Démarrer le serveur FastAPI/Dash
cd qc-dashboard
uvicorn api.app.main:app --reload --port 8000
```

## Utilisation

### Via l'interface web

1. Ouvrir: **http://localhost:8000/runs**

2. Onglet **"Upload Run"** → Section **"Import from AWS S3"**

3. Entrer un Sample ID (exemple: `NA24143_Lib3_Rep1`)

4. Sélectionner les options de benchmarking:
   - ☑️ **csv** (recommandé)
   - ☑️ **truvari** (si vous avez des SVs)
   - ☐ **happy** (optionnel, plus lent)
   - ☐ **stratified** (nécessite happy)

5. ☑️ **"Process automatically after download"**

6. Cliquer **"Import from AWS"**

7. **Observer la console de logs** qui apparaît automatiquement:
   ```
   [12:34:56] Starting AWS download for sample: NA24143_Lib3_Rep1
   [12:34:57] Executing download script: /path/to/aws_download_gvcf.sh
   [12:34:58] Date du jour: 20251113
   [12:34:59] Répertoire de destination: /path/to/data/lab_runs
   [12:35:00] Traitement du sample_ID: NA24143_Lib3_Rep1
   [12:35:02] ⬇️  Téléchargement de NA24143_Lib3_Rep1.gvcf.gz...
   [12:35:45] ✅ NA24143_Lib3_Rep1_R001.gvcf.gz téléchargé avec succès
   [12:36:00] AWS download completed successfully
   [12:36:01] Verifying reference files...
   [12:36:02] Reference files verified successfully
   [12:36:03] Starting benchmarking pipeline (csv=True, truvari=True)
   [12:40:15] Benchmarking pipeline completed successfully
   [12:40:16] ✅ Process completed successfully!
   ```

## Samples de test recommandés

### Samples GIAB (références auto-téléchargées)
```
NA12878_Lib3_Rep1    (HG001)
NA24143_Lib3_Rep1    (HG004) ⭐ RECOMMANDÉ
NA24385_Lib3_Rep1    (HG002)
```

### Vérification des fichiers téléchargés

```bash
# Fichiers de run téléchargés depuis AWS
ls /mnt/acri4_2/gth/project/vcbench/data/lab_runs/NA24143_Lib3_Rep1_R001/

# Références GIAB téléchargées automatiquement
ls /mnt/acri4_2/gth/project/vcbench/data/reference/NA24143/
ls /mnt/acri4_2/gth/project/vcbench/data/reference/NA24143/stvar/
```

## API REST (alternative)

```bash
# Lancer un téléchargement via curl
curl -X POST http://localhost:8000/api/v1/upload/aws \
  -H "Content-Type: application/json" \
  -d '{
    "sample_id": "NA24143_Lib3_Rep1",
    "benchmarking": "csv,truvari",
    "auto_process": true
  }'

# Vérifier le statut
curl http://localhost:8000/api/v1/download/status/NA24143_Lib3_Rep1

# Récupérer tous les logs
curl http://localhost:8000/api/v1/download/logs/NA24143_Lib3_Rep1?since=0
```

## Colorisation des logs

- 🔵 **Bleu** (progress): Téléchargements en cours
- 🟢 **Vert** (success): Opérations réussies
- 🟡 **Jaune** (warning): Avertissements (fichiers ignorés, etc.)
- 🔴 **Rouge** (error): Erreurs
- ⚪ **Gris** (info): Messages informatifs

## Troubleshooting rapide

### Le bouton "Import from AWS" est grisé
➡️ Vérifier que vous avez entré un Sample ID

### Les logs ne s'affichent pas
➡️ Rafraîchir la page (F5) et relancer l'import

### Erreur "AWS download script failed"
```bash
# Tester manuellement le script
cd /mnt/acri4_2/gth/project/vcbench
bash script/aws_download_gvcf.sh NA24143_Lib3_Rep1

# Vérifier le profil AWS
aws --profile vitalite s3 ls
```

### Erreur "Reference files not found"
```bash
# Tester le téléchargement des références
cd /mnt/acri4_2/gth/project/vcbench
bash script/setup_reference.sh NA24143
```

## Documentation complète

- **INTEGRATION_TEST.md** - Tests détaillés et dépannage
- **AWS_DOWNLOAD_INTEGRATION.md** - Architecture et design
- **IMPLEMENTATION_SUMMARY.md** - Résumé technique

## Support

Problème? Consulter les logs:
```bash
# Logs du serveur (terminal où uvicorn tourne)
# Logs du navigateur (F12 → Console)
# Logs API
curl http://localhost:8000/api/v1/download/logs/VOTRE_SAMPLE_ID
```

---

**Bon benchmarking! 🧬**

