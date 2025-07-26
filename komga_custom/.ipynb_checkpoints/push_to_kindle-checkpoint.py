import os
import sys
import tempfile
import zipfile
import rarfile
import subprocess
import io
from PIL import Image
from typing import List
import pillow_avif

# NOTE: You need to install the following python packages:
# pip install rarfile Pillow pillow-avif-plugin

# --- Hardcoded configuration for Kindle ---
KINDLE_IP = "192.168.29.55" # CHANGE THIS
KINDLE_USER = "root" # CHANGE THIS
# The remote path on Kindle where to upload the files.
# It must exist. For example /mnt/us/documents/
KINDLE_REMOTE_PATH = "/mnt/us/book/" # CHANGE THIS

def get_files_list_from_webui() -> List[str]:
    """
    This function gets the file list from the command line arguments.
    The Komga backend will call this script with the file paths of the book/series.
    """
    if len(sys.argv) < 2:
        print("Usage: python push_to_kindle.py <file1> <file2> ...")
        sys.exit(1)
    return sys.argv[1:]

def convert_cbr_to_cbz(file_path: str, temp_dir: str) -> str:
    """
    Checks if a file is a .cbr file. If so, converts it to a .cbz file
    in a temporary directory.
    Returns the path to the (potentially converted) file.
    """
    if not file_path.lower().endswith('.cbr'):
        return file_path

    print(f"Converting CBR to CBZ: {file_path}")
    base_filename = os.path.splitext(os.path.basename(file_path))[0]
    cbz_path = os.path.join(temp_dir, f"{base_filename}.cbz")

    with rarfile.RarFile(file_path) as rf:
        with zipfile.ZipFile(cbz_path, 'w') as zf:
            for member in rf.infolist():
                if member.is_file():
                    zf.writestr(member.filename, rf.read(member))
    
    print(f"Converted to: {cbz_path}")
    return cbz_path

def convert_images_to_jpg(file_path: str, temp_dir: str) -> str:
    """
    Checks the images within a .cbz file. If any are not JPG/JPEG,
    it converts them to JPG and creates a new .cbz file.
    """
    if not file_path.lower().endswith('.cbz'):
        return file_path

    print(f"Checking images in: {file_path}")
    needs_conversion = False
    with zipfile.ZipFile(file_path, 'r') as zf:
        for member in zf.infolist():
            if not member.is_dir() and member.filename.lower().endswith(('.webp', '.avif', '.png', '.gif', '.bmp')):
                needs_conversion = True
                break
    
    if not needs_conversion:
        print("No image conversion needed.")
        return file_path

    print("Image conversion needed. Converting to JPG...")
    base_filename = os.path.splitext(os.path.basename(file_path))[0]
    new_cbz_path = os.path.join(temp_dir, f"{base_filename}_converted.cbz")

    with zipfile.ZipFile(new_cbz_path, 'w') as new_zf:
        with zipfile.ZipFile(file_path, 'r') as old_zf:
            for member in old_zf.infolist():
                if not member.is_dir():
                    filename = member.filename
                    new_filename = os.path.splitext(filename)[0] + '.jpg'
                    img_bytes = old_zf.read(member)
                    
                    if not filename.lower().endswith(('.jpg', '.jpeg')):
                        try:
                            with Image.open(io.BytesIO(img_bytes)) as img:
                                if img.mode == 'RGBA':
                                    img = img.convert('RGB')
                                
                                with io.BytesIO() as output:
                                    img.save(output, format='JPEG')
                                    img_bytes = output.getvalue()
                        except Exception as e:
                            print(f"Could not convert {filename}: {e}")

                    new_zf.writestr(new_filename, img_bytes)

    print(f"Converted images and saved to: {new_cbz_path}")
    return new_cbz_path


def push_to_kindle(file_path: str):
    """
    Pushes a single file to Kindle using scp with no password authentication.
    """
    print(f"--- Debug: Pushing to Kindle ---")
    print(f"File path: {file_path}")

    try:
        filename = os.path.basename(file_path)
        remote_path = f"{KINDLE_USER}@{KINDLE_IP}:{KINDLE_REMOTE_PATH}"
        
        # Using SSH settings for Kindle connection
        # Allow password authentication with empty password (dummy pass)
        # StrictHostKeyChecking=no and UserKnownHostsFile=/dev/null to prevent host key verification
        # Port=2222 specifies the SSH port for Kindle
        command = [
            "sshpass",
            "-p", "",
            "scp",
            "-P", "2222",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            file_path,
            remote_path
        ]
        
        print(f"Executing command: {' '.join(command)}")
        
        result = subprocess.run(command, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"Successfully uploaded {filename} to Kindle.")
            if result.stdout.strip():
                print(f"Stdout: {result.stdout}")
        else:
            print(f"Error uploading file to Kindle.")
            print(f"Return code: {result.returncode}")
            if result.stderr:
                print(f"Stderr: {result.stderr}")
            if result.stdout:
                print(f"Stdout: {result.stdout}")

    except subprocess.TimeoutExpired:
        print(f"Upload timed out after 300 seconds")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print(f"--- End Debug ---")


def main():
    """
    Main function to process and push files to Kindle.
    """
    file_paths = get_files_list_from_webui()
    print(f"Processing files: {file_paths}")

    temp_dir = os.path.join(os.path.dirname(__file__), 'tmp')
    os.makedirs(temp_dir, exist_ok=True)

    for file_path in file_paths:
        # Step 1: Convert CBR to CBZ if needed
        processed_path = convert_cbr_to_cbz(file_path, temp_dir)
        
        # Step 2: Convert images to JPG if needed
        processed_path = convert_images_to_jpg(processed_path, temp_dir)

        # Step 3: Push the final file to Kindle
        push_to_kindle(processed_path)

if __name__ == "__main__":
    main()
