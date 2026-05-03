// dock/items/screenshot.js
DockRegistry.register({
  id: 'snap',
  icon: '📸',
  label: 'Snap',
  shortcut: 'Ctrl+1',
  position: 0,
  render(container, deviceId) {
    container.innerHTML = `
      <div class="space-y-3">
        <p class="text-xs text-gray-400">Capture a screenshot of the remote desktop.</p>
        <button onclick="App.sendCommand('CMD_SCREENSHOT');Dock.closeFlyout();"
          class="w-full py-2 bg-blue-600/30 border border-blue-500/40 rounded-lg hover:bg-blue-600/50 transition text-sm">
          Capture Now
        </button>
        <div class="flex items-center gap-2 text-xs text-gray-400">
          <span>Auto-refresh:</span>
          <button onclick="ScreenshotHero.setInterval(0)" class="px-2 py-1 rounded border border-white/10 hover:bg-white/10">Off</button>
          <button onclick="ScreenshotHero.setInterval(10)" class="px-2 py-1 rounded border border-white/10 hover:bg-white/10">10s</button>
          <button onclick="ScreenshotHero.setInterval(30)" class="px-2 py-1 rounded border border-white/10 hover:bg-white/10">30s</button>
        </div>
      </div>`;
  },
});

const ScreenshotHero = (() => {
  let timer = null;

  function setInterval(sec) {
    if (timer) clearInterval(timer);
    if (sec > 0) {
      timer = setInterval(() => App.sendCommand('CMD_SCREENSHOT'), sec * 1000);
    }
  }

  function show(base64Url) {
    const placeholder = document.getElementById('screenshot-hero');
    const img = document.getElementById('screenshot-img');
    if (placeholder) placeholder.classList.add('hidden');
    if (img) {
      img.src = base64Url;
      img.classList.remove('hidden');
    }
  }

  return { setInterval, show };
})();
