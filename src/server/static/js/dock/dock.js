// dock/dock.js — Dock bar + flyout lifecycle
const Dock = (() => {
  let activeFlyout = null;
  let dockEl = null;
  let flyoutEl = null;
  let deviceId = null;

  function init(container, devId) {
    deviceId = devId;
    buildDOM(container);
    renderIcons();
    document.addEventListener('keydown', handleKeydown);
    document.addEventListener('click', handleOutsideClick);
  }

  function buildDOM(container) {
    container.innerHTML = `
      <div id="dock-bar" class="fixed bottom-0 left-0 right-0 flex justify-center items-end gap-1 px-4 pb-2 z-40">
        <div id="dock-icons" class="flex items-end gap-1 bg-black/60 backdrop-blur-lg border border-white/10 rounded-2xl px-3 py-2"></div>
      </div>
      <div id="flyout-container" class="fixed bottom-20 left-1/2 -translate-x-1/2 z-50 hidden"></div>
    `;
    dockEl = document.getElementById('dock-icons');
    flyoutEl = document.getElementById('flyout-container');
  }

  function renderIcons() {
    const items = DockRegistry.getAll();
    let html = '';
    for (const item of items) {
      html += `
        <button id="dock-${item.id}" data-dock-id="${item.id}"
          class="group flex flex-col items-center px-3 py-2 rounded-xl hover:bg-white/10 transition min-w-[64px]"
          title="${item.label}${item.shortcut ? ' (' + item.shortcut + ')' : ''}">
          <span class="text-2xl">${item.icon}</span>
          <span class="text-[10px] text-gray-400 group-hover:text-white mt-0.5">${item.label}</span>
        </button>`;
    }
    dockEl.innerHTML = html;

    for (const item of items) {
      const btn = document.getElementById(`dock-${item.id}`);
      if (!btn) continue;
      btn.addEventListener('click', () => handleItemClick(item));
    }
    updateBadges();
  }

  function handleItemClick(item) {
    if (activeFlyout === item.id) {
      closeFlyout();
      return;
    }
    if (!item.hasFlyout) {
      if (item.onClick) item.onClick(deviceId);
      return;
    }
    openFlyout(item);
  }

  function openFlyout(item) {
    closeFlyout();
    activeFlyout = item.id;
    flyoutEl.innerHTML = '';
    flyoutEl.classList.remove('hidden');
    flyoutEl.innerHTML = `
      <div class="bg-gray-900/95 backdrop-blur-lg border border-white/10 rounded-2xl w-[400px] max-h-[50vh] overflow-auto p-6 shadow-2xl">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-bold">${item.icon} ${item.label}</h3>
          <button onclick="Dock.closeFlyout()" class="text-gray-500 hover:text-white text-xl leading-none">&times;</button>
        </div>
        <div id="flyout-body"></div>
      </div>`;
    item.render(document.getElementById('flyout-body'), deviceId);
    item.onOpen();
    const btn = document.getElementById(`dock-${item.id}`);
    if (btn) btn.classList.add('bg-white/10');
  }

  function closeFlyout() {
    if (activeFlyout) {
      const item = DockRegistry.get(activeFlyout);
      if (item) {
        item.onClose();
        const btn = document.getElementById(`dock-${item.id}`);
        if (btn) btn.classList.remove('bg-white/10');
      }
    }
    activeFlyout = null;
    flyoutEl.classList.add('hidden');
    flyoutEl.innerHTML = '';
  }

  function updateBadges() {
    for (const item of DockRegistry.getAll()) {
      const count = item.badge();
      const btn = document.getElementById(`dock-${item.id}`);
      if (!btn) continue;
      const existing = btn.querySelector('.dock-badge');
      if (existing) existing.remove();
      if (count) {
        const badge = document.createElement('span');
        badge.className = 'dock-badge absolute -top-1 -right-1 bg-red-500 text-white text-[10px] rounded-full w-5 h-5 flex items-center justify-center font-bold';
        badge.textContent = count > 9 ? '9+' : count;
        btn.style.position = 'relative';
        btn.appendChild(badge);
      }
    }
  }

  function handleKeydown(e) {
    if (e.key === 'Escape') { closeFlyout(); return; }
    const items = DockRegistry.getAll();
    for (const item of items) {
      if (item.shortcut && matchesShortcut(e, item.shortcut)) {
        e.preventDefault();
        if (item.hasFlyout) {
          if (activeFlyout === item.id) closeFlyout();
          else openFlyout(item);
        } else if (item.onClick) {
          item.onClick(deviceId);
        }
        return;
      }
    }
  }

  function matchesShortcut(e, shortcut) {
    const parts = shortcut.toLowerCase().split('+');
    const ctrl = parts.includes('ctrl');
    const key = parts[parts.length - 1];
    return e.ctrlKey === ctrl && e.key.toLowerCase() === key;
  }

  function handleOutsideClick(e) {
    if (flyoutEl && !flyoutEl.contains(e.target) && !e.target.closest('[data-dock-id]')) {
      closeFlyout();
    }
  }

  function setDeviceId(devId) { deviceId = devId; }

  return { init, closeFlyout, updateBadges, setDeviceId, getDeviceId: () => deviceId };
})();
