# Dock UI v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace scroll-based device detail page with a desktop-dock UI: live screenshot hero, dock bar with flyout panels, status bar, pipeline, device tabs, keyboard shortcuts, and mobile adaptation.

**Architecture:** Vanilla JS dock registry pattern where each flyout panel registers as a plugin. Single HTML template with CSS Grid layout. All existing API endpoints and client agent unchanged. WebSocket for real-time updates.

**Tech Stack:** Django templates, Tailwind CSS (CDN), vanilla JS (ES2020+ modules), WebSocket

**Prerequisite:** Main branch (all 4 sub-projects + VolumeExecutor fix merged, 54 tests passing, deployed to GCP VM 34.182.12.121:8000)

---

## File Map

| Action | Path |
|---|---|
| Create | `src/server/templates/core/dock.html` — main dock UI template |
| Create | `src/server/static/js/dock/registry.js` — dock item plugin registry |
| Create | `src/server/static/js/dock/dock.js` — dock bar + flyout lifecycle manager |
| Create | `src/server/static/js/dock/items/screenshot.js` — screenshot capture + auto-refresh |
| Create | `src/server/static/js/dock/items/shell.js` — terminal emulator panel |
| Create | `src/server/static/js/dock/items/clipboard.js` — clipboard read/write |
| Create | `src/server/static/js/dock/items/files.js` — file browser tree |
| Create | `src/server/static/js/dock/items/process.js` — process list + kill |
| Create | `src/server/static/js/dock/items/queue.js` — command queue + flow |
| Create | `src/server/static/js/dock/items/volume.js` — volume + media controls |
| Create | `src/server/static/js/dock/items/schedule.js` — schedule picker |
| Create | `src/server/static/js/dock/items/quick.js` — quick action grid |
| Create | `src/server/static/js/dock/items/lock.js` — lock PC confirm |
| Create | `src/server/static/js/status-bar.js` — top status bar |
| Create | `src/server/static/js/pipeline.js` — command flow visualization |
| Create | `src/server/static/js/notifications.js` — toast system |
| Create | `src/server/static/js/keyboard.js` — shortcut handler |
| Create | `src/server/static/js/mobile.js` — mobile adaptation |
| Create | `src/server/static/js/app-v2.js` — entry point, WebSocket, state, device tabs |
| Create | `src/server/static/css/dock.css` — dock-specific styles |
| Modify | `src/server/core/views.py` — add dock view, remove old dashboard/detail |
| Modify | `src/server/core/urls.py` — route to dock view |
| Modify | `src/server/templates/base.html` — update nav for v2 |
| Modify | `src/server/templates/registration/login.html` — redesign |
| Create | `src/server/tests/test_dock_ui.py` — frontend tests for dock UI |

---

### Task 1: Dock registry + dock bar shell

**Files:**
- Create: `src/server/static/js/dock/registry.js`
- Create: `src/server/static/js/dock/dock.js`

- [ ] **Step 1: Write registry tests**

Create `src/server/tests/test_dock_ui.py`:

```python
import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth.models import User


@pytest.mark.django_db
class TestDockUIRenders:
    def test_dock_page_returns_200_when_logged_in(self):
        user = User.objects.create_user(username='dockuser', password='pass123')
        client = Client()
        client.force_login(user)
        response = client.get(reverse('dock'))
        assert response.status_code == 200
        assert 'dock' in response.content.decode().lower()

    def test_dock_device_page_returns_200_when_logged_in(self):
        from api.models import Tbl_Device
        device = Tbl_Device.objects.create(hardware_id='dock-device', hostname='TestDock')
        user = User.objects.create_user(username='dockuser2', password='pass123')
        client = Client()
        client.force_login(user)
        response = client.get(reverse('dock_device', args=[device.pk_device_id]))
        assert response.status_code == 200
        assert 'dock' in response.content.decode().lower()

    def test_dock_page_redirects_when_unauthenticated(self):
        client = Client()
        response = client.get(reverse('dock'))
        assert response.status_code == 302
```

- [ ] **Step 2: Run test, verify FAIL**

```
pytest src/server/tests/test_dock_ui.py -v
```

Expected: FAIL — `reverse('dock')` not found, template doesn't exist

- [ ] **Step 3: Create `src/server/static/js/dock/registry.js`**

```javascript
// dock/registry.js — Dock item plugin registry
const DockRegistry = (() => {
  const items = new Map();

  return {
    register(config) {
      if (items.has(config.id)) {
        console.warn(`Dock item "${config.id}" already registered, overwriting.`);
      }
      items.set(config.id, {
        id: config.id,
        icon: config.icon || '📌',
        label: config.label || config.id,
        shortcut: config.shortcut || null,
        position: config.position || items.size,
        badge: config.badge || (() => null),
        render: config.render || null,
        onOpen: config.onOpen || (() => {}),
        onClose: config.onClose || (() => {}),
        onClick: config.onClick || null, // for items without flyout
        hasFlyout: !!config.render,
      });
    },

    unregister(id) {
      items.delete(id);
    },

    getAll() {
      return [...items.values()].sort((a, b) => a.position - b.position);
    },

    get(id) {
      return items.get(id);
    },
  };
})();
```

- [ ] **Step 4: Create `src/server/static/js/dock/dock.js`**

```javascript
// dock/dock.js — Dock bar + flyout lifecycle
const Dock = (() => {
  let activeFlyout = null;
  let dockEl = null;
  let flyoutEl = null;
  let deviceId = null;

  function init(container, devId) {
    deviceId = devId;
    buildDOM(container);
    renderIcons();
    document.addEventListener('keydown', handleKeydown);
    document.addEventListener('click', handleOutsideClick);
  }

  function buildDOM(container) {
    container.innerHTML = `
      <div id="dock-bar" class="fixed bottom-0 left-0 right-0 flex justify-center items-end gap-1 px-4 pb-2 z-40">
        <div id="dock-icons" class="flex items-end gap-1 bg-black/60 backdrop-blur-lg border border-white/10 rounded-2xl px-3 py-2"></div>
      </div>
      <div id="flyout-container" class="fixed bottom-20 left-1/2 -translate-x-1/2 z-50 hidden"></div>
    `;
    dockEl = document.getElementById('dock-icons');
    flyoutEl = document.getElementById('flyout-container');
  }

  function renderIcons() {
    const items = DockRegistry.getAll();
    let html = '';
    for (const item of items) {
      html += `
        <button id="dock-${item.id}" data-dock-id="${item.id}"
          class="group flex flex-col items-center px-3 py-2 rounded-xl hover:bg-white/10 transition min-w-[64px]"
          title="${item.label}${item.shortcut ? ' (' + item.shortcut + ')' : ''}">
          <span class="text-2xl">${item.icon}</span>
          <span class="text-[10px] text-gray-400 group-hover:text-white mt-0.5">${item.label}</span>
        </button>`;
    }
    dockEl.innerHTML = html;

    // Wire click handlers
    for (const item of items) {
      const btn = document.getElementById(`dock-${item.id}`);
      if (!btn) continue;
      btn.addEventListener('click', () => handleItemClick(item));
    }
    updateBadges();
  }

  function handleItemClick(item) {
    if (activeFlyout === item.id) {
      closeFlyout();
      return;
    }
    if (!item.hasFlyout) {
      if (item.onClick) item.onClick(deviceId);
      return;
    }
    openFlyout(item);
  }

  function openFlyout(item) {
    closeFlyout();
    activeFlyout = item.id;
    flyoutEl.innerHTML = '';
    flyoutEl.classList.remove('hidden');
    flyoutEl.innerHTML = `
      <div class="bg-gray-900/95 backdrop-blur-lg border border-white/10 rounded-2xl w-[400px] max-h-[50vh] overflow-auto p-6 shadow-2xl">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-bold">${item.icon} ${item.label}</h3>
          <button onclick="Dock.closeFlyout()" class="text-gray-500 hover:text-white text-xl leading-none">&times;</button>
        </div>
        <div id="flyout-body"></div>
      </div>`;
    item.render(document.getElementById('flyout-body'), deviceId);
    item.onOpen();
    const btn = document.getElementById(`dock-${item.id}`);
    if (btn) btn.classList.add('bg-white/10');
  }

  function closeFlyout() {
    if (activeFlyout) {
      const item = DockRegistry.get(activeFlyout);
      if (item) {
        item.onClose();
        const btn = document.getElementById(`dock-${item.id}`);
        if (btn) btn.classList.remove('bg-white/10');
      }
    }
    activeFlyout = null;
    flyoutEl.classList.add('hidden');
    flyoutEl.innerHTML = '';
  }

  function updateBadges() {
    for (const item of DockRegistry.getAll()) {
      const count = item.badge();
      const btn = document.getElementById(`dock-${item.id}`);
      if (!btn) continue;
      const existing = btn.querySelector('.dock-badge');
      if (existing) existing.remove();
      if (count) {
        const badge = document.createElement('span');
        badge.className = 'dock-badge absolute -top-1 -right-1 bg-red-500 text-white text-[10px] rounded-full w-5 h-5 flex items-center justify-center font-bold';
        badge.textContent = count > 9 ? '9+' : count;
        btn.style.position = 'relative';
        btn.appendChild(badge);
      }
    }
  }

  function handleKeydown(e) {
    if (e.key === 'Escape') { closeFlyout(); return; }
    const items = DockRegistry.getAll();
    for (const item of items) {
      if (item.shortcut && matchesShortcut(e, item.shortcut)) {
        e.preventDefault();
        if (item.hasFlyout) {
          if (activeFlyout === item.id) closeFlyout();
          else openFlyout(item);
        } else if (item.onClick) {
          item.onClick(deviceId);
        }
        return;
      }
    }
  }

  function matchesShortcut(e, shortcut) {
    const parts = shortcut.toLowerCase().split('+');
    const ctrl = parts.includes('ctrl');
    const key = parts[parts.length - 1];
    return e.ctrlKey === ctrl && e.key.toLowerCase() === key;
  }

  function handleOutsideClick(e) {
    if (flyoutEl && !flyoutEl.contains(e.target) && !e.target.closest('[data-dock-id]')) {
      closeFlyout();
    }
  }

  function setDeviceId(devId) { deviceId = devId; }

  return { init, closeFlyout, updateBadges, setDeviceId, getDeviceId: () => deviceId };
})();
```

- [ ] **Step 5: Create `src/server/templates/core/dock.html`** (minimal shell)

```html
{% extends 'base.html' %}
{% load static %}

{% block content %}
<div id="dock-app" class="fixed inset-0 bg-gray-950 text-white overflow-hidden">
  <!-- Status Bar -->
  <div id="status-bar" class="fixed top-0 left-0 right-0 h-8 bg-black/40 backdrop-blur border-b border-white/5 flex items-center px-4 text-xs text-gray-400 z-30 gap-4">
    <span id="sb-status">🟡 Connecting...</span>
    <span id="sb-stats">CPU --% RAM --%</span>
    <span class="flex-1"></span>
    <span id="sb-latency">--ms</span>
    <span id="sb-poll">↑ --</span>
    <span id="sb-queue">Queue: 0</span>
  </div>

  <!-- Pipeline -->
  <div id="pipeline" class="fixed top-8 left-0 right-0 h-6 bg-black/30 backdrop-blur border-b border-white/5 flex items-center justify-center gap-1 text-[10px] text-gray-500 z-30">
    <span id="pl-client" class="px-1.5">CLIENT</span>→
    <span id="pl-fetch" class="px-1.5">FETCH</span>→
    <span id="pl-pending" class="px-1.5">PENDING</span>→
    <span id="pl-sent" class="px-1.5">SENT</span>→
    <span id="pl-running" class="px-1.5">RUNNING</span>→
    <span id="pl-result" class="px-1.5">RESULT</span>
  </div>
  <div id="pipeline-active" class="fixed top-[56px] left-0 right-0 text-center text-xs text-gray-400 z-30">No active command</div>

  <!-- Device Tabs -->
  <div id="device-tabs" class="fixed top-[72px] left-0 right-0 flex items-center gap-1 px-4 py-1 z-30 overflow-x-auto">
    <!-- filled by JS -->
  </div>

  <!-- Screenshot Hero -->
  <div id="screenshot-hero" class="absolute inset-0 flex items-center justify-center bg-gray-950">
    <p class="text-gray-600 text-lg">No screenshot yet. Click 📸 Snap to capture.</p>
  </div>
  <img id="screenshot-img" class="absolute inset-0 w-full h-full object-contain hidden" alt="Live screenshot" />

  <!-- Toast Container -->
  <div id="toast-container" class="fixed top-20 right-4 z-50 flex flex-col gap-2"></div>

  <!-- Dock Bar (filled by dock.js) -->
  <div id="dock-container"></div>
</div>
{% endblock %}

{% block extra_js %}
<script src="{% static 'js/dock/registry.js' %}"></script>
<script src="{% static 'js/dock/dock.js' %}"></script>
<script src="{% static 'js/status-bar.js' %}"></script>
<script src="{% static 'js/pipeline.js' %}"></script>
<script src="{% static 'js/notifications.js' %}"></script>
<script src="{% static 'js/keyboard.js' %}"></script>
<script src="{% static 'js/app-v2.js' %}"></script>
{% endblock %}
```

- [ ] **Step 6: Create stub JS files to avoid 404s**

Create stub files for every JS file that doesn't exist yet:

```bash
# Create all stub files for items not yet built
echo "// status-bar.js stub" > src/server/static/js/status-bar.js
echo "// pipeline.js stub" > src/server/static/js/pipeline.js
echo "// notifications.js stub" > src/server/static/js/notifications.js
echo "// keyboard.js stub" > src/server/static/js/keyboard.js
echo "// app-v2.js stub - will be replaced" > src/server/static/js/app-v2.js
mkdir -p src/server/static/js/dock/items
```

- [ ] **Step 7: Wire Django view + URL**

In `src/server/core/views.py`, add:

```python
def dock(request):
    """Dock UI v2 — default view (first device or empty)."""
    from api.models import Tbl_Device
    first_device = Tbl_Device.objects.order_by('-last_seen').first()
    return render(request, 'core/dock.html', {
        'device': first_device,
        'devices': Tbl_Device.objects.all().order_by('-last_seen')
    })


def dock_device(request, pk):
    """Dock UI v2 — scoped to a specific device."""
    from api.models import Tbl_Device
    device = get_object_or_404(Tbl_Device, pk=pk)
    return render(request, 'core/dock.html', {
        'device': device,
        'devices': Tbl_Device.objects.all().order_by('-last_seen')
    })
```

In `src/server/core/urls.py`, update:

```python
from django.urls import path
from . import views

urlpatterns = [
    path('', views.dock, name='dock'),  # was: views.dashboard, name='dashboard'
    path('device/<uuid:pk>/', views.dock_device, name='dock_device'),  # was: views.device_detail, name='device_detail'
]
```

- [ ] **Step 8: Run tests, verify PASS**

```
pytest src/server/tests/test_dock_ui.py tests/ -v
```

Expected: dock UI tests pass, no regressions

- [ ] **Step 9: Commit**

```bash
git add src/server/static/js/dock/registry.js src/server/static/js/dock/dock.js src/server/static/js/status-bar.js src/server/static/js/pipeline.js src/server/static/js/notifications.js src/server/static/js/keyboard.js src/server/static/js/app-v2.js src/server/templates/core/dock.html src/server/core/views.py src/server/core/urls.py src/server/tests/test_dock_ui.py
git commit -m "feat: add dock registry, dock bar shell, and dock html template"
```

---

### Task 2: WebSocket + state management (app-v2.js)

**Files:**
- Overwrite: `src/server/static/js/app-v2.js`
- Modify: `src/server/static/js/status-bar.js`
- Modify: `src/server/static/js/pipeline.js`

- [ ] **Step 1: Write full `app-v2.js`**

```javascript
// app-v2.js — Entry point, WebSocket, state management, device tabs
const AppState = {
  devices: [],
  activeDeviceId: null,
  commands: {},
  activeCommand: null,
  screenshot: null,
  screenshotInterval: null,
  screenshotIntervalSec: 30,
  clientStatus: 'offline',
  lastPoll: null,
  systemInfo: { cpu: 0, ram: 0 },
  serverUrl: window.location.origin,
};

const App = (() => {
  let socket = null;
  let reconnectTimer = null;
  let systemInfoTimer = null;

  function init() {
    const deviceIdFromServer = document.getElementById('dock-app')?.dataset?.deviceId;
    if (deviceIdFromServer) {
      AppState.activeDeviceId = deviceIdFromServer;
    }
    connectWebSocket();
    refreshDevices();
    if (AppState.activeDeviceId) {
      startSystemInfoPoll();
    }
    renderDeviceTabs();
  }

  function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/dashboard/`;
    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      AppState.clientStatus = 'online';
      StatusBar.update();
      if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null; }
      if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
      }
    };

    socket.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      handleWSMessage(msg);
    };

    socket.onclose = () => {
      AppState.clientStatus = 'reconnecting';
      StatusBar.update();
      reconnectTimer = setTimeout(connectWebSocket, 3000);
    };
  }

  function handleWSMessage(msg) {
    if (msg.type === 'device_update') {
      refreshDevices();
      StatusBar.update();
    } else if (msg.type === 'command_update') {
      handleCommandUpdate(msg.data);
    }
  }

  function handleCommandUpdate(data) {
    AppState.commands[data.id] = data;
    const status = data.status;

    if (status === 'RUNNING') {
      AppState.activeCommand = data;
    } else if (status === 'SUCCESS' || status === 'FAILED') {
      if (AppState.activeCommand && AppState.activeCommand.id === data.id) {
        AppState.activeCommand = null;
      }
    }

    Pipeline.update();
    Dock.updateBadges();
    StatusBar.update();
    Notifications.toast(data);

    if (status === 'SUCCESS' || status === 'FAILED') {
      Notifications.push(`${data.type || 'Command'} ${status}`,
        (data.output || '').substring(0, 80));
    }

    // Dispatch to specific handlers
    if (data.type === 'CMD_LIST_PROCESSES' && window.handleProcessList) {
      window.handleProcessList(data.output || '');
    }
    if (data.type === 'CMD_FILE_LIST' && window.handleFileList) {
      window.handleFileList(data.output || '');
    }
    if (data.type === 'CMD_CLIPBOARD_GET' && window.handleClipboardGet) {
      window.handleClipboardGet(data.output || '');
    }
    if (data.type === 'CMD_FILE_READ' && window.handleFileRead) {
      window.handleFileRead(data.output || '');
    }
  }

  async function refreshDevices() {
    try {
      const r = await fetch(`${AppState.serverUrl}/api/v1/devices/`);
      if (r.ok) {
        AppState.devices = await r.json();
        if (!AppState.activeDeviceId && AppState.devices.length > 0) {
          AppState.activeDeviceId = AppState.devices[0].pk_device_id;
          startSystemInfoPoll();
        }
        renderDeviceTabs();
      }
    } catch (e) {
      console.warn('Device refresh failed:', e);
    }
  }

  function renderDeviceTabs() {
    const tabs = document.getElementById('device-tabs');
    if (!tabs) return;
    let html = '';
    for (const d of AppState.devices) {
      const active = d.pk_device_id === AppState.activeDeviceId;
      const dot = d.is_active ? '🟢' : '🟡';
      html += `<button data-device-id="${d.pk_device_id}"
        class="px-3 py-1 rounded-lg text-xs whitespace-nowrap transition ${active ? 'bg-white/10 text-white' : 'text-gray-500 hover:text-white hover:bg-white/5'}">
        ${dot} ${d.hostname || d.hardware_id.substring(0, 8)}
      </button>`;
    }
    html += `<button onclick="alert('Install client on new PC:\\npip install -r requirements.txt\\npython -m src.client.client')"
      class="px-3 py-1 rounded-lg text-xs text-gray-600 hover:text-white hover:bg-white/5 transition">+ Add Device</button>`;
    tabs.innerHTML = html;

    // Wire click handlers
    tabs.querySelectorAll('[data-device-id]').forEach(btn => {
      btn.addEventListener('click', () => switchDevice(btn.dataset.deviceId));
    });
  }

  function switchDevice(deviceId) {
    AppState.activeDeviceId = deviceId;
    AppState.screenshot = null;
    AppState.activeCommand = null;
    const img = document.getElementById('screenshot-img');
    const placeholder = document.getElementById('screenshot-hero');
    if (img) img.classList.add('hidden');
    if (placeholder) placeholder.classList.remove('hidden');
    Dock.setDeviceId(deviceId);
    renderDeviceTabs();
    StatusBar.update();
    Pipeline.update();
    startSystemInfoPoll();
    history.replaceState(null, '', `/device/${deviceId}/`);
  }

  async function sendCommand(type, extra = {}) {
    if (!AppState.activeDeviceId) return;
    try {
      const csrf = getCSRF();
      const body = { device: AppState.activeDeviceId, command_type: type, payload: extra };
      const r = await fetch(`${AppState.serverUrl}/api/v1/commands/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
        body: JSON.stringify(body),
      });
      if (!r.ok) {
        const err = await r.json();
        Notifications.toast({ type, status: 'FAILED', output: err.detail || 'Request failed' });
      }
    } catch (e) {
      Notifications.toast({ type, status: 'FAILED', output: 'Network error' });
    }
  }

  function getCSRF() {
    const cookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
    return cookie ? cookie.split('=')[1] : '';
  }

  function startSystemInfoPoll() {
    if (systemInfoTimer) clearInterval(systemInfoTimer);
    systemInfoTimer = setInterval(async () => {
      if (!AppState.activeDeviceId) return;
      try {
        const r = await fetch(`${AppState.serverUrl}/api/v1/commands/pending/?device_id=DUMMY`);
        // We just care that the server is reachable
        const start = performance.now();
        await fetch(`${AppState.serverUrl}/api/v1/devices/`);
        StatusBar.setLatency(Math.round(performance.now() - start));
      } catch (e) {}
    }, 30000);
  }

  function setSystemInfo(cpu, ram) {
    AppState.systemInfo = { cpu, ram };
    StatusBar.update();
  }

  return { init, sendCommand, switchDevice, setSystemInfo, getState: () => AppState };
})();

document.addEventListener('DOMContentLoaded', () => App.init());
```

- [ ] **Step 2: Write `status-bar.js`**

```javascript
// status-bar.js — Top status bar
const StatusBar = (() => {
  function update() {
    const state = App.getState();
    const statusEl = document.getElementById('sb-status');
    const statsEl = document.getElementById('sb-stats');
    const latencyEl = document.getElementById('sb-latency');
    const pollEl = document.getElementById('sb-poll');
    const queueEl = document.getElementById('sb-queue');

    if (statusEl) {
      const dot = state.clientStatus === 'online' ? '🟢' :
                 state.clientStatus === 'reconnecting' ? '🟡' : '🔴';
      statusEl.textContent = `${dot} ${state.clientStatus}`;
    }
    if (statsEl) {
      statsEl.textContent = `CPU ${state.systemInfo.cpu.toFixed(1)}% RAM ${state.systemInfo.ram.toFixed(1)}%`;
    }
    if (queueEl) {
      const count = Object.values(state.commands).filter(c =>
        ['PENDING', 'SENT', 'RUNNING'].includes(c.status)
      ).length;
      queueEl.textContent = `Queue: ${count}`;
    }
  }

  function setLatency(ms) {
    const el = document.getElementById('sb-latency');
    if (el) el.textContent = `${ms}ms`;
  }

  return { update, setLatency };
})();
```

- [ ] **Step 3: Write `pipeline.js`**

```javascript
// pipeline.js — Command flow visualization
const Pipeline = (() => {
  const stages = ['client', 'fetch', 'pending', 'sent', 'running', 'result'];

  function update() {
    const state = App.getState();
    const activeEl = document.getElementById('pipeline-active');

    // Reset all stages
    for (const s of stages) {
      const el = document.getElementById(`pl-${s}`);
      if (el) el.className = 'px-1.5';
    }

    if (state.activeCommand) {
      // Highlight relevant stages
      const status = state.activeCommand.status;
      const highlightMap = {
        'PENDING': ['client', 'fetch', 'pending'],
        'SENT': ['client', 'fetch', 'pending', 'sent'],
        'RUNNING': ['client', 'fetch', 'pending', 'sent', 'running'],
        'SUCCESS': ['client', 'fetch', 'pending', 'sent', 'running', 'result'],
        'FAILED': ['client', 'fetch', 'pending', 'sent', 'running', 'result'],
      };
      const toHighlight = highlightMap[status] || [];
      for (const s of toHighlight) {
        const el = document.getElementById(`pl-${s}`);
        if (el) {
          el.className = status === 'FAILED' && s === 'result'
            ? 'px-1.5 text-red-400'
            : 'px-1.5 text-green-400';
        }
      }

      if (activeEl) {
        const dot = status === 'RUNNING' ? '●' : '○';
        activeEl.innerHTML = `<span class="${status === 'RUNNING' ? 'animate-pulse text-yellow-400' : status === 'SUCCESS' ? 'text-green-400' : status === 'FAILED' ? 'text-red-400' : 'text-blue-400'}">${dot} ${state.activeCommand.type || 'Command'} ${status}</span>`;
      }
    } else {
      if (activeEl) activeEl.textContent = 'No active command';
    }
  }

  return { update };
})();
```

- [ ] **Step 4: Run tests**

```
pytest src/server/tests/test_dock_ui.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/server/static/js/app-v2.js src/server/static/js/status-bar.js src/server/static/js/pipeline.js
git commit -m "feat: add app state, WebSocket, status bar, and pipeline"
```

---

### Task 3: Screenshot hero + notifications

**Files:**
- Create: `src/server/static/js/dock/items/screenshot.js`
- Modify: `src/server/static/js/notifications.js`
- Modify: `src/server/static/js/app-v2.js` — auto-refresh support

- [ ] **Step 1: Write `screenshot.js`**

```javascript
// dock/items/screenshot.js
DockRegistry.register({
  id: 'snap',
  icon: '📸',
  label: 'Snap',
  shortcut: 'Ctrl+1',
  position: 0,
  render(container, deviceId) {
    container.innerHTML = `
      <div class="space-y-3">
        <p class="text-xs text-gray-400">Capture a screenshot of the remote desktop.</p>
        <button onclick="App.sendCommand('CMD_SCREENSHOT');Dock.closeFlyout();"
          class="w-full py-2 bg-blue-600/30 border border-blue-500/40 rounded-lg hover:bg-blue-600/50 transition text-sm">
          Capture Now
        </button>
        <div class="flex items-center gap-2 text-xs text-gray-400">
          <span>Auto-refresh:</span>
          <button onclick="ScreenshotHero.setInterval(0)" class="px-2 py-1 rounded border border-white/10 hover:bg-white/10">Off</button>
          <button onclick="ScreenshotHero.setInterval(10)" class="px-2 py-1 rounded border border-white/10 hover:bg-white/10">10s</button>
          <button onclick="ScreenshotHero.setInterval(30)" class="px-2 py-1 rounded border border-white/10 hover:bg-white/10">30s</button>
        </div>
      </div>`;
  },
});

const ScreenshotHero = (() => {
  let timer = null;
  let interval = 0;

  function setInterval(sec) {
    interval = sec;
    if (timer) clearInterval(timer);
    if (sec > 0) {
      timer = setInterval(() => App.sendCommand('CMD_SCREENSHOT'), sec * 1000);
    }
  }

  function show(base64Url) {
    const state = App.getState();
    state.screenshot = base64Url;
    const placeholder = document.getElementById('screenshot-hero');
    const img = document.getElementById('screenshot-img');
    if (placeholder) placeholder.classList.add('hidden');
    if (img) {
      img.src = base64Url;
      img.classList.remove('hidden');
    }
  }

  return { setInterval, show, getInterval: () => interval };
})();

// Override command update to capture screenshots
const origHandleCommandUpdate = App.sendCommand;
App.sendCommand = function(type, extra) {
  return origHandleCommandUpdate.call(App, type, extra);
};

// Wire the screenshot result handler
window._origHandleWS = App.handleCommandUpdate || (() => {});
```

- [ ] **Step 2: Write `notifications.js`**

```javascript
// notifications.js — Toast + browser push notifications
const Notifications = (() => {
  function toast(data) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const statusColor = data.status === 'SUCCESS' ? 'border-green-500/40 bg-green-500/10' :
                        data.status === 'FAILED' ? 'border-red-500/40 bg-red-500/10' :
                        'border-blue-500/40 bg-blue-500/10';
    const toastEl = document.createElement('div');
    toastEl.className = `glass border rounded-lg px-4 py-2 text-sm shadow-lg transition-all ${statusColor} slide-in`;
    toastEl.innerHTML = `<span class="font-bold">${data.type || 'Command'}</span> ${data.status}<br>
      <span class="text-xs text-gray-400">${(data.output || '').substring(0, 80)}</span>`;
    container.appendChild(toastEl);
    setTimeout(() => {
      toastEl.style.opacity = '0';
      toastEl.style.transform = 'translateX(100%)';
      setTimeout(() => toastEl.remove(), 300);
    }, 4000);
  }

  function push(title, body) {
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification(title, { body, icon: '/static/img/icon.png' });
    }
  }

  return { toast, push };
})();
```

- [ ] **Step 3: Add screenshot handler in app-v2.js**

In `handleCommandUpdate`, after the existing type dispatches, add:

```javascript
if (data.output && data.output.startsWith('data:image/')) {
  ScreenshotHero.show(data.output);
}
if (data.type === 'CMD_SYSTEM_INFO' && data.output) {
  const parts = data.output.match(/CPU:\s*([\d.]+).*RAM:\s*([\d.]+)/);
  if (parts) {
    App.setSystemInfo(parseFloat(parts[1]), parseFloat(parts[2]));
  }
}
```

- [ ] **Step 4: Load new scripts in dock.html**

Add to the `{% block extra_js %}` before `</script>`:

```html
<script src="{% static 'js/dock/items/screenshot.js' %}"></script>
```

- [ ] **Step 5: Commit**

```bash
git add src/server/static/js/dock/items/screenshot.js src/server/static/js/notifications.js src/server/static/js/app-v2.js src/server/templates/core/dock.html
git commit -m "feat: add screenshot hero with auto-refresh and toast notifications"
```

---

### Task 4: Shell + Clipboard flyouts

**Files:**
- Create: `src/server/static/js/dock/items/shell.js`
- Create: `src/server/static/js/dock/items/clipboard.js`

- [ ] **Step 1: Write `shell.js`**

```javascript
// dock/items/shell.js
DockRegistry.register({
  id: 'shell',
  icon: '💻',
  label: 'Shell',
  shortcut: 'Ctrl+2',
  position: 1,
  render(container, deviceId) {
    container.innerHTML = `
      <div id="shell-output" class="bg-black rounded-lg p-3 text-xs font-mono text-green-400 h-48 overflow-y-auto mb-3 whitespace-pre-wrap"></div>
      <div class="flex gap-2">
        <input id="shell-input" type="text" placeholder="Type a command..."
          class="flex-1 bg-black/60 border border-white/10 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:border-primary"
          onkeydown="if(event.key==='Enter')ShellPanel.send()" />
        <button onclick="ShellPanel.send()"
          class="px-4 py-2 bg-green-600/30 border border-green-500/40 rounded-lg hover:bg-green-600/50 transition text-sm">Run</button>
      </div>`;
  },
  onOpen() {
    setTimeout(() => {
      const input = document.getElementById('shell-input');
      if (input) input.focus();
    }, 100);
  },
});

const ShellPanel = (() => {
  const history = [];
  let historyIdx = 0;

  function send() {
    const input = document.getElementById('shell-input');
    if (!input || !input.value.trim()) return;
    const cmd = input.value.trim();
    history.push(cmd);
    historyIdx = history.length;
    const output = document.getElementById('shell-output');
    if (output) {
      output.innerHTML += `<div class="text-white">$ ${cmd}</div>`;
      output.scrollTop = output.scrollHeight;
    }
    input.value = '';

    const origHandler = window._origHandleWS;
    // Send command and listen for result
    const csrf = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
    const csrfToken = csrf ? csrf.split('=')[1] : '';
    const state = App.getState();
    fetch(`${state.serverUrl}/api/v1/commands/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
      body: JSON.stringify({ device: state.activeDeviceId, command_type: 'CMD_SHELL_EXEC', payload: { command_str: cmd } }),
    }).then(r => r.json()).then(data => {
      // Result comes via WebSocket — displayed by handleCommandUpdate override
    });
  }

  function appendOutput(text) {
    const output = document.getElementById('shell-output');
    if (!output) return;
    const escaped = text.replace(/</g, '&lt;').replace(/>/g, '&gt;');
    output.innerHTML += `<div class="text-gray-300">${escaped}</div>`;
    output.scrollTop = output.scrollHeight;
  }

  return { send, appendOutput };
})();
```

- [ ] **Step 2: Write `clipboard.js`**

```javascript
// dock/items/clipboard.js
DockRegistry.register({
  id: 'clip',
  icon: '📋',
  label: 'Clip',
  shortcut: 'Ctrl+3',
  position: 2,
  render(container, deviceId) {
    container.innerHTML = `
      <div class="space-y-3">
        <button onclick="App.sendCommand('CMD_CLIPBOARD_GET')"
          class="w-full py-2 bg-teal-600/30 border border-teal-500/40 rounded-lg hover:bg-teal-600/50 transition text-sm">
          Read Clipboard
        </button>
        <div class="flex gap-2">
          <input id="clip-input" type="text" placeholder="Text to set..."
            class="flex-1 bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary" />
          <button onclick="ClipPanel.set()"
            class="px-4 py-2 bg-teal-600/30 border border-teal-500/40 rounded-lg hover:bg-teal-600/50 transition text-sm">Set</button>
        </div>
        <div id="clip-preview" class="bg-black/40 rounded-lg p-3 text-xs text-gray-400 min-h-[2rem] max-h-24 overflow-y-auto hidden"></div>
      </div>`;
  },
});

const ClipPanel = (() => {
  function set() {
    const input = document.getElementById('clip-input');
    if (!input || !input.value.trim()) return;
    App.sendCommand('CMD_CLIPBOARD_SET', { text: input.value.trim() });
    input.value = '';
  }

  return { set };
})();

window.handleClipboardGet = function(output) {
  const input = document.getElementById('clip-input');
  const preview = document.getElementById('clip-preview');
  if (input) input.value = output || '';
  if (preview) {
    preview.textContent = output || '';
    preview.classList.remove('hidden');
  }
};
```

- [ ] **Step 3: Add to dock.html script block**

```html
<script src="{% static 'js/dock/items/shell.js' %}"></script>
<script src="{% static 'js/dock/items/clipboard.js' %}"></script>
```

- [ ] **Step 4: Add shell result handler in app-v2.js handleCommandUpdate**

```javascript
if (data.type === 'CMD_SHELL_EXEC' && window.ShellPanel) {
  ShellPanel.appendOutput(data.output || '');
}
```

- [ ] **Step 5: Commit**

```bash
git add src/server/static/js/dock/items/shell.js src/server/static/js/dock/items/clipboard.js src/server/templates/core/dock.html src/server/static/js/app-v2.js
git commit -m "feat: add shell terminal and clipboard flyout panels"
```

---

### Task 5: Files + Process flyouts

**Files:**
- Create: `src/server/static/js/dock/items/files.js`
- Create: `src/server/static/js/dock/items/process.js`

- [ ] **Step 1: Write `process.js`**

```javascript
// dock/items/process.js
DockRegistry.register({
  id: 'proc',
  icon: '🔧',
  label: 'Proc',
  shortcut: 'Ctrl+5',
  position: 4,
  render(container, deviceId) {
    container.innerHTML = `
      <div class="flex items-center gap-2 mb-3">
        <input id="proc-search" type="text" placeholder="Filter by name..."
          class="flex-1 bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-primary"
          oninput="ProcessPanel.filter()" />
        <button onclick="ProcessPanel.refresh()"
          class="px-3 py-2 bg-purple-600/30 border border-purple-500/40 rounded-lg hover:bg-purple-600/50 transition text-xs">Refresh</button>
      </div>
      <div id="proc-table" class="overflow-auto max-h-64 text-xs"></div>`;
    ProcessPanel.refresh();
  },
});

const ProcessPanel = (() => {
  let allProcesses = [];

  function refresh() {
    const orig = window.handleProcessList;
    window.handleProcessList = function(output) {
      try {
        allProcesses = JSON.parse(output);
        renderTable(allProcesses);
      } catch(e) {
        document.getElementById('proc-table').innerHTML = `<p class="text-red-400">${output}</p>`;
      }
      window.handleProcessList = orig;
    };
    App.sendCommand('CMD_LIST_PROCESSES');
  }

  function filter() {
    const q = document.getElementById('proc-search')?.value?.toLowerCase() || '';
    const filtered = q ? allProcesses.filter(p => (p.name || '').toLowerCase().includes(q)) : allProcesses;
    renderTable(filtered);
  }

  function kill(pid) {
    if (!confirm(`Kill PID ${pid}?`)) return;
    App.sendCommand('CMD_KILL_PROCESS', { pid: parseInt(pid) });
    setTimeout(refresh, 2000);
  }

  function renderTable(procs) {
    const el = document.getElementById('proc-table');
    if (!el) return;
    let html = '<table class="w-full"><thead><tr class="text-gray-500 border-b border-white/10"><th class="text-left py-1">PID</th><th class="text-left py-1">Name</th><th class="text-right py-1">MEM%</th><th class="py-1"></th></tr></thead><tbody>';
    for (const p of procs.slice(0, 50)) {
      html += `<tr class="border-b border-white/5 hover:bg-white/5">
        <td class="py-1 font-mono">${p.pid}</td>
        <td class="py-1">${(p.name || '-').replace(/</g,'&lt;')}</td>
        <td class="py-1 text-right text-purple-400">${(p.memory_percent||0).toFixed(1)}%</td>
        <td class="py-1 text-right"><button onclick="ProcessPanel.kill(${p.pid})" class="text-red-400 hover:text-red-200 text-xs px-2">Kill</button></td>
      </tr>`;
    }
    html += '</tbody></table>';
    el.innerHTML = html;
  }

  return { refresh, filter, kill };
})();

window.handleProcessList = function(output) {
  // handled by ProcessPanel.refresh if panel is open, else no-op
};
```

- [ ] **Step 2: Write `files.js`**

```javascript
// dock/items/files.js
DockRegistry.register({
  id: 'files',
  icon: '📁',
  label: 'Files',
  shortcut: 'Ctrl+4',
  position: 3,
  render(container, deviceId) {
    container.innerHTML = `
      <div class="flex gap-2 mb-3">
        <input id="files-path" type="text" value="C:/" placeholder="Path..."
          class="flex-1 bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-xs font-mono focus:outline-none focus:border-primary"
          onkeydown="if(event.key==='Enter')FilesPanel.browse()" />
        <button onclick="FilesPanel.browse()"
          class="px-3 py-2 bg-indigo-600/30 border border-indigo-500/40 rounded-lg hover:bg-indigo-600/50 transition text-xs">Browse</button>
      </div>
      <div id="files-list" class="overflow-auto max-h-64 text-xs"></div>
      <div id="files-preview" class="hidden mt-3 bg-black/40 rounded-lg p-3 text-xs max-h-32 overflow-auto whitespace-pre-wrap"></div>`;
  },
});

const FilesPanel = (() => {
  function browse() {
    const input = document.getElementById('files-path');
    if (!input) return;
    const path = input.value.trim();
    if (!path) return;
    App.sendCommand('CMD_FILE_LIST', { path });
  }

  function readFile(path) {
    App.sendCommand('CMD_FILE_READ', { path });
  }

  function navigateTo(path) {
    const input = document.getElementById('files-path');
    if (input) input.value = path;
    browse();
  }

  return { browse, readFile, navigateTo };
})();

window.handleFileList = function(output) {
  const el = document.getElementById('files-list');
  if (!el) return;
  try {
    const items = JSON.parse(output);
    let html = '<ul class="space-y-0.5">';
    for (const item of items) {
      const icon = item.type === 'dir' ? '📁' : '📄';
      const size = item.size != null ? `<span class="text-gray-600 ml-2">${(item.size/1024).toFixed(1)}KB</span>` : '';
      const name = item.name.replace(/</g, '&lt;').replace(/>/g, '&gt;');
      const path = (item.path || '').replace(/\\/g, '\\\\');
      if (item.type === 'dir') {
        html += `<li class="hover:bg-white/5 rounded px-2 py-0.5 cursor-pointer" onclick="FilesPanel.navigateTo('${path}')">${icon} ${name}</li>`;
      } else {
        html += `<li class="hover:bg-white/5 rounded px-2 py-0.5 flex justify-between items-center">
          <span>${icon} ${name}${size}</span>
          <button onclick="FilesPanel.readFile('${path}')" class="text-primary hover:text-white text-[10px] ml-2">View</button>
        </li>`;
      }
    }
    html += '</ul>';
    el.innerHTML = html;
  } catch(e) {
    el.innerHTML = `<p class="text-red-400">${output}</p>`;
  }
};

window.handleFileRead = function(output) {
  const preview = document.getElementById('files-preview');
  if (!preview) return;
  preview.classList.remove('hidden');
  preview.textContent = output;
};
```

- [ ] **Step 3: Add to dock.html**

```html
<script src="{% static 'js/dock/items/files.js' %}"></script>
<script src="{% static 'js/dock/items/process.js' %}"></script>
```

- [ ] **Step 4: Commit**

```bash
git add src/server/static/js/dock/items/files.js src/server/static/js/dock/items/process.js src/server/templates/core/dock.html
git commit -m "feat: add file browser and process manager flyout panels"
```

---

### Task 6: Queue + Volume + Schedule + Quick + Lock flyouts

**Files:**
- Create: `src/server/static/js/dock/items/queue.js`
- Create: `src/server/static/js/dock/items/volume.js`
- Create: `src/server/static/js/dock/items/schedule.js`
- Create: `src/server/static/js/dock/items/quick.js`
- Create: `src/server/static/js/dock/items/lock.js`

- [ ] **Step 1: Write `queue.js`**

```javascript
// dock/items/queue.js
DockRegistry.register({
  id: 'queue',
  icon: '📊',
  label: 'Queue',
  shortcut: 'Ctrl+J',
  position: 9,
  badge() {
    const state = App.getState();
    return Object.values(state.commands).filter(c =>
      ['PENDING', 'SENT', 'RUNNING'].includes(c.status)
    ).length;
  },
  render(container, deviceId) {
    container.innerHTML = `
      <div class="text-xs mb-2 text-gray-400">
        <span class="text-gray-500">PENDING</span> → <span class="text-blue-400">SENT</span> → <span class="text-yellow-400">RUNNING</span> → <span class="text-green-400">SUCCESS</span> / <span class="text-red-400">FAILED</span>
      </div>
      <div id="queue-list" class="space-y-1 max-h-48 overflow-y-auto text-xs"></div>
      <button onclick="QueuePanel.clearCompleted()"
        class="mt-3 w-full py-1.5 bg-gray-700/50 rounded-lg hover:bg-gray-600/50 transition text-xs">Clear Completed</button>`;
    render();
  },
  onOpen() { QueuePanel.render(); },
});

const QueuePanel = (() => {
  function render() {
    const el = document.getElementById('queue-list');
    if (!el) return;
    const state = App.getState();
    const cmds = Object.values(state.commands).sort((a, b) =>
      (b.created_at || '').localeCompare(a.created_at || '')
    );
    if (cmds.length === 0) {
      el.innerHTML = '<p class="text-gray-500 italic">No commands yet.</p>';
      return;
    }
    const statusColors = {
      PENDING: 'text-gray-400', SENT: 'text-blue-400',
      RUNNING: 'text-yellow-400 animate-pulse', SUCCESS: 'text-green-400', FAILED: 'text-red-400',
    };
    let html = '';
    for (const c of cmds.slice(0, 50)) {
      const cls = statusColors[c.status] || 'text-gray-400';
      html += `<div class="flex items-center justify-between border-b border-white/5 py-1 hover:bg-white/5 rounded px-1">
        <span class="font-mono text-[10px] text-gray-500">${(c.id || '').substring(0,8)}</span>
        <span>${c.type || '?'}</span>
        <span class="${cls}">${c.status}</span>
        <span class="text-gray-600 text-[10px]">${(c.created_at || '').substring(11,19)}</span>
      </div>`;
    }
    el.innerHTML = html;
  }

  function clearCompleted() {
    const state = App.getState();
    for (const [id, cmd] of Object.entries(state.commands)) {
      if (cmd.status === 'SUCCESS' || cmd.status === 'FAILED') {
        delete state.commands[id];
      }
    }
    render();
    Dock.updateBadges();
    Pipeline.update();
  }

  return { render, clearCompleted };
})();
```

- [ ] **Step 2: Write `volume.js`**

```javascript
// dock/items/volume.js
DockRegistry.register({
  id: 'sound',
  icon: '🔊',
  label: 'Sound',
  position: 6,
  render(container, deviceId) {
    container.innerHTML = `
      <label class="text-xs text-gray-400">Volume</label>
      <input id="vol-slider" type="range" min="0" max="100" value="50"
        class="w-full mt-1 mb-4 accent-blue-500"
        onchange="VolumePanel.setLevel(this.value)" />
      <div class="flex justify-between text-xs text-gray-500 mb-3">
        <span>0%</span><span id="vol-label">50%</span><span>100%</span>
      </div>
      <div class="flex justify-between">
        <button onclick="VolumePanel.toggleMute()"
          class="px-4 py-2 bg-yellow-600/30 border border-yellow-500/40 rounded-lg hover:bg-yellow-600/50 transition text-sm">🔇 Mute</button>
        <div class="flex gap-1">
          <button onclick="VolumePanel.media('prev')" class="px-3 py-2 bg-white/5 rounded-lg hover:bg-white/10 text-sm">⏮</button>
          <button onclick="VolumePanel.media('play_pause')" class="px-3 py-2 bg-white/5 rounded-lg hover:bg-white/10 text-sm">▶</button>
          <button onclick="VolumePanel.media('next')" class="px-3 py-2 bg-white/5 rounded-lg hover:bg-white/10 text-sm">⏭</button>
        </div>
      </div>`;
  },
});

const VolumePanel = (() => {
  function setLevel(val) {
    document.getElementById('vol-label').textContent = val + '%';
    App.sendCommand('CMD_SET_VOLUME', { level: parseInt(val) });
  }
  function toggleMute() {
    App.sendCommand('CMD_SET_VOLUME', { mute: true });
  }
  function media(action) {
    App.sendCommand('CMD_MEDIA', { action });
  }
  return { setLevel, toggleMute, media };
})();
```

- [ ] **Step 3: Write `schedule.js`, `quick.js`, `lock.js`**

```javascript
// dock/items/schedule.js
DockRegistry.register({
  id: 'sched',
  icon: '⏰',
  label: 'Sched',
  position: 7,
  render(container, deviceId) {
    container.innerHTML = `
      <div class="space-y-3">
        <select id="sched-type" class="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm"
          onchange="document.getElementById('sched-shell-row').classList.toggle('hidden', this.value!=='CMD_SHELL_EXEC')">
          <option value="CMD_SCREENSHOT">Screenshot</option>
          <option value="CMD_SYSTEM_INFO">System Info</option>
          <option value="CMD_PING">Ping</option>
          <option value="CMD_LOCK_PC">Lock PC</option>
          <option value="CMD_SHUTDOWN">Shutdown</option>
          <option value="CMD_SHELL_EXEC">Shell Exec</option>
        </select>
        <div id="sched-shell-row" class="hidden">
          <input id="sched-shell-input" type="text" placeholder="Shell command..."
            class="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm font-mono" />
        </div>
        <input id="sched-datetime" type="datetime-local"
          class="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm" />
        <button onclick="SchedulePanel.submit()"
          class="w-full py-2 bg-yellow-600/30 border border-yellow-500/40 rounded-lg hover:bg-yellow-600/50 transition text-sm">Schedule</button>
      </div>`;
  },
  onOpen() {
    const dt = new Date(Date.now() + 5 * 60 * 1000);
    const local = new Date(dt.getTime() - dt.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
    document.getElementById('sched-datetime').value = local;
  },
});

const SchedulePanel = (() => {
  async function submit() {
    const type = document.getElementById('sched-type').value;
    const dt = document.getElementById('sched-datetime').value;
    if (!dt) return;
    const payload = {};
    if (type === 'CMD_SHELL_EXEC') {
      payload.command_str = document.getElementById('sched-shell-input').value;
    }
    const state = App.getState();
    const csrf = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
    const body = {
      device: state.activeDeviceId,
      command_type: type,
      payload,
      scheduled_for: new Date(dt).toISOString(),
    };
    const r = await fetch(`${state.serverUrl}/api/v1/commands/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf ? csrf.split('=')[1] : '' },
      body: JSON.stringify(body),
    });
    if (r.ok) {
      Notifications.toast({ type, status: 'SUCCESS', output: `Scheduled for ${dt}` });
      Dock.closeFlyout();
    }
  }
  return { submit };
})();
```

```javascript
// dock/items/quick.js
DockRegistry.register({
  id: 'quick',
  icon: '⚡',
  label: 'Quick',
  position: 8,
  render(container, deviceId) {
    const actions = [
      { label: 'Ping', type: 'CMD_PING', color: 'blue' },
      { label: 'Sys Info', type: 'CMD_SYSTEM_INFO', color: 'green' },
      { label: 'Restart', type: 'CMD_RESTART', color: 'red' },
      { label: 'Shutdown', type: 'CMD_SHUTDOWN', color: 'red' },
      { label: 'Lock PC', type: 'CMD_LOCK_PC', color: 'yellow' },
      { label: 'Browser', type: 'CMD_OPEN_BROWSER', color: 'purple' },
    ];
    let html = '<div class="grid grid-cols-3 gap-2">';
    for (const a of actions) {
      html += `<button onclick="QuickPanel.fire('${a.type}')"
        class="p-3 bg-${a.color}-600/20 border border-${a.color}-500/30 rounded-xl hover:bg-${a.color}-600/40 transition text-sm">${a.label}</button>`;
    }
    html += '</div>';
    container.innerHTML = html;
  },
});

const QuickPanel = (() => ({
  fire(type) {
    if (type === 'CMD_SHUTDOWN' || type === 'CMD_RESTART') {
      if (!confirm(`Are you sure you want to ${type === 'CMD_RESTART' ? 'restart' : 'shutdown'}?`)) return;
    }
    App.sendCommand(type);
    Dock.closeFlyout();
  },
}))();
```

```javascript
// dock/items/lock.js
DockRegistry.register({
  id: 'lock',
  icon: '🔒',
  label: 'Lock',
  shortcut: 'Ctrl+L',
  position: 5,
  onClick(deviceId) {
    if (confirm('Lock the remote PC?')) {
      App.sendCommand('CMD_LOCK_PC');
      Notifications.toast({ type: 'CMD_LOCK_PC', status: 'SUCCESS', output: 'PC locking...' });
    }
  },
});
```

- [ ] **Step 4: Add scripts to dock.html**

```html
<script src="{% static 'js/dock/items/queue.js' %}"></script>
<script src="{% static 'js/dock/items/volume.js' %}"></script>
<script src="{% static 'js/dock/items/schedule.js' %}"></script>
<script src="{% static 'js/dock/items/quick.js' %}"></script>
<script src="{% static 'js/dock/items/lock.js' %}"></script>
```

- [ ] **Step 5: Commit**

```bash
git add src/server/static/js/dock/items/queue.js src/server/static/js/dock/items/volume.js src/server/static/js/dock/items/schedule.js src/server/static/js/dock/items/quick.js src/server/static/js/dock/items/lock.js src/server/templates/core/dock.html
git commit -m "feat: add queue, volume, schedule, quick actions, and lock dock items"
```

---

### Task 7: Keyboard shortcuts + mobile adaptation

**Files:**
- Overwrite: `src/server/static/js/keyboard.js`
- Create: `src/server/static/js/mobile.js`
- Create: `src/server/static/css/dock.css`

- [ ] **Step 1: Write `keyboard.js`**

```javascript
// keyboard.js — Global keyboard shortcut handler
document.addEventListener('keydown', function(e) {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') {
    if (e.key === 'Escape') { e.target.blur(); }
    return; // Don't steal focus from inputs
  }

  const shortcuts = {
    'ctrl+1': () => App.sendCommand('CMD_SCREENSHOT'),
    'ctrl+l': () => {
      if (confirm('Lock the remote PC?')) App.sendCommand('CMD_LOCK_PC');
    },
    'ctrl+k': () => {
      const q = prompt('Quick command: ping / lock / screenshot / system / shell');
      if (!q) return;
      const map = {
        'ping': 'CMD_PING', 'lock': 'CMD_LOCK_PC', 'screenshot': 'CMD_SCREENSHOT',
        'system': 'CMD_SYSTEM_INFO', 'shell': 'CMD_SHELL_EXEC',
      };
      const type = map[q.toLowerCase()];
      if (type) App.sendCommand(type);
    },
  };

  const keys = [];
  if (e.ctrlKey) keys.push('ctrl');
  if (e.altKey) keys.push('alt');
  if (e.shiftKey) keys.push('shift');
  keys.push(e.key.toLowerCase());
  const combo = keys.join('+');

  if (shortcuts[combo]) {
    e.preventDefault();
    shortcuts[combo]();
    return;
  }

  // Device tab switching
  const state = App.getState();
  if (e.key === 'ArrowLeft' && e.ctrlKey) {
    e.preventDefault();
    const idx = state.devices.findIndex(d => d.pk_device_id === state.activeDeviceId);
    if (idx > 0) App.switchDevice(state.devices[idx - 1].pk_device_id);
  }
  if (e.key === 'ArrowRight' && e.ctrlKey) {
    e.preventDefault();
    const idx = state.devices.findIndex(d => d.pk_device_id === state.activeDeviceId);
    if (idx < state.devices.length - 1) App.switchDevice(state.devices[idx + 1].pk_device_id);
  }

  // F5 = manual screenshot
  if (e.key === 'F5') {
    e.preventDefault();
    App.sendCommand('CMD_SCREENSHOT');
  }
});
```

- [ ] **Step 2: Write `dock.css`**

```css
/* dock.css — Dock-specific + mobile styles */

/* Toast slide-in animation */
@keyframes slideIn {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}
.slide-in { animation: slideIn 0.3s ease-out; }

/* Flyout transition */
#flyout-container {
  transition: all 0.3s ease-out;
  animation: flyoutUp 0.3s ease-out;
}
@keyframes flyoutUp {
  from { transform: translate(-50%, 20px); opacity: 0; }
  to { transform: translate(-50%, 0); opacity: 1; }
}

/* Screenshot hero */
#screenshot-img {
  object-fit: contain;
}

/* Mobile adaptation */
@media (max-width: 767px) {
  #status-bar {
    font-size: 10px;
    gap: 8px;
    padding: 0 8px;
  }
  #status-bar span:last-child,
  #status-bar span:nth-last-child(2) {
    /* keep only most important */
  }
  #pipeline, #pipeline-active {
    display: none;
  }
  #device-tabs {
    top: 32px;
    gap: 2px;
  }
  #screenshot-hero {
    top: 56px;
    bottom: 140px;
  }
  #screenshot-img {
    top: 56px;
    bottom: 140px;
  }
  #dock-bar {
    padding: 4px;
  }
  #dock-icons {
    gap: 2px;
    padding: 6px 8px;
    flex-wrap: wrap;
    justify-content: center;
  }
  #dock-icons button {
    min-width: 56px;
    padding: 6px 8px;
  }
  #dock-icons button span:first-child {
    font-size: 1.25rem;
  }
  #dock-icons button span:last-child {
    font-size: 8px;
  }
  #flyout-container {
    width: 100% !important;
    left: 0 !important;
    right: 0 !important;
    transform: none !important;
    bottom: 120px;
    padding: 0 8px;
  }
  #flyout-container > div {
    width: 100% !important;
    max-height: 40vh !important;
  }
}
```

- [ ] **Step 3: Add to dock.html**

```html
<link rel="stylesheet" href="{% static 'css/dock.css' %}">
<!-- in extra_js block -->
<script src="{% static 'js/keyboard.js' %}"></script>
```

- [ ] **Step 4: Commit**

```bash
git add src/server/static/js/keyboard.js src/server/static/css/dock.css src/server/templates/core/dock.html
git commit -m "feat: add keyboard shortcuts and mobile-responsive styles"
```

---

### Task 8: Login page redesign + base.html update

**Files:**
- Overwrite: `src/server/templates/registration/login.html`
- Modify: `src/server/templates/base.html`

- [ ] **Step 1: Rewrite `login.html`**

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
        body { @apply bg-gray-950 text-white font-sans antialiased; }
        .glass { @apply bg-white/5 backdrop-blur-lg border border-white/10; }
    </style>
</head>
<body class="min-h-screen flex items-center justify-center bg-gray-950 relative overflow-hidden">
    <!-- Subtle grid background -->
    <div class="absolute inset-0 opacity-[0.03]"
         style="background-image: radial-gradient(circle at 1px 1px, white 1px, transparent 0); background-size: 40px 40px;"></div>

    <div class="glass p-10 rounded-2xl w-full max-w-sm shadow-2xl relative z-10">
        <div class="text-center mb-8">
            <div class="text-5xl mb-3">🖥️</div>
            <h1 class="text-3xl font-bold">
                <span class="text-primary">Super</span>Personal
            </h1>
            <p class="text-gray-500 text-sm mt-1">Remote System Controller</p>
        </div>

        {% if form.errors %}
        <div class="bg-red-500/20 border border-red-500/40 rounded-lg px-4 py-2 mb-4 text-sm text-red-300">
            Invalid username or password.
        </div>
        {% endif %}

        {% if user.is_authenticated %}
        <p class="text-center text-gray-400 text-sm mb-4">Logged in as <strong>{{ user.username }}</strong>.</p>
        <a href="/" class="block w-full text-center py-3 bg-primary rounded-lg font-medium hover:bg-blue-500 transition">
            Open Dashboard
        </a>
        {% else %}
        <form method="post" class="space-y-4">
            {% csrf_token %}
            <div>
                <label class="block text-gray-400 text-sm mb-1">Username</label>
                <input name="username" type="text" autofocus autocomplete="username"
                    class="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-primary transition" />
            </div>
            <div>
                <label class="block text-gray-400 text-sm mb-1">Password</label>
                <input name="password" type="password" autocomplete="current-password"
                    class="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-primary transition" />
            </div>
            <input type="hidden" name="next" value="{{ next }}" />
            <button type="submit"
                class="w-full py-3 bg-primary rounded-lg font-medium hover:bg-blue-500 transition mt-2">
                Sign In
            </button>
        </form>
        {% endif %}
    </div>
</body>
</html>
```

- [ ] **Step 2: Update base.html nav**

Replace the nav links with:

```html
{% if user.is_authenticated %}
<a href="/" class="text-sm text-gray-400 hover:text-white transition">Dashboard</a>
<form method="post" action="{% url 'logout' %}" class="inline">
    {% csrf_token %}
    <button type="submit" class="text-sm text-gray-500 hover:text-white transition">Logout</button>
</form>
{% endif %}
```

- [ ] **Step 3: Run frontend tests**

```
pytest src/server/tests/test_frontend.py src/server/tests/test_dock_ui.py src/server/tests/test_views.py -v
```

Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add src/server/templates/registration/login.html src/server/templates/base.html
git commit -m "feat: redesign login page and update base nav for dock UI"
```

---

### Task 9: Integration — update views, remove old templates, run full suite

**Files:**
- Modify: `src/server/core/views.py` — clean up old views
- Modify: `src/server/tests/test_frontend.py` — update to dock URLs

- [ ] **Step 1: Clean old views**

Remove `dashboard` and `device_detail` functions from `core/views.py`. Keep only `dock` and `dock_device`.

Also remove the `@login_required` from old views that no longer exist.

- [ ] **Step 2: Update frontend tests**

```python
# In test_frontend.py, update to use dock URLs
class TestFrontendViews:
    def test_dock_view(self, client, django_user_model):
        user = django_user_model.objects.create_user(username='frontend', password='pass')
        client.force_login(user)
        response = client.get(reverse('dock'))
        assert response.status_code == 200
        assert 'dock' in response.content.decode().lower()

    def test_dock_device_view(self, client, django_user_model):
        from api.models import Tbl_Device
        device = Tbl_Device.objects.create(hardware_id='frontend-device', hostname='FE Test')
        user = django_user_model.objects.create_user(username='frontend2', password='pass')
        client.force_login(user)
        response = client.get(reverse('dock_device', args=[device.pk_device_id]))
        assert response.status_code == 200
```

- [ ] **Step 3: Run full test suite**

```
pytest src/server/tests/ -v
```

Expected: All tests PASS (around 56-58)

- [ ] **Step 4: Delete old templates**

Remove `templates/core/dashboard.html` and `templates/core/detail.html` (keep them in git history).

- [ ] **Step 5: Commit**

```bash
git rm src/server/templates/core/dashboard.html src/server/templates/core/detail.html
git add src/server/core/views.py src/server/tests/test_frontend.py
git commit -m "feat: finalize dock UI — remove old templates, update views and tests"
```

---

### Task 10: Deploy to VM and smoke test

- [ ] **Step 1: Push to GitHub**

```bash
git push origin fix-ci-config-v2
```

- [ ] **Step 2: SSH to VM and pull**

```bash
ssh -o ClearAllForwardings=yes personal "cd ~/SuperPersonal && git fetch origin fix-ci-config-v2 && git checkout -f origin/fix-ci-config-v2 -B fix-ci-config-v2 && source venv/bin/activate && cd src/server && python manage.py migrate && python -m pytest tests/ -q && pkill -f daphne; sleep 1; nohup daphne -b 0.0.0.0 -p 8000 super_personal.asgi:application > /tmp/superpersonal-server.log 2>&1 &"
```

- [ ] **Step 3: Verify public access**

```
curl -s -o /dev/null -w "%{http_code}" http://34.182.12.121:8000/
curl -s -o /dev/null -w "%{http_code}" http://34.182.12.121:8000/accounts/login/
```

Expected: 302 (redirect to login), 200 (login page)

- [ ] **Step 4: Manual browser smoke test**

1. Open `http://34.182.12.121:8000/`
2. Login as `admin` / `admin123`
3. Verify dock bar appears at bottom
4. Click 📸 Snap → Capture Now → verify screenshot appears
5. Click 📊 Queue → verify queue panel opens
6. Test keyboard shortcut: Ctrl+1 for screenshot
7. Test on mobile viewport (F12 responsive mode)
