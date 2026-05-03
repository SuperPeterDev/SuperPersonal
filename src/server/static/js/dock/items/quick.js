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
