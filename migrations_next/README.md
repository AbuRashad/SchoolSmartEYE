# Next-generation database migrations

This migration stream is intentionally independent from the legacy database.

- Target: `NEXT_DATABASE_URL` only.
- Config: `alembic-next.ini`.
- Metadata: `app.db.nextgen.base.NextBase`.
- Initial revision `ng_0001` creates schema only; it inserts **zero rows**.
- The target must be a separately provisioned, empty PostgreSQL database.
- The migration environment rejects a target that resolves to the same host/database as `DATABASE_URL`.
- The initial migration refuses to run if user tables or existing Alembic history are present.
- The baseline downgrade is intentionally blocked to prevent accidental schema/data deletion.
- The application does not run these migrations at startup.

Run only after provisioning a new, empty PostgreSQL database:

```bash
alembic -c alembic-next.ini upgrade head
```

Inspect pending SQL first when operating on a hosted environment:

```bash
alembic -c alembic-next.ini upgrade head --sql
```

Never point `NEXT_DATABASE_URL` at the legacy database. Never commit database credentials. No legacy data copy, demo seeding, automatic dual-write, or production cutover is authorized by this migration stream.
