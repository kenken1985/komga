# Technologies and Implementation Details

## Current Tech Stack
- **Backend**: Kotlin/Spring Boot
- **Frontend**: Vue.js
- **File Processing**: Python (to be replaced with Kotlin)
- **Image Processing**: Pillow (to be replaced with Java libraries)
- **Archive Handling**: rarfile (to be replaced with Java libraries)
- **Transfer Protocol**: SCP via sshpass (to be replaced with SSH/SCP libraries)

## Required Dependencies for Kotlin Implementation
- **Spring Boot**: Core framework
- **JSch**: SSH/SCP client for file transfer
- **Apache Commons Compress**: Archive handling (CBR/CBZ)
- **ImageIO**: Java image processing
- **TwelveMonkeys ImageIO**: Additional image format support (WEBP, AVIF)

## Environment Variables
- **KINDLE_IP**: Kindle device IP address
- **KINDLE_USER**: SSH username for Kindle
- **KINDLE_REMOTE_PATH**: Target directory on Kindle
- **KINDLE_SSH_PASSWORD**: SSH password (optional for key-based auth)
- **KINDLE_SSH_PORT**: SSH port (default: 22)

## File Processing Pipeline
1. **Input Validation**: Check file existence and format
2. **CBR Processing**: Convert RAR archives to ZIP (CBZ)
3. **Image Conversion**: Convert non-JPG images to JPG format
4. **Image Resizing**: Resize images to 1246x1648 with black margins
5. **Archive Rebuild**: Create new CBZ with converted images
6. **SCP Transfer**: Upload processed file to Kindle

## Error Handling Strategy
- **File Not Found**: Return 404 for missing files
- **Conversion Failures**: Return 500 with detailed error messages
- **Transfer Failures**: Retry mechanism for network issues
- **Configuration Errors**: Validate all required properties on startup

## Performance Considerations
- **Async Processing**: Use Kotlin coroutines for I/O operations
- **Temporary Files**: Clean up temp files after processing
- **Memory Management**: Stream processing for large archives
- **Concurrent Processing**: Allow parallel processing for series