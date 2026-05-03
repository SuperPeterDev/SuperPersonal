// keyboard.js — Global keyboard shortcut handler
document.addEventListener('keydown', function(e) {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') {
    if (e.key === 'Escape') { e.target.blur(); }
    return;
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

  const state = App.getState();
  if (e.key === 'ArrowLeft' && e.ctrlKey && state.devices) {
    e.preventDefault();
    const idx = state.devices.findIndex(d => d.pk_device_id === state.activeDeviceId);
    if (idx > 0) App.switchDevice(state.devices[idx - 1].pk_device_id);
  }
  if (e.key === 'ArrowRight' && e.ctrlKey && state.devices) {
    e.preventDefault();
    const idx = state.devices.findIndex(d => d.pk_device_id === state.activeDeviceId);
    if (idx < state.devices.length - 1) App.switchDevice(state.devices[idx + 1].pk_device_id);
  }
  if (e.key === 'F5') {
    e.preventDefault();
    App.sendCommand('CMD_SCREENSHOT');
  }
});
