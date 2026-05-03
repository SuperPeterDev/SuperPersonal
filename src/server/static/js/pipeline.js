// pipeline.js — Command flow visualization
const Pipeline = (() => {
  const stages = ['client', 'fetch', 'pending', 'sent', 'running', 'result'];

  function update() {
    const state = App.getState();
    const activeEl = document.getElementById('pipeline-active');

    for (const s of stages) {
      const el = document.getElementById(`pl-${s}`);
      if (el) el.className = 'px-1.5';
    }

    if (state.activeCommand) {
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
        const colorClass = status === 'RUNNING' ? 'animate-pulse text-yellow-400' :
                           status === 'SUCCESS' ? 'text-green-400' :
                           status === 'FAILED' ? 'text-red-400' : 'text-blue-400';
        activeEl.innerHTML = `<span class="${colorClass}">${dot} ${state.activeCommand.type || 'Command'} ${status}</span>`;
      }
    } else {
      if (activeEl) activeEl.textContent = 'No active command';
    }
  }

  return { update };
})();
