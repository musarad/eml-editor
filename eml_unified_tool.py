#!/usr/bin/env python3
"""
Unified EML Tool - Complete email modification with interactive interface
Combines all features: headers, dates, body, attachments, and crypto signing
"""

import os
import sys
import json
import email
import email.utils
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import argparse
import re
from pathlib import Path
import random
from datetime import timedelta
from email.header import decode_header

# Import our modules
from eml_editor import EMLEditor
from eml_advanced_editor import AdvancedEMLEditor

# Try to import crypto modules
try:
    from eml_crypto_signer import EMLCryptoSigner, EMLCryptoEditor, setup_dkim_keys
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("⚠️  Crypto features not available. Install requirements for full functionality:")
    print("    pip install -r requirements.txt")


class UnifiedEMLTool:
    """Unified tool for complete EML file modification"""
    
    def __init__(self, eml_path: str):
        """Initialize with an EML file"""
        self.eml_path = eml_path
        self.editor = AdvancedEMLEditor(eml_path)
        self.crypto_editor = None
        self.modifications = {}
        self.auth_performing_server = 'mx.example.com' # Default, will be updated by transport chain logic
        self.first_sending_smtp_server = 'smtp.example.com' # Default for Message-ID
        
        # Extract original information
        self.original_info = self.extract_email_info()
    
    def _find_primary_body_part(self, msg_obj=None) -> Optional[email.message.Message]:
        """Helper to find the primary text/html or text/plain part."""
        if msg_obj is None:
            msg_obj = self.editor.msg
        
        target_part = None
        if msg_obj.is_multipart():
            # Prefer text/html as it's usually the richer content
            for part in msg_obj.walk():
                if not part.is_multipart() and part.get_content_type() == "text/html":
                    target_part = part
                    break
            if not target_part: # Fallback to text/plain
                for part in msg_obj.walk():
                    if not part.is_multipart() and part.get_content_type() == "text/plain":
                        target_part = part
                        break
        elif msg_obj.get_content_maintype() == 'text': # Single part text message
            target_part = msg_obj
        return target_part

    def extract_email_info(self) -> Dict:
        """Extract all information from the current email"""
        raw_headers = self.editor.get_headers()
        decoded_headers = {}
        for key, value in raw_headers.items():
            # Decode header value if it's a string and potentially encoded
            if isinstance(value, str):
                decoded_parts = decode_header(value)
                header_val_parts = []
                for part_val, charset in decoded_parts:
                    if isinstance(part_val, bytes):
                        header_val_parts.append(part_val.decode(charset or 'utf-8', 'replace'))
                    else:
                        header_val_parts.append(part_val)
                decoded_headers[key] = "".join(header_val_parts)
            elif isinstance(value, list): # Handle multiple headers with the same name
                decoded_list = []
                for item_val_str in value:
                    decoded_item_parts = decode_header(item_val_str)
                    item_parts_collector = []
                    for part_val, charset in decoded_item_parts:
                        if isinstance(part_val, bytes):
                            item_parts_collector.append(part_val.decode(charset or 'utf-8', 'replace'))
                        else:
                            item_parts_collector.append(part_val)
                    decoded_list.append("".join(item_parts_collector))
                decoded_headers[key] = decoded_list # Keep as list if original was list
            else:
                decoded_headers[key] = value # Should not happen often for typical headers

        info = {
            'headers': decoded_headers, # Use decoded headers
            'attachments': self.editor.list_attachments(),
            'body_info': {'content': "", 'type': None, 'charset': 'utf-8', 'part_exists': False},
            'transport_chain': self.extract_transport_chain(),
            'authentication': self.extract_authentication_info()
        }

        primary_body_part = self._find_primary_body_part()
        if primary_body_part:
            info['body_info']['part_exists'] = True
            info['body_info']['type'] = primary_body_part.get_content_type() # e.g. text/html
            charset = primary_body_part.get_content_charset() or 'utf-8'
            info['body_info']['charset'] = charset
            payload = primary_body_part.get_payload(decode=True)
            if payload is not None:
                 info['body_info']['content'] = payload.decode(charset, errors='replace')
        
        return info
    
    def get_email_body(self) -> str:
        """Extract the email body text"""
        extracted_info = self.extract_email_info()
        return extracted_info['body_info']['content']
    
    def extract_transport_chain(self) -> List[Dict]:
        """Extract transport chain from Received headers"""
        received_headers = self.editor.msg.get_all('Received', [])
        chain = []
        
        for header in received_headers:
            # Parse received header
            info = {
                'raw': header,
                'from': '',
                'by': '',
                'with': '',
                'id': '',
                'date': ''
            }
            
            # Extract components using regex
            from_match = re.search(r'from\s+([^\s]+(?:\s+\[[^\]]+\])?)', header)
            by_match = re.search(r'by\s+([^\s]+)', header)
            with_match = re.search(r'with\s+([^\s]+)', header)
            id_match = re.search(r'id\s+([^\s;]+)', header)
            
            if from_match:
                info['from'] = from_match.group(1)
            if by_match:
                info['by'] = by_match.group(1)
            if with_match:
                info['with'] = with_match.group(1)
            if id_match:
                info['id'] = id_match.group(1)
            
            # Extract date (usually after semicolon)
            if ';' in header:
                info['date'] = header.split(';', 1)[1].strip()
            
            chain.append(info)
        
        return chain
    
    def extract_authentication_info(self) -> Dict:
        """Extract authentication information"""
        auth_info = {
            'spf': 'none',
            'dkim': 'none',
            'dmarc': 'none',
            'arc': 'none'
        }
        
        # Check Authentication-Results header
        auth_results = self.editor.msg.get('Authentication-Results', '')
        if auth_results:
            if 'spf=pass' in auth_results:
                auth_info['spf'] = 'pass'
            elif 'spf=fail' in auth_results:
                auth_info['spf'] = 'fail'
            
            if 'dkim=pass' in auth_results:
                auth_info['dkim'] = 'pass'
            elif 'dkim=fail' in auth_results:
                auth_info['dkim'] = 'fail'
            
            if 'dmarc=pass' in auth_results:
                auth_info['dmarc'] = 'pass'
            elif 'dmarc=fail' in auth_results:
                auth_info['dmarc'] = 'fail'
        
        # Check for ARC headers
        if self.editor.msg.get('ARC-Seal'):
            auth_info['arc'] = 'present'
        
        return auth_info
    
    def display_email_info(self):
        """Display current email information"""
        print("\n" + "="*60)
        print("CURRENT EMAIL INFORMATION")
        print("="*60)
        
        # Basic headers
        print("\n📧 Basic Headers:")
        for header in ['From', 'To', 'Subject', 'Date', 'Message-ID']:
            value = self.original_info['headers'].get(header, 'N/A')
            if isinstance(value, list):
                value = value[0]
            print(f"  {header}: {value}")
        
        # Body preview
        print("\n📄 Body Preview:")
        body = self.original_info['body_info']['content']
        preview = body[:200] + '...' if len(body) > 200 else body
        print(f"  {preview}")
        
        # Attachments
        print("\n📎 Attachments:")
        if self.original_info['attachments']:
            for att in self.original_info['attachments']:
                print(f"  - {att}")
        else:
            print("  No attachments")
        
        # Transport info
        print("\n🔄 Transport Chain:")
        for i, hop in enumerate(self.original_info['transport_chain']):
            print(f"  Hop {i+1}: from {hop['from']} by {hop['by']}")
        
        # Authentication
        print("\n🔐 Authentication Status:")
        for check, result in self.original_info['authentication'].items():
            print(f"  {check.upper()}: {result}")
    
    def interactive_modification(self):
        """Interactive interface for modifying email"""
        print("\n" + "="*60)
        print("EMAIL MODIFICATION WIZARD")
        print("="*60)
        
        # 1. Date modification
        print("\n📅 Date Modification:")
        print(f"Current date: {self.original_info['headers'].get('Date', 'N/A')}")
        new_date = input("Enter new date (or press Enter to keep current): ").strip()
        
        if new_date:
            # Validate and format date
            try:
                # Try to parse the date
                if not re.match(r'^\w{3},\s+\d{1,2}\s+\w{3}\s+\d{4}\s+\d{2}:\d{2}:\d{2}', new_date):
                    # If not in RFC format, try to parse and convert
                    parsed = datetime.strptime(new_date, "%Y-%m-%d %H:%M:%S")
                    new_date = email.utils.formatdate(parsed.timestamp(), localtime=True)
                self.modifications['date'] = new_date
                print(f"✅ Date will be changed to: {new_date}")
            except Exception as e:
                print(f"⚠️  Invalid date format. Keeping original date.")
        
        # 2. Body modification
        print("\n📝 Body Modification:")
        print("Current body preview:")
        print("-" * 40)
        print(self.original_info['body_info']['content'][:200] + '...' if len(self.original_info['body_info']['content']) > 200 else self.original_info['body_info']['content'])
        print("-" * 40)
        
        modify_body = input("Do you want to modify the body? (y/n): ").strip().lower()
        if modify_body == 'y':
            print("Enter new body text (type 'END' on a new line when finished):")
            body_lines = []
            while True:
                line = input()
                if line == 'END':
                    break
                body_lines.append(line)
            self.modifications['body'] = '\n'.join(body_lines)
            print("✅ Body will be updated")
        
        # 3. Attachment modification
        print("\n📎 Attachment Modification:")
        if self.original_info['attachments']:
            print("Current attachments:")
            for i, att in enumerate(self.original_info['attachments']):
                print(f"  {i+1}. {att}")
        else:
            print("No current attachments")
        
        print("\nAttachment options:")
        print("1. Add new attachment")
        print("2. Remove attachment")
        print("3. Replace attachment")
        print("4. Skip attachment modification")
        
        att_choice = input("Choose option (1-4): ").strip()
        
        if att_choice == '1':
            file_path = input("Enter path to file to attach: ").strip()
            if os.path.exists(file_path):
                if 'attachments' not in self.modifications:
                    self.modifications['attachments'] = {}
                if 'add' not in self.modifications['attachments']:
                    self.modifications['attachments']['add'] = []
                self.modifications['attachments']['add'].append(file_path)
                print(f"✅ Will add attachment: {os.path.basename(file_path)}")
            else:
                print("⚠️  File not found")
        
        elif att_choice == '2' and self.original_info['attachments']:
            att_num = input("Enter attachment number to remove: ").strip()
            try:
                idx = int(att_num) - 1
                if 0 <= idx < len(self.original_info['attachments']):
                    if 'attachments' not in self.modifications:
                        self.modifications['attachments'] = {}
                    if 'remove' not in self.modifications['attachments']:
                        self.modifications['attachments']['remove'] = []
                    self.modifications['attachments']['remove'].append(self.original_info['attachments'][idx])
                    print(f"✅ Will remove: {self.original_info['attachments'][idx]}")
            except:
                print("⚠️  Invalid selection")
        
        elif att_choice == '3' and self.original_info['attachments']:
            att_num = input("Enter attachment number to replace: ").strip()
            try:
                idx = int(att_num) - 1
                if 0 <= idx < len(self.original_info['attachments']):
                    new_file = input("Enter path to replacement file: ").strip()
                    if os.path.exists(new_file):
                        if 'attachments' not in self.modifications:
                            self.modifications['attachments'] = {}
                        if 'replace' not in self.modifications['attachments']:
                            self.modifications['attachments']['replace'] = []
                        self.modifications['attachments']['replace'].append(
                            [self.original_info['attachments'][idx], new_file]
                        )
                        print(f"✅ Will replace {self.original_info['attachments'][idx]} with {os.path.basename(new_file)}")
            except:
                print("⚠️  Invalid selection")
        
        # 4. Additional headers
        print("\n🔧 Additional Modifications:")
        modify_headers = input("Do you want to modify other headers? (y/n): ").strip().lower()
        if modify_headers == 'y':
            print("Common headers to modify:")
            print("1. From")
            print("2. To") 
            print("3. Subject")
            print("4. Custom header")
            
            header_choice = input("Choose option (1-4): ").strip()
            header_map = {'1': 'From', '2': 'To', '3': 'Subject'}
            
            if header_choice in header_map:
                header_name = header_map[header_choice]
                current_value = self.original_info['headers'].get(header_name, 'N/A')
                print(f"Current {header_name}: {current_value}")
                new_value = input(f"Enter new {header_name}: ").strip()
                if new_value:
                    if 'headers' not in self.modifications:
                        self.modifications['headers'] = {}
                    self.modifications['headers'][header_name] = new_value
                    print(f"✅ {header_name} will be changed")
            elif header_choice == '4':
                header_name = input("Enter header name: ").strip()
                header_value = input("Enter header value: ").strip()
                if header_name and header_value:
                    if 'headers' not in self.modifications:
                        self.modifications['headers'] = {}
                    self.modifications['headers'][header_name] = header_value
                    print(f"✅ {header_name} will be set")
    
    def apply_modifications(self, output_path: str, use_crypto: bool = False, is_new_email: bool = False, realistic_mode: bool = True, align_x_headers: bool = False):
        """
        Apply all modifications and save the result
        
        Args:
            output_path: Path to save modified email
            use_crypto: Whether to use real cryptographic signatures
            is_new_email: Whether this is creating a new email from scratch
            realistic_mode: Whether to use realistic authentication (prevents detection)
            align_x_headers: Whether to regenerate X-headers to align with modifications (vs preserve)
        """
        print("\n" + "="*60)
        print("APPLYING MODIFICATIONS")
        print("="*60)
        
        if realistic_mode and not use_crypto:
            print("🛡️  REALISTIC MODE ENABLED")
            print("   - Authentication results will reflect actual signatures")
            print("   - No false DKIM/DMARC pass claims")
            print("   - Reduces detection risk in forensic analysis")
            print("")
        
        # 0. Preserve original signatures if in realistic mode
        preserved_signatures = {}
        preserved_x_headers = {}
        if realistic_mode and not is_new_email:
            print("🔐 Preserving original signatures...")
            preserved_signatures = self.editor.preserve_original_signatures()
            # Only preserve X-headers if not aligning them
            if not align_x_headers:
                preserved_x_headers = self.editor.preserve_x_headers()
        
        # 1. Apply header modifications first
        if 'headers' in self.modifications:
            print("📝 Updating headers...")
            self.editor.modify_basic_headers(self.modifications['headers'])
        
        # 2. Update date and regenerate Message-ID consistently
        if 'date' in self.modifications:
            print("📅 Updating date...")
            self.editor.modify_date(self.modifications['date'])
        
        # 3. Fix Message-ID domain if needed
        print("🆔 Checking Message-ID consistency...")
        self.editor.fix_message_id_domain()
        
        # 4. Update body content
        if 'body' in self.modifications:
            print("📄 Updating body content...")
            original_body_type = self.original_info['body_info']['type']
            self.update_body(self.modifications['body'], original_body_type)
        
        # 5. Handle attachments
        if 'attachments' in self.modifications:
            print("📎 Processing attachments...")
            att_mods = self.modifications['attachments']
            
            # Remove attachments
            if 'remove' in att_mods:
                for filename in att_mods['remove']:
                    self.editor.remove_attachment(filename)
                    print(f"  ➖ Removed: {filename}")
            
            # Replace attachments  
            if 'replace' in att_mods:
                for old_file, new_file in att_mods['replace']:
                    new_filename = os.path.basename(new_file)
                    self.editor.replace_attachment(old_file, new_file, new_filename)
                    print(f"  🔄 Replaced: {old_file} → {new_filename}")
            
            # Add new attachments
            if 'add' in att_mods:
                for file_path in att_mods['add']:
                    filename = os.path.basename(file_path)
                    self.editor.add_attachment(file_path, filename)
                    print(f"  ➕ Added: {filename}")
        
        # 6. Update transport chain (creates realistic routing)
        print("🔄 Updating transport chain...")
        self.update_transport_chain()
        
        # 7. Manage Google headers based on transport chain
        print("📧 Managing provider-specific headers...")
        transport_chain = self.editor.msg.get_all('Received', [])
        transport_info = []
        for header in transport_chain:
            info = {'by': '', 'from': ''}
            by_match = re.search(r'by\s+([^\s]+)', header)
            from_match = re.search(r'from\s+([^\s]+)', header)
            if by_match:
                info['by'] = by_match.group(1)
            if from_match:
                info['from'] = from_match.group(1)
            transport_info.append(info)
        
        self.editor.manage_google_headers(transport_info)
        
        # 7.5. Handle X-headers based on mode and alignment preference
        if align_x_headers:
            # User wants X-headers to align with modifications
            print("🔄 Generating X-headers aligned with modifications...")
            self.editor.update_x_headers_for_alignment()
        elif preserved_x_headers and realistic_mode:
            # Preserve original X-headers
            print("📋 Restoring preserved X-headers...")
            self.editor.restore_x_headers(preserved_x_headers)
        elif not realistic_mode:
            # Legacy mode - generate aligned headers
            print("🔄 Updating X-headers for alignment (legacy mode)...")
            self.editor.update_x_headers_for_alignment()
        
        # 8. Update authentication headers (critical for realism)
        print("🔐 Updating authentication headers...")
        if realistic_mode:
            self.update_authentication_headers_realistic(use_crypto)
        else:
            self.update_authentication_headers(use_crypto)
        
        # 9. Restore preserved signatures if applicable
        if preserved_signatures and realistic_mode and not use_crypto:
            print("🔐 Restoring preserved signatures...")
            self.editor.restore_preserved_signatures(preserved_signatures)
        
        # 10. Update transport-related headers
        from_addr = self.modifications.get('headers', {}).get('From', self.original_info['headers'].get('From', 'sender@example.com'))
        to_addr = self.modifications.get('headers', {}).get('To', self.original_info['headers'].get('To', 'recipient@example.com'))
        
        if ',' in to_addr:
            primary_recipient = to_addr.split(',')[0].strip()
        else:
            primary_recipient = to_addr
        
        self.editor.modify_transport_headers({
            'Delivered-To': primary_recipient,
            'Return-Path': f'<{from_addr}>'
        })
        
        # 11. Save the result
        print("💾 Saving modified email...")
        self.editor.save_eml(output_path)
        
        # 12. Validate the result
        print("\n🔍 VALIDATION RESULTS:")
        validation = self.editor.validate_authentication_consistency()
        
        if validation['warnings']:
            print("⚠️  Potential detection risks:")
            for warning in validation['warnings']:
                print(f"   - {warning}")
        else:
            print("✅ No obvious authentication inconsistencies detected")
        
        print(f"\n✅ Modified email saved to: {output_path}")
        
        if not realistic_mode and not use_crypto:
            print("\n🚨 WARNING: Email contains authentication inconsistencies!")
            print("   This email may be detected as tampered in forensic analysis.")
            print("   Use --realistic or --crypto flags for better authenticity.")

    def update_body(self, new_body_content: str, original_body_main_type: str = 'text/plain'):
        """Update the email body, ensuring old body parts are removed."""
        print("----------------------------------------------------------")
        print(f"DEBUG: ENTERING update_body method.")
        print(f"DEBUG: original_body_main_type = '{original_body_main_type}'")
        print(f"DEBUG: Initial new_body_content received by update_body:\n'''{new_body_content}'''")
        print("----------------------------------------------------------")
        
        msg = self.editor.msg
        
        # Create new alternative part for text/html content
        new_alternative_part = email.mime.multipart.MIMEMultipart('alternative')
        
        # Add plain text version
        plain_text_part = email.mime.text.MIMEText(new_body_content, 'plain', 'utf-8')
        new_alternative_part.attach(plain_text_part)
        
        # Add HTML version (simple conversion)
        html_body = new_body_content.replace('\n', '<br>\n')
        html_content = f"<html><body><p>{html_body}</p></body></html>"
        html_text_part = email.mime.text.MIMEText(html_content, 'html', 'utf-8')
        new_alternative_part.attach(html_text_part)
        
        # Validate Content-Type before processing
        current_content_type = msg.get_content_type()
        print(f"🔍 Current message Content-Type: {current_content_type}")
        
        # Fix any non-standard Content-Type issues
        if msg.is_multipart():
            content_type_header = msg.get('Content-Type', '')
            if 'multipart/alt' in content_type_header:
                print("⚠️  Detected non-standard 'multipart/alt' - fixing to 'multipart/alternative'")
                # Fix the Content-Type header
                fixed_content_type = content_type_header.replace('multipart/alt', 'multipart/alternative')
                del msg['Content-Type']
                msg['Content-Type'] = fixed_content_type
        
        if msg.is_multipart():
            # Find and replace existing alternative part or add new one
            payload = msg.get_payload()
            alternative_part_index = None
            
            for i, part in enumerate(payload):
                if isinstance(part, email.message.Message) and part.is_multipart():
                    if part.get_content_subtype() == 'alternative':
                        alternative_part_index = i
                        break
            
            if alternative_part_index is not None:
                # Replace existing alternative part
                payload[alternative_part_index] = new_alternative_part
                print("🔄 Replaced existing multipart/alternative part")
            else:
                # Add new alternative part
                payload.append(new_alternative_part)
                print("➕ Added new multipart/alternative part")
            
            msg.set_payload(payload)
            
            print(f"DEBUG: Main message payload *after* set_payload (count: {len(msg.get_payload())}):")
            for i, p_after in enumerate(msg.get_payload()):
                print(f"  Part {i} Content-Type: {p_after.get_content_type()}")
                if p_after.is_multipart() and p_after.get_content_subtype() == 'alternative':
                    print(f"    Alternative part has {len(p_after.get_payload())} sub-parts.")
                    for j, sub_p in enumerate(p_after.get_payload()):
                        print(f"      Sub-part {j} Content-Type: {sub_p.get_content_type()}")
            print("----------------------------------------------------------")
            
            # Force boundary regeneration for proper MIME structure
            if 'boundary' in msg.get_params(header='Content-Type'):
                msg.del_param('boundary', header='Content-Type')
                print("🔄 Forcing MIME boundary regeneration for standards compliance")
        else:
            print("Original message was not multipart. Creating new multipart/mixed structure.")
            # Preserve original headers but create proper MIME structure
            old_headers = dict(msg.items())
            new_root_msg = email.mime.multipart.MIMEMultipart('mixed')
            
            # Copy headers except MIME-related ones
            for k, v in old_headers.items():
                if k.lower() not in ['content-type', 'content-transfer-encoding', 'mime-version']:
                    new_root_msg[k] = v
            
            # Ensure proper MIME-Version
            if 'MIME-Version' not in new_root_msg:
                new_root_msg['MIME-Version'] = '1.0'
            
            new_root_msg.attach(new_alternative_part)
            self.editor.msg = new_root_msg
            msg = self.editor.msg 
            print("✅ Created proper multipart/mixed structure with multipart/alternative content")
            print("----------------------------------------------------------")
            print(f"DEBUG: New root message payload (count: {len(msg.get_payload())}):")
            for i, p_after in enumerate(msg.get_payload()):
                print(f"  Part {i} Content-Type: {p_after.get_content_type()}")
                if p_after.is_multipart() and p_after.get_content_subtype() == 'alternative':
                    print(f"    Alternative part has {len(p_after.get_payload())} sub-parts.")
                    for j, sub_p in enumerate(p_after.get_payload()):
                        print(f"      Sub-part {j} Content-Type: {sub_p.get_content_type()}")
            print("----------------------------------------------------------")

        print("Body update process completed.")
        self.modifications['body_updated'] = True

    def update_transport_chain(self):
        """Update transport chain based on modifications"""
        # Check if original email routed through Google
        original_received = self.editor.msg.get_all('Received', [])
        routes_through_google_originally = any(
            'google' in h.lower() or 'gmail' in h.lower() 
            for h in original_received
        )
        
        # Get current date or use modified date
        # Ensure we have a datetime object to work with for timestamps
        base_datetime_obj = None
        date_str_for_eml = self.modifications.get('date')
        original_eml_date_str = self.original_info['headers'].get('Date')

        if date_str_for_eml:
            try:
                base_datetime_obj = email.utils.parsedate_to_datetime(date_str_for_eml)
            except (TypeError, ValueError, AttributeError):
                pass # Will try original if modified fails
        
        if base_datetime_obj is None and original_eml_date_str:
            try:
                base_datetime_obj = email.utils.parsedate_to_datetime(original_eml_date_str)
            except (TypeError, ValueError, AttributeError):
                pass # Will fall back to datetime.now()

        if base_datetime_obj is None:
            base_datetime_obj = datetime.now()
        
        # Ensure it's timezone-aware for consistent timestamp generation
        if base_datetime_obj.tzinfo is None or base_datetime_obj.tzinfo.utcoffset(base_datetime_obj) is None:
            base_datetime_obj = base_datetime_obj.astimezone()
        
        from_addr = self.modifications.get('headers', {}).get('From', self.original_info['headers'].get('From', 'sender@example.com'))
        domain = from_addr.split('@')[1] if '@' in from_addr else 'example.com'
        recipient_addr = self.modifications.get('headers', {}).get('To', self.original_info['headers'].get('To', 'recipient@example.com'))
        if ',' in recipient_addr: # Take the first recipient if multiple
            recipient_addr = recipient_addr.split(',')[0].strip()

        # Build transport chain - Hops are defined chronologically (earliest first)
        # create_complete_transport_chain will add them in reverse so earliest is bottom-most in EML
        
        # Determine routing server based on original email
        if routes_through_google_originally:
            # Route through Google like the original
            receiving_server = 'mx.google.com'
            gateway_server = f'mail-gw{random.randint(1,4)}.google.com'
            self.auth_performing_server = 'mx.google.com'
        else:
            # Generic routing
            receiving_server = f'mx.{domain}'
            gateway_server = f'mail.{domain}'
            self.auth_performing_server = receiving_server

        # The server that would typically generate the Message-ID (first hop from client's network)
        self.first_sending_smtp_server = f'smtp.{domain}' # from hop1

        # Create hops with proper timing
        hop1_datetime = base_datetime_obj
        hop2_datetime = hop1_datetime + timedelta(seconds=random.randint(1, 5))
        hop3_datetime = hop2_datetime + timedelta(seconds=random.randint(1, 3))
        
        hops = [
            {
                'from': f'client.{domain} [192.168.1.{random.randint(10,200)}]', # Slightly randomized internal IP
                'by': f'smtp.{domain}',
                'with': 'ESMTPS', # Common for first hop
                'id': f'{int(hop1_datetime.timestamp())}.{random.randint(10000, 99999)}.client.{domain.replace(".", "")}',
                'date': hop1_datetime
            },
            {
                'from': f'smtp.{domain}',
                'by': receiving_server,
                'with': 'ESMTPS',
                'id': f'gmx{int(hop2_datetime.timestamp())}.{random.randint(10000,99999)}' if routes_through_google_originally else f'{int(hop2_datetime.timestamp())}.{random.randint(10000,99999)}',
                'for': f'<{recipient_addr}>',
                'date': hop2_datetime
            },
            {
                'from': receiving_server,
                'by': f'{gateway_server} [209.85.220.{random.randint(10,250)}]' if routes_through_google_originally else gateway_server,
                'with': 'SMTP',
                'id': f'{random.choice(["a","b","c","d","e","f"])}{random.randint(10,99)}csp{random.randint(100000,999999)}xyz' if routes_through_google_originally else f'{int(hop3_datetime.timestamp())}.{random.randint(10000,99999)}',
                'for': f'<{recipient_addr}>',
                'date': hop3_datetime
            }
        ]
        
        self.editor.create_complete_transport_chain(hops)
    
    def update_authentication_headers(self, use_crypto: bool):
        """Update authentication headers with consistency validation"""
        from_addr = self.modifications.get('headers', {}).get('From', self.original_info['headers'].get('From', 'sender@example.com'))
        domain = from_addr.split('@')[1] if '@' in from_addr else 'example.com'
        
        if use_crypto and CRYPTO_AVAILABLE:
            # Use real crypto signing
            print("🔐 Applying real cryptographic signatures...")
            self.apply_crypto_signatures(domain)
            
            # Update authentication results to match real signatures
            self.editor.modify_authentication_results(self.auth_performing_server, {
                'spf': {'result': 'pass', 'domain': domain},
                'dkim': {'result': 'pass', 'domain': domain},
                'dmarc': {'result': 'pass', 'policy': 'none'},
                'arc': {'result': 'pass'}
            }, validate_consistency=True)
        else:
            print("⚠️  Using placeholder authentication (not cryptographically valid)")
            print("   For real authentication, use --crypto flag")
            
            # Update authentication results with warnings about placeholders
            self.editor.modify_authentication_results(self.auth_performing_server, {
                'spf': {'result': 'pass', 'domain': domain},
                'dkim': {'result': 'none', 'domain': domain},  # ← Changed to 'none' since signature is placeholder
                'dmarc': {'result': 'none', 'policy': 'none'},  # ← Changed to 'none'
                'arc': {'result': 'none'}  # ← Changed to 'none'
            }, validate_consistency=True)
            
            # Add placeholder DKIM signature with clear warnings
            self.editor.add_dkim_signature(domain, 'selector1', use_real_crypto=False)
    
    def apply_crypto_signatures(self, domain: str):
        """Apply real cryptographic signatures"""
        # Check if we have keys for this domain
        selector = 'default'
        private_key_path = f'./dkim_keys/{domain}.{selector}.private.pem'
        
        if not os.path.exists(private_key_path):
            print(f"📝 Generating DKIM keys for {domain}...")
            setup_dkim_keys(domain, selector, key_dir='./dkim_keys')
        
        # Create crypto signer
        signer = EMLCryptoSigner(private_key_path, selector, domain)
        
        # Save current state
        temp_path = 'temp_for_signing.eml'
        self.editor.save_eml(temp_path)
        
        # Create crypto editor
        crypto_editor = EMLCryptoEditor(temp_path, signer)
        
        # Add real signatures
        crypto_editor.strip_existing_signatures()
        crypto_editor.add_dkim_signature()
        crypto_editor.add_arc_chain()
        
        # Load back the signed version
        self.editor = AdvancedEMLEditor(temp_path)
        
        # Clean up
        os.remove(temp_path)
        
        print("✅ Real DKIM and ARC signatures applied")

    def update_authentication_headers_realistic(self, use_crypto: bool):
        """Update authentication headers in realistic mode - prevents false claims"""
        from_addr = self.modifications.get('headers', {}).get('From', self.original_info['headers'].get('From', 'sender@example.com'))
        domain = from_addr.split('@')[1] if '@' in from_addr else 'example.com'
        
        if use_crypto and CRYPTO_AVAILABLE:
            # Use real crypto signing
            print("🔐 Applying real cryptographic signatures...")
            self.apply_crypto_signatures(domain)
            
            # Update authentication results to match real signatures
            self.editor.modify_authentication_results(self.auth_performing_server, {
                'spf': {'result': 'pass', 'domain': domain},
                'dkim': {'result': 'pass', 'domain': domain},
                'dmarc': {'result': 'pass', 'policy': 'none'},
                'arc': {'result': 'pass'}
            }, validate_consistency=True)
        else:
            print("🛡️  Using realistic authentication results (no false claims)")
            
            # In realistic mode, don't claim DKIM/DMARC pass without real signatures
            self.editor.modify_authentication_results(self.auth_performing_server, {
                'spf': {'result': 'pass', 'domain': domain},  # SPF can often be simulated
                'dkim': {'result': 'none', 'domain': domain},  # No false claims
                'dmarc': {'result': 'none', 'policy': 'none'}  # No false claims
            }, validate_consistency=False)  # Skip validation since we're being honest
            
            print("   - SPF: pass (can be simulated)")
            print("   - DKIM: none (no valid signature)")
            print("   - DMARC: none (no DKIM/SPF alignment)")
            print("   - No fake DKIM signatures added")


def main():
    """Main function for the unified tool"""
    parser = argparse.ArgumentParser(
        description='Unified EML Tool - Complete email modification with all features',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Interactive mode (recommended):
    python eml_unified_tool.py email.eml
    
  With options:
    python eml_unified_tool.py email.eml -o modified.eml --crypto
    
  Show info only:
    python eml_unified_tool.py email.eml --info-only
        """
    )
    
    parser.add_argument('input', help='Input EML file path')
    parser.add_argument('-o', '--output', help='Output EML file path', 
                       default=None)
    parser.add_argument('--crypto', action='store_true',
                       help='Use real cryptographic signatures (requires dependencies)')
    parser.add_argument('--info-only', action='store_true',
                       help='Display email information only')
    parser.add_argument('--config', help='Load modifications from JSON config file')
    parser.add_argument('--new-email', action='store_true',
                       help='Treat as a new email (strip In-Reply-To/References headers)')
    parser.add_argument('--realistic', action='store_true', default=True,
                       help='Use realistic mode (prevents authentication inconsistencies) - DEFAULT')
    parser.add_argument('--legacy', action='store_true',
                       help='Use legacy mode (may create authentication inconsistencies - detectable)')
    parser.add_argument('--align-x-headers', action='store_true',
                       help='Generate new X-headers aligned with modifications (default: preserve original)')
    
    args = parser.parse_args()
    
    # Determine realistic mode
    realistic_mode = args.realistic and not args.legacy
    
    # Check if input file exists
    if not os.path.exists(args.input):
        print(f"❌ Error: File '{args.input}' not found")
        sys.exit(1)
    
    # Create output filename if not provided
    if not args.output:
        base_name = os.path.splitext(args.input)[0]
        if realistic_mode:
            args.output = f"{base_name}_realistic.eml"
        else:
            args.output = f"{base_name}_modified.eml"
    
    # Create tool instance
    print(f"📧 Loading email: {args.input}")
    
    if realistic_mode:
        print("🛡️  REALISTIC MODE: Prevents authentication inconsistencies")
    else:
        print("⚠️  LEGACY MODE: May create detectable inconsistencies")
    
    tool = UnifiedEMLTool(args.input)
    
    # Display current information
    tool.display_email_info()
    
    if args.info_only:
        sys.exit(0)
    
    # Load modifications from config or interactive
    if args.config:
        print(f"\n📋 Loading modifications from: {args.config}")
        with open(args.config, 'r') as f:
            tool.modifications = json.load(f)
    else:
        # Interactive modification
        tool.interactive_modification()
    
    # Confirm before applying
    print("\n" + "="*60)
    print("MODIFICATION SUMMARY")
    print("="*60)
    print(json.dumps(tool.modifications, indent=2))
    
    confirm = input("\nApply these modifications? (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ Modification cancelled")
        sys.exit(0)
    
    # Apply modifications
    tool.apply_modifications(args.output, use_crypto=args.crypto, 
                           is_new_email=args.new_email, realistic_mode=realistic_mode, align_x_headers=args.align_x_headers)
    
    # Show final info
    print("\n" + "="*60)
    print("MODIFICATION COMPLETE")
    print("="*60)
    print(f"✅ Original file: {args.input}")
    print(f"✅ Modified file: {args.output}")
    
    if args.crypto and CRYPTO_AVAILABLE:
        print("\n🔐 Cryptographic signatures applied:")
        print("   - Real DKIM signature added")
        print("   - ARC chain added")
        print(f"   - Keys stored in: ./dkim_keys/")
    elif args.crypto and not CRYPTO_AVAILABLE:
        print("\n⚠️  Crypto features not available - example signatures used")
        print("   Install requirements for real signatures:")
        print("   pip install -r requirements.txt")


if __name__ == '__main__':
    main() 