Markdown
# 🏡 EmanHomes - Premier Real Estate Platform

A modern, high-performance real estate portfolio website built for **EmanHomes**, a trusted real estate partner in East Legon & Greater Accra, Ghana. This platform allows administrators to easily list properties, manage team members, and connect with clients via WhatsApp and direct calls.

**Live Website:** [https://emanhomes.com](https://emanhomes.com)

---

## ✨ Key Features

### 🏠 Property Management
* **Video-First Listings:** Support for embedding **YouTube** and **Instagram** videos directly into property cards.
* **Smart Fallbacks:** Automatically displays a video player if no image is uploaded.
* **Dynamic Currency:** Admin can toggle prices between **USD ($)** and **GHS (GH₵)**.
* **Mortgage Calculator:** Built-in JS calculator on every property page.
* **Filtering:** Search by title, description and location, then filter by category, status, price and bedrooms.
* **Conversion Tracking:** Optional GA4 events for property views, enquiries, phone clicks and WhatsApp clicks.

### 👥 Team & About
* **"No-Upload" System:** Team member photos are added via direct URL (LinkedIn/Imgur) to save server storage and prevent broken links.
* **Auto-Fix Drive Links:** Smart logic to handle various image link formats.

### 🛠 Administrative Control
* **Custom Admin Panel:** Secure login to manage all site content.
* **Site Configuration:** Update phone numbers, email, and address from the admin panel without touching code.
* **Lead Operations:** Track enquiry type, preferred contact method, status, follow-up date, internal notes, and related property.
* **Property Gallery:** Add multiple listing images, captions, and display order from the Property admin page.

### 🎨 User Experience
* **Luxury Theme:** Custom "Navy & Gold" branding.
* **Responsive Design:** Fully mobile-friendly layout using Bootstrap 5.
* **Direct Contact:** Floating WhatsApp & Call buttons.
* **Broker Forms:** Integration with Google Forms & PDF downloads for transaction agreements.

---

## 🚀 Tech Stack

* **Backend:** Python 3.11, Django 5.1.5
* **Database:** PostgreSQL (Production), SQLite (Development)
* **Frontend:** HTML5, CSS3, JavaScript, Bootstrap 5
* **Static Files:** WhiteNoise
* **Deployment:** Render (Web Service + Managed PostgreSQL)

---

## ⚙️ Local Installation Guide

Follow these steps to run the project on your machine.

### 1. Clone the Repository
```bash
git clone [https://github.com/KobbyFlex00/emanhomes-v2.git](https://github.com/KobbyFlex00/emanhomes-v2.git)
cd emanhomes-v2
2. Create a Virtual Environment
Bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
3. Install Dependencies
Bash
pip install -r requirements.txt
4. Setup Database
Bash
python manage.py makemigrations
python manage.py migrate
5. Create Admin User
Bash
python manage.py createsuperuser
# Follow the prompts to set a username and password
6. Run the Server
Bash
python manage.py runserver
Visit http://127.0.0.1:8000 in your browser.

## 🚀 Production release checklist

Set these environment variables in Render before deploying:

```text
SECRET_KEY=<long-random-production-secret>
ALLOWED_HOSTS=emanhomes.com,www.emanhomes.com
CSRF_TRUSTED_ORIGINS=https://emanhomes.com,https://www.emanhomes.com
DATABASE_URL=<managed-postgresql-url>
EMAIL_HOST_PASSWORD=<gmail-app-password-or-smtp-secret>
LEAD_NOTIFICATION_EMAIL=<inbox-for-new-leads>
CLOUDINARY_URL=<cloudinary-connection-url>
ANALYTICS_MEASUREMENT_ID=<optional-ga4-measurement-id>
```

`SECRET_KEY` is required; the application intentionally fails to start if it is
missing. Generate a value with `python -c "from secrets import token_urlsafe;
print(token_urlsafe(64))"` and save it only in Render's environment settings.
If the old committed fallback key was ever used in production, rotate it before
the next deploy; this will invalidate existing Django sessions.

Use the following Render commands:

```text
Build:  pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
Start:  gunicorn emanhomes_project.wsgi:application
```

After deployment:

1. Submit a general enquiry and a property enquiry; confirm both appear in `/admin/` and the notification inbox.
2. Test WhatsApp and phone buttons on mobile and confirm the listing title is present in WhatsApp property messages.
3. Verify `/sitemap.xml`, `/robots.txt`, canonical URLs, page descriptions, and Google Search Console.
4. Create a database backup before migrations and retain the previous deployment for rollback.
5. Replace generic imagery and review every listing’s price, status, availability, gallery, description, and contact details.

📖 Usage Guide
Logging In
Access the admin panel at: http://127.0.0.1:8000/admin/ or https://emanhomes.com/admin/.

Adding a Property
Go to Properties > Add Property.

Title & Price: Enter details and select Currency (USD or GHS).

Media:

Video: Paste a YouTube or Instagram link (Recommended).

Image: Optional. Acts as a thumbnail if provided.

Bed/Bath: Enter numbers manually.

Adding a Team Member
Go to Team Members > Add.

Image URL: Paste a direct link to the photo (e.g., Right-click a LinkedIn photo -> "Copy Image Address"). Do not upload files directly.

☁️ Deployment (Render)
This project is configured for automated deployment on Render.com.

Build Command: pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate

Start Command: gunicorn emanhomes_project.wsgi:application

📞 Contact
EmanHomes

📍 Location: Dzen-Ayor, East Legon, Accra

📱 Phone: +233 20 584 3775

📧 Email: emanpages@gmail.com

© 2026 EmanHomes. All Rights Reserved.
