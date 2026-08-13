import os
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import PyPDF2
import io

# Configure paths for Windows
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
poppler_path = r'C:\Program Files\poppler-25.12.0\Library\bin'

# If the above doesn't work, check inside your poppler folder
# and look for the directory containing pdftoppm.exe, then update the path above


def pdf_to_searchable(input_path, output_path, dpi=300):
    """
    Convert a non-searchable PDF to a searchable PDF using OCR.
    
    Args:
        input_path: Path to input PDF file
        output_path: Path to output searchable PDF file
        dpi: Resolution for image conversion (higher = better quality but slower)
    """
    try:
        print(f"Processing: {os.path.basename(input_path)}")
        
        # Convert PDF to images
        images = convert_from_path(input_path, dpi=dpi, poppler_path=poppler_path)
        
        # Create a PDF writer (Updated for modern PyPDF2 / pypdf)
        pdf_writer = PyPDF2.PdfWriter()
        
        # Process each page
        for i, image in enumerate(images):
            print(f"  OCR processing page {i+1}/{len(images)}...")
            
            # Perform OCR to get searchable PDF
            pdf_bytes = pytesseract.image_to_pdf_or_hocr(image, extension='pdf')
            
            # Read the PDF bytes (Updated for modern PyPDF2 / pypdf)
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            
            # Add page to writer (Updated syntax: add_page & pages[0])
            pdf_writer.add_page(pdf_reader.pages[0])
        
        # Write the output PDF
        with open(output_path, 'wb') as output_file:
            pdf_writer.write(output_file)
        
        print(f"✓ Completed: {os.path.basename(output_path)}")
        return True
        
    except Exception as e:
        print(f"✗ Error processing {os.path.basename(input_path)}: {str(e)}")
        return False


def process_folder(input_folder, output_folder, dpi=300):
    """
    Process all PDFs in input folder and save searchable versions to output folder.
    
    Args:
        input_folder: Path to folder containing input PDFs
        output_folder: Path to folder where searchable PDFs will be saved
        dpi: Resolution for image conversion
    """
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    # Get all PDF files from input folder
    pdf_files = [f for f in os.listdir(input_folder) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print("No PDF files found in input folder!")
        return
    
    print(f"Found {len(pdf_files)} PDF file(s) to process\n")
    
    success_count = 0
    fail_count = 0
    
    # Process each PDF
    for pdf_file in pdf_files:
        input_path = os.path.join(input_folder, pdf_file)
        output_path = os.path.join(output_folder, pdf_file)
        
        if pdf_to_searchable(input_path, output_path, dpi):
            success_count += 1
        else:
            fail_count += 1
        print()  # Empty line for readability
    
    # Summary
    print("="*50)
    print("Processing Complete!")
    print(f"Successfully processed: {success_count}")
    print(f"Failed: {fail_count}")
    print("="*50)


if __name__ == "__main__":
    # Set your input and output folder paths
    INPUT_FOLDER = "input"    # Change this to your input folder path
    OUTPUT_FOLDER = "output"  # Change this to your output folder path
    
    # Optional: Adjust DPI (higher = better quality but slower and larger files)
    DPI = 300  # 300 is good balance, use 150 for faster processing
    
    process_folder(INPUT_FOLDER, OUTPUT_FOLDER, DPI)