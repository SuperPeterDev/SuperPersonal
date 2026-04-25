# detailed Technical Design

## 1. Additional Tech Stack
To satisfy the requirements for "Real-time", "Smart", and "Reliable":
*   **Django Channels**: For WebSocket support. Enables real-time server-to-client command pushing without aggressive polling.
*   **Redis**: Backing store for Channels and potential task queues.
*   **Django REST Framework (DRF)**: For robust, standard API creation.
*   **JWT (JSON Web Tokens)**: Stateless validation for client authentication.
*   **Celery**: For handling scheduled tasks or heavy background processing on the server.
*   **Pytest**: For a powerful testing framework (more flexible than `unittest`).

## 2. Available Commands
The system will support the following commands (`CommandType`):
1.  `CMD_PING`: Health check.
2.  `CMD_SHELL_EXEC`: Run a shell command (e.g., `ipconfig`, `dir`).
3.  `CMD_OPEN_BROWSER`: Open a specific URL.
4.  `CMD_SCREENSHOT`: Capture and upload a screenshot.
5.  `CMD_SYSTEM_INFO`: Retrieve CPU/RAM usage.
6.  `CMD_LOCK_PC`: Lock the workstation.
7.  `CMD_SHUTDOWN`: (Protected) Shutdown the PC.
8.  `CMD_RESTART`: (Protected) Restart the PC.
9.  `CMD_SCHEDULED_SHUTDOWN`: Schedule a shutdown with a delay (payload: `{seconds: int}`).
10. `CMD_SET_VOLUME`: Set system volume (payload: `{level: int, mute: bool}`).

## 3. System Flows

### 3.1 Device Registration Flow
1.  **Client** starts up. Generates or reads a unique Hardware ID (UUID).
2.  **Client** sends `POST /api/v1/devices/register` with Metadata (Hostname, OS, IP).
3.  **Server** validates and creates/updates `Tbl_Device`.
4.  **Server** returns `access_token` (JWT).

### 3.2 Command Execution Flow (Happy Path)
1.  **User** (Web UI) clicks "Take Screenshot".
2.  **Server** creates `Tbl_Command` with status `PENDING`.
3.  **Server** pushes event via WebSocket to **Client** channel OR **Client** polls `GET /commands/pending`.
4.  **Client** receives command, creates local queue item.
5.  **Client** acknowledges receipt -> **Server** updates status to `QUEUED`.
6.  **Client** executes logic (takes screenshot).
7.  **Client** posts result to `POST /api/v1/commands/{id}/result`.
8.  **Server** updates `Tbl_Command` status to `SUCCESS` and stores output in `Tbl_CommandLog`.
9.  **Server** updates Web UI via WebSocket.

## 4. API Specification
**Base URL**: `/api/v1`

### Authentication
*   `POST /auth/device-login`: Exchange Device UUID for JWT.

### Devices
*   `GET /devices`: List all devices.
*   `POST /devices/register`: Register a new device.
*   `GET /devices/{id}`: Detailed view.

### Commands
*   `POST /commands`: Issue a command.
    *   Body: `{"device_id": "...", "type": "CMD_OPEN_BROWSER", "payload": {"url": "google.com"}}`
*   `GET /commands/pending`: (For polling clients) Get pending commands.
*   `POST /commands/{id}/ack`: Acknowledge receipt (`QUEUED`).
*   `POST /commands/{id}/result`: Submit execution result.
    *   Body: `{"status": "SUCCESS", "output": "...", "error_log": null}`

## 5. SQL Database Design (Schema)
Using Django ORM mapping to SQL Tables:

### `Tbl_Device`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `PK_DeviceID` | UUID | Primary Key | Unique internal ID |
| `HardwareID` | String | Unique, Index | Client-generated persistent ID |
| `Hostname` | String | | |
| `OSConfig` | JSON | | OS version, Architecture |
| `LastSeen` | DateTime | Index | For online/offline status |
| `IsActive` | Boolean | Default True | Logical delete |

### `Tbl_Preset`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `PK_PresetID` | UUID | Primary Key | |
| `Name` | String | | e.g. "LoFi Playlist" |
| `URL` | String | | e.g. "youtube.com/..." |
| `Icon` | String | | Optional icon class |
| `CreatedAt` | DateTime | Auto Now | |

### `Tbl_Command`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `PK_CommandID` | UUID | Primary Key | |
| `FK_DeviceID` | UUID | Foreign Key | Target Device |
| `CommandType` | String | Index | User-friendly type |
| `Payload` | JSON | | Args for command |
| `Status` | Enum | Index | PENDING, SENT, QUEUED, RUNNING, SUCCESS, FAILED, CANCELLED |
| `CreatedAt` | DateTime | Auto Now | |
| `ExecutedAt` | DateTime | Nullable | |

### `Tbl_CommandLog`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `PK_LogID` | UUID | Primary Key | |
| `FK_CommandID` | UUID | Foreign Key | Link to command |
| `Output` | Text | | Stdout or Return value |
| `ErrorTrace` | Text | | Stderr or Exception trace |

## 6. Testing Strategy
Following the "Reliable" requirement:

### Server-Side (Pytest-Django)
*   **Model Tests**: Verify `Tbl_Command` state transitions (e.g., cannot go from FAILED to QUEUED).
*   **API Tests**: Test `POST /register` with valid/invalid payloads. Test auth barriers.
*   **Integration**: Simulate a full flow: Create Command -> Mock Client Fetch -> Mock Client Result -> Verify DB State.

### Client-Side (Pytest)
*   **Command Processor**: Unit test each `CMD_` function.
*   **Queue**: Test offline behavior (add to queue, retry on reconnect).
*   **Mocking**: Use `requests-mock` to simulate Server APIs.
