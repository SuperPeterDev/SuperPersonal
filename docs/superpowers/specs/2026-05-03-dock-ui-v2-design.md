# SuperPersonal v2 — Desktop Dock UI Design

**Status:** Approved
**Date:** 2026-05-03
**Branch:** fix-ci-config-v2

## Summary

Replace the current scroll-based device detail page with a "desktop dock" design where a live screenshot fills the background and a persistent dock bar at the bottom provides one-click access to all actions via flyout panels. No page navigations — everything is inline.

---

## 1. Architecture

### 1.1 Page Layout

```
┌─────────────────────────────────────────────────────────┐
│ 🟢 Client online │ CPU 22% RAM 68% │ ↑ 2s │ Queue: 3    │  STATUS BAR
│                                                         │
│ [CLIENT]→[FETCH]→[PENDING]→[SENT]→[RUNNING]→[SUCCESS]   │  PIPELINE
│                                                         │
│                   LIVE SCREENSHOT                        │  HERO
│             (auto-refresh, toggleable)                   │
│                                                         │
│              ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐                   │  TOAST
│              │  Command completed      │                   │  (transient)
│              └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘                   │
│                                                         │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌──────┐ ┌──────┐    │  DOCK
│  │ 📸  │ │ 💻  │ │ 📋  │ │ 📁  │ │  🔧  │ │  📊  │    │  (always visible)
│  │ Snap │ │Shell │ │Clip  │ │Files │ │ Proc │ │ Queue│    │
│  └─────┘ └─────┘ └─────┘ └─────┘ └──────┘ └──────┘    │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌──────┐                     │
│  │ 🔒  │ │ 🔊  │ │ ⏰  │ │  ⚡   │                     │
│  │Lock │ │Sound │ │Sched│ │ Quick │                     │
│  └─────┘ └─────┘ └─────┘ └──────┘                     │
└─────────────────────────────────────────────────────────┘
```

### 1.2 Core Principles

- **No page navigations** — everything is inline via flyout panels from the dock
- **One click to action** — every commandable function is one dock click away
- **Live state visible** — status bar, pipeline, queue show what's happening now
- **Extensible** — new features register as dock items, no layout changes needed
- **Mobile-adaptive** — dock wraps to rows, flyouts become bottom sheets

### 1.3 URL Structure

| Path | Purpose |
|------|---------|
| `/` | Dock UI (replaces dashboard) |
| `/device/<id>/` | Dock UI scoped to specific device |
| `/accounts/login/` | Login page (unchanged path, redesigned) |

### 1.4 File Architecture

```
src/server/static/js/
├── dock/
│   ├── dock.js              — dock bar manager + flyout lifecycle
│   ├── registry.js           — dock item plugin registry
│   └── items/
│       ├── screenshot.js     — screenshot capture + auto-refresh
│       ├── shell.js          — terminal emulator panel
│       ├── clipboard.js      — clipboard read/write
│       ├── files.js          — file browser tree
│       ├── process.js        — process list + kill
│       ├── volume.js         — volume slider + mute + media keys
│       ├── schedule.js       — schedule a command
│       ├── quick.js          — configurable quick-action grid
│       └── queue.js          — command queue + flow
├── status-bar.js             — top bar: client state, stats, latency, queue count
├── pipeline.js               — command flow visualization bar
├── notifications.js          — toast + push notification system
├── keyboard.js               — shortcut handler
├── mobile.js                 — mobile adaptation helpers
└── app.js                    — entry point, WebSocket, device tabs, init
```

---

## 2. Components

### 2.1 Status Bar (always visible, top)

Shows real-time system health:
- **Client status**: 🟢 online (polled < 10s ago) / 🟡 stale (10-30s) / 🔴 offline (> 30s)
- **System stats**: CPU%, RAM% from most recent CMD_SYSTEM_INFO
- **Latency**: server ping time in ms
- **Queue count**: `Queue: N` with color if > 0
- **Last poll**: "↑ 2s ago"
- Updates via WebSocket push from server

### 2.2 Pipeline Bar (between status bar and screenshot)

Visual flow of the command state machine:

```
[CLIENT] → [FETCH] → [PENDING] → [SENT] → [RUNNING] → [SUCCESS/FAILED]
```

Each node highlights when a command is at that stage. Below nodes, the active command label: `CMD_SCREENSHOT ● RUNNING — 1.2s`. When idle: `No active command`.

### 2.3 Live Screenshot (hero area)

- Full bleed background, fills available space
- Auto-refresh: toggle 10s / 30s / off (control in Snap flyout)
- Click to manual refresh
- Double-click = fullscreen view
- On first load (no screenshot yet): shows device name, OS info, "Take a Screenshot" button

### 2.4 Dock (always visible, bottom)

#### 2.4.1 Dock Items

| ID | Icon | Label | Flyout | Shortcut |
|----|------|-------|--------|----------|
| snap | 📸 | Snap | Screenshot controls | Ctrl+1 |
| shell | 💻 | Shell | Terminal panel | Ctrl+2 |
| clip | 📋 | Clip | Clipboard read/write | Ctrl+3 |
| files | 📁 | Files | File browser tree | Ctrl+4 |
| proc | 🔧 | Proc | Process list + kill | Ctrl+5 |
| lock | 🔒 | Lock | None (confirm dialog) | Ctrl+L |
| sound | 🔊 | Sound | Volume + media controls | — |
| sched | ⏰ | Sched | Schedule picker | — |
| quick | ⚡ | Quick | Configurable action grid | — |
| queue | 📊 | Queue | Command queue + flow | Ctrl+J |

Last dock item is "…" (more) for future items. User can reorder via drag.

#### 2.4.2 Dock Behavior

- Always visible at bottom of viewport
- Click icon → flyout panel slides up from dock
- Click same icon again OR Esc OR click another icon → closes current flyout
- Badge: queue icon shows count of active/pending commands
- Labels shown under icons
- Active icon highlighted with accent color

#### 2.4.3 Flyout Panels

All flyouts share these behaviors:
- Slide up from dock (300ms transition)
- Max height: 50% of viewport
- Width: 400px (desktop), full-width (mobile)
- Semi-transparent dark background with border
- Close on: second click, Esc, click outside, click another dock item
- Only one flyout open at a time

#### 2.4.4 Shell Flyout

- Real terminal feel: black background, monospace font, green/white text
- Input bar at bottom: `> _`
- Output scrolls above
- Command history via up/down arrow keys
- Paste support
- Runs via CMD_SHELL_EXEC, result renders in output area
- Shows stdout + stderr with color distinction

#### 2.4.5 File Flyout

- Tree view: folder expand/collapse with indentation
- Click folder → navigate, fetch contents
- Click file → inline preview (text files) or `[binary file, N bytes]` message
- Breadcrumb path bar at top: `C:/ > Users > coopt > Desktop`
- Path input for direct navigation

#### 2.4.6 Process Flyout

- Table: PID (monospace), Name, CPU%, MEM%, Kill button
- Auto-refresh toggle (on/off, 5s interval)
- Search/filter by name input
- Sort by column click (default: MEM% descending)
- Kill button = confirm → CMD_KILL_PROCESS

#### 2.4.7 Queue Flyout

- Live WebSocket-updated command list
- Each row: `[type icon] [command_type] [status badge] [age]`
- Status colors: PENDING=gray, SENT=blue, RUNNING=yellow (pulse), SUCCESS=green, FAILED=red
- Flow indicator: `PENDING → SENT → RUNNING → SUCCESS/FAILED` with highlights
- Click row → expands inline showing full output + error trace + execution time
- "Clear completed" button at bottom
- Badge on dock icon showing count of PENDING + SENT + RUNNING

#### 2.4.8 Quick Flyout

- Configurable grid of 4-8 action buttons
- Default buttons: Ping, System Info, Restart, Shutdown, Scheduled Shutdown
- User adds/removes/reorders via edit mode
- Each maps to a command type with optional payload

#### 2.4.9 Volume Flyout

- Vertical slider (0-100%) with pycaw
- Mute toggle button
- Media control row: ⏮ prev | ▶ play/pause | ⏭ next

#### 2.4.10 Schedule Flyout

- Command type dropdown
- Datetime-local picker (defaults to now + 5 min)
- Shell command input (appears only when CMD_SHELL_EXEC selected)
- Schedule button → POST with scheduled_for

---

## 3. Device Management

### 3.1 Device Tabs

Above the status bar:

```
[PeterLaptop 🟢] [OfficePC 🟡] [+ Add Device]
```

- Click tab → dock targets that device, screenshot swaps, queue filters
- 🟢 = client polled within 30s
- 🟡 = last seen > 30s, < 5min
- 🔴 = offline > 5min (hidden from tabs, shown in dropdown)
- "+ Add Device" shows instructions for installing client
- Active tab underlined with accent color

### 3.2 Switching Devices

- Click tab → instant switch
- Keyboard: ← → arrow keys switch tabs
- Each device remembers its own screenshot refresh interval
- Dock actions always target the selected device

---

## 4. Authentication

### 4.1 Login Page Redesign

- Dark page, centered card
- Background: last known screenshot (blurred + darkened) from any device
- Username + password fields
- "Remember this device" checkbox → 30-day session
- After login: redirect to `/` (dock UI, first device tab selected)
- If no devices registered: show device setup instructions

### 4.2 Session Management

- Django session auth (already implemented in Sub4)
- DRF SessionAuthentication for API calls
- CSRF token in all POST requests
- Client registration/polling bypasses auth (AllowAny, already in Sub4)

---

## 5. Notification System

### 5.1 Toast Overlay

- Top-right corner, slides in from right
- Shows: command type icon + status + brief output (truncated to 80 chars)
- Auto-dismiss after 4s
- Click to expand → opens queue flyout
- Stackable: multiple toasts stack vertically

### 5.2 Browser Push Notifications

- Already implemented in Sub3
- Fires on command SUCCESS/FAILED
- Permission requested on first connect

### 5.3 Dock Badge

- Red dot + count on Queue icon
- Shows number of PENDING + SENT + RUNNING commands
- Updates in real time via WebSocket

---

## 6. Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Ctrl+1 | Screenshot now (immediate, no flyout) |
| Ctrl+2 | Open Shell flyout, focus input |
| Ctrl+3 | Open Clipboard flyout |
| Ctrl+4 | Open Files flyout |
| Ctrl+5 | Open Processes flyout |
| Ctrl+L | Lock PC (confirm dialog) |
| Ctrl+K | Command palette (Spotlight-style, type any action/command) |
| Ctrl+J | Toggle Queue flyout |
| Ctrl+S | Schedule command |
| Esc | Close any open flyout / close palette |
| Tab | Cycle dock items left to right |
| ← → | Switch device tabs |
| F5 | Manual screenshot refresh |

---

## 7. Mobile Adaptation (< 768px)

```
┌─────────────────────┐
│ [🟢·22%·68%·Q:3]     │  ← collapsed status bar
│                     │
│                     │
│    SCREENSHOT       │
│  (tap to fullscreen)│
│                     │
│                     │
├─────────────────────┤
│ CMD_PING ● RUNNING  │  ← active command (thin banner)
├─────────────────────┤
│ ┌───┐ ┌───┐ ┌───┐  │  ← dock wraps to rows
│ │📸 │ │💻 │ │📋 │  │
│ └───┘ └───┘ └───┘  │
│ ┌───┐ ┌───┐ ┌───┐  │
│ │📁 │ │🔒 │ │🔊 │  │
│ └───┘ └───┘ └───┘  │
│ [Queue ▸ 3 pending]  │  ← queue as expandable bar
└─────────────────────┘
```

- Status bar collapses to single row: `🟢·22%·68%·Q:3`
- Dock wraps to 2-3 rows (3 columns)
- Flyouts become bottom sheets (slide up from bottom, full width, 60% height)
- Screenshot tap → fullscreen with pinch-to-zoom, tap to dismiss
- Pipeline bar hidden (replaced by active command banner)
- Swipe left/right on screenshot area to switch devices
- Keyboard shortcuts not applicable

---

## 8. Extensibility — Dock Registry Pattern

### 8.1 Registration API

```javascript
DockRegistry.register({
  id: 'shell',
  icon: '💻',
  label: 'Shell',
  shortcut: 'Ctrl+2',
  position: 2, // dock order
  badge: () => null, // or function returning count
  flyout: {
    render: (container) => { /* build flyout DOM */ },
    onOpen: () => { /* focus input, etc */ },
    onClose: () => { /* cleanup */ }
  },
  onClick: (deviceId) => { /* for items without flyout (e.g., Lock) */ }
});
```

### 8.2 Adding a New Feature

1. Create `src/server/static/js/dock/items/newfeature.js`
2. Register it via `DockRegistry.register({...})`
3. No other files need changes — the dock bar auto-updates

---

## 9. Templates

### 9.1 New Template Files

| File | Purpose |
|------|---------|
| `templates/core/dock.html` | Main dock UI (replaces dashboard.html for authenticated users) |
| `templates/core/dock_device.html` | Dock UI scoped to specific device |
| `templates/registration/login.html` | Redesigned login page (replace existing) |

### 9.2 Removed Template Files

- `templates/core/detail.html` — all panels now flyouts
- `templates/core/dashboard.html` — replaced by dock.html

### 9.3 Backward Compatibility

- `/device/<id>/` URL still works but renders dock view instead of detail page
- All existing API endpoints unchanged
- Client agent unchanged

---

## 10. State Management

### 10.1 Client State

```javascript
const AppState = {
  devices: [],              // all registered devices
  activeDeviceId: null,     // currently selected device
  commands: [],             // all known commands for active device
  activeCommand: null,      // currently RUNNING command (or null)
  screenshot: null,         // base64 data URL for active device
  screenshotInterval: null, // timer ID
  clientStatus: 'online',   // online | stale | offline
  lastPoll: null,           // timestamp
  systemInfo: { cpu: 0, ram: 0 },
  openFlyout: null,         // ID of open flyout (or null)
};
```

### 10.2 WebSocket Events

| Event Type | Updates |
|------------|---------|
| `device_update` | Refresh device list, update status dots |
| `command_update` | Add/update command in queue, update pipeline, fire toast |
| `device_status` | Client online/offline transitions |

### 10.3 Polling

- Client polls server every 5s for pending commands (unchanged)
- Browser polls screenshot on interval (configurable, default off)
- Browser polls system info on 30s interval when device tab active

---

## 11. Browser Support

- Target: Chrome, Firefox, Edge, Safari (latest 2 versions)
- ES2020+ (dynamic imports for dock items)
- CSS Grid + Flexbox
- Push Notifications API (optional, feature-detected)
- No framework dependencies — vanilla JS

---

## 12. Implementation Notes

### 12.1 Migration Path

- Build dock UI in parallel with existing detail page
- Keep detail.html working during development
- Once dock is feature-complete, switch the dashboard route to dock.html
- Remove detail.html and dashboard.html after validation

### 12.2 No Server Changes Needed

- All existing API endpoints serve the new UI
- Device registration, command creation, pending poll, result submission unchanged
- Auth system (Sub4) unchanged
- Scheduled commands (Sub3) unchanged

### 12.3 No Client Changes Needed

- `src/client/client.py` unchanged
- All new executors (Sub2) unchanged
- Volume/media executors unchanged
