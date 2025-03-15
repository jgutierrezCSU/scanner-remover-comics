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
            # Check if ComicInfo.xml exists in the CBZ archive
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

        # Save the updated ComicInfo.xml
        tree.write(file_path, encoding='utf-8', xml_declaration=True)
    except Exception as e:
        print(f"An error occurred while updating ComicInfo.xml: {e}")

def compare_last_page_with_target(cbz_file, page_count, target_image_path):
    """Compare the last page image with the target; return True if they match, False otherwise."""
    last_page_filename = f"{page_count:02d}.jpg"  # Formatting with leading zero
    print(f"Comparing last page: {last_page_filename} from {os.path.basename(cbz_file)} with target: {os.path.basename(target_image_path)}")

    try:
        with zipfile.ZipFile(cbz_file, 'r') as zip_ref:
            # Check if the last page image exists in the CBZ archive
            if last_page_filename in zip_ref.namelist():
                with zip_ref.open(last_page_filename) as last_page_file:
                    last_page_image = Image.open(last_page_file)
                    target_image = Image.open(target_image_path)

                    # Compare the last page image with the target image
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
                        # Write the updated ComicInfo.xml
                        temp_zip.write('ComicInfo.xml', arcname='ComicInfo.xml')
                    elif item.filename != last_page_filename:
                        # Write other files unchanged except the last page
                        temp_zip.writestr(item.filename, zip_ref.read(item.filename))

        # Replace the original file with the updated version
        os.replace(cbz_file + '.tmp', cbz_file)
        os.remove('ComicInfo.xml')  # Clean up the temporary ComicInfo.xml
    except Exception as e:
        print(f"An error occurred while replacing ComicInfo.xml in CBZ and removing last page: {e}")

def update_comic_info_page_count_in_cbz(cbz_file, new_page_count):
    """Update the page count in the ComicInfo.xml file inside the CBZ file."""
    try:
        # Extract ComicInfo.xml
        comic_info_path = extract_comic_info(cbz_file)
        
        # Update the page count
        update_comic_info_page_count(comic_info_path, new_page_count)

        # Replace ComicInfo.xml and remove the last page
        replace_comic_info_and_remove_last_page_in_cbz(cbz_file, new_page_count)

        print(f"Updated ComicInfo.xml with new page count: {new_page_count}")
    except Exception as e:
        print(f"An error occurred while updating ComicInfo.xml: {e}")

def process_cbz_and_cbr_files(directory, target_image_path):
    """Process all CBZ and CBR files in the specified directory and its subdirectories."""
    for dirpath, _, filenames in os.walk(directory):
        for filename in filenames:
            # Check if the file is a CBZ or CBR
            if filename.lower().endswith(('.cbz', '.cbr')):
                file_path = os.path.join(dirpath, filename)
                page_count = get_page_count_from_cbz(file_path)  # Get the page count

                if page_count is not None:
                    # Compare the last page with the target image
                    if compare_last_page_with_target(file_path, page_count, target_image_path):
                        # Update the page count in ComicInfo.xml if there is a match
                        update_comic_info_page_count_in_cbz(file_path, page_count - 1)

def select_directory():
    """Open a file dialog to select a directory."""
    directory = filedialog.askdirectory()
    if directory:
        entry_directory.delete(0, tk.END)  # Clear the entry field
        entry_directory.insert(0, directory)  # Insert the selected directory

def select_image_folder():
    """Open a file dialog to select a folder containing target images."""
    directory = filedialog.askdirectory()
    if directory:
        entry_image.delete(0, tk.END)  # Clear the entry field
        entry_image.insert(0, directory)  # Insert the selected directory

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

    # Get a list of all image files in the selected folder
    target_images = [os.path.join(target_image_folder, f) for f in os.listdir(target_image_folder) 
                     if f.lower().endswith(('.jpg', '.png'))]

    if not target_images:
        messagebox.showerror("Error", "No valid images found in the selected folder.")
        return

    # Process each target image
    try:
        for target_image_path in target_images:
            process_cbz_and_cbr_files(directory_path, target_image_path)
        messagebox.showinfo("Success", "Processing completed successfully.")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")

# GUI Setup 
root = tk.Tk()
root.title("Comic Processing Tool")

# Directory Selection
label_directory = tk.Label(root, text="Select Comic Directory:")
label_directory.pack(pady=3)  # Add vertical padding
entry_directory = tk.Entry(root, width=50)
entry_directory.pack(pady=3)  # Add vertical padding
button_browse_directory = tk.Button(root, text="Browse", command=select_directory)
button_browse_directory.pack(pady=3)  # Add vertical padding

# Image Folder Selection
label_image = tk.Label(root, text="Select Target Image Folder \n (all images here will be compared):")
label_image.pack(pady=5)  # Add vertical padding
entry_image = tk.Entry(root, width=50)
entry_image.pack(pady=5)  # Add vertical padding
button_browse_image = tk.Button(root, text="Browse", command=select_image_folder)
button_browse_image.pack(pady=3)  # Add vertical padding

# Process Button
button_process = tk.Button(root, text="Process Comics", command=process_files)
button_process.pack(pady=10)  # Add vertical padding

# Collapsible Output Section
def toggle_output():
    """Toggle the visibility of the output frame."""
    if output_frame.winfo_viewable():
        output_frame.pack_forget()
        toggle_button.config(text="Show Output")
    else:
        output_frame.pack(fill=tk.BOTH, expand=True)
        toggle_button.config(text="Hide Output")

toggle_button = tk.Button(root, text="Show Output", command=toggle_output)
toggle_button.pack(pady=5)  # Add vertical padding

# Frame for command output
output_frame = tk.Frame(root)
output_frame.pack(fill=tk.BOTH, expand=True)

# ScrolledText for command output
output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, height=10)
output_text.pack(fill=tk.BOTH, expand=True)

# Redirect print statements to the scrolled text
class RedirectText:
    """Class to redirect print statements to a text widget."""
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, string):
        """Insert the string into the text widget."""
        self.text_widget.insert(tk.END, string)
        self.text_widget.see(tk.END)  # Auto-scroll to the end

    def flush(self):
        """Flush method for compatibility."""
        pass  # This is needed for compatibility

# Redirecting stdout to the output_text
import sys
sys.stdout = RedirectText(output_text)

# Start the Tkinter event loop
root.mainloop()
