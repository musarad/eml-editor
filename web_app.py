#!/usr/bin/env python3
"""
EML Editor Web Application
A web-based panel for modifying EML files
"""

from flask import Flask, render_template, request, send_file, flash, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
import os
import tempfile
import shutil
from datetime import datetime
import json
import traceback
import email.utils

# Import our EML tools
from eml_unified_tool import UnifiedEMLTool
from eml_advanced_editor import AdvancedEMLEditor

# Import the new PDF metadata editor
from pdf_metadata_editor import set_pdf_metadata_dates

# Try to import crypto modules
try:
    from eml_crypto_signer import EMLCryptoSigner, EMLCryptoEditor, setup_dkim_keys
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload and output directories
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_EXTENSIONS = {'eml', 'msg'}

for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def cleanup_old_files():
    """Clean up files older than 1 hour"""
    import time
    current_time = time.time()
    
    for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
        for filename in os.listdir(folder):
            filepath = os.path.join(folder, filename)
            if os.path.isfile(filepath):
                if current_time - os.path.getctime(filepath) > 3600:  # 1 hour
                    try:
                        os.remove(filepath)
                    except:
                        pass


@app.route('/')
def index():
    """Main page with upload form"""
    cleanup_old_files()
    return render_template('index.html', crypto_available=CRYPTO_AVAILABLE)


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and display modification form"""
    if 'file' not in request.files:
        flash('No file selected')
        return redirect(url_for('index'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No file selected')
        return redirect(url_for('index'))
    
    if file and allowed_file(file.filename):
        # Save uploaded file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        try:
            # Load and analyze the email
            tool = UnifiedEMLTool(filepath)
            email_info = tool.extract_email_info()
            
            # Prepare data for template
            current_date = email_info['headers'].get('Date', '')
            current_from = email_info['headers'].get('From', '')
            current_to = email_info['headers'].get('To', '')
            current_subject = email_info['headers'].get('Subject', '')
            current_body = email_info['body_info']['content']
            current_body_type = email_info['body_info']['type'] or 'text/plain' # Default to plain if none
            attachments = email_info['attachments']
            
            return render_template('modify.html',
                                 filename=unique_filename,
                                 current_date=current_date,
                                 current_from=current_from,
                                 current_to=current_to,
                                 current_subject=current_subject,
                                 current_body=current_body,
                                 current_body_type=current_body_type,
                                 attachments=attachments,
                                 crypto_available=CRYPTO_AVAILABLE)
        
        except Exception as e:
            flash(f'Error loading EML file: {str(e)}')
            os.remove(filepath)
            return redirect(url_for('index'))
    
    flash('Invalid file type. Please upload an EML file.')
    return redirect(url_for('index'))


@app.route('/process', methods=['POST'])
def process_email():
    """Process the email with modifications"""
    try:
        # Get form data
        filename = request.form.get('filename')
        new_date_str_from_form = request.form.get('new_date', '').strip()
        new_from = request.form.get('new_from', '').strip()
        new_to = request.form.get('new_to', '').strip()
        new_subject = request.form.get('new_subject', '').strip()
        new_body = request.form.get('new_body', '').strip()
        use_crypto = request.form.get('use_crypto') == 'on'
        is_new_email = request.form.get('is_new_email') == 'on'
        
        # NEW: Get realistic mode setting (default to True for safety)
        realistic_mode = request.form.get('realistic_mode', 'on') == 'on'
        legacy_mode = request.form.get('legacy_mode') == 'on'
        
        # If legacy mode is explicitly selected, disable realistic mode
        if legacy_mode:
            realistic_mode = False

        # NEW: Get preservation setting
        preserve_signatures = request.form.get('preserve_signatures') == 'on'
        
        # NEW: Get X-header mode
        x_header_mode = request.form.get('x_header_mode', 'preserve')
        align_x_headers = (x_header_mode == 'align')
        
        # Get original values from hidden fields to check for actual changes
        original_from = request.form.get('original_from', '').strip()
        original_to = request.form.get('original_to', '').strip()
        original_subject = request.form.get('original_subject', '').strip()
        original_date_header = request.form.get('original_date_header', '').strip()
        # current_body_type is also available: request.form.get('current_body_type')
        
        # Load the original email
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        tool = UnifiedEMLTool(filepath)
        
        # Build modifications
        modifications = {}
        
        new_datetime_obj_for_eml = None # For PDF date sync
        # Date modification - only if a new date is actually provided
        if new_date_str_from_form:
            try:
                # Consistent parsing for the EML date itself
                new_datetime_obj_for_eml = datetime.strptime(new_date_str_from_form, "%Y-%m-%dT%H:%M")
                # Make it timezone-aware (local timezone) for consistency before formatting for EML
                if new_datetime_obj_for_eml.tzinfo is None or new_datetime_obj_for_eml.tzinfo.utcoffset(new_datetime_obj_for_eml) is None:
                    new_datetime_obj_for_eml = new_datetime_obj_for_eml.astimezone()

                formatted_date_for_eml = new_datetime_obj_for_eml.strftime("%a, %d %b %Y %H:%M:%S %z").strip()
                if not formatted_date_for_eml.endswith(('+0000', '-0000')) and len(formatted_date_for_eml.split()[-1]) != 5 : # crude check for missing tz
                     formatted_date_for_eml = email.utils.formatdate(new_datetime_obj_for_eml.timestamp(), localtime=True)
                modifications['date'] = formatted_date_for_eml
            except Exception as e_date_parse:
                print(f"Warning: Could not parse date '{new_date_str_from_form}' for EML, keeping original. Error: {e_date_parse}")
                new_datetime_obj_for_eml = None 
        else:
            # If no new date string from form, try to parse the original date header for PDF sync
            if original_date_header:
                try:
                    new_datetime_obj_for_eml = email.utils.parsedate_to_datetime(original_date_header)
                    if new_datetime_obj_for_eml.tzinfo is None or new_datetime_obj_for_eml.tzinfo.utcoffset(new_datetime_obj_for_eml) is None:
                        new_datetime_obj_for_eml = new_datetime_obj_for_eml.astimezone()
                except Exception as e_orig_date_parse:
                    print(f"Warning: Could not parse original_date_header '{original_date_header}' for PDF sync. Error: {e_orig_date_parse}")
                    new_datetime_obj_for_eml = None # Ensure it's None if parsing fails

        
        # Get attachment operations
        remove_attachments = request.form.getlist('remove_attachments')
        
        # Handle file uploads for new attachments
        new_attachments = []
        if 'new_attachments' in request.files:
            files = request.files.getlist('new_attachments')
            for file in files:
                if file and file.filename:
                    # Save new attachment temporarily
                    att_filename = secure_filename(file.filename)
                    att_path = os.path.join(app.config['UPLOAD_FOLDER'], f"att_{att_filename}")
                    file.save(att_path)
                    
                    # If a new date was successfully parsed for the EML, try to set it for the PDF
                    if new_datetime_obj_for_eml and att_filename.lower().endswith('.pdf'):
                        print(f"Attempting to update metadata for PDF: {att_filename}")
                        if not set_pdf_metadata_dates(att_path, new_datetime_obj_for_eml):
                            # Handle PDF metadata update failure if necessary, e.g., flash a warning
                            print(f"Warning: Failed to update metadata for PDF: {att_filename}")
                            # Decide if you want to proceed attaching the PDF with old metadata or skip it
                    
                    new_attachments.append(att_path)
        
        # Header modifications
        headers = {}
        if new_from and new_from != original_from:
            headers['From'] = new_from
        if new_to and new_to != original_to:
            headers['To'] = new_to
        if new_subject and new_subject != original_subject:
            headers['Subject'] = new_subject
        
        if headers:
            modifications['headers'] = headers
        
        # Body modification
        if new_body:
            modifications['body'] = new_body
        
        # Attachment modifications
        if remove_attachments or new_attachments:
            modifications['attachments'] = {}
            
            if remove_attachments:
                modifications['attachments']['remove'] = remove_attachments
            
            if new_attachments:
                modifications['attachments']['add'] = new_attachments
        
        # Apply modifications
        tool.modifications = modifications
        
        # Generate output filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_name = os.path.splitext(os.path.basename(filename))[0]
        mode_suffix = 'realistic' if realistic_mode else 'legacy'
        output_filename = f"{base_name}_{mode_suffix}_{timestamp}.eml"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        
        # Ensure output directory exists
        os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
        
        # Apply modifications with preserve_signatures support
        if realistic_mode and preserve_signatures and not use_crypto:
            # Preserve original signatures in realistic mode
            preserved = tool.editor.preserve_original_signatures()
            tool.apply_modifications(output_path, use_crypto=use_crypto, 
                                   is_new_email=is_new_email, 
                                   realistic_mode=realistic_mode,
                                   align_x_headers=align_x_headers)
            # Signatures are restored within apply_modifications when appropriate
        else:
            tool.apply_modifications(output_path, use_crypto=use_crypto, 
                                   is_new_email=is_new_email, 
                                   realistic_mode=realistic_mode,
                                   align_x_headers=align_x_headers)
        
        # Clean up temporary attachment files
        for att_path in new_attachments:
            if os.path.exists(att_path):
                os.remove(att_path)
        
        # Get validation results for user feedback
        validation = tool.editor.validate_authentication_consistency()
        validation_warnings = validation.get('warnings', [])
        
        # Return success with download link and validation info
        return jsonify({
            'success': True,
            'download_url': url_for('download_file', filename=output_filename),
            'filename': output_filename,
            'realistic_mode': realistic_mode,
            'validation_warnings': validation_warnings,
            'crypto_used': use_crypto and CRYPTO_AVAILABLE
        })
    
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/download/<filename>')
def download_file(filename):
    """Download the modified EML file"""
    filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=filename)
    else:
        flash('File not found')
        return redirect(url_for('index'))


@app.route('/api/parse-date', methods=['POST'])
def parse_date():
    """API endpoint to parse and format date"""
    try:
        date_str = request.json.get('date', '')
        # Try to parse the date
        parsed_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        formatted_date = parsed_date.strftime("%a, %d %b %Y %H:%M:%S +0000")
        return jsonify({
            'success': True,
            'formatted': formatted_date
        })
    except:
        return jsonify({
            'success': False,
            'error': 'Invalid date format'
        })


if __name__ == '__main__':
    print("🌐 Starting EML Editor Web Panel...")
    print(f"📁 Upload folder: {UPLOAD_FOLDER}")
    print(f"📁 Output folder: {OUTPUT_FOLDER}")
    print(f"🔐 Crypto features: {'Available' if CRYPTO_AVAILABLE else 'Not available'}")
    print("\n🚀 Server starting at http://localhost:8080")
    
    app.run(debug=True, host='0.0.0.0', port=8080) 