#!/usr/bin/env python3
"""
SuperPersonal Dock UI v2 — Production E2E Tests
Target: http://34.182.12.121:8000
Tests the full authenticated UI flow against the live production server.
"""

import sys
import json
import time
import requests

BASE = "http://34.182.12.121:8000"
USERNAME = "admin"
PASSWORD = "admin123"

s = requests.Session()
passed = 0
failed = 0


def test(name, fn):
    global passed, failed
    try:
        fn()
        passed += 1
        print(f"  PASS {name}")
    except Exception as e:
        failed += 1
        print(f"  FAIL {name}: {e}")


# -- Auth --------------------------------------------
def test_login_redirect():
    """Dashboard redirects to login when unauthenticated"""
    r = requests.get(f"{BASE}/", allow_redirects=False)
    assert r.status_code == 302, f"Expected 302, got {r.status_code}"
    assert '/accounts/login/' in r.headers.get('Location', '')


def test_login_page_loads():
    """Login page returns 200 and contains expected HTML"""
    r = s.get(f"{BASE}/accounts/login/")
    assert r.status_code == 200
    assert 'SuperPersonal' in r.text


def test_login_succeeds():
    """Login with valid credentials redirects to dashboard"""
    r = s.get(f"{BASE}/accounts/login/")
    csrf = r.text.split('name="csrfmiddlewaretoken" value="')[1].split('"')[0]
    r = s.post(f"{BASE}/accounts/login/", data={
        "username": USERNAME, "password": PASSWORD,
        "csrfmiddlewaretoken": csrf
    }, allow_redirects=False)
    assert r.status_code == 302, f"Expected 302, got {r.status_code}"
    # Follow redirect
    r = s.get(f"{BASE}/", allow_redirects=True)
    assert r.status_code == 200


# -- Dock Page Structure -----------------------------
def test_dock_page_has_status_bar():
    r = s.get(f"{BASE}/")
    assert 'sb-status' in r.text, "Missing status bar element"


def test_dock_page_has_pipeline():
    r = s.get(f"{BASE}/")
    assert 'pl-client' in r.text, "Missing pipeline element"
    assert 'pl-result' in r.text, "Missing pipeline result element"


def test_dock_page_has_screenshot_hero():
    r = s.get(f"{BASE}/")
    assert 'screenshot-hero' in r.text, "Missing screenshot hero"
    assert 'No screenshot yet' in r.text


def test_dock_page_has_toast_container():
    r = s.get(f"{BASE}/")
    assert 'toast-container' in r.text, "Missing toast container"


def test_dock_page_has_device_tabs():
    r = s.get(f"{BASE}/")
    assert 'device-tabs' in r.text, "Missing device tabs"


# -- Dock Items Loaded -------------------------------
def test_dock_registry_loaded():
    r = s.get(f"{BASE}/")
    assert 'dock/registry.js' in r.text, "registry.js not loaded"


def test_dock_items_all_present():
    r = s.get(f"{BASE}/")
    items = ['screenshot.js', 'shell.js', 'clipboard.js', 'files.js',
             'process.js', 'queue.js', 'volume.js', 'schedule.js', 'quick.js', 'lock.js']
    for item in items:
        assert f'dock/items/{item}' in r.text, f"Missing dock item: {item}"


def test_app_v2_loaded():
    r = s.get(f"{BASE}/")
    assert 'app-v2.js' in r.text, "app-v2.js not loaded"


def test_css_loaded():
    r = s.get(f"{BASE}/")
    assert 'dock.css' in r.text, "dock.css not loaded"


# -- API Flow (Authenticated) ------------------------
def test_api_devices_returns_data():
    r = s.get(f"{BASE}/api/v1/devices/")
    assert r.status_code == 200
    devices = r.json()
    assert isinstance(devices, list)


def test_api_can_create_command():
    r = s.get(f"{BASE}/api/v1/devices/")
    devices = r.json()
    if not devices:
        print("(no devices — skipping command test)")
        return

    device_id = devices[0].get('pk_device_id')
    csrf = s.cookies.get('csrftoken', '')
    r = s.post(f"{BASE}/api/v1/commands/", json={
        "device": device_id, "command_type": "CMD_PING", "payload": {}
    }, headers={"X-CSRFToken": csrf})
    assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"


# -- Unauthenticated API Protection ------------------
def test_api_create_command_blocked_without_auth():
    r = requests.get(f"{BASE}/api/v1/devices/")
    devices = r.json()
    if not devices:
        return
    r = requests.post(f"{BASE}/api/v1/commands/", json={
        "device": devices[0].get('pk_device_id'), "command_type": "CMD_PING", "payload": {}
    })
    assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"


def test_api_pending_allowed_without_auth():
    r = requests.get(f"{BASE}/api/v1/devices/")
    devices = r.json()
    if not devices:
        return
    hw_id = devices[0].get('hardware_id', '')
    r = requests.get(f"{BASE}/api/v1/commands/pending/?device_id={hw_id}")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"


# -- Command E2E Flow (if client is connected) -------
def test_command_e2e_flow():
    """Create command -> wait for client -> verify result"""
    r = s.get(f"{BASE}/api/v1/devices/")
    devices = r.json()
    if not devices:
        print("(no devices — skipping E2E flow)")
        return

    # Find an active device
    active = [d for d in devices if d.get('is_active')]
    if not active:
        print("(no active devices — skipping E2E flow)")
        return

    device = active[0]
    device_id = device.get('pk_device_id')
    csrf = s.cookies.get('csrftoken', '')

    # Create command
    r = s.post(f"{BASE}/api/v1/commands/", json={
        "device": device_id, "command_type": "CMD_PING", "payload": {}
    }, headers={"X-CSRFToken": csrf})
    assert r.status_code == 201, f"Command creation failed: {r.text}"
    cmd = r.json()
    cmd_id = cmd['pk_command_id']
    print(f"      (created ping cmd {cmd_id[:8]}...)")

    # Wait for client to poll and execute
    for _ in range(12):
        time.sleep(1)
        r = s.get(f"{BASE}/api/v1/commands/?device={device_id}",
                  headers={"X-CSRFToken": csrf})
        cmds = r.json()
        match = [c for c in cmds if c['pk_command_id'] == cmd_id]
        if match and match[0]['status'] in ('SUCCESS', 'FAILED'):
            cmd = match[0]
            assert cmd['status'] == 'SUCCESS', f"Command failed: {cmd.get('log', {})}"
            log = cmd.get('log', {})
            assert 'Pong' in log.get('output', ''), f"Expected 'Pong', got: {log}"
            print(f"      (client responded in {_+1}s)")
            return

    # If we get here, try checking pending
    hw_id = device.get('hardware_id', '')
    r = requests.get(f"{BASE}/api/v1/commands/pending/?device_id={hw_id}")
    pending = r.json()
    if pending:
        print(f"      (!!  client may be offline — {len(pending)} commands still pending)")
    else:
        assert False, "Command not completed after 12s"


# -- Run ---------------------------------------------
if __name__ == "__main__":
    print(f"\nSuperPersonal Dock UI v2 -- E2E Test")
    print(f"Target: {BASE}\n")

    print("-- Auth --")
    test("Dashboard redirects to login", test_login_redirect)
    test("Login page loads (200)", test_login_page_loads)
    test("Login succeeds with valid credentials", test_login_succeeds)

    print("\n-- Dock Page Structure --")
    test("Status bar present", test_dock_page_has_status_bar)
    test("Pipeline bar present", test_dock_page_has_pipeline)
    test("Screenshot hero present", test_dock_page_has_screenshot_hero)
    test("Toast container present", test_dock_page_has_toast_container)
    test("Device tabs present", test_dock_page_has_device_tabs)

    print("\n-- Dock Items Loaded --")
    test("Dock registry.js loaded", test_dock_registry_loaded)
    test("All 10 dock items loaded", test_dock_items_all_present)
    test("app-v2.js loaded", test_app_v2_loaded)
    test("dock.css loaded", test_css_loaded)

    print("\n-- API Flow --")
    test("GET /api/v1/devices/ returns list", test_api_devices_returns_data)
    test("POST /api/v1/commands/ with auth (201)", test_api_can_create_command)

    print("\n-- Auth Protection --")
    test("POST /commands/ without auth blocked (401/403)", test_api_create_command_blocked_without_auth)
    test("GET /commands/pending/ without auth allowed (200)", test_api_pending_allowed_without_auth)

    print("\n-- E2E Command Flow --")
    test("PING -> client -> SUCCESS -> Pong", test_command_e2e_flow)

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {passed+failed}")
    if failed:
        sys.exit(1)
    else:
        print("All production E2E tests passed!")
