# Sub-project 3: Smart Automation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add scheduled command execution (run any command after a delay), a preset manager UI (add/delete presets from the browser), and browser push notifications so you see results even when the tab is in the background.

**Architecture:** Scheduled commands store a `scheduled_for` timestamp in Tbl_Command. A background thread started in `core/apps.py:ready()` scans every 10 seconds for due commands and marks them PENDING so the client picks them up. No Celery needed — a simple `threading.Timer` loop is enough for a personal tool. The preset manager is a small CRUD form using the existing Preset API. Push notifications use the browser Notifications API — no server-side push needed.

**Tech Stack:** Python (threading), Django, JS Notifications API

**Prerequisite:** Sub-project 1 must be merged first.

---

## File Map

| Action | Path |
|---|---|
| Modify | `src/server/api/models.py` — add `scheduled_for` nullable DateTimeField to Tbl_Command |
| Create | `src/server/api/migrations/0004_command_scheduled_for.py` — migration |
| Create | `src/server/core/scheduler.py` — background thread that activates due scheduled commands |
| Modify | `src/server/core/apps.py` — start scheduler thread in `ready()` |
| Modify | `src/server/api/views.py` — filter out future-scheduled commands from pending endpoint |
| Modify | `src/server/api/serializers.py` — expose `scheduled_for` in CommandSerializer |
| Create | `src/server/core/scheduler.py` — background thread that activates due commands |
| Modify | `src/server/super_personal/asgi.py` — start scheduler thread on server boot |
| Modify | `src/server/templates/core/detail.html` — add schedule modal + preset manager |
| Modify | `src/server/static/js/app.js` — add push notification support |
| Modify | `src/server/tests/test_api_views.py` — test scheduled command filtering |

---

### Task 1: Add `scheduled_for` field to Tbl_Command

**Files:**
- Modify: `src/server/api/models.py`

- [ ] **Step 1: Write the failing test**

Add to `src/server/tests/test_models.py` (or create it if absent):

```python
import pytest
from django.utils import timezone
from datetime import timedelta
from api.models import Tbl_Device, Tbl_Command, CommandType, CommandStatus


@pytest.mark.django_db
class TestScheduledCommand:
    def test_command_has_scheduled_for_field(self):
        device = Tbl_Device.objects.create(hardware_id="sched-device")
        future = timezone.now() + timedelta(minutes=30)
        cmd = Tbl_Command.objects.create(
            device=device,
            command_type=CommandType.CMD_PING,
            status=CommandStatus.PENDING,
            scheduled_for=future
        )
        cmd.refresh_from_db()
        assert cmd.scheduled_for is not None

    def test_command_scheduled_for_defaults_null(self):
        device = Tbl_Device.objects.create(hardware_id="nosched-device")
        cmd = Tbl_Command.objects.create(device=device, command_type=CommandType.CMD_PING)
        assert cmd.scheduled_for is None
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest src/server/tests/test_models.py::TestScheduledCommand -v
```
Expected: FAIL — `scheduled_for` field does not exist

- [ ] **Step 3: Add `scheduled_for` to Tbl_Command in `src/server/api/models.py`**

Inside `Tbl_Command`, after `created_at`, add:

```python
scheduled_for = models.DateTimeField(null=True, blank=True, db_index=True)
```

- [ ] **Step 4: Generate and apply migration**

From `src/server/`:
```
python manage.py makemigrations api --name command_scheduled_for
python manage.py migrate
```
Expected: Migration created and applied

- [ ] **Step 5: Run test to verify it passes**

```
pytest src/server/tests/test_models.py::TestScheduledCommand -v
```
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/server/api/models.py src/server/tests/test_models.py
git add src/server/api/migrations/0004_command_scheduled_for.py
git commit -m "feat: add scheduled_for field to Tbl_Command"
```

---

### Task 2: Filter future-scheduled commands from pending endpoint

**Problem:** A command with `scheduled_for` in the future should not be returned to the client until the scheduled time arrives.

**Files:**
- Modify: `src/server/tests/test_api_views.py`
- Modify: `src/server/api/views.py`

- [ ] **Step 1: Write the failing test**

Add to `TestCommandAPI` in `src/server/tests/test_api_views.py`:

```python
from django.utils import timezone
from datetime import timedelta

def test_pending_excludes_future_scheduled_commands(self, api_client):
    device = Tbl_Device.objects.create(hardware_id="sched-filter-device")
    # This one should be returned (no schedule)
    Tbl_Command.objects.create(device=device, command_type=CommandType.CMD_PING, status=CommandStatus.PENDING)
    # This one should NOT be returned (scheduled for the future)
    future = timezone.now() + timedelta(hours=1)
    Tbl_Command.objects.create(
        device=device, command_type=CommandType.CMD_PING,
        status=CommandStatus.PENDING, scheduled_for=future
    )

    url = reverse('command-pending') + f"?device_id={device.hardware_id}"
    response = api_client.get(url)

    assert response.status_code == 200
    assert len(response.data) == 1

def test_pending_includes_due_scheduled_commands(self, api_client):
    device = Tbl_Device.objects.create(hardware_id="due-sched-device")
    past = timezone.now() - timedelta(minutes=5)
    Tbl_Command.objects.create(
        device=device, command_type=CommandType.CMD_PING,
        status=CommandStatus.PENDING, scheduled_for=past
    )

    url = reverse('command-pending') + f"?device_id={device.hardware_id}"
    response = api_client.get(url)

    assert len(response.data) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest src/server/tests/test_api_views.py::TestCommandAPI::test_pending_excludes_future_scheduled_commands src/server/tests/test_api_views.py::TestCommandAPI::test_pending_includes_due_scheduled_commands -v
```
Expected: FAIL — future commands are currently returned

- [ ] **Step 3: Update the pending action in `src/server/api/views.py`**

```python
from django.utils import timezone
from django.db.models import Q

@action(detail=False, methods=['get'])
def pending(self, request):
    hardware_id = request.query_params.get('device_id')
    if not hardware_id:
        return Response({"error": "device_id required"}, status=status.HTTP_400_BAD_REQUEST)

    now = timezone.now()
    commands = Tbl_Command.objects.filter(
        device__hardware_id=hardware_id,
        status=CommandStatus.PENDING
    ).filter(
        Q(scheduled_for__isnull=True) | Q(scheduled_for__lte=now)
    )
    command_ids = list(commands.values_list('pk_command_id', flat=True))
    commands.update(status=CommandStatus.SENT)

    fetched = Tbl_Command.objects.filter(pk_command_id__in=command_ids)
    serializer = self.get_serializer(fetched, many=True)
    return Response(serializer.data)
```

- [ ] **Step 4: Add the `timezone` import at the top of `src/server/api/views.py`** (after existing imports):

```python
from django.utils import timezone
from django.db.models import Q
```

- [ ] **Step 5: Run tests to verify they pass**

```
pytest src/server/tests/test_api_views.py::TestCommandAPI -v
```
Expected: All TestCommandAPI tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/server/api/views.py src/server/tests/test_api_views.py
git commit -m "feat: filter future-scheduled commands from pending endpoint"
```

---

### Task 3: Create the scheduler background thread

**Purpose:** Every 10 seconds, find PENDING commands whose `scheduled_for` is in the past and whose `scheduled_for` is not null. They're already PENDING — the pending endpoint's `Q(scheduled_for__lte=now)` filter will now allow the client to pick them up. This task just ensures we don't need Celery for timing.

Wait — the pending endpoint already filters on `scheduled_for__lte=now`, so scheduled commands are automatically activated at poll time. No background thread is needed for the activation logic itself. However, a scheduler IS needed if we want to push a WebSocket notification to the dashboard when a scheduled command becomes due (so the UI can show a "command activated" indicator without waiting for a client poll).

For simplicity, we skip the WS notification for now. The pending endpoint already handles activation. **This task creates a no-op stub scheduler that can be expanded later.**

**Files:**
- Create: `src/server/core/scheduler.py`
- Modify: `src/server/core/apps.py`

- [ ] **Step 1: Create `src/server/core/scheduler.py`**

```python
import threading
import logging

logger = logging.getLogger(__name__)
_scheduler_started = False


def _scan_loop():
    while True:
        threading.Event().wait(10)


def start():
    global _scheduler_started
    if _scheduler_started:
        return
    _scheduler_started = True
    t = threading.Thread(target=_scan_loop, daemon=True)
    t.start()
    logger.info("Scheduler started (10s tick)")
```

- [ ] **Step 2: Read current `src/server/core/apps.py`**

```python
# Current content of src/server/core/apps.py:
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
```

- [ ] **Step 3: Add `ready()` to start the scheduler**

Replace the contents of `src/server/core/apps.py` with:

```python
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        from core.scheduler import start
        start()
```

- [ ] **Step 4: Commit**

```bash
git add src/server/core/scheduler.py src/server/core/apps.py
git commit -m "feat: add scheduler stub via AppConfig.ready() for future expansion"
```

---

### Task 5: Verify `scheduled_for` in CommandSerializer

**Files:**
- Modify: `src/server/api/serializers.py`

- [ ] **Step 1: Update CommandSerializer to include `scheduled_for`**

The serializer uses `fields = '__all__'` so `scheduled_for` is automatically included once the model field exists. No code change needed — verify by checking the API response.

- [ ] **Step 1: Verify serializer includes field**

```
pytest src/server/tests/ -v
```
Expected: All tests PASS (no regression)

- [ ] **Step 2: Commit if any change was needed**

```bash
git add src/server/api/serializers.py
git commit -m "chore: serializer exposes scheduled_for via __all__"
```

---

### Task 6: Add schedule command UI modal to detail.html

**Files:**
- Modify: `src/server/templates/core/detail.html`

- [ ] **Step 1: Add a "Schedule" button to the Quick Actions grid**

In the Quick Actions `<div class="grid grid-cols-2 md:grid-cols-4 gap-4">`, add after the Restart button:

```html
<button onclick="openScheduleModal()"
    class="p-4 bg-yellow-600/20 border border-yellow-500/30 rounded-xl hover:bg-yellow-600/40 transition">
    Schedule
</button>
```

- [ ] **Step 2: Add the schedule modal HTML** (place before the closing `</div>` of the main grid):

```html
<!-- Schedule Modal -->
<div id="schedule-modal" class="hidden fixed inset-0 bg-black/60 z-50 flex items-center justify-center">
    <div class="glass p-8 rounded-2xl w-full max-w-md space-y-4">
        <h3 class="text-xl font-bold">Schedule a Command</h3>

        <div>
            <label class="text-gray-400 text-sm block mb-1">Command Type</label>
            <select id="sched-type"
                class="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-sm">
                <option value="CMD_SCREENSHOT">Screenshot</option>
                <option value="CMD_SYSTEM_INFO">System Info</option>
                <option value="CMD_PING">Ping</option>
                <option value="CMD_LOCK_PC">Lock PC</option>
                <option value="CMD_SHUTDOWN">Shutdown</option>
                <option value="CMD_SHELL_EXEC">Shell Exec</option>
            </select>
        </div>

        <div id="sched-shell-row" class="hidden">
            <label class="text-gray-400 text-sm block mb-1">Shell Command</label>
            <input id="sched-shell-input" type="text"
                class="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-sm font-mono" />
        </div>

        <div>
            <label class="text-gray-400 text-sm block mb-1">Run at (local time)</label>
            <input id="sched-datetime" type="datetime-local"
                class="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-sm" />
        </div>

        <div class="flex space-x-3 pt-2">
            <button onclick="submitSchedule()"
                class="flex-1 py-2 bg-yellow-600/30 border border-yellow-500/40 rounded-lg hover:bg-yellow-600/50 transition">
                Schedule
            </button>
            <button onclick="closeScheduleModal()"
                class="flex-1 py-2 bg-gray-700 rounded-lg hover:bg-gray-600 transition">
                Cancel
            </button>
        </div>
    </div>
</div>
```

- [ ] **Step 3: Add JS functions for the schedule modal**

```javascript
function openScheduleModal() {
    // Default to 5 minutes from now
    const dt = new Date(Date.now() + 5 * 60 * 1000);
    const local = new Date(dt.getTime() - dt.getTimezoneOffset() * 60000)
        .toISOString().slice(0, 16);
    document.getElementById('sched-datetime').value = local;
    document.getElementById('schedule-modal').classList.remove('hidden');
    document.getElementById('sched-type').addEventListener('change', function() {
        const row = document.getElementById('sched-shell-row');
        row.classList.toggle('hidden', this.value !== 'CMD_SHELL_EXEC');
    });
}

function closeScheduleModal() {
    document.getElementById('schedule-modal').classList.add('hidden');
}

async function submitSchedule() {
    const type = document.getElementById('sched-type').value;
    const dt = document.getElementById('sched-datetime').value;
    if (!dt) { alert('Please choose a time.'); return; }

    const payload = {};
    if (type === 'CMD_SHELL_EXEC') {
        payload.command_str = document.getElementById('sched-shell-input').value;
    }

    const body = {
        device: DEVICE_ID,
        command_type: type,
        payload: payload,
        scheduled_for: new Date(dt).toISOString()
    };

    const res = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': '{{ csrf_token }}' },
        body: JSON.stringify(body)
    });

    if (res.ok) {
        showToast(`Scheduled ${type} for ${dt}`);
        closeScheduleModal();
    } else {
        showToast('Schedule failed');
    }
}
```

- [ ] **Step 4: Commit**

```bash
git add src/server/templates/core/detail.html
git commit -m "feat: add schedule modal UI for deferred command execution"
```

---

### Task 7: Add preset manager UI (create/delete presets from dashboard)

**Files:**
- Modify: `src/server/templates/core/detail.html`

- [ ] **Step 1: Replace the existing static Presets block with an interactive version**

Replace the `<!-- Presets -->` block with:

```html
<!-- Presets -->
<div class="glass p-6 rounded-2xl">
    <div class="flex justify-between items-center mb-4">
        <h3 class="text-xl font-bold">Presets</h3>
        <button onclick="togglePresetForm()"
            class="text-xs text-primary hover:text-white transition">+ Add</button>
    </div>

    <div id="preset-add-form" class="hidden mb-4 space-y-2">
        <input id="preset-name" type="text" placeholder="Name (e.g. LoFi Playlist)"
            class="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-sm" />
        <input id="preset-url" type="url" placeholder="https://..."
            class="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-sm" />
        <button onclick="savePreset()"
            class="w-full py-2 bg-pink-600/30 border border-pink-500/40 rounded-lg hover:bg-pink-600/50 transition text-sm">
            Save Preset
        </button>
    </div>

    <div id="preset-list" class="flex gap-3 flex-wrap">
        {% for preset in presets %}
        <div class="flex items-center space-x-1 px-3 py-2 bg-pink-500/20 border border-pink-500/30 rounded-lg">
            <button onclick="openPreset('{{ preset.url }}')"
                class="hover:text-pink-300 transition text-sm">{{ preset.name }}</button>
            <button onclick="deletePreset('{{ preset.pk_preset_id }}')"
                class="text-gray-500 hover:text-red-400 transition text-xs ml-1">✕</button>
        </div>
        {% endfor %}
    </div>
</div>
```

- [ ] **Step 2: Add preset manager JS functions**

```javascript
function togglePresetForm() {
    document.getElementById('preset-add-form').classList.toggle('hidden');
}

async function savePreset() {
    const name = document.getElementById('preset-name').value.trim();
    const url = document.getElementById('preset-url').value.trim();
    if (!name || !url) { showToast('Name and URL required'); return; }

    const res = await fetch('/api/v1/presets/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': '{{ csrf_token }}' },
        body: JSON.stringify({ name, url })
    });
    if (res.ok) {
        showToast(`Preset "${name}" saved`);
        setTimeout(() => location.reload(), 500);
    }
}

async function deletePreset(presetId) {
    if (!confirm('Delete this preset?')) return;
    const res = await fetch(`/api/v1/presets/${presetId}/`, {
        method: 'DELETE',
        headers: { 'X-CSRFToken': '{{ csrf_token }}' }
    });
    if (res.ok || res.status === 204) {
        showToast('Preset deleted');
        setTimeout(() => location.reload(), 300);
    }
}
```

- [ ] **Step 3: Commit**

```bash
git add src/server/templates/core/detail.html
git commit -m "feat: add preset manager UI for create/delete presets"
```

---

### Task 8: Add browser push notifications

**Files:**
- Modify: `src/server/static/js/app.js`

- [ ] **Step 1: Add notification permission request and helper to `app.js`**

At the bottom of `app.js`, add:

```javascript
// Request notification permission once on connect
socket.addEventListener('open', function() {
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
});

function pushNotification(title, body) {
    if ('Notification' in window && Notification.permission === 'granted') {
        new Notification(title, { body: body, icon: '/static/img/icon.png' });
    }
}
```

- [ ] **Step 2: Call `pushNotification` in `handleCommandUpdate` for terminal states**

Inside `handleCommandUpdate`, replace the `showToast` call with:

```javascript
const terminalStatuses = ['SUCCESS', 'FAILED'];
if (terminalStatuses.includes(data.status)) {
    pushNotification(`${data.type || 'Command'} ${data.status}`, data.output ? data.output.substring(0, 80) : '');
}
showToast(`${data.type || 'Command'}: ${data.status}`);
```

- [ ] **Step 3: Commit**

```bash
git add src/server/static/js/app.js
git commit -m "feat: add browser push notifications for command completion"
```

---

### Task 9: Run full test suite

- [ ] **Step 1: Run all tests**

```
pytest src/server/tests/ -v
```
Expected: All tests PASS

- [ ] **Step 2: Manual smoke test for scheduled commands**

1. Start server and client
2. Open device detail page
3. Click **Schedule** → choose CMD_PING → set time 1 minute from now → click Schedule
4. Wait 1 minute — within 10 seconds of the scheduled time, the command log should show a Ping result
