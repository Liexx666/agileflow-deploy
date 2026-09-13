# AgileFlow - Agile Project Management System

**AgileFlow** is an Agile project management web application developed by **Team 2 (Project Pulse)** for **FIT2101 Software Engineering Process and Management** at Monash University.

---

## Live Website

**AgileFlow:** https://agileflow-deploy.onrender.com/

The application runs on a Render Free Web Service and uses the team's shared Neon PostgreSQL database. Ask the team privately for a login email and password. A website account is different from the database credentials used in `DATABASE_URL`.

The free service can sleep when inactive, so the first visit may take about a minute to load.

**Current limitation:** persistent storage for uploaded attachments is not configured. Neon stores database records, not the attachment files. Local uploads are not available automatically on Render, and files saved on Render's local filesystem can be lost when the service restarts or redeploys. Production attachment upload/download support is not yet complete.

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
python -m pip install -r requirements.txt
```

---

## 🗄️ Database Configuration

AgileFlow supports both **Shared Cloud Database (Neon PostgreSQL)** and **Local Offline Mode (SQLite)**:

### Option A: Connect to Shared Cloud Database (Neon PostgreSQL)
To sync live tasks with the team in real-time:
1. Create a `.env` file in the project root directory (you can copy `.env.example`):
   **Windows PowerShell:**
   ```powershell
   Copy-Item .env.example .env
   ```
   **macOS / Linux:**
   ```bash
   cp .env.example .env
   ```
2. In `.env`, add the shared team `DATABASE_URL`:
   ```env
   DATABASE_URL="postgresql://YOUR_USER:YOUR_PASSWORD@YOUR_HOST/YOUR_DATABASE?sslmode=require"
   ```

   Replace the placeholders with the actual connection string obtained privately from the database maintainer. Copying `.env.example` alone does not configure working credentials. Keep `.env` out of Git.

   Local changes made while connected to this database are shared with the deployed website and other team members.

### Option B: Local Offline Mode (SQLite)
If `DATABASE_URL` is not set in either `.env` or your terminal environment, AgileFlow defaults to a local `db.sqlite3` file. Accounts and tasks created in this mode are local only and will not appear on the deployed website.

---

## 🚀 Running the Application

For a new local SQLite database, apply migrations once:
```bash
python manage.py migrate
```

For the shared Neon database, inspect pending migrations first and coordinate schema changes with the database maintainer:
```bash
python manage.py showmigrations --plan
```

Start the development server:
```bash
python manage.py runserver
```

**Do not use `python run.py` or `seed_backlog` against the shared database.** The launcher invokes the seed command, which resets the sample users' passwords even when tasks already exist. The seed command's `--force` option also deletes existing tasks. Seeding is only suitable for a disposable local development database.

👉 Open your web browser at: **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)**

---

## 🔑 Login & Administration

* **Web App Login:** [http://127.0.0.1:8000/login/](http://127.0.0.1:8000/login/)
* **Django Admin Dashboard:** [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

> **Team login:** Ask the project team privately for a demo account.
> Do not store shared account passwords or database credentials in this repository.

Login requires a unique email address and an active account. An administrator can create a user through Django Admin and then set their email address. Regular website users do not need staff or superuser privileges.

Accounts created in the same Neon database are immediately usable by the deployed website without redeploying. Passwords are stored as hashes and cannot be read back as plaintext.

*(Optional)* To create an additional superuser/admin account:
```bash
python manage.py createsuperuser
```


---

## Render Deployment

The current service uses the private GitHub deployment repository `Liexx666/agileflow-deploy`, branch `main`. The school GitLab repository remains the team's source of truth.

| Setting | Value |
| --- | --- |
| Language | Python 3 |
| Root Directory | Leave empty |
| Compute | Free |
| Build Command | `bash build.sh && python manage.py migrate --check` |
| Start Command | `gunicorn agileflow_project.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --threads 2` |
| `PYTHON_VERSION` | `3.13.5` |
| `SECRET_KEY` | Generate a secret in Render; never commit it |
| `DATABASE_URL` | The team's actual Neon connection string, without surrounding quotes |

Render provides `RENDER` and `RENDER_EXTERNAL_HOSTNAME` automatically. The settings disable debug mode on Render, use its hostname, and enable HTTPS-related settings.

`build.sh` installs dependencies and collects static files. `migrate --check` verifies that the selected database has no pending migrations; it does not apply them. If this check fails, the database maintainer should review and apply the required migrations before redeploying.

### Updating the deployed website

1. Commit changes on a feature branch in the school GitLab repository and open a merge request into its `main` branch.
2. After review and merge, update the local school `main` checkout and validate the changes.
3. Update the existing GitHub deployment repository with a clean snapshot of the reviewed code. Exclude `.env`, local databases, uploads, generated `staticfiles/`, and the school repository's `.git` history. Preserve the deployment repository's own Git history and remove obsolete files from the snapshot as needed.
4. Commit and push that snapshot to the GitHub deployment repository's `main` branch. Deploy the latest commit from Render, or let automatic deployment run if enabled.
5. Verify login, backlog data, page styling, and logout at the live URL.

**Merging into school GitLab `main` does not automatically update Render.** The initial GitHub deployment was created with separate history to avoid copying old credentials from the school repository. Do not directly push the school branch or force-push its history over the deployment repository. The temporary folder used for the initial export is not the long-term development workspace.

---

## 🧪 Running Automated Tests

Use a local development/test database for automated tests rather than the shared Neon configuration. Django creates a separate test database; the database user needs permission to create it when using PostgreSQL.

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
