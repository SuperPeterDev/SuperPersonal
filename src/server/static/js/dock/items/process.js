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
        const el = document.getElementById('proc-table');
        if (el) el.innerHTML = `<p class="text-red-400">${output}</p>`;
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
        <td class="py-1">${(p.name || '-').replace(/</g,'&lt;').replace(/>/g,'&gt;')}</td>
        <td class="py-1 text-right text-purple-400">${(p.memory_percent||0).toFixed(1)}%</td>
        <td class="py-1 text-right"><button onclick="ProcessPanel.kill(${p.pid})" class="text-red-400 hover:text-red-200 text-xs px-2">Kill</button></td>
      </tr>`;
    }
    html += '</tbody></table>';
    el.innerHTML = html;
  }

  return { refresh, filter, kill };
})();

window.handleProcessList = function(output) { /* handled in refresh callback */ };
