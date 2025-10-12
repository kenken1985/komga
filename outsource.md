# Outsource Document: Add Processing Time to Kindle Push History

## 1. Goal

Add processing time reporting to the "Book pushed to Kindle successfully" message in the webUI History section. The processing time should be displayed in the history details dialog when users click the information button for a successful Kindle push event.

## 2. Complete Folder Structure

```
komga/
├── komga/src/main/kotlin/org/gotson/komga/domain/model/HistoricalEvent.kt
├── komga/src/main/kotlin/org/gotson/komga/interfaces/api/rest/BookController.kt
└── komga_custom/
    └── push_to_kindle.py

komga-webui/
└── src/views/HistoryView.vue
```

## 3. Source Code (per file)

### File: komga/src/main/kotlin/org/gotson/komga/domain/model/HistoricalEvent.kt

The `BookPushedToKindleSuccess` class needs to be updated to include processing time in its properties.

### File: komga/src/main/kotlin/org/gotson/komga/interfaces/api/rest/BookController.kt

The `pushToKindle` method needs to be updated to:
1. Capture processing time from the Python script output
2. Include processing time in the `BookPushedToKindleSuccess` historical event

### File: komga_custom/push_to_kindle.py

The `main()` function needs to be updated to:
1. Add timing measurement around the main processing logic
2. Output processing time in a structured format for the backend to parse

### File: komga-webui/src/views/HistoryView.vue

The `formatPropertyKey` and `showDetails` methods may need updates to properly display the processing time in the history details dialog.

## 4. Data Structures

### HistoricalEventDto (Frontend)
```typescript
export interface HistoricalEventDto {
  type: string,
  timestamp: Date,
  bookId?: string,
  seriesId?: string,
  properties: Record<string, string>[],
}
```

### BookPushedToKindleSuccess (Backend - Current)
```kotlin
class BookPushedToKindleSuccess(
  book: Book,
  series: Series,
  kindlePath: String,
) : HistoricalEvent(
  type = "BookPushedToKindleSuccess",
  bookId = book.id,
  seriesId = series.id,
  properties = mapOf(
    "name" to book.path.toString(),
    "series" to series.name,
    "kindle_path" to kindlePath,
  ),
)
```

### BookPushedToKindleSuccess (Backend - Updated)
```kotlin
class BookPushedToKindleSuccess(
  book: Book,
  series: Series,
  kindlePath: String,
  processingTimeSeconds: Long,
) : HistoricalEvent(
  type = "BookPushedToKindleSuccess",
  bookId = book.id,
  seriesId = series.id,
  properties = mapOf(
    "name" to book.path.toString(),
    "series" to series.name,
    "kindle_path" to kindlePath,
    "processing_time_seconds" to processingTimeSeconds.toString(),
  ),
)
```

## 5. Expected Output

### Frontend Display
When users view the history details for a successful Kindle push, they should see:

```
Type: Book pushed to Kindle
Name: /path/to/book.cbz
Series: Series Name
Kindle Path: New Volume
Processing Time: 45 seconds
Timestamp: 2025-01-15 14:30:25
```

### Script Output
The Python script should output processing time in a structured format:
```
HISTORICAL_EVENT_KINDLE_PATH:New Volume
HISTORICAL_EVENT_PROCESSING_TIME:45
SCRIPT_STATUS:SUCCESS
```

### Backend Event Creation
The controller should parse the processing time and create the historical event with the timing information included.

## Implementation Notes

1. **Timing Measurement**: Processing time should be measured from the start of script execution until completion, covering file processing, KCC conversion, and SCP transfer.

2. **Error Handling**: If timing measurement fails, the system should still function normally but without processing time data.

3. **Backward Compatibility**: The changes should be backward compatible. Historical events created without processing time should still display properly.

4. **Unit Formatting**: Processing time should be displayed in seconds with appropriate formatting (e.g., "45 seconds" for times under 60 seconds, "1 minute 5 seconds" for longer times).

5. **Data Validation**: The backend should validate that the processing time is a reasonable number (positive, not excessively large).