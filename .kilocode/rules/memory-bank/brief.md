This is a customized version of Komga, a Manga reading server. The customization aims at adding a "PUSH TO KINDLE BUTTON" which adds the following functionality:

1) ✅ **COMPLETED**: The WEBUI passes file path(s) to the Python script (komga_custom/push_to_kindle.py)
2) ✅ **COMPLETED**: If CBR is detected, it's converted to temporary CBZ
3) ✅ **COMPLETED**: Kindle Comic Converter (KCC) integration handles all image formats natively including AVIF/WEBP
4) ✅ **COMPLETED**: Files are pushed to remote Kindle device using SCP

## **COMPLETED FEATURES** ✅

1) ✅ **Multi-file folder organization**: If multiple files are pushed at once, creates a folder named as the series name; otherwise, pushes single files to "New Volume" folder

2) ✅ **Kindle Comic Converter (KCC) Integration**: 
   - Added `process_with_kcc` function that calls KCC with optimized parameters
   - Uses command: `python3 kcc-c2e.py -p KPW5 -q -u --mozjpeg -f CBZ -o <output_path> <book_path>`
   - Handles all image formats natively (AVIF/WEBP/JPG/PNG/etc.)

3) ✅ **KCC Installation**: KCC is included in the komga_custom folder with all dependencies

## **CURRENT ARCHITECTURE**

The push-to-kindle feature uses a Python-based implementation with the following components:

### **Frontend Components** ✅
- **BrowseSeries.vue**: Series-level push functionality
- **BrowseBook.vue**: Individual book push functionality

### **Backend Components** ✅
- **BookController.kt**: REST endpoint for single book push
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

## **NOT IMPLEMENTED**
- **MultiSelectBar.vue**: Push button for multiple selected books in the multi-select toolbar is not yet implemented
  - **Planned Implementation**: Add push-to-kindle button on the most left side of existing icons in MultiSelectBar.vue
  - **Icon**: Use same icon as the PUSH TO KINDLE button on BrowseSeries.vue (mdi-send)
  - **Functionality**: Should enable pushing multiple selected books to Kindle in a single operation

## **CURRENT IMPLEMENTATION STATUS**

### **✅ COMPLETED FEATURES**
1. **Individual Book Push**: BrowseBook.vue has functional push-to-kindle button
2. **Series Push**: BrowseSeries.vue has functional push-to-kindle button for entire series
3. **Python Processing**: Complete pipeline with KCC integration and SCP transfer
4. **Format Support**: Native handling of all image formats including AVIF/WEBP
5. **Smart Folder Organization**: Series-based folder creation for multiple files

### **🔄 NEXT PHASE**
- **Multi-Select Push**: Implementation needed for MultiSelectBar.vue to handle bulk book transfers
- **Push To Kindle Progress Page**: Add a page that display the log output from push_to_kindle.py. Put the page link to the sidebar as a subcatrgory of History, rename original History as Scan History and put it as subcatrgory too
- **Improve KCC edge removal** Extend the current page number removal to remove watermark and title on the edge. Example is provided in test_crop.


## **STATUS**: **PRODUCTION READY v2.0** ✅
Core functionality is complete and in production. Multi-select feature is planned for future enhancement.