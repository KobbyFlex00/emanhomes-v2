# Architecture audit — Phase 0

**Date:** 2026-10-15
**Scope:** `emanhomes-v2` repository (branch `main`, HEAD `f91d4d4`), compared against the spec pack (`01_PRD.md` – `07_DESIGN.md`).
**Method:** read-only inspection, plus `manage.py check`, `makemigrations --check` and `manage.py test` against a throwaway test database. No source code, migrations or databases were modified.

---

## 1. Current architecture

| Layer | What exists |
|---|---|
| Rendering | Server-rendered Django templates (`templates/core/*.html`), Bootstrap 5.3.0 + Font Awesome 6.4.0 via CDN, a little custom JS/CSS in `static/` |
| Backend | Django 5.1.5 (pinned), single app `core`. An empty `users` app exists but is **not** in `INSTALLED_APPS` |
| API | **None.** No DRF, no `/api/` routes |
| Database | PostgreSQL via `DATABASE_URL` in production; SQLite locally |
| Media | Intended: Cloudinary. Actual: local filesystem (see R1) |
| Static | WhiteNoise `CompressedStaticFilesStorage` |
| Hosting | Render web service tracking `main`; `render.staging.yaml` Blueprint for staging |
| Email | Gmail SMTP, credentials from env |
| Analytics | Optional GA4 via `ANALYTICS_MEASUREMENT_ID`, `data-analytics-event` attributes |
| CI | GitHub Actions: `check --deploy`, `makemigrations --check`, `test`, `collectstatic` |

**Recommendation:** keep the Django-template architecture (TRD §1: "retain Django templates unless there is a concrete requirement to split the frontend"). Nothing in the PRD needs a separate SPA. Add DRF only for the endpoints the TRD lists, as a read-only public layer next to the templates, not as a replacement for them.

## 2. Existing routes

| Path | View | Notes |
|---|---|---|
| `/` | `home` | Hero search, category tiles, 6 listings, trust panel |
| `/about/` | `about` | Static copy + `TeamMember` list |
| `/properties/` | `properties_list` | `q`, `category`, `status`, `min_price`, `max_price`, `bedrooms`; 9 per page |
| `/property/<slug>/` | `property_detail` | Gallery, video, mortgage calculator, WhatsApp/phone, 3 related |
| `/contact/` | `contact` | GET/POST; `?property=<slug>`, `?type=listing` |
| `/sitemap.xml` | Django sitemaps | Static pages + **all** properties |
| `/robots.txt` | inline lambda | |
| `/admin/` | Django Admin | |

Missing from the PRD page list: land, houses and rentals landing pages (these can be filtered views), services, projects, blog/articles, enquiry success page, privacy policy, terms, and custom 404/500 templates. `templates/core/mortgage_calculator.html` is not rendered by any view.

## 3. Existing data models (`core`)

- **SiteConfiguration**: name, main/secondary/WhatsApp phone, email, address, Facebook/Instagram/Twitter/LinkedIn. Admin blocks a second row. No TikTok, Linktree, YouTube, SEO defaults or `updated_at`.
- **Property**: title, slug, `reference_number` (auto `EH-xxxxxxxxxx`), `category` (land/residential/commercial, a choice field rather than an FK), `status` (for_sale/for_rent/sold), `is_featured`, `currency` (USD/GHS, default USD), `price` (**required**), `location` (free text), description, size and unit, amenities (newline text), bedrooms and bathrooms (default 0), `main_image`, `video_url`, `created_at`. No `updated_at`, no publication state, no SEO fields.
- **PropertyImage**: FK to property, image, caption, `display_order`. No alt text and no cover flag.
- **ContactMessage** (the enquiry): name, email, subject, message, `inquiry_type` (general/property/viewing/listing), `preferred_contact`, property FK (SET_NULL), `source`, `consent_to_contact`, `lead_status` (new/in_progress/qualified/closed), `follow_up_at`, `internal_notes`, `created_at`. **No phone field.**
- **Service**: title, description, Font Awesome icon class.
- **TeamMember**: name, role, bio, `image_url`.

There are 11 migrations, all in `core`, and they are consistent (`makemigrations --check` reports no changes).

## 4. Test and check results

```
python manage.py check                    → no issues
python manage.py makemigrations --check   → No changes detected
python manage.py test                     → Ran 5 tests, OK
```

The 5 tests cover keyword search, category and bedroom filtering, the consent requirement, saving an enquiry and sending its email, and linking an enquiry to a property. Nothing covers visibility rules, honeypot rejection, email-failure handling, the sitemap or admin permissions.

Note: the local environment has Django 5.2.18 installed, but `requirements.txt` pins 5.1.5, so production and CI install 5.1.5.

---

## 5. Risk list

Ordered by urgency. **Bold** items should be fixed before or alongside Phase 1.

### Critical / urgent

**R1. Media uploads are written to Render's ephemeral disk, not Cloudinary.**
`settings.py` defines `STORAGES['default'] = FileSystemStorage` (added in `4055da6`, 2026-10-13, now on `main`). `DEFAULT_FILE_STORAGE` was removed in Django 5.1, so the Cloudinary line is ignored. I confirmed at runtime that `default_storage` resolves to `FileSystemStorage` with `MEDIA_ROOT = ''`. On Render, any property image uploaded since this change will disappear on the next deploy or restart, and `/media/` is not served when `DEBUG=False`.
*Action:* set `STORAGES['default']` to `cloudinary_storage.storage.MediaCloudinaryStorage`. Then check in Admin and on the live site which existing image URLs do not start with `res.cloudinary.com`, and re-upload those.

**R2. A real `SECRET_KEY` was committed in the initial commit (`2607ddf`).**
It is still in git history (I have not printed the value). The README already says to rotate it.
*Action:* confirm that the production `SECRET_KEY` in Render differs from the historical value, and rotate it if it does not. Rewriting history is optional because the key is invalid once rotated.

**R3. No publication state. Every property is public, including sold ones.**
`Property.status` mixes availability with visibility. Nothing hides a draft or archived listing, and the sitemap lists every property. This conflicts with PRD §7 and APPFLOW §7.
*Action (Phase 2):* add a separate visibility field (`draft`/`published`/`archived`) with a data migration that sets **all existing rows to `published`**, so live listings do not vanish. Leave the existing `status` choices in place. Map sold/rented visibility after the company agrees a policy.

**R4. Staging is not isolated from production in branch terms.**
`render.staging.yaml` has `branch: main` (commit `f91d4d4`), while `docs/staging-deployment.md` says staging uses `feature/eman-homes-launch-integration`. Staging therefore cannot test a change before production receives it.
*Action:* point staging at an integration branch, or adopt a "merge to `staging` first" flow, and update the doc to match.

### High

**R5. A long `source` value can return a 500 error.** `contact()` sets `inquiry.source = request.POST.get('source', ...)` without validation. The column is `varchar(100)`, so PostgreSQL raises `DataError` on longer input. Validate it in the form instead.

**R6. The enquiry form has no phone field.** PRD §9 requires one, and phone/WhatsApp are the main contact channels.

**R7. Enquiry spam controls are weak.** The honeypot is a `HiddenInput`, which many bots skip. There is no rate limiting or throttling. `EMAIL_TIMEOUT` is unset, so a slow SMTP server can hang the request. Notification failures are logged but not recorded on the enquiry.

**R8. Contact details are not centralised and contain unconfirmed values.**
- The address "Dzen-Ayor, East Legon, Accra" is hard-coded as a template fallback in about 4 places. *Confirmed by Eman Homes on 2026-10-15 as the real office address;* keep it, but source it from `SiteConfiguration` only.
- The WhatsApp number is hard-coded in `property_detail.html:153`.
- The Facebook default is `facebook.com/emanhomes`, but the PRD's is `facebook.com/emanhomesofficial`.
- TikTok, X, LinkedIn and Linktree URLs are not modelled.
- "Available Mon-Fri, 8am - 5pm" on the contact page is an unconfirmed operating claim.

**R9. Outdated dependencies.** Django 5.1 is out of security support; move to 5.2 LTS. `gunicorn==21.2.0` has a known HTTP request-smuggling issue fixed in 22.x. Pillow, psycopg2-binary and dj-database-url are unpinned. *Action:* pin everything and upgrade to Django 5.2 LTS, gunicorn ≥ 23, and current whitenoise.

### Medium

**R10. Content that the spec forbids or needs confirmed:**
- Unsplash stock photos in the hero, category tiles and About page. The brief says no imagery that misrepresents listings, so label these as placeholders or replace them.
- "Meet the Experts" heading.
- "Premium Real Estate" in every `<title>`.
- "cleaning services" in the home copy, which is not in the PRD's services list.
- About-page tagline "Building Trust, Delivering Excellence". Confirm it or use the proposed draft.
- README describes a "Navy & Gold" theme, but the CSS uses navy `#0D2E59` and red `#D72638`. The spec's starting tokens are `#061A3A` and `#E60023`. Sample the real logo (`static/img/logo.jpeg`) before changing either.

**R11. "Contact for price" is impossible.** `price` is required and non-nullable, and bedrooms and bathrooms default to 0 rather than null. Making `price` nullable is a safe additive migration.

**R12. Arbitrary iframe source.** `get_embed_url()` falls back to returning any `video_url` unchanged into an iframe. This is staff-controlled, but it should be allow-listed to YouTube and Instagram.

**R13. SEO gaps.** There is no `updated_at` (sitemap `lastmod` uses `created_at`). The OG description is identical on every page. The canonical URL is built from the request host. There are no 404/500 templates and no structured data.

**R14. Local development friction.** `DEBUG` is hard-coded `False` (the `DEBUG` env var in CLAUDE.md does nothing), and `SECURE_SSL_REDIRECT=True` always. As a result `runserver` redirects to https, local media is not served, and tests need `override_settings`. Read both values from env, with production-safe defaults.

**R15. External links of uncertain status on the contact page.** The "Exclusive Transaction Broker Agreement" Google Form and Drive PDF are linked from the contact page. Confirm they are current and company-approved.

### Low / housekeeping

- `CLAUDE.md` is untracked. Commit it or ignore it deliberately.
- `STATICFILES_STORAGE` and `DEFAULT_FILE_STORAGE` are dead settings alongside `STORAGES`. Remove them as part of R1.
- The `users` app is empty and not installed. Remove it, or install it only if staff profiles are needed.
- The README has broken Markdown (stray "Markdown"/"Bash" lines, an unclosed code fence) and a malformed clone URL.
- Outside the repo, the parent folder holds `gcm-diagnose.log` (Git Credential Manager diagnostics) and unrelated Postman/Kilo instruction files. None are tracked in git. Consider deleting the log.
- Tracked secrets check: no `.env`, `db.sqlite3`, `media/` or `staticfiles/` are tracked. `.gitignore` is adequate.

---

## 6. Gap summary against the spec

| Spec area | Status |
|---|---|
| Listings search/filter/paginate | Exists (keyword, category, status, price, bedrooms). No sort control, location filter, filter chips or land-size filter |
| Property detail | Exists. Needs alt text, disclaimer, `updated_at`, "Contact for price" |
| Enquiries saved + emailed | Exists. Needs phone, throttling, a better honeypot, timeout, failure tracking, success page |
| Admin | Basic. Needs list_editable/readonly tuning, image previews, group permissions (APPFLOW §10) |
| Publication workflow | **Missing** (R3) |
| Locations / categories / amenities as models | Free text and choices only. Migrating is optional and must preserve data |
| Services page, Articles/blog, Projects, FAQ | Missing (`Service` model exists but has no page) |
| Privacy / Terms / 404 / 500 | Missing. The consent checkbox has no privacy policy to link to |
| Public JSON API (`/api/v1/`) | Missing |
| Design tokens / accessibility | Partial. Inline CSS in `base.html`; needs focus states, labels tied to inputs, reduced motion |

## 7. Recommended implementation sequence

1. **Hotfix, before Phase 1:** R1 (Cloudinary storage), confirm R2 (key rotation), R4 (staging branch), R5 (`source` validation). These are small, isolated changes. Ship them through staging.
2. **Phase 1, foundation:** env-driven `DEBUG`/SSL settings (R14), `.env.example`, pinned dependency upgrade (R9), logging config with `EMAIL_TIMEOUT`, `/healthz`, Ruff, and custom 404/500 templates.
3. **Phase 2, data and admin:** additive migrations only. Property `publication_status` (backfilled to published), `updated_at`, nullable price, nullable bed/bath, SEO fields, image alt text and cover flag. `SiteConfiguration` gets the missing social links. `ContactMessage` gets phone and notification tracking. Add Admin groups. Defer moving `category`/`location` to FK models until the free-text values have been reviewed.
4. **Phase 4, enquiries** (before the API, because enquiries are live): rate limiting, an honeypot that bots can see, a success page, and tests.
5. **Phase 5–6, templates:** centralise contact data, design tokens, the missing pages (services, land/houses/rentals views, privacy/terms placeholders that need legal text), and removal of stock and unconfirmed copy.
6. **Phase 3, API:** add DRF read-only endpoints only if a consumer exists (mobile app, partner feed). Otherwise this can stay deferred.
7. **Phase 7–9:** SEO, accessibility, QA and deployment, as written in the plan.

## 8. Files expected to change

- `emanhomes_project/settings.py`: storage, env-driven DEBUG/SSL, logging, email timeout
- `emanhomes_project/urls.py`: sitemap visibility filter, new routes, error handlers
- `core/models.py` and new migrations `0012+` (additive only)
- `core/forms.py`, `core/views.py`, `core/admin.py`, `core/tests.py`
- `templates/core/*.html`, plus new templates for services, success, privacy, terms, 404 and 500
- `static/css/`: move tokens out of inline `<style>`
- `requirements.txt`, `render.staging.yaml`, `docs/staging-deployment.md`, `README.md`
- New: `.env.example`

## 9. Decisions needed from Eman Homes

1. ~~Is "Dzen-Ayor, East Legon, Accra" the real public office address?~~ Yes (confirmed 2026-10-15).
2. Which number is the canonical WhatsApp number?
3. Are the office hours (Mon–Fri 8–5) correct?
4. Is the Facebook URL `emanhomesofficial` or `emanhomes`?
5. What is the policy for sold or rented listings: hide them, or show them as "Sold"?
6. Is the broker agreement form/PDF current?
7. Does any consumer need the JSON API now?
8. Who supplies the privacy policy and terms text?
