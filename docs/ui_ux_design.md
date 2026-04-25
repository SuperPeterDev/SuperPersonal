# UI/UX Design Document

## 1. Design Philosophy
*   **Aesthetic**: "Cyberpunk Premium" / "Modern Glass". High contrast, dark mode by default.
*   **Feel**: Responsive, "Alive", Fluid.
*   **Inspiration**: macOS Control Center, dashboard UI kits (e.g., Vercel, Linear).

## 2. Color Palette
*   **Background**: Deep Charcoal (`#0F172A`) to Pure Black (`#000000`).
*   **Primary Accent**: Neon Blue (`#3B82F6`) or Electric Purple (`#8B5CF6`).
*   **Surface**: Semi-transparent Glass (`rgba(255, 255, 255, 0.05)`) with blurred backdrop (`backdrop-filter: blur(10px)`).
*   **Text**:
    *   Primary: White (`#FFFFFF`).
    *   Secondary: Slate Grey (`#94A3B8`).
*   **Status Indicators**:
    *   Online: Glowing Green (`#22C55E`).
    *   Busy/Queued: Amber (`#F59E0B`).
    *   Offline: Muted Red (`#EF4444`).

## 3. Typography
*   **Font Family**: `Inter` or `Outfit` (Clean, Sans-serif).
*   **Weights**: Light (300) for body, Bold (700) for headers.
*   **Monospace**: `JetBrains Mono` for logs/terminals.

## 4. Key Screens & Layouts

### 4.1 Dashboard (Main View)
*   **Grid Layout**: Cards representing connected devices.
*   **Device Card**:
    *   **Header**: Device Name + Status Dot (pulsing if online).
    *   **Body**: CPU/RAM Mini-charts (Sparklines).
    *   **Footer**: Quick Actions (Screenshot, Lock, Shutdown).
    *   **Hover Effect**: Glow border and lift animation.

### 4.2 Device Detail View
*   **Split View**:
    *   **Left Panel**: Real-time stats, System Specs (OS, Uptime).
    *   **Right Panel**:
        *   **Command Center**: Input field for Shell Commands.
        *   **Action Grid**: Large buttons for common actions (Screenshot, Open URL).
        *   **History/Logs**: Scrollable list of recent actions with status icons.

### 4.3 Mobile View
*   **Stack Layout**: Cards stack vertically.
*   **Bottom Navigation**: Dashboard, Devices, Settings.
*   **Touch Friendly**: Large hit areas for buttons (min 44px).

## 5. Interactions & Animations
*   **Loading**: Skeleton loaders instead of spinners.
*   **Transitions**: Smooth page transitions (fade-in, slide-up).
*   **Feedback**: Toast notifications for command success/failure (top-right).
*   **Micro-interactions**: Buttons scale down slightly on click (`active:scale-95`).
