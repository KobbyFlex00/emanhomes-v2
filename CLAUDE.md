# Eman Homes repository guidance

## Project

This is the production Django application for Eman Homes Limited GH. The live Render service tracks `main`.

## Branches

- `main`: production. Render auto-deploys every push.
- `staging`: Render staging service (`render.staging.yaml`).
- Work happens on `feature/*` or `hotfix/*`, merges into `staging`, and reaches `main` only after staging sign-off.

The Phase 0 audit and open risks are tracked in `docs/architecture-audit.md`.

## Safety

- Preserve the existing `core` models, migrations, admin workflows, and templates unless a migration plan is reviewed.
- Never reset, drop, or replace the production database.
- Keep staging on a separate Render service and PostgreSQL database.
- Keep secrets in Render environment variables; never commit `.env` files, SMTP credentials, database URLs, or Cloudinary secrets.
- Do not invent property records, prices, addresses, testimonials, legal claims, or contact details.

## Validation

Before proposing a merge:

```powershell
$env:SECRET_KEY = "local-test-secret"
$env:DEBUG = "true"
$env:ALLOWED_HOSTS = "localhost,127.0.0.1"
python manage.py check
python manage.py test
```

Review migrations and run `git diff --check`. Production deployment requires staging verification, a database backup, and an explicit promotion decision.
