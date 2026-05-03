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
