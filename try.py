import os
from PyPDF2 import PdfReader, PdfWriter

def split_pdf(file_path, pages_per_split=15):
    # Load PDF file
    pdf = PdfReader(file_path)
    total_pages = len(pdf.pages)
    output_folder = os.path.splitext(file_path)[0] + '_splits'

    # Create output directory if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Split the PDF
    for start in range(0, total_pages, pages_per_split):
        end = min(start + pages_per_split, total_pages)
        pdf_writer = PdfWriter()

        # Add pages to the new PDF
        for page in range(start, end):
            pdf_writer.add_page(pdf.pages[page])

        # Write out the new PDF
        output_filename = os.path.join(output_folder, f'split_{start//pages_per_split + 1}.pdf')
        with open(output_filename, 'wb') as out:
            pdf_writer.write(out)

        print(f'Created: {output_filename}')

# Example usage
file_path = r"C:\Users\rparb\Downloads\Parbat_Singh_Rajpurohit (9).pdf"
split_pdf(file_path)
