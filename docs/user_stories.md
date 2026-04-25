# User Stories & User Flows

## 1. User Stories

### Epicl: Device Control
*   **US-1**: As a user, I want to see a list of all my connected devices so that I know which ones are online.
*   **US-2**: As a user, I want to take a screenshot of a specific device so that I can see what is on the screen.
*   **US-3**: As a user, I want to schedule a shutdown for my PC in 1 hour so that I don't leave it running all night.
    *   *Acceptance Criteria*: User selects "Shutdown", chooses "1 Hour" delay, system confirms schedule.
*   **US-4**: As a user, I want to cancel a scheduled shutdown if I change my mind.
*   **US-5**: As a user, I want to set the volume to 50% remotely so I can adjust music without getting up.

### Epic: Intelligence & Monitoring
*   **US-6**: As a user, I want to save a YouTube link as a "Preset" so I can easily reopen it later.
*   **US-7**: As a user, I want to see real-time CPU and RAM usage so I can detect performance issues.
*   **US-8**: As a user, I want the system to suggest "Close Browser" if RAM is > 90% (Smart Feature).

### Epic: Reliability
*   **US-9**: As a user, I want commands to be queued if my device is offline, and executed when it comes back online.

## 2. User Flow Diagram (Text Description)

**Flow: Scheduling a Shutdown**
1.  **Start**: User logs into Web Dashboard.
2.  **Select**: User clicks on "Gaming PC" card.
3.  **Action**: User clicks "Power Options" -> "Schedule Shutdown".
4.  **Input**: User enters "3600" seconds (or selects "1 Hour").
5.  **Submit**: System sends `CMD_SCHEDULED_SHUTDOWN` to Server.
6.  **Feedback**: Server pushes "Command Queued" notification.
7.  **Execution**:
    *   *If Online*: Client receives command, runs `shutdown /s /t 3600`.
    *   *If Offline*: Command waits in Queue.
8.  **End**: User sees "Shutdown Scheduled for [Time]" on dashboard.
