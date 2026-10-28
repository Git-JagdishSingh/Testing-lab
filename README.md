# TestLab Finder

TestLab Finder is a Django-based web application for discovering testing laboratories by city, service, and rating.

## Features
- Responsive home page with featured labs and search
- Laboratory directory with filters and pagination
- Laboratory detail pages with reviews
- User registration, login, verification, and password reset
- Company-style laboratory registration
- REST APIs for laboratories, categories, and reviews
- Admin interface for managing users, labs, reviews, and categories

## Setup
1. Create and activate a virtual environment (Windows PowerShell):
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Apply migrations:
   ```bash
   python manage.py migrate
   ```
4. Populate sample data:
   ```bash
   python manage.py populate_sample_data
   ```
5. Run the development server:
   ```bash
   python manage.py runserver
   ```
6. Open http://127.0.0.1:8000/

The local database (`db.sqlite3`) and uploaded files (`media/`) are intentionally
excluded from Git. Run the migrations and sample-data command above after cloning
to create a local database.

## Upload to GitHub

1. Create a new, empty repository on GitHub. Do not initialize it with a README,
   license, or `.gitignore` because this project already has those files.
2. From PowerShell, open this project folder and initialize Git:
   ```powershell
   git init
   git add .
   git status
   ```
3. Check `git status` before proceeding. It should not list `.venv/`, `.env`,
   `db.sqlite3`, or `media/`.
4. Commit the project and set the default branch:
   ```powershell
   git commit -m "Initial project upload"
   git branch -M main
   ```
5. Copy the HTTPS repository URL from GitHub, then add it as the remote and push:
   ```powershell
   git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
   git push -u origin main
   ```

The GitHub repository shares the source code, not a running website. To let
friends use the app online, deploy the repository to a Django-compatible host.
Never commit `.env`, passwords, tokens, the local database, or uploaded files.

## Admin access
Create a superuser:
```bash
python manage.py createsuperuser
```

For production, set `DEBUG=False`, provide a unique `SECRET_KEY` and configure
`ALLOWED_HOSTS` in the hosting provider's environment settings. The development
secret key fallback is only for local use.

## API
- /api/laboratories/
- /api/categories/
- /api/reviews/
- /api/search/?q=water
