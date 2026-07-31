import os
import sys
import shutil
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

EXCLUDED_LIBRARIES = {"ライトノベル", "漫画", "小説家になろう"}
TARGET_LIBRARY_NAME = "ライトノベル"

def move_directory_contents(src_dir: str, dst_dir: str):
    """
    Recursively move all files and subdirectories from src_dir to dst_dir.
    """
    os.makedirs(dst_dir, exist_ok=True)
    for item in os.listdir(src_dir):
        s_item = os.path.join(src_dir, item)
        d_item = os.path.join(dst_dir, item)
        if os.path.isdir(s_item):
            if os.path.exists(d_item):
                move_directory_contents(s_item, d_item)
                if os.path.exists(s_item) and not os.listdir(s_item):
                    os.rmdir(s_item)
            else:
                shutil.move(s_item, d_item)
        else:
            if os.path.exists(d_item):
                os.remove(d_item)
            shutil.move(s_item, d_item)

def clean_series_folder_name(name: str) -> str:
    if name.endswith(")") or name.endswith("）"):
        idx = -1
        for i, ch in enumerate(name):
            if ch == "(" or ch == "（":
                idx = i
        if idx != -1:
            return name[:idx].rstrip()
        return name[:-1].rstrip()
    return name

def move_to_light_novel(series_path: str, current_library_name: str, target_library_root: str) -> bool:
    """
    Move series folder or files from current location to Light Novel library.
    
    Checks if current library is excluded (ライトノベル, 漫画, 小説家になろう).
    If target series folder already exists in Light Novel library, moves all files into it.
    Otherwise, moves the whole series folder.
    """
    logger.info(f"Checking move for series at '{series_path}', current library: '{current_library_name}'")
    
    if current_library_name in EXCLUDED_LIBRARIES:
        msg = f"Skipped: Current library '{current_library_name}' is in excluded list ({', '.join(sorted(EXCLUDED_LIBRARIES))})"
        logger.warning(msg)
        print(msg)
        return False
        
    src_dir = os.path.abspath(series_path)
    if not os.path.exists(src_dir):
        msg = f"Error: Source series path '{src_dir}' does not exist."
        logger.error(msg)
        print(msg)
        return False
        
    series_folder_name = os.path.basename(src_dir)
    cleaned_name = clean_series_folder_name(series_folder_name)
    target_dir = os.path.abspath(target_library_root)
    target_series_dir = os.path.join(target_dir, cleaned_name)
    
    logger.info(f"Source series folder: {src_dir}")
    logger.info(f"Target library root: {target_dir}")
    logger.info(f"Target series folder: {target_series_dir}")
    
    if os.path.exists(target_series_dir):
        logger.info(f"Target folder '{target_series_dir}' already exists. Moving contents inside...")
        move_directory_contents(src_dir, target_series_dir)
        if os.path.exists(src_dir) and not os.listdir(src_dir):
            os.rmdir(src_dir)
            logger.info(f"Removed empty source folder '{src_dir}'.")
    else:
        logger.info(f"Target folder does not exist. Moving entire series folder '{src_dir}' to '{target_series_dir}'...")
        os.makedirs(target_dir, exist_ok=True)
        shutil.move(src_dir, target_series_dir)

    msg = f"Successfully moved series '{cleaned_name}' to '{TARGET_LIBRARY_NAME}' library."
    logger.info(msg)
    print(msg)
    return True

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python move_to_light_novel.py <series_path> <current_library_name> <target_library_root>")
        sys.exit(1)
        
    series_path = sys.argv[1]
    current_library_name = sys.argv[2]
    target_library_root = sys.argv[3]
    
    success = move_to_light_novel(series_path, current_library_name, target_library_root)
    sys.exit(0 if success else 1)
