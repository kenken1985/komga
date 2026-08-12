import os
import sys
import shutil
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def move_to_import(book_path: str, current_library_name: str, target_dir: str) -> bool:
    logger.info(f"Checking move for book at '{book_path}', current library: '{current_library_name}'")

    src_file = os.path.abspath(book_path)
    if not os.path.exists(src_file):
        msg = f"Error: Source book path '{src_file}' does not exist."
        logger.error(msg)
        print(msg)
        return False

    if not os.path.isfile(src_file):
        msg = f"Error: Source path '{src_file}' is not a file."
        logger.error(msg)
        print(msg)
        return False

    os.makedirs(target_dir, exist_ok=True)
    dest_file = os.path.join(target_dir, os.path.basename(src_file))

    logger.info(f"Source book file: {src_file}")
    logger.info(f"Target directory: {target_dir}")
    logger.info(f"Destination file: {dest_file}")

    if os.path.exists(dest_file):
        logger.info(f"Target file '{dest_file}' already exists. Overwriting...")
        os.remove(dest_file)

    shutil.move(src_file, dest_file)

    msg = f"Successfully moved book '{os.path.basename(src_file)}' to '{target_dir}'."
    logger.info(msg)
    print(msg)
    return True

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python move_to_import.py <book_path> <current_library_name> <target_dir>")
        sys.exit(1)

    book_path = sys.argv[1]
    current_library_name = sys.argv[2]
    target_dir = sys.argv[3]

    success = move_to_import(book_path, current_library_name, target_dir)
    sys.exit(0 if success else 1)
