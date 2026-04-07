#!/usr/bin/env python3
"""
Batch combine images from multiple subfolders into individual PDFs,
then combine all PDFs into a single master PDF
"""

import os
import sys
from PIL import Image
from pathlib import Path
import PyPDF2
from PyPDF2 import PdfMerger
import re

def extract_number(filename):
    """Extract number from filename like 'page-001.jpg' -> 1"""
    match = re.search(r'page-(\d+)', filename, re.IGNORECASE)
    return int(match.group(1)) if match else 0

def process_folder_to_pdf(folder_path, output_path):
    """
    Process a folder: either combine images to PDF or combine existing PDFs
    
    Args:
        folder_path (Path): Path to folder containing images or PDFs
        output_path (Path): Path for output PDF file
    
    Returns:
        bool: Success status
    """
    
    if not folder_path.exists():
        print(f"[!] Error: Folder '{folder_path}' does not exist")
        return False
    
    # Check for existing PDF files first
    pdf_files = list(folder_path.glob("*.pdf"))
    pdf_files.sort(key=lambda x: extract_number(x.name) if extract_number(x.name) > 0 else x.name)
    
    if pdf_files:
        print(f"[+] Found {len(pdf_files)} existing PDF files in '{folder_path.name}':")
        for i, pdf_file in enumerate(pdf_files, 1):
            print(f"    {i}. {pdf_file.name}")
        
        return combine_multiple_pdfs(pdf_files, output_path)
    
    # If no PDFs, look for image files
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif'}
    image_files = []
    
    for file_path in folder_path.iterdir():
        if file_path.suffix.lower() in image_extensions:
            image_files.append(file_path)
    
    # Sort files by numerical order
    image_files.sort(key=lambda x: extract_number(x.name))
    
    if not image_files:
        print(f"[!] No image or PDF files found in '{folder_path.name}'")
        return False
    
    print(f"[+] Processing {len(image_files)} images in '{folder_path.name}':")
    for i, img_file in enumerate(image_files, 1):
        print(f"    {i}. {img_file.name}")
    
    try:
        # Convert images to PDF
        print(f"[+] Converting images to PDF...")
        
        # Open images and get their sizes
        images = []
        for img_path in image_files:
            print(f"    Processing: {img_path.name}")
            
            # Open image
            img = Image.open(img_path)
            
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            images.append(img)
        
        # Calculate optimal PDF page size (A4 at 300 DPI)
        a4_width = 2480
        a4_height = 3508
        
        # Resize images to fit A4 while maintaining aspect ratio
        resized_images = []
        for i, img in enumerate(images):
            # Calculate scaling to fit A4
            img_width, img_height = img.size
            scale_w = a4_width / img_width
            scale_h = a4_height / img_height
            scale = min(scale_w, scale_h)
            
            # Calculate new dimensions
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            
            # Resize image with high quality
            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Create A4 canvas and center the image
            a4_img = Image.new('RGB', (a4_width, a4_height), 'white')
            
            # Calculate position to center the image
            x_offset = (a4_width - new_width) // 2
            y_offset = (a4_height - new_height) // 2
            
            # Paste the resized image onto A4 canvas
            a4_img.paste(resized_img, (x_offset, y_offset))
            
            resized_images.append(a4_img)
        
        # Save as PDF
        resized_images[0].save(
            output_path,
            save_all=True,
            append_images=resized_images[1:],
            quality=95,
            optimize=True,
            dpi=(300, 300)
        )
        
        # Close all images
        for img in images:
            img.close()
        for img in resized_images:
            img.close()
        
        # Get file size
        pdf_size = output_path.stat().st_size
        size_mb = pdf_size / (1024 * 1024)
        
        print(f"[+] PDF created: {output_path.name} ({size_mb:.2f} MB, {len(image_files)} pages)")
        return True
        
    except Exception as e:
        print(f"[!] Error creating PDF for '{folder_path.name}': {e}")
        return False

def combine_multiple_pdfs(pdf_files, output_path):
    """
    Combine multiple PDF files into a single PDF
    
    Args:
        pdf_files (list): List of Path objects for PDF files
        output_path (Path): Path for output PDF file
    
    Returns:
        bool: Success status
    """
    
    if not pdf_files:
        print("[!] No PDF files to combine")
        return False
    
    try:
        print(f"[+] Combining {len(pdf_files)} PDFs into master PDF...")
        
        merger = PdfMerger()
        
        for pdf_file in pdf_files:
            print(f"    Adding: {pdf_file.name}")
            merger.append(str(pdf_file))
        
        merger.write(str(output_path))
        merger.close()
        
        # Get file size
        pdf_size = output_path.stat().st_size
        size_mb = pdf_size / (1024 * 1024)
        
        print(f"[+] Master PDF created: {output_path.name} ({size_mb:.2f} MB)")
        return True
        
    except Exception as e:
        print(f"[!] Error combining PDFs: {e}")
        return False

def main():
    """Main function"""
    
    # Define paths
    class5_folder = Path("class 5")
    
    if not class5_folder.exists():
        print(f"[!] Error: 'class 5' folder does not exist")
        sys.exit(1)
    
    print("=" * 80)
    print("Batch PDF Creator for Class 5 Materials")
    print("=" * 80)
    
    # Get all subfolders
    subfolders = [folder for folder in class5_folder.iterdir() if folder.is_dir()]
    subfolders.sort(key=lambda x: x.name)  # Sort alphabetically
    
    print(f"[+] Found {len(subfolders)} subfolders:")
    for i, folder in enumerate(subfolders, 1):
        print(f"    {i}. {folder.name}")
    
    if not subfolders:
        print("[!] No subfolders found")
        sys.exit(1)
    
    # Step 1: Create individual PDFs for each subfolder
    print(f"\n" + "=" * 40)
    print("STEP 1: Creating Individual PDFs")
    print("=" * 40)
    
    created_pdfs = []
    
    for subfolder in subfolders:
        print(f"\n[{subfolders.index(subfolder) + 1}/{len(subfolders)}] Processing: {subfolder.name}")
        print("-" * 50)
        
        # Define output PDF path
        pdf_name = f"{subfolder.name}.pdf"
        pdf_path = class5_folder / pdf_name
        
        # Create PDF from images or combine existing PDFs
        success = process_folder_to_pdf(subfolder, pdf_path)
        
        if success and pdf_path.exists():
            created_pdfs.append(pdf_path)
        else:
            print(f"[!] Failed to create PDF for '{subfolder.name}'")
    
    print(f"\n[+] Successfully created {len(created_pdfs)} individual PDFs:")
    for pdf in created_pdfs:
        size_mb = pdf.stat().st_size / (1024 * 1024)
        print(f"    - {pdf.name} ({size_mb:.2f} MB)")
    
    # Step 2: Combine all PDFs into master PDF
    print(f"\n" + "=" * 40)
    print("STEP 2: Creating Master PDF")
    print("=" * 40)
    
    if created_pdfs:
        master_pdf_path = class5_folder / "class5.pdf"
        
        # Sort PDFs by folder name for consistent order
        created_pdfs.sort(key=lambda x: x.name)
        
        success = combine_multiple_pdfs(created_pdfs, master_pdf_path)
        
        if success:
            # Get master PDF size
            master_size = master_pdf_path.stat().st_size
            master_size_mb = master_size / (1024 * 1024)
            
            print(f"\n" + "=" * 80)
            print("BATCH PROCESSING COMPLETED SUCCESSFULLY!")
            print("=" * 80)
            print(f"Individual PDFs: {len(created_pdfs)}")
            print(f"Master PDF: class5.pdf ({master_size_mb:.2f} MB)")
            print(f"Output folder: {class5_folder.absolute()}")
            print("=" * 80)
        else:
            print(f"\n[!] Failed to create master PDF")
            sys.exit(1)
    else:
        print("[!] No PDFs were created, cannot create master PDF")
        sys.exit(1)

if __name__ == "__main__":
    main()
