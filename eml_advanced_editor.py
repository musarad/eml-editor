#!/usr/bin/env python3
"""
Advanced EML File Editor - Extended functionality for authentication headers
"""

from eml_editor import EMLEditor
import json
import sys
from datetime import datetime, timedelta
import re


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
    
    def modify_authentication_results(self, domain: str, results: dict):
        """
        Create comprehensive Authentication-Results header
        Example results: {
            'spf': {'result': 'pass', 'domain': 'example.com'},
            'dkim': {'result': 'pass', 'domain': 'example.com', 'selector': 's1'},
            'dmarc': {'result': 'pass', 'policy': 'none'},
            'arc': {'result': 'pass'}
        }
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
        
        del self.msg['Authentication-Results']
        self.msg['Authentication-Results'] = auth_header
    
    def add_dkim_signature(self, domain: str, selector: str = 's1'):
        """
        Add example DKIM-Signature header
        Note: This is an example. Real DKIM requires private key signing.
        """
        dkim_sig = (
            f"v=1; a=rsa-sha256; c=relaxed/relaxed; d={domain}; "
            f"s={selector}; h=from:to:subject:date:message-id; "
            f"bh=ExampleBodyHash==; "
            f"b=ExampleDKIMSignature=="
        )
        
        del self.msg['DKIM-Signature']
        self.msg['DKIM-Signature'] = dkim_sig
    
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
    
    def create_complete_transport_chain(self, hops: list):
        """
        Create a complete transport chain with multiple hops
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
        # Clear existing Received headers
        del self.msg['Received']
        
        # Add hops in reverse order (newest first)
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
            auth.get('results', {})
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