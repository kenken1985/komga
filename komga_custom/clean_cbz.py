import zipfile
from pathlib import Path

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
