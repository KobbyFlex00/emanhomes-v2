# Operations guide

How to keep emanhomes.com healthy: alerts, monitoring, backups and recovery.

## Error alerts

When the live site hits an unexpected server error (HTTP 500), Django emails the details to the addresses in `ADMIN_EMAILS`. If that is not set, it uses `LEAD_NOTIFICATION_EMAIL`. The email subject starts with `[EmanHomes] ERROR`.

- "Page not found" (404) responses are not emailed. They appear in the Render logs only.
- Alerts are sent through the same Gmail account as enquiry notifications. If Gmail itself is failing, check the Render logs instead.
- Staging uses the prefix `[EmanHomes staging]`, so its alerts are easy to tell apart.

**What to do with an alert:** open the service's **Logs** in Render around the time in the email and look for the matching traceback. One-off errors can be noted and fixed in the next release. Repeated errors on the same page need a fix straight away.

## Uptime monitoring (recommended)

Render restarts the app when `/healthz/` stops responding, but it does not tell you. Set up a free external monitor:

1. Create a free account at a monitoring service such as UptimeRobot or Better Stack.
2. Add an HTTP monitor for `https://emanhomes.com/healthz/`, checking every 5 minutes.
3. Expect status `200` and the text `"ok"`.
4. Send alerts to the company email or phone.

`/healthz/` checks both the web server and the database connection.

## Database backups

**Check in Render now:** open the production PostgreSQL database and confirm:

1. **Plan:** it must be a paid plan. Free Render databases expire and have no backups.
2. **Backups / Recovery tab:** paid plans include automatic daily backups and point-in-time recovery. Note how many days are kept.

**Before every release that includes a database migration** (the PR description says so), take a manual export:

```bash
# Use the database's "External Database URL" from Render (keep it private).
pg_dump --no-owner --format=custom "$EXTERNAL_DATABASE_URL" > emanhomes-$(date +%Y%m%d-%H%M).dump
```

Store the file somewhere private and access-controlled, for example the company Google Drive. Never put it in the code repository.

**Test a restore at least once**, into a new empty database such as the staging one, never production:

```bash
pg_restore --no-owner --clean --if-exists --dbname "$STAGING_EXTERNAL_DATABASE_URL" emanhomes-YYYYMMDD-HHMM.dump
```

## Media (listing photos)

Listing photos are stored in Cloudinary, not on Render. They survive redeploys and are not part of the database backup. Cloudinary keeps uploaded files until they are deleted. Keep the original photos as well (for example in Google Drive) in case a file is deleted by mistake.

After changing `CLOUDINARY_URL`, run `python manage.py check_media_storage` in the Render Shell.

## Rolling back a bad release

1. In Render, open the production service → **Events**, then choose the previous successful deploy → **Rollback**.
2. If the bad release included a migration, check whether the previous code can run against the new schema. Our migrations only add columns with database defaults, so it normally can. If the database itself needs restoring, use Render's point-in-time recovery or the manual dump above.
3. Fix the problem on a branch and release it through staging as usual.

## Search engines

- `SITE_URL` (default `https://emanhomes.com`) is used for canonical links, share previews and structured data.
- Any `*.onrender.com` address, and any deployment with `SITE_NOINDEX=true`, is marked noindex and its `robots.txt` disallows crawling. Only the real domain appears in Google.
- Google Search Console is verified with the HTML-tag method. The code is the default for `GOOGLE_SITE_VERIFICATION` in settings. If Google issues a new code, set that variable on the production service in Render. Do not remove the tag, because Google re-checks it.
- Submit `https://emanhomes.com/sitemap.xml` in Google Search Console once, then check it there occasionally.
