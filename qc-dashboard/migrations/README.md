# Database Migrations

This directory contains SQL migrations for the VCBench QC Dashboard database.

## Available Migrations

### 001_add_truvari_metrics.sql
Creates the `truvari_metrics` table for storing Truvari structural variant benchmarking results.

**Table Schema:**
- Stores TP (True Positives), FP (False Positives), FN (False Negatives)
- Performance metrics: Precision, Recall, F1 Score
- Genotype concordance metrics
- Linked to `lab_runs` table via foreign key

## How to Apply Migrations

### Option 1: Using the Python script (requires psycopg2)
```bash
cd /mnt/acri4_2/gth/project/vcbench/qc-dashboard
python3 migrations/apply_migration.py
```

### Option 2: Manual SQL execution
```bash
# Connect to PostgreSQL
psql -U wgs_user -d wgs -h localhost -p 5433

# Apply the migration
\i /mnt/acri4_2/gth/project/vcbench/qc-dashboard/migrations/001_add_truvari_metrics.sql
```

### Option 3: Using Docker (if database is in Docker)
```bash
cd /mnt/acri4_2/gth/project/vcbench
docker exec -i wgs_db psql -U wgs_user -d wgs < qc-dashboard/migrations/001_add_truvari_metrics.sql
```

### Option 4: Using SQLAlchemy (automatic on app startup)
The table will be automatically created when you start the FastAPI application if `Base.metadata.create_all(engine)` is called in `database.py`.

## Verify Migration

After applying the migration, verify the table was created:

```sql
-- Check if table exists
SELECT table_name 
FROM information_schema.tables 
WHERE table_name = 'truvari_metrics';

-- Check table structure
\d truvari_metrics

-- Verify no data yet
SELECT COUNT(*) FROM truvari_metrics;
```

## Rollback

To rollback this migration:

```sql
DROP TABLE IF EXISTS truvari_metrics CASCADE;
```

## Notes

- The `truvari_metrics` table has a `UNIQUE` constraint on `run_id` (one Truvari result per run)
- All metrics are `NOT NULL` to ensure data integrity
- Foreign key constraint ensures referential integrity with `lab_runs` table
- Indexes are created for performance optimization

