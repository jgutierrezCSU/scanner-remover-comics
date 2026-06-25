

# Comic Processing Tool (Scanner Remover & Metadata Manager)

This robust application is designed to process, convert, and manage comic book files in CBZ (Comic Book Zip) and CBR (Comic Book RAR) formats. Originally built just to remove scanner logos from the end of comics, it has evolved into a fully multithreaded, multi-tool suite with a responsive Graphical User Interface (GUI).

Key Features

### 1. Advanced Page Remover (Tab 1)
*   **Flexible Scanning**: No longer limited to just the last page! You can now choose to scan the **First Page**, **Last Page**, **Last 2 Pages**, or **All Pages** for scanner logos.
*   **Smarter Image Comparison**: Uses Structural Similarity Index (SSIM) via `scikit-image` for highly accurate visual matching, rather than simple byte comparisons.
*   **Auto-Conversion**: Can automatically convert `.cbr` files to `.cbz` on-the-fly before scanning.
*   **Format Support**: Now scans `.jpg`, `.jpeg`, `.png`, and `.gif` files inside archives.
*   **Auto Metadata Update**: Automatically updates the `<PageCount>` in `ComicInfo.xml` when a page is removed.

### 2. Dedicated CBR to CBZ Converter (Tab 2)
*   Batch convert entire folders of `.cbr` (RAR) comics to `.cbz` (ZIP) formats.
*   Automatically cleans up and deletes the original `.cbr` file upon successful conversion.

### 3. Smart Metadata Editor (Tab 3)
*   **Intelligent Parsing**: Reads the comic's filename and intelligently updates or creates a `ComicInfo.xml` file without extracting the archive to your hard drive (fast, in-memory processing).
*   **Preserves Existing Data**: Updates *only* the `Series`, `Volume`, `Number`, and `Title` tags. It safely leaves your existing metadata (writers, summaries, etc.) completely untouched.
*   **Handles Complex Naming**: 
    *   Correctly parses decimals (e.g., Issue `#23.1`).
    *   Identifies Annuals (e.g., `SP2015` -> `Annual 2015`).
    *   Standardizes event tie-ins (e.g., `054.LR` becomes `<Number>54.1</Number>` while keeping the original string in the `<Title>` tag).
*   **Remove Metadata**: Easily strip all `ComicInfo.xml` files from a folder of comics if desired.

### 4. Multithreaded UI
*   The application runs all heavy processing in the background. The GUI remains 100% responsive with real-time log updates, preventing "Not Responding" freezes.

---

## Demo
<img src="https://github.com/jgutierrezCSU/scanner-remover-comics/blob/main/scanner_animation.gif" alt="Comic Processing Tool Demo" width="450"/>

*(Note: GIF may reflect an older version of the UI)*

---

## Code Requirements

- **Python 3.x**
- **Required Python Libraries**: `Pillow`, `numpy`, `scikit-image`, `rarfile`
- **External Dependency**: `UnRAR.exe` (Required for handling `.cbr` files)
- **Standard Libraries used**: `zipfile`, `xml.etree.ElementTree`, `os`, `threading`, `queue`, `tkinter`

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/jgutierrezCSU/scanner-remover-comics
   ```

2. **Install Required Python Libraries**:
   ```bash
   pip install Pillow numpy scikit-image rarfile
   ```

3. **Install UnRAR (Crucial for CBR support)**:
   * Download the command-line **UnRAR for Windows** from the [official RARLAB website](https://www.rarlab.com/rar_add.htm).
   * Extract `UnRAR.exe` and place it in the **exact same folder** as your Python scripts (or add it to your Windows System PATH).

## Usage

1. **Run the application**:
   ```bash
   python main_program.py
   ```
2. **Using the GUI**:
   * Navigate between the **Page Remover**, **Converter**, and **Metadata Editor** tabs depending on the task.
   * **Target Images**: For the Page Remover, ensure you have extracted copies of the scanner logos/images you want to remove into a specific folder so the app has something to compare against.
   * Click the **START** button on any tab. The bottom log window will update in real-time to show you exact successes, failures, and skipped files.

---

## Comic Processing Tool - Executable Version (EXE)

If you don't want to mess with Python or pip, you can download the standalone Windows Executable!

### [Download the Latest Release Here](https://github.com/jgutierrezCSU/scanner-remover-comics/releases) 

### Summary
The executable version provides an easy-to-use graphical interface, allowing comic enthusiasts to efficiently handle, convert, and clean their comic collections without writing a single line of code.

### Important Note for EXE Users
To process `.cbr` files, the `.exe` still relies on the `UnRAR` utility. Ensure that `UnRAR.exe` is located in the same folder where you place and run your downloaded `ComicProcessingTool.exe`.