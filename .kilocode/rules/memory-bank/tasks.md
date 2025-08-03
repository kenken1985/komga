# Task Documentation

This file contains documentation for repetitive tasks and workflows that may be needed for future development or maintenance of the push-to-kindle feature.

## Add Multi-Select Push Functionality
**Last performed**: Not yet performed
**Status**: Planned for future implementation

**Files to modify:**
- `komga-webui/src/components/bars/MultiSelectBar.vue` - Add push-to-kindle button
- `komga/src/main/kotlin/org/gotson/komga/interfaces/api/rest/BookController.kt` - Add endpoint for multiple books
- `komga-webui/src/views/BrowseSeries.vue` - Update MultiSelectBar event handling

**Steps:**
1. Add push-to-kindle button to MultiSelectBar.vue template
2. Implement pushToKindle method in MultiSelectBar.vue component
3. Add REST endpoint in BookController.kt for handling multiple book IDs
4. Update BrowseSeries.vue to handle the new push-to-kindle event
5. Test with multiple selected books

**Important notes:**
- Use mdi-send icon for consistency with existing buttons
- Place button on the left side of existing icons
- Reuse existing Python script for processing
- Ensure proper error handling for multiple file transfers
- Consider rate limiting for large batches

## Update Kindle Comic Converter (KCC)
**Last performed**: Not yet performed
**Status**: Maintenance task

**Files to modify:**
- `komga_custom/kindlecomicconverter/` - KCC module files
- `komga_custom/push_to_kindle.py` - Update KCC integration if needed

**Steps:**
1. Check for KCC updates from upstream repository
2. Update KCC module files if new version available
3. Test with all supported image formats (AVIF, WEBP, PNG, JPG)
4. Verify KCC command parameters are still optimal
5. Update documentation if parameters change

**Important notes:**
- KCC is located at `/app/komga_custom/kcc-c2e.py`
- Current command: `python3 kcc-c2e.py -p KPW5 -q -u --mozjpeg -f CBZ -o <output_path> <book_path>`
- Test with various comic file formats and sizes
- Monitor for any deprecation warnings or breaking changes

## Add New Kindle Model Support
**Last performed**: Not yet performed
**Status**: Future enhancement

**Files to modify:**
- `komga_custom/push_to_kindle.py` - Update KCC parameters
- `komga/src/main/kotlin/org/gotson/komga/interfaces/api/rest/BookController.kt` - Add model detection
- `komga/src/main/kotlin/org/gotson/komga/interfaces/api/rest/SeriesController.kt` - Add model detection

**Steps:**
1. Research new Kindle device specifications
2. Update KCC parameters for new device profile
3. Add device detection logic if needed
4. Test file transfer and format conversion
5. Update documentation with supported models

**Important notes:**
- Current device profile: KPW5 (Kindle Paperwhite 5th generation)
- KCC supports various device profiles with different optimizations
- Consider adding environment variable for device model
- Test with actual device when possible

## Environment Configuration Updates
**Last performed**: Ongoing maintenance
**Status**: Operational task

**Files to modify:**
- `komga_custom/push_to_kindle.py` - Environment variable handling
- Docker configuration files
- Documentation files

**Steps:**
1. Review current environment variables and defaults
2. Add new configuration options if needed
3. Update validation logic for environment variables
4. Test with different configuration scenarios
5. Update documentation

**Important notes:**
- Current environment variables: KINDLE_IP, KINDLE_USER, KINDLE_REMOTE_PATH, KINDLE_SSH_PASSWORD, KINDLE_SSH_PORT
- Default values should be sensible but not production-ready
- Provide clear error messages for missing required configurations
- Support both password and key-based authentication

## Error Handling and Logging Improvements
**Last performed**: Not yet performed
**Status**: Future enhancement

**Files to modify:**
- `komga_custom/push_to_kindle.py` - Enhanced error handling
- Backend controllers - Improved error responses
- Frontend components - Better user feedback

**Steps:**
1. Analyze current error handling patterns
2. Add more specific error types and messages
3. Implement retry logic for transient failures
4. Add comprehensive logging throughout the pipeline
5. Update frontend to show detailed error information

**Important notes:**
- Current timeout: 300 seconds for SCP, 600 seconds for KCC
- Consider adding progress indicators for long operations
- Log both success and failure cases with relevant details
- Provide actionable error messages for users
- Consider adding monitoring/metrics collection