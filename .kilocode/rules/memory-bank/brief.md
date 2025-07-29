This is a customized version of Komga, a Manga reading server. The customization aims at adding a "PUSH TO KINDLE BUTTON" which adds the following functionality:

1) ✅ **COMPLETED**: The WEBUI passes file path(s) to the Python script (komga_custom/push_to_kindle.py)
2) ✅ **COMPLETED**: If CBR is detected, it's converted to temporary CBZ
3) ✅ **COMPLETED**: Kindle Comic Converter (KCC) integration handles all image formats natively including AVIF/WEBP
4) ✅ **COMPLETED**: Files are pushed to remote Kindle device using SCP

## **COMPLETED FEATURES** ✅

1) ✅ **Multi-file folder organization**: If multiple files are pushed at once, creates a folder named as the series name; otherwise, pushes single files to "New Volume" folder

2) ✅ **PUSH TO KINDLE button for selected books**: Added to the menu that appears when multiple books in the same series are selected in WEBUI

3) ✅ **Kindle Comic Converter (KCC) Integration**: 
   - Added `process_with_kcc` function that calls KCC with optimized parameters
   - Uses command: `python3 kcc-c2e.py -p KPW5 -q -u --mozjpeg -f CBZ -o <output_path> <book_path>`
   - Handles all image formats natively (AVIF/WEBP/JPG/PNG/etc.)

4) ✅ **KCC Installation**: KCC is included in the komga_custom folder with all dependencies

## **CURRENT ARCHITECTURE**

The push-to-kindle feature uses a Python-based implementation with the following components:

### **Frontend Components** ✅
- **MultiSelectBar.vue**: Push button for multiple selected books in the multi-select toolbar
- **BrowseSeries.vue**: Series-level push functionality
- **BrowseBook.vue**: Individual book push functionality

### **Backend Components** ✅
- **BookController.kt**: REST endpoints for single and multiple book push
- **SeriesController.kt**: REST endpoint for series-level push
- **push_to_kindle.py**: Main Python processing script with KCC integration

### **Processing Pipeline** ✅
1. **File Validation**: Checks file existence and media readiness
2. **KCC Processing**: Uses Kindle Comic Converter for optimal format conversion
3. **Folder Organization**: Creates appropriate folder structure on Kindle
4. **SCP Transfer**: Secure file transfer to Kindle device

### **Environment Variables** ✅
- `KINDLE_IP`: Kindle device IP address
- `KINDLE_USER`: SSH username for Kindle
- `KINDLE_REMOTE_PATH`: Target directory on Kindle
- `KINDLE_SSH_PASSWORD`: SSH password (optional for key-based auth)
- `KINDLE_SSH_PORT`: SSH port (default: 2222)

## **STATUS**: **PRODUCTION READY** ✅
All planned features have been implemented and tested successfully.