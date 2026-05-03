# Developer Manual

## Architecture

SuperPersonal follows a **client-server** model with real-time WebSocket communication:

```
┌─────────────┐     WebSocket      ┌──────────────┐     HTTP/Poll      ┌──────────────┐
│  Windows    │ ◄────────────────► │  Django       │ ◄───────────────► │  Browser     │
│  Client     │     (commands)     │  Server       │     (dashboard)   │  Dashboard   │
└─────────────┘                    └──────────────┘                    └──────────────┘
                                          │
                                          │ Redis
                                          ▼
                                   ┌──────────────┐
                                   │   Celery     │
                                   │   Workers    │
                                   └──────────────┘
```

### Key Modules

| Module                        | Responsibility                                        |
|-------------------------------|-------------------------------------------------------|
| `src/server/super_personal/`  | Django settings, URL routing, ASGI config             |
| `src/server/api/`             | REST API endpoints for device/command CRUD            |
| `src/server/devices/`         | Device registry, connection state, heartbeat tracking |
| `src/client/executors/`       | Command execution: screenshots, shell, media control  |
| `src/client/websocket/`       | Persistent WebSocket client with reconnection logic   |
| `tests/`                      | pytest suite — unit, integration, WebSocket           |

### Data Flow

1. User issues command via dashboard → REST API
2. Server stores command in DB, pushes via WebSocket to client
3. Client executes command using platform-specific executor
4. Result streams back via WebSocket, stored in DB, polled by dashboard

## Testing

```bash
# Run full suite
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_executors.py

# Run with coverage
pip install pytest-cov
pytest --cov=src
```

### CI Testing

The CI pipeline runs on **headless Ubuntu**. Tests using Windows-only libraries
(`pyautogui`, `pycaw`) are skipped on Linux CI via `@pytest.mark.skipif`.
Import these libraries lazily inside executor methods — never at module level.

## Platform Dependencies

| Library     | Platform  | Purpose                    |
|-------------|-----------|----------------------------|
| pyautogui   | Windows   | Screenshots, mouse/keyboard |
| pycaw       | Windows   | Audio volume control       |
| comtypes    | Windows   | COM interface for PyCaw    |

These are declared in `requirements.txt` with platform markers:
```
pyautogui; sys_platform == 'win32'
pycaw; sys_platform == 'win32'
comtypes; sys_platform == 'win32'
```

## Deployment

See deployment scripts in the repository root for:
- SSH tunnel setup to Google VM
- Environment-aware client configuration
- Production Django settings (PostgreSQL, secure keys)
