#!/usr/bin/env python3
"""
Advanced EML File Editor - Extended functionality for authentication headers
"""

from eml_editor import EMLEditor
import json
import sys
from datetime import datetime, timedelta
import re
import os
from typing import Dict, List
import random
import email.utils


class AdvancedEMLEditor(EMLEditor):
    """Extended EML editor with advanced authentication features"""
    
    def modify_received_headers(self, modifications: list):
        """
        Modify Received headers with detailed control
        Example: [
            {
                'index': 0,  # Which Received header to modify (0 = topmost/newest)
                'by': '10.159.59.83',
                'from': 'mail.example.com',
                'with': 'SMTP',
                'id': 'j19csp1780682uah',
                'date': 'Tue, 23 May 2017 03:35:36 -0700 (PDT)'
            }
        ]
        """
        received_headers = self.msg.get_all('Received', [])
        
        for mod in modifications:
            idx = mod.get('index', 0)
            if idx < len(received_headers):
                # Parse existing header
                header = received_headers[idx]
                
                # Build new header
                new_parts = []
                
                if 'from' in mod:
                    new_parts.append(f"from {mod['from']}")
                
                if 'by' in mod:
                    new_parts.append(f"by {mod['by']}")
                
                if 'with' in mod:
                    new_parts.append(f"with {mod['with']}")
                
                if 'id' in mod:
                    new_parts.append(f"id {mod['id']}")
                
                # Join parts and add date
                new_header = ' '.join(new_parts)
                if 'date' in mod:
                    new_header += f"; {mod['date']}"
                
                received_headers[idx] = new_header
        
        # Update headers
        del self.msg['Received']
        for header in received_headers:
            self.msg['Received'] = header
    
    def add_received_header(self, by_host: str, from_host: str = None, 
                          protocol: str = 'SMTP', id_string: str = None,
                          timestamp: datetime = None):
        """Add a new Received header at the top"""
        if timestamp is None:
            timestamp = datetime.now()
        
        if id_string is None:
            id_string = f"id{int(timestamp.timestamp())}"
        
        parts = []
        if from_host:
            parts.append(f"from {from_host}")
        parts.append(f"by {by_host}")
        parts.append(f"with {protocol}")
        parts.append(f"id {id_string}")
        
        date_str = timestamp.strftime("%a, %d %b %Y %H:%M:%S %z")
        if not date_str.endswith((' +0000', ' -0000')):
            # Add timezone if not present
            date_str += ' +0000'
        
        new_header = f"{' '.join(parts)}; {date_str}"
        
        # Get existing headers
        existing = self.msg.get_all('Received', [])
        
        # Clear and re-add with new one first
        del self.msg['Received']
        self.msg['Received'] = new_header
        
        for header in existing:
            self.msg['Received'] = header
    
    def modify_arc_headers(self, instance: int = 1, domain: str = 'example.com',
                          results: dict = None):
        """
        Modify or create ARC headers
        Note: This creates example ARC headers. Real ARC requires cryptographic signing.
        """
        if results is None:
            results = {
                'spf': 'pass',
                'dkim': 'pass',
                'dmarc': 'pass'
            }
        
        # ARC-Authentication-Results
        auth_results_parts = []
        auth_results_parts.append(f"i={instance}")
        auth_results_parts.append(domain)
        
        for check, result in results.items():
            auth_results_parts.append(f"{check}={result}")
        
        arc_auth_results = '; '.join(auth_results_parts)
        
        # ARC-Message-Signature (example - real one needs crypto)
        arc_msg_sig = (
            f"i={instance}; a=rsa-sha256; c=relaxed/relaxed; "
            f"d={domain}; s=arc-20160816; "
            f"h=from:to:subject:date:message-id:mime-version; "
            f"bh=ExampleBase64Hash==; "
            f"b=ExampleSignatureBase64=="
        )
        
        # ARC-Seal (example - real one needs crypto)
        arc_seal = (
            f"i={instance}; a=rsa-sha256; t={int(datetime.now().timestamp())}; "
            f"cv=none; d={domain}; s=arc-20160816; "
            f"b=ExampleSealBase64=="
        )
        
        # Update headers
        del self.msg['ARC-Authentication-Results']
        del self.msg['ARC-Message-Signature']
        del self.msg['ARC-Seal']
        
        self.msg['ARC-Authentication-Results'] = arc_auth_results
        self.msg['ARC-Message-Signature'] = arc_msg_sig
        self.msg['ARC-Seal'] = arc_seal
    
    def modify_authentication_results(self, domain: str, results: dict, validate_consistency: bool = True):
        """
        Modify authentication headers with optional consistency validation
        
        Args:
            domain: Authenticating domain
            results: Dictionary of authentication results
            validate_consistency: Whether to validate against actual signatures
        """
        parts = [domain]
        
        # SPF
        if 'spf' in results:
            spf = results['spf']
            spf_str = f"spf={spf['result']}"
            if 'domain' in spf:
                spf_str += f" smtp.mailfrom={spf['domain']}"
            parts.append(spf_str)
        
        # DKIM
        if 'dkim' in results:
            dkim = results['dkim']
            dkim_str = f"dkim={dkim['result']}"
            if 'domain' in dkim:
                dkim_str += f" header.i=@{dkim['domain']}"
            if 'selector' in dkim:
                dkim_str += f" header.s={dkim['selector']}"
            parts.append(dkim_str)
        
        # DMARC
        if 'dmarc' in results:
            dmarc = results['dmarc']
            dmarc_str = f"dmarc={dmarc['result']}"
            if 'policy' in dmarc:
                dmarc_str += f" policy.dmarc={dmarc['policy']}"
            parts.append(dmarc_str)
        
        # ARC
        if 'arc' in results:
            arc = results['arc']
            parts.append(f"arc={arc['result']}")
        
        # Build header
        auth_header = ";\n\t".join(parts)
        
        # Remove existing Authentication-Results header
        if 'Authentication-Results' in self.msg:
            del self.msg['Authentication-Results']
        self.msg['Authentication-Results'] = auth_header
        
        # Validate consistency if requested
        if validate_consistency:
            validation = self.validate_authentication_consistency()
            if validation['warnings']:
                print("⚠️  Authentication consistency warnings:")
                for warning in validation['warnings']:
                    print(f"   - {warning}")
                print("   Consider using real cryptographic signing for authenticity")
    
    def add_dkim_signature(self, domain: str, selector: str = 's1', use_real_crypto: bool = False):
        """
        Add DKIM-Signature header - either real cryptographic signature or clear placeholder
        
        Args:
            domain: Signing domain
            selector: DKIM selector
            use_real_crypto: If True, attempts real DKIM signing. If False, adds clear placeholder.
        
        Note: For real DKIM signing, use eml_crypto_signer.py instead
        """
        if use_real_crypto:
            # Try to use real crypto signer
            try:
                from eml_crypto_signer import EMLCryptoSigner, EMLCryptoEditor
                private_key_path = f'./dkim_keys/{domain}.{selector}.private.pem'
                
                if os.path.exists(private_key_path):
                    # Use real crypto signing
                    signer = EMLCryptoSigner(private_key_path, selector, domain)
                    temp_path = 'temp_for_dkim_signing.eml'
                    self.save_eml(temp_path)
                    
                    crypto_editor = EMLCryptoEditor(temp_path, signer)
                    crypto_editor.add_dkim_signature()
                    
                    # Reload the signed message
                    self.load_eml(temp_path)
                    os.remove(temp_path)
                    return
                else:
                    print(f"⚠️  DKIM private key not found at {private_key_path}")
                    print("   Use eml_crypto_signer.py to generate keys first")
            except ImportError:
                print("⚠️  Crypto dependencies not available for real DKIM signing")
        
        # Create a clearly marked placeholder signature
        dkim_sig = (
            f"v=1; a=rsa-sha256; c=relaxed/relaxed; d={domain}; "
            f"s={selector}; h=from:to:subject:date:message-id; "
            f"bh=PLACEHOLDER_BODY_HASH_NOT_VALID; "
            f"b=PLACEHOLDER_SIGNATURE_NOT_VALID"
        )
        
        # Remove existing DKIM signature
        if 'DKIM-Signature' in self.msg:
            del self.msg['DKIM-Signature']
        self.msg['DKIM-Signature'] = dkim_sig
        
        print("⚠️  Added PLACEHOLDER DKIM signature (not cryptographically valid)")
        print("   For real DKIM signing, use use_real_crypto=True or eml_crypto_signer.py")
    
    def modify_x_headers(self, x_headers: dict):
        """
        Modify custom X- headers
        Example: {
            'X-Originating-IP': '[192.168.1.100]',
            'X-Mailer': 'Custom Mailer 1.0',
            'X-Spam-Score': '0.0',
            'X-Virus-Scanned': 'ClamAV at example.com'
        }
        """
        for header_name, header_value in x_headers.items():
            if header_name.startswith('X-'):
                del self.msg[header_name]
                self.msg[header_name] = header_value
    
    def create_complete_transport_chain(self, hops: list, preserve_original_hops: int = 2):
        """
        Create a complete transport chain with multiple hops, optionally preserving some original hops
        
        Args:
            hops: List of hop dictionaries to add
            preserve_original_hops: Number of original Received headers to preserve (0 = replace all)
        
        Example hops: [
            {
                'from': 'client.example.com [192.168.1.100]',
                'by': 'smtp.example.com',
                'with': 'ESMTP',
                'id': 'abc123',
                'for': '<recipient@example.com>',
                'date': datetime.now()
            }
        ]
        """
        # Preserve some original Received headers for realism
        original_received = []
        if preserve_original_hops > 0:
            existing_received = self.msg.get_all('Received', [])
            if existing_received:
                # Keep the last N received headers (most recent ones)
                original_received = existing_received[:preserve_original_hops]
                print(f"🔄 Preserving {len(original_received)} original Received headers for realism")
        
        # Clear all existing Received headers
        del self.msg['Received']
        
        # Add preserved headers first (they should appear first in the email)
        for received_header in original_received:
            self.msg['Received'] = received_header
        
        # Add new hops in reverse order (newest first)
        for hop in reversed(hops):
            parts = []
            
            if 'from' in hop:
                parts.append(f"from {hop['from']}")
            
            parts.append(f"by {hop['by']}")
            
            if 'with' in hop:
                parts.append(f"with {hop['with']}")
            
            if 'id' in hop:
                parts.append(f"id {hop['id']}")
            
            if 'for' in hop:
                parts.append(f"for {hop['for']}")
            
            # Format date
            date = hop.get('date', datetime.now())
            date_str = date.strftime("%a, %d %b %Y %H:%M:%S %z")
            if not re.search(r'[+-]\d{4}$', date_str):
                date_str += ' +0000'
            
            header = f"{' '.join(parts)}; {date_str}"
            self.msg['Received'] = header

    def validate_authentication_consistency(self) -> Dict[str, bool]:
        """
        Validate that authentication results match actual signatures in the message
        
        Returns:
            Dict with validation results for each authentication method
        """
        validation = {
            'dkim_consistent': True,
            'arc_consistent': True,
            'warnings': []
        }
        
        # Check DKIM consistency
        auth_results = self.msg.get('Authentication-Results', '')
        dkim_signature = self.msg.get('DKIM-Signature', '')
        
        if 'dkim=pass' in auth_results:
            if not dkim_signature:
                validation['dkim_consistent'] = False
                validation['warnings'].append("Authentication-Results claims dkim=pass but no DKIM-Signature header found")
            elif 'PLACEHOLDER' in dkim_signature or 'Example' in dkim_signature:
                validation['dkim_consistent'] = False
                validation['warnings'].append("Authentication-Results claims dkim=pass but DKIM-Signature is placeholder/example")
        
        # Check ARC consistency
        arc_auth_results = self.msg.get('ARC-Authentication-Results', '')
        arc_seal = self.msg.get('ARC-Seal', '')
        arc_message_sig = self.msg.get('ARC-Message-Signature', '')
        
        if arc_auth_results and ('dkim=pass' in arc_auth_results or 'spf=pass' in arc_auth_results):
            if not arc_seal or not arc_message_sig:
                validation['arc_consistent'] = False
                validation['warnings'].append("ARC-Authentication-Results present but missing ARC-Seal or ARC-Message-Signature")
            elif 'Example' in arc_seal or 'PLACEHOLDER' in arc_seal:
                validation['arc_consistent'] = False
                validation['warnings'].append("ARC headers contain placeholder/example data")
        
        return validation

    def preserve_original_signatures(self) -> Dict[str, str]:
        """
        Preserve original DKIM and ARC signatures
        
        Returns:
            Dictionary with preserved signatures
        """
        preserved = {}
        
        # Preserve DKIM-Signature
        dkim_sig = self.msg.get('DKIM-Signature', '')
        if dkim_sig and 'PLACEHOLDER' not in dkim_sig and 'Example' not in dkim_sig:
            preserved['DKIM-Signature'] = dkim_sig
            print(f"🔐 Preserved original DKIM signature")
        
        # Preserve ARC headers
        arc_seal = self.msg.get('ARC-Seal', '')
        if arc_seal and 'Example' not in arc_seal:
            preserved['ARC-Seal'] = arc_seal
            
        arc_msg_sig = self.msg.get('ARC-Message-Signature', '')
        if arc_msg_sig and 'Example' not in arc_msg_sig:
            preserved['ARC-Message-Signature'] = arc_msg_sig
            
        arc_auth = self.msg.get('ARC-Authentication-Results', '')
        if arc_auth:
            preserved['ARC-Authentication-Results'] = arc_auth
            
        if 'ARC-Seal' in preserved:
            print(f"🔐 Preserved original ARC chain")
            
        return preserved
    
    def restore_preserved_signatures(self, preserved: Dict[str, str]):
        """Restore preserved signatures to the message"""
        for header, value in preserved.items():
            if header in self.msg:
                del self.msg[header]
            self.msg[header] = value
    
    def manage_google_headers(self, transport_chain: List[Dict]):
        """
        Manage Google-specific headers based on transport chain
        
        Args:
            transport_chain: List of transport hops
        """
        # Check if email actually routes through Google
        routes_through_google = any(
            'google.com' in hop.get('by', '') or 
            'gmail.com' in hop.get('by', '') or
            'googlemail.com' in hop.get('by', '')
            for hop in transport_chain
        )
        
        if routes_through_google:
            # Generate appropriate Google headers
            if 'X-Google-Smtp-Source' not in self.msg:
                # Generate a realistic-looking ID
                import string
                chars = string.ascii_letters + string.digits + '+/='
                google_id = ''.join(random.choice(chars) for _ in range(76))
                self.msg['X-Google-Smtp-Source'] = google_id
                print("✅ Added X-Google-Smtp-Source (routes through Google)")
        else:
            # Remove Google headers if not routing through Google
            google_headers = ['X-Google-Smtp-Source', 'X-Google-DKIM-Signature']
            for header in google_headers:
                if header in self.msg:
                    del self.msg[header]
                    print(f"🗑️ Removed {header} (not routing through Google)")
    
    def fix_message_id_domain(self):
        """Fix Message-ID to use proper domain instead of gmail.com"""
        current_msg_id = self.msg.get('Message-ID', '')
        from_header = self.msg.get('From', '')
        
        # Extract sender domain
        if '@' in from_header:
            from email.utils import parseaddr
            _, email_addr = parseaddr(from_header)
            if '@' in email_addr:
                sender_domain = email_addr.split('@')[1]
            else:
                sender_domain = 'example.com'
        else:
            sender_domain = 'example.com'
        
        # Check if Message-ID uses wrong domain
        if '@mail.gmail.com>' in current_msg_id or '@gmail.com>' in current_msg_id:
            # Extract the ID part
            if '<' in current_msg_id:
                id_part = current_msg_id.split('<')[1].split('@')[0]
            else:
                id_part = str(int(datetime.now().timestamp()))
            
            # Generate new Message-ID with proper domain
            new_msg_id = f"<{id_part}@{sender_domain}>"
            
            del self.msg['Message-ID']
            self.msg['Message-ID'] = new_msg_id
            print(f"🆔 Fixed Message-ID domain: {new_msg_id}")

    def preserve_x_headers(self) -> Dict[str, List[str]]:
        """
        Preserve all X- headers from the original message
        
        Returns:
            Dictionary of X-headers and their values
        """
        preserved_x = {}
        
        for header, value in self.msg.items():
            if header.startswith('X-'):
                if header not in preserved_x:
                    preserved_x[header] = []
                preserved_x[header].append(value)
        
        if preserved_x:
            print(f"📋 Preserved {len(preserved_x)} X-headers")
            
        return preserved_x
    
    def restore_x_headers(self, preserved_x: Dict[str, List[str]]):
        """Restore preserved X-headers to the message"""
        for header, values in preserved_x.items():
            # Remove existing instances
            if header in self.msg:
                del self.msg[header]
            # Add back all values
            for value in values:
                self.msg[header] = value
        
        if preserved_x:
            print(f"♻️ Restored {len(preserved_x)} X-headers")

    def generate_aligned_x_headers(self, routes_through_google: bool = False) -> Dict[str, str]:
        """
        Generate X-headers that align with the current message state
        
        Args:
            routes_through_google: Whether the message routes through Google
            
        Returns:
            Dictionary of aligned X-headers
        """
        aligned_headers = {}
        
        if routes_through_google:
            # Generate new X-Google-Smtp-Source that aligns with current message
            import string
            import hashlib
            
            # Create a hash based on current message content for uniqueness
            msg_content = str(self.msg)
            content_hash = hashlib.sha256(msg_content.encode()).digest()
            
            # Generate Google-style ID incorporating the content hash
            chars = string.ascii_letters + string.digits + '+/='
            # Use first 8 bytes of hash to seed the ID generation
            seed_value = int.from_bytes(content_hash[:8], 'big')
            random.seed(seed_value)  # Deterministic based on content
            
            google_id = ''.join(random.choice(chars) for _ in range(76))
            aligned_headers['X-Google-Smtp-Source'] = google_id
            
            # Generate X-Received header
            date_header = self.msg.get('Date', '')
            if date_header:
                try:
                    msg_date = email.utils.parsedate_to_datetime(date_header)
                except:
                    msg_date = datetime.now()
            else:
                msg_date = datetime.now()
                
            # Generate X-Received in Google's format
            x_received = (
                f"by 2002:a05:6808:{random.randint(1000,9999)}:b0:"
                f"{random.randint(100,999)}:{random.randint(1000000,9999999)} "
                f"with SMTP id {random.choice(string.ascii_lowercase)}"
                f"{random.randint(10,99)}-{random.randint(10000000,99999999)}"
                f".{random.randint(100,999)}.{int(msg_date.timestamp())}; "
                f"{msg_date.strftime('%a, %d %b %Y %H:%M:%S %z')}"
            )
            aligned_headers['X-Received'] = x_received
            
            print("🔄 Generated aligned Google X-headers based on current message state")
            
        # Reset random seed to avoid affecting other operations
        random.seed()
        
        return aligned_headers
    
    def update_x_headers_for_alignment(self, force_google_headers: bool = None):
        """
        Update X-headers to align with current message modifications
        
        Args:
            force_google_headers: If True, add Google headers. If False, remove them.
                                If None, auto-detect based on transport chain.
        """
        # Auto-detect if we should have Google headers
        if force_google_headers is None:
            received_headers = self.msg.get_all('Received', [])
            routes_through_google = any(
                'google' in h.lower() or 'gmail' in h.lower() 
                for h in received_headers
            )
        else:
            routes_through_google = force_google_headers
            
        if routes_through_google:
            # Generate aligned headers
            aligned_headers = self.generate_aligned_x_headers(routes_through_google=True)
            
            # Update the headers
            for header, value in aligned_headers.items():
                if header in self.msg:
                    del self.msg[header]
                self.msg[header] = value
                
            print(f"✅ Updated {len(aligned_headers)} X-headers to align with modifications")
        else:
            # Remove Google-specific X-headers if not routing through Google
            google_x_headers = ['X-Google-Smtp-Source', 'X-Received']
            removed_count = 0
            for header in google_x_headers:
                if header in self.msg:
                    del self.msg[header]
                    removed_count += 1
                    
            if removed_count > 0:
                print(f"🗑️ Removed {removed_count} Google X-headers (not routing through Google)")


def example_usage():
    """Example of how to use the advanced editor"""
    
    # Example 1: Basic modifications
    print("Example 1: Basic EML modifications")
    print("-" * 50)
    
    # Create a sample EML file for demonstration
    sample_eml = """From: sender@example.com
To: recipient@example.com
Subject: Test Email
Date: Mon, 1 Jan 2024 10:00:00 +0000
Message-ID: <123456@example.com>
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8

This is a test email.
"""
    
    with open('sample.eml', 'w') as f:
        f.write(sample_eml)
    
    # Edit the email
    editor = AdvancedEMLEditor('sample.eml')
    
    # Modify basic headers
    editor.modify_basic_headers({
        'From': 'int.department@tic.ir',
        'To': 'unal.abaci@cellsigma.com, billing@cellsigma.com',
        'Subject': 'TIC invoice Apr 17'
    })
    
    # Modify date
    editor.modify_date('Tue, 23 May 2017 14:59:31 +0430')
    
    # Add transport headers
    editor.modify_transport_headers({
        'Delivered-To': 'billing@cellsigma.com',
        'Return-Path': '<int.department@tic.ir>'
    })
    
    # Add authentication results
    editor.modify_authentication_results('mx.google.com', {
        'spf': {'result': 'pass', 'domain': 'tic.ir'},
        'dkim': {'result': 'pass', 'domain': 'tic.ir'},
        'dmarc': {'result': 'pass', 'policy': 'none'},
        'arc': {'result': 'pass'}
    })
    
    # Add received headers
    editor.create_complete_transport_chain([
        {
            'from': 'zimbra.tic.ir [192.168.39.87]',
            'by': 'mx1.tic.ir',
            'with': 'ESMTP',
            'id': '1224472481.40492',
            'date': datetime(2017, 5, 23, 14, 59, 31)
        },
        {
            'from': 'mx1.tic.ir [mail.tic.ir]',
            'by': 'mx.google.com',
            'with': 'ESMTPS',
            'id': 'd17mr1768016wmd.90.1495535736487',
            'for': '<billing@cellsigma.com>',
            'date': datetime(2017, 5, 23, 10, 35, 36)  # UTC
        },
        {
            'from': 'mx.google.com',
            'by': '10.159.59.83',
            'with': 'SMTP',
            'id': 'j19csp1780682uah',
            'date': datetime(2017, 5, 23, 10, 35, 36)  # UTC
        }
    ])
    
    # Add X-headers
    editor.modify_x_headers({
        'X-Originating-IP': '[192.168.39.87]',
        'X-Mailer': 'Zimbra 8.6.0_GA_1194',
        'X-Virus-Scanned': 'amavisd-new at tic.ir'
    })
    
    # Add ARC headers
    editor.modify_arc_headers(1, 'google.com', {
        'spf': 'pass',
        'dkim': 'pass',
        'dmarc': 'pass'
    })
    
    # Add DKIM signature
    editor.add_dkim_signature('tic.ir', 's1')
    
    # Save the modified email
    editor.save_eml('modified_complete.eml')
    
    print("Modified email saved to: modified_complete.eml")
    print("\nHeaders in modified email:")
    headers = editor.get_headers()
    for key, value in headers.items():
        if isinstance(value, list):
            print(f"{key}:")
            for v in value:
                print(f"  {v[:100]}...")
        else:
            print(f"{key}: {value[:100]}...")


def create_example_config():
    """Create an example configuration file for batch processing"""
    
    config = {
        "modifications": {
            "basic_headers": {
                "From": "int.department@tic.ir",
                "To": "unal.abaci@cellsigma.com, billing@cellsigma.com",
                "Subject": "TIC invoice Apr 17"
            },
            "date": "Tue, 23 May 2017 14:59:31 +0430",
            "transport_headers": {
                "Delivered-To": "billing@cellsigma.com",
                "Return-Path": "<int.department@tic.ir>"
            },
            "authentication": {
                "domain": "mx.google.com",
                "results": {
                    "spf": {"result": "pass", "domain": "tic.ir"},
                    "dkim": {"result": "pass", "domain": "tic.ir"},
                    "dmarc": {"result": "pass", "policy": "none"}
                }
            },
            "x_headers": {
                "X-Originating-IP": "[192.168.39.87]",
                "X-Mailer": "Zimbra 8.6.0_GA_1194",
                "X-Virus-Scanned": "amavisd-new at tic.ir"
            },
            "attachments": {
                "add": [],
                "remove": [],
                "replace": []
            }
        }
    }
    
    with open('eml_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print("Example configuration saved to: eml_config.json")


def process_with_config(eml_path: str, config_path: str, output_path: str):
    """Process an EML file using a configuration file"""
    
    # Load configuration
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Create editor
    editor = AdvancedEMLEditor(eml_path)
    
    mods = config.get('modifications', {})
    
    # Apply modifications
    if 'basic_headers' in mods:
        editor.modify_basic_headers(mods['basic_headers'])
    
    if 'date' in mods:
        editor.modify_date(mods['date'])
    
    if 'transport_headers' in mods:
        editor.modify_transport_headers(mods['transport_headers'])
    
    if 'authentication' in mods:
        auth = mods['authentication']
        editor.modify_authentication_results(
            auth.get('domain', 'mx.google.com'),
            auth.get('results', {}),
            validate_consistency=True
        )
    
    if 'x_headers' in mods:
        editor.modify_x_headers(mods['x_headers'])
    
    # Handle attachments
    if 'attachments' in mods:
        atts = mods['attachments']
        
        for file_path in atts.get('add', []):
            editor.add_attachment(file_path)
        
        for filename in atts.get('remove', []):
            editor.remove_attachment(filename)
        
        for old_name, new_file in atts.get('replace', []):
            editor.replace_attachment(old_name, new_file)
    
    # Save
    editor.save_eml(output_path)
    print(f"Processed email saved to: {output_path}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Advanced EML Editor')
    parser.add_argument('--example', action='store_true', 
                       help='Run example usage')
    parser.add_argument('--create-config', action='store_true',
                       help='Create example configuration file')
    parser.add_argument('--process', nargs=3, 
                       metavar=('EML_FILE', 'CONFIG_FILE', 'OUTPUT_FILE'),
                       help='Process EML file with configuration')
    
    args = parser.parse_args()
    
    if args.example:
        example_usage()
    elif args.create_config:
        create_example_config()
    elif args.process:
        process_with_config(*args.process)
    else:
        parser.print_help() 