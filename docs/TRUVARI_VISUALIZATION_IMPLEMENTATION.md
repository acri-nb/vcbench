# 📊 Implémentation de la Visualisation Truvari

## ✅ Statut: COMPLET

Date: 2025-11-13
Auteur: AI Assistant

---

## 🎯 Objectif

Implémenter la visualisation des résultats de benchmarking Truvari (variants structuraux) dans l'interface web du QC Dashboard.

## 📋 Composants Implémentés

### 1. Parser Truvari (`api/tasks/parsers.py`)

**Fonction:** `parse_truvari_summary(summary_json_path: Path) -> Optional[Dict]`

Parse le fichier `summary.json` généré par Truvari et extrait les métriques clés :

```python
metrics = {
    'tp_base': int,      # True Positives (référence)
    'tp_comp': int,      # True Positives (query)
    'fp': int,           # False Positives
    'fn': int,           # False Negatives
    'precision': float,  # Précision
    'recall': float,     # Rappel/Sensibilité
    'f1': float,         # Score F1
    'base_cnt': int,     # Total variants référence
    'comp_cnt': int,     # Total variants query
    'gt_concordance': float,  # Concordance génotypique
    # ... et autres métriques de genotype
}
```

### 2. Modèle de Base de Données (`api/app/models.py`)

**Table:** `truvari_metrics`

```sql
CREATE TABLE truvari_metrics (
    id SERIAL PRIMARY KEY,
    tp_base INTEGER NOT NULL,
    tp_comp INTEGER NOT NULL,
    fp INTEGER NOT NULL,
    fn INTEGER NOT NULL,
    precision FLOAT NOT NULL,
    recall FLOAT NOT NULL,
    f1 FLOAT NOT NULL,
    base_cnt INTEGER NOT NULL,
    comp_cnt INTEGER NOT NULL,
    gt_concordance FLOAT NOT NULL,
    tp_comp_tp_gt INTEGER NOT NULL,
    tp_comp_fp_gt INTEGER NOT NULL,
    tp_base_tp_gt INTEGER NOT NULL,
    tp_base_fp_gt INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    run_id INTEGER NOT NULL REFERENCES lab_runs(id),
    CONSTRAINT unique_run_truvari UNIQUE (run_id)
);
```

**Relations:**
- `LabRun.truvari_metrics` → One-to-Many relationship

### 3. Schémas Pydantic (`api/app/schemas.py`)

**Classes:**
- `TruvariMetricBase`: Champs de base
- `TruvariMetricCreate`: Pour création (inclut `run_id`)
- `TruvariMetricResponse`: Pour réponses API (inclut `id`, `created_at`)

### 4. Fonctions CRUD (`api/app/crud.py`)

**Fonctions:**
- `create_truvari_metric(db, truvari_metric)` - Créer une métrique
- `get_truvari_metrics(db, run_id)` - Obtenir toutes les métriques d'un run
- `get_truvari_metric_by_run_name(db, run_name)` - Obtenir par nom de run
- `delete_truvari_metric(db, metric_id)` - Supprimer une métrique

### 5. Intégration Pipeline (`api/tasks/process_run.py`)

**Fonction:** `post_truvari_metrics(sample, run, summary_json_path)`

Appelée automatiquement après l'exécution de Truvari :

```python
def process_truvari(sample, run):
    # ... (code existant pour exécuter Truvari)
    
    # Parse and store Truvari metrics
    summary_json = output_path / 'truvari' / 'summary.json'
    if summary_json.exists():
        post_truvari_metrics(sample, run, summary_json)
```

Workflow:
1. Parse `summary.json`
2. Récupère `run_id` depuis la base de données
3. Valide les données avec Pydantic
4. POST vers l'API `/api/v1/runs/{run_name}/truvari_metrics`

### 6. Endpoints API (`api/app/api_v1/endpoints/truvari_metrics.py`)

**Routes:**

```python
POST   /api/v1/runs/{run_name}/truvari_metrics
  → Store Truvari metrics for a run
  
GET    /api/v1/runs/{run_name}/truvari_metrics
  → Get Truvari metrics for a run
  
GET    /api/v1/runs/{run_id}/truvari_metrics/all
  → Get all Truvari metrics for a run ID
```

**Enregistrement:** Ajouté dans `api/app/main.py`

### 7. Page Dash de Visualisation (`dash_app/pages/truvari.py`)

**URL:** `http://localhost:8000/truvari`

**Fonctionnalités:**

1. **Sélecteur de Run**
   - Dropdown listant uniquement les runs avec résultats Truvari
   - Filtrage automatique via l'API

2. **Cartes de Métriques**
   - **Precision** (Bleu) - TP / (TP + FP)
   - **Recall** (Vert) - TP / (TP + FN)
   - **F1 Score** (Violet) - Moyenne harmonique
   - **GT Concordance** (Orange) - Concordance génotypique

3. **Visualisations Interactives**
   - **Diagramme Sankey**: Flow des classifications de variants
   - **Bar Chart Groupé**: Comparaison Base vs Comp
   - **Bar Chart Empilé**: Breakdown de concordance génotypique

4. **Tableau Détaillé**
   - Toutes les métriques avec formatage
   - Lignes alternées pour lisibilité
   - Valeurs numériques formatées avec séparateurs

### 8. Migrations Database (`qc-dashboard/migrations/`)

**Fichiers:**
- `001_add_truvari_metrics.sql` - Migration SQL
- `apply_migration.py` - Script Python pour appliquer les migrations
- `README.md` - Guide d'utilisation
- `../init_db.py` - Script d'initialisation complète de la BD

**Application:**

```bash
# Option 1: Via Python (nécessite psycopg2)
python3 qc-dashboard/init_db.py

# Option 2: Via Docker
docker exec -i wgs_db psql -U wgs_user -d wgs < qc-dashboard/migrations/001_add_truvari_metrics.sql

# Option 3: SQLAlchemy auto-create
# La table sera créée automatiquement au démarrage de l'app
```

---

## 🔄 Workflow Complet

### 1. Exécution de Truvari

```bash
# Via l'interface web: http://localhost:8000/runs
# → Sélectionner un run
# → Cocher "truvari"
# → Cliquer "Launch Selected Benchmarking"
```

### 2. Traitement Automatique

```
process_truvari()
  ↓
Exécution Docker Truvari
  ↓
Génération de summary.json
  ↓
parse_truvari_summary()
  ↓
post_truvari_metrics()
  ↓
Validation Pydantic
  ↓
POST /api/v1/runs/{run_name}/truvari_metrics
  ↓
Stockage en base de données ✅
```

### 3. Visualisation

```
Utilisateur → http://localhost:8000/truvari
  ↓
Sélection du run dans dropdown
  ↓
GET /api/v1/runs/{run_name}/truvari_metrics
  ↓
Affichage des cartes + graphiques + tableau
```

---

## 📊 Exemple de Données Visualisées

Pour le run `NA24143_Lib3_Rep1_R001` (avec référence HG002 temporaire) :

```
┌─────────────────────────────────────────────────┐
│  Precision: 3.66%  │  Recall: 3.24%             │
│  F1 Score: 0.0344  │  GT Concordance: 70.51%    │
└─────────────────────────────────────────────────┘

Variant Counts:
  Base Total:  9,641
  Comp Total:  8,524
  TP (Base):     312
  TP (Comp):     312
  FP:          8,212
  FN:          9,329

Genotype Concordance:
  TP-base correct GT:  220
  TP-base incorrect GT: 92
  TP-comp correct GT:  220
  TP-comp incorrect GT: 92
```

**Note:** Ces faibles métriques sont normales car NA24143 (HG004) est comparé à HG002 (individus différents).

---

## 🚀 Utilisation

### Première Fois

1. **Initialiser la base de données :**
   ```bash
   cd /mnt/acri4_2/gth/project/vcbench/qc-dashboard
   python3 init_db.py
   ```

2. **Vérifier que la table existe :**
   ```sql
   psql -U wgs_user -d wgs -h localhost -p 5433
   \dt truvari_metrics
   \d truvari_metrics
   ```

### Exécuter Truvari

1. Aller sur http://localhost:8000/runs
2. Sélectionner un run avec des fichiers `.sv.vcf.gz`
3. Cocher "truvari" dans les options de benchmarking
4. Cliquer "Launch Selected Benchmarking"
5. Attendre la complétion (logs visibles)

### Visualiser les Résultats

1. Aller sur http://localhost:8000/truvari
2. Sélectionner le run dans le dropdown
3. Explorer les métriques, graphiques et tableau

---

## 🧪 Test de l'Implémentation

### Test 1: Vérifier le Parser

```python
from pathlib import Path
from api.tasks.parsers import parse_truvari_summary

summary_path = Path("/mnt/acri4_2/gth/project/vcbench/data/processed/NA24143_Lib3_Rep1_R001/truvari/summary.json")
metrics = parse_truvari_summary(summary_path)
print(metrics)
```

### Test 2: Tester l'API

```bash
# Obtenir les métriques d'un run
curl http://localhost:8000/api/v1/runs/NA24143_Lib3_Rep1_R001/truvari_metrics

# Réponse attendue: JSON avec toutes les métriques
```

### Test 3: Vérifier la Base de Données

```sql
SELECT * FROM truvari_metrics;
SELECT run_name, precision, recall, f1 
FROM truvari_metrics 
JOIN lab_runs ON truvari_metrics.run_id = lab_runs.id;
```

---

## 📝 Fichiers Modifiés/Créés

### Modifiés
1. `api/tasks/parsers.py` - Ajout `parse_truvari_summary()`
2. `api/tasks/process_run.py` - Ajout `post_truvari_metrics()`
3. `api/app/models.py` - Ajout classe `TruvariMetric`
4. `api/app/schemas.py` - Ajout schémas Truvari
5. `api/app/crud.py` - Ajout fonctions CRUD Truvari
6. `api/app/main.py` - Enregistrement du router Truvari

### Créés
1. `api/app/api_v1/endpoints/truvari_metrics.py` - Nouveau endpoint
2. `dash_app/pages/truvari.py` - Nouvelle page Dash
3. `migrations/001_add_truvari_metrics.sql` - Migration SQL
4. `migrations/apply_migration.py` - Script de migration
5. `migrations/README.md` - Guide de migration
6. `init_db.py` - Script d'initialisation DB
7. `docs/TRUVARI_VISUALIZATION_IMPLEMENTATION.md` - Cette doc

---

## 🐛 Dépannage

### Problème: Table truvari_metrics n'existe pas

```bash
# Solution: Initialiser la base de données
python3 qc-dashboard/init_db.py
```

### Problème: Pas de métriques affichées

```bash
# Vérifier si Truvari s'est exécuté
ls -la data/processed/*/truvari/summary.json

# Vérifier si les métriques sont en BD
psql -U wgs_user -d wgs -h localhost -p 5433 -c "SELECT * FROM truvari_metrics;"

# Re-lancer le benchmarking Truvari si nécessaire
```

### Problème: Page /truvari vide

1. Vérifier que l'API répond :
   ```bash
   curl http://localhost:8000/api/v1/runs
   ```

2. Vérifier les logs du serveur FastAPI/Dash

3. Vérifier la console du navigateur (F12)

---

## 🎓 Concepts Truvari

### Métriques Principales

- **TP (True Positives)** : Variants trouvés dans référence ET query
- **FP (False Positives)** : Variants dans query mais PAS dans référence
- **FN (False Negatives)** : Variants dans référence mais PAS trouvés dans query

### Formules

```
Precision = TP / (TP + FP)  [Combien de nos appels sont corrects]
Recall    = TP / (TP + FN)  [Combien de vrais variants avons-nous trouvés]
F1 Score  = 2 × (Precision × Recall) / (Precision + Recall)
```

### Concordance Génotypique

Pour les variants qui matchent (TP), Truvari vérifie aussi si le **génotype** est correct :
- `0/1` vs `0/1` → Correct
- `1/1` vs `1/1` → Correct
- `0/1` vs `1/1` → Incorrect (match de position mais génotype différent)

---

## 📚 Références

- **Truvari Documentation**: https://github.com/ACEnglish/truvari
- **Structural Variants**: https://en.wikipedia.org/wiki/Structural_variation
- **GIAB Samples**: https://www.nist.gov/programs-projects/genome-bottle
- **FastAPI**: https://fastapi.tiangolo.com/
- **Plotly Dash**: https://dash.plotly.com/

---

## ✅ Checklist de Validation

- [x] Parser Truvari fonctionne
- [x] Modèle de BD créé et testé
- [x] Schémas Pydantic validés
- [x] Fonctions CRUD opérationnelles
- [x] Intégration dans process_truvari()
- [x] Endpoints API créés et testés
- [x] Page Dash créée avec visualisations
- [x] Migration SQL prête
- [x] Documentation complète
- [x] Pas d'erreurs de linting

---

**Status:** ✅ **PRÊT POUR PRODUCTION**

L'implémentation est complète et fonctionnelle. Les résultats Truvari sont maintenant automatiquement parsés, stockés et visualisés dans l'interface web !

