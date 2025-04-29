import zipfile
import xml.etree.ElementTree as ET
import os
from PIL import Image
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from PIL import Image, ImageChops
from skimage.metrics import structural_similarity as ssim 
import numpy as np
import logging


def get_mult_info_cbz(cbz_file):
    """Extract the names of the first and second-to-last files in a CBZ file."""
    print(cbz_file)
    if not os.path.isfile(cbz_file):
        print("File does not exist.")
        return []

    if cbz_file.lower().endswith('.cbz'):
        with zipfile.ZipFile(cbz_file, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            if len(file_list) < 2:
                print("Not enough files in the CBZ archive.")
                return []
            
            first_page = file_list[1]  # Second item (index 1)
            last_page = file_list[-1]    # Last item (index -1)
            return file_list, first_page, last_page;
    else:
        print("Unsupported file format. Please use a .cbz file.")
        return []
        

def compare_images_with_ssim(image_path1, image_path2):
    """Compare two images using SSIM."""
    # Open and convert images to grayscale
    image1 = Image.open(image_path1).convert('L')
    image2 = Image.open(image_path2).convert('L')

    # Resize images to the same size, if necessary
    if image1.size != image2.size:
        image2 = image2.resize(image1.size)

    # Convert images to numpy arrays
    img1_array = np.array(image1)
    img2_array = np.array(image2)

    # Calculate SSIM
    similarity_index, _ = ssim(img1_array, img2_array, full=True)
    print("comparing: ",image_path1, "--> ",image_path2 )
    return similarity_index



def extract_second_and_last(item_list):
    """Extract the second item and the last item from the list."""
    if len(item_list) < 2:
        print("List must contain at least two items.")
        return None, None  # Return None for both if there are not enough items

    second_item = item_list[1]  # Second item (index 1)
    last_item = item_list[-1]    # Last item (index -1)
    return second_item, last_item
    
 
        
MATCH_LIST = {}  # Dictionary to store matched files with their match status
def compare_pages_with_target(cbz_file, target_image_path, cbz_details_lst, option):
    print("cur comic: -->", cbz_file)
    
    # Initialize the match status for this cbz_file if not already present
    if cbz_file not in MATCH_LIST:
        MATCH_LIST[cbz_file] = {'first_match': False, 'last_match': False}
    
    # Use the current match status as the starting point for match_outcome
    match_outcome = {
        'first_match': MATCH_LIST[cbz_file]['first_match'], 
        'last_match': MATCH_LIST[cbz_file]['last_match']
    }
    
    # If both pages are already matched, skip comparison
    if match_outcome['first_match'] and match_outcome['last_match']:
        return match_outcome

    first_page_filename, last_page_filename = extract_second_and_last(cbz_details_lst)
    try:
        with zipfile.ZipFile(cbz_file, 'r') as zip_ref:
            # Check for last page match 
            if option in ['last', 'both'] and last_page_filename in zip_ref.namelist():
                if not match_outcome['last_match']:
                    print("*In Last OPTION*")
                    last_page_path = os.path.join("temp", last_page_filename)
                    zip_ref.extract(last_page_filename, "temp")
                    similarity_index = compare_images_with_ssim(last_page_path, target_image_path)                
                    if similarity_index >= 0.7:
                        match_outcome['last_match'] = True
                        MATCH_LIST[cbz_file]['last_match'] = True
                        print("cbz=", cbz_file)
                        print(f"Last page match FOUND: {last_page_filename}")

            # Check for first page match
            if option in ['first', 'both'] and first_page_filename in zip_ref.namelist():
                if not match_outcome['first_match']:
                    print("In first OPTION")
                    first_page_path = os.path.join("temp", first_page_filename)
                    zip_ref.extract(first_page_filename, "temp")
                    similarity_index = compare_images_with_ssim(first_page_path, target_image_path)                    
                    if similarity_index >= 0.7:
                        match_outcome['first_match'] = True
                        MATCH_LIST[cbz_file]['first_match'] = True
                        print(f"First page match FOUND: {first_page_filename}")
            
            return match_outcome

    except Exception as e:
        print(f"Error during comparison: {e}")

    return match_outcome


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)  # Define the logger

# NEW FUNCT
def update_comic_info_page_count(comic_info_bytes, new_page_count):
    """
    Update the PageCount in the ComicInfo.xml content.
    
    :param comic_info_bytes: Byte content of ComicInfo.xml
    :param new_page_count: New page count to set
    :return: Updated byte content of ComicInfo.xml
    """
    # Parse the XML content
    tree = ET.ElementTree(ET.fromstring(comic_info_bytes))
    root = tree.getroot()

    # Update the PageCount with the new value
    page_count_elem = root.find('.//PageCount')
    if page_count_elem is not None:
        page_count_elem.text = str(new_page_count)  # Use the passed variable

    # Convert the modified XML back to bytes
    updated_comic_info = ET.tostring(root, encoding='utf-8', xml_declaration=True)
    
    return updated_comic_info


def process_last_file_from_cbz(source_zip, target_zip):
    """
    Process a CBZ file to remove the last image file.
    
    :param source_zip: The opened source zipfile object
    :param target_zip: The opened target zipfile object where files will be written
    """
    # Get a list of all files in the zip
    all_files = source_zip.namelist()
    logger.info(f"Processing files: {len(all_files)} files found")
    
    # Check if there are files to process
    if not all_files:
        logger.warning("No files found in the CBZ.")
        return
    
    # Filter to only get image files (exclude ComicInfo.xml and other non-image files)
    image_files = [
        f for f in all_files
        if f != 'ComicInfo.xml' and
        any(f.lower().endswith(ext) for ext in ['.jpg', '.png', '.jpeg', '.gif'])
    ]
    
    # Sort the image files to ensure consistent ordering
    image_files.sort()
    
    # Identify the last file (to exclude it)
    if image_files:
        last_file = image_files[-1]
        logger.info(f"Excluding last file: {last_file}")
        
        # Copy all image files except the last one to the target zip
        for filename in all_files:
            # Skip the last image file and ComicInfo.xml (which is handled separately)
            if filename != last_file and filename != 'ComicInfo.xml':
                file_content = source_zip.read(filename)
                target_zip.writestr(filename, file_content)
                logger.info(f"Copied: {filename}")
    else:
        logger.warning("No image files found to process")

def make_new_cbz_file(cbz_file, cbz_details_lst, page_count, option):
    """
    Renumber/Make new copy pages in a CBZ file, removing the first/last page and adjusting numbering.
    
    :param cbz_file: Path to the CBZ file to be processed
    :param cbz_details_lst: List containing file details (typically from a previous extraction)
    :param page_count: Current page count
    :param option: "first" to remove first page, "last" to remove last page
    """
    
    new_page_count = page_count - 1
    # Configure logging
    logger.info(f"Processing with option: {option}")
    logger.info(f"Starting renumbering process for {cbz_file}")
    
    try:
        # Create a temporary file name for the new CBZ
        temp_cbz = cbz_file + '.tmp'
        logger.info("Preparing to process file")
        
        # Filter and sort image files (excluding ComicInfo.xml)
        image_files = sorted([
            f for f in cbz_details_lst
            if f not in ['ComicInfo.xml']
            and any(f.lower().endswith(ext) for ext in ['.jpg', '.png', '.jpeg', '.gif'])
        ])       
        logger.info(f"Found {len(image_files)} image files")
        
        # Check if there are any image files to process
        if not image_files:
            logger.error("No image files found in the CBZ")
            return False
        
        # Open source and target ZIP files
        with zipfile.ZipFile(cbz_file, 'r') as source_zip, \
             zipfile.ZipFile(temp_cbz, 'w', zipfile.ZIP_DEFLATED) as target_zip:
            
            # Check if ComicInfo.xml exists and copy it
            try:
                # Read ComicInfo.xml from the source ZIP
                comic_info = source_zip.read('ComicInfo.xml')     
                # Update the PageCount using the new function
                updated_comic_info = update_comic_info_page_count(comic_info, new_page_count)
                # Write the modified ComicInfo.xml back to the target ZIP
                target_zip.writestr('ComicInfo.xml', updated_comic_info)
                logger.info("ComicInfo.xml updated and copied successfully")
            except KeyError:
                logger.warning("No ComicInfo.xml found in the source CBZ")
            
            # Process based on the selected option
            if option == "first":
                # Skip the first image and renumber the rest
                for new_index, old_filename in enumerate(image_files[1:], 1):
                    new_filename = f"{new_index:02d}{os.path.splitext(old_filename)[1]}"
                    try:
                        file_content = source_zip.read(old_filename)
                        target_zip.writestr(new_filename, file_content)
                        logger.info(f"Processed: {old_filename} -> {new_filename}")
                    except Exception as file_error:
                        logger.error(f"Error processing file {old_filename}: {file_error}")
                        raise
            elif option == "last":
                logger.info("Processing option: remove last file")
                # ComicInfo.xml is already handled above, so we can now process the image files
                process_last_file_from_cbz(source_zip, target_zip)
            else:
                logger.warning(f"Unknown option: {option}")
        
        # Replace the original file with the new one
        os.replace(temp_cbz, cbz_file)
        logger.info(f"Successfully processed {cbz_file}")
        return True
    
    except Exception as e:
        logger.error(f"Error processing file: {e}", exc_info=True)
        # Clean up temporary file if it exists
        if os.path.exists(temp_cbz):
            os.remove(temp_cbz)
        return False
        

    
    except Exception as e:
        logger.error(f"Error processing file: {e}", exc_info=True)
        # Clean up temporary file if it exists
        if os.path.exists(temp_cbz):
            os.remove(temp_cbz)
        return False

def extract_comic_info(cbz_file):
    """Extracts Locally the ComicInfo.xml from the CBZ file for editing and return its path."""
    comic_info_path = 'ComicInfo.xml'
    with zipfile.ZipFile(cbz_file, 'r') as zip_ref:
        zip_ref.extract(comic_info_path)
    return comic_info_path


def process_cbz_and_cbr_files(directory, target_image_path, option):
    """Process all CBZ and CBR files in the specified directory and its subdirectories."""
    for dirpath, _, filenames in os.walk(directory):
        for filename in filenames:
            if filename.lower().endswith(('.cbz', '.cbr')):
                cbz_file = os.path.join(dirpath, filename)
                cbz_details_lst, first_page, last_page = get_mult_info_cbz(cbz_file)
                page_count = len(cbz_details_lst) - 1  # Minus the XML file
                option="last"
                if cbz_details_lst is not None:                    
                    # Use the updated comparison function
                    print("cbz_details_lst=",cbz_details_lst)
                    match_outcome = compare_pages_with_target(cbz_file, target_image_path, cbz_details_lst, option)
                    print("match_outcome= ",match_outcome)
                    # Check if a match was found for either page
                    pages_to_remove = []
                    if match_outcome['first_match']:
                        pages_to_remove.append(first_page)  # Add first page to modified pages list
                        MATCH_LIST[cbz_file]['first_match'] = False                        
                        make_new_cbz_file(cbz_file, cbz_details_lst,page_count,option)
                    if match_outcome['last_match']:
                        print("IN LAST")
                        pages_to_remove.append(last_page)  # Add last page to modified pages list
                        MATCH_LIST[cbz_file]['last_match'] = False
                        make_new_cbz_file(cbz_file, cbz_details_lst,page_count,option)
                    # Only update if there are modified pages
                    if pages_to_remove:
                        final_modified_files.append(cbz_file)  # Track modified files


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
    # Needed
    target_images = [os.path.join(target_image_folder, f) for f in os.listdir(target_image_folder) 
                     if f.lower().endswith(('.jpg', '.png','.gif','.jpeg'))]

    if not target_images:
        messagebox.showerror("Error", "No valid images found in the selected folder.")
        return

    try:
        for target_image_path in target_images: 
            print("Cur img: ",target_image_path)
            process_cbz_and_cbr_files(directory_path, target_image_path,"temp")  # First Function after button Press
        display_final_modified_files()  # Update the scrollable window
        messagebox.showinfo("Success", "Processing completed successfully.")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")

def select_directory():
    """Open a file dialog to select a directory."""
    #directory = filedialog.askdirectory() #original
    directory="W:\Documents\Coding\Python\Remove Comic Scanner\TESTING\Temp Coms Solo"
    if directory:
        entry_directory.delete(0, tk.END)
        entry_directory.insert(0, directory)

def select_image_folder():
    """Open a file dialog to select a folder containing target images."""
    #directory = filedialog.askdirectory() #original
    directory= "W:\Documents\Coding\Python\Remove Comic Scanner\TESTING\Target Images"
    if directory:
        entry_image.delete(0, tk.END)
        entry_image.insert(0, directory)


# Global list to keep track of successfully modified files
final_modified_files = []
def display_final_modified_files():
    """Display the list of modified files in the scrollable window."""
    listbox.delete(0, tk.END)  # Clear previous entries
    for file in final_modified_files:
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
label_final_modified_files = tk.Label(scrollable_frame, text="Files Modified/Updated")
label_final_modified_files.pack(pady=5)

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
