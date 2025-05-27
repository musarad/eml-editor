#!/usr/bin/env python3
"""
EML File Editor - Modify email files including headers, dates, and attachments
"""

import email
import email.utils
import email.mime.multipart
import email.mime.text
import email.mime.base
import email.mime.image
import email.mime.audio
import email.mime.application
from email.header import Header, decode_header
from email.encoders import encode_base64
import mimetypes
import os
import sys
import argparse
from datetime import datetime, timezone
import re
import base64
import hashlib
import json
from typing import Dict, List, Optional, Any
import copy
from email.utils import parseaddr, formataddr


class EMLEditor:
    """Class for editing EML files"""
    
    def __init__(self, eml_path: str):
        """Initialize with an EML file path"""
        self.eml_path = eml_path
        self.msg = None
        self.load_eml()
    
    def load_eml(self):
        """Load the EML file"""
        with open(self.eml_path, 'rb') as f:
            self.msg = email.message_from_bytes(f.read())
    
    def save_eml(self, output_path: str):
        """Save the modified EML file"""
        if self.msg.is_multipart():
            # Delete boundary from main Content-Type to force regeneration
            if 'boundary' in self.msg.get_params(header='Content-Type'):
                self.msg.del_param('boundary', header='Content-Type')

            # Iterate through direct children. If a child is also multipart, regenerate its boundary.
            for part in self.msg.get_payload(): # get_payload() for direct children
                if isinstance(part, email.message.Message) and part.is_multipart():
                    if 'boundary' in part.get_params(header='Content-Type'):
                        part.del_param('boundary', header='Content-Type')
            
            # Clean up redundant MIME-Version headers in sub-parts
            for part in self.msg.walk(): # walk() for all descendants
                if part is not self.msg and 'MIME-Version' in part:
                    del part['MIME-Version']
            
            if 'MIME-Version' not in self.msg:
                self.msg['MIME-Version'] = '1.0'
        else:
            if 'MIME-Version' not in self.msg:
                self.msg['MIME-Version'] = '1.0'

        with open(output_path, 'wb') as f:
            f.write(self.msg.as_bytes())
    
    def modify_date(self, new_date_input_str: str):
        """
        Modify the date in the email.
        The input new_date_input_str can be in various common formats.
        It will be converted to RFC 2822 format for email headers.
        Example valid input: 'Tue, 23 May 2017 14:59:31 +0430' or '2017-05-23 14:59:31'
        """
        parsed_dt_obj = None
        
        # Attempt 1: Use the standard email date parser (often the most robust for email date strings)
        try:
            parsed_dt_obj = email.utils.parsedate_to_datetime(new_date_input_str)
        except (TypeError, ValueError, AttributeError): # Catch potential errors from parsedate_to_datetime
            parsed_dt_obj = None # Ensure it's None if an error occurred

        # Attempt 2: If parsedate_to_datetime failed or returned None, try a common user format
        if parsed_dt_obj is None:
            try:
                # Try YYYY-MM-DD HH:MM:SS (stripping potential sub-second precision or 'T' separator)
                processed_input_str = new_date_input_str.replace('T', ' ').split('.')[0]
                parsed_dt_obj = datetime.strptime(processed_input_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass # strptime failed
        
        # Attempt 3: Try ISO format as another fallback if the above failed
        if parsed_dt_obj is None:
            try:
                # Handle Z for UTC explicitly for fromisoformat
                iso_input_str = new_date_input_str
                if iso_input_str.endswith('Z'):
                    iso_input_str = iso_input_str[:-1] + '+00:00'
                parsed_dt_obj = datetime.fromisoformat(iso_input_str)
            except ValueError:
                pass # fromisoformat failed

        if parsed_dt_obj is None:
            print(f"Failed to parse date string: '{new_date_input_str}' using all available methods.")
            return

        # Ensure the datetime object is timezone-aware for formatdate.
        # If it's naive, formatdate treats it as local time.
        # If it has tzinfo, formatdate uses it.
        if parsed_dt_obj.tzinfo is None or parsed_dt_obj.tzinfo.utcoffset(parsed_dt_obj) is None:
            # This makes it naive, and email.utils.formatdate will interpret it as local time.
            # For more explicit control, one might replace with a specific timezone if known, e.g., timezone.utc
            pass

        formatted_new_date_str = email.utils.formatdate(parsed_dt_obj.timestamp(), localtime=True)
        
        if 'Date' in self.msg:
            del self.msg['Date']
        self.msg['Date'] = formatted_new_date_str
        
        # Pass the parsed datetime object to modify_message_id if it was successfully parsed
        if parsed_dt_obj:
            self.modify_message_id(parsed_dt_obj=parsed_dt_obj)
        else:
            # If date couldn't be parsed for the Date header, 
            # modify_message_id will use current time or its existing logic
            self.modify_message_id()
        
        headers_to_scan_for_dates = ['Received', 'X-Received']
        
        for header_name in headers_to_scan_for_dates:
            existing_header_values = self.msg.get_all(header_name, [])
            if not existing_header_values:
                continue

            del self.msg[header_name] # Remove all existing headers of this type

            for header_value in existing_header_values:
                new_header_value = header_value # Default to original if not changed
                if ';' in header_value:
                    parts = header_value.rsplit(';', 1)
                    if len(parts) == 2:
                        header_body, old_date_part = parts
                        # Attempt to replace if old_date_part looks like a date component
                        # This is a heuristic. More advanced parsing could be added.
                        # Checking for presence of day, month, year words/numbers.
                        if re.search(r'(\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b.*?\d{1,2}\s+\w{3}\s+\d{4}|\d{1,2}\s+\w{3}\s+\d{4}.*\b(GMT|UT|UTC|EST|EDT|CST|CDT|MST|MDT|PST|PDT|[A-IK-Z])\b|\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', old_date_part, re.IGNORECASE):
                            new_header_value = f"{header_body.strip()}; {formatted_new_date_str}"
                self.msg.add_header(header_name, new_header_value)
    
    def modify_transport_headers(self, headers_dict: Dict[str, str]):
        """
        Modify transport and authentication headers
        Example: {'Delivered-To': 'newuser@example.com', 'Return-Path': '<sender@example.com>'}
        """
        for header_name, header_value in headers_dict.items():
            # Remove existing header(s)
            del self.msg[header_name]
            # Add new header
            self.msg[header_name] = header_value
    
    def modify_authentication_headers(self, auth_config: Dict[str, Any]):
        """
        Modify authentication headers (SPF, DKIM, ARC)
        Example: {
            'spf': 'pass',
            'dkim': 'pass',
            'arc_seal': 'i=1; a=rsa-sha256; ...',
            'arc_message_signature': 'i=1; a=rsa-sha256; ...',
            'arc_authentication_results': 'i=1; mx.google.com; ...'
        }
        """
        # SPF result (usually in Authentication-Results)
        if 'spf' in auth_config:
            auth_results = self.msg.get('Authentication-Results', '')
            # Simple replacement - in production, parse properly
            if 'spf=' in auth_results:
                auth_results = re.sub(r'spf=\w+', f"spf={auth_config['spf']}", auth_results)
            else:
                auth_results += f"; spf={auth_config['spf']}"
            del self.msg['Authentication-Results']
            self.msg['Authentication-Results'] = auth_results
        
        # DKIM result
        if 'dkim' in auth_config:
            auth_results = self.msg.get('Authentication-Results', '')
            if 'dkim=' in auth_results:
                auth_results = re.sub(r'dkim=\w+', f"dkim={auth_config['dkim']}", auth_results)
            else:
                auth_results += f"; dkim={auth_config['dkim']}"
            del self.msg['Authentication-Results']
            self.msg['Authentication-Results'] = auth_results
        
        # ARC headers
        if 'arc_seal' in auth_config:
            del self.msg['ARC-Seal']
            self.msg['ARC-Seal'] = auth_config['arc_seal']
        
        if 'arc_message_signature' in auth_config:
            del self.msg['ARC-Message-Signature']
            self.msg['ARC-Message-Signature'] = auth_config['arc_message_signature']
        
        if 'arc_authentication_results' in auth_config:
            del self.msg['ARC-Authentication-Results']
            self.msg['ARC-Authentication-Results'] = auth_config['arc_authentication_results']
    
    def modify_basic_headers(self, headers: Dict[str, str]):
        """
        Modify basic email headers
        Example: {'From': 'sender@example.com', 'To': 'recipient@example.com', 'Subject': 'New Subject'}
        """
        address_headers = ['from', 'to', 'cc', 'bcc', 'reply-to', 'sender'] # Lowercase for comparison

        for header_name, header_value in headers.items():
            # Always remove the old header before adding the new one to avoid duplicates
            if header_name in self.msg:
                del self.msg[header_name]

            if isinstance(header_value, str):
                if header_name.lower() in address_headers:
                    # Handle address headers (From, To, Cc, etc.)
                    real_name, email_addr = parseaddr(header_value)
                    if real_name: # If there's a display name
                        try:
                            real_name.encode('ascii')
                            # Name is ASCII, format directly
                            self.msg[header_name] = formataddr((real_name, email_addr))
                        except UnicodeEncodeError:
                            # Name contains non-ASCII, encode it
                            encoded_name = Header(real_name, 'utf-8').encode()
                            self.msg[header_name] = formataddr((encoded_name, email_addr))
                    else:
                        # No display name, just an email address
                        self.msg[header_name] = email_addr # or header_value if it's just the address
                else:
                    # Handle non-address headers (like Subject)
                    try:
                        header_value.encode('ascii')
                        self.msg[header_name] = header_value # It's ASCII
                    except UnicodeEncodeError:
                        # Contains non-ASCII, use Header object for RFC2047 encoding
                        self.msg[header_name] = Header(header_value, 'utf-8')
            else:
                # If header_value is not a string (e.g., already a Header object), assign directly
                self.msg[header_name] = header_value

        # Special handling for Date - should already be formatted by web_app or tool
        if 'Date' in headers and 'Date' not in self.msg: # If it was deleted and needs re-adding
            if isinstance(headers['Date'], str): # Ensure it's a string before assigning
                self.msg['Date'] = headers['Date']
    
    def replace_attachment(self, old_filename: str, new_file_path: str, new_filename: Optional[str] = None):
        """Replace an attachment with a new file"""
        if new_filename is None:
            new_filename = os.path.basename(new_file_path)
        
        # For multipart messages
        if self.msg.is_multipart():
            parts = []
            attachment_replaced = False
            
            # Use get_payload() to get direct children only, not walk() which gets all descendants
            for part in self.msg.get_payload():
                if part.get_content_disposition() == 'attachment':
                    filename = part.get_filename()
                    if filename == old_filename:
                        # Create new attachment
                        new_part = self._create_attachment(new_file_path, new_filename)
                        parts.append(new_part)
                        attachment_replaced = True
                    else:
                        parts.append(part)
                else:
                    parts.append(part)
            
            if attachment_replaced:
                # Rebuild the message
                new_msg = email.mime.multipart.MIMEMultipart(self.msg.get_content_subtype())
                
                # Copy headers
                for header, value in self.msg.items():
                    if header.lower() not in ['content-type', 'mime-version']:
                        new_msg[header] = value
                
                # Add parts
                for part in parts:
                    new_msg.attach(part)
                
                self.msg = new_msg
    
    def add_attachment(self, file_path: str, filename: Optional[str] = None):
        """Add a new attachment to the email"""
        if filename is None:
            filename = os.path.basename(file_path)
        
        attachment = self._create_attachment(file_path, filename)
        
        # If message is not multipart, convert it
        if not self.msg.is_multipart():
            # Create new multipart message
            new_msg = email.mime.multipart.MIMEMultipart('mixed')
            
            # Copy headers
            for header, value in self.msg.items():
                if header.lower() not in ['content-type', 'mime-version']:
                    new_msg[header] = value
            
            # Add original content as first part
            body_part = email.mime.text.MIMEText(self.msg.get_payload(), self.msg.get_content_subtype())
            new_msg.attach(body_part)
            
            self.msg = new_msg
        
        # Add attachment
        self.msg.attach(attachment)
    
    def _create_attachment(self, file_path: str, filename: str):
        """Create an attachment from a file"""
        # Guess the content type
        ctype, encoding = mimetypes.guess_type(file_path)
        if ctype is None or encoding is not None:
            ctype = 'application/octet-stream'
        
        maintype, subtype = ctype.split('/', 1)
        
        # Read the file
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # Create appropriate MIME type
        if maintype == 'text':
            attachment = email.mime.text.MIMEText(file_data.decode('utf-8', errors='ignore'), _subtype=subtype)
        elif maintype == 'image':
            attachment = email.mime.image.MIMEImage(file_data, _subtype=subtype)
        elif maintype == 'audio':
            attachment = email.mime.audio.MIMEAudio(file_data, _subtype=subtype)
        else:
            attachment = email.mime.base.MIMEBase(maintype, subtype)
            attachment.set_payload(file_data)
            encode_base64(attachment)
        
        # Add headers
        # Ensure filename is RFC2047 encoded if it contains non-ASCII characters
        try:
            filename.encode('ascii')
            # Filename is ASCII, use directly
            attachment.add_header('Content-Disposition', 'attachment', filename=filename)
            # Some clients also expect a name parameter in Content-Type for attachments
            if maintype == 'application' and subtype == 'octet-stream': # Common for generic attachments
                attachment.set_param('name', filename, header='Content-Type')
            elif maintype == 'image' or maintype == 'audio' or maintype == 'text': # For these, name in CT is also common
                 # Check if name param already exists from mimetypes.guess_type, if so, update if different
                 # or add if not. set_param will replace if it exists.
                 attachment.set_param('name', filename, header='Content-Type')

        except UnicodeEncodeError:
            # Filename contains non-ASCII, encode it
            encoded_filename_header = Header(filename, 'utf-8').encode()
            attachment.add_header('Content-Disposition', 'attachment', filename=encoded_filename_header)
            # Also encode for Content-Type name parameter
            if maintype == 'application' and subtype == 'octet-stream':
                 attachment.set_param('name', encoded_filename_header, header='Content-Type')
            elif maintype == 'image' or maintype == 'audio' or maintype == 'text':
                 attachment.set_param('name', encoded_filename_header, header='Content-Type')
        
        return attachment
    
    def remove_attachment(self, filename: str):
        """Remove an attachment by filename"""
        if self.msg.is_multipart():
            parts = []
            
            # Use get_payload() to get direct children only, not walk() which gets all descendants
            for part in self.msg.get_payload():
                if part.get_content_disposition() == 'attachment':
                    if part.get_filename() != filename:
                        parts.append(part)
                else:
                    parts.append(part)
            
            # Rebuild message
            new_msg = email.mime.multipart.MIMEMultipart(self.msg.get_content_subtype())
            
            # Copy headers
            for header, value in self.msg.items():
                if header.lower() not in ['content-type', 'mime-version']:
                    new_msg[header] = value
            
            # Add parts
            for part in parts:
                new_msg.attach(part)
            
            self.msg = new_msg
    
    def list_attachments(self) -> List[str]:
        """List all attachments in the email"""
        attachments = []
        
        if self.msg.is_multipart():
            for part in self.msg.walk():
                if part.get_content_disposition() == 'attachment':
                    filename = part.get_filename()
                    if filename:
                        attachments.append(filename)
        
        return attachments
    
    def get_headers(self) -> Dict[str, str]:
        """Get all headers as a dictionary"""
        headers = {}
        for key, value in self.msg.items():
            if key in headers:
                # Handle multiple headers with same name
                if isinstance(headers[key], list):
                    headers[key].append(value)
                else:
                    headers[key] = [headers[key], value]
            else:
                headers[key] = value
        return headers
    
    def modify_message_id(self, domain: str = None, parsed_dt_obj: Optional[datetime] = None):
        """Generate and set a new Message-ID, optionally based on a given datetime."""
        if domain is None:
            # Extract domain from From address
            from_addr = self.msg.get('From', '')
            match = re.search(r'@([^\s>]+)', from_addr)
            domain = match.group(1) if match else 'example.com'
        
        # Generate new Message-ID
        if parsed_dt_obj:
            # Ensure the datetime object is timezone-aware for consistent timestamp generation
            if parsed_dt_obj.tzinfo is None or parsed_dt_obj.tzinfo.utcoffset(parsed_dt_obj) is None:
                dt_for_msg_id = parsed_dt_obj.astimezone() # Convert naive to local-aware
            else:
                dt_for_msg_id = parsed_dt_obj
            timestamp = dt_for_msg_id.timestamp()
        else:
            timestamp = datetime.now().timestamp()
        
        random_part = hashlib.md5(str(timestamp).encode()).hexdigest()[:8]
        new_message_id = f"<{int(timestamp)}.{random_part}@{domain}>"
        
        if 'Message-ID' in self.msg: # Check before deleting
            del self.msg['Message-ID']
        self.msg['Message-ID'] = new_message_id
    
    def strip_threading_headers(self):
        """Remove headers related to email threading (In-Reply-To, References) and ensure a new Message-ID."""
        if 'In-Reply-To' in self.msg:
            del self.msg['In-Reply-To']
        if 'References' in self.msg:
            del self.msg['References']
        # Ensure a fresh Message-ID for a truly "new" email, 
        # even if the date wasn't explicitly changed in this modification round.
        self.modify_message_id()

    def update_mime_headers(self):
        """Update MIME-related headers to ensure consistency"""
        # This is automatically handled by the email library when as_bytes() is called
        pass


def main():
    parser = argparse.ArgumentParser(description='EML File Editor')
    parser.add_argument('input', help='Input EML file path')
    parser.add_argument('-o', '--output', help='Output EML file path', default='modified.eml')
    parser.add_argument('--date', help='New date (e.g., "Tue, 23 May 2017 14:59:31 +0430")')
    parser.add_argument('--from', dest='from_addr', help='New From address')
    parser.add_argument('--to', help='New To address(es)')
    parser.add_argument('--subject', help='New Subject')
    parser.add_argument('--add-attachment', help='Add attachment (file path)')
    parser.add_argument('--remove-attachment', help='Remove attachment (filename)')
    parser.add_argument('--replace-attachment', nargs=2, metavar=('OLD_NAME', 'NEW_FILE'), 
                       help='Replace attachment')
    parser.add_argument('--list-attachments', action='store_true', help='List all attachments')
    parser.add_argument('--show-headers', action='store_true', help='Show all headers')
    parser.add_argument('--delivered-to', help='New Delivered-To address')
    parser.add_argument('--return-path', help='New Return-Path address')
    parser.add_argument('--new-message-id', action='store_true', help='Generate new Message-ID')
    
    args = parser.parse_args()
    
    # Create editor instance
    editor = EMLEditor(args.input)
    
    # List attachments if requested
    if args.list_attachments:
        print("Attachments:")
        for att in editor.list_attachments():
            print(f"  - {att}")
        return
    
    # Show headers if requested
    if args.show_headers:
        print("Headers:")
        headers = editor.get_headers()
        for key, value in headers.items():
            print(f"  {key}: {value}")
        return
    
    # Apply modifications
    if args.date:
        editor.modify_date(args.date)
    
    # Basic headers
    basic_headers = {}
    if args.from_addr:
        basic_headers['From'] = args.from_addr
    if args.to:
        basic_headers['To'] = args.to
    if args.subject:
        basic_headers['Subject'] = args.subject
    
    if basic_headers:
        editor.modify_basic_headers(basic_headers)
    
    # Transport headers
    transport_headers = {}
    if args.delivered_to:
        transport_headers['Delivered-To'] = args.delivered_to
    if args.return_path:
        transport_headers['Return-Path'] = args.return_path
    
    if transport_headers:
        editor.modify_transport_headers(transport_headers)
    
    # Message-ID
    if args.new_message_id:
        editor.modify_message_id()
    
    # Attachments
    if args.add_attachment:
        editor.add_attachment(args.add_attachment)
    
    if args.remove_attachment:
        editor.remove_attachment(args.remove_attachment)
    
    if args.replace_attachment:
        old_name, new_file = args.replace_attachment
        editor.replace_attachment(old_name, new_file)
    
    # Save the modified email
    editor.save_eml(args.output)
    print(f"Modified EML saved to: {args.output}")


if __name__ == '__main__':
    main() 