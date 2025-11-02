# Geoph-Tools

A collection of Python tools designed for geophysicists to streamline common workflows involving data extraction, file management, and GIS project maintenance.

## Tools Overview

This repository contains three main tools:

1. **PDF-to-CSV** - Extract tables from images/PDFs using OCR and convert to CSV format
2. **List Compiler** - Automated Google Drive file organization and Google Sheets integration
3. **Fix Data Source QGIS** - Repair broken data source paths in QGIS projects

---

## 📋 Table of Contents

- [PDF-to-CSV](#pdf-to-csv)
- [List Compiler](#list-compiler)
- [Fix Data Source QGIS](#fix-data-source-qgis)
- [Requirements](#requirements)
- [Installation](#installation)

---

## 📄 PDF-to-CSV

**Location:** `pdf-to-csv/`

An OCR-based tool that extracts tabular data from images and converts them to CSV format using docTR (Document Text Recognition). Perfect for digitizing tables from scanned documents, PDF pages, or screenshots.

### Features

- Extract tables from images (JPEG, PNG, BMP, TIFF)
- Automatic column and row detection
- Manual override for table dimensions
- Batch processing for multiple images
- Combine results from multiple images into a single CSV
- Uses state-of-the-art OCR models (docTR with ResNet50 + CRNN)

### Requirements

```bash
numpy>=1.26,<2.0
pandas>=2.0,<3.0
torch>=2.2,<3.0
python-doctr[torch]>=1.0.0
natsort>=8.0,<9.0
```

### Installation

```bash
cd pdf-to-csv
pip install -r requirements.txt
```

**Note:** The first run will download pre-trained OCR models (may take a few minutes and require several GB of disk space).

### Usage

#### Single Image Processing

```bash
# Basic usage (auto-detect table dimensions)
python script.py path/to/image.jpeg

# Specify table dimensions
python script.py path/to/image.jpeg --cols 3 --rows 10

# Custom output directory
python script.py path/to/image.jpeg --output-dir my_output
```

#### Batch Processing

```bash
# Process all images in a directory
python script.py ./images/ --batch

# Batch with specified dimensions
python script.py ./images/ --batch --cols 1 --rows 73

# Process individually without combining results
python script.py ./images/ --batch --no-combine
```

#### Python Module Usage

```python
from pdf_to_csv.script import read_img_to_csv, batch_process_images

# Single image
df = read_img_to_csv('sample.jpeg', n_cols=3, n_rows=10)

# Batch processing
result = batch_process_images('./images/', combine=True)
```

### Output

- Individual CSV files: `{image_name}_table.csv`
- Combined CSV (batch mode): `combined_results.csv`
- All outputs saved to `output/` directory by default

### Example

```bash
python script.py images/sample.jpeg --cols 2 --rows 5
```

Output:
```
Processing: sample.jpeg
Loading OCR model...
Performing OCR...
Detected 45 text elements
Inferred n_cols: 2
Inferred n_rows: 5
Building 5x2 table...
Table extracted and saved to: output/sample_table.csv
```

---

## 📂 List Compiler

**Location:** `list-compiler/`

An automation tool for managing files in Google Drive and updating Google Sheets. Designed to search for files matching specific criteria, organize them in target folders, and track progress in spreadsheets.

**⚠️ Note:** This tool is available in two versions:
- **Google Colab version** (`script collab.ipynb`) - **Recommended, easier to use!** No setup required, just open in Google Colab and run.
- **Python version** (`script.py`) - For local execution (requires authentication setup)

### Features

- Search files in Google Drive folders based on keywords/criteria
- Parse Excel index files (`index.xls`) to find matching files
- Recursively search subfolders
- Copy and rename files with standardized naming
- Update Google Sheets with file links and status
- Batch process multiple entries from a spreadsheet

---

### 🚀 Google Colab Version (Easier - Recommended)

The Colab version is simpler to use as it handles authentication automatically through your Google account.

**Usage:**
1. Open `script collab.ipynb` in [Google Colab](https://colab.research.google.com/)
2. Click "Runtime" → "Run all" or run cells individually
3. Follow the authentication prompts when mounting Google Drive
4. Edit configuration parameters at the top of the notebook
5. Run the search and results will be saved to a Google Sheet automatically

**Advantages:**
- No local setup required
- Automatic authentication via Google account
- No need for service account credentials
- Results automatically saved to Google Sheets
- Easy to share and collaborate

---

### 💻 Python Version (Local)

For users who prefer running the script locally or need more customization.

#### Requirements

```bash
pydrive2
gspread
pandas
oauth2client
```

#### Setup

1. **Google Cloud Setup:**
   - Create a Google Cloud Project
   - Enable Google Drive API and Google Sheets API
   - Create a Service Account
   - Download the service account JSON key file

2. **Authentication:**
   - Save your service account JSON key as `service_account.json` in the `list-compiler/` directory
   - Or set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to point to your credentials file

3. **Install Dependencies:**
   ```bash
   cd list-compiler
   pip install pydrive2 gspread pandas oauth2client openpyxl
   ```

#### Configuration

Edit the configuration variables in `script.py`:

```python
SPREADSHEET_NAME = ""  # Your Google Spreadsheet name
SPREADSHEET_ID = ""    # Your Google Spreadsheet ID
CHECK_COL = 1          # Column to update (1 = Column A)
PARENT_FOLDER_DRIVE_ID = ""  # Parent folder ID in Google Drive
TARGET_FOLDER_ID = ""        # Target folder for copied files
SEARCH_CRITERIA = ["criteria1", "criteria2"]  # Keywords to search
WORKSHEET_NAME = ""          # Worksheet name to update
STRING_VALUE_WHEN_FOUND = "" # Text to insert in spreadsheet
NAME_COLUMN_INDEX = 2        # Column containing names to process
START_ROW_INDEX = 51         # First row to process
END_ROW_INDEX = 61           # Last row to process
```

#### Usage

```bash
cd list-compiler
python script.py
```

The script will:
1. Read names from the specified column (rows 51-61 by default)
2. For each name:
   - Find corresponding folder in Google Drive
   - Search for `index.xls` file
   - Parse the index file for matching criteria
   - Recursively search for matching files
   - Copy files to target folder with renamed format: `{NAME}_{filename}_MUDLOG{ext}`
   - Update Google Sheet with file link

#### Options

- `force_fill=False`: Skip if cell is already filled
- `force_without_index=True`: Search files without requiring `index.xls`

#### Example Output

```
Now running for well: WELL-001
Found folder for well WELL-001 (abc123xyz...)
index.xls found: index.xls
Downloaded index.xls: index.xls
Found drive file {'id': '...', 'title': 'mudlog.pdf'}
New file saved as WELL-001_mudlog_MUDLOG.pdf
Updating A51
Process completed successfully for WELL-001!
====================================================
```

---

## 🗺️ Fix Data Source QGIS

**Location:** `fix-data-source-qgis/`

A QGIS Python script that automatically fixes broken data source paths in QGIS projects. When data files are moved or project paths change, this tool helps restore layer connections by matching filenames.

### Features

- Automatically detect broken layer data sources
- Match files by filename across directories
- Update layer paths while preserving layer properties
- Support for both vector and raster layers
- Interactive folder selection
- Detailed processing summary

### Requirements

```bash
PyQt5
qgis
```

**Note:** This script must be run within QGIS (Python Console or as a QGIS plugin).

### Setup

1. **QGIS Installation:**
   - Ensure QGIS is installed on your system
   - This script uses QGIS's Python environment

2. **Install PyQt5** (if not included with QGIS):
   ```bash
   pip install PyQt5
   ```

### Usage

#### Method 1: QGIS Python Console

1. Open QGIS
2. Open your QGIS project (even if layers are broken)
3. Go to **Plugins → Python Console**
4. Run the script:

```python
exec(open('/path/to/geoph-tools/fix-data-source-qgis/script.py').read())
```

#### Method 2: Copy to QGIS Script

1. Copy `script.py` to your QGIS scripts folder:
   - **Windows:** `C:/Users/[username]/.qgis2/python/`
   - **macOS:** `~/.qgis2/python/`
   - **Linux:** `~/.qgis2/python/`

2. In QGIS, go to **Plugins → Python Console**
3. Import and run:
   ```python
   import script
   script.main_file_matching()
   ```

### Workflow

1. **Open QGIS Project:** Load your project (layers may show as broken)
2. **Run Script:** Execute the script from Python Console
3. **Select Folder:** Choose the directory containing your correct data files
4. **Review Results:** Check the console output for processing summary
5. **Save Project:** Save your QGIS project to persist the fixes

### How It Works

1. Scans all layers in the current QGIS project
2. For each broken/invalid layer:
   - Extracts the original filename from the broken path
   - Recursively searches the selected folder for matching filename
   - Updates the layer's data source to the correct path
   - Preserves layer name, style, and other properties

### Example Output

```
=== FIXING DATASOURCES WITH FILE MATCHING ===

--- Processing: Well Locations ---
Current source: /old/path/wells.shp
Original filename: wells.shp
Found correct file: /new/path/data/wells.shp
Successfully fixed datasource!

--- Processing: Seismic Grid ---
Current source: /old/path/grid.tif
Original filename: grid.tif
Found correct file: /new/path/rasters/grid.tif
Successfully fixed datasource!

=== SUMMARY ===
Already valid layers: 5
Successfully fixed: 2
Could not fix: 0
Total layers processed: 7
```

### Notes

- The script preserves layer parameters (symbology, joins, etc.)
- It handles both vector (.shp, .geojson, etc.) and raster (.tif, .img, etc.) layers
- Files are matched by exact filename (case-sensitive)
- If multiple files with the same name exist, the first match is used

---

## 🔧 General Requirements

### Python Version

- Python 3.8 or higher recommended
- Some tools may require Python 3.9+ (check individual tool requirements)

### System Requirements

- **PDF-to-CSV:** Requires significant disk space (~2-3 GB) for PyTorch and docTR models
- **List Compiler:** Requires Google account with API access
- **Fix Data Source QGIS:** Requires QGIS installation

---

## 📦 Installation

### Install All Tools (if sharing common dependencies)

```bash
# Clone the repository
git clone <repository-url>
cd geoph-tools

# Install each tool's requirements individually
cd pdf-to-csv && pip install -r requirements.txt && cd ..
cd list-compiler && pip install pydrive2 gspread pandas oauth2client openpyxl && cd ..
```

### Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install tool-specific requirements as needed
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

[Add your license information here]

## 👤 Author

Created for geophysicists to streamline common data processing workflows.

---

## 📚 Additional Notes

- **PDF-to-CSV:** First run downloads models (~1-2 GB), subsequent runs are faster
- **List Compiler:** Ensure proper Google API permissions for Drive and Sheets access
- **Fix Data Source QGIS:** Always backup your QGIS project before running fixes

For issues or questions, please open an issue on the repository.
