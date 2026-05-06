# VCBench Database Migrations

Run migrations from the `qc-dashboard` directory:

```bash
alembic upgrade head
```

The migration environment reads `DATABASE_URL` from `api.app.settings`.
The URL in `alembic.ini` is only a fallback for Alembic tooling.

The initial migration is intentionally tolerant of an existing PostgreSQL
database: it creates missing tables and adds the run status columns that older
local databases may not have. The second migration adds `truvari_metrics` and
also no-ops if that table already exists from the previous SQL-only migration.
