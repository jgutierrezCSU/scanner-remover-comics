# scanner-remover-comics
Script is designed to process comic book files in CBZ (Comic Book Zip) and CBR (Comic Book RAR) formats and removes the last image (the scan). Key functions, including extracting page counts from comic metadata, comparing images, and updating comic information.


# Comic Processing Tool

A Python application for processing comic book files in CBZ (Comic Book Zip) and CBR (Comic Book RAR) formats. This tool allows users to extract metadata, compare images, and update comic information through a user-friendly graphical interface.

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
   
