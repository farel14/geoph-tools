# --- AUTH ---
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import gspread
import pandas as pd
import io
import os
import gspread.utils as utils
from oauth2client.service_account import ServiceAccountCredentials

# --- Authenticate for Sheets & Drive (local) ---
CREDS_PATH = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "service_account.json")
SCOPES = [
  "https://www.googleapis.com/auth/drive",
  "https://www.googleapis.com/auth/spreadsheets"
]

gc = gspread.service_account(filename=CREDS_PATH)

gauth = GoogleAuth()
gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDS_PATH, scopes=SCOPES)
drive = GoogleDrive(gauth)

check_row = None

# --- Helpers ---
def sanitize_cell_text(value: str) -> str:
  if value is None:
    return ""
  value = str(value).strip()
  if value[:1] in ("=", "+", "-", "@"):
    value = "'" + value
  return value[:500]

# === CONFIG ===
SPREADSHEET_NAME = "" # Spreadsheet name
SPREADSHEET_ID = "" # Spreadsheet ID
CHECK_COL = 1 #Column W

DRIVE_FOLDER_ID = None  # folder where index.xls is stored
PARENT_FOLDER_DRIVE_ID = "" # parent folder ID where the file is stored
TARGET_FOLDER_ID = "" # the target folder ID that needed to be sorted
SEARCH_CRITERIA = ["criteria1", "criteria2", "criteria2"] # list of criteria/keyword to check
WORKSHEET_NAME = "" # the name of the worksheet that needed to be updated
STRING_VALUE_WHEN_FOUND = ""
NAME_COLUMN_INDEX = 2
START_ROW_INDEX = 51
END_ROW_INDEX = 61

# === STEP 1: Open Sheet ===
spreadsheet = gc.open_by_key(SPREADSHEET_ID)
sheet = spreadsheet.worksheet(WORKSHEET_NAME)

def search_filenames_in_index(name, force_fill=False, force_without_index=False):
  found_file_name = None

  # === STEP 2: Check cell ===
  criteria_name = sheet.find(name, in_column=2)
  check_row = criteria_name.row
  cell_value = sheet.cell(check_row, CHECK_COL).value

  if cell_value and force_fill == False:  # not empty → skip
      print("Cell is already filled, skipping...")
      return

  # === STEP 2.5: Find folder id ===
  query = f"'{PARENT_FOLDER_DRIVE_ID}' in parents and mimeType = 'application/vnd.google-apps.folder' and title contains '{name}' and trashed=false"
  folder_list = drive.ListFile({'q': query}).GetList()

  if folder_list:
      folder = folder_list[0]  # first match
      print(f"Found folder for well {folder['title']} ({folder['id']})")
      DRIVE_FOLDER_ID = folder['id']
  else:
      print("No matching folder found")
      return

  # Build regex pattern: "(keyword1|keyword2|anotherWord)"
  pattern = "|".join(SEARCH_CRITERIA)

  if force_without_index == False:
    # can be force to find files even without index file, or file not found in index file

    # === STEP 3: Find index.xls in Drive folder ===
    query = f"'{DRIVE_FOLDER_ID}' in parents and title = 'index.xls' and trashed=false"
    file_list = drive.ListFile({'q': query}).GetList()
    folder = drive.CreateFile({'id': DRIVE_FOLDER_ID})
    folder.FetchMetadata()

    if not file_list:
        print("index.xls not found, skipping...")
        return

    index_file = file_list[0]
    print(f"index.xls found: {index_file['title']}")

    # === STEP 4: Download index.xls ===
    index_file.GetContentFile("index.xls")  # <- this writes the file locally
    print(f"Downloaded index.xls: {index_file['title']}")

    # === STEP 5: Read Excel and search ===
    df = pd.read_excel("index.xls", header=None)

    if df.iloc[0].isnull().all():
        df.columns = df.iloc[1]   # set row 2 as headers
        df = df.drop([0,1])       # drop first two rows
    else:
        df.columns = df.iloc[0]   # set row 1 as headers
        df = df.drop([0])         # drop only first row


    # Search case-insensitive
    matches = df[df["Desc"].str.contains(pattern, case=False, na=False)]
    if matches.empty:
        print("No matching file found in index.xls, skipping...")
        return

    filename_to_find = matches.iloc[0]["File Name"]
    found_file_name = matches.iloc[0]["Barcode"]
    found_file_name_lower = found_file_name.lower()
  else:
    filename_to_find = None
    found_file_name = None
    found_file_name_lower = None

  # === STEP 6: Recursive search ===
  def search_file_recursive(folder_id, filename):
      query = f"'{folder_id}' in parents and trashed=false"
      files = drive.ListFile({'q': query}).GetList()
      for item in files:
          title_only, file_ext = os.path.splitext(item['title'])
          title_lower = title_only.lower()
          if item['mimeType'] == 'application/vnd.google-apps.folder':
              found = search_file_recursive(item['id'], filename)
              if found:
                  return found
          elif item['title'] == filename or any(term in title_lower for term in SEARCH_CRITERIA) or found_file_name_lower in title_lower:
              return item
      return None
  def search_file_recursive_without_index(folder_id):
      query = f"'{folder_id}' in parents and trashed=false"
      files = drive.ListFile({'q': query}).GetList()
      for item in files:
          title_only, file_ext = os.path.splitext(item['title'])
          title_lower = title_only.lower()
          if item['mimeType'] == 'application/vnd.google-apps.folder':
              found = search_file_recursive_without_index(item['id'])
              if found:
                  return found
          elif any(term in title_lower for term in SEARCH_CRITERIA):
              return item
      return None

  found_file = None
  if force_without_index == False:
    found_file = search_file_recursive(DRIVE_FOLDER_ID, filename_to_find)
  else:
    found_file = search_file_recursive_without_index(DRIVE_FOLDER_ID)

  if not found_file:
      print(f"{filename_to_find} not found in any subfolder, skipping...")
      return
  print('Found drive file', found_file)

  source_folder_id = found_file['parents'][0]['id']

  # === STEP 7: Copy to target folder ===
  copied_file = drive.CreateFile({
      'title': f"temp_{filename_to_find}",
      'parents': [{'id': TARGET_FOLDER_ID}]
  })
  found_file.GetContentFile("tempfile")  # download
  copied_file.SetContentFile("tempfile") # reupload
  copied_file.Upload()

  found_file_name, file_ext = os.path.splitext(found_file['title'])
  found_file.FetchMetadata()

  # === STEP 8: Rename copied file with source folder name ===
  source_folder = drive.CreateFile({'id': source_folder_id})
  source_folder.FetchMetadata()

  copied_file['title'] = f'{name.upper()}_{found_file_name}_MUDLOG{file_ext}'
  copied_file.Upload()

  print(f"New file saved as {copied_file['title']}")

  # # === STEP 9: Update sheet ===
  file_link = f"https://drive.google.com/file/d/{copied_file['id']}/view"
  cell_label = utils.rowcol_to_a1(check_row, CHECK_COL)
  print('Updating '+ cell_label)
  spreadsheet.batch_update({
      "requests": [
          {
              "updateCells": {
                  "rows": [
                      {
                          "values": [
                              {
                                  "userEnteredValue": {"stringValue": sanitize_cell_text(STRING_VALUE_WHEN_FOUND)}, # use sanitize_cell_text() to prevent formula injection
                                  "textFormatRuns": [
                                      {
                                          "startIndex": 0,
                                          "format": {"link": {"uri": file_link}}
                                      }
                                  ]
                              }
                          ]
                      }
                  ],
                  "fields": "userEnteredValue,textFormatRuns",
                  "start": {"sheetId": sheet.id, "rowIndex": check_row-1, "columnIndex": CHECK_COL-1}
              }
          }
      ]
  })
  print(f"Process completed successfully for {name}!")

## RUN HERE
if __name__ == "__main__":
  for cell in sheet.col_values(NAME_COLUMN_INDEX)[START_ROW_INDEX:END_ROW_INDEX]:
    print('Now running for well ', cell)
    search_filenames_in_index(cell, force_without_index=True)
    print('====================================================')

# search_filenames_in_index('report1', force_without_index=True)
