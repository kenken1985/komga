Of course. Here are the specific functions and code blocks that need to be changed to implement the processing time feature, keeping the logic concentrated in the Python script.

-----

### **`komga/src/main/kotlin/org/gotson/komga/domain/model/HistoricalEvent.kt`**

In this file, only the `BookPushedToKindleSuccess` class needs to be updated to accept the processing time. This change is backward compatible.

```kotlin
  class BookPushedToKindleSuccess(
    book: Book,
    series: Series,
    kindlePath: String,
    processingTimeSeconds: Long?,
  ) : HistoricalEvent(
    type = "BookPushedToKindleSuccess",
    bookId = book.id,
    seriesId = series.id,
    properties =
      mapOf(
        "name" to book.path.toString(),
        "series" to series.name,
        "kindle_path" to kindlePath,
      ) + (processingTimeSeconds?.let { mapOf("processing_time_seconds" to it.toString()) } ?: emptyMap()),
  )
```

-----

### **`komga/src/main/kotlin/org/gotson/komga/interfaces/api/rest/BookController.kt`**

You'll need to update the `pushToKindle` function to parse the new output from the script and add a new helper function, `extractProcessingTimeFromOutput`, to handle the parsing.

```kotlin
  @PostMapping("api/v1/books/{bookId}/push-to-kindle")
  @ResponseStatus(HttpStatus.ACCEPTED)
  fun pushToKindle(
    @PathVariable bookId: String,
    @AuthenticationPrincipal principal: KomgaPrincipal,
  ) {
    // Immediate feedback when the button is pressed
    logger.info { "[push_to_kindle] Upload requested from WebUI for book: $bookId. Starting..." }

    bookRepository.findByIdOrNull(bookId)?.let { book ->
      contentRestrictionChecker.checkContentRestriction(principal.user, book)

      val media = mediaRepository.findById(book.id)
      if (media.status != Media.Status.READY) {
        throw ResponseStatusException(HttpStatus.NOT_FOUND, "Book is not ready")
      }

      // Create initialization event
      val series = book.seriesId?.let { seriesRepository.findByIdOrNull(it) }
      if (series != null) {
        historicalEventRepository.insert(HistoricalEvent.BookPushedToKindleInitialized(book, series))
        logger.info { "[push_to_kindle] Created initialization event for book: $bookId" }
      } else {
        logger.warn { "[push_to_kindle] Could not find series for book: $bookId, skipping initialization event" }
      }

      try {
        val processBuilder = ProcessBuilder("python3", "/app/komga_custom/push_to_kindle.py", book.url.path)
        processBuilder.redirectErrorStream(true)
        val process = processBuilder.start()
        val reader = process.inputStream.bufferedReader()
        val preface = "[push_to_kindle] Upload requested from WebUI for book: $bookId. Starting...\n"
        val output = reader.readText()
        logger.info { "Push to kindle script output: $preface$output" }
        val exitCode = process.waitFor()
        
        if (exitCode == 0) {
          // Parse Kindle path and processing time from output
          val kindlePath = extractKindlePathFromOutput(output)
          val processingTime = extractProcessingTimeFromOutput(output)
          if (kindlePath != null) {
            // Create success event for successful push
            if (series != null) {
              historicalEventRepository.insert(HistoricalEvent.BookPushedToKindleSuccess(book, series, kindlePath, processingTime))
            } else {
              logger.warn { "[push_to_kindle] Could not find series for book: $bookId, skipping success event" }
            }
            logger.info { "[push_to_kindle] Successfully created success event for book: $bookId, Kindle path: $kindlePath, Processing time: $processingTime seconds" }
          } else {
            logger.warn { "[push_to_kindle] Push succeeded but could not extract Kindle path from output for book: $bookId" }
            // Create success event even without kindle path
            if (series != null) {
              historicalEventRepository.insert(HistoricalEvent.BookPushedToKindleSuccess(book, series, "", processingTime))
            }
          }
        } else {
          // Script failed - parse error from output
          val errorMessage = extractErrorFromOutput(output) ?: "Script failed with exit code: $exitCode"
          logger.error { "[push_to_kindle] Script failed for book: $bookId, exit code: $exitCode, error: $errorMessage" }
          // Create failure event
          if (series != null) {
            historicalEventRepository.insert(HistoricalEvent.BookPushedToKindleFailed(book, series, errorMessage))
          }
          throw ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "Push to kindle script failed: $errorMessage")
        }
      } catch (e: Exception) {
        logger.error(e) { "Error while executing push to kindle script for book: $bookId" }
        // Create failure event
        val errorMessage = e.message ?: "Script execution failed: ${e::class.simpleName}"
        if (series != null) {
          historicalEventRepository.insert(HistoricalEvent.BookPushedToKindleFailed(book, series, errorMessage))
        }
        throw ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "Error while executing push to kindle script: $errorMessage")
      }
    } ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)
  }

  private fun extractProcessingTimeFromOutput(output: String): Long? {
    val lines = output.split("\n")
    for (line in lines) {
      if (line.startsWith("HISTORICAL_EVENT_PROCESSING_TIME:")) {
        return line.substringAfter("HISTORICAL_EVENT_PROCESSING_TIME:").trim().toLongOrNull()
      }
    }
    return null
  }
```

-----

### **`komga_custom/push_to_kindle.py`**

Add `import time` at the top of the script. Then, replace the `main` function with this version, which captures the start and end times to calculate the total duration.

```python
import time

def main():
    """
    Main function to process and push files to Kindle with folder organization.
    """
    start_time = time.time()
    print("SCRIPT_STATUS:STARTING")
    file_paths = get_files_list_from_webui()
    print(f"Processing files: {file_paths}")

    # Determine target folder based on number of files
    target_folder = "New"
    if len(file_paths) > 1:
        # For multiple files, try to extract series name from first file
        series_name = extract_series_name_from_path(file_paths[0])
        if series_name:
            target_folder = series_name
            print(f"Multiple files detected, using series folder: {target_folder}")
        else:
            print("Multiple files detected but couldn't determine series, using 'New' folder")
    else:
        print("Single file detected, using 'New' folder")

    # Create the target folder on Kindle
    print("SCRIPT_STATUS:CREATING_FOLDER")
    folder_success = create_remote_folder(target_folder)
    if not folder_success:
        print("SCRIPT_STATUS:FAILED")
        print("SCRIPT_ERROR_CODE:FOLDER_CREATION_FAILED")
        print("SCRIPT_ERROR_MESSAGE:Failed to create folder on Kindle device")
        sys.exit(1)

    temp_dir = '/tmp'
    os.makedirs(temp_dir, exist_ok=True)

    all_success = True
    for file_path in file_paths:
        print(f"--- Processing file: {file_path} ---")
        print(f"FILE_STATUS:PROCESSING")
        print(f"FILE_PATH:{file_path}")

        # Check if file is EPUB
        if is_epub_file(file_path):
            print(f"EPUB file detected, skipping KCC processing and pushing directly.")
            kcc_output_file = file_path
            kcc_success = True
            cleaned_cbz_path = False
            original_filename = os.path.basename(file_path)
        else:
            kcc_output_dir = temp_dir

            kcc_success, cleaned_cbz_path, original_filename = process_with_kcc(file_path, kcc_output_dir)
            base_filename = os.path.splitext(os.path.basename(file_path))[0]
            kcc_output_file = os.path.join(kcc_output_dir, f"{base_filename}_kcc.cbz")

        if kcc_success:
            if os.path.exists(kcc_output_file):
                print(f"KCC processing successful. Pushing file to Kindle.")
                print(f"FILE_STATUS:KCC_SUCCESS")
                push_to_kindle(kcc_output_file, target_folder, original_filename)
            else:
                print(f"Error: KCC reported success, but output file '{kcc_output_file}' not found.")
                print(f"FILE_STATUS:FAILED")
                print(f"FILE_ERROR_CODE:OUTPUT_FILE_NOT_FOUND")
                print(f"FILE_ERROR_MESSAGE:KCC reported success, but output file not found")
                all_success = False
        else:
            print(f"KCC processing failed for {file_path}. The file will not be pushed to Kindle.")
            print(f"FILE_STATUS:FAILED")
            print(f"FILE_ERROR_CODE:KCC_PROCESSING_FAILED")
            print(f"FILE_ERROR_MESSAGE:KCC processing failed")
            all_success = False

        # Remove cleaned CBZ if it was created
        if cleaned_cbz_path and os.path.exists(cleaned_cbz_path):
            try:
                os.remove(cleaned_cbz_path)
                print(f"Removed cleaned CBZ: {cleaned_cbz_path}")
            except Exception as cleanup_err:
                print(f"Warning: Failed to remove cleaned CBZ {cleaned_cbz_path}: {cleanup_err}")

        print(f"--- Finished processing file: {file_path} ---")

    end_time = time.time()
    processing_time = int(end_time - start_time)

    if all_success:
        print("SCRIPT_STATUS:SUCCESS")
        print(f"HISTORICAL_EVENT_PROCESSING_TIME:{processing_time}")
    else:
        print("SCRIPT_STATUS:FAILED")
        print("SCRIPT_ERROR_CODE:ONE_OR_MORE_FILES_FAILED")
        print("SCRIPT_ERROR_MESSAGE:One or more files failed to process")
        # Exit with non-zero code to ensure Kotlin controllers detect the failure
        sys.exit(1)
```

-----

### **`komga-webui/src/views/HistoryView.vue`**

To display the processing time nicely, update the details dialog `<tbody>` in the template and add/update two methods in the script section.

#### Template Update

Replace the existing `<tbody>` in the details dialog with this one to add conditional formatting for the processing time.

```html
            <tbody>
            <tr v-for="[key, value] in Object.entries(dialogDetailsItem.properties)" :key="key">
              <td class="text-capitalize font-weight-bold">{{ formatPropertyKey(key) }}</td>
              <td>
                <span v-if="key === 'processing_time_seconds'">{{ formatSeconds(value) }}</span>
                <span v-else>{{ value }}</span>
              </td>
            </tr>
            <tr v-if="getPageHash(dialogDetailsItem)">
              <td class="font-weight-bold">Page</td>
              <td>
                <v-img
                  width="200"
                  height="300"
                  contain
                  :src="pageHashKnownThumbnailUrl(getPageHash(dialogDetailsItem))"
                />
              </td>
            </tr>
            </tbody>
```

#### Script Methods

Update the `formatPropertyKey` method and add the new `formatSeconds` method inside the `methods` object.

```ts
    formatPropertyKey(key: string): string {
      if (key === 'processing_time_seconds') return 'Processing Time'
      // Convert snake_case to Title Case with spaces
      return key
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ')
    },
    formatSeconds(secondsStr: string): string {
      const totalSeconds = parseInt(secondsStr, 10)
      if (isNaN(totalSeconds) || totalSeconds < 0) return secondsStr

      if (totalSeconds < 1) return 'Less than a second'
      if (totalSeconds < 60) {
        return `${totalSeconds} second${totalSeconds > 1 ? 's' : ''}`
      }

      const minutes = Math.floor(totalSeconds / 60)
      const seconds = totalSeconds % 60

      if (seconds === 0) {
        return `${minutes} minute${minutes > 1 ? 's' : ''}`
      }

      return `${minutes} minute${minutes > 1 ? 's' : ''} ${seconds} second${seconds > 1 ? 's' : ''}`
    },
```