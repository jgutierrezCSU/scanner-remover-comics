import os
import io
import sys
import zipfile
import logging
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk # Added ttk for Notebook

import xml.etree.ElementTree as ET
from PIL import Image
import numpy as np
from skimage.metrics import structural_similarity as ssim

# --- NEW: Import the conversion logic from our separate file ---
import converter_logic

# --- Core Image and Comic Processing Functions (Largely Unchanged) ---

def compare_images_in_memory(image_bytes_1, image_bytes_2):
    try:
        image1 = Image.open(io.BytesIO(image_bytes_1)).convert('L')
        image2 = Image.open(io.BytesIO(image_bytes_2)).convert('L')
        if image1.size != image2.size:
            image2 = image2.resize(image1.size)
        img1_array = np.array(image1)
        img2_array = np.array(image2)
        similarity_index, _ = ssim(img1_array, img2_array, full=True)
        return similarity_index
    except Exception as e:
        logging.error(f"Failed to compare images in memory: {e}")
        return 0.0

def find_pages_to_remove(cbz_path, target_image_data, options):
    pages_to_remove = []
    try:
        with zipfile.ZipFile(cbz_path, 'r') as archive:
            image_files = sorted([
                f for f in archive.namelist()
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))
            ])
            if not image_files:
                logging.warning(f"No image files found in {os.path.basename(cbz_path)}")
                return [], 0
            
            total_page_count = len(image_files)
            pages_to_check_set = set()
            if "all" in options:
                pages_to_check_set.update(image_files)
            else:
                if "first" in options: pages_to_check_set.add(image_files[0])
                if "last_2" in options:
                    if len(image_files) >= 2:
                        pages_to_check_set.update(image_files[-2:])
                    elif image_files:
                        pages_to_check_set.add(image_files[-1])
                elif "last" in options:
                    pages_to_check_set.add(image_files[-1])

            for page_filename in pages_to_check_set:
                comic_page_data = archive.read(page_filename)
                for target_data in target_image_data:
                    similarity = compare_images_in_memory(comic_page_data, target_data)
                    if similarity >= 0.7:
                        logging.info(f"MATCH FOUND: '{page_filename}' (Similarity: {similarity:.2f}).")
                        pages_to_remove.append(page_filename)
                        break
        return pages_to_remove, total_page_count
    except zipfile.BadZipFile:
        logging.error(f"Could not open {os.path.basename(cbz_path)}: Bad ZIP file.")
        return [], 0
    except Exception as e:
        logging.error(f"Error scanning {os.path.basename(cbz_path)}: {e}")
        return [], 0

def update_comic_info(comic_info_bytes, pages_removed_count, original_page_count):
    tree = ET.ElementTree(ET.fromstring(comic_info_bytes))
    root = tree.getroot()
    page_count_elem = root.find('.//PageCount')
    if page_count_elem is None:
        page_count_elem = ET.SubElement(root, 'PageCount')
    new_page_count = original_page_count - pages_removed_count
    page_count_elem.text = str(new_page_count)
    logging.info(f"Updating page count from {original_page_count} to {new_page_count}.")
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)

def rebuild_cbz_archive(cbz_path, files_to_remove, original_page_count):
    temp_cbz_path = cbz_path + '.tmp'
    try:
        with zipfile.ZipFile(cbz_path, 'r') as source_zip, \
             zipfile.ZipFile(temp_cbz_path, 'w', zipfile.ZIP_DEFLATED) as target_zip:

            original_image_files = sorted([f for f in source_zip.namelist() if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))])
            files_to_keep = [f for f in original_image_files if f not in files_to_remove]
            
            renumbering_needed = not (len(files_to_remove) == 1 and files_to_remove[0] == original_image_files[-1])

            try:
                comic_info_content = source_zip.read('ComicInfo.xml')
                updated_content = update_comic_info(comic_info_content, len(files_to_remove), original_page_count)
                target_zip.writestr('ComicInfo.xml', updated_content)
            except KeyError:
                logging.warning(f"No ComicInfo.xml in {os.path.basename(cbz_path)}. Cannot update page count.")
            
            if renumbering_needed:
                logging.info("Renumbering pages for sequential order...")
                for i, old_filename in enumerate(files_to_keep, 1):
                    _, extension = os.path.splitext(old_filename)
                    new_filename = f"{i:03d}{extension}"
                    target_zip.writestr(new_filename, source_zip.read(old_filename))
            else:
                logging.info("Copying remaining pages without renumbering...")
                for filename in files_to_keep:
                    target_zip.writestr(filename, source_zip.read(filename))

            for item in source_zip.infolist():
                if not item.filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', 'comicinfo.xml')):
                    target_zip.writestr(item, source_zip.read(item.filename))

        os.replace(temp_cbz_path, cbz_path)
        logging.info(f"Successfully rebuilt {os.path.basename(cbz_path)}.")
        return True
    except Exception as e:
        logging.error(f"Failed to rebuild {os.path.basename(cbz_path)}: {e}", exc_info=True)
        if os.path.exists(temp_cbz_path): os.remove(temp_cbz_path)
        return False

# --- MODIFIED: Main Orchestration and GUI Functions ---

def process_directory(directory, target_image_paths, selected_options, convert_cbr_option):
    modified_files = []
    try:
        target_image_data = [open(p, 'rb').read() for p in target_image_paths]
    except Exception as e:
        logging.error(f"Fatal Error: Failed to read target images: {e}")
        messagebox.showerror("Error", f"Could not read target images: {e}")
        return []

    for dirpath, _, filenames in os.walk(directory):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            
            # --- NEW: CBR Conversion Logic ---
            if filename.lower().endswith('.cbr'):
                if convert_cbr_option:
                    logging.info(f"Found CBR file: '{filename}'. Attempting conversion...")
                    # Call the function from our other file
                    new_cbz_path = converter_logic.convert_single_cbr_to_cbz(file_path)
                    
                    if new_cbz_path:
                        file_path = new_cbz_path 
                        logging.info(f"Conversion successful. Now processing '{os.path.basename(file_path)}' for page removal.")
                    else:
                        logging.error(f"Failed to convert '{filename}'. Skipping file.")
                        continue # Move to the next file
                else:
                    logging.warning(f"Skipping CBR file (conversion option not enabled): {filename}")
                    continue # Move to the next file
            
            # Only process CBZ files from this point on
            if not file_path.lower().endswith('.cbz'):
                continue

            pages_to_remove, original_page_count = find_pages_to_remove(file_path, target_image_data, selected_options)
            if pages_to_remove:
                logging.info(f"Found {len(pages_to_remove)} page(s) to remove in {os.path.basename(file_path)}.")
                success = rebuild_cbz_archive(file_path, pages_to_remove, original_page_count)
                if success:
                    modified_files.append(file_path)
            else:
                logging.info(f"No matching pages found in {os.path.basename(file_path)}. No changes made.")

    return modified_files

def process_files_main_tab():
    directory_path = entry_directory.get()
    target_image_folder = entry_image.get()
    
    selected_options = []
    if first_var.get(): selected_options.append("first")
    if last_var.get(): selected_options.append("last")
    if all_var.get(): selected_options.append("all")
    if last_2_var.get(): selected_options.append("last_2")
    
    # --- NEW: Get state of the CBR conversion checkbox ---
    convert_cbr = bool(convert_cbr_var.get())

    if not selected_options:
        messagebox.showerror("Error", "Please select at least one scan option (First, Last, etc.).")
        return
    if not directory_path or not os.path.isdir(directory_path):
        messagebox.showerror("Error", "Please select a valid comic directory.")
        return
    if not target_image_folder or not os.path.isdir(target_image_folder):
        messagebox.showerror("Error", "Please select a valid target image folder.")
        return
    
    target_images = [os.path.join(target_image_folder, f) for f in os.listdir(target_image_folder) if f.lower().endswith(('.jpg', '.png', '.gif', '.jpeg'))]
    if not target_images:
        messagebox.showerror("Error", "No valid images found in the target folder.")
        return

    logging.info("--- Starting Page Removal Process ---")
    try:
        final_modified_files = process_directory(directory_path, target_images, selected_options, convert_cbr)
        listbox_main_tab.delete(0, tk.END)
        for file in final_modified_files:
            listbox_main_tab.insert(tk.END, os.path.basename(file))
        
        logging.info("\n--- Processing Complete ---")
        logging.info(f"Successfully modified {len(final_modified_files)} files.")
        messagebox.showinfo("Success", f"Processing completed.\n\nModified {len(final_modified_files)} files.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        messagebox.showerror("Error", f"An unexpected error occurred: {e}")

# --- GUI Helper Functions ---

def select_directory_main_tab():
    directory = filedialog.askdirectory()
    if directory:
        entry_directory.delete(0, tk.END)
        entry_directory.insert(0, directory)

def select_image_folder():
    directory = filedialog.askdirectory()
    if directory:
        entry_image.delete(0, tk.END)
        entry_image.insert(0, directory)

def validate_checkboxes(*args):
    if all_var.get():
        first_check.config(state=tk.DISABLED); first_var.set(0)
        last_check.config(state=tk.DISABLED); last_var.set(0)
        last_2_check.config(state=tk.DISABLED); last_2_var.set(0)
    else:
        first_check.config(state=tk.NORMAL)
        last_check.config(state=tk.NORMAL)
        last_2_check.config(state=tk.NORMAL)

def on_first_last_checked(*args):
    if first_var.get() or last_var.get():
        if all_var.get(): all_var.set(0)
    if last_var.get() and last_2_var.get():
        last_2_var.set(0)

def on_last_2_checked(*args):
    if last_2_var.get():
        if all_var.get(): all_var.set(0)
        if last_var.get(): last_var.set(0)

class TkinterLogHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
    def emit(self, record):
        msg = self.format(record)
        self.text_widget.configure(state='normal')
        self.text_widget.insert(tk.END, msg + '\n')
        self.text_widget.configure(state='disabled')
        self.text_widget.see(tk.END)

# --- NEW: Functions for the Converter Tab ---

def select_directory_converter_tab():
    directory = filedialog.askdirectory()
    if directory:
        entry_directory_converter.delete(0, tk.END)
        entry_directory_converter.insert(0, directory)
        # Automatically scan for CBR files and populate the listbox
        populate_cbr_list(directory)

def populate_cbr_list(directory):
    listbox_converter_tab.delete(0, tk.END)
    logging.info(f"[Converter] Scanning '{directory}' for .cbr files...")
    cbr_files_found = []
    for dirpath, _, filenames in os.walk(directory):
        for filename in filenames:
            if filename.lower().endswith('.cbr'):
                cbr_files_found.append(os.path.join(dirpath, filename))
    
    if cbr_files_found:
        for file_path in sorted(cbr_files_found):
            listbox_converter_tab.insert(tk.END, file_path)
        logging.info(f"[Converter] Found {len(cbr_files_found)} .cbr file(s). Ready to convert.")
    else:
        logging.info("[Converter] No .cbr files found in the selected directory.")

def start_conversion_process():
    files_to_convert = listbox_converter_tab.get(0, tk.END)
    if not files_to_convert:
        messagebox.showwarning("Warning", "No CBR files are listed to convert. Please select a directory first.")
        return

    logging.info("--- Starting CBR to CBZ Conversion Process ---")
    success_count = 0
    
    for cbr_path in files_to_convert:
        new_cbz_path = converter_logic.convert_single_cbr_to_cbz(cbr_path)
        if new_cbz_path:
            success_count += 1
    
    logging.info("\n--- Conversion Complete ---")
    logging.info(f"Successfully converted {success_count} of {len(files_to_convert)} file(s).")
    messagebox.showinfo("Success", f"Conversion completed.\n\nSuccessfully converted {success_count} file(s).")
    # Rescan the directory to show it's empty now
    populate_cbr_list(os.path.dirname(files_to_convert[0]))

# ===================================================================
# GUI SETUP
# ===================================================================

root = tk.Tk()
root.title("Comic Processing Tool v2.0")
root.geometry("850x650")

# --- Setup Main Logger ---
logger = logging.getLogger()
logger.setLevel(logging.INFO)
for handler in logger.handlers[:]: logger.removeHandler(handler) # Clear existing handlers

# --- Create the Tab Control (Notebook) ---
tab_control = ttk.Notebook(root)

page_remover_tab = ttk.Frame(tab_control, padding=10)
converter_tab = ttk.Frame(tab_control, padding=10)

tab_control.add(page_remover_tab, text='Page Remover')
tab_control.add(converter_tab, text='CBR to CBZ Converter')
tab_control.pack(expand=1, fill="both")

# ===================================================================
# TAB 1: PAGE REMOVER
# ===================================================================
main_left_frame = tk.Frame(page_remover_tab)
main_left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

main_right_frame = tk.LabelFrame(page_remover_tab, text="Modified Files", font=("Helvetica", 10, "bold"), padx=10, pady=10)
main_right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

# --- Widgets for the left side of the main tab ---
tk.Label(main_left_frame, text="1. Select Comic Directory:", font=("Helvetica", 10, "bold")).pack(anchor='w')
entry_directory = tk.Entry(main_left_frame, width=70)
entry_directory.pack(fill='x', expand=True)
tk.Button(main_left_frame, text="Browse...", command=select_directory_main_tab).pack(anchor='w', pady=(0, 10))

tk.Label(main_left_frame, text="2. Select Target Image Folder:", font=("Helvetica", 10, "bold")).pack(anchor='w')
entry_image = tk.Entry(main_left_frame, width=70)
entry_image.pack(fill='x', expand=True)
tk.Button(main_left_frame, text="Browse...", command=select_image_folder).pack(anchor='w', pady=(0, 10))

options_frame = tk.LabelFrame(main_left_frame, text="3. Processing Options", font=("Helvetica", 10, "bold"), padx=10, pady=10)
options_frame.pack(fill="x", expand=True, pady=10)

first_var, last_var, all_var, last_2_var = tk.IntVar(), tk.IntVar(), tk.IntVar(), tk.IntVar()
convert_cbr_var = tk.IntVar(value=1) # NEW: Variable for CBR conversion, default to ON

# Scan options
scan_options_frame = tk.Frame(options_frame)
scan_options_frame.pack(fill='x')
first_check = tk.Checkbutton(scan_options_frame, text="First Page", variable=first_var); first_check.pack(side=tk.LEFT, padx=5)
last_check = tk.Checkbutton(scan_options_frame, text="Last Page", variable=last_var); last_check.pack(side=tk.LEFT, padx=5)
last_2_check = tk.Checkbutton(scan_options_frame, text="Last 2 Pages", variable=last_2_var); last_2_check.pack(side=tk.LEFT, padx=5)
all_check = tk.Checkbutton(scan_options_frame, text="All Pages", variable=all_var); all_check.pack(side=tk.LEFT, padx=5)

# --- NEW: CBR conversion checkbox ---
cbr_check_frame = tk.Frame(options_frame)
cbr_check_frame.pack(fill='x', pady=(10,0))
tk.Checkbutton(cbr_check_frame, text="Automatically convert CBR files to CBZ before processing", variable=convert_cbr_var).pack(side=tk.LEFT)

first_var.trace_add("write", on_first_last_checked); last_var.trace_add("write", on_first_last_checked)
last_2_var.trace_add("write", on_last_2_checked); all_var.trace_add("write", validate_checkboxes)

button_process = tk.Button(main_left_frame, text="START PROCESSING", font=("Helvetica", 12, "bold"), bg="#4CAF50", fg="white", command=process_files_main_tab)
button_process.pack(pady=20, fill='x', ipady=5)

output_text = scrolledtext.ScrolledText(main_left_frame, wrap=tk.WORD, height=15, state='disabled')
output_text.pack(fill=tk.BOTH, expand=True)

# --- Widgets for the right side of the main tab (Modified Files list) ---
listbox_scrollbar = tk.Scrollbar(main_right_frame, orient="vertical")
listbox_main_tab = tk.Listbox(main_right_frame, yscrollcommand=listbox_scrollbar.set)
listbox_scrollbar.config(command=listbox_main_tab.yview)
listbox_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
listbox_main_tab.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

# ===================================================================
# TAB 2: CBR to CBZ CONVERTER
# ===================================================================
tk.Label(converter_tab, text="Select Directory Containing .CBR Files:", font=("Helvetica", 10, "bold")).pack(anchor='w')
entry_directory_converter = tk.Entry(converter_tab, width=70)
entry_directory_converter.pack(fill='x', expand=True, pady=(0, 5))
tk.Button(converter_tab, text="Browse and Scan for CBR files...", command=select_directory_converter_tab).pack(anchor='w', pady=(0, 10))

list_frame_converter = tk.LabelFrame(converter_tab, text="Found CBR Files (Ready to Convert)", font=("Helvetica", 10, "bold"), padx=10, pady=10)
list_frame_converter.pack(fill=tk.BOTH, expand=True)
listbox_scrollbar_converter = tk.Scrollbar(list_frame_converter, orient="vertical")
listbox_converter_tab = tk.Listbox(list_frame_converter, yscrollcommand=listbox_scrollbar_converter.set)
listbox_scrollbar_converter.config(command=listbox_converter_tab.yview)
listbox_scrollbar_converter.pack(side=tk.RIGHT, fill=tk.Y)
listbox_converter_tab.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

button_convert = tk.Button(converter_tab, text="START CONVERSION", font=("Helvetica", 12, "bold"), bg="#008CBA", fg="white", command=start_conversion_process)
button_convert.pack(pady=20, fill='x', ipady=5)

# The global logger will output to the main tab's log window
gui_handler = TkinterLogHandler(output_text)
gui_handler.setFormatter(logging.Formatter('%(asctime)s: %(message)s', datefmt='%H:%M:%S'))
logger.addHandler(gui_handler)

validate_checkboxes()
root.mainloop()