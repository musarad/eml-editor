from datetime import datetime, timezone
import os

# Attempt to import fitz (PyMuPDF), but don't fail at import time if not available.
# The function will handle the case where it's not found.
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    fitz = None # To prevent NameError if accessed later when not available

def _format_datetime_for_pdf_metadata(dt_obj: datetime) -> str:
    """
    Formats a Python datetime object into a PDF date string (D:YYYYMMDDHHMMSSOHH\'mm\').
    Ensures the datetime object is timezone-aware.
    """
    if dt_obj.tzinfo is None or dt_obj.tzinfo.utcoffset(dt_obj) is None:
        # If naive, assume it's local time and make it offset-aware for PDF.
        # Alternatively, could convert to UTC: dt_obj = dt_obj.replace(tzinfo=timezone.utc).astimezone(timezone.utc)
        dt_aware = dt_obj.astimezone() # Converts naive to local-aware
    else:
        dt_aware = dt_obj

    offset_str = dt_aware.strftime("%z") # Gets +HHMM or -HHMM or empty if UTC and not explicit
    
    if not offset_str: # Handle UTC (Zulu time) explicitly if %z is empty
        pdf_dt_str = dt_aware.strftime("D:%Y%m%d%H%M%SZ00\'00\"")
    else:
        # Format for PDF: D:YYYYMMDDHHMMSS+HH'mm' or D:YYYYMMDDHHMMSS-HH'mm'
        pdf_dt_str = dt_aware.strftime(f"D:%Y%m%d%H%M%S{offset_str[:3]}\'{offset_str[3:]}\'")
    return pdf_dt_str

def set_pdf_metadata_dates(pdf_path: str, new_datetime_obj: datetime) -> bool:
    """
    Modifies the CreationDate and ModDate of a PDF file using PyMuPDF (fitz).
    Sets the PDF dates to 2 hours before the provided datetime (email date).
    
    Args:
        pdf_path (str): The path to the PDF file.
        new_datetime_obj (datetime): The email datetime - PDF dates will be set to 2 hours before this.
    Returns:
        bool: True if metadata was successfully updated (or if PyMuPDF is not available),
              False if an error occurred during PDF processing.
    """
    if not os.path.exists(pdf_path) or not pdf_path.lower().endswith('.pdf'):
        print(f"Error: PDF path does not exist or is not a PDF: {pdf_path}")
        return False

    if not PYMUPDF_AVAILABLE:
        print("Warning: PyMuPDF (fitz) library not found. PDF metadata will not be changed.")
        print("         To enable this feature, please install it: pip install PyMuPDF")
        return True # Return True to allow EML process to continue without PDF modification

    try:
        doc = fitz.open(pdf_path)
        metadata = doc.metadata
        if metadata is None:
            metadata = {} 

        # Import timedelta for date arithmetic
        from datetime import timedelta
        
        # Subtract 2 hours from the email date for PDF creation/modification times
        pdf_datetime = new_datetime_obj - timedelta(hours=2)
        pdf_date_str = _format_datetime_for_pdf_metadata(pdf_datetime)
        
        # Clear all metadata fields except dates
        metadata['producer'] = ''
        metadata['creator'] = ''
        metadata['author'] = ''
        metadata['title'] = ''
        metadata['subject'] = ''
        metadata['keywords'] = ''
        metadata['trapped'] = ''
        
        # Set the date fields
        metadata['creationDate'] = pdf_date_str
        metadata['modDate'] = pdf_date_str
        
        doc.set_metadata(metadata)
        
        # Save to a temporary file first
        import tempfile
        temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf')
        os.close(temp_fd)
        
        doc.save(temp_path)
        doc.close()
        
        # Replace original with modified version
        import shutil
        shutil.move(temp_path, pdf_path)
        
        print(f"SUCCESS: PyMuPDF successfully updated metadata for {pdf_path}")
        print(f"  Email date: {new_datetime_obj.strftime('%Y-%m-%d %H:%M:%S %z')}")
        print(f"  PDF dates set to: {pdf_datetime.strftime('%Y-%m-%d %H:%M:%S %z')} (2 hours earlier)")
        return True
    except Exception as e:
        print(f"ERROR: Failed to modify PDF metadata for {pdf_path} using PyMuPDF: {e}")
        return False

def clear_pdf_metadata(pdf_path: str) -> bool:
    """
    Clears all metadata fields in a PDF file using PyMuPDF (fitz).
    
    Args:
        pdf_path (str): The path to the PDF file.
    Returns:
        bool: True if metadata was successfully cleared,
              False if an error occurred during PDF processing.
    """
    if not os.path.exists(pdf_path) or not pdf_path.lower().endswith('.pdf'):
        print(f"Error: PDF path does not exist or is not a PDF: {pdf_path}")
        return False

    if not PYMUPDF_AVAILABLE:
        print("Warning: PyMuPDF (fitz) library not found. PDF metadata will not be changed.")
        print("         To enable this feature, please install it: pip install PyMuPDF")
        return True

    try:
        doc = fitz.open(pdf_path)
        
        # Create empty metadata dictionary - all fields set to empty strings
        empty_metadata = {
            'producer': '',
            'creator': '',
            'author': '',
            'title': '',
            'subject': '',
            'keywords': '',
            'creationDate': '',
            'modDate': '',
            'trapped': ''
        }
        
        # Set all metadata fields to empty strings
        doc.set_metadata(empty_metadata)
        
        # Save to a temporary file first
        import tempfile
        temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf')
        os.close(temp_fd)
        
        # Save with garbage=4 to remove unused objects and clean the file
        doc.save(temp_path, garbage=4, deflate=True)
        doc.close()
        
        # Now open the saved file again and clear metadata that might have been added during save
        doc2 = fitz.open(temp_path)
        doc2.set_metadata(empty_metadata)
        
        # Save again to final location
        temp_fd2, temp_path2 = tempfile.mkstemp(suffix='.pdf')
        os.close(temp_fd2)
        doc2.save(temp_path2, garbage=4, deflate=True)
        doc2.close()
        
        # Replace original with modified version
        import shutil
        shutil.move(temp_path2, pdf_path)
        
        # Clean up first temp file
        os.remove(temp_path)
        
        print(f"SUCCESS: Cleared all metadata for {pdf_path}")
        return True
    except Exception as e:
        print(f"ERROR: Failed to clear PDF metadata for {pdf_path}: {e}")
        return False

if __name__ == '__main__':
    if not PYMUPDF_AVAILABLE:
        print("PyMuPDF (fitz) is not installed. Example usage for PDF modification cannot run fully.")
        print("Please install it using: pip install PyMuPDF")
    
    # Create a dummy test.pdf for example usage if it doesn't exist
    # and PyMuPDF is available
    if PYMUPDF_AVAILABLE and not os.path.exists("test.pdf"):
        try:
            doc = fitz.open() # create a new empty PDF
            page = doc.new_page()
            doc.save("test.pdf")
            print("Created a dummy test.pdf for example.")
            doc.close()
        except Exception as e_create:
            print(f"Could not create dummy test.pdf for example: {e_create}")

    if os.path.exists("test.pdf"):
        print("\nRunning example usage of set_pdf_metadata_dates...")
        now = datetime.now()
        aware_now = now.astimezone()
        print(f"\nSetting date to now (local): {aware_now.isoformat()}")
        success = set_pdf_metadata_dates("test.pdf", aware_now)
        print(f"Operation successful: {success}")
        
        specific_dt = datetime(2020, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        print(f"\nSetting date to specific UTC: {specific_dt.isoformat()}")
        success_specific = set_pdf_metadata_dates("test.pdf", specific_dt)
        print(f"Operation successful: {success_specific}")
        
        # To verify, you would typically open test.pdf in a PDF reader and check its properties.
        if PYMUPDF_AVAILABLE and success_specific: # Check metadata of the last operation
            try:
                doc = fitz.open("test.pdf")
                print("\nVerifying metadata in test.pdf:")
                print(f"  CreationDate: {doc.metadata.get('creationDate')}")
                print(f"  ModDate: {doc.metadata.get('modDate')}")
                doc.close()
            except Exception as e_verify:
                print(f"Could not verify metadata: {e_verify}")
    else:
        print("test.pdf not found. Skipping example usage.") 