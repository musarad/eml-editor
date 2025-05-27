# EML File Editor

A comprehensive Python toolkit for modifying EML (email) files, including headers, dates, attachments, and authentication information.

## 🎯 Quick Start - Unified Tool

**NEW!** Use the all-in-one unified tool with interactive interface:

```bash
# Interactive mode - guides you through all modifications
python eml_unified_tool.py email.eml

# With real cryptographic signatures
python eml_unified_tool.py email.eml --crypto
```

See [UNIFIED_TOOL_GUIDE.md](UNIFIED_TOOL_GUIDE.md) for complete documentation.

## Features

- **Basic Header Modification**: Change From, To, Subject, Date, Message-ID
- **Transport Headers**: Modify Delivered-To, Return-Path, Received headers
- **Authentication Headers**: Edit SPF, DKIM, DMARC, ARC headers
- **Attachment Management**: Add, remove, or replace attachments
- **Transport Chain**: Create complete email routing paths
- **X-Headers**: Modify custom headers (X-Mailer, X-Originating-IP, etc.)

## Installation

No external dependencies required - uses Python's built-in `email` module.

```bash
# Clone or download the files
python3 eml_editor.py --help
```

## Quick Start

### Basic Usage

1. **Simple header modification:**
```bash
python eml_editor.py input.eml -o output.eml \
  --from "sender@example.com" \
  --to "recipient@example.com" \
  --subject "New Subject" \
  --date "Tue, 23 May 2017 14:59:31 +0430"
```

2. **List attachments:**
```bash
python eml_editor.py email.eml --list-attachments
```

3. **Show all headers:**
```bash
python eml_editor.py email.eml --show-headers
```

### Advanced Usage

1. **Run examples:**
```bash
python example_eml_modifications.py
```

2. **Create configuration file:**
```bash
python eml_advanced_editor.py --create-config
```

3. **Process with configuration:**
```bash
python eml_advanced_editor.py --process input.eml eml_config.json output.eml
```

## Programmatic Usage

### Basic Editor

```python
from eml_editor import EMLEditor

# Load EML file
editor = EMLEditor('email.eml')

# Modify headers
editor.modify_basic_headers({
    'From': 'new.sender@example.com',
    'To': 'new.recipient@example.com',
    'Subject': 'Modified Subject'
})

# Change date
editor.modify_date('Tue, 23 May 2017 14:59:31 +0430')

# Add attachment
editor.add_attachment('document.pdf')

# Save
editor.save_eml('modified.eml')
```

### Advanced Editor

```python
from eml_advanced_editor import AdvancedEMLEditor
from datetime import datetime

editor = AdvancedEMLEditor('email.eml')

# Create transport chain
editor.create_complete_transport_chain([
    {
        'from': 'client.example.com [192.168.1.100]',
        'by': 'smtp.example.com',
        'with': 'ESMTP',
        'id': 'abc123',
        'date': datetime.now()
    }
])

# Add authentication results
editor.modify_authentication_results('mx.google.com', {
    'spf': {'result': 'pass', 'domain': 'example.com'},
    'dkim': {'result': 'pass', 'domain': 'example.com'},
    'dmarc': {'result': 'pass', 'policy': 'none'}
})

# Add ARC headers
editor.modify_arc_headers(1, 'google.com', {
    'spf': 'pass',
    'dkim': 'pass',
    'dmarc': 'pass'
})

editor.save_eml('authenticated.eml')
```

## Configuration File Format

Create a JSON configuration file for batch processing:

```json
{
  "modifications": {
    "basic_headers": {
      "From": "sender@example.com",
      "To": "recipient@example.com",
      "Subject": "New Subject"
    },
    "date": "Tue, 23 May 2017 14:59:31 +0430",
    "transport_headers": {
      "Delivered-To": "recipient@example.com",
      "Return-Path": "<sender@example.com>"
    },
    "authentication": {
      "domain": "mx.google.com",
      "results": {
        "spf": {"result": "pass", "domain": "example.com"},
        "dkim": {"result": "pass", "domain": "example.com"},
        "dmarc": {"result": "pass", "policy": "none"}
      }
    },
    "x_headers": {
      "X-Originating-IP": "[192.168.1.100]",
      "X-Mailer": "Custom Mailer 1.0"
    },
    "attachments": {
      "add": ["file1.pdf", "file2.docx"],
      "remove": ["old_file.txt"],
      "replace": [["old.pdf", "new.pdf"]]
    }
  }
}
```

## Header Types Explained

### Transport & Authentication Headers

- **Delivered-To**: Final recipient mailbox
- **Received**: Shows each hop in the email's journey
- **Return-Path**: Bounce address for delivery failures
- **SPF/DKIM/DMARC**: Email authentication results
- **ARC headers**: Preserve authentication across forwarding

### Basic Headers

- **From/To/Subject**: Standard email fields
- **Date**: When the email was sent
- **Message-ID**: Unique identifier for the email

### Custom Headers

- **X-Headers**: Custom headers like X-Mailer, X-Originating-IP
- **Thread headers**: For email client threading

## Examples

See `example_eml_modifications.py` for comprehensive examples:

1. Basic header and date modifications
2. Complete transport chain with authentication
3. Attachment modifications
4. Complete email recreation (TIC invoice example)
5. Command-line usage examples

## Cryptographic Signing (NEW!)

The toolkit now includes **real DKIM and ARC cryptographic signing** capabilities:

### Setup DKIM Keys

```bash
# Generate DKIM keys for your domain
python eml_crypto_signer.py --generate-keys --domain example.com --selector mail2024
```

This will:
- Generate RSA key pair (2048-bit)
- Save private/public keys in `./dkim_keys/`
- Provide DNS TXT record for DKIM

### Sign with Real DKIM

```bash
# Sign an email with DKIM
python eml_crypto_signer.py --sign email.eml --domain example.com \
  --selector mail2024 --private-key ./dkim_keys/example.com.mail2024.private.pem
```

### Verify Signatures

```bash
# Verify DKIM and ARC signatures
python eml_crypto_signer.py --verify signed_email.eml
```

### Programmatic Crypto Usage

```python
from eml_crypto_signer import EMLCryptoSigner, EMLCryptoEditor

# Initialize signer
signer = EMLCryptoSigner('private_key.pem', 'selector', 'domain.com')

# Sign email with DKIM
editor = EMLCryptoEditor('email.eml', signer)
editor.add_dkim_signature()
editor.add_arc_chain()
editor.save_eml('signed.eml')
```

### Run Crypto Examples

```bash
# Install crypto dependencies
pip install -r requirements.txt

# Run comprehensive examples
python example_crypto_signing.py
```

## Notes

- **Basic features** work without any external dependencies
- **Crypto signing** requires: dkimpy, authheaders, cryptography, dnspython
- DKIM verification requires DNS records to be published
- The tool preserves MIME structure and encoding
- Attachments are properly encoded in base64
- All modifications maintain email format compliance

## License

This tool is provided as-is for educational and legitimate email processing purposes. 