# Push To Kindle Progress Page - Technical Specification

## Goal

Add a new page to the Komga web interface that displays log output from the push_to_kindle.py script. This page should be accessible from the sidebar navigation as a subcategory of History. The existing History page should be renamed to "Scan History" and both should be organized under a History menu in the sidebar.

## Complete Folder Structure

```
komga/
├── komga-webui/
│   ├── src/
│   │   ├── views/
│   │   │   ├── HistoryView.vue (existing - needs to be renamed/modified)
│   │   │   ├── PushToKindleProgressView.vue (new - needs to be created)
│   │   │   └── HomeView.vue (existing - needs sidebar modification)
│   │   ├── router.ts (existing - needs route modification)
│   │   ├── locales/ (existing - may need translation updates)
│   │   ├── services/ (existing - may need new service for logs)
│   │   └── types/ (existing - may need new type definitions)
│   └── public/
└── komga/
    └── src/
        └── main/
            └── kotlin/
                └── org/
                    └── gotson/
                        └── komga/
                            └── interfaces/
                                └── api/
                                    └── rest/
                                        ├── BookController.kt (existing - needs modification for log capture)
                                        ├── SeriesController.kt (existing - needs modification for log capture)
                                        └── KindleLogController.kt (new - needs to be created)
```

## Source Code

### Frontend Files

#### File: komga-webui/src/views/HistoryView.vue
- **Current Purpose**: Displays historical events (book deletions, imports, etc.)
- **Required Changes**: 
  - Rename to "ScanHistoryView.vue"
  - Update component name to "ScanHistoryView"
  - Update all references to match new name
  - Modify page title and headers to display "Scan History"

#### File: komga-webui/src/views/PushToKindleProgressView.vue (NEW)
- **Purpose**: Display log output from push_to_kindle.py script
- **Requirements**:
  - Display logs in a scrollable text area with monospace font
  - Auto-refresh logs every 5 seconds
  - Show timestamp for each log entry
  - Include manual refresh button
  - Show clear logs button
  - Display loading indicator while fetching logs
  - Handle error states gracefully
  - Use Vuetify components for consistent UI

#### File: komga-webui/src/views/HomeView.vue
- **Current Purpose**: Main layout with sidebar navigation
- **Required Changes**:
  - Modify sidebar navigation structure to create History menu group
  - Add "Scan History" as first submenu item
  - Add "Push To Kindle Progress" as second submenu item
  - Update icons and routing accordingly
  - Update navigation logic to handle expanded/collapsed state

#### File: komga-webui/src/router.ts
- **Current Purpose**: Define application routes
- **Required Changes**:
  - Update route for HistoryView to point to ScanHistoryView
  - Add new route for PushToKindleProgressView
  - Update route names and paths accordingly
  - Ensure admin guards are properly applied

#### File: komga-webui/src/services/kindle-log.service.ts (NEW)
- **Purpose**: Handle API communication for Kindle logs
- **Requirements**:
  - Method to fetch logs from backend API
  - Method to clear logs from backend API
  - Proper error handling and typing
  - Axios-based HTTP client integration

### Backend Files

#### File: komga/src/main/kotlin/org/gotson/komga/interfaces/api/rest/BookController.kt
- **Current Purpose**: Handle book-related API endpoints
- **Required Changes**:
  - Modify pushToKindle method to capture and store logs
  - Add unique job ID for each push operation
  - Store logs in memory or temporary storage
  - Return job ID in response

#### File: komga/src/main/kotlin/org/gotson/komga/interfaces/api/rest/SeriesController.kt
- **Current Purpose**: Handle series-related API endpoints
- **Required Changes**:
  - Modify pushToKindle method to capture and store logs
  - Add unique job ID for each push operation
  - Store logs in memory or temporary storage
  - Return job ID in response

#### File: komga/src/main/kotlin/org/gotson/komga/interfaces/api/rest/KindleLogController.kt (NEW)
- **Purpose**: Handle Kindle log-related API endpoints
- **Requirements**:
  - GET endpoint to retrieve logs by job ID
  - GET endpoint to list all recent jobs
  - DELETE endpoint to clear logs
  - Proper error handling and response formatting
  - Admin-only access restriction
  - Log storage management (cleanup old logs)

## Data Structures

### Frontend Types

```typescript
// komga-webui/src/types/kindle-log.ts
interface KindleLogEntry {
  timestamp: string;
  level: 'INFO' | 'ERROR' | 'DEBUG' | 'WARNING';
  message: string;
  jobId: string;
}

interface KindleJob {
  id: string;
  type: 'BOOK' | 'SERIES';
  targetId: string;
  status: 'RUNNING' | 'COMPLETED' | 'FAILED';
  startTime: string;
  endTime?: string;
  logEntries: KindleLogEntry[];
}

interface KindleLogResponse {
  jobs: KindleJob[];
  totalElements: number;
}
```

### Backend DTOs

```kotlin
// komga/src/main/kotlin/org/gotson/komga/interfaces/api/rest/dto/KindleLogDto.kt
data class KindleLogEntryDto(
  val timestamp: Instant,
  val level: LogLevel,
  val message: String,
  val jobId: String
)

data class KindleJobDto(
  val id: String,
  val type: JobType,
  val targetId: String,
  val status: JobStatus,
  val startTime: Instant,
  val endTime: Instant?,
  val logEntries: List<KindleLogEntryDto>
)

data class KindleLogResponseDto(
  val jobs: List<KindleJobDto>,
  val totalElements: Int
)

enum class LogLevel {
  INFO, ERROR, DEBUG, WARNING
}

enum class JobType {
  BOOK, SERIES
}

enum class JobStatus {
  RUNNING, COMPLETED, FAILED
}
```

## Expected Output

### 1. Modified Sidebar Navigation
- History menu group with two sub-items:
  - "Scan History" (renamed from original History)
  - "Push To Kindle Progress" (new)

### 2. Push To Kindle Progress Page UI
- Page title: "Push To Kindle Progress"
- Auto-refreshing log display with:
  - Monospace font for log text
  - Color-coded log levels (INFO=blue, ERROR=red, DEBUG=gray, WARNING=orange)
  - Timestamps for each entry
  - Scrollable container for long logs
- Action buttons:
  - Refresh (manual refresh)
  - Clear Logs (with confirmation dialog)
- Loading indicator during API calls
- Error message display when API calls fail

### 3. Backend API Endpoints
- `GET /api/v1/kindle-logs` - Retrieve all recent Kindle jobs with logs
- `GET /api/v1/kindle-logs/{jobId}` - Retrieve specific job logs
- `DELETE /api/v1/kindle-logs` - Clear all logs
- `POST /api/v1/books/{bookId}/push-to-kindle` - Modified to return job ID
- `POST /api/v1/series/{seriesId}/push-to-kindle` - Modified to return job ID

### 4. Log Capture and Storage
- Real-time log capture from push_to_kindle.py script execution
- Temporary storage of logs with automatic cleanup
- Unique job identification for tracking multiple operations
- Proper error handling and log level classification

### 5. User Experience
- Seamless navigation between Scan History and Push To Kindle Progress
- Real-time log updates without page refresh
- Clear visual indication of operation status
- Responsive design that works on all screen sizes
- Consistent with existing Komga UI patterns