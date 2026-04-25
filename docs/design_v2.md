# Design V2: Modular OOP Architecture

## Overview
This document outlines the refactored architecture of the SuperPersonal system, focusing on Object-Oriented Principles, Type Safety, and Clean Architecture.

## Shared Library (`src/shared`)
A single source of truth for command definitions and data structures.
- **Enums**: `CommandType`, `CommandStatus` provide strict typing for command logic.
- **Schemas**: Pydantic models (`Command`, `CommandPayload`, `CommandResult`) ensure data validation across Client and Server.

## Client Architecture (`src/client`)
The client has been refactored from a monolithic script to a modular application.

### Core Components
1.  **ClientApp** (`client.py`): The main orchestrator. Initializes API client and handles the event loop.
2.  **APIClient** (`core/api_client.py`): Handles all HTTP communication with the server. Uses Pydantic to parse responses into typed objects.
3.  **ExecutorRegistry** (`core/registry.py`): A central registry where command executors are registered via decorators.
4.  **CommandExecutor** (`core/executor.py`): Abstract Base Class defining the contract (`execute(payload) -> CommandResult`) for all commands.

### Executors
Command logic is split into domain-specific modules:
-   `system_executors.py`: Ping, System Info.
-   `browser_executors.py`: Browser automation.
-   `media_executors.py`: Volume and Media control (with smart fallbacks).
-   `power_executors.py`: Shutdown, Restart, Lock.

## Server Architecture (`src/server`)
The Django server now shares definitions with the client to prevent contract mismatches.
-   **Models**: updated to use `src.shared.enums` for `command_type` and `status`.
-   **Views**: updated to respect the shared enum definitions.

## Workflow
1.  **Registration**: Client generates Hardware ID -> Registers via API -> Server stores Device.
2.  **Command Creation**: Admin/Dashboard creates a Command (Pending) in DB.
3.  **Polling**: Client polls `/commands/pending/`.
4.  **Execution**: `ClientApp` dispatches command to appropriate `Executor`.
5.  **Result**: Executor returns `CommandResult` -> Client sends Result to Server.

## Directory Structure
```
src/
├── client/
│   ├── core/           # Framework logic
│   ├── executors/      # Business logic
│   ├── utils/          # Helpers
│   └── client.py       # Entry point
├── server/
│   ├── api/            # Django App
│   └── ...
├── shared/             # Common code
│   ├── enums.py
│   └── schemas.py
└── utils/              # General utils
```
