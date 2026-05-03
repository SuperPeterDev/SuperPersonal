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
    QueuePanel.render();
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
