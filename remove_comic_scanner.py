import zipfile
import xml.etree.ElementTree as ET
import os
from PIL import Image
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

def get_page_count_from_cbz(cbz_file):
    """Retrieve the page count from ComicInfo.xml inside the CBZ file."""
    try:
        with zipfile.ZipFile(cbz_file, 'r') as zip_ref:
            if 'ComicInfo.xml' not in zip_ref.namelist():
                raise FileNotFoundError("ComicInfo.xml not found in the CBZ archive.")

            with zip_ref.open('ComicInfo.xml') as xml_file:
                tree = ET.parse(xml_file)
                root = tree.getroot()

                page_count_elem = root.find('.//PageCount')
                if page_count_elem is not None:
                    return int(page_count_elem.text)
                else:
                    raise ValueError("PageCount element not found in the ComicInfo.xml file.")
    
    except Exception as e:
        print(f"An error occurred while processing {cbz_file}: {e}")
        return None

def extract_comic_info(cbz_file):
    """Extract the ComicInfo.xml from the CBZ file and return its path."""
    comic_info_path = 'ComicInfo.xml'
    with zipfile.ZipFile(cbz_file, 'r') as zip_ref:
        zip_ref.extract(comic_info_path)
    return comic_info_path

def update_comic_info_page_count(file_path, new_page_count):
    """Update the page count in the ComicInfo.xml file."""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()

        page_count_elem = root.find('.//PageCount')
        if page_count_elem is not None:
            page_count_elem.text = str(new_page_count)

        tree.write(file_path, encoding='utf-8', xml_declaration=True)
    except Exception as e:
        print(f"An error occurred while updating ComicInfo.xml: {e}")

def compare_last_page_with_target(cbz_file, page_count, target_image_path):
    """Compare the last page image with the target; return True if they match, False otherwise."""
    last_page_filename = f"{page_count:02d}.jpg"  # Formatting with leading zero
    print(f"Comparing last page: {last_page_filename} from {os.path.basename(cbz_file)} with target: {os.path.basename(target_image_path)}")

    try:
        with zipfile.ZipFile(cbz_file, 'r') as zip_ref:
            if last_page_filename in zip_ref.namelist():
                with zip_ref.open(last_page_filename) as last_page_file:
                    last_page_image = Image.open(last_page_file)
                    target_image = Image.open(target_image_path)

                    if last_page_image.tobytes() == target_image.tobytes():
                        print(f"{os.path.basename(cbz_file)}: It's a match!")
                        return True
                    else:
                        print(f"{os.path.basename(cbz_file)}: No match.")
                        return False
                    
            else:
                print(f"{os.path.basename(cbz_file)}: Last page image not found in the CBZ archive.")
                return False
    except Exception as e:
        print(f"An error occurred while comparing pages: {e}")
        return False

def replace_comic_info_and_remove_last_page_in_cbz(cbz_file, page_count):
    """Replace ComicInfo.xml in the CBZ file with the updated version and remove the last page."""
    try:
        last_page_filename = f"{page_count + 1:02d}.jpg"  # Formatting with leading zero
        print("------ Removing last page:", last_page_filename)

        with zipfile.ZipFile(cbz_file, 'r') as zip_ref:
            with zipfile.ZipFile(cbz_file + '.tmp', 'w') as temp_zip:
                for item in zip_ref.infolist():
                    if item.filename == 'ComicInfo.xml':
                        temp_zip.write('ComicInfo.xml', arcname='ComicInfo.xml')
                    elif item.filename != last_page_filename:
                        temp_zip.writestr(item.filename, zip_ref.read(item.filename))

        os.replace(cbz_file + '.tmp', cbz_file)
        os.remove('ComicInfo.xml')
    except Exception as e:
        print(f"An error occurred while replacing ComicInfo.xml in CBZ and removing last page: {e}")

def update_comic_info_page_count_in_cbz(cbz_file, new_page_count):
    """Update the page count in the ComicInfo.xml file inside the CBZ file."""
    try:
        comic_info_path = extract_comic_info(cbz_file)
        update_comic_info_page_count(comic_info_path, new_page_count)
        replace_comic_info_and_remove_last_page_in_cbz(cbz_file, new_page_count)
        print(f"Updated ComicInfo.xml with new page count: {new_page_count}")
    except Exception as e:
        print(f"An error occurred while updating ComicInfo.xml: {e}")

# Global list to keep track of successfully modified files
modified_files = []

def process_cbz_and_cbr_files(directory, target_image_path):
    """Process all CBZ and CBR files in the specified directory and its subdirectories."""
    for dirpath, _, filenames in os.walk(directory):
        for filename in filenames:
            if filename.lower().endswith(('.cbz', '.cbr')):
                file_path = os.path.join(dirpath, filename)
                page_count = get_page_count_from_cbz(file_path)

                if page_count is not None:
                    if compare_last_page_with_target(file_path, page_count, target_image_path):
                        update_comic_info_page_count_in_cbz(file_path, page_count - 1)
                        modified_files.append(file_path)  # Track modified files

def display_modified_files():
    """Display the list of modified files in the scrollable window."""
    listbox.delete(0, tk.END)  # Clear previous entries
    for file in modified_files:
        listbox.insert(tk.END, file)

def select_directory():
    """Open a file dialog to select a directory."""
    directory = filedialog.askdirectory()
    if directory:
        entry_directory.delete(0, tk.END)
        entry_directory.insert(0, directory)

def select_image_folder():
    """Open a file dialog to select a folder containing target images."""
    directory = filedialog.askdirectory()
    if directory:
        entry_image.delete(0, tk.END)
        entry_image.insert(0, directory)

def process_files():
    """Process files in the selected directory."""
    directory_path = entry_directory.get()
    target_image_folder = entry_image.get()
    
    if not directory_path or not os.path.isdir(directory_path):
        messagebox.showerror("Error", "Please select a valid directory.")
        return
    if not target_image_folder or not os.path.isdir(target_image_folder):
        messagebox.showerror("Error", "Please select a valid image folder.")
        return

    target_images = [os.path.join(target_image_folder, f) for f in os.listdir(target_image_folder) 
                     if f.lower().endswith(('.jpg', '.png'))]

    if not target_images:
        messagebox.showerror("Error", "No valid images found in the selected folder.")
        return

    try:
        for target_image_path in target_images:
            process_cbz_and_cbr_files(directory_path, target_image_path)
        display_modified_files()  # Update the scrollable window
        messagebox.showinfo("Success", "Processing completed successfully.")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")

# Define necessary functions (get_page_count_from_cbz, extract_comic_info, etc.) here...

# Global list to keep track of successfully modified files
modified_files = []

def display_modified_files():
    """Display the list of modified files in the scrollable window."""
    listbox.delete(0, tk.END)  # Clear previous entries
    for file in modified_files:
        listbox.insert(tk.END, file)

# GUI Setup 
root = tk.Tk()
root.title("Comic Processing Tool")

# Create a frame for the main content
main_frame = tk.Frame(root)
main_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

# Directory Selection
label_directory = tk.Label(main_frame, text="Select Comic Directory:")
label_directory.pack(pady=3)
entry_directory = tk.Entry(main_frame, width=50)
entry_directory.pack(pady=3)
button_browse_directory = tk.Button(main_frame, text="Browse", command=select_directory)
button_browse_directory.pack(pady=3)

# Image Folder Selection
label_image = tk.Label(main_frame, text="Select Target Image Folder \n (all images here will be compared):")
label_image.pack(pady=5)
entry_image = tk.Entry(main_frame, width=50)
entry_image.pack(pady=5)
button_browse_image = tk.Button(main_frame, text="Browse", command=select_image_folder)
button_browse_image.pack(pady=3)

# Process Button
button_process = tk.Button(main_frame, text="Process Comics", command=process_files)
button_process.pack(pady=10)

# Toggle Output Button
def toggle_output():
    """Toggle the visibility of the output frame."""
    if output_frame.winfo_viewable():
        output_frame.pack_forget()
        toggle_button.config(text="Show Output")
    else:
        output_frame.pack(fill=tk.BOTH, expand=True)
        toggle_button.config(text="Hide Output")

toggle_button = tk.Button(main_frame, text="Show Output", command=toggle_output)
toggle_button.pack(pady=5)

# Create a frame for command output
output_frame = tk.Frame(main_frame)
output_frame.pack(fill=tk.BOTH, expand=True)

# ScrolledText for command output
output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, height=10)
output_text.pack(fill=tk.BOTH, expand=True)

# Create a new frame for the scrollable window
scrollable_frame = tk.Frame(root)
scrollable_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

# Title for the scrollable section
label_modified_files = tk.Label(scrollable_frame, text="Files Modified/Updated")
label_modified_files.pack(pady=5)

# Create a canvas for scrolling
canvas = tk.Canvas(scrollable_frame)
scrollable_canvas = tk.Frame(canvas)
scrollbar_y = tk.Scrollbar(scrollable_frame, orient="vertical", command=canvas.yview)
scrollbar_x = tk.Scrollbar(scrollable_frame, orient="horizontal", command=canvas.xview)
canvas.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

# Layout the canvas and scrollbars
scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
canvas.create_window((0, 0), window=scrollable_canvas, anchor="nw")

# Update scroll region
def configure_canvas(event):
    canvas.configure(scrollregion=canvas.bbox("all"))

scrollable_canvas.bind("<Configure>", configure_canvas)

# Create a frame to hold the Listbox
listbox_frame = tk.Frame(scrollable_canvas)
listbox_frame.pack(fill=tk.BOTH, expand=True)

# Listbox to display modified files
listbox = tk.Listbox(listbox_frame, width=50, height=20)
listbox.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

# Add horizontal scrollbar to the Listbox
listbox_scrollbar_x = tk.Scrollbar(listbox_frame, orient="horizontal", command=listbox.xview)
listbox_scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
listbox.configure(xscrollcommand=listbox_scrollbar_x.set)

# Redirect print statements to the scrolled text
class RedirectText:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, string):
        self.text_widget.insert(tk.END, string)
        self.text_widget.see(tk.END)

    def flush(self):
        pass

import sys
sys.stdout = RedirectText(output_text)

# Start the Tkinter event loop
root.mainloop()
