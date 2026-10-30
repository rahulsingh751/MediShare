# MediShare

MediShare is a Django and vanilla HTML/CSS/JavaScript MVP for responsible medicine-submission review and community discovery. A single account can submit listings and search; accounts are not split into permanent donor/receiver roles.

> **Safety and legal notice:** This is a prototype, not a pharmacy or medical service. A listing or reviewer status is not a safety guarantee, medical recommendation, prescription, or legal authorization to transfer a medicine. The software does not establish that a medicine may lawfully be redistributed in India. Obtain current legal advice and qualified pharmacy-professional review before operating real medicine workflows.

## What is implemented

- Django authentication, password hashing, registration, password reset and signed email verification.
- SQLite for local development; PostgreSQL configuration through environment variables.
- Responsive landing page and account dashboard with database-backed counts.
- Medicine submission, image preview and server-side file validation.
- Conservative, server-enforced restrictions for prescription/controlled, expired, opened, damaged, improperly stored and cold-chain medicines.
- Recall/withdrawal confirmation is required for discovery; there is no automated recall-feed integration, so reviewers must independently verify recall status.
- Human-reviewed listing moderation through Django Admin; only a superuser or staff member explicitly marked as a verified pharmacist can approve listings or reserve requests.
- Search across medicine names, brand/generic names, ingredients, strength, form and manufacturer; city/PIN filters and autocomplete.
- Listing requests, duplicate-request protection, atomic inventory decrement, cancellation, saved listings, notifications and a safety-report review queue.
- Privacy-first approximate locality display; no precise coordinates or home addresses are collected.
- In-app data uses normal Django ORM persistence. No fabricated listings, impact figures or sample data are included.

## Project structure

- `config/` — Django settings, root URLs, WSGI and ASGI entry points.
- `accounts/` — custom universal member account, registration/login forms, email verification and account administration.
- `medicines/` — medicine submission, image storage, eligibility rules, discovery filters and reviewer moderation.
- `exchange/` — medicine requests, transactional reservation, saved listings, notifications and safety reports.
- `core/` — server-rendered page views, URL routing and shared dashboard context.
- `templates/` — Django HTML templates grouped by account, listing, exchange and legal pages.
- `static/css/` and `static/js/` — separate responsive stylesheet and vanilla JavaScript interactions.

The custom Django user is the parent for listings and requests. A listing owns its image records, while requests refer to both the listing and the requesting member. Saved listings, notifications and reports are separate relational records. Inventory changes and request transitions run in database transactions; PostgreSQL row locks and conditional quantity updates protect reservation updates.

## Important prototype limitations

The following are **not implemented or configured** and must not be represented as active: mobile OTP/SMS, identity verification, NGO or pharmacy onboarding/credentials, a map/geocoder, real-time messaging, medicine barcode/OCR extraction, medicine database/recall feeds, alert subscriptions, cloud object storage, production email delivery, self-service account deletion, multilingual translations, rate limiting, and a production privacy/retention program.

The default email backend prints email contents and verification/reset links in the terminal. Configure a vetted email provider before deployment. No SMS provider credentials or integrations are supplied.

Request/reservation workflows are **disabled by default in every environment**. For controlled local testing only, set `$env:MEDISHARE_REQUEST_WORKFLOWS_ENABLED="true"` in PowerShell before starting Django. In production the setting is also required to be explicitly enabled. **Do not enable real-world request/reservation workflows until qualified Indian legal counsel and pharmacy professionals have approved the precise workflow, eligibility rules, partner controls and operational procedures.** A medical-verifier flag is an administrator credential, not an external credential check.

## Requirements

- Python 3.11 or newer (the project was validated with Python 3.14).
- PostgreSQL for a production deployment; SQLite is the local default.

## Local setup (Windows PowerShell)

From the project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py makemigrations accounts medicines exchange
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/`. On registration, the local console email backend prints the signed email-verification link in the terminal running Django. Follow it, then sign in. The Django admin is at `http://127.0.0.1:8000/admin/`.

### Receive verification emails locally with Gmail

The default console backend does not deliver email to an inbox. To send through Gmail, enable 2-Step Verification on the sender's Google account and create an App Password. Do not use the normal Google account password. In the same PowerShell window used to start Django, set the SMTP configuration below, substituting the sender's address:

```powershell
$env:DJANGO_EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
$env:DJANGO_EMAIL_HOST = "smtp.gmail.com"
$env:DJANGO_EMAIL_PORT = "587"
$env:DJANGO_EMAIL_HOST_USER = "your-address@gmail.com"
$securePassword = Read-Host "Gmail App Password" -AsSecureString
$env:DJANGO_EMAIL_HOST_PASSWORD = [System.Net.NetworkCredential]::new("", $securePassword).Password
$env:DJANGO_EMAIL_USE_TLS = "true"
$env:DJANGO_DEFAULT_FROM_EMAIL = $env:DJANGO_EMAIL_HOST_USER
python manage.py runserver
```

Keep the App Password private. Restart Django after setting these variables. To verify an existing unverified account, sign in, select **Resend link** on the dashboard, and check the recipient's spam folder as well as the inbox. The sender account must permit SMTP access; if sending fails, Django reports the SMTP error in the server terminal.

The environment example documents supported environment variables. `.env` is intentionally ignored by Git; this project does not automatically load it. Set environment variables in the shell or through your deployment environment. SQLite is used unless `DB_ENGINE=postgresql` is set.

Example PostgreSQL environment variables:

```powershell
$env:DB_ENGINE = "postgresql"
$env:DB_NAME = "medishare"
$env:DB_USER = "medishare"
$env:DB_PASSWORD = "use-a-secret-manager"
$env:DB_HOST = "127.0.0.1"
$env:DB_PORT = "5432"
```

Create the PostgreSQL database and user separately, then run `python manage.py migrate`.

## Review workflow

1. A verified member submits medicine details and optional package photographs.
2. The backend marks submissions with minimum eligibility failures as restricted; only eligible submissions enter the review queue.
3. Staff with verified-pharmacist permission inspect the listing under Django Admin. A reviewer can mark it under review, approve an eligible submission for discovery, or reject it.
4. Only approved listings that still satisfy every server-side eligibility check appear in discovery and autocomplete. Expired, restricted, prescription-required, controlled, opened, damaged, improperly stored, cold-chain and unavailable listings are excluded.
5. When request workflows are enabled, members can request an eligible listing. A reviewer can reserve it from the request queue. Inventory updates are transactional and cannot exceed available quantity.
6. Platform approval is not transfer authorization. The current prototype does not provide legal classification data, prescription checks, partner verification, handover logistics or proof that a transfer is lawful.

To grant reviewer access, a superuser must create/staff-enable the account and explicitly set `is_pharmacist_verified` in Django Admin after independently checking credentials. Do not rely on the flag as automatic credential validation.

## Configuration and deployment notes

- Set a unique, long `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`, and restrictive `DJANGO_ALLOWED_HOSTS` in production.
- Configure PostgreSQL, secure SMTP credentials, HTTPS termination, backups, monitoring and operational alerting.
- Run `python manage.py collectstatic`; configure a trusted static/media service. The development server's media serving is not for production.
- Production media currently uses Django's local filesystem setting. Configure a secure private object-storage backend and authorization policy before accepting real medicine images.
- Review Django's deployment checklist with `python manage.py check --deploy` in a production-like environment.
- Conduct legal, privacy, accessibility, threat-model and professional safety review before launch.

## Validation

```powershell
python manage.py check
python manage.py test
```
