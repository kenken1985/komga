# System Architecture

## Current Architecture Overview
The push-to-kindle feature follows a pipeline pattern with these components:

### Frontend Components
- **BrowseBook.vue**: Single book push button ✅ IMPLEMENTED
  - Location: Lines 227-234 and 283-290
  - Icon: mdi-send
  - Function: Calls `this.$komgaBooks.pushToKindle(this.book.id)`
- **BrowseSeries.vue**: Series push button for multiple books ✅ IMPLEMENTED
  - Location: Lines 206-213 and 277-284
  - Icon: mdi-send
  - Function: Calls `this.$komgaSeries.pushToKindle(this.seriesId)`
- **MultiSelectBar.vue**: Push button for multiple selected books in the multi-select toolbar ❌ NOT IMPLEMENTED
  - Planned: Left-most button with mdi-send icon
  - Current: No push-to-kindle functionality present

### Backend Components
- **BookController.kt**: REST endpoint `/api/v1/books/{bookId}/push-to-kindle` ✅ IMPLEMENTED
  - Location: Lines 772-797
  - Function: Executes Python script with single book path
- **SeriesController.kt**: REST endpoint `/api/v1/series/{seriesId}/push-to-kindle` ✅ IMPLEMENTED
  - Location: Lines 880-909
  - Function: Executes Python script with multiple book paths
- **Python Script**: External process execution via ProcessBuilder ✅ IMPLEMENTED
  - Location: `/app/komga_custom/push_to_kindle.py`
  - Function: Main processing pipeline with KCC integration

### External Dependencies
- **RarFile**: CBR file handling
- **Kindle Comic Converter (KCC)**: Native image format support including AVIF/WEBP
- **sshpass**: SSH password authentication
- **SCP**: File transfer to Kindle

## Architecture Decision
**CANCELLED**: The Kotlin refactoring has been cancelled. The system remains Python-based as requested.

## Current Python Architecture

### Processing Pipeline
1. **File Validation**: Check file existence and media readiness
2. **KCC Processing**: Uses Kindle Comic Converter for optimal format conversion
3. **Folder Organization**: Creates appropriate folder structure on Kindle
4. **SCP Transfer**: Secure file transfer to Kindle device

### Key Components Location
- **Source Code**: `komga/src/main/kotlin/org/gotson/komga`
- **Controllers**: `komga/src/main/kotlin/org/gotson/komga/interfaces/api/rest`
- **Python Script**: `komga_custom/push_to_kindle.py`
- **KCC Module**: `komga_custom/kindlecomicconverter/`

### Data Flow
```
Frontend (Vue.js) → REST Controllers → Python Script → [KCC Processing → Folder Organization → SCP Transfer] → Kindle
```

### Image Processing Pipeline
1. **Format Support**: KCC handles all image formats natively (WEBP/AVIF/PNG/JPG)
2. **Optimization**: KCC applies Kindle-specific optimizations
3. **Quality**: Maintains readability while minimizing file size

### Configuration
- **Environment Variables**: 
  - `KINDLE_IP`: Kindle device IP address
  - `KINDLE_USER`: SSH username for Kindle
  - `KINDLE_REMOTE_PATH`: Target directory on Kindle
  - `KINDLE_SSH_PASSWORD`: SSH password (optional for key-based auth)
  - `KINDLE_SSH_PORT`: SSH port (default: 2222)