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
    const cookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
    const csrf = cookie ? cookie.split('=')[1] : '';
    const body = {
      device: state.activeDeviceId,
      command_type: type,
      payload,
      scheduled_for: new Date(dt).toISOString(),
    };
    const r = await fetch(`${state.serverUrl}/api/v1/commands/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
      body: JSON.stringify(body),
    });
    if (r.ok) {
      Notifications.toast({ type, status: 'SUCCESS', output: `Scheduled for ${dt}` });
      Dock.closeFlyout();
    }
  }
  return { submit };
})();
