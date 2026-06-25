import os
import io
import sys
import zipfile
import logging
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

# --- NEW: Imports for multithreading ---
import threading
import queue

import xml.etree.ElementTree as ET
from PIL import Image
import numpy as np
from skimage.metrics import structural_similarity as ssim

# --- Import our custom logic modules ---
import converter_logic
import metadata_logic

# ===================================================================
# ALL CORE LOGIC AND HELPER FUNCTIONS ARE UNCHANGED
# ===================================================================
# [ ... The code for compare_images_in_memory, find_pages_to_remove,
#       update_comic_info, rebuild_cbz_archive, process_directory,
#       select_directory functions, checkbox validation, etc.,
#       is exactly the same as before. It is included here for completeness. ... ]

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
            image_files = sorted([f for f in archive.namelist() if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))])
            if not image_files: return [], 0
            total_page_count = len(image_files)
            pages_to_check_set = set()
            if "all" in options: pages_to_check_set.update(image_files)
            else:
                if "first" in options: pages_to_check_set.add(image_files[0])
                if "last_2" in options:
                    if len(image_files) >= 2: pages_to_check_set.update(image_files[-2:])
                    elif image_files: pages_to_check_set.add(image_files[-1])
                elif "last" in options: pages_to_check_set.add(image_files[-1])
            for page_filename in pages_to_check_set:
                comic_page_data = archive.read(page_filename)
                for target_data in target_image_data:
                    similarity = compare_images_in_memory(comic_page_data, target_data)
                    if similarity >= 0.7:
                        logging.info(f"MATCH FOUND: '{page_filename}' (Similarity: {similarity:.2f}).")
                        pages_to_remove.append(page_filename)
                        break
        return pages_to_remove, total_page_count
    except Exception: return [], 0

def update_comic_info(comic_info_bytes, pages_removed_count, original_page_count):
    tree = ET.ElementTree(ET.fromstring(comic_info_bytes))
    root = tree.getroot()
    page_count_elem = root.find('.//PageCount')
    if page_count_elem is None: page_count_elem = ET.SubElement(root, 'PageCount')
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
            except KeyError: pass
            if renumbering_needed:
                for i, old_filename in enumerate(files_to_keep, 1):
                    _, extension = os.path.splitext(old_filename)
                    new_filename = f"{i:03d}{extension}"
                    target_zip.writestr(new_filename, source_zip.read(old_filename))
            else:
                for filename in files_to_keep: target_zip.writestr(filename, source_zip.read(filename))
            for item in source_zip.infolist():
                if not item.filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', 'comicinfo.xml')):
                    target_zip.writestr(item, source_zip.read(item.filename))
        os.replace(temp_cbz_path, cbz_path)
        return True
    except Exception:
        if os.path.exists(temp_cbz_path): os.remove(temp_cbz_path)
        return False

# ===================================================================
# NEW: THREADING AND QUEUE MANAGEMENT
# ===================================================================

# A new handler that directs log messages to our thread-safe queue
class QueueHandler(logging.Handler):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(self.format(record))

# A function that the GUI will run periodically to check for new messages
def process_queue():
    try:
        # Get a message from the queue without blocking
        message = log_queue.get_nowait()
        
        # Check for our special "task complete" message
        if message == "__TASK_COMPLETE__":
            # Re-enable all the action buttons
            for btn in action_buttons:
                btn.config(state=tk.NORMAL)
        else:
            # It's a regular log message, so display it
            output_text.configure(state='normal')
            output_text.insert(tk.END, message + '\n')
            output_text.configure(state='disabled')
            output_text.see(tk.END)
            
    except queue.Empty:
        # If the queue is empty, do nothing
        pass
    finally:
        # Reschedule this function to run again after 100ms
        root.after(100, process_queue)

# A generic function to start any long-running task on a new thread
def start_threaded_task(task_function, *args):
    # Disable all action buttons to prevent multiple tasks at once
    for btn in action_buttons:
        btn.config(state=tk.DISABLED)

    # This wrapper function runs the real task and then posts the "complete" message
    def task_wrapper():
        try:
            task_function(*args)
        except Exception as e:
            logging.error(f"A critical error occurred in the worker thread: {e}")
        finally:
            log_queue.put("__TASK_COMPLETE__")

    # Create and start the new thread
    thread = threading.Thread(target=task_wrapper)
    thread.daemon = True  # Allows the main window to close even if the thread is running
    thread.start()

# ===================================================================
# MODIFIED: "START" functions are now split into GUI and LOGIC parts
# ===================================================================

# --- PAGE REMOVAL TAB ---
def page_removal_logic(directory, target_image_paths, selected_options, convert_cbr_option):
    """The actual processing logic, designed to be run on a worker thread."""
    modified_files = []
    try:
        target_image_data = [open(p, 'rb').read() for p in target_image_paths]
    except Exception as e:
        logging.error(f"Fatal Error: Failed to read target images: {e}")
        return
    
    for dirpath, _, filenames in os.walk(directory):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            if filename.lower().endswith('.cbr'):
                if convert_cbr_option:
                    logging.info(f"Found CBR: '{filename}'. Converting...")
                    new_cbz_path = converter_logic.convert_single_cbr_to_cbz(file_path)
                    if new_cbz_path:
                        file_path = new_cbz_path
                        logging.info(f"Converted. Now processing '{os.path.basename(file_path)}'.")
                    else:
                        logging.error(f"Failed to convert '{filename}'. Skipping.")
                        continue
                else:
                    logging.warning(f"Skipping CBR (conversion disabled): {filename}")
                    continue
            if not file_path.lower().endswith('.cbz'): continue
            
            pages, count = find_pages_to_remove(file_path, target_image_data, selected_options)
            if pages:
                if rebuild_cbz_archive(file_path, pages, count):
                    modified_files.append(file_path)
            else:
                logging.info(f"No matches in {os.path.basename(file_path)}. No changes.")
                
    logging.info(f"\n--- Page Removal Complete ---")
    logging.info(f"Successfully modified {len(modified_files)} files.")
    messagebox.showinfo("Success", f"Processing completed.\nModified {len(modified_files)} files.")

def start_page_removal_task():
    """This function runs on the main thread. It gathers GUI inputs and starts the worker thread."""
    directory_path = entry_directory.get()
    target_image_folder = entry_image.get()
    selected_options = [opt for var, opt in [(first_var, "first"), (last_var, "last"), (all_var, "all"), (last_2_var, "last_2")] if var.get()]
    convert_cbr = bool(convert_cbr_var.get())
    
    # Input validation
    if not selected_options: messagebox.showerror("Error", "Please select at least one scan option."); return
    if not os.path.isdir(directory_path): messagebox.showerror("Error", "Please select a valid comic directory."); return
    if not os.path.isdir(target_image_folder): messagebox.showerror("Error", "Please select a valid target image folder."); return
    target_images = [os.path.join(target_image_folder, f) for f in os.listdir(target_image_folder) if f.lower().endswith(('.jpg', '.png', '.gif', '.jpeg'))]
    if not target_images: messagebox.showerror("Error", "No valid images in target folder."); return
    
    logging.info("--- Starting Page Removal Process ---")
    start_threaded_task(page_removal_logic, directory_path, target_images, selected_options, convert_cbr)


# --- CONVERTER TAB ---
def conversion_logic(files_to_convert):
    """The actual processing logic, designed to be run on a worker thread."""
    logging.info("--- Starting CBR to CBZ Conversion Process ---")
    success_count = 0
    total_count = len(files_to_convert)
    for cbr_path in files_to_convert:
        if converter_logic.convert_single_cbr_to_cbz(cbr_path):
            success_count += 1
    logging.info(f"\n--- Conversion Complete ---")
    logging.info(f"Successfully converted {success_count} of {total_count} file(s).")
    messagebox.showinfo("Success", f"Conversion completed.\nConverted {success_count} file(s).")

def start_conversion_task():
    """This function runs on the main thread. It gathers GUI inputs and starts the worker thread."""
    files_to_convert = listbox_converter_tab.get(0, tk.END)
    if not files_to_convert:
        messagebox.showwarning("Warning", "No CBR files are listed to convert.")
        return
    start_threaded_task(conversion_logic, files_to_convert)


# --- METADATA TAB ---
def metadata_processing_logic(files_to_process, mode):
    """The actual processing logic, designed to be run on a worker thread."""
    logging.info(f"--- Starting Metadata Process (Mode: {mode.upper()}) ---")
    success_files, failed_files = [], []
    total_count = len(files_to_process)
    for cbz_path in files_to_process:
        filename = os.path.basename(cbz_path)
        logging.info(f"Processing: {filename}")
        status, message = metadata_logic.process_comic_metadata(cbz_path, mode)
        logging.info(f"  -> Status: {message}")
        if status.startswith('SUCCESS') or status.startswith('SKIPPED'):
            success_files.append(filename)
        else:
            failed_files.append(filename)
    
    logging.info(f"\n--- Metadata Processing Complete ---")
    summary = f"Processing completed.\n\nSuccessfully processed: {len(success_files)}"
    if failed_files:
        logging.warning(f"Failed to process: {len(failed_files)} file(s).")
        logging.warning("--- Unsuccessful Files ---")
        for f in failed_files: logging.warning(f"  - {f}")
        summary += f"\nFailed: {len(failed_files)}\n\nSee log for details."
    messagebox.showinfo("Processing Complete", summary)

def start_metadata_task():
    """This function runs on the main thread. It gathers GUI inputs and starts the worker thread."""
    files_to_process = listbox_metadata_tab.get(0, tk.END)
    if not files_to_process:
        messagebox.showwarning("Warning", "No CBZ files are listed to process.")
        return
    mode = metadata_mode_var.get()
    start_threaded_task(metadata_processing_logic, files_to_process, mode)


# --- GUI Helper Functions (largely unchanged) ---
def select_directory_main_tab():
    directory = filedialog.askdirectory()
    if directory: entry_directory.delete(0, tk.END); entry_directory.insert(0, directory)
def select_image_folder():
    directory = filedialog.askdirectory()
    if directory: entry_image.delete(0, tk.END); entry_image.insert(0, directory)
def validate_checkboxes(*args):
    if all_var.get():
        for check, var in [(first_check, first_var), (last_check, last_var), (last_2_check, last_2_var)]:
            check.config(state=tk.DISABLED); var.set(0)
    else:
        for check in [first_check, last_check, last_2_check]: check.config(state=tk.NORMAL)
def on_first_last_checked(*args):
    if first_var.get() or last_var.get():
        if all_var.get(): all_var.set(0)
    if last_var.get() and last_2_var.get(): last_2_var.set(0)
def on_last_2_checked(*args):
    if last_2_var.get():
        if all_var.get(): all_var.set(0)
        if last_var.get(): last_var.set(0)
def select_directory_converter_tab():
    directory = filedialog.askdirectory()
    if directory:
        entry_directory_converter.delete(0, tk.END); entry_directory_converter.insert(0, directory)
        listbox_converter_tab.delete(0, tk.END)
        logging.info(f"[Converter] Scanning '{directory}' for .cbr files...")
        cbr_files = [os.path.join(r, f) for r, _, fl in os.walk(directory) for f in fl if f.lower().endswith('.cbr')]
        if cbr_files:
            for f in sorted(cbr_files): listbox_converter_tab.insert(tk.END, f)
            logging.info(f"[Converter] Found {len(cbr_files)} file(s).")
        else: logging.info("[Converter] No .cbr files found.")
def select_directory_metadata_tab():
    directory = filedialog.askdirectory()
    if directory:
        entry_directory_metadata.delete(0, tk.END); entry_directory_metadata.insert(0, directory)
        listbox_metadata_tab.delete(0, tk.END)
        logging.info(f"[Metadata] Scanning '{directory}' for .cbz files...")
        cbz_files = [os.path.join(directory, f) for f in os.listdir(directory) if f.lower().endswith('.cbz')]
        if cbz_files:
            for f in sorted(cbz_files): listbox_metadata_tab.insert(tk.END, f)
            logging.info(f"[Metadata] Found {len(cbz_files)} file(s).")
        else: logging.info("[Metadata] No .cbz files found.")

# ===================================================================
# GUI SETUP
# ===================================================================

root = tk.Tk()
root.title("Comic Processing Tool v4.0 (Threaded)")
root.geometry("850x700")

# --- Setup Main Logger to use the Queue ---
log_queue = queue.Queue()
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# Remove all old handlers and add our new queue handler
logger.handlers.clear()
logger.addHandler(QueueHandler(log_queue))

# --- Create Tab Control and Tabs ---
tab_control = ttk.Notebook(root)
page_remover_tab = ttk.Frame(tab_control, padding=10)
converter_tab = ttk.Frame(tab_control, padding=10)
metadata_tab = ttk.Frame(tab_control, padding=10)
tab_control.add(page_remover_tab, text='Page Remover')
tab_control.add(converter_tab, text='CBR to CBZ Converter')
tab_control.add(metadata_tab, text='Metadata Editor')
tab_control.pack(expand=1, fill="both")

# --- Global Log Output Frame ---
log_frame = tk.LabelFrame(root, text="Log Output", font=("Helvetica", 10, "bold"), padx=10, pady=10)
log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
output_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=15, state='disabled', bg='black', fg='lightgrey')
output_text.pack(fill=tk.BOTH, expand=True)

# ===================================================================
# BUILD EACH TAB'S WIDGETS
# ===================================================================

# --- TAB 1: PAGE REMOVER ---
main_left_frame = tk.Frame(page_remover_tab); main_left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
main_right_frame = tk.LabelFrame(page_remover_tab, text="Modified Files", font=("Helvetica", 10, "bold"), padx=10, pady=10); main_right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
tk.Label(main_left_frame, text="1. Select Comic Directory:", font=("Helvetica", 10, "bold")).pack(anchor='w')
entry_directory = tk.Entry(main_left_frame, width=70); entry_directory.pack(fill='x', expand=True)
tk.Button(main_left_frame, text="Browse...", command=select_directory_main_tab).pack(anchor='w', pady=(0, 10))
tk.Label(main_left_frame, text="2. Select Target Image Folder:", font=("Helvetica", 10, "bold")).pack(anchor='w')
entry_image = tk.Entry(main_left_frame, width=70); entry_image.pack(fill='x', expand=True)
tk.Button(main_left_frame, text="Browse...", command=select_image_folder).pack(anchor='w', pady=(0, 10))
options_frame = tk.LabelFrame(main_left_frame, text="3. Processing Options", font=("Helvetica", 10, "bold"), padx=10, pady=10); options_frame.pack(fill="x", pady=10)
first_var, last_var, all_var, last_2_var = tk.IntVar(), tk.IntVar(), tk.IntVar(), tk.IntVar()
convert_cbr_var = tk.IntVar(value=1)
scan_options_frame = tk.Frame(options_frame); scan_options_frame.pack(fill='x')
first_check = tk.Checkbutton(scan_options_frame, text="First Page", variable=first_var); first_check.pack(side=tk.LEFT, padx=5)
last_check = tk.Checkbutton(scan_options_frame, text="Last Page", variable=last_var); last_check.pack(side=tk.LEFT, padx=5)
last_2_check = tk.Checkbutton(scan_options_frame, text="Last 2 Pages", variable=last_2_var); last_2_check.pack(side=tk.LEFT, padx=5)
all_check = tk.Checkbutton(scan_options_frame, text="All Pages", variable=all_var); all_check.pack(side=tk.LEFT, padx=5)
cbr_check_frame = tk.Frame(options_frame); cbr_check_frame.pack(fill='x', pady=(10,0))
tk.Checkbutton(cbr_check_frame, text="Automatically convert CBR files to CBZ before processing", variable=convert_cbr_var).pack(side=tk.LEFT)
first_var.trace_add("write", on_first_last_checked); last_var.trace_add("write", on_first_last_checked)
last_2_var.trace_add("write", on_last_2_checked); all_var.trace_add("write", validate_checkboxes)
button_process = tk.Button(main_left_frame, text="START PAGE REMOVAL", font=("Helvetica", 12, "bold"), bg="#4CAF50", fg="white", command=start_page_removal_task)
button_process.pack(pady=20, fill='x', ipady=5)
listbox_scrollbar = tk.Scrollbar(main_right_frame, orient="vertical"); listbox_main_tab = tk.Listbox(main_right_frame, yscrollcommand=listbox_scrollbar.set); listbox_scrollbar.config(command=listbox_main_tab.yview); listbox_scrollbar.pack(side=tk.RIGHT, fill=tk.Y); listbox_main_tab.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

# --- TAB 2: CBR to CBZ CONVERTER ---
tk.Label(converter_tab, text="Select Directory Containing .CBR Files:", font=("Helvetica", 10, "bold")).pack(anchor='w')
entry_directory_converter = tk.Entry(converter_tab, width=70); entry_directory_converter.pack(fill='x', expand=True, pady=(0, 5))
tk.Button(converter_tab, text="Browse and Scan for CBR files...", command=select_directory_converter_tab).pack(anchor='w', pady=(0, 10))
list_frame_converter = tk.LabelFrame(converter_tab, text="Found CBR Files (Ready to Convert)", font=("Helvetica", 10, "bold"), padx=10, pady=10); list_frame_converter.pack(fill=tk.BOTH, expand=True)
listbox_scrollbar_converter = tk.Scrollbar(list_frame_converter, orient="vertical"); listbox_converter_tab = tk.Listbox(list_frame_converter, yscrollcommand=listbox_scrollbar_converter.set); listbox_scrollbar_converter.config(command=listbox_converter_tab.yview); listbox_scrollbar_converter.pack(side=tk.RIGHT, fill=tk.Y); listbox_converter_tab.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
button_convert = tk.Button(converter_tab, text="START CONVERSION", font=("Helvetica", 12, "bold"), bg="#008CBA", fg="white", command=start_conversion_task)
button_convert.pack(pady=20, fill='x', ipady=5)

# --- TAB 3: METADATA EDITOR ---
tk.Label(metadata_tab, text="1. Select Directory Containing .CBZ Files:", font=("Helvetica", 10, "bold")).pack(anchor='w')
entry_directory_metadata = tk.Entry(metadata_tab, width=70); entry_directory_metadata.pack(fill='x', expand=True, pady=(0, 5))
tk.Button(metadata_tab, text="Browse and Scan for CBZ files...", command=select_directory_metadata_tab).pack(anchor='w', pady=(0, 10))
meta_options_frame = tk.LabelFrame(metadata_tab, text="2. Select Processing Action", font=("Helvetica", 10, "bold"), padx=10, pady=10); meta_options_frame.pack(fill="x", pady=10)
metadata_mode_var = tk.StringVar(value="update")
tk.Radiobutton(meta_options_frame, text="Add / Update Series, Volume, & Number from Filename", variable=metadata_mode_var, value="update").pack(anchor='w')
tk.Radiobutton(meta_options_frame, text="Remove ComicInfo.xml from all files", variable=metadata_mode_var, value="remove").pack(anchor='w')
list_frame_metadata = tk.LabelFrame(metadata_tab, text="3. Found CBZ Files (Ready to Process)", font=("Helvetica", 10, "bold"), padx=10, pady=10); list_frame_metadata.pack(fill=tk.BOTH, expand=True)
listbox_scrollbar_metadata = tk.Scrollbar(list_frame_metadata, orient="vertical"); listbox_metadata_tab = tk.Listbox(list_frame_metadata, yscrollcommand=listbox_scrollbar_metadata.set); listbox_scrollbar_metadata.config(command=listbox_metadata_tab.yview); listbox_scrollbar_metadata.pack(side=tk.RIGHT, fill=tk.Y); listbox_metadata_tab.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
button_metadata = tk.Button(metadata_tab, text="START METADATA PROCESSING", font=("Helvetica", 12, "bold"), bg="#f44336", fg="white", command=start_metadata_task)
button_metadata.pack(pady=20, fill='x', ipady=5)

# --- List of all action buttons to be managed by the threading logic ---
action_buttons = [button_process, button_convert, button_metadata]

# --- Final Setup and Main Loop ---
validate_checkboxes()
# Start the queue processing loop
process_queue()
root.mainloop()