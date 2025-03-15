# scanner-remover-comics
Script is designed to process comic book files in CBZ (Comic Book Zip) and CBR (Comic Book RAR) formats and removes the last image (if its a scan). Key functions, including extracting page counts from comic metadata, comparing images, and updating comic information.


## Features

- Extract page counts from `ComicInfo.xml` files.
- Compare the last page of comics with target images.
- Update comic metadata based on image comparisons.
- GUI built with Tkinter for easy interaction.

## Requirements



- Python 3.x
- Pillow (PIL)
- Tkinter (usually included with Python's standard library)
- Other standard libraries: `zipfile`, `xml.etree.ElementTree`, `os`

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/jgutierrezCSU/scanner-remover-comics

2. **Install Pillow (if not already installed)**:
```bash
   pip install Pillow
```
##Usage
1. **Run the application**:
```bash
python comic_processing_tool.py
```
2. **In the GUI**:
Click Browse to select a directory containing your CBZ and CBR files.
Click Browse to select a folder containing target images.
Click Process Comics to start processing.
The application will compare the last page of each comic with the images in the selected folder and update the comic's metadata if matches are found.
