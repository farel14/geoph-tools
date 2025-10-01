#!/usr/bin/env python3
"""
OCR Table Extractor
Converts images containing tables to CSV format using docTR OCR
"""

import numpy as np
import pandas as pd
from doctr.io import DocumentFile
from doctr.models import ocr_predictor
from pathlib import Path
import argparse
import sys

def read_img_to_csv(input_file, n_cols=None, n_rows=None, predictor=None, output_dir=None):
    """
    Extract table from image and save as CSV
    
    Args:
        input_file (str): Path to input image file
        n_cols (int, optional): Number of columns in table. If None, will try to infer
        n_rows (int, optional): Number of rows in table. If None, will try to infer
        predictor (object, optional): Pre-loaded OCR predictor. If None, will load default
        output_dir (str, optional): Output directory. Defaults to 'output'
    
    Returns:
        pd.DataFrame: Extracted table as DataFrame, or None if extraction failed
    """
    # File path handling
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"Error: Input file '{input_file}' not found")
        return None
    
    filename = input_path.name
    name_only = input_path.stem
    ext = input_path.suffix
    
    # Output directory setup
    if output_dir is None:
        output_dir = "output"
    output_folder = Path(output_dir)
    output_folder.mkdir(exist_ok=True)
    output_file = output_folder / f"{name_only}_table.csv"
    
    print(f"Processing: {filename}")
    
    # Load OCR model if not provided
    if not predictor:
        print("Loading OCR model...")
        predictor = ocr_predictor("db_resnet50", "crnn_vgg16_bn", pretrained=True)
    
    try:
        # Load image and perform OCR
        print("Performing OCR...")
        doc = DocumentFile.from_images(str(input_path))
        result = predictor(doc)
        
        # Export result as dict
        blocks = result.export()["pages"][0]["blocks"]
        
        # Flatten into a list of (text, x, y, w, h)
        items = []
        for block in blocks:
            for line in block["lines"]:
                for word in line["words"]:
                    (x0, y0), (x1, y1) = word["geometry"]
                    text = word["value"]
                    items.append((text, x0, y0, x1 - x0, y1 - y0))
        
        if not items:
            print("No text detected in image")
            return None
        
        df = pd.DataFrame(items, columns=["text", "x", "y", "w", "h"])
        print(f"Detected {len(df)} text elements")
        
        # Infer number of columns if not provided
        if n_cols is None:
            x_coords = sorted(df['x'].unique())
            tolerance = 0.02  # slightly increased tolerance for better clustering
            distinct_x = []
            if x_coords:
                distinct_x.append(x_coords[0])
                for x in x_coords[1:]:
                    if all(abs(x - dx) > tolerance for dx in distinct_x):
                        distinct_x.append(x)
            n_cols = len(distinct_x) if distinct_x else 1
            print(f"Inferred n_cols: {n_cols}")
        
        # Ensure we have at least 1 column
        n_cols = max(1, n_cols or 1)
        
        # Snap to Fixed Columns
        x_min, x_max = df["x"].min(), df["x"].max()
        col_width = (x_max - x_min) / n_cols if n_cols > 1 else 1
        
        def assign_col(x):
            if n_cols == 1:
                return 0
            col = int((x - x_min) / col_width)
            return min(col, n_cols - 1)  # keep inside bounds
        
        df["col"] = df["x"].apply(assign_col)
        
        # Infer number of rows if not provided
        if n_rows is None:
            y_coords = sorted(df['y'].unique())
            tolerance = 0.02  # slightly increased tolerance for better clustering
            distinct_y = []
            if y_coords:
                distinct_y.append(y_coords[0])
                for y in y_coords[1:]:
                    if all(abs(y - dy) > tolerance for dy in distinct_y):
                        distinct_y.append(y)
            n_rows = len(distinct_y) if distinct_y else 1
            print(f"Inferred n_rows: {n_rows}")
        
        # Ensure we have at least 1 row
        n_rows = max(1, n_rows or 1)
        
        # Assign rows based on y-coordinates
        y_min, y_max = df["y"].min(), df["y"].max()
        row_height = (y_max - y_min) / n_rows if n_rows > 1 else 1
        
        def assign_row(y):
            if n_rows == 1:
                return 0
            row = int((y - y_min) / row_height)
            return min(row, n_rows - 1)  # keep inside bounds
        
        df["row"] = df["y"].apply(assign_row)
        
        # Always build table (we now guarantee n_rows and n_cols are at least 1)
        print(f"Building {n_rows}x{n_cols} table...")
        
        # Initialize empty table
        table = [[""] * n_cols for _ in range(n_rows)]
        
        # Fill table with text
        for _, word in df.iterrows():
            row_idx = min(word.get("row", 0), n_rows - 1)
            col_idx = min(word.get("col", 0), n_cols - 1)
            
            if 0 <= row_idx < len(table) and 0 <= col_idx < len(table[row_idx]):
                # Concatenate if cell already has text
                if table[row_idx][col_idx]:
                    table[row_idx][col_idx] += " " + word["text"]
                else:
                    table[row_idx][col_idx] = word["text"]
        
        # If table seems too sparse, try a fallback approach
        empty_cells = sum(1 for row in table for cell in row if not cell.strip())
        total_cells = n_rows * n_cols
        sparsity = empty_cells / total_cells if total_cells > 0 else 1
        
        if sparsity > 0.7:  # If more than 70% of cells are empty, try simpler approach
            print(f"Table seems sparse ({sparsity:.1%} empty cells), trying fallback approach...")
            
            # Fallback: Create a single column table with all text sorted by position
            df_sorted = df.sort_values(['y', 'x'])  # Sort by row then column
            fallback_table = [[text] for text in df_sorted['text'].tolist()]
            table_df = pd.DataFrame(fallback_table, columns=['text'])
            
            print(f"Created single-column table with {len(fallback_table)} entries")
        else:
            # Create DataFrame from table
            table_df = pd.DataFrame(table)
        
        # Save to CSV
        table_df.to_csv(output_file, index=False, header=False)
        print(f"Table extracted and saved to: {output_file}")
        print(f"\nTable dimensions: {table_df.shape[0]} rows x {table_df.shape[1]} columns")
        print("\nPreview (first 5 rows):")
        print(table_df.head(5))
        
        return table_df
            
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        return None


def batch_process_images(input_dir, n_cols=None, n_rows=None, output_dir="output", combine=True):
    """
    Process multiple images in a directory and optionally combine results
    
    Args:
        input_dir (str): Directory containing images to process
        n_cols (int, optional): Number of columns
        n_rows (int, optional): Number of rows  
        output_dir (str): Output directory
        combine (bool): Whether to combine all results into one CSV
        
    Returns:
        pd.DataFrame or list: Combined DataFrame if combine=True, else list of DataFrames
    """
    import glob
    import natsort
    
    input_path = Path(input_dir)
    if not input_path.exists():
        print(f"Error: Input directory '{input_dir}' not found")
        return None
        
    # Find all image files
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff', '*.tif']
    image_files = []
    for ext in image_extensions:
        image_files.extend(glob.glob(str(input_path / ext)))
        image_files.extend(glob.glob(str(input_path / ext.upper())))
    
    if not image_files:
        print(f"No image files found in '{input_dir}'")
        return None
    
    # Sort files naturally
    image_files = natsort.natsorted(image_files)
    print(f"Found {len(image_files)} image files")
    
    # Load OCR model once for all images
    print("Loading OCR model...")
    predictor = ocr_predictor("db_resnet50", "crnn_vgg16_bn", pretrained=True)
    
    # Process each image
    df_list = []
    for i, file_path in enumerate(image_files, 1):
        print(f"\nProcessing {i}/{len(image_files)}: {Path(file_path).name}")
        
        df = read_img_to_csv(
            input_file=file_path,
            n_cols=n_cols,
            n_rows=n_rows,
            predictor=predictor,
            output_dir=output_dir
        )
        
        if df is not None:
            df_list.append(df)
        else:
            print(f"Skipped {Path(file_path).name} due to processing error")
    
    if not df_list:
        print("No images were successfully processed")
        return None
    
    if combine:
        print(f"\nCombining {len(df_list)} tables...")
        combined_df = pd.concat(df_list, ignore_index=True)
        
        # Save combined CSV
        output_path = Path(output_dir) / 'combined_results.csv'
        combined_df.to_csv(output_path, index=False, header=False)
        
        print(f"Combined results saved to: {output_path}")
        print(f"Final table: {combined_df.shape[0]} rows x {combined_df.shape[1]} columns")
        
        return combined_df
    else:
        print(f"Processed {len(df_list)} images individually")
        return df_list


def main():
    """Command line interface for the OCR table extractor"""
    parser = argparse.ArgumentParser(
        description="Extract tables from images using OCR",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single image
  python -m pdf-to-csv sample.jpeg
  python pdf-to-csv.py sample.jpeg --cols 3 --rows 10
  
  # Batch process directory
  python pdf-to-csv.py ./images/ --batch
  python pdf-to-csv.py ./images/ --batch --cols 1 --rows 73
  python pdf-to-csv.py ./images/ --batch --no-combine
        """
    )
    
    parser.add_argument("input", help="Path to input image file or directory (use --batch for directory)")
    parser.add_argument("--batch", action="store_true", help="Process all images in the input directory")
    parser.add_argument("--cols", "-c", type=int, help="Number of columns (will infer if not specified)")
    parser.add_argument("--rows", "-r", type=int, help="Number of rows (will infer if not specified)")
    parser.add_argument("--output-dir", "-o", default="output", help="Output directory (default: output)")
    parser.add_argument("--no-combine", action="store_true", help="Don't combine batch results into single CSV")
    
    args = parser.parse_args()
    
    if args.batch:
        # Batch processing mode
        result = batch_process_images(
            input_dir=args.input,
            n_cols=args.cols,
            n_rows=args.rows,
            output_dir=args.output_dir,
            combine=not args.no_combine
        )
        
        if result is not None:
            print("Batch processing completed successfully!")
        else:
            print("Batch processing failed!")
            sys.exit(1)
    else:
        # Single file processing mode
        if not Path(args.input).exists():
            print(f"Error: Input file '{args.input}' not found")
            sys.exit(1)
        
        # Load OCR model once
        print("Initializing OCR model...")
        predictor = ocr_predictor("db_resnet50", "crnn_vgg16_bn", pretrained=True)
        
        # Process the image
        result = read_img_to_csv(
            input_file=args.input,
            n_cols=args.cols,
            n_rows=args.rows,
            predictor=predictor,
            output_dir=args.output_dir
        )
        
        if result is not None:
            print("Processing completed successfully!")
        else:
            print("Processing failed!")
            sys.exit(1)


if __name__ == "__main__":
    main()