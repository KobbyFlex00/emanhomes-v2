# Eman Homes staging deployment

This repository is the source for the live Eman Homes website. Production Render currently follows the production branch, so the replacement must be tested separately before merging.

## Branch and service separation

- Staging branch: `staging` (long-lived; Render staging deploys it)
- Production branch: `main` (Render production deploys it)
- Work branches: `feature/*` or `hotfix/*`, merged into `staging` first, then `staging` into `main`
- Staging configuration: `render.staging.yaml`
- Staging database: `eman-homes-staging-db`

Do not connect the staging service to the production database or production Cloudinary folder. Route staging enquiry notifications to a test inbox.

## Render setup

1. In Render, create a Blueprint from `render.staging.yaml`, or create an equivalent web service manually.
2. Connect the existing `KobbyFlex00/emanhomes-v2` GitHub repository.
3. Select the `staging` branch.
4. Configure `ALLOWED_HOSTS` with the Render staging hostname and `CSRF_TRUSTED_ORIGINS` with its `https://` origin.
5. Add staging-only `CLOUDINARY_URL`, SMTP credentials, and `LEAD_NOTIFICATION_EMAIL`.
6. Deploy and verify `/`, `/properties/`, `/contact/`, `/sitemap.xml`, `/robots.txt`, and `/admin/`.

## Staging acceptance

- Add approved test properties through Admin; do not use fabricated production records.
- Verify property filters, gallery ordering, video fallback, related properties, and mobile layouts.
- Submit general and property-linked enquiries.
- Confirm each enquiry is saved in Admin and notification delivery works.
- Test a failed email configuration and confirm the saved enquiry is retained.
- Verify PostgreSQL migrations complete without deleting existing data.
- Check Cloudinary uploads and image rendering.

## Production promotion

Before merging to `main`:

1. Back up the production database.
2. Review every migration and the changed-file diff.
3. Record staging acceptance.
4. Confirm production environment variables and Render build/start commands.
5. Merge `staging` into `main` through the normal review process.
6. Monitor the deployment and retain the previous Render revision for rollback.

Never reset the production database, replace the production database with staging data, or commit secrets.
