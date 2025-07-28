# System Architecture

## Current Architecture Overview
The push-to-kindle feature follows a pipeline pattern with these components:

### Frontend Components
- **BrowseBook.vue**: Single book push button
- **BrowseSeries.vue**: Series push button for multiple books

### Backend Components
- **BookController.kt**: REST endpoint `/api/v1/books/{bookId}/kindle`
- **SeriesController.kt**: REST endpoint `/api/v1/series/{seriesId}/kindle`
- **Python Script**: External process execution via ProcessBuilder

### External Dependencies
- **RarFile**: CBR file handling
- **Pillow**: Image processing and format conversion
- **sshpass**: SSH password authentication
- **SCP**: File transfer to Kindle

## Proposed Kotlin Architecture

### Service Layer
- **PushToKindleService**: Main orchestrator service
- **FileConversionService**: Handles CBR to CBZ conversion
- **ImageConversionService**: Handles image format conversion to JPG
- **ImageResizingService**: Resizes images to Kindle Paperwhite aspect ratio (1246x1648) with black margins
- **ScpTransferService**: Handles SCP file transfer to Kindle

### Configuration
- **KindleConfig**: Configuration properties for Kindle connection
- **ApplicationProperties**: Centralized configuration management

### Data Flow
```
Frontend (Vue.js) → REST Controllers → Service Layer → [File Processing → Image Processing → Resizing → SCP Transfer] → Kindle
```

### Image Processing Pipeline
1. **Format Conversion**: WEBP/AVIF/PNG → JPG
2. **Aspect Ratio Adjustment**: Resize to 1246x1648 with black margins
3. **Quality Optimization**: Maintain readability while minimizing file size

### Key Components Location
- **Source Code**: `komga/src/main/kotlin/org/gotson/komga`
- **Services**: `komga/src/main/kotlin/org/gotson/komga/infrastructure/kindle`
- **Configuration**: `komga/src/main/kotlin/org/gotson/komga/infrastructure/configuration`
- **Controllers**: `komga/src/main/kotlin/org/gotson/komga/interfaces/api/rest`