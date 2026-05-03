# SuperPersonal

Client-server automation system bridging a Django web dashboard to Windows hardware — remote control of audio, keyboard, mouse, and screenshots via WebSocket.

[![CI](https://github.com/SuperPeterDev/SuperPersonal/actions/workflows/ci.yml/badge.svg)](https://github.com/SuperPeterDev/SuperPersonal/actions/workflows/ci.yml)

## Architecture

```
Browser (Dashboard) ←→ WebSocket ←→ Django/Channels ←→ Windows Client
                                                  ↕
                                              Celery/Redis
```

- **Server**: Django 6.0 + Channels + DRF — serves the web dashboard, relays commands to clients via WebSocket.
- **Client**: Python agent on Windows — receives commands, executes them (pyautogui/pycaw), and streams results back.
- **Task Queue**: Celery + Redis for async command dispatch and polling.

## Tech Stack

| Layer     | Technology                        |
|-----------|-----------------------------------|
| Web       | Django 6.0, Channels, DRF, JWT    |
| Async     | Celery, Redis                     |
| Client    | PyAutoGUI, PyCaw, psutil          |
| Testing   | pytest, pytest-django, requests-mock |
| CI/CD     | GitHub Actions (headless Ubuntu)  |

## CI/CD

- **Pipeline**: GitHub Actions on `ubuntu-latest` — runs `pytest` on every push and PR.
- **Headless**: Windows-only GUI libraries (`pyautogui`, `pycaw`, `comtypes`) are scoped with `sys_platform == 'win32'` in `requirements.txt`. No Xvfb required.
- **Status**: Check the badge above for current build status.

## Development

```bash
# 1. Create virtual environment
python3 -m venv venv && source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run migrations
python manage.py migrate

# 4. Start development server
python manage.py runserver

# 5. Run tests
pytest
```

## Project Structure

```
SuperPersonal/
├── src/
│   ├── server/          # Django backend (API, WebSocket, models)
│   │   ├── super_personal/
│   │   │   └── settings.py
│   │   ├── api/         # REST endpoints
│   │   └── devices/     # Device management
│   └── client/          # Windows client agent
│       ├── executors/   # Command executors (screenshot, shell, media)
│       └── websocket/   # WebSocket client connection
├── tests/               # pytest test suite
├── .github/workflows/   # CI/CD pipeline
└── requirements.txt     # Dependencies with platform markers
```

## License

MIT — see [LICENSE](LICENSE) for details.
