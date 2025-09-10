import os
import shutil
import zipfile
import logging
import rarfile

# You can configure the path to your UnRAR.exe if it's not in the system's PATH
# rarfile.UNRAR_TOOL = "path/to/your/UnRAR.exe"

def convert_single_cbr_to_cbz(cbr_file_path):
    """
    Converts a single .cbr file to a .cbz file.

    Upon successful conversion, the original .cbr file is deleted.
    The function handles its own logging for success or failure.

    Args:
        cbr_file_path (str): The full, absolute path to the .cbr file.

    Returns:
        str: The full path to the newly created .cbz file on success.
        None: On failure.
    """
    if not os.path.exists(cbr_file_path):
        logging.error(f"[Converter] File not found: {cbr_file_path}")
        return None

    folder_path = os.path.dirname(cbr_file_path)
    filename = os.path.basename(cbr_file_path)
    base_name = os.path.splitext(filename)[0]
    
    cbz_file_path = os.path.join(folder_path, f"{base_name}.cbz")
    temp_extract_dir = os.path.join(folder_path, f"__temp_{base_name}__")

    try:
        # 1. Extract the CBR (RAR) file to a temporary directory
        logging.info(f"[Converter] Extracting '{filename}'...")
        if os.path.exists(temp_extract_dir):
            shutil.rmtree(temp_extract_dir)
        os.makedirs(temp_extract_dir)

        with rarfile.RarFile(cbr_file_path) as rf:
            rf.extractall(path=temp_extract_dir)

        # 2. Create the CBZ (ZIP) archive from the extracted files
        logging.info(f"[Converter] Creating '{base_name}.cbz'...")
        with zipfile.ZipFile(cbz_file_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(temp_extract_dir):
                for file in files:
                    full_path = os.path.join(root, file)
                    archive_name = os.path.relpath(full_path, temp_extract_dir)
                    zf.write(full_path, arcname=archive_name)

        # 3. If successful, delete the original CBR file
        os.remove(cbr_file_path)
        logging.info(f"[Converter] Success! Original CBR '{filename}' deleted.")
        return cbz_file_path

    except rarfile.BadRarFile:
        logging.error(f"[Converter] '{filename}' is not a valid RAR file or is corrupted. Skipping.")
        return None
    except Exception as e:
        logging.error(f"[Converter] An error occurred while converting '{filename}': {e}")
        return None
    finally:
        # 4. Clean up the temporary directory regardless of success or failure
        if os.path.exists(temp_extract_dir):
            shutil.rmtree(temp_extract_dir)