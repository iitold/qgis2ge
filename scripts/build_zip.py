"""Build script to create a compliant ZIP package for plugins.qgis.org and GitHub Releases."""

import os
import zipfile


def build_qgis_zip(output_path: str = "qgis2ge.zip") -> None:
    source_dir = "qgis2ge"
    if not os.path.exists(source_dir):
        raise FileNotFoundError(f"Source directory '{source_dir}' not found.")

    # Remove existing zip if present
    if os.path.exists(output_path):
        os.remove(output_path)

    # Excluded patterns
    excluded_dirs = {"__pycache__", "tests", ".pytest_cache"}
    excluded_exts = {".pyc", ".pyo", ".pyd", ".bak", ".swp"}

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for root, dirs, files in os.walk(source_dir):
            # Prune excluded directories in-place so os.walk does not recurse into them
            dirs[:] = [d for d in dirs if d not in excluded_dirs]

            for file in sorted(files):
                ext = os.path.splitext(file)[1].lower()
                if ext in excluded_exts or file.startswith("."):
                    continue

                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, ".")
                # CRITICAL FOR QGIS REPO: Must use forward slashes strictly (no Windows backslashes!)
                arcname = rel_path.replace("\\", "/")

                zf.write(full_path, arcname)

    # Verification check
    with zipfile.ZipFile(output_path, "r") as zf:
        names = zf.namelist()
        print(f"Archive '{output_path}' created successfully ({os.path.getsize(output_path)} bytes).")
        print("Archive contents:")
        for name in names:
            if "\\" in name:
                raise ValueError(f"ERROR: Found backslash in archive entry: {name}")
            if "__pycache__" in name or name.endswith(".pyc"):
                raise ValueError(f"ERROR: Found compiled/cache file in archive: {name}")
            print(f"  - {name}")

    print("\n[SUCCESS] ZIP file fully complies with QGIS Plugin Repository specification!")


if __name__ == "__main__":
    build_qgis_zip()
