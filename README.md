# scanner-remover-comics-logo
Script is designed to process comic book files in CBZ (Comic Book Zip) and CBR (Comic Book RAR) formats and removes the last image (if its a scan). Key functions, including extracting page counts from comic metadata, comparing images, and updating comic information.


## Features

- Extract page counts from `ComicInfo.xml` files.
- Compare the last page of comics with target images.
- Update comic metadata based on image comparisons.
- GUI built with Tkinter for easy interaction.

## Demo
<img src="https://github.com/jgutierrezCSU/scanner-remover-comics/blob/main/scanner_animation.gif" alt="Comic Processing Tool Demo" width="450"/>



## Code Requirements

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
python remove_comic_scanner.py
```
2. **In the GUI**:
   * Click Browse to select a directory containing your CBZ and CBR files. 
   * Click Browse to select a folder containing target images.
   * Click Process Comics to start processing.
   * The application will compare the last page of each comic with the images in the selected folder and update the comic's metadata if matches are found.


## EXE

## Comic Processing Tool - Executable Version
## Download

You can download the latest version of the **Comic Processing Tool** from the following link:

[Download the Comic Processing Tool v1.0](https://github.com/jgutierrezCSU/scanner-remover-comics/releases/tag/remove-comic-scanner)

### Summary

The **Comic Processing Tool** is a standalone application designed to simplify the management and processing of comic book files in CBZ (Comic Book Zip) and CBR (Comic Book RAR) formats. This executable version provides users with an easy-to-use graphical interface, allowing comic enthusiasts to efficiently handle their comic collections without the need for programming knowledge.

### Key Features

- **User-Friendly GUI**: Built with Tkinter, the graphical interface allows users to navigate and perform tasks effortlessly.
- **Page Count Extraction**: Automatically retrieves and updates page counts from the `ComicInfo.xml` file within comic archives.
- **Image Comparison**: Compares the last page of comics against target images to ensure consistency and accuracy.
- **Metadata Management**: Updates comic metadata based on image comparisons, keeping your comic collection organized and accurate.

### Installation and Usage

- Simply download the executable file and run it on your Windows machine.
- Use the GUI to select directories containing your comic files and target images.
- Click the "Process Comics" button to start the processing.

