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

---

## 10. Progress log

**2026-10-15: hotfix branch (`hotfix/media-storage-and-enquiry-source`, merged to `staging`)**
- R1 fixed: media uses Cloudinary via `STORAGES`, and the app refuses to start on Render without `CLOUDINARY_URL`. The live site's listings use Instagram embeds and no uploaded images appeared on public pages, so no image loss was observed.
- R2: Eman Homes confirmed the production `SECRET_KEY` has been rotated.
- R4 fixed: the staging Blueprint tracks the `staging` branch.
- R5 fixed: the enquiry `source` value goes through the form and is trimmed to 100 characters.
- **New finding, fixed:** `/sitemap.xml` returned 500 in production because `django.contrib.sitemaps` was not installed.
- PR #2 review follow-ups: there are no uploaded images to migrate, because all 36 live listings use Instagram embeds and none reference `/media/` or Cloudinary (checked 2026-10-15). **Open (Phase 2):** clean up Cloudinary objects orphaned when an admin save fails after the upload succeeds.
- `STATICFILES_STORAGE` is kept on purpose: the `django-cloudinary-storage` `collectstatic` command used in the build still reads it. A test now runs that command.

**2026-10-15: Phase 1 (`feature/phase1-foundation`)**
- R9 fixed: all dependencies pinned. Now on Django 5.2 LTS, gunicorn 23 and whitenoise 6.12.
- R14 fixed: `DEBUG` is read from the environment (default off, refused on Render). The HTTPS redirect, secure cookies and HSTS are derived from it.
- Added `/healthz/`, branded 404 and self-contained 500 pages, a 10-second `EMAIL_TIMEOUT`, stdout logging, Ruff in CI, and `.env.example`. Rewrote the README.

**2026-10-15: Phase 2 (`feature/phase2-data-admin`)**
- R3 fixed: listings have `publication_status` (draft/published/archived). Existing listings migrate as *published*. Drafts and archived listings are hidden from pages, search, the sitemap and enquiry links. Per Eman Homes policy, Sold and the new Rented listings stay visible, badged, and sort after available ones.
- R6 fixed: enquiries require a validated phone number. The property-page form no longer auto-ticks consent; it shows a real checkbox.
- R7 (partly): notification failures are recorded on the enquiry (`notification_sent_at` / `notification_error`). Visitors always see a success message once the enquiry is saved. The staff email now includes phone, property reference, listing link and admin link. Rate limiting is still open (Phase 4).
- R8 fixed: business hours, WhatsApp (+233 20 584 3775, confirmed), TikTok, X, LinkedIn, YouTube and Linktree come from Site Configuration. Empty X/LinkedIn fields are filled from the PRD. Facebook is unchanged pending confirmation.
- R11 fixed: a blank price shows "Contact for price"; the payment calculator is hidden for those and for sold/rented listings.
- R12 fixed: video embeds are allow-listed to YouTube and Instagram and parsed properly.
- R13 (partly): `updated_at` added and used for sitemap `lastmod`; per-listing SEO title and description.
- New findings, fixed: malformed price/bedroom filters caused 500s; duplicate listing titles caused a save error (slugs are now unique).
- Admin: listing actions (publish, draft, archive, sold, rented), editable status columns, image previews and alt text. Enquiry details are read-only, with a notification indicator. Roles are kept in sync on every migrate: Property managers, Enquiry managers (no delete), Content editors.
- CI runs on PostgreSQL 16 so migrations are tested on the production engine.
- Removed the unconfirmed "Price is negotiable" tooltip.
- PR #4 review: new columns got database-level defaults (`0014`). Code from the previous release keeps inserting enquiries and listings while a deploy's migrations have run but old workers are still serving. Existing listings' `updated_at` is backfilled from `created_at`. Unicode-digit and out-of-range filter values are handled. Malformed stored video URLs no longer break a page. Content editors can create the Site Configuration record.
- **Known limitation, not changed:** enquiries submitted through the old property-page form were recorded as consented, because of the hidden auto-tick. They can't be told apart from contact-page enquiries, which had a real checkbox, so the records were left as they are. Contacting people about their own enquiry is expected. Don't use pre-2026-10-15 property enquiries for marketing.

**2026-10-15: Phase 4 (`feature/phase4-enquiry-protection`)**
- R7 fixed: enquiry submissions are rate-limited per visitor IP (10 per 10 minutes, configurable through `ENQUIRY_RATE_LIMIT_COUNT` / `ENQUIRY_RATE_LIMIT_WINDOW`). The IP comes from Cloudflare's `CF-Connecting-IP`. Over the limit, visitors get a friendly 429 that points them to phone and WhatsApp.
- The honeypot is now an off-screen text input; the old hidden input was skipped by most bots. A signed timestamp discards forms submitted within 3 seconds of loading. Caught submissions see the normal thank-you page, and nothing is saved or emailed.
- New `/contact/thank-you/` page (noindex) with WhatsApp and call options, and a GA4 `generate_lead` event when analytics is configured.
- Limitation: the rate-limit counter lives in each worker's memory (no shared cache), so with N gunicorn workers the effective limit is up to N × 10. That's acceptable for spam friction. Move to a shared cache if abuse appears.

**2026-10-15: Legal pages and official Facebook (`feature/legal-pages-facebook`)**
- Facebook confirmed by Eman Homes as https://www.facebook.com/emanhomesofficial. It is now the model default, and the migration replaces the old `facebook.com/emanhomes` value. A custom value entered by staff is kept.
- Privacy policy and Terms of use are seeded as **drafts** (`LegalPage`), edited in Admin. The drafts were written by the developer based on the Data Protection Act, 2012 (Act 843) and contain `[TO CONFIRM]` items. **They are not legally approved.** While in draft they return 404 to the public; signed-in staff see them with a "DRAFT – not legally approved" banner. Publishing a page (superusers only; no staff role has the permission) adds the footer links, the "See our privacy policy" link by the consent checkbox, and the sitemap entry.
- Staff-entered legal text is rendered with a restricted formatter (headings, bullets, paragraphs, auto-linked emails and URLs). All HTML is escaped.

**2026-10-16: Phase 5 part 1 (`feature/phase5-pages-content-a11y`)**
- New pages: `/services/` (Service gains `display_order` and `is_active`; the six PRD services are seeded only if none exist) and the landing pages `/properties/land/`, `/properties/houses/` and `/properties/rentals/`. Each has its own title, description and fixed filter. Per the PRD, the Rentals link and sitemap entry appear only when a published listing is for rent. The Properties menu becomes a dropdown. Services cards link to `/contact/?service=<id>`, which pre-fills the subject.
- R10 fixed: removed every Unsplash stock photo. Category tiles use a real listing photo from that category, or a brand gradient. Removed "Premium" from all titles, "Meet the Experts", "cleaning services" (replaced with the PRD service list) and the unconfirmed "Delivering Excellence" tagline. The About page layout bug (process section nested inside a bullet) is fixed, and the team section is hidden when there are no team members.
- Accessibility: skip link and focusable `<main>`, a visible focus ring on navy and white backgrounds, labelled listing filters, a menu button label, and the decorative hero badge hidden from screen readers and no longer spinning. Reveal-on-scroll content is hidden only when JavaScript runs, so it stays visible if scripts fail.

**2026-10-16: Hero, brand and discovery (PRs #8 to #13, all in production)**
- #8 and #9: the homepage hero rotates photos of current listings every 45 seconds, with an "Available now" caption. Photos have no navy tint. Without photos it falls back to the brand background. The spinning circular "VISIT OUR LINKTREE" badge links to the Linktree from Site Configuration. The headline is editable in Admin; the default is "Your trusted partner for land and property in Ghana", and the requested "Ghana's No.1…" was declined as an unprovable claim. Fixed a hero layout bug: the text was squeezed against the left edge and the search card covered a button.
- #10: listings can be saved with only gallery photos. A gallery row with no file no longer crashes the homepage or listing page. Gallery-only listings show their photos. The carousel prefetches one photo per listing and orders ties by id.
- #11: colours sampled from the logo (navy `#00183A`, red `#E40021`), with no navy-on-red text. Listing sorting (recommended, newest, price ascending and descending), with currencies grouped. Phone floating buttons sit clear of the action bar. Fixed invisible navy-on-navy banner titles.
- #12: per-page Open Graph and Twitter tags (listing photo or logo); canonical URLs from `SITE_URL`; RealEstateAgent and BreadcrumbList JSON-LD; `*.onrender.com` hosts and staging are noindex. Server errors are emailed to `ADMIN_EMAILS`. Added `docs/operations.md`.
- #13: Google Search Console verification tag. Eman Homes verified the property and submitted the sitemap (Success, 68 pages). Eman Homes also confirmed a paid Render plan with database backups on, and UptimeRobot monitoring `/healthz/`.

**2026-10-16: Photos, filters and Insights (`feature/photos-filters-insights`)**
- Faster photos: Cloudinary delivery URLs get `f_auto,q_auto,c_limit,w_<n>` (WebP/AVIF, compressed, resized), with `srcset` on listing cards and the listing page. Hero slides are 1600px and share images 1200px. Non-Cloudinary URLs are unchanged.
- Richer filters: location (with suggestions from published listings), currency, min and max price, and 2+/5+ bedroom options. The landing page's own filter is hidden and locked. Active filters show as removable chips with "Clear all". The form keeps the visitor on the current landing page and preserves the sort.
- Insights: `Article` model (draft, published or archived; scheduled `published_at`; escaped plain-text formatting; cover photo; SEO fields). Pages at `/insights/` and `/insights/<slug>/` with Article JSON-LD. The menu, footer, homepage section and sitemap entries appear only once an article is live. Staff can preview drafts (noindex). Content editors can manage articles.
- Fixed the invisible footer brand heading and raised the footer section titles to white (dark red on navy was about 2.5:1 contrast).

## 11. Status at 2026-10-16

| Risk | Status |
|---|---|
| R1 Media on ephemeral disk | Fixed: Cloudinary, enforced on Render, `check_media_storage` |
| R2 Committed secret key | Fixed: rotated in production (confirmed by Eman Homes) |
| R3 No publication state | Fixed: draft/published/archived; sold/rented stay visible |
| R4 Staging tracked `main` | Fixed: `staging` branch |
| R5 Enquiry `source` overflow | Fixed |
| R6 No phone on enquiries | Fixed |
| R7 Weak spam controls | Fixed: rate limit, honeypot, time trap, notification tracking |
| R8 Scattered contact data | Fixed: Site Configuration is the single source |
| R9 Outdated dependencies | Fixed: Django 5.2 LTS, gunicorn 23, everything pinned |
| R10 Stock photos and unconfirmed copy | Fixed |
| R11 No "Contact for price" | Fixed |
| R12 Arbitrary iframe source | Fixed: YouTube/Instagram allow-list |
| R13 SEO gaps | Fixed: `updated_at`, share tags, canonical, structured data, 404/500, Search Console |
| R14 Local development friction | Fixed: env-driven DEBUG and HTTPS |
| R15 Broker agreement links | **Open:** confirm the Google Form and PDF are current |

**Decisions from section 9:**
1. Address: confirmed.
2. WhatsApp: +233 20 584 3775.
3. Hours: 24/7.
4. Facebook: `facebook.com/emanhomesofficial`.
5. Sold/rented listings: stay visible, badged.
6. Broker form: open.
7. JSON API consumer: none identified, so the API is deferred.
8. Legal text: developer drafts written; **awaiting review by a Ghana-qualified lawyer before publishing**.

**Still open:**
- **Eman Homes:**
  - lawyer review and publication of the privacy policy and terms
  - uploading listing photos (they feed the carousel, cards and share previews)
  - confirming the broker agreement links
  - deciding who writes Insights articles
- **Development:**
  - clean-up of Cloudinary files orphaned by failed admin saves
  - a shared cache if per-worker rate limiting proves too loose
  - a Projects page, once real development project content exists
- **Known limitation:** property enquiries submitted before 2026-10-15 were recorded as consented by the old hidden field. Do not use them for marketing.
