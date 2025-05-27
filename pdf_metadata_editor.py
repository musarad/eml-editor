from datetime import datetime, timezone, timedelta
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
    The PDF dates will be set to 10 hours before the provided datetime.
    
    Args:
        pdf_path (str): The path to the PDF file.
        new_datetime_obj (datetime): The email datetime - PDF dates will be 10 hours before this.
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

        # Subtract 10 hours from the email datetime for PDF creation/modification
        pdf_datetime = new_datetime_obj - timedelta(hours=10)
        pdf_date_str = _format_datetime_for_pdf_metadata(pdf_datetime)
        
        metadata['creationDate'] = pdf_date_str
        metadata['modDate'] = pdf_date_str
        
        doc.set_metadata(metadata)
        doc.saveIncr()  # Use saveIncr() instead of save() for metadata changes
        doc.close()
        print(f"SUCCESS: PyMuPDF successfully updated metadata for {pdf_path}")
        print(f"  Email date: {new_datetime_obj.strftime('%Y-%m-%d %H:%M:%S %z')}")
        print(f"  PDF dates: {pdf_datetime.strftime('%Y-%m-%d %H:%M:%S %z')} (10 hours earlier)")
        return True
    except Exception as e:
        print(f"ERROR: Failed to modify PDF metadata for {pdf_path} using PyMuPDF: {e}")
        return False

def clear_pdf_metadata(pdf_path: str, keep_dates: bool = False) -> bool:
    """
    Clears all metadata fields in a PDF file using PyMuPDF (fitz).
    
    Args:
        pdf_path (str): The path to the PDF file.
        keep_dates (bool): If True, keeps creation and modification dates.
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
        metadata = doc.metadata or {}
        
        # Create empty metadata dictionary
        empty_metadata = {
            'producer': '',
            'creator': '',
            'author': '',
            'title': '',
            'subject': '',
            'keywords': '',
            'trapped': ''
        }
        
        # If keeping dates, preserve them
        if keep_dates and metadata:
            empty_metadata['creationDate'] = metadata.get('creationDate', '')
            empty_metadata['modDate'] = metadata.get('modDate', '')
        else:
            empty_metadata['creationDate'] = ''
            empty_metadata['modDate'] = ''
        
        # Set all metadata fields
        doc.set_metadata(empty_metadata)
        doc.saveIncr()  # Use saveIncr() for metadata changes
        doc.close()
        
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