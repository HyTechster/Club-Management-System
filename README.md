# Club Management System

A small web app for running one student club: members, committee roles, events, and attendance taken by QR code check-in. Members use it on their phones. The committee manages everything from a back-office.

![Upcoming events page](thumbnail.png)

## What it does

- **Members** sign up with their student ID, see upcoming events, check in at events by scanning a QR code, and see their own attendance history.
- **The committee** creates events, opens and closes check-in, shows the event's QR code on a projector, sees who came, and exports members and attendance to CSV.
- **Exco** (President, VP, Secretary, Treasurer) can also manage committee terms and roles.

## Why Django

This is a small project with one club, one database and a handful of pages. Django fits it well because most of what the app needs comes built in:

- **The back-office is free.** Django admin gives the committee search, filters, forms, bulk actions and CSV export for every model. We customise it instead of building a dashboard, which removes most of the work.
- **Accounts and permissions are built in.** Login, password hashing, sessions, and Groups with per-model permissions cover the Member, Committee and Exco roles without extra libraries.
- **Security defaults are on.** CSRF protection, escaped templates, clickjacking headers and safe redirects matter here, because anyone can open a check-in link that was shared in a group chat.
- **Migrations keep databases in step.** Schema changes, and even the permission groups, are created by migrations, so every developer's database and the live one are set up the same way.
- **Server-rendered pages suit phones.** Check-in is a plain HTML page with one button. It loads fast on campus Wi-Fi and needs no frontend build step or JavaScript framework.
- **Small dependency list.** The whole app runs on three packages: `Django`, `segno` (QR codes as SVG, no image libraries) and `django-environ` (settings from `.env`).
- **Easy to hand over.** Student committees change every year. Django is widely taught and well documented, so the next developer can pick it up quickly.

## Tech stack

| Part | Choice |
|---|---|
| Language | Python 3.12 or newer |
| Framework | Django 5.2 |
| Database | SQLite for development (PostgreSQL recommended when deploying) |
| Frontend | Django templates and plain CSS, a few lines of vanilla JS |
| QR codes | `segno` |
| Config | `django-environ`, reading `.env` |

## Getting started

### 1. Requirements

- Python 3.12 or newer (`python --version`)
- Git

### 2. Get the code and install

```bash
git clone <repo-url> club-management
cd club-management
python -m venv .venv
```

Activate the virtual environment:

```bash
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (Git Bash)
source .venv/Scripts/activate

# macOS / Linux
source .venv/bin/activate
```

Then install the packages:

```bash
pip install -r requirements.txt
```

### 3. Configure

Copy the example settings file:

```bash
cp .env.example .env        # Windows PowerShell: Copy-Item .env.example .env
```

Open `.env` and set a secret key. You can generate one with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

| Variable | What it does | Example |
|---|---|---|
| `SECRET_KEY` | Django's signing key. Required. Keep it secret. | long random string |
| `DEBUG` | `True` for development, `False` on a live site | `True` |
| `ALLOWED_HOSTS` | Hostnames the site answers to, comma separated | `localhost,127.0.0.1` |
| `CSRF_TRUSTED_ORIGINS` | Full origins for HTTPS sites | `https://club.example.com` |
| `CLUB_NAME` | Name shown in the header | `Computing Society` |
| `DATABASE_URL` | Optional. Defaults to `db.sqlite3` | `postgres://user:pass@host/db` |

`.env` is in `.gitignore`. Never commit it.

### 4. Create the database

```bash
python manage.py migrate
```

This creates the tables and also the `Committee` and `Exco` permission groups.

### 5. Add sample data (optional)

```bash
python manage.py seed
```

This creates a current term, 20 members, a committee and 7 events, one of which is happening now with check-in open. Running it again is safe and will not make duplicates.

Every seed account uses the password `clubpass123`. Log in with the student ID:

| Student ID | Who | Can do |
|---|---|---|
| `1211101001` | President (Exco) | Everything below, plus terms and committee roles |
| `1211101006` | AJK (Committee) | Back-office for events, attendance and members |
| `1211101010` | Regular member | Member pages only |

The seed command refuses to run when `DEBUG=False`, because it creates staff accounts with a known password.

### 6. Create your own admin account

```bash
python manage.py createsuperuser
```

It asks for a username, email, student ID, full name and password. For yourself you can use a student ID like `ADMIN01`.

### 7. Run it

```bash
python manage.py runserver
```

- Member site: http://127.0.0.1:8000/
- Back-office: http://127.0.0.1:8000/admin/

The login form is labelled "Student ID", but it takes any username, so superusers log in there with their username.

## Using the app

### Members

1. Sign up at `/accounts/signup/` with student ID, name, faculty, email and password. The student ID becomes the login name.
2. `/` lists upcoming events. Tap one for details.
3. At an event, scan the QR code with the phone camera, then tap **Check me in**. If you are not logged in, you log in first and come straight back.
4. `/me/` shows your attendance this term and all time.
5. `/committee/` shows the current committee.

### Committee: running check-in at an event

1. In the back-office, go to **Events**, tick the event, choose **Open check-in** from the actions menu and press **Go**.
2. Open the event and click **Open QR display**, or use **Show QR** on the event page. Put that page on the projector. It refreshes every 30 seconds to update the count.
3. Members scan and check in. Check-in works from 30 minutes before the start until the end time.
4. Afterwards, choose **Close check-in**. To see who came, open the event (the attendance list is at the bottom) or use **Export attendance to CSV**.

If a photo of the QR code gets shared in a group chat, use **Regenerate check-in token**. The old code stops working at once. Reload the QR page to show the new one.

### Committee: managing people

- **New committee member:** a superuser edits their account, ticks **Staff status** and adds them to the `Committee` or `Exco` group. Then an Exco member adds a **Committee role** for the current term so they appear on `/committee/`. Groups control access. Roles are only for display and history.
- **New term:** an Exco member adds a **Term** and ticks **Is current**. The previous term stops being current automatically.
- **Forgotten password:** any committee member can reset a regular member's password from their page in the back-office (use the "this form" link under Password). Staff passwords are reset by a superuser. There is no email reset, because the app does not send email.
- **Adding a member by hand:** set the username to the same value as their student ID so they can log in with it.

### Who can do what

| Group | Access |
|---|---|
| No group | Member pages only |
| `Committee` | Back-office: view, add and change Events, Attendance and Users. Open and close check-in. |
| `Exco` | Everything Committee has, plus Terms and Committee Roles |
| Superuser | Everything, including staff status and group membership |

Only superusers can change staff status, superuser status, groups or permissions. Committee and Exco members can edit regular members and their own account, but not other staff accounts.

## Testing check-in with a real phone

The QR code contains the address you opened the QR page with. If you open it at `127.0.0.1`, your phone will try to reach itself and fail. To test on a phone:

1. Put the laptop and phone on the same Wi-Fi.
2. Find the laptop's IP address (`ipconfig` on Windows, `ipconfig getifaddr en0` on macOS), for example `192.168.1.20`.
3. Add it to `ALLOWED_HOSTS` in `.env`: `ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.20`
4. Run `python manage.py runserver 0.0.0.0:8000`
5. On the laptop, open the QR page at `http://192.168.1.20:8000/...`, not `127.0.0.1`.
6. Scan it with the phone. If it does not load, allow Python through the laptop's firewall.

## Running the tests

```bash
python manage.py test
```

The tests cover check-in rules (closed, wrong or old token, too early, ended, inactive member, full event, scanning twice, login redirect), group permissions, the one-current-term rule, sign-up validation and redirects, back-office privilege limits, CSV export safety and the seed command.

Run the tests and `python manage.py makemigrations --check` before opening a pull request.

## Project structure

```
config/        settings, URLs, CSV export helper, template context
accounts/      custom User model, sign-up, profile page, user admin
committee/     Term and CommitteeRole, committee page, groups migration
events/        Event and Attendance, QR code (qr.py), check-in, event admin, seed command
templates/     base.html and page templates
static/css/    styles.css (design tokens at the top)
static/js/     app.js (stops double-tapped form submits)
```

Business rules live on the models, for example `Event.can_check_in(user)` and `Term.save()`, not in views or templates.

## Conventions

- Keep to the three apps. Discuss before adding a fourth.
- Run `python manage.py makemigrations` after every model change and commit the migration with the code. Never edit a migration that has already been applied. Add a new one.
- Other apps refer to users through `settings.AUTH_USER_MODEL`. Never import `User` directly.
- Use `select_related` and `prefetch_related` on list pages to avoid extra queries.
- Protect member pages with `@login_required` and committee pages with `@permission_required(...)`. Never check role titles for access.
- Design: plain CSS only, mobile first, light and dark mode, touch targets at least 44px, motion respects reduced-motion settings. UI copy stays short and friendly. Leave the Django admin unstyled apart from its header.
- Do not add DRF, React, HTMX, Celery, Docker or a CSS framework without agreeing it first.

## Deploying

Before going live:

1. Set `DEBUG=False`, a new `SECRET_KEY`, your real `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS=https://your-domain`.
2. Use PostgreSQL by setting `DATABASE_URL`.
3. Serve over HTTPS. With `DEBUG=False` the app turns on secure cookies, HTTPS redirect, and trusts `X-Forwarded-Proto` from your proxy. Set `SECURE_SSL_REDIRECT=False` only if your proxy already redirects. Set `SECURE_HSTS_SECONDS` once HTTPS is confirmed working.
4. Run `python manage.py collectstatic` and serve `staticfiles/`, for example with `whitenoise`.
5. Run with a production server such as `gunicorn config.wsgi`.
6. Run `python manage.py check --deploy` and fix what it reports.

Never run `seed` against the live database.

## Known limitations

- There is no limit on login attempts. Put the site behind a proxy with rate limiting if that is a concern.
- Fonts (Google Fonts) and icons (jsDelivr) load from CDNs. Pages still work without them, just with fallback fonts and missing icons.
- One club per installation.

## Planned for later

- Membership fee tracking per term
- Email reminders the day before an event
- E-certificate PDF for attendees
- PostgreSQL and deployment on Coolify with `gunicorn` and `whitenoise`
