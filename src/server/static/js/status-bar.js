// status-bar.js — Top status bar
const StatusBar = (() => {
  function update() {
    const state = App.getState();
    const statusEl = document.getElementById('sb-status');
    const statsEl = document.getElementById('sb-stats');
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
