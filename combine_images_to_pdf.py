#!/usr/bin/env python3
"""
Combine images into a high-quality PDF
"""

import os
import sys
from PIL import Image
import img2pdf
from pathlib import Path

def combine_images_to_pdf(image_folder, output_pdf):
    """
    Combine all images in a folder into a high-quality PDF
    
    Args:
        image_folder (str): Path to folder containing images
        output_pdf (str): Path for output PDF file
    """
    
    # Get the folder path
    folder_path = Path(image_folder)
    
    if not folder_path.exists():
        print(f"[!] Error: Folder '{image_folder}' does not exist")
        return False
    
    # Get all image files and sort them
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif'}
    image_files = []
    
    for file_path in folder_path.iterdir():
        if file_path.suffix.lower() in image_extensions:
            image_files.append(file_path)
    
    # Sort files by numerical order (extract numbers from filename)
    def extract_number(filename):
        """Extract number from filename like 'page-001.jpg' -> 1"""
        import re
        match = re.search(r'page-(\d+)', filename, re.IGNORECASE)
        return int(match.group(1)) if match else 0
    
    image_files.sort(key=lambda x: extract_number(x.name))
    
    print(f"[+] Found {len(image_files)} images:")
    for i, img_file in enumerate(image_files, 1):
        print(f"    {i}. {img_file.name}")
    
    if not image_files:
        print("[!] No image files found in the folder")
        return False
    
    try:
        # Convert images to PDF
        print(f"\n[+] Converting images to PDF...")
        
        # Open images and get their sizes
        images = []
        for img_path in image_files:
            print(f"    Processing: {img_path.name}")
            
            # Open image
            img = Image.open(img_path)
            
            # Convert to RGB if necessary (for PDF compatibility)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Get image dimensions
            width, height = img.size
            print(f"        Size: {width}x{height}px")
            
            images.append(img)
        
        # Calculate optimal PDF page size (A4 at 300 DPI)
        # A4 size: 210mm x 297mm = 2480 x 3508 pixels at 300 DPI
        a4_width = 2480
        a4_height = 3508
        
        # Resize images to fit A4 while maintaining aspect ratio
        resized_images = []
        for i, img in enumerate(images):
            print(f"    Resizing: {image_files[i].name}")
            
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
            
            print(f"        Resized to: {new_width}x{new_height}px")
            print(f"        Positioned at: ({x_offset}, {y_offset})")
        
        # Save as PDF
        print(f"\n[+] Creating PDF: {output_pdf}")
        resized_images[0].save(
            output_pdf,
            save_all=True,
            append_images=resized_images[1:],
            quality=95,  # High quality
            optimize=True,
            dpi=(300, 300)  # High DPI for print quality
        )
        
        # Close all images
        for img in images:
            img.close()
        for img in resized_images:
            img.close()
        
        # Get file size
        pdf_size = os.path.getsize(output_pdf)
        size_mb = pdf_size / (1024 * 1024)
        
        print(f"[+] PDF created successfully!")
        print(f"    Output: {output_pdf}")
        print(f"    Pages: {len(image_files)}")
        print(f"    Size: {size_mb:.2f} MB")
        print(f"    Quality: HD (300 DPI)")
        
        return True
        
    except Exception as e:
        print(f"[!] Error creating PDF: {e}")
        return False

def main():
    """Main function"""
    
    # Define input and output paths
    image_folder = "class 5/Marathi - hasat gaat shikyua"
    output_pdf = "class 5/Marathi - hasat gaat shikyua.pdf"
    
    print("=" * 60)
    print("Image to PDF Converter")
    print("=" * 60)
    
    # Combine images to PDF
    success = combine_images_to_pdf(image_folder, output_pdf)
    
    if success:
        print("\n" + "=" * 60)
        print("CONVERSION COMPLETED SUCCESSFULLY!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("CONVERSION FAILED!")
        print("=" * 60)
        sys.exit(1)

if __name__ == "__main__":
    main()
