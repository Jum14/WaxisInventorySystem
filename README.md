# Waxi's Inventory Management System

Django starter for the SND Foods International Inc. (Waxi's) inventory project.

## Roles

- Developer — technical superuser
- Owner — business superuser
- Manager — operational management
- Crew — kitchen/stock operations

Business hierarchy:

Owner > Manager > Crew

Developer is the technical administrator outside the business hierarchy.

## Run

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open:

http://127.0.0.1:8000/accounts/login/

## Owner account

Django's `createsuperuser` creates a technical superuser. To make that account an Owner rather than Developer, after logging in to `/admin/`, edit its Profile and set Role to `Owner`.

Alternatively, create the account normally and set both `is_staff`/`is_superuser` plus Profile role `OWNER` in Django admin.

## PostgreSQL

Set these environment variables before running:

DB_NAME
DB_USER
DB_PASSWORD
DB_HOST
DB_PORT

If DB_NAME is not set, the project uses SQLite for easier local development.
