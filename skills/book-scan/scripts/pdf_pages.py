"""Print the page count of a PDF made by html2pdf (our own file, not the book).

    python pdf_pages.py <file.pdf>
"""
import sys

import pypdf

print(len(pypdf.PdfReader(sys.argv[1]).pages))
