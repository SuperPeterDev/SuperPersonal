// dock/items/lock.js
DockRegistry.register({
  id: 'lock',
  icon: '🔒',
  label: 'Lock',
  shortcut: 'Ctrl+L',
  position: 5,
  onClick(deviceId) {
    if (confirm('Lock the remote PC?')) {
      App.sendCommand('CMD_LOCK_PC');
      Notifications.toast({ type: 'CMD_LOCK_PC', status: 'SUCCESS', output: 'PC locking...' });
    }
  },
});
