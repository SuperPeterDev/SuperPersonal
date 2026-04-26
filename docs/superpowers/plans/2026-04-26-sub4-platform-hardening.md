# Sub-project 4: Platform Hardening Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add login authentication to the web UI so the dashboard and device controls are protected by a username/password, and add API authentication so only the logged-in user can issue commands. Rate limiting on command creation prevents accidental command floods.

**Architecture:** Django's built-in session authentication for the web UI (login page + `@login_required`). Django REST Framework `IsAuthenticated` permission class for all API endpoints. The device client continues to authenticate via hardware_id (no change). DRF throttling limits command creation to 30/minute per IP.

**Tech Stack:** Django auth, DRF SessionAuthentication + IsAuthenticated, DRF throttling

**Prerequisite:** Sub-project 1 must be merged first.

---

## File Map

| Action | Path |
|---|---|
| Modify | `src/server/super_personal/settings.py` — add `LOGIN_URL`, `LOGIN_REDIRECT_URL`, DRF auth/throttle defaults |
| Modify | `src/server/super_personal/urls.py` — add Django auth URLs |
| Create | `src/server/templates/auth/login.html` — login page |
| Modify | `src/server/core/views.py` — add `@login_required` to dashboard and device_detail |
| Modify | `src/server/api/views.py` — add DRF auth/permission classes, throttle on CommandViewSet |
| Modify | `src/server/api/serializers.py` — no change (already fine) |
| Modify | `src/server/tests/test_api_views.py` — add auth tests |
| Modify | `src/server/tests/conftest.py` — add authenticated `api_client` fixture |

---

### Task 1: Configure auth settings

**Files:**
- Modify: `src/server/super_personal/settings.py`

- [ ] **Step 1: Write the failing test**

Add to `src/server/tests/test_api_views.py`:

```python
class TestAuthProtection:
    def test_unauthenticated_command_creation_rejected(self, unauthenticated_api_client):
        device = Tbl_Device.objects.create(hardware_id="auth-test-device")
        url = reverse('command-list')
        data = {"device": str(device.pk_device_id), "command_type": "CMD_PING"}
        response = unauthenticated_api_client.post(url, data, format='json')
        assert response.status_code in [401, 403]

    def test_authenticated_command_creation_allowed(self, api_client):
        device = Tbl_Device.objects.create(hardware_id="auth-ok-device")
        url = reverse('command-list')
        data = {"device": str(device.pk_device_id), "command_type": "CMD_PING", "payload": {}}
        response = api_client.post(url, data, format='json')
        assert response.status_code == 201
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest src/server/tests/test_api_views.py::TestAuthProtection -v
```
Expected: FAIL — unauthenticated request currently returns 201 (no auth enforcement)

- [ ] **Step 3: Add auth + throttle settings to `src/server/super_personal/settings.py`**

At the bottom of `settings.py`, add:

```python
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '0/minute',
        'user': '30/minute',
    }
}
```

- [ ] **Step 4: Add `django.contrib.auth.urls` to `src/server/super_personal/urls.py`**

Open `src/server/super_personal/urls.py` and add the auth URLs. The current file has existing URL patterns. Add:

```python
from django.urls import path, include

# Add this to urlpatterns list:
path('accounts/', include('django.contrib.auth.urls')),
```

- [ ] **Step 5: Update conftest.py to provide both authenticated and unauthenticated clients**

Open `src/server/tests/conftest.py` and add/update:

```python
import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User


@pytest.fixture
def api_client():
    client = APIClient()
    user = User.objects.create_user(username='testuser', password='testpass123')
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def unauthenticated_api_client():
    return APIClient()
```

- [ ] **Step 6: Run test to verify it passes**

```
pytest src/server/tests/test_api_views.py::TestAuthProtection -v
```
Expected: PASS

- [ ] **Step 7: Run full test suite to check for regressions**

```
pytest src/server/tests/ -v
```
All tests must PASS. If existing tests break because they now get 401, update their `api_client` fixture to use the authenticated version (the conftest fixture now auto-authenticates).

- [ ] **Step 8: Commit**

```bash
git add src/server/super_personal/settings.py src/server/super_personal/urls.py src/server/tests/conftest.py src/server/tests/test_api_views.py
git commit -m "feat: add DRF session auth + 30/min throttle + test fixtures"
```

---

### Task 2: Create login page template

**Files:**
- Create: `src/server/templates/registration/login.html`

Django's built-in `django.contrib.auth.views.LoginView` looks for `registration/login.html`.

- [ ] **Step 1: Create the template directory and file**

Create `src/server/templates/registration/login.html`:

```html
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SuperPersonal — Login</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: { extend: { colors: { primary: { DEFAULT: '#3b82f6' } } } }
        }
    </script>
    <style type="text/tailwindcss">
        body { @apply bg-gray-900 text-white font-sans antialiased; }
        .glass { @apply bg-white/5 backdrop-blur-lg border border-white/10; }
    </style>
</head>
<body class="min-h-screen flex items-center justify-center">
    <div class="glass p-10 rounded-2xl w-full max-w-sm shadow-2xl">
        <h1 class="text-3xl font-bold text-center mb-2">
            <span class="text-primary">Super</span>Personal
        </h1>
        <p class="text-gray-400 text-center text-sm mb-8">System Controller</p>

        {% if form.errors %}
        <div class="bg-red-500/20 border border-red-500/40 rounded-lg px-4 py-2 mb-4 text-sm text-red-300">
            Invalid username or password.
        </div>
        {% endif %}

        <form method="post" class="space-y-4">
            {% csrf_token %}
            <div>
                <label class="block text-gray-400 text-sm mb-1">Username</label>
                <input name="username" type="text" autofocus
                    class="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-primary" />
            </div>
            <div>
                <label class="block text-gray-400 text-sm mb-1">Password</label>
                <input name="password" type="password"
                    class="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-primary" />
            </div>
            <input type="hidden" name="next" value="{{ next }}" />
            <button type="submit"
                class="w-full py-3 bg-primary rounded-lg font-medium hover:bg-blue-500 transition mt-2">
                Sign In
            </button>
        </form>
    </div>
</body>
</html>
```

- [ ] **Step 2: Verify the login page renders**

Start the server:
```
python manage.py runserver
```
Navigate to `http://localhost:8000/accounts/login/` — the styled login page should appear.

- [ ] **Step 3: Commit**

```bash
git add src/server/templates/registration/login.html
git commit -m "feat: add styled login page for Django session auth"
```

---

### Task 3: Protect dashboard views with @login_required

**Files:**
- Modify: `src/server/core/views.py`

- [ ] **Step 1: Write the failing test**

Create `src/server/tests/test_views.py`:

```python
import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestDashboardAuth:
    def test_dashboard_redirects_unauthenticated(self, client):
        response = client.get(reverse('dashboard'))
        assert response.status_code == 302
        assert '/accounts/login/' in response['Location']

    def test_dashboard_accessible_when_logged_in(self, client, django_user_model):
        user = django_user_model.objects.create_user(username='viewer', password='pass123')
        client.force_login(user)
        response = client.get(reverse('dashboard'))
        assert response.status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest src/server/tests/test_views.py -v
```
Expected: FAIL — dashboard returns 200 without auth

- [ ] **Step 3: Add `@login_required` to views in `src/server/core/views.py`**

```python
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from api.models import Tbl_Device, Tbl_Command, Tbl_Preset


@login_required
def dashboard(request):
    devices = Tbl_Device.objects.all().order_by('-last_seen')
    return render(request, 'core/dashboard.html', {'devices': devices})


@login_required
def device_detail(request, pk):
    device = get_object_or_404(Tbl_Device, pk=pk)
    presets = Tbl_Preset.objects.all()
    logs = Tbl_Command.objects.filter(device=device).select_related('log').order_by('-created_at')[:10]
    return render(request, 'core/detail.html', {
        'device': device,
        'presets': presets,
        'logs': logs
    })
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest src/server/tests/test_views.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/server/core/views.py src/server/tests/test_views.py
git commit -m "feat: protect dashboard and device_detail views with @login_required"
```

---

### Task 4: Allow device client to bypass API auth

**Problem:** The device client (`src/client/api_client.py`) uses `requests.Session()` without any credentials. After enabling `IsAuthenticated`, all client API calls (register, poll, result) will return 403.

**Solution:** Device registration and command polling endpoints should allow unauthenticated access from the client. Override the permission class on `DeviceViewSet` and the `pending`/`result` actions on `CommandViewSet`.

**Files:**
- Modify: `src/server/api/views.py`

- [ ] **Step 1: Write the failing test**

Add to `TestCommandAPI` in `test_api_views.py`:

```python
def test_pending_endpoint_accessible_without_auth(self, unauthenticated_api_client):
    device = Tbl_Device.objects.create(hardware_id="noauth-poll-device")
    url = reverse('command-pending') + f"?device_id={device.hardware_id}"
    response = unauthenticated_api_client.get(url)
    assert response.status_code == 200

def test_result_endpoint_accessible_without_auth(self, unauthenticated_api_client):
    device = Tbl_Device.objects.create(hardware_id="noauth-res-device")
    cmd = Tbl_Command.objects.create(device=device, command_type=CommandType.CMD_PING)
    url = reverse('command-result', args=[cmd.pk])
    response = unauthenticated_api_client.post(url, {"status": "SUCCESS", "log": {"output": "Pong"}}, format='json')
    assert response.status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest src/server/tests/test_api_views.py::TestCommandAPI::test_pending_endpoint_accessible_without_auth src/server/tests/test_api_views.py::TestCommandAPI::test_result_endpoint_accessible_without_auth -v
```
Expected: FAIL — returns 403

- [ ] **Step 3: Add `AllowAny` to device and client-facing actions in `src/server/api/views.py`**

```python
from rest_framework.permissions import IsAuthenticated, AllowAny


class DeviceViewSet(viewsets.ModelViewSet):
    queryset = Tbl_Device.objects.all()
    serializer_class = DeviceSerializer
    lookup_field = 'hardware_id'
    permission_classes = [AllowAny]  # Device client registers without user session

    # ... rest of DeviceViewSet unchanged ...


class CommandViewSet(viewsets.ModelViewSet):
    queryset = Tbl_Command.objects.all()
    serializer_class = CommandSerializer
    # Default: IsAuthenticated (web user creates commands)

    def get_permissions(self):
        # Device client polls and posts results without user session
        if self.action in ('pending', 'result'):
            return [AllowAny()]
        return [IsAuthenticated()]

    # ... rest of CommandViewSet unchanged ...
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest src/server/tests/test_api_views.py -v
```
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/server/api/views.py src/server/tests/test_api_views.py
git commit -m "feat: allow device client to access pending/result/register without session auth"
```

---

### Task 5: Create a superuser and verify end-to-end login flow

- [ ] **Step 1: Create a superuser**

From `src/server/`:
```
python manage.py createsuperuser
```
Enter username, email (optional), and password when prompted.

- [ ] **Step 2: Run the server**

```
python manage.py runserver
```

- [ ] **Step 3: Verify redirect when unauthenticated**

Navigate to `http://localhost:8000/`. Should redirect to `http://localhost:8000/accounts/login/?next=/`.

- [ ] **Step 4: Log in**

Enter credentials on login page. Should redirect to the dashboard.

- [ ] **Step 5: Start client and send a command**

```
python -m src.client.client
```
Open device detail, click Screenshot. Result should appear in log without any auth errors.

- [ ] **Step 6: Add logout link to base.html navbar**

In `src/server/templates/base.html`, replace the `Settings` nav link with a logout link:

```html
<a href="{% url 'logout' %}" class="hover:text-white transition-colors">Logout</a>
```

- [ ] **Step 7: Commit**

```bash
git add src/server/templates/base.html
git commit -m "feat: add logout link to navbar"
```

---

### Task 6: Run full test suite

- [ ] **Step 1: Run all tests**

```
pytest src/server/tests/ -v
```
Expected: All tests PASS

- [ ] **Step 2: Commit summary tag**

```bash
git tag v1.0.0 -m "Complete: all 4 sub-projects implemented and tested"
```
