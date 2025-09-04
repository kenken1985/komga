import os
import zipfile
from pathlib import Path

def clean_cbz(file_path):
    file_path = Path(file_path)
    temp_path = file_path.parent / f"{file_path.stem}_cleaned.cbz"
    with zipfile.ZipFile(file_path, 'r') as z_in:
        with zipfile.ZipFile(temp_path, 'w') as z_out:
            for item in z_in.infolist():
                if item.is_dir():
                    continue
                # Exclude macOS-specific metadata files
                if item.filename.startswith('__MACOSX/'):
                    continue
                # Write file to the root of the archive
                z_out.writestr(Path(item.filename).name, z_in.read(item.filename))
    return temp_path

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <file.cbz>")
        sys.exit(1)
    cleaned_file = clean_cbz(sys.argv[1])
    print(f"Cleaned file saved as: {cleaned_file}")
