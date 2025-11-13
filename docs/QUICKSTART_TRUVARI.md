# 🚀 Guide de Démarrage Rapide - Visualisation Truvari

## ⚡ Mise en Route (5 minutes)

### Étape 1: Initialiser la Base de Données

```bash
cd /mnt/acri4_2/gth/project/vcbench/qc-dashboard
python3 init_db.py
```

**Résultat attendu:**
```
Initializing database...
Database URL: postgresql+psycopg2://wgs_user:password@localhost:5433/wgs

✅ Database initialized successfully!

Created tables:
  - users
  - lab_runs
  - qc_metrics
  - happy_metrics
  - truvari_metrics  ← Nouvelle table !
```

### Étape 2: Redémarrer l'Application (si nécessaire)

```bash
# Si l'app tourne déjà, pas besoin de redémarrer !
# La nouvelle page /truvari est automatiquement détectée par Dash

# Sinon, démarrer l'app:
cd /mnt/acri4_2/gth/project/vcbench/qc-dashboard
uvicorn api.app.main:app --reload --port 8000
```

### Étape 3: Lancer un Benchmarking Truvari

1. **Ouvrir:** http://localhost:8000/runs
2. **Sélectionner:** `NA24143_Lib3_Rep1_R001` (ou un autre run avec fichier `.sv.vcf.gz`)
3. **Cocher:** ☑️ `truvari` (Structural variant benchmarking)
4. **Cliquer:** `Launch Selected Benchmarking`
5. **Attendre:** ~30 secondes (dépend de la taille des fichiers)

**Vous verrez:**
```
Processing truvari...
Filtering VCFs...
Normalizing chromosomes...
Running Truvari bench...
✅ Successfully processed truvari
Parsing Truvari summary...
✅ Successfully posted Truvari metric
```

### Étape 4: Visualiser les Résultats

1. **Ouvrir:** http://localhost:8000/truvari
2. **Sélectionner le run** dans le dropdown
3. **Explorer** les métriques, graphiques et tableau !

---

## 📊 Ce que Vous Verrez

### Cartes de Métriques
```
┌──────────────┬──────────────┬──────────────┬──────────────┐
│  Precision   │   Recall     │  F1 Score    │ GT Concord.  │
│    3.66%     │    3.24%     │   0.0344     │   70.51%     │
│ TP/(TP+FP)   │ TP/(TP+FN)   │ Harmonic Mean│ GT Accuracy  │
└──────────────┴──────────────┴──────────────┴──────────────┘
```

### Graphiques Interactifs
- **Sankey Diagram:** Flow de classification des variants
- **Bar Chart:** Comparaison Base vs Query
- **Stacked Bar:** Concordance génotypique

### Tableau Détaillé
Toutes les métriques avec formatage professionnel

---

## 🎯 Exemple Complet pour NA24143

```bash
# 1. Vérifier que les fichiers existent
ls -lh /mnt/acri4_2/gth/project/vcbench/data/lab_runs/NA24143_Lib3_Rep1_R001/*.sv.vcf.gz
# ✅ NA24143_Lib3_Rep1_R001.dragen.sv.vcf.gz (4.5 MB)

ls -lh /mnt/acri4_2/gth/project/vcbench/data/reference/NA24143/stvar/
# ✅ NA24143_sv_truth.vcf.gz (25 MB)
# ✅ NA24143_sv_confident_regions.bed (726 KB)

# 2. Lancer depuis l'interface web (Étape 3 ci-dessus)

# 3. Vérifier que les métriques sont en BD
psql -U wgs_user -d wgs -h localhost -p 5433 -c \
  "SELECT run_name, precision, recall, f1 FROM truvari_metrics 
   JOIN lab_runs ON truvari_metrics.run_id = lab_runs.id;"

# Résultat:
          run_name          | precision | recall  |    f1    
----------------------------+-----------+---------+----------
 NA24143_Lib3_Rep1_R001     | 0.0366025 | 0.03236 | 0.034352
```

---

## ❓ FAQ

### Q: Pourquoi les métriques sont-elles si faibles pour NA24143 ?
**R:** NA24143 (HG004) est comparé à la référence HG002 (individus différents). C'est **normal** ! Pour des métriques valides, utiliser HG002 vs HG002.

### Q: Comment tester avec de vraies données valides ?
**R:** Télécharger un run HG002 (NA24385) depuis AWS et le comparer à la référence HG002.

### Q: La page /truvari ne montre aucun run ?
**R:** Seuls les runs avec `truvari=True` dans `/api/v1/runs/{run_name}/benchmarking` apparaissent. Lancez d'abord un benchmarking Truvari !

### Q: Les graphiques ne s'affichent pas ?
**R:** Vérifier la console navigateur (F12) et les logs serveur. Problème courant : API non accessible.

---

## 🔧 Commandes Utiles

```bash
# Vérifier les résultats Truvari bruts
cat /mnt/acri4_2/gth/project/vcbench/data/processed/NA24143_Lib3_Rep1_R001/truvari/summary.json | python3 -m json.tool

# Vérifier la BD
psql -U wgs_user -d wgs -h localhost -p 5433
\dt truvari_metrics
SELECT * FROM truvari_metrics;

# Tester l'API
curl http://localhost:8000/api/v1/runs/NA24143_Lib3_Rep1_R001/truvari_metrics

# Vérifier les logs en temps réel
tail -f qc-dashboard/logs/*.log  # si logs activés
```

---

## 🎉 C'est Tout !

Vous pouvez maintenant :
- ✅ Exécuter Truvari depuis l'interface web
- ✅ Stocker automatiquement les résultats en BD
- ✅ Visualiser les métriques avec des graphiques interactifs
- ✅ Comparer différents runs facilement

**Profitez de votre nouvelle visualisation Truvari ! 🚀**

