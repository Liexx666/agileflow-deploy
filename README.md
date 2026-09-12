# AgileFlow - Agile Project Management System

**AgileFlow** is an Agile project management web application developed by **Team 2 (Project Pulse)** for **FIT2101 Software Engineering Process and Management** at Monash University.

---

## ⚡ Quick Start Guide

Follow these steps to set up and run AgileFlow locally on your computer:

### 1. Clone the Repository
```bash
git clone https://git.infotech.monash.edu/fit2101/fit2101-s2-2026/fit2101-group-repo/MA_Monday1230pm_Team2.git
cd MA_Monday1230pm_Team2
```

### 2. Set Up a Virtual Environment (Recommended)
**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 🗄️ Database Configuration

AgileFlow supports both **Shared Cloud Database (Neon PostgreSQL)** and **Local Offline Mode (SQLite)**:

### Option A: Connect to Shared Cloud Database (Neon PostgreSQL)
To sync live tasks with the team in real-time:
1. Create a `.env` file in the project root directory (you can copy `.env.example`):
   ```bash
   cp .env.example .env
   ```
2. In `.env`, add the shared team `DATABASE_URL`:
   ```env
   DATABASE_URL="postgresql://YOUR_USER:YOUR_PASSWORD@YOUR_HOST/YOUR_DATABASE?sslmode=require"
   ```

### Option B: Local Offline Mode (SQLite)
If you don't create a `.env` file, AgileFlow will automatically default to a local `db.sqlite3` file on your machine.

---

## 🚀 Running the Application

Start the server using the quick launcher:
```bash
python run.py
```
*This command automatically applies database migrations, seeds initial data, and starts the Django server.*

👉 Open your web browser at: **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)**

---

## 🔑 Login & Administration

* **Web App Login:** [http://127.0.0.1:8000/login/](http://127.0.0.1:8000/login/)
* **Django Admin Dashboard:** [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

> **Team login:** Ask the project team privately for a demo account.
> Do not store shared account passwords or database credentials in this repository.

*(Optional)* To create an additional superuser/admin account:
```bash
python manage.py createsuperuser
```


---

## 🧪 Running Automated Tests

Run the full automated test suite:
```bash
python manage.py test
```

Or run backlog-specific tests:
```bash
python manage.py test backlog
```

---

## 👥 Team 2 (Project Pulse)

* **Ethan Tiang Yong Xuan** (35626127) - Scrum Master
* **Chloe Lai Phui Yan** (35622342) - Product Owner
* **Hiromu Tao** (36557609) - Lead Developer
* **Siddharth Mahendran** (33590656) - UI/UX Lead
* **Li YaoXing** (35578009) - QA & DevOps Lead

---

## 📌 Features in Sprint 1 (Iteration 1)

* **User Authentication**: Secure user login, logout with CSRF protection, and session management.
* **Product Backlog View**: 4-column structured list view displaying Task Name, Tags, Priority color badges, Story Points (0–10), Stage, and Status.
* **Sprint Management**: Sidebar with sprint status pills (`Planning`, `Active`, `Completed`) and sprint filtering.
* **Task Creation & Editing**: Form controls with validation, priority selection, tag assignment, and task history tracking.
* **Sorting & Filtering**: Dynamic sorting by Priority and Date Created, with instant tag filtering.
