# 🏡 EmanHomes — Real Estate Website

The website and property platform for **Eman Homes Limited GH**, based in East Legon, Greater Accra, Ghana. Staff list properties, manage content and follow up on enquiries through Django Admin. Visitors browse listings and get in touch by enquiry form, WhatsApp or phone.

**Live website:** [https://emanhomes.com](https://emanhomes.com)

---

## ✨ Key features

### 🏠 Property management
* **Video-first listings:** embed **YouTube** and **Instagram** videos in property cards.
* **Fallbacks:** a property shows its video when no image has been uploaded.
* **Currency:** prices in **USD ($)** or **GHS (GH₵)**.
* **Mortgage calculator** on property pages.
* **Search and filters:** keyword (title, description, location), category, status, price and bedrooms.
* **Conversion tracking:** optional GA4 events for property views, enquiries, phone clicks and WhatsApp clicks.

### 👥 Team & About
* Team member photos are added by direct image URL rather than upload.

### 🛠 Administration
* **Django Admin** for all site content.
* **Site configuration:** phone numbers, email and address are edited in Admin, not in code.
* **Lead operations:** enquiry type, preferred contact method, status, follow-up date, internal notes and related property.
* **Property gallery:** multiple images per listing, with captions and display order.

### 🎨 User experience
* Navy, white and red branding taken from the Eman Homes logo.
* Responsive Bootstrap 5 layout.
* Floating WhatsApp and call buttons.
* Links to the transaction broker agreement (Google Form and PDF).

---

## 🚀 Tech stack

* **Backend:** Python 3.11, Django 5.2 LTS
* **Database:** PostgreSQL in production and staging; SQLite for local development
* **Frontend:** server-rendered Django templates, Bootstrap 5, a little vanilla JavaScript
* **Static files:** WhiteNoise
* **Media:** Cloudinary (required on Render)
* **Hosting:** Render web service and managed PostgreSQL

---

## ⚙️ Local development

### 1. Clone and create a virtual environment

```powershell
git clone https://github.com/KobbyFlex00/emanhomes-v2.git
cd emanhomes-v2
python -m venv venv
.\venv\Scripts\Activate.ps1          # macOS/Linux: source venv/bin/activate
pip install -r requirements-dev.txt
```

### 2. Set environment variables

`.env.example` lists every variable. The app reads them from the environment, and nothing loads `.env` automatically. For a quick local session in PowerShell:

```powershell
$env:SECRET_KEY = "local-dev-secret"
$env:DEBUG = "true"                  # enables plain-HTTP local serving
$env:EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
```

macOS/Linux:

```bash
export SECRET_KEY=local-dev-secret DEBUG=true \
       EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

Without `DATABASE_URL` the app uses `db.sqlite3`. Without `CLOUDINARY_URL` uploads are saved to `./media`. Both files are git-ignored.

### 3. Migrate, create an admin user and run

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000. The admin is at http://127.0.0.1:8000/admin/.

> Do not run `makemigrations` casually. Migrations are committed. Create new ones only for a reviewed model change.

### 4. Checks before every commit

These are the same checks CI runs:

```powershell
ruff check .
python manage.py check --deploy
python manage.py makemigrations --check --dry-run
python manage.py test
git diff --check
```

---

## 🌿 Branches and releases

| Branch | Deploys to |
|---|---|
| `main` | **Production**: Render auto-deploys every push |
| `staging` | Render staging service (`render.staging.yaml`) |
| `feature/*`, `hotfix/*` | Nothing. Merge into `staging` first |

Changes go `feature/*` → `staging` → verify on staging → `main`. See [`docs/staging-deployment.md`](docs/staging-deployment.md) for the promotion process. Open risks are tracked in [`docs/architecture-audit.md`](docs/architecture-audit.md).

---

## 🔐 Production configuration

Set these in Render's environment settings. Never commit them.

```text
SECRET_KEY=<long-random-production-secret>
ALLOWED_HOSTS=emanhomes.com,www.emanhomes.com
CSRF_TRUSTED_ORIGINS=https://emanhomes.com,https://www.emanhomes.com
DATABASE_URL=<managed-postgresql-url>
CLOUDINARY_URL=<cloudinary-connection-url>
EMAIL_HOST_PASSWORD=<gmail-app-password-or-smtp-secret>
LEAD_NOTIFICATION_EMAIL=<inbox-for-new-leads>
ANALYTICS_MEASUREMENT_ID=<optional-ga4-measurement-id>
ADMIN_EMAILS=<optional: where server-error alerts go; defaults to LEAD_NOTIFICATION_EMAIL>
```

See [`docs/operations.md`](docs/operations.md) for error alerts, uptime monitoring, backups and rollback.

Safety rails:

* The app will not start without `SECRET_KEY`.
* On Render, the app will not start without `CLOUDINARY_URL`, so uploads cannot land on the ephemeral disk.
* On Render, the app will not start with `DEBUG=true`.

After setting or changing `CLOUDINARY_URL`, open the service's **Shell** in Render and run `python manage.py check_media_storage`. It confirms that Cloudinary accepts the credentials before staff try to upload images.

Generate a secret key with `python -c "from secrets import token_urlsafe; print(token_urlsafe(64))"`.

Render commands:

```text
Build:        ./build.sh
Start:        gunicorn emanhomes_project.wsgi:application
Health check: /healthz/
```

### After each production deploy

1. Check that `/healthz/` returns `{"status": "ok"}`.
2. Submit a general enquiry and a property enquiry. Confirm both appear in `/admin/` and in the notification inbox.
3. Test the WhatsApp and phone buttons on mobile.
4. Verify that `/sitemap.xml` and `/robots.txt` load.
5. Back up the database before any migration, and keep the previous deploy available for rollback.

---

## 📖 Admin guide

**Adding a property:** go to *Properties → Add property*.
* Enter the title and price, and choose the currency (USD or GHS).
* **Media:** paste a YouTube or Instagram link, upload a main image, or both. At least one is required.
* Enter bedrooms and bathrooms, and add gallery images with a display order.

**Adding a team member:** go to *Team members → Add*. Paste a direct image URL. Google Drive "view" links do not work.

---

## 📞 Contact

**Eman Homes Limited GH**
📍 Dzen-Ayor, East Legon, Accra
📱 +233 20 584 3775
📧 emanpages@gmail.com

© Eman Homes Limited GH. All rights reserved.
