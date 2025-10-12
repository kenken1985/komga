import zipfile
from pathlib import Path
import cv2
import numpy as np
import pytesseract
import tempfile
import os

def is_mono_color_background(image, x, y, w, h, threshold=50):
    """
    Check if a region has a mono-color or near mono-color background.
    
    Args:
        image: OpenCV image array (BGR)
        x, y, w, h: Region coordinates
        threshold: Maximum standard deviation for considering it mono-color
        
    Returns:
        Boolean indicating if the region has a mono-color background
    """
    # Extract the region
    region = image[y:y+h, x:x+w]
    
    if region.size == 0:
        return False
    
    # Convert to grayscale for luminance analysis
    region_gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    
    # Check standard deviation in grayscale (main indicator)
    gray_std = np.std(region_gray)
    gray_mean = np.mean(region_gray)
    
    # More lenient criteria for watermark removal:
    # 1. Light backgrounds (typical for watermarks)
    is_light_bg = gray_mean > 180 and gray_std < threshold
    
    # 2. Dark backgrounds  
    is_dark_bg = gray_mean < 100 and gray_std < threshold
    
    # 3. Any reasonably uniform background
    is_uniform = gray_std < threshold * 0.7  # 35 for default threshold of 50
    
    # Be lenient - if any criteria match, consider it mono-color
    is_mono = is_light_bg or is_dark_bg or is_uniform
    
    # Background check debug info removed for production
    # print(f"  Background check - Gray std: {gray_std:.1f}, mean: {gray_mean:.1f} -> {'Mono' if is_mono else 'Complex'}")
    
    return is_mono

def detect_and_remove_watermark(image, watermark_texts=['RawLazy.Com', 'DL-Raw.Se']):
    """
    Detect and remove watermarks from an image using Tesseract OCR and cv2.inpaint().
    
    Args:
        image: OpenCV image array
        watermark_texts: List of watermark texts to look for
        
    Returns:
        Cleaned image with watermarks removed
    """
    h, w = image.shape[:2]
    
    # Create a copy for processing
    result_image = image.copy()
    
    # Convert to grayscale for OCR
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Create mask for inpainting
    mask = np.zeros(gray.shape, dtype=np.uint8)
    found_watermarks = []  # Track found watermarks to avoid duplicates
    
    # Strategy 1: Use full image OCR with detailed data
    try:
        data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
        for i, text in enumerate(data['text']):
            if any(watermark.lower() in text.lower() for watermark in watermark_texts):
                # Get bounding box coordinates
                x = data['left'][i]
                y = data['top'][i]
                w_box = data['width'][i]
                h_box = data['height'][i]
                
                # Check if this watermark overlaps with already found ones
                overlaps = False
                for found_x, found_y, found_w, found_h in found_watermarks:
                    if (abs(x - found_x) < 50 and abs(y - found_y) < 50):
                        overlaps = True
                        break
                
                if not overlaps:
                    # Expand the bounding box slightly to ensure complete removal
                    padding = 5
                    x = max(0, x - padding)
                    y = max(0, y - padding)
                    w_box = min(w - x, w_box + 2 * padding)
                    h_box = min(h - y, h_box + 2 * padding)
                    
                    # print(f"Found watermark '{text}' at ({x}, {y}, {w_box}, {h_box})")
                    cv2.rectangle(mask, (x, y), (x + w_box, y + h_box), 255, -1)
                    found_watermarks.append((x, y, w_box, h_box))
    except Exception as e:
        pass  # Full image OCR failed silently
    
    # Strategy 2: Check known watermark regions specifically for RawLazy.Com
    # Only check top region if we haven't found RawLazy watermark yet
    if not any('rawlazy' in str(found).lower() for found in found_watermarks):
        # Use a smaller, more targeted search region for top watermarks
        search_regions = [
            (90, 0, 220, 60),   # Top area where RawLazy typically appears
        ]
        
        for search_x, search_y, search_w, search_h in search_regions:
            search_x = max(0, search_x)
            search_y = max(0, search_y)
            search_w = min(w - search_x, search_w)
            search_h = min(h - search_y, search_h)
            
            if search_w > 0 and search_h > 0:
                search_region = gray[search_y:search_y+search_h, search_x:search_x+search_w]
                if search_region.size > 0:
                    try:
                        # Use OCR to get precise coordinates within the search region
                        region_data = pytesseract.image_to_data(search_region, output_type=pytesseract.Output.DICT)
                        for i, text in enumerate(region_data['text']):
                            if any(watermark.lower() in text.lower() for watermark in ['RawLazy.Com', 'rawlazy']):
                                # Get precise coordinates from OCR
                                rel_x = region_data['left'][i]
                                rel_y = region_data['top'][i]
                                text_w = region_data['width'][i]
                                text_h = region_data['height'][i]
                                
                                # Convert to full image coordinates
                                abs_x = search_x + rel_x
                                abs_y = search_y + rel_y
                                
                                # print(f"Found top watermark '{text}' at precise location ({abs_x}, {abs_y}, {text_w}, {text_h})")
                                # Add minimal padding around just the text
                                padding = 3
                                mask_x = max(0, abs_x - padding)
                                mask_y = max(0, abs_y - padding)
                                mask_w = min(w - mask_x, text_w + 2 * padding)
                                mask_h = min(h - mask_y, text_h + 2 * padding)
                                cv2.rectangle(mask, (mask_x, mask_y), (mask_x + mask_w, mask_y + mask_h), 255, -1)
                                found_watermarks.append((mask_x, mask_y, mask_w, mask_h))
                                break
                    except Exception as e:
                        continue
    
    # Strategy 3: Bottom region for DL-Raw.Se (only if not found yet)
    if not any('dl-raw' in str(found).lower() for found in found_watermarks):
        # Use a smaller, more targeted search region for bottom watermarks
        search_regions = [
            (800, h-80, 250, 70),  # Bottom-right area where DL-Raw typically appears
        ]
        
        for search_x, search_y, search_w, search_h in search_regions:
            search_x = max(0, search_x)
            search_y = max(0, search_y)
            search_w = min(w - search_x, search_w)
            search_h = min(h - search_y, search_h)
            
            if search_w > 0 and search_h > 0:
                search_region = gray[search_y:search_y+search_h, search_x:search_x+search_w]
                if search_region.size > 0:
                    try:
                        # Use OCR to get precise coordinates within the search region
                        region_data = pytesseract.image_to_data(search_region, output_type=pytesseract.Output.DICT)
                        for i, text in enumerate(region_data['text']):
                            if any(watermark.lower() in text.lower() for watermark in ['DL-Raw.Se', 'dl-raw']):
                                # Get precise coordinates from OCR
                                rel_x = region_data['left'][i]
                                rel_y = region_data['top'][i]
                                text_w = region_data['width'][i]
                                text_h = region_data['height'][i]
                                
                                # Convert to full image coordinates
                                abs_x = search_x + rel_x
                                abs_y = search_y + rel_y
                                
                                # print(f"Found bottom watermark '{text}' at precise location ({abs_x}, {abs_y}, {text_w}, {text_h})")
                                # Add minimal padding around just the text
                                padding = 3
                                mask_x = max(0, abs_x - padding)
                                mask_y = max(0, abs_y - padding)
                                mask_w = min(w - mask_x, text_w + 2 * padding)
                                mask_h = min(h - mask_y, text_h + 2 * padding)
                                cv2.rectangle(mask, (mask_x, mask_y), (mask_x + mask_w, mask_y + mask_h), 255, -1)
                                found_watermarks.append((mask_x, mask_y, mask_w, mask_h))
                                break
                    except Exception as e:
                        continue
                    except Exception as e:
                        continue
    
    # Apply inpainting if any watermarks were found
    if np.any(mask):
        # print("Applying inpainting to remove watermarks...")
        result_image = cv2.inpaint(result_image, mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
    else:
        pass  # No watermarks detected
    
    return result_image

def process_image_for_watermarks(image_data):
    """
    Process image data to remove watermarks.
    
    Args:
        image_data: Raw image bytes
        
    Returns:
        Processed image bytes with watermarks removed
    """
    # Convert bytes to numpy array
    nparr = np.frombuffer(image_data, np.uint8)
    
    # Decode image
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        print("Failed to decode image")
        return image_data
    
    # Remove watermarks
    cleaned_img = detect_and_remove_watermark(img)
    
    # Encode back to bytes
    _, buffer = cv2.imencode('.jpg', cleaned_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
    
    return buffer.tobytes()

def clean_cbz(file_path: str, remove_watermarks: bool = True) -> str:
    """
    Cleans a CBZ file by removing directories and __MACOSX files, flattening the structure,
    and optionally removing watermarks from images.
    Returns the path to the cleaned file, or None if cleaning fails.
    """
    try:
        file_path = Path(file_path)
        tmp_dir = Path('/tmp')
        cleaned_cbz_path = tmp_dir / f"{file_path.stem}_cleaned.cbz"
        
        print(f"Processing CBZ file: {file_path}")
        if remove_watermarks:
            print("Watermark removal enabled")
        
        with zipfile.ZipFile(file_path, 'r') as z_in:
            with zipfile.ZipFile(cleaned_cbz_path, 'w') as z_out:
                for item in z_in.infolist():
                    if item.is_dir() or item.filename.startswith('__MACOSX/'):
                        continue
                    
                    # Read the file data
                    file_data = z_in.read(item.filename)
                    filename = Path(item.filename).name
                    
                    # Check if it's an image file and watermark removal is enabled
                    if remove_watermarks and filename.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff')):
                        # print(f"Processing image: {filename}")
                        try:
                            # Process the image to remove watermarks
                            processed_data = process_image_for_watermarks(file_data)
                            z_out.writestr(filename.replace('_', '+'), processed_data)
                        except Exception as e:
                            print(f"Failed to process image {filename}: {e}")
                            # Fall back to original image if processing fails
                            z_out.writestr(filename.replace('_', '+'), file_data)
                    else:
                        # Write file as-is
                        z_out.writestr(filename.replace('_', '+'), file_data)
        
        print(f"Cleaned CBZ created at: {cleaned_cbz_path}")
        return str(cleaned_cbz_path)
    except Exception as e:
        print(f"Failed to clean CBZ: {e}")
        return None

def test_watermark_removal(image_path: str):
    """
    Test watermark removal on a single image file.
    """
    try:
        print(f"Testing watermark removal on: {image_path}")
        
        # Load the image
        img = cv2.imread(image_path)
        if img is None:
            print("Failed to load image")
            return
        
        print(f"Original image shape: {img.shape}")
        
        # Remove watermarks
        cleaned_img = detect_and_remove_watermark(img)
        
        # Save the result
        output_path = f"{Path(image_path).stem}_no_watermark.jpg"
        cv2.imwrite(output_path, cleaned_img)
        print(f"Cleaned image saved as: {output_path}")
        
    except Exception as e:
        print(f"Error testing watermark removal: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "test_image" and len(sys.argv) > 2:
            test_watermark_removal(sys.argv[2])
        elif sys.argv[1] == "clean_cbz" and len(sys.argv) > 2:
            # Check for optional --no-watermark-removal flag
            remove_watermarks = True
            file_path = sys.argv[2]
            if len(sys.argv) > 3 and sys.argv[3] == "--no-watermark-removal":
                remove_watermarks = False
                print("Watermark removal disabled")
            
            result = clean_cbz(file_path, remove_watermarks=remove_watermarks)
            if result:
                print(f"Success: {result}")
            else:
                print("Failed to clean CBZ")
        else:
            print("Usage:")
            print("  python clean_cbz.py test_image <image_path>")
            print("  python clean_cbz.py clean_cbz <cbz_path> [--no-watermark-removal]")
    else:
        # Default test with available test files
        print("Testing with default files...")
        if Path("test_image.jpg").exists():
            test_watermark_removal("test_image.jpg")
        if Path("test_book.cbz").exists():
            result = clean_cbz("test_book.cbz")
            if result:
                print(f"CBZ cleaning result: {result}")
        else:
            print("No test files found. Usage:")
            print("  python clean_cbz.py test_image <image_path>")
            print("  python clean_cbz.py clean_cbz <cbz_path> [--no-watermark-removal]")
