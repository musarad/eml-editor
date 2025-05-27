#!/usr/bin/env python3
"""
Example script demonstrating various EML file modifications
"""

from eml_advanced_editor import AdvancedEMLEditor
from datetime import datetime, timedelta
import os
import email.utils


def create_sample_eml_with_attachment():
    """Create a sample EML file with an attachment for testing"""
    
    # Create a sample attachment
    with open('sample_invoice.txt', 'w') as f:
        f.write("Invoice #12345\nAmount: $100.00\nDate: 2017-04-01")
    
    # Create EML with attachment
    import email.mime.multipart
    import email.mime.text
    import email.mime.base
    from email.encoders import encode_base64
    
    msg = email.mime.multipart.MIMEMultipart('mixed')
    
    # Headers
    msg['From'] = 'original.sender@oldcompany.com'
    msg['To'] = 'original.recipient@oldcompany.com'
    msg['Subject'] = 'Original Invoice'
    msg['Date'] = email.utils.formatdate(localtime=True)
    msg['Message-ID'] = '<original123@oldcompany.com>'
    
    # Body
    body = email.mime.text.MIMEText('Please find attached invoice.', 'plain')
    msg.attach(body)
    
    # Attachment
    with open('sample_invoice.txt', 'rb') as f:
        attachment = email.mime.base.MIMEBase('text', 'plain')
        attachment.set_payload(f.read())
        encode_base64(attachment)
        attachment.add_header('Content-Disposition', 'attachment', 
                            filename='invoice_old.txt')
        msg.attach(attachment)
    
    # Save
    with open('original.eml', 'wb') as f:
        f.write(msg.as_bytes())
    
    print("Created original.eml with attachment")


def example_1_basic_modifications():
    """Example 1: Basic header and date modifications"""
    print("\n" + "="*60)
    print("Example 1: Basic Header and Date Modifications")
    print("="*60)
    
    # Create editor
    editor = AdvancedEMLEditor('original.eml')
    
    # Show original headers
    print("\nOriginal headers:")
    headers = editor.get_headers()
    for key in ['From', 'To', 'Subject', 'Date']:
        print(f"  {key}: {headers.get(key, 'N/A')}")
    
    # Modify headers
    editor.modify_basic_headers({
        'From': 'int.department@tic.ir',
        'To': 'unal.abaci@cellsigma.com, billing@cellsigma.com',
        'Subject': 'TIC invoice Apr 17'
    })
    
    # Modify date
    editor.modify_date('Tue, 23 May 2017 14:59:31 +0430')
    
    # Save
    editor.save_eml('example1_basic.eml')
    
    print("\nModified headers saved to example1_basic.eml")


def example_2_transport_chain():
    """Example 2: Complete transport chain with authentication"""
    print("\n" + "="*60)
    print("Example 2: Transport Chain and Authentication Headers")
    print("="*60)
    
    editor = AdvancedEMLEditor('original.eml')
    
    # Add complete transport chain
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
            'date': datetime(2017, 5, 23, 10, 35, 36)
        },
        {
            'from': 'mx.google.com',
            'by': '10.159.59.83',
            'with': 'SMTP',
            'id': 'j19csp1780682uah',
            'date': datetime(2017, 5, 23, 10, 35, 36)
        }
    ])
    
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
    
    # Add ARC headers
    editor.modify_arc_headers(1, 'google.com', {
        'spf': 'pass',
        'dkim': 'pass',
        'dmarc': 'pass'
    })
    
    # Add DKIM signature
    editor.add_dkim_signature('tic.ir', 's1')
    
    # Save
    editor.save_eml('example2_transport.eml')
    
    print("\nAdded transport chain and authentication headers")
    print("Saved to example2_transport.eml")


def example_3_attachment_modifications():
    """Example 3: Attachment modifications"""
    print("\n" + "="*60)
    print("Example 3: Attachment Modifications")
    print("="*60)
    
    # Create new attachment
    with open('new_invoice.pdf', 'wb') as f:
        f.write(b'%PDF-1.4\n%Fake PDF content for demo\n')
    
    editor = AdvancedEMLEditor('original.eml')
    
    # List current attachments
    print("\nCurrent attachments:")
    for att in editor.list_attachments():
        print(f"  - {att}")
    
    # Replace attachment
    editor.replace_attachment('invoice_old.txt', 'new_invoice.pdf', 'TIC_invoice_Apr17.pdf')
    
    # Add another attachment
    with open('terms.txt', 'w') as f:
        f.write('Payment terms: Net 30 days')
    editor.add_attachment('terms.txt', 'payment_terms.txt')
    
    # Save
    editor.save_eml('example3_attachments.eml')
    
    print("\nModified attachments:")
    editor2 = AdvancedEMLEditor('example3_attachments.eml')
    for att in editor2.list_attachments():
        print(f"  - {att}")
    
    print("\nSaved to example3_attachments.eml")


def example_4_complete_modification():
    """Example 4: Complete email modification matching the TIC invoice example"""
    print("\n" + "="*60)
    print("Example 4: Complete TIC Invoice Email Recreation")
    print("="*60)
    
    editor = AdvancedEMLEditor('original.eml')
    
    # 1. Basic headers
    editor.modify_basic_headers({
        'From': 'int.department@tic.ir',
        'To': 'unal.abaci@cellsigma.com, billing@cellsigma.com',
        'Subject': 'TIC invoice Apr 17'
    })
    
    # 2. Date
    editor.modify_date('Tue, 23 May 2017 14:59:31 +0430')
    
    # 3. Message-ID
    editor.modify_message_id('tic.ir')
    
    # 4. Transport headers
    editor.modify_transport_headers({
        'Delivered-To': 'billing@cellsigma.com',
        'Return-Path': '<int.department@tic.ir>'
    })
    
    # 5. X-headers
    editor.modify_x_headers({
        'X-Originating-IP': '[192.168.39.87]',
        'X-Mailer': 'Zimbra 8.6.0_GA_1194 (zclient/8.6.0_GA_1194)',
        'X-Virus-Scanned': 'amavisd-new at tic.ir',
        'Thread-Topic': 'TIC invoice Apr 17',
        'Thread-Index': 'lENzmuH66ZgoyQqJ6DhuBgDg8QhH/A=='
    })
    
    # 6. Transport chain
    editor.create_complete_transport_chain([
        {
            'from': 'zimbra.tic.ir [192.168.39.87]',
            'by': 'mx1.tic.ir',
            'with': 'ESMTP',
            'id': '1224472481.40492.1495535371917',
            'date': datetime(2017, 5, 23, 14, 59, 31)
        },
        {
            'from': 'mx1.tic.ir',
            'by': 'mx.google.com',
            'with': 'ESMTPS',
            'id': 'd17mr1768016wmd.90.1495535736487',
            'for': '<billing@cellsigma.com>',
            'date': datetime(2017, 5, 23, 10, 35, 36)
        },
        {
            'from': 'mx.google.com',
            'by': '10.159.59.83',
            'with': 'SMTP',
            'id': 'j19csp1780682uah',
            'date': datetime(2017, 5, 23, 10, 35, 36)
        }
    ])
    
    # 7. Authentication results
    editor.modify_authentication_results('mx.google.com', {
        'spf': {
            'result': 'pass',
            'domain': 'tic.ir'
        },
        'dkim': {
            'result': 'pass',
            'domain': 'tic.ir'
        },
        'dmarc': {
            'result': 'pass',
            'policy': 'none'
        }
    })
    
    # 8. ARC headers
    editor.modify_arc_headers(1, 'google.com', {
        'spf': 'pass',
        'dkim': 'pass',
        'dmarc': 'pass'
    })
    
    # 9. DKIM signature
    editor.add_dkim_signature('tic.ir', 's1')
    
    # Save
    editor.save_eml('example4_complete_tic_invoice.eml')
    
    print("\nComplete TIC invoice email created")
    print("Saved to example4_complete_tic_invoice.eml")
    
    # Show summary
    print("\nEmail summary:")
    headers = editor.get_headers()
    important_headers = [
        'From', 'To', 'Subject', 'Date', 'Message-ID',
        'Delivered-To', 'Return-Path', 'Authentication-Results',
        'DKIM-Signature', 'X-Originating-IP', 'X-Mailer'
    ]
    
    for header in important_headers:
        value = headers.get(header, 'N/A')
        if isinstance(value, list):
            value = value[0]
        if len(str(value)) > 60:
            value = str(value)[:57] + '...'
        print(f"  {header}: {value}")


def example_5_command_line_usage():
    """Example 5: Command-line usage examples"""
    print("\n" + "="*60)
    print("Example 5: Command-Line Usage Examples")
    print("="*60)
    
    print("\n1. Basic modification:")
    print("   python eml_editor.py input.eml -o output.eml \\")
    print("     --from 'sender@example.com' \\")
    print("     --to 'recipient@example.com' \\")
    print("     --subject 'New Subject' \\")
    print("     --date 'Tue, 23 May 2017 14:59:31 +0430'")
    
    print("\n2. List and show headers:")
    print("   python eml_editor.py input.eml --list-attachments")
    print("   python eml_editor.py input.eml --show-headers")
    
    print("\n3. Attachment operations:")
    print("   python eml_editor.py input.eml -o output.eml \\")
    print("     --add-attachment 'document.pdf' \\")
    print("     --remove-attachment 'old_file.txt' \\")
    print("     --replace-attachment 'invoice.txt' 'new_invoice.pdf'")
    
    print("\n4. Advanced modifications:")
    print("   python eml_advanced_editor.py --create-config")
    print("   # Edit eml_config.json as needed")
    print("   python eml_advanced_editor.py --process input.eml eml_config.json output.eml")


def cleanup():
    """Clean up temporary files"""
    temp_files = [
        'sample_invoice.txt', 'new_invoice.pdf', 'terms.txt',
        'sample.eml', 'original.eml'
    ]
    
    for file in temp_files:
        if os.path.exists(file):
            os.remove(file)


def main():
    print("EML File Editor - Comprehensive Examples")
    print("========================================")
    
    # Create sample files
    create_sample_eml_with_attachment()
    
    # Run examples
    example_1_basic_modifications()
    example_2_transport_chain()
    example_3_attachment_modifications()
    example_4_complete_modification()
    example_5_command_line_usage()
    
    print("\n" + "="*60)
    print("All examples completed!")
    print("="*60)
    
    # Optional cleanup
    response = input("\nClean up temporary files? (y/n): ")
    if response.lower() == 'y':
        cleanup()
        print("Temporary files cleaned up.")


if __name__ == '__main__':
    main() 