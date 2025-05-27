#!/usr/bin/env python3
"""
Test script to demonstrate authentication fixes
Shows before/after comparison of manipulation detection issues
"""

import os
import email
import email.mime.multipart
import email.mime.text
import email.utils
from datetime import datetime, timedelta
from eml_unified_tool import UnifiedEMLTool
from eml_advanced_editor import AdvancedEMLEditor


def create_problematic_email():
    """Create an email with all the manipulation detection issues"""
    msg = email.mime.multipart.MIMEMultipart('mixed')
    
    # Headers that will cause detection
    msg['From'] = 'info@marmaristrading.com'
    msg['To'] = 'i.mohaddes@kpic.ir, ceo@kpic.ir'
    msg['Subject'] = 'Follow'
    msg['Date'] = 'Sat, 20 Aug 2022 18:31:00 +0300'
    msg['Message-ID'] = '<1661009460.523e1f0b@mail.gmail.com>'  # Wrong domain!
    
    # Problematic authentication results (claims pass without signature)
    msg['Authentication-Results'] = '''mx.google.com;
    spf=pass smtp.mailfrom=marmaristrading.com;
    dkim=pass header.i=@marmaristrading.com;
    dmarc=pass policy.dmarc=none;
    arc=pass'''
    
    # Google header without proper routing
    msg['X-Google-Smtp-Source'] = 'AGHT+IF7dHqFaLEbIeHVKw+1mV+4R30t6UAsLO32LHQJRGgsQkupX9UhG/6kDdmNmgqUnOMFzSKiYfYK+9yHxsvLpQ=='
    
    # NO DKIM-Signature header (but claims dkim=pass!)
    
    # Limited transport chain
    msg['Received'] = '''from client.marmaristrading.com [192.168.1.184]
    by smtp.marmaristrading.com with ESMTPS id 1661009460.77552.client.marmaristradingcom;
    Sat, 20 Aug 2022 18:31:00 +0300'''
    
    # Body
    body_part = email.mime.multipart.MIMEMultipart('alternative')
    text_content = "This is a test email with authentication issues."
    body_part.attach(email.mime.text.MIMEText(text_content, 'plain'))
    msg.attach(body_part)
    
    return msg


def analyze_email_issues(eml_path):
    """Analyze an email for manipulation detection issues"""
    with open(eml_path, 'r') as f:
        msg = email.message_from_file(f)
    
    issues = []
    
    # Check 1: DKIM consistency
    auth_results = msg.get('Authentication-Results', '')
    dkim_sig = msg.get('DKIM-Signature', '')
    
    if 'dkim=pass' in auth_results and not dkim_sig:
        issues.append("❌ Claims dkim=pass but no DKIM-Signature header")
    elif 'dkim=pass' in auth_results and ('PLACEHOLDER' in dkim_sig or 'Example' in dkim_sig):
        issues.append("❌ Fake DKIM signature with dkim=pass claim")
    
    # Check 2: Message-ID domain
    msg_id = msg.get('Message-ID', '')
    from_addr = msg.get('From', '')
    
    if '@' in from_addr:
        sender_domain = from_addr.split('@')[1].strip('>')
        if '@mail.gmail.com>' in msg_id and 'gmail' not in sender_domain:
            issues.append(f"❌ Message-ID uses gmail.com but sender is {sender_domain}")
    
    # Check 3: Google headers without Google routing
    google_header = msg.get('X-Google-Smtp-Source', '')
    received_headers = msg.get_all('Received', [])
    routes_through_google = any('google' in h or 'gmail' in h for h in received_headers)
    
    if google_header and not routes_through_google:
        issues.append("❌ Has X-Google-Smtp-Source but doesn't route through Google")
    
    # Check 4: Limited Received headers
    if len(received_headers) < 3:
        issues.append(f"❌ Only {len(received_headers)} Received headers (suspicious)")
    
    # Check 5: Timestamp consistency
    date_header = msg.get('Date', '')
    if date_header:
        try:
            msg_date = email.utils.parsedate_to_datetime(date_header)
            for received in received_headers:
                if ';' in received:
                    received_date_str = received.split(';')[-1].strip()
                    try:
                        received_date = email.utils.parsedate_to_datetime(received_date_str)
                        if received_date < msg_date:
                            issues.append("❌ Received header timestamp before Date header")
                    except:
                        pass
        except:
            pass
    
    return issues


def main():
    """Test the authentication fixes"""
    print("🧪 TESTING AUTHENTICATION FIXES")
    print("="*60)
    
    # Create problematic email
    print("\n📧 Creating email with manipulation detection issues...")
    problematic_msg = create_problematic_email()
    
    # Save it
    problematic_path = 'test_problematic.eml'
    with open(problematic_path, 'w') as f:
        f.write(problematic_msg.as_string())
    
    # Analyze issues
    print("\n🔍 Analyzing problematic email...")
    issues = analyze_email_issues(problematic_path)
    
    print("\nIssues found in original email:")
    for issue in issues:
        print(f"  {issue}")
    
    # Now fix it with our tool
    print("\n🔧 Applying fixes with unified tool...")
    
    # Test 1: Legacy mode (should maintain issues)
    print("\n--- TEST 1: Legacy Mode ---")
    tool = UnifiedEMLTool(problematic_path)
    tool.modifications = {
        'headers': {
            'Subject': 'Follow - Modified Legacy'
        }
    }
    tool.apply_modifications('test_legacy_mode.eml', realistic_mode=False)
    
    legacy_issues = analyze_email_issues('test_legacy_mode.eml')
    print("\nIssues in legacy mode:")
    for issue in legacy_issues:
        print(f"  {issue}")
    
    # Test 2: Realistic mode (should fix issues)
    print("\n--- TEST 2: Realistic Mode ---")
    tool2 = UnifiedEMLTool(problematic_path)
    tool2.modifications = {
        'headers': {
            'Subject': 'Follow - Modified Realistic'
        }
    }
    tool2.apply_modifications('test_realistic_mode.eml', realistic_mode=True)
    
    realistic_issues = analyze_email_issues('test_realistic_mode.eml')
    print("\nIssues in realistic mode:")
    if realistic_issues:
        for issue in realistic_issues:
            print(f"  {issue}")
    else:
        print("  ✅ No manipulation detection issues found!")
    
    # Show the improvements
    print("\n📊 SUMMARY:")
    print(f"Original email issues: {len(issues)}")
    print(f"Legacy mode issues: {len(legacy_issues)}")
    print(f"Realistic mode issues: {len(realistic_issues)}")
    
    if len(realistic_issues) < len(issues):
        print("\n✅ SUCCESS: Realistic mode fixes authentication issues!")
    else:
        print("\n❌ FAILURE: Issues not properly fixed")
    
    # Cleanup
    for f in [problematic_path, 'test_legacy_mode.eml', 'test_realistic_mode.eml']:
        if os.path.exists(f):
            os.remove(f)


if __name__ == '__main__':
    main() 