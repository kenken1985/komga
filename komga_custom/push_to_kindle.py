import os
import sys
import tempfile
import zipfile
import rarfile
import subprocess
import io
import urllib.parse
from PIL import Image
from typing import List
import pillow_avif

# NOTE: You need to install the following python packages:
# pip install rarfile Pillow pillow-avif-plugin

# --- Kindle configuration from environment variables ---
KINDLE_IP = os.environ.get("KINDLE_IP", "192.168.29.55")
KINDLE_USER = os.environ.get("KINDLE_USER", "root") 
KINDLE_REMOTE_PATH = os.environ.get("KINDLE_REMOTE_PATH" ,"/mnt/us/book")
KINDLE_SSH_PASSWORD = os.environ.get("KINDLE_SSH_PASSWORD", "dummy")  # Empty for passwordless auth
KINDLE_SSH_PORT = os.environ.get("KINDLE_SSH_PORT", "2222")

# Validate required environment variables
if not KINDLE_IP:
    print("Warning: KINDLE_IP not set, using default value. Please set KINDLE_IP environment variable.")
if not KINDLE_USER:
    print("Warning: KINDLE_USER not set, using default value. Please set KINDLE_USER environment variable.")
if not KINDLE_REMOTE_PATH:
    print("Warning: KINDLE_REMOTE_PATH not set, using default value. Please set KINDLE_REMOTE_PATH environment variable.")
if not KINDLE_SSH_PASSWORD:
    print("Info: KINDLE_SSH_PASSWORD not set, using passwordless SSH authentication.")
else:
    print("Info: Using password-based SSH authentication.")

def decode_url_path(url_path: str) -> str:
    """
    Decode URL-encoded path to actual file system path.
    """
    try:
        # Decode URL-encoded characters
        decoded_path = urllib.parse.unquote(url_path)
        return decoded_path
    except Exception as e:
        print(f"Error decoding URL path {url_path}: {e}")
        return url_path

def get_files_list_from_webui() -> List[str]:
    """
    This function gets the file list from the command line arguments.
    The Komga backend will call this script with the file paths of the book/series.
    """
    if len(sys.argv) < 2:
        print("Usage: python push_to_kindle.py <file1> <file2> ...")
        sys.exit(1)
    
    # Decode URL-encoded paths
    decoded_paths = [decode_url_path(path) for path in sys.argv[1:]]
    return decoded_paths

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


def extract_series_name_from_path(file_path: str) -> str:
    """
    Extract series name from file path by looking for directory structure.
    Assumes structure: /path/to/library/SeriesName/VolumeName/file.cbz
    """
    try:
        # Check if the path has the expected structure
        if not file_path:
            return None
            
        # Normalize the path
        normalized_path = os.path.normpath(file_path)
        
        # Split the path
        parts = normalized_path.split(os.sep)
        
        # Check if we have at least 2 parts (series folder and file)
        if len(parts) < 2:
            return None
            
        # Get the directory containing the file (second to last part)
        series_name = parts[-2]
        
        # Check if series name is empty or just dots
        if not series_name or series_name == '.' or series_name == '..':
            return None
        
        # Clean up series name for Kindle folder
        # Remove special characters, limit length
        clean_name = ''.join(c for c in series_name if c.isalnum() or c in ' -_').strip()
        return clean_name[:50] if clean_name else None  # Limit to 50 characters
    except Exception:
        return None

def push_to_kindle(file_path: str, target_folder: str = None):
    """
    Pushes a file to Kindle using scp with configurable authentication and folder organization.
    """
    print(f"--- Debug: Pushing to Kindle ---")
    print(f"File path: {file_path}")
    print(f"Target folder: {target_folder}")

    try:
        filename = os.path.basename(file_path)
        
        # Determine remote path based on target folder
        if target_folder and target_folder.strip():
            remote_path = f"{KINDLE_USER}@{KINDLE_IP}:{KINDLE_REMOTE_PATH}/{target_folder}"
        else:
            remote_path = f"{KINDLE_USER}@{KINDLE_IP}:{KINDLE_REMOTE_PATH}/New Volume"
        
        # Build the scp command based on authentication method
        if KINDLE_SSH_PASSWORD:
            # Password-based authentication
            command = [
                "sshpass",
                "-p", KINDLE_SSH_PASSWORD,
                "scp",
                "-P", KINDLE_SSH_PORT,
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                file_path,
                remote_path
            ]
        else:
            # Passwordless authentication (using SSH keys)
            command = [
                "scp",
                "-P", KINDLE_SSH_PORT,
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                file_path,
                remote_path
            ]
        
        print(f"Executing command: {' '.join(command)}")
        
        result = subprocess.run(command, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            folder_display = target_folder if target_folder else "New Volume"
            print(f"Successfully uploaded {filename} to Kindle folder: {folder_display}")
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


def create_remote_folder(folder_name: str):
    """
    Create folder on Kindle device using ssh.
    """
    print(f"Creating folder on Kindle: {folder_name}")
    
    try:
        remote_path = f"{KINDLE_USER}@{KINDLE_IP}:{KINDLE_REMOTE_PATH}/{folder_name}"
        
        # Build the ssh command to create directory
        if KINDLE_SSH_PASSWORD:
            # Password-based authentication
            command = [
                "sshpass",
                "-p", KINDLE_SSH_PASSWORD,
                "ssh",
                "-p", KINDLE_SSH_PORT,
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                f"{KINDLE_USER}@{KINDLE_IP}",
                f"mkdir -p {KINDLE_REMOTE_PATH}/{folder_name}"
            ]
        else:
            # Passwordless authentication (using SSH keys)
            command = [
                "ssh",
                "-p", KINDLE_SSH_PORT,
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                f"{KINDLE_USER}@{KINDLE_IP}",
                f"mkdir -p {KINDLE_REMOTE_PATH}/{folder_name}"
            ]
        
        print(f"Executing command: {' '.join(command)}")
        
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print(f"Successfully created folder: {folder_name}")
            if result.stdout.strip():
                print(f"Stdout: {result.stdout}")
        else:
            print(f"Error creating folder on Kindle.")
            print(f"Return code: {result.returncode}")
            if result.stderr:
                print(f"Stderr: {result.stderr}")
            if result.stdout:
                print(f"Stdout: {result.stdout}")

    except subprocess.TimeoutExpired:
        print(f"SSH command timed out after 30 seconds")
    except Exception as e:
        print(f"An error occurred while creating folder: {e}")

def main():
    """
    Main function to process and push files to Kindle with folder organization.
    """
    file_paths = get_files_list_from_webui()
    print(f"Processing files: {file_paths}")

    # Determine target folder based on number of files
    target_folder = "New Volume"
    if len(file_paths) > 1:
        # For multiple files, try to extract series name from first file
        series_name = extract_series_name_from_path(file_paths[0])
        if series_name:
            target_folder = series_name
            print(f"Multiple files detected, using series folder: {target_folder}")
        else:
            print("Multiple files detected but couldn't determine series, using 'New Volume' folder")
    else:
        print("Single file detected, using 'New Volume' folder")

    # Create the target folder on Kindle
    create_remote_folder(target_folder)

    temp_dir = '/tmp'
    os.makedirs(temp_dir, exist_ok=True)

    for file_path in file_paths:
        # Step 1: Convert CBR to CBZ if needed
        processed_path = convert_cbr_to_cbz(file_path, temp_dir)
        
        # Step 2: Convert images to JPG if needed
        processed_path = convert_images_to_jpg(processed_path, temp_dir)

        # Step 3: Push the final file to Kindle with folder organization
        push_to_kindle(processed_path, target_folder)

if __name__ == "__main__":
    main()
