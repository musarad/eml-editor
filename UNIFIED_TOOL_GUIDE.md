# Unified EML Tool - Complete Guide

A comprehensive tool that combines all EML modification features with an interactive interface.

## Features

✅ **Complete Email Analysis**: Extracts and displays all email information
✅ **Interactive Modification**: User-friendly wizard for making changes
✅ **Date Modification**: Change email dates with automatic formatting
✅ **Body Editing**: Modify email content while preserving structure
✅ **Attachment Management**: Add, remove, or replace attachments
✅ **Header Updates**: Modify any email header
✅ **Transport Chain**: Automatically creates realistic routing paths
✅ **Authentication Headers**: Adds SPF, DKIM, DMARC, and ARC headers
✅ **Cryptographic Signing**: Optional real DKIM/ARC signatures

## Installation

### Basic Installation (No Dependencies)
```bash
# Just run the tool - basic features work out of the box
python eml_unified_tool.py email.eml
```

### Full Installation (With Crypto Features)
```bash
# Install dependencies for cryptographic signing
pip install -r requirements.txt
```

## Usage

### Interactive Mode (Recommended)

The tool guides you through each modification step:

```bash
python eml_unified_tool.py email.eml
```

This will:
1. Display current email information
2. Ask what date you want to change to
3. Ask if you want to modify the body
4. Provide options for attachment modifications
5. Ask about other header changes
6. Apply all modifications and create a new file

### Command Line Options

```bash
# Basic usage
python eml_unified_tool.py input.eml

# Specify output file
python eml_unified_tool.py input.eml -o output.eml

# Use real cryptographic signatures
python eml_unified_tool.py input.eml --crypto

# Just display information
python eml_unified_tool.py input.eml --info-only

# Use configuration file
python eml_unified_tool.py input.eml --config modifications.json
```

## Interactive Workflow Example

```
📧 Loading email: invoice.eml

============================================================
CURRENT EMAIL INFORMATION
============================================================

📧 Basic Headers:
  From: sender@oldcompany.com
  To: recipient@oldcompany.com
  Subject: Old Invoice
  Date: Mon, 1 Jan 2024 10:00:00 +0000
  Message-ID: <123@oldcompany.com>

📄 Body Preview:
  Please find attached the invoice for...

📎 Attachments:
  - invoice_2024.pdf

🔄 Transport Chain:
  Hop 1: from mail.oldcompany.com by smtp.gmail.com

🔐 Authentication Status:
  SPF: pass
  DKIM: pass
  DMARC: none
  ARC: none

============================================================
EMAIL MODIFICATION WIZARD
============================================================

📅 Date Modification:
Current date: Mon, 1 Jan 2024 10:00:00 +0000
Enter new date (or press Enter to keep current): 2017-05-23 14:59:31
✅ Date will be changed to: Tue, 23 May 2017 14:59:31 +0430

📝 Body Modification:
Current body preview:
----------------------------------------
Please find attached the invoice for...
----------------------------------------
Do you want to modify the body? (y/n): y
Enter new body text (type 'END' on a new line when finished):
Dear Customer,

Please find attached the TIC invoice for April 2017.

Best regards,
International Department
END
✅ Body will be updated

📎 Attachment Modification:
Current attachments:
  1. invoice_2024.pdf

Attachment options:
1. Add new attachment
2. Remove attachment
3. Replace attachment
4. Skip attachment modification
Choose option (1-4): 3
Enter attachment number to replace: 1
Enter path to replacement file: /path/to/tic_invoice_apr17.pdf
✅ Will replace invoice_2024.pdf with tic_invoice_apr17.pdf

🔧 Additional Modifications:
Do you want to modify other headers? (y/n): y
Common headers to modify:
1. From
2. To
3. Subject
4. Custom header
Choose option (1-4): 1
Current From: sender@oldcompany.com
Enter new From: int.department@tic.ir
✅ From will be changed
```

## Configuration File Format

Create a JSON file for batch processing:

```json
{
  "date": "Tue, 23 May 2017 14:59:31 +0430",
  "body": "New email body text here",
  "headers": {
    "From": "int.department@tic.ir",
    "To": "billing@cellsigma.com",
    "Subject": "TIC invoice Apr 17"
  },
  "attachments": {
    "add": ["document.pdf"],
    "remove": ["old_file.txt"],
    "replace": [["invoice.pdf", "new_invoice.pdf"]]
  }
}
```

Then use:
```bash
python eml_unified_tool.py email.eml --config modifications.json
```

## What Gets Modified

### 1. **Date and Message-ID**
- Updates the Date header
- Generates new Message-ID based on the new timestamp
- Updates dates in transport headers

### 2. **Email Body**
- Preserves MIME structure
- Handles both plain text and HTML
- Maintains proper encoding

### 3. **Attachments**
- Properly encodes new attachments
- Preserves MIME boundaries
- Supports all file types

### 4. **Transport Headers**
- Creates realistic Received headers
- Updates Delivered-To and Return-Path
- Maintains proper routing chain

### 5. **Authentication Headers**
- SPF: Sets pass/fail status
- DKIM: Adds signature (example or real)
- DMARC: Sets policy compliance
- ARC: Adds chain for forwarding

### 6. **Custom Headers**
- X-Originating-IP
- X-Mailer
- Thread-Topic
- Any custom header you need

## Cryptographic Signing

### Example Signatures (Default)
- Quick and easy
- No setup required
- Good for testing

### Real Signatures (--crypto flag)
- Generates RSA keys automatically
- Creates valid DKIM signatures
- Adds ARC chain
- Keys saved in ./dkim_keys/

## Examples

### Example 1: Simple Date Change
```bash
python eml_unified_tool.py email.eml
# Just change the date when prompted
```

### Example 2: Complete Transformation
```bash
python eml_unified_tool.py original.eml -o tic_invoice.eml --crypto
# Change date, body, attachments, and add real signatures
```

### Example 3: Batch Processing
```bash
# Create config file
cat > mods.json << EOF
{
  "date": "2017-05-23 14:59:31",
  "headers": {
    "From": "int.department@tic.ir",
    "Subject": "TIC invoice Apr 17"
  }
}
EOF

# Apply to multiple files
for eml in *.eml; do
  python eml_unified_tool.py "$eml" --config mods.json
done
```

## Output

The tool creates a new EML file with:
- All requested modifications applied
- Proper MIME structure maintained
- Valid email format
- Authentication headers added
- Transport chain created
- Optional cryptographic signatures

## Tips

1. **Date Format**: You can enter dates in various formats:
   - RFC format: `Tue, 23 May 2017 14:59:31 +0430`
   - Simple format: `2017-05-23 14:59:31`
   - The tool auto-converts to proper RFC format

2. **Body Editing**: When entering new body text:
   - Type line by line
   - Press Enter for new lines
   - Type `END` on its own line to finish

3. **File Paths**: Use absolute paths for attachments to avoid issues

4. **Crypto Mode**: First run generates keys automatically, subsequent runs reuse them

## Troubleshooting

**"Crypto features not available"**
- Install requirements: `pip install -r requirements.txt`

**"File not found"**
- Check the file path is correct
- Use absolute paths for attachments

**"Invalid date format"**
- Use YYYY-MM-DD HH:MM:SS format
- Or use full RFC format

## Security Note

This tool is for legitimate email processing. Generated keys and signatures are for testing/archival purposes. For production email sending, use proper mail servers with valid DNS records. 