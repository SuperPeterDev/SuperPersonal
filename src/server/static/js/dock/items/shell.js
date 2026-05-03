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
  function send() {
    const input = document.getElementById('shell-input');
    if (!input || !input.value.trim()) return;
    const cmd = input.value.trim();
    const output = document.getElementById('shell-output');
    if (output) {
      output.innerHTML += `<div class="text-white">$ ${cmd}</div>`;
      output.scrollTop = output.scrollHeight;
    }
    input.value = '';
    App.sendCommand('CMD_SHELL_EXEC', { command_str: cmd });
  }

  function appendOutput(text) {
    const output = document.getElementById('shell-output');
    if (!output || !text) return;
    const escaped = text.replace(/</g, '&lt;').replace(/>/g, '&gt;');
    output.innerHTML += `<div class="text-gray-300">${escaped}</div>`;
    output.scrollTop = output.scrollHeight;
  }

  return { send, appendOutput };
})();
