// dock/items/volume.js
DockRegistry.register({
  id: 'sound',
  icon: '🔊',
  label: 'Sound',
  position: 6,
  render(container, deviceId) {
    container.innerHTML = `
      <label class="text-xs text-gray-400">Volume</label>
      <input id="vol-slider" type="range" min="0" max="100" value="50"
        class="w-full mt-1 mb-4 accent-blue-500"
        onchange="VolumePanel.setLevel(this.value)" />
      <div class="flex justify-between text-xs text-gray-500 mb-3">
        <span>0%</span><span id="vol-label">50%</span><span>100%</span>
      </div>
      <div class="flex justify-between">
        <button onclick="VolumePanel.toggleMute()"
          class="px-4 py-2 bg-yellow-600/30 border border-yellow-500/40 rounded-lg hover:bg-yellow-600/50 transition text-sm">🔇 Mute</button>
        <div class="flex gap-1">
          <button onclick="VolumePanel.media('prev')" class="px-3 py-2 bg-white/5 rounded-lg hover:bg-white/10 text-sm">⏮</button>
          <button onclick="VolumePanel.media('play_pause')" class="px-3 py-2 bg-white/5 rounded-lg hover:bg-white/10 text-sm">▶</button>
          <button onclick="VolumePanel.media('next')" class="px-3 py-2 bg-white/5 rounded-lg hover:bg-white/10 text-sm">⏭</button>
        </div>
      </div>`;
  },
});

const VolumePanel = (() => {
  function setLevel(val) {
    const label = document.getElementById('vol-label');
    if (label) label.textContent = val + '%';
    App.sendCommand('CMD_SET_VOLUME', { level: parseInt(val) });
  }
  function toggleMute() { App.sendCommand('CMD_SET_VOLUME', { mute: true }); }
  function media(action) { App.sendCommand('CMD_MEDIA', { action }); }
  return { setLevel, toggleMute, media };
})();
