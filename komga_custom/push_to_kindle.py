import os
import sys
import tempfile
import zipfile
import subprocess
import io
import urllib.parse
from PIL import Image
from typing import List
from pathlib import Path

# NOTE: You need to install the following python packages:
# pip install Pillow

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
    print("[push_to_kindle] Received command to push file to Kindle.", flush=True)
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except Exception:
        pass
    print(f"--- Debug: Pushing to Kindle ---")
    print(f"File path: {file_path}")
    print(f"Target folder: {target_folder}")

    try:
        filename = os.path.basename(file_path)
        
        # Determine remote path based on target folder
        if target_folder and target_folder.strip():
            remote_path = f"{KINDLE_USER}@{KINDLE_IP}:{KINDLE_REMOTE_PATH}/{target_folder}"
        else:
            remote_path = f"{KINDLE_USER}@{KINDLE_IP}:{KINDLE_REMOTE_PATH}/New_Volume"
        
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
            folder_display = target_folder if target_folder else "New_Volume"
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
        # Remove the temporary file after upload if it exists and is in /tmp
        try:
            if file_path.startswith("/tmp/") and os.path.exists(file_path):
                os.remove(file_path)
                print(f"Removed temporary file: {file_path}")
        except Exception as cleanup_err:
            print(f"Warning: Failed to remove temporary file {file_path}: {cleanup_err}")


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

def process_with_kcc(book_path: str, output_path: str) -> bool:
    """
    Process a comic file using Kindle Comic Converter (KCC).
    
    Args:
        book_path: Path to the comic file (CBZ/CBR)
        output_path: Directory where processed file should be saved
        
    Returns:
        bool: True if processing succeeded, False otherwise
    """
    kcc_script_dir = os.path.dirname(os.path.abspath(__file__))
    kcc_script = os.path.join(kcc_script_dir, "kcc-c2e.py")
    
    if not os.path.exists(kcc_script):
        print(f"Error: KCC script not found at {kcc_script}")
        # Fallback for Docker environment
        kcc_script = "/app/komga_custom/kcc-c2e.py"
        if not os.path.exists(kcc_script):
            print(f"Error: KCC script not found at {kcc_script} either.")
            return False
    
    # Get base filename without extension
    base_filename = os.path.splitext(os.path.basename(book_path))[0]
    # Create full output path with specific filename
    output_file_path = os.path.join(output_path, f"{base_filename}_kcc.cbz")
    
    print(f"Processing with KCC: {book_path}")
    print(f"Output file: {output_file_path}")
    
    cleaned_cbz_path = None
    try:
        # Add PYTHONPATH to include the directory containing kindlecomicconverter module
        env = os.environ.copy()
        env['PYTHONPATH'] = os.path.dirname(kcc_script)
        command = [
            "python3",
            "-c",
            f"import sys; sys.path.insert(0, '{os.path.dirname(kcc_script)}'); exec(open('{kcc_script}').read())",
            "-p", "KPW5",
            "-q",
            "-u",
            "-m",
            "--cp", "2",
            "--mozjpeg",
            "-f", "CBZ",
            "-o", output_file_path,
            book_path
        ]
        print(f"Executing KCC command with PYTHONPATH={env['PYTHONPATH']}")
        print(f"Command: {' '.join(command)}")
        result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=600)
        if result.returncode == 0:
            print("KCC processing completed successfully")
            if result.stdout.strip():
                print(f"KCC stdout: {result.stdout}")
            return True, cleaned_cbz_path
        else:
            print("Error during KCC processing")
            print(f"Return code: {result.returncode}")
            if result.stderr:
                print(f"KCC stderr: {result.stderr}")
            if result.stdout:
                print(f"KCC stdout: {result.stdout}")
            # Check for extraction error in KCC output
            if "Failed to extract archive" in result.stdout or "Failed to extract archive" in result.stderr:
                print("Detected extraction error. Attempting to clean the CBZ and retry...")
                cleaned_cbz_path = clean_cbz(book_path)
                if cleaned_cbz_path and os.path.exists(cleaned_cbz_path):
                    print(f"Retrying KCC with cleaned CBZ: {cleaned_cbz_path}")
                    # Retry KCC with the cleaned CBZ
                    command[-1] = cleaned_cbz_path  # Update the book path in the command
                    result2 = subprocess.run(command, capture_output=True, text=True, timeout=600)
                    if result2.returncode == 0:
                        print("KCC processing completed successfully after cleaning")
                        if result2.stdout.strip():
                            print(f"KCC stdout: {result2.stdout}")
                        return True, cleaned_cbz_path
                    else:
                        print("KCC still failed after cleaning.")
                        if result2.stderr:
                            print(f"KCC stderr: {result2.stderr}")
                        if result2.stdout:
                            print(f"KCC stdout: {result2.stdout}")
                        return False, cleaned_cbz_path
                else:
                    print("CBZ cleaning failed.")
                    return False, cleaned_cbz_path
            return False, cleaned_cbz_path
    except subprocess.TimeoutExpired:
        print("KCC processing timed out after 600 seconds")
        return False, cleaned_cbz_path
    except Exception as e:
        print(f"Exception during KCC processing: {e}")
        return False, cleaned_cbz_path

def clean_cbz(file_path: str) -> str:
    """
    Cleans a CBZ file by removing directories and __MACOSX files, and flattening the structure.
    Returns the path to the cleaned file, or None if cleaning fails.
    """
    try:
        file_path = Path(file_path)
        tmp_dir = Path('/tmp')
        cleaned_cbz_path = tmp_dir / f"{file_path.stem}_cleaned.cbz"
        with zipfile.ZipFile(file_path, 'r') as z_in:
            with zipfile.ZipFile(cleaned_cbz_path, 'w') as z_out:
                for item in z_in.infolist():
                    if item.is_dir() or item.filename.startswith('__MACOSX/'):
                        continue
                    # Write file to the root of the archive
                    z_out.writestr(Path(item.filename).name, z_in.read(item.filename))
        print(f"Cleaned CBZ created at: {cleaned_cbz_path}")
        return str(cleaned_cbz_path)
    except Exception as e:
        print(f"Failed to clean CBZ: {e}")
        return None

def main():
    """
    Main function to process and push files to Kindle with folder organization.
    """
    file_paths = get_files_list_from_webui()
    print(f"Processing files: {file_paths}")

    # Determine target folder based on number of files
    target_folder = "New_Volume"
    if len(file_paths) > 1:
        # For multiple files, try to extract series name from first file
        series_name = extract_series_name_from_path(file_paths[0])
        if series_name:
            target_folder = series_name
            print(f"Multiple files detected, using series folder: {target_folder}")
        else:
            print("Multiple files detected but couldn't determine series, using 'New_Volume' folder")
    else:
        print("Single file detected, using 'New_Volume' folder")

    # Create the target folder on Kindle
    create_remote_folder(target_folder)

    temp_dir = '/tmp'
    os.makedirs(temp_dir, exist_ok=True)

    for file_path in file_paths:
        print(f"--- Processing file: {file_path} ---")
        kcc_output_dir = temp_dir

        kcc_success, cleaned_cbz_path = process_with_kcc(file_path, kcc_output_dir)
        base_filename = os.path.splitext(os.path.basename(file_path))[0]
        kcc_output_file = os.path.join(kcc_output_dir, f"{base_filename}_kcc.cbz")

        if kcc_success:
            if os.path.exists(kcc_output_file):
                print(f"KCC processing successful. Pushing file to Kindle.")
                push_to_kindle(kcc_output_file, target_folder)
            else:
                print(f"Error: KCC reported success, but output file '{kcc_output_file}' not found.")
        else:
            print(f"KCC processing failed for {file_path}. The file will not be pushed to Kindle.")

        # Remove cleaned CBZ if it was created
        if cleaned_cbz_path and os.path.exists(cleaned_cbz_path):
            try:
                os.remove(cleaned_cbz_path)
                print(f"Removed cleaned CBZ: {cleaned_cbz_path}")
            except Exception as cleanup_err:
                print(f"Warning: Failed to remove cleaned CBZ {cleaned_cbz_path}: {cleanup_err}")

        print(f"--- Finished processing file: {file_path} ---")


if __name__ == "__main__":
    main()
