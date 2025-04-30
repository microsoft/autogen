#!/usr/bin/env python3
"""
Example demonstrating how to send a PDF file to OpenAI using the Media class hierarchy
and verifying that OpenAI can read the file content.
"""

import base64
import os
from pathlib import Path
import sys

from autogen_core import File
from openai import OpenAI

# A minimal valid PDF with text content as bytes
PDF_WITH_TEXT = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << >> >>
endobj
4 0 obj
<< /Length 68 >>
stream
BT
/F1 24 Tf
100 700 Td
(This is a test PDF for AutoGen Media class) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000010 00000 n
0000000059 00000 n
0000000118 00000 n
0000000217 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
335
%%EOF"""

def main():
    # Check for OpenAI API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
        print("Please set your OpenAI API key using:")
        print("  export OPENAI_API_KEY='your-api-key'")
        return 1
    
    # Create a PDF file
    pdf_path = Path("test_document.pdf")
    with open(pdf_path, "wb") as f:
        f.write(PDF_WITH_TEXT)
    
    try:
        print(f"Created test PDF at {pdf_path}")
        
        # Load the PDF as a File object
        file_obj = File.from_file(pdf_path)
        
        print(f"\nFile object created: {file_obj}")
        print(f"MIME type: {file_obj.mime_type}")
        print(f"Size: {len(file_obj.data)} bytes")
        
        # Get the OpenAI format
        openai_format = file_obj.to_openai_format()
        print(f"\nOpenAI format type: {openai_format['type']}")
        print(f"Format structure: {list(openai_format.keys())}")
        print(f"File structure: {list(openai_format['file'].keys())}")
        
        # Create OpenAI client and send the request with the PDF
        client = OpenAI(api_key=api_key)
        
        print("\nSending request to OpenAI with the PDF file...")
        response = client.chat.completions.create(
            model="gpt-4o",  # Using gpt-4o which supports file inputs
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What text can you read from this PDF file?"},
                        file_obj.to_openai_format()
                    ]
                }
            ]
        )
        
        # Print the response
        print("\n===== OpenAI Response =====")
        print(response.choices[0].message.content)
        print("===========================")
        
        print("\nPDF test completed successfully!")
        return 0
        
    except Exception as e:
        print(f"\nError: {e}")
        return 1
        
    finally:
        # Clean up
        if pdf_path.exists():
            pdf_path.unlink()
            print(f"\nRemoved temporary file: {pdf_path}")

if __name__ == "__main__":
    sys.exit(main())
