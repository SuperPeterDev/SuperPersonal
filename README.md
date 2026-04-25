# SuperPersonal

Client-server automation system bridging Django web dashboard to Windows hardware.

## Project Overview
Automate Windows tasks (audio, keyboard, mouse) remotely through a Django-based web interface.

## Tech Stack
- Django 6.0
- Channels (WebSockets)
- Celery
- PyAutoGUI / PyCaw
- SQLite (testing)

## Development
1. Setup virtualenv: `python3 -m venv venv`
2. Install deps: `pip install -r requirements.txt`
3. Run migrations: `python manage.py migrate`
4. Tests: `pytest`
