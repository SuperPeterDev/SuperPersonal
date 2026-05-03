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
    const deviceElement = document.querySelector('[data-device-id]');
    const deviceIdFromDom = deviceElement ? deviceElement.dataset.deviceId : null;
    if (deviceIdFromDom) {
      AppState.activeDeviceId = deviceIdFromDom;
    }
    connectWebSocket();
    refreshDevices();
    if (AppState.activeDeviceId) {
      startSystemInfoPoll();
    }
    Dock.init(document.getElementById('dock-container'), AppState.activeDeviceId);
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

    // Dispatch to dock item handlers
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
    // Screenshot detection
    if (data.output && data.output.startsWith('data:image/')) {
      if (typeof ScreenshotHero !== 'undefined') ScreenshotHero.show(data.output);
    }
    // System info parsing
    if (data.type === 'CMD_SYSTEM_INFO' && data.output) {
      const parts = data.output.match(/CPU:\s*([\d.]+).*RAM:\s*([\d.]+)/);
      if (parts) {
        AppState.systemInfo = { cpu: parseFloat(parts[1]), ram: parseFloat(parts[2]) };
        StatusBar.update();
      }
    }
    // Shell output
    if (data.type === 'CMD_SHELL_EXEC' && typeof ShellPanel !== 'undefined') {
      ShellPanel.appendOutput(data.output || '');
    }
  }

  async function refreshDevices() {
    try {
      const r = await fetch(`${AppState.serverUrl}/api/v1/devices/`);
      if (r.ok) {
        AppState.devices = await r.json();
        if (!AppState.activeDeviceId && AppState.devices.length > 0) {
          AppState.activeDeviceId = AppState.devices[0].pk_device_id;
          Dock.setDeviceId(AppState.activeDeviceId);
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
    html += `<button onclick="alert('Install client: pip install -r requirements.txt && python -m src.client.client')"
      class="px-3 py-1 rounded-lg text-xs text-gray-600 hover:text-white hover:bg-white/5 transition">+ Add Device</button>`;
    tabs.innerHTML = html;

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
    window.history.replaceState(null, '', `/device/${deviceId}/`);
  }

  async function sendCommand(type, extra = {}) {
    if (!AppState.activeDeviceId) return;
    try {
      const cookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
      const csrf = cookie ? cookie.split('=')[1] : '';
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

  function startSystemInfoPoll() {
    if (systemInfoTimer) clearInterval(systemInfoTimer);
    systemInfoTimer = setInterval(async () => {
      if (!AppState.activeDeviceId) return;
      try {
        const start = performance.now();
        await fetch(`${AppState.serverUrl}/api/v1/devices/`);
        StatusBar.setLatency(Math.round(performance.now() - start));
      } catch (e) {}
    }, 30000);
  }

  return { init, sendCommand, switchDevice, getState: () => AppState };
})();

document.addEventListener('DOMContentLoaded', () => App.init());
