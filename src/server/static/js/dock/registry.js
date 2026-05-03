// dock/registry.js — Dock item plugin registry
const DockRegistry = (() => {
  const items = new Map();

  return {
    register(config) {
      if (items.has(config.id)) {
        console.warn(`Dock item "${config.id}" already registered, overwriting.`);
      }
      items.set(config.id, {
        id: config.id,
        icon: config.icon || '📌',
        label: config.label || config.id,
        shortcut: config.shortcut || null,
        position: config.position || items.size,
        badge: config.badge || (() => null),
        render: config.render || null,
        onOpen: config.onOpen || (() => {}),
        onClose: config.onClose || (() => {}),
        onClick: config.onClick || null,
        hasFlyout: !!config.render,
      });
    },

    unregister(id) {
      items.delete(id);
    },

    getAll() {
      return [...items.values()].sort((a, b) => a.position - b.position);
    },

    get(id) {
      return items.get(id);
    },
  };
})();
