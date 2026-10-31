# Next-generation database migrations

This migration stream is intentionally independent from the legacy database.

- Target: `NEXT_DATABASE_URL` only.
- Config: `alembic-next.ini`.
- Metadata: `app.db.nextgen.base.NextBase`.
- Initial revision `ng_0001` creates schema only; it inserts **zero rows**.
- Never point `NEXT_DATABASE_URL` at the legacy database.

Run only after provisioning a separate, empty PostgreSQL database:

```bash
alembic -c alembic-next.ini upgrade head
```

Inspect pending SQL first when operating on a hosted environment:

```bash
alembic -c alembic-next.ini upgrade head --sql
```

The application does not run these migrations at startup. The existing `DATABASE_URL`, legacy metadata, Alembic history, and startup behavior remain separate.
