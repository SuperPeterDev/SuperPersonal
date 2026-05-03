# Sub-project 1: Core End-to-End Validation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix existing bugs and add screenshot + shell-exec so every command button in the browser triggers real execution on the connected Windows PC.

**Architecture:** Three bug fixes (pending double-dispatch, missing command_type in WS result, duplicate onclose in JS) plus two new executors (screenshot as inline base64 JPEG, shell exec via subprocess). No new models or migrations needed — screenshots are stored in the existing CommandLog.output TextField as data URLs.

**Tech Stack:** Python (pyautogui, subprocess), Django REST Framework, Django Channels, Tailwind CSS, vanilla JS

---

## File Map

| Action | Path |
|---|---|
| Create | `src/client/executors/screenshot_executor.py` |
| Create | `src/client/executors/shell_executor.py` |
| Modify | `src/shared/schemas.py` — add `command_str` field to CommandPayload |
| Modify | `src/server/api/views.py` — fix pending (mark SENT) + fix result WS message |
| Modify | `src/server/static/js/app.js` — remove duplicate onclose, add image rendering |
| Modify | `src/server/templates/core/detail.html` — add shell input section |
| Modify | `src/client/client.py` — add new executor imports |
| Modify | `src/server/tests/test_api_views.py` — add pending/result tests |
| Modify | `src/server/tests/test_client.py` — rewrite to match current ClientApp architecture |

---

### Task 1: Fix pending endpoint — mark commands SENT to prevent double-dispatch

**Problem:** `GET /commands/pending/` returns PENDING commands but never transitions them, so the client re-fetches and re-executes the same command on every 5-second poll.

**Files:**
- Modify: `src/server/tests/test_api_views.py`
- Modify: `src/server/api/views.py`

- [ ] **Step 1: Write the failing test**

Add to `TestCommandAPI` in `src/server/tests/test_api_views.py`:

```python
def test_pending_endpoint_marks_commands_sent(self, api_client):
    device = Tbl_Device.objects.create(hardware_id="sent-test-device")
    Tbl_Command.objects.create(device=device, command_type=CommandType.CMD_PING, status=CommandStatus.PENDING)

    url = reverse('command-pending') + f"?device_id={device.hardware_id}"
    api_client.get(url)

    # After polling, the command must be SENT — not PENDING
    cmd = Tbl_Command.objects.get()
    assert cmd.status == CommandStatus.SENT
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest src/server/tests/test_api_views.py::TestCommandAPI::test_pending_endpoint_marks_commands_sent -v
```
Expected: FAIL — status is still PENDING

- [ ] **Step 3: Fix the pending action in `src/server/api/views.py`**

Replace the `pending` action (lines ~82–93):

```python
@action(detail=False, methods=['get'])
def pending(self, request):
    hardware_id = request.query_params.get('device_id')
    if not hardware_id:
        return Response({"error": "device_id required"}, status=status.HTTP_400_BAD_REQUEST)

    commands = Tbl_Command.objects.filter(
        device__hardware_id=hardware_id,
        status=CommandStatus.PENDING
    )
    command_ids = list(commands.values_list('pk_command_id', flat=True))
    commands.update(status=CommandStatus.SENT)

    fetched = Tbl_Command.objects.filter(pk_command_id__in=command_ids)
    serializer = self.get_serializer(fetched, many=True)
    return Response(serializer.data)
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest src/server/tests/test_api_views.py::TestCommandAPI::test_pending_endpoint_marks_commands_sent -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/server/api/views.py src/server/tests/test_api_views.py
git commit -m "fix: mark commands SENT on poll to prevent double-dispatch"
```

---

### Task 2: Fix result WebSocket message — add command_type to data

**Problem:** The `result` action sends a WebSocket message to the dashboard but omits `command_type` in the data dict. `app.js` reads `data.type` (which is `undefined`) so the system-info handler and log labels never work after command completion.

**Files:**
- Modify: `src/server/tests/test_api_views.py`
- Modify: `src/server/api/views.py`

- [ ] **Step 1: Write the failing test**

Add to `TestCommandAPI` in `src/server/tests/test_api_views.py`:

```python
from unittest.mock import patch, call

def test_result_ws_message_includes_command_type(self, api_client):
    device = Tbl_Device.objects.create(hardware_id="ws-type-device")
    cmd = Tbl_Command.objects.create(device=device, command_type=CommandType.CMD_PING)

    url = reverse('command-result', args=[cmd.pk])
    data = {"status": "SUCCESS", "log": {"output": "Pong"}}

    with patch('api.views.async_to_sync') as mock_async:
        api_client.post(url, data, format='json')
        # The inner call args contain the group_send payload
        inner_call = mock_async.return_value
        ws_payload = inner_call.call_args[0][1]
        assert ws_payload['data']['type'] == CommandType.CMD_PING
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest src/server/tests/test_api_views.py::TestCommandAPI::test_result_ws_message_includes_command_type -v
```
Expected: FAIL — `ws_payload['data']['type']` is missing

- [ ] **Step 3: Fix the result action in `src/server/api/views.py`**

In the `result` action, update the `channel_layer.group_send` data dict to include `"type"`:

```python
async_to_sync(channel_layer.group_send)(
    "dashboard",
    {
        "type": "command_update",
        "data": {
            "id": str(command.pk_command_id),
            "device_id": str(command.device.pk_device_id),
            "type": command.command_type,
            "status": command.status,
            "output": log_data.get('output', '') if log_data else ""
        }
    }
)
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest src/server/tests/test_api_views.py::TestCommandAPI::test_result_ws_message_includes_command_type -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/server/api/views.py src/server/tests/test_api_views.py
git commit -m "fix: include command_type in result WebSocket message"
```

---

### Task 3: Fix duplicate onclose in app.js

**Problem:** `src/server/static/js/app.js` defines `socket.onclose` twice (lines 19 and 41). The second assignment overwrites the first, silently discarding the auto-reconnect and toast logic.

**Files:**
- Modify: `src/server/static/js/app.js`

- [ ] **Step 1: Remove the duplicate (dead) onclose at the bottom of app.js**

In `src/server/static/js/app.js`, delete lines 40–42 (the second `socket.onclose` block):

```javascript
// DELETE these lines:
socket.onclose = function (e) {
    console.error("WebSocket Connection Closed");
};
```

The first `socket.onclose` (lines 13–18) already has the full reconnect logic and must remain.

- [ ] **Step 2: Commit**

```bash
git add src/server/static/js/app.js
git commit -m "fix: remove duplicate socket.onclose that discarded reconnect logic"
```

---

### Task 4: Add `command_str` field to CommandPayload

**Purpose:** Shell exec commands need to send the shell command string in the payload. The shared Pydantic schema is the single source of truth for payload fields.

**Files:**
- Modify: `src/shared/schemas.py`

- [ ] **Step 1: Write the failing test**

Create `src/server/tests/test_schemas.py`:

```python
from src.shared.schemas import CommandPayload

class TestCommandPayload:
    def test_accepts_command_str(self):
        p = CommandPayload(command_str="ipconfig /all")
        assert p.command_str == "ipconfig /all"

    def test_command_str_defaults_to_none(self):
        p = CommandPayload()
        assert p.command_str is None
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest src/server/tests/test_schemas.py -v
```
Expected: FAIL — `CommandPayload` has no `command_str` field

- [ ] **Step 3: Add `command_str` to CommandPayload in `src/shared/schemas.py`**

```python
class CommandPayload(BaseModel):
    url: Optional[str] = None
    seconds: Optional[int] = None
    level: Optional[int] = None
    mute: Optional[bool] = None
    action: Optional[str] = None
    command_str: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest src/server/tests/test_schemas.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/shared/schemas.py src/server/tests/test_schemas.py
git commit -m "feat: add command_str field to CommandPayload for shell exec"
```

---

### Task 5: Add ScreenshotExecutor

**Behaviour:** Captures the screen as a JPEG at 60% quality, base64-encodes it, and returns a data URL string as `output`. The frontend detects this format and renders an `<img>` tag.

**Files:**
- Create: `src/client/executors/screenshot_executor.py`
- Modify: `src/server/tests/test_client.py`

- [ ] **Step 1: Write the failing test**

Replace the entire contents of `src/server/tests/test_client.py` with:

```python
import pytest
from unittest.mock import patch, MagicMock
import io
from PIL import Image

from src.client.executors.screenshot_executor import ScreenshotExecutor
from src.client.executors.shell_executor import ShellExecExecutor
from src.shared.schemas import CommandPayload
from src.shared.enums import CommandStatus


class TestScreenshotExecutor:
    def _make_fake_screenshot(self):
        img = Image.new('RGB', (100, 100), color=(73, 109, 137))
        return img

    def test_returns_data_url(self):
        executor = ScreenshotExecutor()
        fake_img = self._make_fake_screenshot()

        with patch('pyautogui.screenshot', return_value=fake_img):
            result = executor.execute(CommandPayload())

        assert result.status == CommandStatus.SUCCESS
        assert result.output.startswith('data:image/jpeg;base64,')

    def test_output_is_valid_jpeg(self):
        executor = ScreenshotExecutor()
        fake_img = self._make_fake_screenshot()

        with patch('pyautogui.screenshot', return_value=fake_img):
            result = executor.execute(CommandPayload())

        import base64
        b64_data = result.output.split(',', 1)[1]
        raw = base64.b64decode(b64_data)
        loaded = Image.open(io.BytesIO(raw))
        assert loaded.format == 'JPEG'


class TestShellExecExecutor:
    def test_returns_stdout(self):
        executor = ShellExecExecutor()

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(stdout='hello\n', stderr='', returncode=0)
            result = executor.execute(CommandPayload(command_str='echo hello'))

        assert result.status == CommandStatus.SUCCESS
        assert 'hello' in result.output

    def test_empty_command_fails(self):
        executor = ShellExecExecutor()
        result = executor.execute(CommandPayload(command_str=None))
        assert result.status == CommandStatus.FAILED

    def test_stderr_included_in_output(self):
        executor = ShellExecExecutor()

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(stdout='', stderr='error msg\n', returncode=1)
            result = executor.execute(CommandPayload(command_str='bad_cmd'))

        assert 'error msg' in result.output
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest src/server/tests/test_client.py -v
```
Expected: FAIL — `screenshot_executor` and `shell_executor` modules do not exist

- [ ] **Step 3: Create `src/client/executors/screenshot_executor.py`**

```python
import io
import base64
from src.client.core.executor import CommandExecutor
from src.client.core.registry import ExecutorRegistry
from src.shared.schemas import CommandPayload, CommandResult
from src.shared.enums import CommandType, CommandStatus


@ExecutorRegistry.register(CommandType.CMD_SCREENSHOT)
class ScreenshotExecutor(CommandExecutor):
    def execute(self, payload: CommandPayload) -> CommandResult:
        import pyautogui

        screenshot = pyautogui.screenshot()
        buffer = io.BytesIO()
        screenshot.convert('RGB').save(buffer, format='JPEG', quality=60)
        b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return CommandResult(
            status=CommandStatus.SUCCESS,
            output=f"data:image/jpeg;base64,{b64}"
        )
```

- [ ] **Step 4: Run screenshot tests to verify they pass**

```
pytest src/server/tests/test_client.py::TestScreenshotExecutor -v
```
Expected: PASS (both screenshot tests)

- [ ] **Step 5: Commit (screenshot only — shell executor not written yet)**

```bash
git add src/client/executors/screenshot_executor.py src/server/tests/test_client.py
git commit -m "feat: add ScreenshotExecutor with base64 JPEG output"
```

---

### Task 6: Add ShellExecExecutor

**Files:**
- Create: `src/client/executors/shell_executor.py`

- [ ] **Step 1: Create `src/client/executors/shell_executor.py`**

```python
import subprocess
from src.client.core.executor import CommandExecutor
from src.client.core.registry import ExecutorRegistry
from src.shared.schemas import CommandPayload, CommandResult
from src.shared.enums import CommandType, CommandStatus


@ExecutorRegistry.register(CommandType.CMD_SHELL_EXEC)
class ShellExecExecutor(CommandExecutor):
    def execute(self, payload: CommandPayload) -> CommandResult:
        if not payload.command_str:
            return CommandResult(status=CommandStatus.FAILED, output="No command provided")

        try:
            proc = subprocess.run(
                payload.command_str,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            combined = proc.stdout + proc.stderr
            return CommandResult(status=CommandStatus.SUCCESS, output=combined.strip())
        except subprocess.TimeoutExpired:
            return CommandResult(status=CommandStatus.FAILED, output="Command timed out (30s limit)")
        except Exception as e:
            return CommandResult(status=CommandStatus.FAILED, output=str(e))
```

- [ ] **Step 2: Run all client tests to verify they pass**

```
pytest src/server/tests/test_client.py -v
```
Expected: PASS (all 5 tests)

- [ ] **Step 3: Commit**

```bash
git add src/client/executors/shell_executor.py
git commit -m "feat: add ShellExecExecutor with subprocess and 30s timeout"
```

---

### Task 7: Register new executors in client.py

**Files:**
- Modify: `src/client/client.py`

- [ ] **Step 1: Add the two new import lines in `src/client/client.py`**

After the existing executor imports (after line 11 `import src.client.executors.power_executors`), add:

```python
import src.client.executors.screenshot_executor
import src.client.executors.shell_executor
```

- [ ] **Step 2: Run the full test suite to verify no regressions**

```
pytest src/server/tests/ -v
```
Expected: All existing tests PASS

- [ ] **Step 3: Commit**

```bash
git add src/client/client.py
git commit -m "feat: register ScreenshotExecutor and ShellExecExecutor in client"
```

---

### Task 8: Add shell input section to detail.html

**Files:**
- Modify: `src/server/templates/core/detail.html`

- [ ] **Step 1: Add Shell Exec section after the Volume Control block in `src/server/templates/core/detail.html`**

Insert this new block after the `<!-- Volume Control -->` block (after the closing `</div>` of Volume Control, before `<!-- Presets -->`):

```html
<!-- Shell Exec -->
<div class="glass p-6 rounded-2xl">
    <h3 class="text-xl font-bold mb-4">Shell Command</h3>
    <div class="flex space-x-3">
        <input id="shell-input" type="text" placeholder="e.g. ipconfig /all"
            class="flex-1 bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-sm font-mono focus:outline-none focus:border-primary"
            onkeydown="if(event.key==='Enter') runShellCmd()" />
        <button onclick="runShellCmd()"
            class="px-6 py-2 bg-primary/20 border border-primary/40 rounded-lg hover:bg-primary/40 transition text-sm font-medium">
            Run
        </button>
    </div>
</div>
```

- [ ] **Step 2: Add `runShellCmd` function to the inline `<script>` block in `detail.html`**

Inside the `<script>` block (after the `sendMedia` function), add:

```javascript
function runShellCmd() {
    const input = document.getElementById('shell-input');
    const cmd = input.value.trim();
    if (!cmd) return;
    sendCommand('CMD_SHELL_EXEC', { command_str: cmd });
    input.value = '';
}
```

- [ ] **Step 3: Commit**

```bash
git add src/server/templates/core/detail.html
git commit -m "feat: add shell command input UI to device detail page"
```

---

### Task 9: Render base64 screenshots in the command log

**Files:**
- Modify: `src/server/static/js/app.js`

- [ ] **Step 1: Update `handleCommandUpdate` in `src/server/static/js/app.js`**

Replace the entire `handleCommandUpdate` function with:

```javascript
function handleCommandUpdate(data) {
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

    if (data.type === 'CMD_SYSTEM_INFO' && window.handleSystemInfo) {
        window.handleSystemInfo(data.output || '');
    }

    showToast(`${data.type || 'Command'}: ${data.status}`);
}
```

- [ ] **Step 2: Commit**

```bash
git add src/server/static/js/app.js
git commit -m "feat: render base64 screenshots and escape HTML in command log"
```

---

### Task 10: Full end-to-end smoke test

Manually validate the complete flow:

- [ ] **Step 1: Start the server**

From `src/server/`:
```
python manage.py runserver
```
Expected output includes: `Starting ASGI/Channels version...`

- [ ] **Step 2: Start the client**

From project root:
```
python -m src.client.client
```
Expected: `Registered/Connected: <uuid>` within 5 seconds

- [ ] **Step 3: Open the dashboard in a browser**

Navigate to `http://localhost:8000/`. The connected PC should appear as a device card.

- [ ] **Step 4: Test Screenshot**

Click the device → click **Screenshot** button. Within 10 seconds the command log should update with an inline JPEG image of the screen.

- [ ] **Step 5: Test Shell Exec**

Type `ipconfig` in the Shell Command input, press Enter. Within 10 seconds the log should show the network config output.

- [ ] **Step 6: Test Volume**

Move the volume slider. The PC's system volume should change.

- [ ] **Step 7: Run full test suite to confirm no regressions**

```
pytest src/server/tests/ -v
```
Expected: All tests PASS
