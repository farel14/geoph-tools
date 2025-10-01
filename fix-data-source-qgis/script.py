import os
import glob
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from qgis.core import QgsProject, QgsVectorLayer, QgsRasterLayer, QgsMapLayer

def get_all_file(root_folder):
    """
    Get all file in the root directory and subdirectories
    Returns dict: {file_name: full_path}
    """
    file_dict = {}
    
    for root, dirs, files in os.walk(root_folder):
        for file in files:
            full_path = os.path.join(root, file)
            # Store both the exact name and lowercase for flexible matching
            file_dict[file] = full_path
            file_dict[file.lower()] = full_path
    
    return file_dict

def fix_datasource_with_file_matching(correct_file_dict):
    """
    Main function to fix datasources using file matching logic
    """
    project = QgsProject.instance()
    layers = project.mapLayers().values()
    
    print(f"\n=== FIXING DATASOURCES WITH FILE MATCHING ===")
    fixed_count = 0
    not_found_count = 0
    already_valid_count = 0
    
    for layer in layers:
        layer_name = layer.name()
        current_source = layer.source()
        
        print(f"\n--- Processing: {layer_name} ---")
        print(f"Current source: {current_source}")
        
        # Check if layer is already valid
        if layer.isValid():
            print("Status: Already valid, skipping")
            already_valid_count += 1
            continue
        
        # Step 3: Extract subfolder from incorrect path
        if "|" in current_source:  # Handle sources with parameters
            file_part = current_source.split("|")[0]
            parameters = "|" + current_source.split("|", 1)[1]
        else:
            file_part = current_source
            parameters = ""
        
        # Normalize path to handle mixed separators
        file_part = os.path.normpath(file_part)
        original_filename = os.path.basename(file_part)        
        print(f"Original filename: {original_filename}")


        if original_filename not in correct_file_dict:
            print(f"File '{original_filename}' not found in matching subfolder")
            not_found_count += 1
            continue

        correct_file_path = correct_file_dict[original_filename]
        
        print(f"Found correct file: {correct_file_path}")
        
        # Step 6: Update the datasource
        new_source = correct_file_path + parameters
        layer.setDataSource(new_source, layer_name, layer.providerType())
        
        if layer.isValid():
            print(f"Successfully fixed datasource!")
            fixed_count += 1
        else:
            print(f"Failed to fix datasource")
            not_found_count += 1
    
    # Step 7: Summary (saving is manual)
    print(f"\n=== SUMMARY ===")
    print(f"Already valid layers: {already_valid_count}")
    print(f"Successfully fixed: {fixed_count}")
    print(f"Could not fix: {not_found_count}")
    print(f"Total layers processed: {len(layers)}")
    
    if fixed_count > 0:
        print(f"\nFixed {fixed_count} layers!")
        print("Don't forget to save your project to keep the changes!")
    
    return fixed_count, not_found_count

def main_file_matching():
    """
    Main interactive function
    """
    # Check if project is open
    project = QgsProject.instance()
    if not project.fileName():
        QMessageBox.information(None, "Info", "Please open a QGIS project first!")
        return
    
    print("Current project:", project.fileName())
    
    # Step 1: Select correct folder
    correct_folder_path = QFileDialog.getExistingDirectory(
        None, 
        "Select the CORRECT folder containing your data"
    )
    
    if not correct_folder_path:
        print("No folder selected.")
        return

   
    if not_found_count > 0:
        correct_file_dict = get_all_file(correct_folder_path)
        fix_datasource_with_file_matching(correct_file_dict)

# Run the main function
main_file_matching()