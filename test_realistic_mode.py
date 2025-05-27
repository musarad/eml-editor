#!/usr/bin/env python3
"""
Test script to demonstrate realistic vs legacy mode fixes
"""

import os
import sys
from eml_unified_tool import UnifiedEMLTool
from eml_advanced_editor import AdvancedEMLEditor
import email.mime.multipart
import email.mime.text
import email.utils

def create_test_email():
    """Create a test email for comparison"""
    msg = email.mime.multipart.MIMEMultipart('mixed')
    
    # Headers
    msg['From'] = 'test.sender@oldcompany.com'
    msg['To'] = 'test.recipient@newcompany.com'
    msg['Subject'] = 'Test Invoice'
    msg['Date'] = email.utils.formatdate(localtime=True)
    msg['Message-ID'] = '<test123@oldcompany.com>'
    
    # Add some authentication headers (typical of real email)
    msg['Authentication-Results'] = 'mx.google.com; spf=pass smtp.mailfrom=oldcompany.com; dkim=pass header.d=oldcompany.com'
    
    # Body
    body = email.mime.text.MIMEText('Please find attached test invoice.', 'plain')
    msg.attach(body)
    
    # Save
    with open('test_original.eml', 'wb') as f:
        f.write(msg.as_bytes())
    
    print("Created test_original.eml")

def test_legacy_mode():
    """Test legacy mode (problematic)"""
    print("\n" + "="*60)
    print("TESTING LEGACY MODE (PROBLEMATIC)")
    print("="*60)
    
    tool = UnifiedEMLTool('test_original.eml')
    
    # Make modifications
    tool.modifications = {
        'headers': {
            'From': 'int.department@tic.ir',
            'To': 'billing@newcompany.com',
            'Subject': 'TIC Invoice Modified'
        },
        'date': 'Tue, 23 May 2017 14:59:31 +0430'
    }
    
    # Apply with legacy mode (realistic_mode=False)
    tool.apply_modifications('test_legacy.eml', use_crypto=False, realistic_mode=False)
    
    print("\n🔍 LEGACY MODE ANALYSIS:")
    editor = AdvancedEMLEditor('test_legacy.eml')
    validation = editor.validate_authentication_consistency()
    
    if validation['warnings']:
        print("❌ PROBLEMS DETECTED:")
        for warning in validation['warnings']:
            print(f"   - {warning}")
    else:
        print("✅ No problems detected")

def test_realistic_mode():
    """Test realistic mode (fixed)"""
    print("\n" + "="*60)
    print("TESTING REALISTIC MODE (FIXED)")
    print("="*60)
    
    tool = UnifiedEMLTool('test_original.eml')
    
    # Same modifications
    tool.modifications = {
        'headers': {
            'From': 'int.department@tic.ir',
            'To': 'billing@newcompany.com', 
            'Subject': 'TIC Invoice Modified'
        },
        'date': 'Tue, 23 May 2017 14:59:31 +0430'
    }
    
    # Apply with realistic mode (realistic_mode=True)
    tool.apply_modifications('test_realistic.eml', use_crypto=False, realistic_mode=True)
    
    print("\n🔍 REALISTIC MODE ANALYSIS:")
    editor = AdvancedEMLEditor('test_realistic.eml')
    validation = editor.validate_authentication_consistency()
    
    if validation['warnings']:
        print("❌ PROBLEMS DETECTED:")
        for warning in validation['warnings']:
            print(f"   - {warning}")
    else:
        print("✅ No authentication inconsistencies detected")

def compare_outputs():
    """Compare the two outputs side by side"""
    print("\n" + "="*60)
    print("COMPARISON OF OUTPUTS")
    print("="*60)
    
    print("\n📄 LEGACY MODE AUTHENTICATION HEADERS:")
    with open('test_legacy.eml', 'r') as f:
        lines = f.readlines()
        for line in lines:
            if any(header in line for header in ['Authentication-Results', 'DKIM-Signature']):
                print(f"   {line.strip()}")
    
    print("\n📄 REALISTIC MODE AUTHENTICATION HEADERS:")
    with open('test_realistic.eml', 'r') as f:
        lines = f.readlines()
        for line in lines:
            if any(header in line for header in ['Authentication-Results', 'DKIM-Signature']):
                print(f"   {line.strip()}")
    
    print("\n📊 SUMMARY:")
    print("   Legacy Mode: Claims DKIM/DMARC pass with fake signatures")
    print("   Realistic Mode: Honest authentication results, no false claims")

def main():
    """Main test function"""
    print("🧪 EML Editor Realism Fix Test")
    print("=" * 60)
    
    # Create test email
    create_test_email()
    
    # Test both modes
    test_legacy_mode()
    test_realistic_mode()
    
    # Compare results
    compare_outputs()
    
    # Cleanup
    print("\n🧹 Cleaning up test files...")
    for file in ['test_original.eml', 'test_legacy.eml', 'test_realistic.eml']:
        if os.path.exists(file):
            os.remove(file)
    
    print("\n✅ Test completed!")

if __name__ == '__main__':
    main() 