
# Comic Processing Tool

A graphical utility designed to batch process, convert, and manage metadata for comic book archives in CBZ (Comic Book Zip) and CBR (Comic Book RAR) formats on Windows. 

The application uses multithreading to ensure the user interface remains responsive and updates real-time logs during heavy file operations.

---

## Technical Specifications & Features

### 1. Page Remover Tab
*   **Targeted Scanning**: Scans comic archives for specific images (such as scan group credits or logo pages) based on user-selected criteria:
    *   *First Page*
    *   *Last Page*
    *   *Last 2 Pages*
    *   *All Pages*
*   **Image Similarity Matching**: Uses the Structural Similarity Index (SSIM) algorithm via `scikit-image` to compare pages within the archive to reference images. This handles different resolutions and slight compressions.
*   **Automatic XML Updates**: When pages are successfully removed, the script automatically parses the internal `ComicInfo.xml` file and decrements the `<PageCount>` tag to match the new count.
*   **Auto-Conversion**: Includes an optional checkbox to automatically convert `.cbr` files to `.cbz` before processing for page removal.
*   **File Formats**: Supports scanning and re-packing `.jpg`, `.jpeg`, `.png`, and `.gif` image types inside the archives.

### 2. CBR to CBZ Converter Tab
*   **Batch Conversion**: Automatically scans a directory to find `.cbr` (RAR-based) files and converts them into `.cbz` (ZIP-based) files.
*   **File Cleanup**: Safely deletes the original `.cbr` file only after confirming the `.cbz` copy has been successfully written.

### 3. Metadata Editor Tab
*   **In-Memory XML Modification**: Opens, reads, and rebuilds the `ComicInfo.xml` directly in system memory. This avoids writing temporary extraction folders to the disk, reducing disk read/write cycles.
*   **Selective Metadata Updates**: Automatically parses the filename to update *only* the `<Series>`, `<Volume>`, `<Number>`, and `<Title>` tags. It leaves all other pre-existing XML metadata (such as `<Writer>`, `<Penciller>`, `<Summary>`) untouched.
*   **Namespace Stripping**: Automatically cleans up and strips XML namespaces (e.g., `xmlns:xsd`, `xmlns:xsi`) from incoming XML files to prevent parser errors.
*   **Advanced Filename Parsing**:
    *   **Event Suffixes**: Parses issue numbers with alphabetic suffixes (e.g., `054.LR` or `078.BEY`). It saves the full suffix in the `<Title>` tag (e.g., `... #054.LR`) but standardizes the `<Number>` tag to a numeric decimal (e.g., `54.1`) for comic reader sorting.
    *   **Decimal Issues**: Recognizes decimal issues (e.g., `023.1`) and updates both `<Number>` and `<Title>` tags correctly.
    *   **Annuals/Special Issues**: Parses annual naming conventions (e.g., `SP2015`) to write `Annual 2015` directly to the `<Number>` and `<Title>` tags.
*   **Metadata Removal**: Includes an alternate mode to strip and remove `ComicInfo.xml` files from all `.cbz` archives in a selected folder.

---

## System Requirements

### Python Environment
To run the source code, you need **Python 3.x** and the following dependencies:
*   `Pillow` (for image loading and processing)
*   `numpy` (for structural image array conversions)
*   `scikit-image` (for the SSIM comparison algorithm)
*   `rarfile` (for reading RAR/CBR files)

### External Dependencies
*   **UnRAR.exe**: The `rarfile` library requires the command-line UnRAR executable to read CBR archives.
    1. Download the command-line utility from [RARLAB](https://www.rarlab.com/rar_add.htm).
    2. Place `UnRAR.exe` in the same directory as the script, or add it to your Windows System PATH.

---

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/jgutierrezCSU/scanner-remover-comics
   ```

2. **Install dependencies**:
   ```bash
   pip install Pillow numpy scikit-image rarfile
   ```

3. **Verify UnRAR**: Place `UnRAR.exe` into the project directory.

---

## How to Use

1. **Launch the application**:
   ```bash
   python main_program.py
   ```
2. **Page Remover**:
   * Select the folder containing comics.
   * Select the folder containing target images (extracted reference logos).
   * Choose your page options (First, Last, etc.) and hit **START**.
3. **CBR to CBZ Converter**:
   * Select the folder, scan for `.cbr` files, and click **START CONVERSION**.
4. **Metadata Editor**:
   * Select a folder containing `.cbz` files.
   * Choose either **Add/Update** or **Remove** mode, and click **START METADATA PROCESSING**.

---

## Standalone Executable (EXE)

A compiled Windows executable is available for users who prefer a standalone application without setting up Python.

### [Download the Windows Executable](https://github.com/jgutierrezCSU/scanner-remover-comics/releases)

*Note: The executable version still requires `UnRAR.exe` to be present in the same directory to process `.cbr` files.*