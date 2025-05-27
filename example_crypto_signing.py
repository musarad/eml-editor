#!/usr/bin/env python3
"""
Example script demonstrating real DKIM and ARC cryptographic signing
"""

import os
import sys
from datetime import datetime
from eml_crypto_signer import EMLCryptoSigner, EMLCryptoEditor, setup_dkim_keys
from eml_advanced_editor import AdvancedEMLEditor


def example_1_generate_keys():
    """Example 1: Generate DKIM keys for a domain"""
    print("\n" + "="*60)
    print("Example 1: Generate DKIM Keys")
    print("="*60)
    
    domain = "example.com"
    selector = "mail2024"
    
    print(f"\nGenerating keys for domain: {domain}")
    print(f"Selector: {selector}")
    
    # Generate keys
    key_info = setup_dkim_keys(domain, selector, key_dir='./dkim_keys')
    
    print("\n✅ Keys generated successfully!")
    print(f"\nTo enable DKIM signing, add this DNS TXT record:")
    print(f"Name: {selector}._domainkey.{domain}")
    print(f"Type: TXT")
    print(f"Value: {key_info['dns_record']}")
    
    return key_info


def example_2_sign_with_real_dkim():
    """Example 2: Sign an email with real DKIM signature"""
    print("\n" + "="*60)
    print("Example 2: Real DKIM Signing")
    print("="*60)
    
    # First, ensure we have keys
    domain = "example.com"
    selector = "mail2024"
    private_key_path = f"./dkim_keys/{domain}.{selector}.private.pem"
    
    if not os.path.exists(private_key_path):
        print("Generating keys first...")
        setup_dkim_keys(domain, selector, key_dir='./dkim_keys')
    
    # Create a sample email
    sample_eml = """From: sender@example.com
To: recipient@example.com
Subject: Test Email with Real DKIM
Date: Mon, 1 Jan 2024 10:00:00 +0000
Message-ID: <test123@example.com>
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8

This email will be signed with a real DKIM signature.
"""
    
    with open('unsigned.eml', 'w') as f:
        f.write(sample_eml)
    
    # Sign the email
    signer = EMLCryptoSigner(private_key_path, selector, domain)
    editor = EMLCryptoEditor('unsigned.eml', signer)
    
    # Add DKIM signature
    editor.add_dkim_signature()
    
    # Save signed email
    editor.save_eml('signed_with_dkim.eml')
    
    print("\n✅ Email signed with DKIM!")
    print("Signed email saved to: signed_with_dkim.eml")
    
    # Show the DKIM signature
    print("\nDKIM-Signature header:")
    print("-" * 40)
    with open('signed_with_dkim.eml', 'r') as f:
        for line in f:
            if line.startswith('DKIM-Signature:'):
                print(line.strip())
                # Continue reading folded header lines
                while True:
                    next_line = f.readline()
                    if next_line.startswith((' ', '\t')):
                        print(next_line.strip())
                    else:
                        break
                break


def example_3_sign_with_arc():
    """Example 3: Add ARC chain to an email"""
    print("\n" + "="*60)
    print("Example 3: ARC (Authenticated Received Chain) Signing")
    print("="*60)
    
    domain = "forwarder.com"
    selector = "arc2024"
    private_key_path = f"./dkim_keys/{domain}.{selector}.private.pem"
    
    if not os.path.exists(private_key_path):
        print("Generating keys for ARC...")
        setup_dkim_keys(domain, selector, key_dir='./dkim_keys')
    
    # Use the previously signed email
    if not os.path.exists('signed_with_dkim.eml'):
        print("Creating DKIM signed email first...")
        example_2_sign_with_real_dkim()
    
    # Sign with ARC (simulating email forwarding)
    signer = EMLCryptoSigner(private_key_path, selector, domain)
    editor = EMLCryptoEditor('signed_with_dkim.eml', signer)
    
    # Add ARC chain
    editor.add_arc_chain({
        'spf': 'pass',
        'dkim': 'pass',
        'dmarc': 'pass'
    })
    
    # Save
    editor.save_eml('signed_with_arc.eml')
    
    print("\n✅ ARC chain added!")
    print("Email with ARC saved to: signed_with_arc.eml")
    
    # Show ARC headers
    print("\nARC headers added:")
    print("-" * 40)
    with open('signed_with_arc.eml', 'r') as f:
        content = f.read()
        for line in content.split('\n'):
            if line.startswith(('ARC-Seal:', 'ARC-Message-Signature:', 'ARC-Authentication-Results:')):
                print(line[:80] + '...' if len(line) > 80 else line)


def example_4_verify_signatures():
    """Example 4: Verify DKIM and ARC signatures"""
    print("\n" + "="*60)
    print("Example 4: Verify Signatures")
    print("="*60)
    
    signer = EMLCryptoSigner()
    
    # Verify DKIM signed email
    if os.path.exists('signed_with_dkim.eml'):
        print("\nVerifying DKIM signature...")
        with open('signed_with_dkim.eml', 'rb') as f:
            import email
            msg = email.message_from_bytes(f.read())
        
        try:
            dkim_valid = signer.verify_dkim(msg)
            print(f"DKIM verification: {'✅ PASS' if dkim_valid else '❌ FAIL'}")
        except Exception as e:
            print(f"DKIM verification error: {e}")
            print("Note: Verification requires DNS records to be published")
    
    # Verify ARC chain
    if os.path.exists('signed_with_arc.eml'):
        print("\nVerifying ARC chain...")
        with open('signed_with_arc.eml', 'rb') as f:
            import email
            msg = email.message_from_bytes(f.read())
        
        try:
            arc_valid, cv = signer.verify_arc(msg)
            print(f"ARC verification: {cv.upper()} {'✅' if arc_valid else '❌'}")
        except Exception as e:
            print(f"ARC verification error: {e}")
            print("Note: Verification requires DNS records to be published")


def example_5_complete_workflow():
    """Example 5: Complete email modification with crypto signing"""
    print("\n" + "="*60)
    print("Example 5: Complete Workflow - Modify and Sign")
    print("="*60)
    
    # Create original email
    original_eml = """From: original@oldcompany.com
To: original@recipient.com
Subject: Original Email
Date: Mon, 1 Jan 2024 10:00:00 +0000
Message-ID: <original@oldcompany.com>
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8

This is the original email content.
"""
    
    with open('workflow_original.eml', 'w') as f:
        f.write(original_eml)
    
    # Step 1: Modify with advanced editor
    print("\nStep 1: Modifying email headers and content...")
    editor = AdvancedEMLEditor('workflow_original.eml')
    
    editor.modify_basic_headers({
        'From': 'int.department@tic.ir',
        'To': 'billing@cellsigma.com',
        'Subject': 'TIC invoice Apr 17'
    })
    
    editor.modify_date('Tue, 23 May 2017 14:59:31 +0430')
    
    editor.create_complete_transport_chain([
        {
            'from': 'zimbra.tic.ir [192.168.39.87]',
            'by': 'mx1.tic.ir',
            'with': 'ESMTP',
            'id': '1224472481.40492',
            'date': datetime(2017, 5, 23, 14, 59, 31)
        }
    ])
    
    editor.save_eml('workflow_modified.eml')
    print("✅ Email modified")
    
    # Step 2: Sign with real DKIM
    print("\nStep 2: Adding real DKIM signature...")
    
    domain = "tic.ir"
    selector = "default"
    private_key_path = f"./dkim_keys/{domain}.{selector}.private.pem"
    
    if not os.path.exists(private_key_path):
        setup_dkim_keys(domain, selector, key_dir='./dkim_keys')
    
    crypto_signer = EMLCryptoSigner(private_key_path, selector, domain)
    crypto_editor = EMLCryptoEditor('workflow_modified.eml', crypto_signer)
    
    crypto_editor.add_dkim_signature()
    crypto_editor.save_eml('workflow_final.eml')
    
    print("✅ DKIM signature added")
    print("\nFinal signed email saved to: workflow_final.eml")
    
    # Show summary
    print("\nEmail transformation summary:")
    print("-" * 40)
    with open('workflow_final.eml', 'r') as f:
        lines = f.readlines()
        for line in lines[:20]:  # Show first 20 lines
            if line.strip() and not line.startswith(' '):
                print(line.strip()[:80] + '...' if len(line.strip()) > 80 else line.strip())


def check_dependencies():
    """Check if crypto dependencies are installed"""
    try:
        import dkim
        import authheaders
        import cryptography
        import dns.resolver
        return True
    except ImportError as e:
        print("\n⚠️  Missing dependencies for cryptographic signing!")
        print("\nPlease install the required packages:")
        print("  pip install -r requirements.txt")
        print("\nOr install individually:")
        print("  pip install dkimpy authheaders cryptography dnspython")
        return False


def main():
    print("EML Crypto Signing Examples")
    print("===========================")
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Cannot proceed without crypto dependencies")
        return
    
    print("\n✅ All dependencies installed!")
    
    # Run examples
    try:
        # Generate keys
        example_1_generate_keys()
        
        # Sign with DKIM
        example_2_sign_with_real_dkim()
        
        # Add ARC chain
        example_3_sign_with_arc()
        
        # Verify signatures
        example_4_verify_signatures()
        
        # Complete workflow
        example_5_complete_workflow()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("All examples completed!")
    print("="*60)
    
    # Cleanup option
    response = input("\nClean up generated files? (y/n): ")
    if response.lower() == 'y':
        cleanup_files = [
            'unsigned.eml', 'signed_with_dkim.eml', 'signed_with_arc.eml',
            'workflow_original.eml', 'workflow_modified.eml', 'workflow_final.eml'
        ]
        for f in cleanup_files:
            if os.path.exists(f):
                os.remove(f)
        print("Temporary files cleaned up (keys preserved in ./dkim_keys/)")


if __name__ == '__main__':
    main() 