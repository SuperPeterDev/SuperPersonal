# Sub-project 2: Command Expansion Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add process manager (list/kill), clipboard read/write, and file browser (list/download) so the web UI becomes a full remote management interface.

**Architecture:** Six new CommandType values added to the shared enum. Each has a matching client executor. The server gets a new API endpoint for file downloads (files can't be sent through the command log). UI panels are added to the device detail page.

**Tech Stack:** Python (psutil, pyperclip, pathlib), Django REST Framework, Tailwind CSS, vanilla JS

**Prerequisite:** Sub-project 1 must be merged first (CommandPayload already has `command_str`).

---

## File Map

| Action | Path |
|---|---|
| Modify | `src/shared/enums.py` — add 6 new CommandType values |
| Modify | `src/shared/schemas.py` — add `pid`, `text`, `path` fields to CommandPayload |
| Create | `src/client/executors/system_advanced_executors.py` — process list, kill, clipboard |
| Create | `src/client/executors/file_executor.py` — file list, file read |
| Modify | `src/client/client.py` — import new executors |
| Modify | `src/server/api/models.py` — update command_type choices |
| Create | `src/server/api/migrations/0003_new_command_types.py` — migration |
| Modify | `src/server/api/views.py` — add file download endpoint |
| Modify | `src/server/api/urls.py` — register file download route |
| Modify | `src/server/templates/core/detail.html` — add process manager + clipboard + file browser panels |
| Modify | `src/server/tests/test_client.py` — add tests for new executors |
| Modify | `src/server/tests/test_api_views.py` — test file download endpoint |

---

### Task 1: Add new CommandType values and payload fields

**Files:**
- Modify: `src/shared/enums.py`
- Modify: `src/shared/schemas.py`

- [ ] **Step 1: Write the failing test**

Create `src/server/tests/test_new_enums.py`:

```python
from src.shared.enums import CommandType
from src.shared.schemas import CommandPayload


class TestNewCommandTypes:
    def test_all_new_command_types_exist(self):
        assert CommandType.CMD_LIST_PROCESSES
        assert CommandType.CMD_KILL_PROCESS
        assert CommandType.CMD_CLIPBOARD_GET
        assert CommandType.CMD_CLIPBOARD_SET
        assert CommandType.CMD_FILE_LIST
        assert CommandType.CMD_FILE_READ

    def test_payload_has_pid_field(self):
        p = CommandPayload(pid=1234)
        assert p.pid == 1234

    def test_payload_has_text_field(self):
        p = CommandPayload(text="hello clipboard")
        assert p.text == "hello clipboard"

    def test_payload_has_path_field(self):
        p = CommandPayload(path="C:/Users")
        assert p.path == "C:/Users"
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest src/server/tests/test_new_enums.py -v
```
Expected: FAIL — new enum values and fields don't exist

- [ ] **Step 3: Add new values to `src/shared/enums.py`**

```python
class CommandType(str, Enum):
    CMD_PING = 'CMD_PING'
    CMD_SHELL_EXEC = 'CMD_SHELL_EXEC'
    CMD_OPEN_BROWSER = 'CMD_OPEN_BROWSER'
    CMD_SCREENSHOT = 'CMD_SCREENSHOT'
    CMD_SYSTEM_INFO = 'CMD_SYSTEM_INFO'
    CMD_LOCK_PC = 'CMD_LOCK_PC'
    CMD_SHUTDOWN = 'CMD_SHUTDOWN'
    CMD_RESTART = 'CMD_RESTART'
    CMD_SCHEDULED_SHUTDOWN = 'CMD_SCHEDULED_SHUTDOWN'
    CMD_SET_VOLUME = 'CMD_SET_VOLUME'
    CMD_OPEN_PRESET = 'CMD_OPEN_PRESET'
    CMD_MEDIA = 'CMD_MEDIA'
    CMD_LIST_PROCESSES = 'CMD_LIST_PROCESSES'
    CMD_KILL_PROCESS = 'CMD_KILL_PROCESS'
    CMD_CLIPBOARD_GET = 'CMD_CLIPBOARD_GET'
    CMD_CLIPBOARD_SET = 'CMD_CLIPBOARD_SET'
    CMD_FILE_LIST = 'CMD_FILE_LIST'
    CMD_FILE_READ = 'CMD_FILE_READ'
```

- [ ] **Step 4: Add new fields to `src/shared/schemas.py`**

```python
class CommandPayload(BaseModel):
    url: Optional[str] = None
    seconds: Optional[int] = None
    level: Optional[int] = None
    mute: Optional[bool] = None
    action: Optional[str] = None
    command_str: Optional[str] = None
    pid: Optional[int] = None
    text: Optional[str] = None
    path: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)
```

- [ ] **Step 5: Run test to verify it passes**

```
pytest src/server/tests/test_new_enums.py -v
```
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/shared/enums.py src/shared/schemas.py src/server/tests/test_new_enums.py
git commit -m "feat: add process/clipboard/file CommandType values and payload fields"
```

---

### Task 2: Create process manager and clipboard executors

**Files:**
- Create: `src/client/executors/system_advanced_executors.py`

- [ ] **Step 1: Write the failing test**

Add to `src/server/tests/test_client.py`:

```python
from src.client.executors.system_advanced_executors import (
    ListProcessesExecutor, KillProcessExecutor,
    ClipboardGetExecutor, ClipboardSetExecutor,
)
import json


class TestProcessExecutors:
    def test_list_processes_returns_json_list(self):
        executor = ListProcessesExecutor()
        with patch('psutil.process_iter') as mock_iter:
            mock_proc = MagicMock()
            mock_proc.info = {'pid': 1, 'name': 'test.exe', 'cpu_percent': 0.5, 'memory_percent': 1.2}
            mock_iter.return_value = [mock_proc]
            result = executor.execute(CommandPayload())

        assert result.status == CommandStatus.SUCCESS
        processes = json.loads(result.output)
        assert processes[0]['pid'] == 1
        assert processes[0]['name'] == 'test.exe'

    def test_kill_process_calls_kill(self):
        executor = KillProcessExecutor()
        with patch('psutil.Process') as MockProc:
            result = executor.execute(CommandPayload(pid=9999))
            MockProc.return_value.kill.assert_called_once()

        assert result.status == CommandStatus.SUCCESS

    def test_kill_process_missing_pid_fails(self):
        executor = KillProcessExecutor()
        result = executor.execute(CommandPayload())
        assert result.status == CommandStatus.FAILED


class TestClipboardExecutors:
    def test_clipboard_get_returns_text(self):
        executor = ClipboardGetExecutor()
        with patch('pyperclip.paste', return_value='copied text'):
            result = executor.execute(CommandPayload())
        assert result.status == CommandStatus.SUCCESS
        assert result.output == 'copied text'

    def test_clipboard_set_writes_text(self):
        executor = ClipboardSetExecutor()
        with patch('pyperclip.copy') as mock_copy:
            result = executor.execute(CommandPayload(text='new text'))
            mock_copy.assert_called_once_with('new text')
        assert result.status == CommandStatus.SUCCESS

    def test_clipboard_set_missing_text_fails(self):
        executor = ClipboardSetExecutor()
        result = executor.execute(CommandPayload())
        assert result.status == CommandStatus.FAILED
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest src/server/tests/test_client.py::TestProcessExecutors src/server/tests/test_client.py::TestClipboardExecutors -v
```
Expected: FAIL — module does not exist

- [ ] **Step 3: Create `src/client/executors/system_advanced_executors.py`**

```python
import json
import psutil
from src.client.core.executor import CommandExecutor
from src.client.core.registry import ExecutorRegistry
from src.shared.schemas import CommandPayload, CommandResult
from src.shared.enums import CommandType, CommandStatus


@ExecutorRegistry.register(CommandType.CMD_LIST_PROCESSES)
class ListProcessesExecutor(CommandExecutor):
    def execute(self, payload: CommandPayload) -> CommandResult:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            processes.append(proc.info)
        processes.sort(key=lambda p: p.get('memory_percent', 0), reverse=True)
        return CommandResult(status=CommandStatus.SUCCESS, output=json.dumps(processes[:50]))


@ExecutorRegistry.register(CommandType.CMD_KILL_PROCESS)
class KillProcessExecutor(CommandExecutor):
    def execute(self, payload: CommandPayload) -> CommandResult:
        if payload.pid is None:
            return CommandResult(status=CommandStatus.FAILED, output="No PID provided")
        try:
            psutil.Process(payload.pid).kill()
            return CommandResult(status=CommandStatus.SUCCESS, output=f"Killed PID {payload.pid}")
        except psutil.NoSuchProcess:
            return CommandResult(status=CommandStatus.FAILED, output=f"No process with PID {payload.pid}")
        except psutil.AccessDenied:
            return CommandResult(status=CommandStatus.FAILED, output=f"Access denied killing PID {payload.pid}")


@ExecutorRegistry.register(CommandType.CMD_CLIPBOARD_GET)
class ClipboardGetExecutor(CommandExecutor):
    def execute(self, payload: CommandPayload) -> CommandResult:
        import pyperclip
        text = pyperclip.paste()
        return CommandResult(status=CommandStatus.SUCCESS, output=text)


@ExecutorRegistry.register(CommandType.CMD_CLIPBOARD_SET)
class ClipboardSetExecutor(CommandExecutor):
    def execute(self, payload: CommandPayload) -> CommandResult:
        if payload.text is None:
            return CommandResult(status=CommandStatus.FAILED, output="No text provided")
        import pyperclip
        pyperclip.copy(payload.text)
        return CommandResult(status=CommandStatus.SUCCESS, output=f"Clipboard set ({len(payload.text)} chars)")
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest src/server/tests/test_client.py::TestProcessExecutors src/server/tests/test_client.py::TestClipboardExecutors -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/client/executors/system_advanced_executors.py src/server/tests/test_client.py
git commit -m "feat: add ListProcesses, KillProcess, ClipboardGet, ClipboardSet executors"
```

---

### Task 3: Create file browser executor

**Files:**
- Create: `src/client/executors/file_executor.py`

- [ ] **Step 1: Write the failing test**

Add to `src/server/tests/test_client.py`:

```python
from src.client.executors.file_executor import FileListExecutor, FileReadExecutor
import json


class TestFileExecutors:
    def test_file_list_returns_json(self, tmp_path):
        (tmp_path / "foo.txt").write_text("hello")
        (tmp_path / "bar.py").write_text("world")
        executor = FileListExecutor()
        result = executor.execute(CommandPayload(path=str(tmp_path)))

        assert result.status == CommandStatus.SUCCESS
        items = json.loads(result.output)
        names = [i['name'] for i in items]
        assert 'foo.txt' in names
        assert 'bar.py' in names

    def test_file_list_nonexistent_path_fails(self):
        executor = FileListExecutor()
        result = executor.execute(CommandPayload(path="/nonexistent/path"))
        assert result.status == CommandStatus.FAILED

    def test_file_read_returns_text(self, tmp_path):
        f = tmp_path / "hello.txt"
        f.write_text("file contents here")
        executor = FileReadExecutor()
        result = executor.execute(CommandPayload(path=str(f)))
        assert result.status == CommandStatus.SUCCESS
        assert result.output == "file contents here"

    def test_file_read_limits_size(self, tmp_path):
        f = tmp_path / "big.txt"
        f.write_text("x" * 200_000)
        executor = FileReadExecutor()
        result = executor.execute(CommandPayload(path=str(f)))
        assert result.status == CommandStatus.SUCCESS
        assert len(result.output) <= 100_100  # 100KB limit + small overhead
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest src/server/tests/test_client.py::TestFileExecutors -v
```
Expected: FAIL — module does not exist

- [ ] **Step 3: Create `src/client/executors/file_executor.py`**

```python
import json
from pathlib import Path
from src.client.core.executor import CommandExecutor
from src.client.core.registry import ExecutorRegistry
from src.shared.schemas import CommandPayload, CommandResult
from src.shared.enums import CommandType, CommandStatus

_READ_LIMIT_BYTES = 100 * 1024  # 100 KB


@ExecutorRegistry.register(CommandType.CMD_FILE_LIST)
class FileListExecutor(CommandExecutor):
    def execute(self, payload: CommandPayload) -> CommandResult:
        if not payload.path:
            return CommandResult(status=CommandStatus.FAILED, output="No path provided")

        p = Path(payload.path)
        if not p.exists():
            return CommandResult(status=CommandStatus.FAILED, output=f"Path not found: {payload.path}")

        if p.is_file():
            items = [{"name": p.name, "type": "file", "size": p.stat().st_size}]
        else:
            items = []
            for child in sorted(p.iterdir()):
                try:
                    items.append({
                        "name": child.name,
                        "type": "dir" if child.is_dir() else "file",
                        "size": child.stat().st_size if child.is_file() else None,
                        "path": str(child)
                    })
                except PermissionError:
                    pass

        return CommandResult(status=CommandStatus.SUCCESS, output=json.dumps(items))


@ExecutorRegistry.register(CommandType.CMD_FILE_READ)
class FileReadExecutor(CommandExecutor):
    def execute(self, payload: CommandPayload) -> CommandResult:
        if not payload.path:
            return CommandResult(status=CommandStatus.FAILED, output="No path provided")

        p = Path(payload.path)
        if not p.is_file():
            return CommandResult(status=CommandStatus.FAILED, output=f"Not a file: {payload.path}")

        try:
            raw = p.read_bytes()[:_READ_LIMIT_BYTES]
            try:
                text = raw.decode('utf-8', errors='replace')
            except Exception:
                text = f"[binary file, {p.stat().st_size} bytes]"
            return CommandResult(status=CommandStatus.SUCCESS, output=text)
        except PermissionError:
            return CommandResult(status=CommandStatus.FAILED, output=f"Permission denied: {payload.path}")
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest src/server/tests/test_client.py::TestFileExecutors -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/client/executors/file_executor.py src/server/tests/test_client.py
git commit -m "feat: add FileListExecutor and FileReadExecutor"
```

---

### Task 4: Register new executors in client.py

**Files:**
- Modify: `src/client/client.py`

- [ ] **Step 1: Add import lines to `src/client/client.py`**

After the existing executor imports, add:

```python
import src.client.executors.system_advanced_executors
import src.client.executors.file_executor
```

- [ ] **Step 2: Run full test suite**

```
pytest src/server/tests/ -v
```
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add src/client/client.py
git commit -m "feat: register system_advanced and file executors in client"
```

---

### Task 5: Generate Django migration for new command types

**Files:**
- Modify: `src/server/api/migrations/`

- [ ] **Step 1: Generate migration**

From `src/server/`:
```
python manage.py makemigrations api --name new_command_types
```
Expected: Creates `api/migrations/0003_new_command_types.py`

- [ ] **Step 2: Apply migration**

```
python manage.py migrate
```
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add src/server/api/migrations/0003_new_command_types.py
git commit -m "chore: migrate db for new CommandType enum values"
```

---

### Task 6: Add process manager and clipboard UI panels to detail.html

**Files:**
- Modify: `src/server/templates/core/detail.html`

- [ ] **Step 1: Add Process Manager panel after the Shell Exec block**

Insert after the `<!-- Shell Exec -->` block:

```html
<!-- Process Manager -->
<div class="glass p-6 rounded-2xl">
    <div class="flex justify-between items-center mb-4">
        <h3 class="text-xl font-bold">Process Manager</h3>
        <button onclick="loadProcesses()"
            class="text-xs text-primary hover:text-white transition">Refresh</button>
    </div>
    <div id="process-table" class="overflow-auto max-h-64 text-sm">
        <p class="text-gray-500 italic">Click Refresh to load processes.</p>
    </div>
</div>

<!-- Clipboard -->
<div class="glass p-6 rounded-2xl">
    <h3 class="text-xl font-bold mb-4">Clipboard</h3>
    <div class="flex space-x-3 mb-3">
        <button onclick="sendCommand('CMD_CLIPBOARD_GET')"
            class="px-4 py-2 bg-teal-600/20 border border-teal-500/30 rounded-lg hover:bg-teal-600/40 transition text-sm">
            Read Clipboard
        </button>
    </div>
    <div class="flex space-x-3">
        <input id="clipboard-input" type="text" placeholder="Text to send to clipboard..."
            class="flex-1 bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-primary" />
        <button onclick="setClipboard()"
            class="px-4 py-2 bg-teal-600/20 border border-teal-500/30 rounded-lg hover:bg-teal-600/40 transition text-sm">
            Set Clipboard
        </button>
    </div>
</div>
```

- [ ] **Step 2: Add JS functions to the inline `<script>` block in detail.html**

```javascript
function loadProcesses() {
    sendCommand('CMD_LIST_PROCESSES');
}

function killProcess(pid) {
    if (!confirm(`Kill PID ${pid}?`)) return;
    sendCommand('CMD_KILL_PROCESS', { pid: parseInt(pid) });
}

function setClipboard() {
    const text = document.getElementById('clipboard-input').value;
    if (!text) return;
    sendCommand('CMD_CLIPBOARD_SET', { text: text });
    document.getElementById('clipboard-input').value = '';
}

// Called by app.js when CMD_LIST_PROCESSES result arrives
window.handleProcessList = function(output) {
    const table = document.getElementById('process-table');
    if (!table) return;
    try {
        const procs = JSON.parse(output);
        let html = '<table class="w-full text-xs"><thead><tr class="text-gray-500 border-b border-white/10"><th class="text-left py-1">PID</th><th class="text-left py-1">Name</th><th class="text-right py-1">MEM%</th><th class="py-1"></th></tr></thead><tbody>';
        for (const p of procs) {
            html += `<tr class="border-b border-white/5 hover:bg-white/5">
                <td class="py-1 font-mono">${p.pid}</td>
                <td class="py-1">${p.name || '-'}</td>
                <td class="py-1 text-right text-purple-400">${(p.memory_percent||0).toFixed(1)}%</td>
                <td class="py-1 text-right"><button onclick="killProcess(${p.pid})" class="text-red-400 hover:text-red-200 px-2">Kill</button></td>
            </tr>`;
        }
        html += '</tbody></table>';
        table.innerHTML = html;
    } catch(e) {
        table.innerHTML = `<p class="text-red-400">${output}</p>`;
    }
};
```

- [ ] **Step 3: Update `app.js` `handleCommandUpdate` to dispatch CMD_LIST_PROCESSES**

In `src/server/static/js/app.js`, in `handleCommandUpdate`, after the `CMD_SYSTEM_INFO` check, add:

```javascript
if (data.type === 'CMD_LIST_PROCESSES' && window.handleProcessList) {
    window.handleProcessList(data.output || '');
}
```

- [ ] **Step 4: Commit**

```bash
git add src/server/templates/core/detail.html src/server/static/js/app.js
git commit -m "feat: add process manager and clipboard UI panels"
```

---

### Task 7: Add file browser panel and path navigation

**Files:**
- Modify: `src/server/templates/core/detail.html`

- [ ] **Step 1: Add File Browser panel after Clipboard panel**

```html
<!-- File Browser -->
<div class="glass p-6 rounded-2xl">
    <h3 class="text-xl font-bold mb-4">File Browser</h3>
    <div class="flex space-x-3 mb-3">
        <input id="file-path-input" type="text" value="C:/"
            class="flex-1 bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-sm font-mono focus:outline-none focus:border-primary"
            onkeydown="if(event.key==='Enter') browsePath()" />
        <button onclick="browsePath()"
            class="px-4 py-2 bg-indigo-600/20 border border-indigo-500/30 rounded-lg hover:bg-indigo-600/40 transition text-sm">
            Browse
        </button>
    </div>
    <div id="file-list" class="overflow-auto max-h-64 text-sm">
        <p class="text-gray-500 italic">Enter a path and click Browse.</p>
    </div>
</div>
```

- [ ] **Step 2: Add JS functions for file browser**

```javascript
function browsePath() {
    const path = document.getElementById('file-path-input').value.trim();
    if (!path) return;
    sendCommand('CMD_FILE_LIST', { path: path });
}

function readFile(path) {
    sendCommand('CMD_FILE_READ', { path: path });
}

window.handleFileList = function(output) {
    const container = document.getElementById('file-list');
    if (!container) return;
    try {
        const items = JSON.parse(output);
        let html = '<ul class="space-y-1">';
        for (const item of items) {
            const icon = item.type === 'dir' ? '📁' : '📄';
            const sizeStr = item.size != null ? `<span class="text-gray-500 text-xs ml-2">${(item.size/1024).toFixed(1)}KB</span>` : '';
            if (item.type === 'dir') {
                html += `<li class="hover:bg-white/5 rounded px-2 py-1 cursor-pointer" onclick="navigateTo('${item.path.replace(/\\/g, '\\\\')}')">
                    ${icon} ${item.name}
                </li>`;
            } else {
                html += `<li class="hover:bg-white/5 rounded px-2 py-1 flex justify-between items-center">
                    <span>${icon} ${item.name}${sizeStr}</span>
                    <button onclick="readFile('${item.path.replace(/\\/g, '\\\\')}');" class="text-xs text-primary hover:text-white ml-4">View</button>
                </li>`;
            }
        }
        html += '</ul>';
        container.innerHTML = html;
    } catch(e) {
        container.innerHTML = `<p class="text-red-400">${output}</p>`;
    }
};

function navigateTo(path) {
    document.getElementById('file-path-input').value = path;
    sendCommand('CMD_FILE_LIST', { path: path });
}
```

- [ ] **Step 3: Update `app.js` to dispatch CMD_FILE_LIST and CMD_FILE_READ**

Add to `handleCommandUpdate` in `app.js`:

```javascript
if (data.type === 'CMD_FILE_LIST' && window.handleFileList) {
    window.handleFileList(data.output || '');
}
```

- [ ] **Step 4: Commit**

```bash
git add src/server/templates/core/detail.html src/server/static/js/app.js
git commit -m "feat: add file browser panel with directory navigation and file view"
```

---

### Task 8: Add pyperclip to requirements

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Check if pyperclip is in requirements**

```
grep pyperclip requirements.txt
```

- [ ] **Step 2: If missing, add it**

```
echo "pyperclip" >> requirements.txt
```

- [ ] **Step 3: Install it**

```
pip install pyperclip
```

- [ ] **Step 4: Run full test suite**

```
pytest src/server/tests/ -v
```
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add requirements.txt
git commit -m "chore: add pyperclip dependency for clipboard executors"
```
