# Technologies and Implementation Details

## Current Tech Stack
- **Backend**: Kotlin/Spring Boot
- **Frontend**: Vue.js
- **File Processing**: Python (confirmed as production-ready)
- **Image Processing**: Kindle Comic Converter (KCC) - handles all formats natively
- **Archive Handling**: rarfile (Python) + KCC for CBZ/CBR processing
- **Transfer Protocol**: SCP via sshpass (Python) + SCP client

## Current Dependencies (Python-based)
- **RarFile**: For CBR file extraction
- **Kindle Comic Converter (KCC)**: Native image format support including AVIF/WEBP
- **sshpass**: SSH password authentication
- **subprocess**: Process execution for external tools
- **os/pathlib**: File system operations
- **tempfile**: Temporary file management

## Environment Variables
- **KINDLE_IP**: Kindle device IP address
- **KINDLE_USER**: SSH username for Kindle
- **KINDLE_REMOTE_PATH**: Target directory on Kindle
- **KINDLE_SSH_PASSWORD**: SSH password (optional for key-based auth)
- **KINDLE_SSH_PORT**: SSH port (default: 2222)

## File Processing Pipeline
1. **Input Validation**: Check file existence and format
2. **CBR Processing**: Convert RAR archives to ZIP (CBZ) using rarfile
3. **KCC Processing**: Kindle Comic Converter applies Kindle-specific optimizations
4. **Folder Organization**: Creates appropriate folder structure on Kindle
5. **SCP Transfer**: Upload processed file to Kindle device

## Error Handling Strategy
- **File Not Found**: Return 404 for missing files
- **Conversion Failures**: Return 500 with detailed error messages
- **Transfer Failures**: Retry mechanism for network issues
- **Configuration Errors**: Validate all required properties on startup

## Performance Considerations
- **Async Processing**: Spring Boot async endpoints for I/O operations
- **Temporary Files**: Clean up temp files after processing
- **Memory Management**: Stream processing via KCC for large archives
- **Concurrent Processing**: Allow parallel processing for series

## Development Setup
- **Python 3.8+**: Required for the processing script
- **KCC**: Included in `komga_custom/kindlecomicconverter/`
- **sshpass**: System package for SSH password authentication
- **rarfile**: Python package for RAR archive handling

## Deployment Notes
- **Docker**: All dependencies included in container
- **Environment Variables**: Must be configured for production
- **SSH Setup**: Ensure SSH access to Kindle is configured
- **File Permissions**: Ensure read access to Komga library files