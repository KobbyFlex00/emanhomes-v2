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
* **Filtering:** Search by category (Land, Residential, Commercial) and location.

### 👥 Team & About
* **"No-Upload" System:** Team member photos are added via direct URL (LinkedIn/Imgur) to save server storage and prevent broken links.
* **Auto-Fix Drive Links:** Smart logic to handle various image link formats.

### 🛠 Administrative Control
* **Custom Admin Panel:** Secure login to manage all site content.
* **Site Configuration:** Update phone numbers, email, and address from the admin panel without touching code.

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
