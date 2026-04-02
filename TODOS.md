# SCIPHR — TODOS

Items considered and explicitly deferred. Each entry has enough context to
be actionable in 3 months without re-deriving the motivation.

---

## TODO-01 — Alembic migration versioning

**What:** Set up Alembic for schema version control in `backend/db/migrations/`.

**Why:** Phase 1 uses `Base.metadata.create_all(engine)` to create the schema,
which cannot be rolled back and can't be incrementally applied to an existing
database. Before the Phase 6 Supabase production deploy, any schema change
(adding a column, adding an index) requires manual SQL or wiping the DB.

**Pros:**
- Schema changes are versioned, reviewable, and reversible.
- `alembic upgrade head` is a single command for deploy pipelines.
- Supabase has Alembic integration guides that make Phase 6 deploy cleaner.

**Cons:**
- ~30 min of setup: `alembic init`, edit `env.py` to import `Base`, generate
  initial migration with `alembic revision --autogenerate -m "Phase 1 schema"`.
- Adds `alembic` to requirements.txt.

**Current state:** Schema defined in `backend/db/models.py`. Tables are
created by `backend/scripts/migrate_csv.py` via `create_all()`. Migration
files directory `backend/db/migrations/` doesn't exist yet.

**Where to start:**
```
cd backend
pip install alembic
alembic init db/migrations
# Edit db/migrations/env.py to import Base from db.models
alembic revision --autogenerate -m "Phase 1 initial schema"
alembic upgrade head
```

**Depends on / blocked by:** Nothing. Can be done any time after Phase 1.
Should be done before Phase 6 deploy.
