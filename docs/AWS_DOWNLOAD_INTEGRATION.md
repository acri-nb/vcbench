# Intégration AWS Download + Setup Reference avec WebSocket

## Résumé des modifications

Cette intégration résout le problème `"Required files not found in reference or run directories"` et ajoute un suivi en temps réel des téléchargements AWS.

## Problème résolu

Lorsqu'un utilisateur lance un benchmarking via l'interface Dash après un téléchargement AWS, le système échouait car les fichiers de référence GIAB (truth sets, confident regions, etc.) n'étaient pas présents dans `data/reference/`.

## Solution implémentée

### 1. Vérification automatique des références

Les fonctions `process_happy()` et `process_truvari()` appellent maintenant `ensure_references()` qui :
- Vérifie si les fichiers de référence existent
- Si le sample est connu (GIAB: NA12878, NA24143, etc.), télécharge automatiquement les références
- Utilise le script `setup_reference.sh` pour le téléchargement
- Retourne des messages d'erreur clairs si le sample n'est pas reconnu

### 2. Suivi en temps réel via WebSocket/Polling

Architecture hybride pour la compatibilité maximale :

**WebSocket** (`/ws/download/{sample_id}`):
- Streaming en temps réel des logs
- Connexion bidirectionnelle pour les navigateurs modernes

**Polling HTTP** (`/api/v1/download/logs/{sample_id}`):
- Fallback pour tous les navigateurs
- Le frontend Dash interroge l'API toutes les 2 secondes
- Logs stockés en mémoire (1h de rétention)

### 3. Console de logs dans l'interface Dash

Une console style terminal affiche :
- Logs colorés selon le niveau (info, success, error, warning, progress)
- Timestamps pour chaque message
- Scroll automatique
- Arrêt automatique à la fin du processus

## Fichiers modifiés

### Backend

1. **`requirements.txt`**
   - Ajout de `python-socketio>=5.0.0` et `websockets>=10.0`

2. **`qc-dashboard/api/app/websocket.py`** (nouveau)
   - Gestionnaire WebSocket
   - Stockage des logs en mémoire
   - Fonctions: `broadcast_log()`, `get_logs()`, `get_status()`

3. **`qc-dashboard/api/app/main.py`**
   - Montage du WebSocket endpoint `/ws/download/{sample_id}`
   - Import du router `download_status`

4. **`qc-dashboard/api/app/api_v1/endpoints/download_status.py`** (nouveau)
   - `GET /api/v1/download/status/{sample_id}` - Statut
   - `GET /api/v1/download/logs/{sample_id}` - Logs avec pagination
   - `POST /api/v1/download/cleanup` - Nettoyage

5. **`qc-dashboard/api/app/api_v1/endpoints/uploads.py`**
   - `process_aws_run_background()` rendue async
   - Streaming ligne par ligne du script AWS
   - Émission des logs via WebSocket
   - Intégration avec `ensure_references()`

6. **`qc-dashboard/api/tasks/process_run.py`**
   - Ajout de `ensure_references()` dans `process_happy()`
   - Ajout de `ensure_references()` dans `process_truvari()`
   - Logging amélioré

### Frontend

7. **`qc-dashboard/dash_app/pages/runs.py`**
   - Composant `aws-logs-console` avec style terminal
   - Callback `poll_logs()` pour récupérer les logs
   - Callback `launch_aws_import()` modifié pour initialiser le polling
   - Stores Dash pour tracking: `log-index-store`, `current-sample-id`
   - Interval Dash: `log-poll-interval` (2s)

### Documentation

8. **`INTEGRATION_TEST.md`** (nouveau)
   - Guide de test complet
   - Flux détaillé
   - Exemples de tests manuels
   - Dépannage

9. **`AWS_DOWNLOAD_INTEGRATION.md`** (ce fichier)
   - Vue d'ensemble de l'intégration
   - Résumé des modifications

## Utilisation

### Interface utilisateur

1. Naviguer vers `http://localhost:8000/runs`
2. Onglet "Upload Run"
3. Section "Import from AWS S3"
4. Entrer le Sample ID (ex: `NA24143_Lib3_Rep1`)
5. Sélectionner les options de benchmarking
6. Cliquer "Import from AWS"
7. Observer les logs en temps réel dans la console

### API directe

```bash
# Lancer un téléchargement
curl -X POST http://localhost:8000/api/v1/upload/aws \
  -H "Content-Type: application/json" \
  -d '{
    "sample_id": "NA24143_Lib3_Rep1",
    "benchmarking": "csv,truvari",
    "auto_process": true
  }'

# Vérifier le statut
curl http://localhost:8000/api/v1/download/status/NA24143_Lib3_Rep1

# Récupérer les logs
curl http://localhost:8000/api/v1/download/logs/NA24143_Lib3_Rep1?since=0
```

## Flux complet

```
1. Utilisateur clique "Import from AWS"
   ↓
2. API lance process_aws_run_background() en arrière-plan
   ↓
3. Script aws_download_gvcf.sh s'exécute
   → Logs streamés ligne par ligne
   → Émis via WebSocket et stockés en mémoire
   ↓
4. Téléchargement terminé → Vérification des références
   → ensure_references(sample) appelé
   → Si GIAB sample et références manquantes:
     → setup_reference.sh télécharge automatiquement
   ↓
5. Lancement du pipeline de benchmarking
   → process_happy() si activé
   → process_truvari() si activé
   → process_csv_files() si activé
   ↓
6. Logs de fin: "✅ Process completed successfully!"
   → Polling s'arrête automatiquement
```

## Niveaux de logs

- **info** (gris): Messages informatifs généraux
- **success** (vert): Opérations réussies
- **warning** (jaune): Avertissements non-bloquants
- **error** (rouge): Erreurs bloquantes
- **progress** (bleu): Indicateurs de progression

## États du processus

- **pending**: En attente de démarrage
- **running**: En cours d'exécution
- **completed**: Terminé avec succès
- **error**: Erreur fatale

## Samples GIAB supportés

Le téléchargement automatique des références fonctionne pour :

- NA12878 / HG001
- NA24385 / HG002
- NA24149 / HG003
- **NA24143 / HG004**
- NA24631 / HG005
- NA24694 / HG006
- NA24695 / HG007

Pour les samples non-GIAB, les références doivent être fournies manuellement dans:
```
data/reference/{sample}/
  ├── {sample}_truth.vcf.gz
  ├── {sample}_confident_regions.bed
  └── stvar/
      ├── {sample}_sv_truth.vcf.gz
      └── {sample}_sv_confident_regions.bed
```

## Configuration

### Paramètres ajustables

**Dans `qc-dashboard/api/app/websocket.py`:**
```python
LOG_RETENTION_HOURS = 1  # Rétention des logs en mémoire
```

**Dans `qc-dashboard/dash_app/pages/runs.py`:**
```python
interval=2000  # Intervalle de polling en millisecondes
```

**Dans `qc-dashboard/api/app/api_v1/endpoints/uploads.py`:**
```python
env={"AWS_PROFILE": "vitalite"}  # Profil AWS à utiliser
```

## Limitations actuelles

1. **Logs en mémoire**: Les logs sont stockés en RAM, pas en DB
   - Perdus au redémarrage du serveur
   - Limitée à 1h de rétention
   
2. **Pas de parallélisation**: Un seul téléchargement par `sample_id` à la fois

3. **WebSocket non authentifié**: Pas de sécurité sur la connexion WS

4. **Pas de notification**: Pas d'email/Slack à la fin du processus

## Améliorations futures possibles

1. Persistance des logs dans PostgreSQL
2. Authentification WebSocket (JWT)
3. File d'attente avec Celery pour les téléchargements
4. Barre de progression visuelle (%)
5. Notifications email/Slack
6. Export des logs en fichier
7. Historique des téléchargements dans l'interface
8. Annulation manuelle d'un téléchargement en cours

## Support

Pour les problèmes ou questions:
- Consulter `INTEGRATION_TEST.md` pour les tests et le dépannage
- Vérifier les logs du serveur uvicorn
- Consulter la console navigateur (F12) pour les erreurs frontend

