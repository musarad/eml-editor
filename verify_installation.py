#!/usr/bin/env python3
"""
EML Editor - Installation Verification Script
Checks all dependencies and core functionality
"""

import sys
import os
from datetime import datetime

def check_python_version():
    """Check Python version compatibility"""
    print("🐍 Python Version Check:")
    print(f"   Version: {sys.version}")
    
    if sys.version_info < (3, 8):
        print("   ❌ Python 3.8+ required")
        return False
    else:
        print("   ✅ Python version compatible")
        return True

def check_core_dependencies():
    """Check core email processing dependencies"""
    print("\n📧 Core Email Dependencies:")
    
    try:
        import email
        import email.utils
        import email.mime.multipart
        import email.mime.text
        import mimetypes
        import base64
        import hashlib
        print("   ✅ Core email modules")
    except ImportError as e:
        print(f"   ❌ Core email modules: {e}")
        return False
    
    try:
        from datetime import datetime, timezone, timedelta
        import json
        import re
        import os
        print("   ✅ Standard library modules")
    except ImportError as e:
        print(f"   ❌ Standard library: {e}")
        return False
    
    return True

def check_web_dependencies():
    """Check Flask web framework dependencies"""
    print("\n🌐 Web Framework Dependencies:")
    
    try:
        import flask
        try:
            version = flask.__version__
        except AttributeError:
            import importlib.metadata
            version = importlib.metadata.version('flask')
        print(f"   ✅ Flask {version}")
    except ImportError as e:
        print(f"   ❌ Flask: {e}")
        return False
    
    try:
        import werkzeug
        try:
            version = werkzeug.__version__
        except AttributeError:
            import importlib.metadata
            version = importlib.metadata.version('werkzeug')
        print(f"   ✅ Werkzeug {version}")
    except ImportError as e:
        print(f"   ❌ Werkzeug: {e}")
        return False
    
    try:
        import jinja2
        import markupsafe
        import itsdangerous
        import click
        import blinker
        print("   ✅ Flask dependencies")
    except ImportError as e:
        print(f"   ❌ Flask dependencies: {e}")
        return False
    
    return True

def check_crypto_dependencies():
    """Check cryptographic dependencies"""
    print("\n🔐 Cryptographic Dependencies:")
    
    try:
        import dkim
        print(f"   ✅ DKIM library")
    except ImportError as e:
        print(f"   ❌ DKIM library: {e}")
        return False
    
    try:
        import authheaders
        print(f"   ✅ Auth headers library")
    except ImportError as e:
        print(f"   ❌ Auth headers: {e}")
        return False
    
    try:
        import cryptography
        try:
            version = cryptography.__version__
        except AttributeError:
            import importlib.metadata
            version = importlib.metadata.version('cryptography')
        print(f"   ✅ Cryptography {version}")
    except ImportError as e:
        print(f"   ❌ Cryptography: {e}")
        return False
    
    try:
        import dns.resolver
        print(f"   ✅ DNS Python")
    except ImportError as e:
        print(f"   ❌ DNS Python: {e}")
        return False
    
    return True

def check_pdf_dependencies():
    """Check PDF processing dependencies"""
    print("\n📄 PDF Processing Dependencies:")
    
    try:
        import fitz  # PyMuPDF
        print(f"   ✅ PyMuPDF (fitz)")
    except ImportError as e:
        print(f"   ❌ PyMuPDF: {e}")
        return False
    
    return True

def check_utility_dependencies():
    """Check utility dependencies"""
    print("\n🛠️ Utility Dependencies:")
    
    try:
        import dateutil
        print(f"   ✅ Python dateutil")
    except ImportError as e:
        print(f"   ❌ Python dateutil: {e}")
        return False
    
    try:
        import typing_extensions
        print(f"   ✅ Typing extensions")
    except ImportError as e:
        print(f"   ❌ Typing extensions: {e}")
        return False
    
    return True

def check_project_modules():
    """Check project-specific modules"""
    print("\n📦 Project Modules:")
    
    try:
        from eml_editor import EMLEditor
        print("   ✅ EML Editor")
    except ImportError as e:
        print(f"   ❌ EML Editor: {e}")
        return False
    
    try:
        from eml_advanced_editor import AdvancedEMLEditor
        print("   ✅ Advanced EML Editor")
    except ImportError as e:
        print(f"   ❌ Advanced EML Editor: {e}")
        return False
    
    try:
        from eml_unified_tool import UnifiedEMLTool
        print("   ✅ Unified EML Tool")
    except ImportError as e:
        print(f"   ❌ Unified EML Tool: {e}")
        return False
    
    try:
        from eml_crypto_signer import EMLCryptoSigner
        print("   ✅ Crypto Signer")
    except ImportError as e:
        print(f"   ❌ Crypto Signer: {e}")
        return False
    
    try:
        from pdf_metadata_editor import set_pdf_metadata_dates
        print("   ✅ PDF Metadata Editor")
    except ImportError as e:
        print(f"   ❌ PDF Metadata Editor: {e}")
        return False
    
    try:
        from web_app import app
        print("   ✅ Web Application")
    except ImportError as e:
        print(f"   ❌ Web Application: {e}")
        return False
    
    return True

def check_functionality():
    """Test basic functionality"""
    print("\n🧪 Functionality Tests:")
    
    try:
        # Test EML creation
        import email.mime.text
        msg = email.mime.text.MIMEText("Test message")
        msg['From'] = 'test@example.com'
        msg['To'] = 'recipient@example.com'
        msg['Subject'] = 'Test'
        print("   ✅ Basic EML creation")
    except Exception as e:
        print(f"   ❌ EML creation: {e}")
        return False
    
    try:
        # Test crypto availability
        from eml_crypto_signer import EMLCryptoSigner
        print("   ✅ Crypto signer available")
    except Exception as e:
        print(f"   ❌ Crypto signer: {e}")
        return False
    
    try:
        # Test PDF processing
        import fitz
        print("   ✅ PDF processing available")
    except Exception as e:
        print(f"   ❌ PDF processing: {e}")
        return False
    
    return True

def main():
    """Main verification function"""
    print("🔍 EML Editor Installation Verification")
    print("=" * 50)
    
    checks = [
        check_python_version(),
        check_core_dependencies(),
        check_web_dependencies(),
        check_crypto_dependencies(),
        check_pdf_dependencies(),
        check_utility_dependencies(),
        check_project_modules(),
        check_functionality()
    ]
    
    print("\n" + "=" * 50)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 50)
    
    passed = sum(checks)
    total = len(checks)
    
    if passed == total:
        print(f"🎉 ALL CHECKS PASSED ({passed}/{total})")
        print("\n✅ Installation is complete and ready to use!")
        print("\n🚀 You can now run:")
        print("   • python3 web_app.py (Web interface)")
        print("   • python3 eml_unified_tool.py (Command line)")
        print("   • python3 example_eml_modifications.py (Examples)")
        return True
    else:
        print(f"❌ SOME CHECKS FAILED ({passed}/{total})")
        print("\n🔧 Please install missing dependencies:")
        print("   pip3 install -r requirements_web.txt")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1) 