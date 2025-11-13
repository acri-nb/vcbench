# Test d'intégration AWS Download + Setup Reference + Benchmarking

## Vue d'ensemble

Ce document décrit le flux complet d'intégration entre le téléchargement AWS, la vérification/téléchargement des références GIAB, et le benchmarking avec suivi en temps réel.

## Architecture

```
Frontend (Dash)
    ↓
  API Endpoint (/api/v1/upload/aws)
    ↓
  Background Task (async)
    ↓
  ┌─────────────────────────────────────┐
  │ 1. AWS Download (streaming)         │
  │    - Script: aws_download_gvcf.sh   │
  │    - Logs streamés via WebSocket    │
  └─────────────────────────────────────┘
    ↓
  ┌─────────────────────────────────────┐
  │ 2. Setup Reference                  │
  │    - ensure_references()            │
  │    - Auto-download si GIAB sample   │
  │    - setup_reference.sh             │
  └─────────────────────────────────────┘
    ↓
  ┌─────────────────────────────────────┐
  │ 3. Benchmarking Pipeline            │
  │    - process_happy() → hap.py       │
  │    - process_truvari() → truvari    │
  │    - process_csv_files()            │
  └─────────────────────────────────────┘
```

## Composants modifiés

### 1. Backend - WebSocket Manager
**Fichier**: `qc-dashboard/api/app/websocket.py`

- Gestion des connexions WebSocket par `sample_id`
- Stockage des logs en mémoire pour polling HTTP
- Niveaux de logs: info, success, warning, error, progress
- États: pending, running, completed, error

### 2. Backend - API Endpoints
**Fichier**: `qc-dashboard/api/app/api_v1/endpoints/download_status.py`

- `GET /api/v1/download/status/{sample_id}` - Statut du téléchargement
- `GET /api/v1/download/logs/{sample_id}?since=N` - Logs depuis l'index N
- `POST /api/v1/download/cleanup` - Nettoyage des logs anciens

### 3. Backend - Process AWS avec streaming
**Fichier**: `qc-dashboard/api/app/api_v1/endpoints/uploads.py`

- Fonction `process_aws_run_background()` rendue async
- Streaming ligne par ligne de la sortie du script AWS
- Émission des logs via WebSocket en temps réel
- Intégration avec `ensure_references()` après téléchargement
- Gestion des erreurs avec logs appropriés

### 4. Backend - Intégration setup_reference
**Fichier**: `qc-dashboard/api/tasks/process_run.py`

- Appel de `ensure_references()` dans `process_happy()`
- Appel de `ensure_references()` dans `process_truvari()`
- Téléchargement automatique des références GIAB manquantes
- Messages d'erreur clairs si références non disponibles

### 5. Frontend - Console de logs
**Fichier**: `qc-dashboard/dash_app/pages/runs.py`

- Composant `aws-logs-console` avec style terminal
- Polling des logs toutes les 2 secondes via `dcc.Interval`
- Colorisation des logs selon le niveau
- Arrêt automatique du polling à la fin du processus

## Flux de test manuel

### Prérequis
```bash
# Installer les dépendances mises à jour
pip install -r requirements.txt

# S'assurer que le profil AWS est configuré
aws --profile vitalite s3 ls
```

### Démarrer l'application
```bash
cd /mnt/acri4_2/gth/project/vcbench/qc-dashboard
uvicorn api.app.main:app --reload --port 8000
```

### Test 1: Téléchargement AWS avec sample GIAB connu (NA24143)

1. Ouvrir le navigateur: `http://localhost:8000/runs`
2. Onglet "Upload Run" → Section "Import from AWS S3"
3. Entrer Sample ID: `NA24143_Lib3_Rep1`
4. Sélectionner options: `csv`, `truvari`
5. Cocher "Process automatically after download"
6. Cliquer "Import from AWS"

**Comportement attendu:**
- Message de confirmation s'affiche
- Console de logs apparaît automatiquement
- Logs du téléchargement AWS streamés en temps réel
- Message "Verifying reference files..." après téléchargement
- Si références manquantes: téléchargement automatique via `setup_reference.sh`
- Lancement du pipeline de benchmarking
- Message final "✅ Process completed successfully!"

**Vérifications:**
```bash
# Vérifier que les fichiers sont téléchargés
ls /mnt/acri4_2/gth/project/vcbench/data/lab_runs/NA24143_Lib3_Rep1_R001/

# Vérifier que les références existent
ls /mnt/acri4_2/gth/project/vcbench/data/reference/NA24143/
ls /mnt/acri4_2/gth/project/vcbench/data/reference/NA24143/stvar/

# Vérifier le génome de référence
ls /mnt/acri4_2/gth/project/vcbench/data/reference/GRCh38.sdf
```

### Test 2: Sample déjà téléchargé avec références existantes

1. Relancer le même sample: `NA24143_Lib3_Rep1`
2. Observer que les fichiers existants sont ignorés
3. Vérification rapide des références (déjà présentes)
4. Pipeline lancé immédiatement

### Test 3: WebSocket vs Polling

**Test WebSocket (si navigateur supporte):**
- Ouvrir la console du navigateur
- Vérifier la connexion WebSocket: `ws://localhost:8000/ws/download/NA24143_Lib3_Rep1`

**Test Polling (fallback):**
- Les logs sont aussi disponibles via HTTP
- Tester manuellement:
```bash
# Vérifier le statut
curl http://localhost:8000/api/v1/download/status/NA24143_Lib3_Rep1

# Récupérer les logs
curl http://localhost:8000/api/v1/download/logs/NA24143_Lib3_Rep1?since=0
```

### Test 4: Gestion d'erreurs

**Sample non-GIAB sans références:**
1. Entrer un sample inconnu: `TEST_SAMPLE_123`
2. Le téléchargement peut échouer (sample n'existe pas sur S3)
3. OU si le sample existe, l'erreur survient lors de `ensure_references()`
4. Message d'erreur clair dans la console

**Vérification:**
- Logs affichent le niveau "error" en rouge
- Statut passe à "error"
- Polling s'arrête automatiquement

## Tests automatisés (optionnel)

Pour des tests automatisés futurs, créer:

```python
# tests/test_integration_aws_download.py
import pytest
from api.app import websocket as ws_manager

def test_log_store_initialization():
    sample_id = "test_sample"
    ws_manager.init_log_store(sample_id)
    assert sample_id in ws_manager.log_store
    assert ws_manager.log_store[sample_id]["status"] == "pending"

def test_add_log():
    sample_id = "test_sample"
    ws_manager.init_log_store(sample_id)
    ws_manager.add_log(sample_id, "Test message", ws_manager.LogLevel.INFO)
    logs = ws_manager.get_logs(sample_id)
    assert len(logs) == 1
    assert logs[0]["message"] == "Test message"
```

## Dépannage

### Les logs ne s'affichent pas
1. Vérifier que l'API est accessible: `curl http://localhost:8000/api/v1/download/status/SAMPLE_ID`
2. Vérifier la console navigateur pour les erreurs JavaScript
3. Vérifier que le callback Dash `poll_logs` est enregistré

### Le téléchargement AWS échoue
1. Vérifier le profil AWS: `aws --profile vitalite s3 ls`
2. Vérifier les logs du script: `/mnt/acri4_2/gth/project/vcbench/script/aws_download_gvcf.sh`
3. Tester manuellement: `bash aws_download_gvcf.sh SAMPLE_ID`

### Les références ne se téléchargent pas
1. Vérifier que `setup_reference.sh` est exécutable
2. Tester manuellement: `bash setup_reference.sh NA24143`
3. Vérifier les dépendances: `wget`, `samtools`, `tabix`

### Le benchmarking échoue
1. Vérifier que les fichiers de run sont présents dans `data/lab_runs/`
2. Vérifier que les références sont complètes dans `data/reference/`
3. Consulter les logs dans le terminal où uvicorn tourne

## Nettoyage après tests

```bash
# Supprimer les logs anciens via l'API
curl -X POST http://localhost:8000/api/v1/download/cleanup

# Ou nettoyer manuellement les répertoires de test
rm -rf /mnt/acri4_2/gth/project/vcbench/data/lab_runs/TEST_*
```

## Performance

- **Polling Interval**: 2 secondes (configurable dans `runs.py`)
- **Rétention des logs**: 1 heure (configurable dans `websocket.py`)
- **Taille max logs en mémoire**: Illimitée (à surveiller en production)

## Améliorations futures

1. **Authentification WebSocket**: Sécuriser les connexions WebSocket
2. **Persistance des logs**: Stocker dans une base de données plutôt qu'en mémoire
3. **Notifications**: Email/Slack à la fin du processus
4. **Progress bar**: Ajouter une barre de progression visuelle
5. **Historique**: Conserver l'historique des téléchargements passés

