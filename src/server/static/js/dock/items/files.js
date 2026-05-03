// dock/items/files.js
DockRegistry.register({
  id: 'files',
  icon: '📁',
  label: 'Files',
  shortcut: 'Ctrl+4',
  position: 3,
  render(container, deviceId) {
    container.innerHTML = `
      <div class="flex gap-2 mb-3">
        <input id="files-path" type="text" value="C:/" placeholder="Path..."
          class="flex-1 bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-xs font-mono focus:outline-none focus:border-primary"
          onkeydown="if(event.key==='Enter')FilesPanel.browse()" />
        <button onclick="FilesPanel.browse()"
          class="px-3 py-2 bg-indigo-600/30 border border-indigo-500/40 rounded-lg hover:bg-indigo-600/50 transition text-xs">Browse</button>
      </div>
      <div id="files-list" class="overflow-auto max-h-64 text-xs"></div>
      <div id="files-preview" class="hidden mt-3 bg-black/40 rounded-lg p-3 text-xs max-h-32 overflow-auto whitespace-pre-wrap"></div>`;
  },
});

const FilesPanel = (() => {
  function browse() {
    const input = document.getElementById('files-path');
    if (!input) return;
    const path = input.value.trim();
    if (!path) return;
    App.sendCommand('CMD_FILE_LIST', { path });
  }

  function readFile(path) {
    App.sendCommand('CMD_FILE_READ', { path });
  }

  function navigateTo(path) {
    const input = document.getElementById('files-path');
    if (input) input.value = path;
    browse();
  }

  return { browse, readFile, navigateTo };
})();

window.handleFileList = function(output) {
  const el = document.getElementById('files-list');
  if (!el) return;
  try {
    const items = JSON.parse(output);
    let html = '<ul class="space-y-0.5">';
    for (const item of items) {
      const icon = item.type === 'dir' ? '📁' : '📄';
      const size = item.size != null ? `<span class="text-gray-600 ml-2">${(item.size/1024).toFixed(1)}KB</span>` : '';
      const name = item.name.replace(/</g, '&lt;').replace(/>/g, '&gt;');
      const path = (item.path || '').replace(/\\/g, '\\\\');
      if (item.type === 'dir') {
        html += `<li class="hover:bg-white/5 rounded px-2 py-0.5 cursor-pointer" onclick="FilesPanel.navigateTo('${path}')">${icon} ${name}</li>`;
      } else {
        html += `<li class="hover:bg-white/5 rounded px-2 py-0.5 flex justify-between items-center">
          <span>${icon} ${name}${size}</span>
          <button onclick="FilesPanel.readFile('${path}')" class="text-primary hover:text-white text-[10px] ml-2">View</button>
        </li>`;
      }
    }
    html += '</ul>';
    el.innerHTML = html;
  } catch(e) {
    el.innerHTML = `<p class="text-red-400">${output}</p>`;
  }
};

window.handleFileRead = function(output) {
  const preview = document.getElementById('files-preview');
  if (!preview) return;
  preview.classList.remove('hidden');
  preview.textContent = output;
};
