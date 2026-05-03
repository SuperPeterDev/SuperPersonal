// notifications.js — Toast + browser push notifications
const Notifications = (() => {
  function toast(data) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const statusColor = data.status === 'SUCCESS' ? 'border-green-500/40 bg-green-500/10' :
                        data.status === 'FAILED' ? 'border-red-500/40 bg-red-500/10' :
                        'border-blue-500/40 bg-blue-500/10';
    const toastEl = document.createElement('div');
    toastEl.className = `glass border rounded-lg px-4 py-2 text-sm shadow-lg transition-all ${statusColor}`;
    toastEl.style.cssText = 'animation: slideIn 0.3s ease-out;';
    toastEl.innerHTML = `<span class="font-bold">${data.type || 'Command'}</span> ${data.status}<br>
      <span class="text-xs text-gray-400">${(data.output || '').substring(0, 80)}</span>`;
    container.appendChild(toastEl);
    setTimeout(() => {
      toastEl.style.opacity = '0';
      toastEl.style.transform = 'translateX(100%)';
      toastEl.style.transition = 'all 0.3s ease-out';
      setTimeout(() => toastEl.remove(), 300);
    }, 4000);
  }

  function push(title, body) {
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification(title, { body, icon: '/static/img/icon.png' });
    }
  }

  return { toast, push };
})();
