# SuperPersonal Project Requirements

## 1. Project Overview
**Project Name**: SuperPersonal
**Description**: A Personal PC WebApp Controller system that allows a user to control their personal computer remotely via a responsive, intelligent web interface. The system consists of a central Django server acting as the controller and a client application running on the target PC to execute commands.

## 2. System Architecture
The system follows a Client-Server architecture:
*   **Server (Controller)**: A Django-based web application hosted on a server (or accessible network location). It provides the UI for the user to issue commands and view status.
*   **Client (Agent)**: A Python application running on the target Personal PC. It connects to the server to receive commands, execute them, and report results.
*   **Communication**: RESTful API (or WebSocket) for reliable command dispatch and status updates.

## 3. Functional Requirements

### 3.1 Server (Web Controller)
*   **User Interface**:
    *   Responsive design for use on mobile and desktop.
    *   "Smart" and "Wise" features with a focus on premium UI/UX.
    *   Dashboard to view connected clients and their status.
*   **Command Management**:
    *   Issue commands to connected clients.
    *   Queue commands if the client is busy or offline.
    *   Cancel pending or running commands.
    *   **Scheduled Shutdown**: Schedule a shutdown command for a future time.
    *   **Volume Control**: Adjust logical system volume (0-100) or Mute/Unmute.
    *   View command history and logs.
*   **Intelligence**:
    *   Smart suggestions or automated workflows (implied by "more wise").
    *   **Link Presets**: Save frequently used links (e.g., YouTube playlists) and open them with one click.

### 3.2 Client (PC Agent)
*   **Command Execution**:
    *   Listen for commands from the server.
    *   Execute system actions (e.g., run scripts, open apps, system control).
    *   Report success, failure, or progress to the server.
*   **Queue Management**:
    *   Handle command queues locally if necessary.
    *   Support cancellation of ongoing tasks.
*   **Reliability**:
    *   Auto-reconnect logic.
    *   Reliable error handling and reporting.

## 4. Non-Functional Requirements
*   **Object-Oriented Programming (OOP)**: Strict adherence to OOP principles in both Server and Client codebases.
*   **Reliability**: The system must handle network interruptions and client execution failures gracefully.
*   **Consistency**: Uniform coding style and behavior across the system.
*   **UX/UI**: High-quality, intuitive interface.

## 5. Data Models (Conceptual)
*   **Client**: Represents a target PC (ID, Name, Status, Last Seen).
*   **Command**: Represents an action to be taken (ID, Type, Params, Status [Queued, Running, Success, Failed, Cancelled], CreatedAt, ExecutedAt).
*   **Log**: Execution logs for commands.

## 6. Technology Stack
*   **Backend**: Python, Django
*   **Frontend**: HTML, CSS (Tailwind/custom), JavaScript (Vue/React or Vanilla as needed for "smart" UI)
*   **Client**: Python
*   **Database**: SQLite/PostgreSQL (via Django ORM)
