console.log("SuperPersonal Frontend Loaded");

// Connect to WebSocket
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = `${protocol}//${window.location.host}/ws/dashboard/`;

const socket = new WebSocket(wsUrl);

socket.onopen = function (e) {
    console.log("WebSocket Connection Established");
    updateConnectionStatus(true);
};

socket.onclose = function (e) {
    console.error("WebSocket Connection Closed");
    updateConnectionStatus(false);
    showToast("Connection Lost. Reconnecting...");
    setTimeout(() => location.reload(), 5000); // Auto-reload to reconnect
};

function updateConnectionStatus(connected) {
    const dot = document.getElementById('ws-status-dot');
    if (dot) {
        dot.className = `w-2 h-2 rounded-full ${connected ? 'bg-green-500 shadow-[0_0_10px_#22c55e]' : 'bg-red-500'}`;
        dot.title = connected ? "Real-time Connected" : "Disconnected";
    }
}

socket.onmessage = function (e) {
    const data = JSON.parse(e.data);
    console.log("WS Message:", data);

    if (data.type === 'command_update') {
        handleCommandUpdate(data.data);
    } else if (data.type === 'device_update') {
        handleDeviceUpdate(data.data);
    }
};

function handleCommandUpdate(data) {
    // If on detail page, update log
    const logContainer = document.getElementById('log-container');
    if (logContainer && typeof DEVICE_ID !== 'undefined' && DEVICE_ID === data.device_id) {
        const LogEl = document.createElement('div');
        const color = data.status === 'SUCCESS'
            ? 'border-green-500'
            : (data.status === 'FAILED' ? 'border-red-500' : 'border-gray-500');

        const isImage = data.output && data.output.startsWith('data:image/');
        let outputHtml;
        if (isImage) {
            outputHtml = `<img src="${data.output}" class="mt-2 rounded max-w-full cursor-pointer" onclick="this.classList.toggle('max-w-full')" />`;
        } else {
            const escaped = (data.output || data.status || '').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            outputHtml = `<pre class="text-gray-300 mt-1 whitespace-pre-wrap text-xs">${escaped}</pre>`;
        }

        LogEl.className = `border-l-2 ${color} pl-3`;
        LogEl.innerHTML = `
            <div class="flex justify-between text-gray-500 text-xs">
                <span>${data.type || 'Update'}</span>
                <span>Now</span>
            </div>
            ${outputHtml}
        `;
        logContainer.prepend(LogEl);
    }

    // Special handling for System Info
    if (data.type === 'CMD_SYSTEM_INFO' && window.handleSystemInfo) {
        window.handleSystemInfo(data.output || '');
    }

    // Toast notification
    showToast(`${data.type || 'Command'}: ${data.status}`);
}

function handleDeviceUpdate(data) {
    showToast(`Device Update: ${data.hostname} is ${data.status}`);
    // Ideally reload page or strictly update DOM
    // For MVP transparency:
    if (window.location.pathname === '/') {
        setTimeout(() => location.reload(), 1000); // Reload dashboard to see new device
    }
}

function showToast(message) {
    const toast = document.createElement('div');
    toast.className = "fixed top-4 right-4 bg-gray-800 border border-gray-700 text-white px-4 py-2 rounded shadow-lg z-50 transition-opacity duration-300";
    toast.innerText = message;
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}
