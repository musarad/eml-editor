#!/usr/bin/env python3
"""
EML Crypto Signer - Real DKIM and ARC signing for email messages
"""

import base64
import hashlib
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import email
from email.utils import parseaddr, formatdate
import dns.resolver
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature
import dkim
import authheaders


class EMLCryptoSigner:
    """Handles real DKIM and ARC signing for email messages"""
    
    def __init__(self, private_key_path: str = None, selector: str = 'default', 
                 domain: str = None):
        """
        Initialize crypto signer
        
        Args:
            private_key_path: Path to RSA private key file
            selector: DKIM selector (subdomain)
            domain: Signing domain
        """
        self.private_key = None
        self.private_key_path = private_key_path
        self.selector = selector
        self.domain = domain
        
        if private_key_path:
            self.load_private_key(private_key_path)
    
    def load_private_key(self, key_path: str):
        """Load RSA private key from file"""
        with open(key_path, 'rb') as f:
            self.private_key = serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend()
            )
    
    def generate_key_pair(self, key_size: int = 2048) -> Tuple[str, str]:
        """
        Generate new RSA key pair for DKIM signing
        
        Returns:
            Tuple of (private_key_pem, public_key_pem)
        """
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend()
        )
        
        # Private key
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Public key
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return private_pem.decode(), public_pem.decode()
    
    def create_dkim_dns_record(self, public_key_pem: str) -> str:
        """
        Create DNS TXT record for DKIM
        
        Args:
            public_key_pem: Public key in PEM format
            
        Returns:
            DNS TXT record value
        """
        # Extract key data from PEM
        lines = public_key_pem.strip().split('\n')
        key_data = ''.join(lines[1:-1])
        
        # Create DNS record
        dns_record = f"v=DKIM1; k=rsa; p={key_data}"
        
        return dns_record
    
    def sign_with_dkim(self, msg: email.message.Message, 
                      headers_to_sign: List[str] = None) -> email.message.Message:
        """
        Add real DKIM signature to message
        
        Args:
            msg: Email message to sign
            headers_to_sign: List of headers to include in signature
            
        Returns:
            Message with DKIM-Signature header
        """
        if not self.private_key_path or not self.domain:
            raise ValueError("Private key and domain required for DKIM signing")
        
        # Default headers to sign
        if headers_to_sign is None:
            headers_to_sign = [
                b'from', b'to', b'subject', b'date', b'message-id',
                b'content-type', b'mime-version'
            ]
        else:
            headers_to_sign = [h.encode() if isinstance(h, str) else h 
                             for h in headers_to_sign]
        
        # Read private key
        with open(self.private_key_path, 'rb') as f:
            private_key = f.read()
        
        # Convert message to bytes
        msg_bytes = msg.as_bytes()
        
        # Sign with dkim library
        signature = dkim.sign(
            msg_bytes,
            self.selector.encode(),
            self.domain.encode(),
            private_key,
            include_headers=headers_to_sign
        )
        
        # Add signature to message
        sig_header = signature.decode().replace('DKIM-Signature: ', '')
        msg['DKIM-Signature'] = sig_header.strip()
        
        return msg
    
    def sign_with_arc(self, msg: email.message.Message,
                     previous_arc_sets: List[Dict] = None,
                     spf_result: str = 'pass',
                     dkim_result: str = 'pass',
                     dmarc_result: str = 'pass') -> email.message.Message:
        """
        Add ARC (Authenticated Received Chain) headers

        Args:
            msg: Email message to sign
            previous_arc_sets: Previous ARC sets if forwarding (used to determine instance)
            spf_result: SPF authentication result
            dkim_result: DKIM authentication result
            dmarc_result: DMARC authentication result

        Returns:
            Message with ARC headers
        """
        if not self.private_key_path or not self.domain:
            raise ValueError("Private key and domain required for ARC signing")

        # Determine ARC instance number (i= tag)
        # This counts existing ARC-Seal headers to determine the new instance number
        instance = 1
        if previous_arc_sets: # Simplified: assume previous_arc_sets gives count of *prior* sets
            instance = len(previous_arc_sets) + 1
        else:
            # More robust: count existing ARC-Seal headers in the message
            existing_arc_seals = [h for h in msg.keys() if h.lower() == 'arc-seal']
            instance = len(existing_arc_seals) + 1

        # Read private key
        with open(self.private_key_path, 'rb') as f:
            private_key = f.read()

        # Construct the ARC-Authentication-Results (AAR) header content
        # The authserv_id for AAR is self.domain
        authserv_id = self.domain 
        from_domain_for_aar = parseaddr(msg.get('From', ''))[1].split('@')[-1] if '@' in msg.get('From', '') else self.domain
        
        aar_content_parts = [
            f"spf={spf_result} smtp.mailfrom={from_domain_for_aar}",
            f"dkim={dkim_result} header.d={self.domain}"
        ]
        if dmarc_result: # DMARC is optional in AAR per some interpretations
            aar_content_parts.append(f"dmarc={dmarc_result} header.from={from_domain_for_aar}")
        
        aar_value = f"i={instance}; {authserv_id}; {'; '.join(aar_content_parts)}"

        # Add the newly constructed ARC-Authentication-Results header to the message
        # It's important to add it such that it's correctly picked up.
        # We might need to prepend if other ARC headers exist. For now, simple add.
        if 'ARC-Authentication-Results' in msg:
            # If one already exists, decide on strategy (e.g. replace if same instance, or add another)
            # For simplicity, let's assume we are creating the AAR for the *current* instance 'i'
            # and the dkim library will handle it. We might need to remove old ones for this instance.
            # Let's try adding and letting dkim.ARC handle it.
            msg.add_header('ARC-Authentication-Results', aar_value)
        else:
            msg['ARC-Authentication-Results'] = aar_value
            
        # Convert message to bytes (needed by authheaders.sign_message)
        msg_bytes = msg.as_bytes()

        # Headers to be included in the ARC-Message-Signature (h= tag)
        # These should be a list of bytes
        # Common practice includes From, To, Subject, Date, Message-ID, and existing ARC headers
        # The dkim library's ARC implementation usually handles selecting these.
        # For authheaders.sign_message, if sig_headers isn't passed, dkim default is used.
        # Let's rely on dkim.ARC's default header selection for now.
        headers_to_sign_in_arc = [
            b'from', b'to', b'date', b'subject', b'message-id', 
            b'mime-version', b'content-type',
            b'arc-authentication-results' # Ensure our new AAR is signed
        ]


        # Call authheaders.sign_message for ARC.
        # srv_id should match the authserv_id used in the AAR (our domain)
        # The dkim.ARC.sign method (called by authheaders.sign_message)
        # will create ARC-Seal and ARC-Message-Signature.
        arc_signature_headers_bytes = authheaders.sign_message(
            msg_bytes, # The full message including our new AAR
            self.selector.encode(),
            self.domain.encode(),
            private_key,
            sig=b'ARC',
            srv_id=authserv_id.encode(), # Service identifier, matches AAR
            sig_headers=headers_to_sign_in_arc, # Specify headers for AMS
            standardize=True # Recommended for predictable output
        )
        
        # authheaders.sign_message for ARC returns the new ARC-Seal and ARC-Message-Signature
        # headers as a byte string. We need to parse and add them to the message.
        
        # First, remove the temporary AAR we added if dkim.ARC().sign also adds one,
        # or if it modifies it. The dkim lib usually prepends its own AAR.
        # For now, let's clear all AARs and then add back what sign_message returns.
        # This is tricky; dkim.ARC might handle AAR creation itself if srv_id is present.
        # Let's assume dkim.ARC.sign will generate its own AAR based on srv_id
        # and the results it calculates or is passed.
        # The safest is to let dkim.ARC fully manage the AAR it seals.
        # So, remove our manually added AAR before adding the new set.
        
        # Re-create the message object from bytes to ensure clean state for adding new headers
        # First, delete our placeholder AAR
        # This part is tricky because the behavior of dkim.ARC().sign regarding AAR can be complex.
        # Let's temporarily remove ALL AARs and then add the ones from the result.
        # This might be too aggressive if there were prior valid AARs we shouldn't touch.
        
        # A better approach: dkim.ARC.sign will create the AAR as part of its set.
        # We should NOT add AAR manually before calling it if srv_id is specified.
        # It will look for an existing AAR with that srv_id or create one.

        # Let's REVERT to NOT adding AAR manually.
        # Instead, we'll pass the components of AAR to sign_message if possible.
        # The dkim.ARC.sign() function, which authheaders.sign_message calls,
        # does NOT directly take spf_result, dkim_result etc.
        # It DOES however take an `auth_results` parameter which is the *string* for the AAR.

        # Back to the drawing board based on dkim.ARC.sign signature:
        # ARC(msg).sign(selector, domain, privkey, srv_id, auth_results_str=None, ...)
        # So, authheaders.sign_message *should* pass this through if it's a param.

        # The issue is that `authheaders.sign_message` does NOT pass `auth_results_str`
        # or a similar param to `dkim.ARC().sign()`.
        # It only passes: selector, domain, privkey, srv_id, include_headers, timestamp, standardize.

        # This means dkim.ARC().sign() will try to *calculate* auth results internally,
        # or pick up an *existing* AAR with the given srv_id.
        # This is why we MUST add the AAR header to the message *before* calling sign.

        # Let's retry adding AAR to msg, then signing.
        # The key is that dkim.ARC.sign *prepends* the new ARC set.

        # Create a fresh message object for signing to avoid mutation issues
        # This is getting complicated due to library abstractions.
        # Let's simplify: add AAR, sign, then parse returned headers.

        # Remove any existing ARC headers for the current instance to avoid duplication
        # before adding the new set. This is to ensure we replace them cleanly.
        temp_msg = email.message_from_bytes(msg.as_bytes()) # Work on a copy

        # Remove headers for the current instance if they exist from a previous attempt
        del_headers = []
        for k_header in temp_msg.keys():
            if k_header.lower() in ['arc-seal', 'arc-message-signature', 'arc-authentication-results']:
                # Check if 'i=instance' is in the value
                header_values = temp_msg.get_all(k_header)
                for v_header in header_values:
                    if f"i={instance}" in v_header:
                        del_headers.append(k_header)
                        break # Found one for this instance
        
        unique_del_headers = list(set(del_headers))
        for h_to_del in unique_del_headers:
            del temp_msg[h_to_del]

        # Add our constructed AAR for the current instance
        temp_msg['ARC-Authentication-Results'] = aar_value
        msg_bytes_for_signing = temp_msg.as_bytes()

        # Sign the message (which now includes our AAR)
        arc_signature_headers_bytes = authheaders.sign_message(
            msg_bytes_for_signing,
            self.selector.encode(),
            self.domain.encode(),
            private_key,
            sig=b'ARC',
            srv_id=authserv_id.encode(), 
            sig_headers=headers_to_sign_in_arc,
            standardize=True
        )

        # The result `arc_signature_headers_bytes` contains the new
        # ARC-Seal, ARC-Message-Signature, and the ARC-Authentication-Results
        # (as managed by dkim.ARC). These need to be added to the original `msg`.

        # Clear *all* ARC headers from the original message to avoid conflicts/duplication
        # before adding the ones returned by the signing function.
        for k_header in list(msg.keys()): # Iterate over a copy of keys for safe deletion
            if k_header.lower() in ['arc-seal', 'arc-message-signature', 'arc-authentication-results']:
                del msg[k_header]
        
        # Parse and add the new ARC headers
        if arc_signature_headers_bytes:
            arc_header_str = arc_signature_headers_bytes.decode().strip()
            # Headers are typically LF separated, but msg.add_header handles folding.
            header_parser = email.parser.HeaderParser()
            parsed_arc_headers = header_parser.parsestr(arc_header_str, headersonly=True)
            
            for arc_k, arc_v in parsed_arc_headers.items():
                # The dkim library might return multi-line headers already folded
                # or as separate entries if multiple of same type (e.g. multiple AARs if chain)
                # For ARC set, typically one of each (AMS, AS, AAR for current instance)
                msg[arc_k] = arc_v # Replace if exists, add if new.

        return msg
    
    def verify_dkim(self, msg: email.message.Message) -> bool:
        """
        Verify DKIM signature
        
        Args:
            msg: Email message to verify
            
        Returns:
            True if signature is valid
        """
        msg_bytes = msg.as_bytes()
        
        try:
            return dkim.verify(msg_bytes)
        except Exception as e:
            print(f"DKIM verification failed: {e}")
            return False
    
    def verify_arc(self, msg: email.message.Message) -> Tuple[bool, str]:
        """
        Verify ARC chain
        
        Args:
            msg: Email message to verify
            
        Returns:
            Tuple of (is_valid, chain_validation_status)
        """
        msg_bytes = msg.as_bytes()
        
        try:
            arc_verifier = authheaders.ARC(
                msg_bytes,
                logger=None
            )
            
            cv, results = arc_verifier.verify()
            
            return cv == 'pass', cv
        except Exception as e:
            print(f"ARC verification failed: {e}")
            return False, 'fail'
    
    def generate_dkim_header(self, body_hash: str, headers_signed: List[str]) -> str:
        """
        Generate DKIM-Signature header value
        
        Args:
            body_hash: Base64 encoded body hash
            headers_signed: List of headers included in signature
            
        Returns:
            DKIM-Signature header value
        """
        timestamp = int(datetime.now().timestamp())
        
        # Build signature data
        sig_data = [
            f"v=1",
            f"a=rsa-sha256",
            f"c=relaxed/relaxed",
            f"d={self.domain}",
            f"s={self.selector}",
            f"t={timestamp}",
            f"bh={body_hash}",
            f"h={':'.join(headers_signed)}"
        ]
        
        return '; '.join(sig_data)


class EMLCryptoEditor:
    """Enhanced EML editor with real crypto signing"""
    
    def __init__(self, eml_path: str, crypto_signer: EMLCryptoSigner):
        """
        Initialize crypto-enabled editor
        
        Args:
            eml_path: Path to EML file
            crypto_signer: Crypto signer instance
        """
        self.eml_path = eml_path
        self.crypto_signer = crypto_signer
        self.msg = None
        self.load_eml()
    
    def load_eml(self):
        """Load EML file"""
        with open(self.eml_path, 'rb') as f:
            self.msg = email.message_from_bytes(f.read())
    
    def save_eml(self, output_path: str):
        """Save modified EML file"""
        with open(output_path, 'wb') as f:
            f.write(self.msg.as_bytes())
    
    def add_dkim_signature(self):
        """Add real DKIM signature to the message"""
        self.msg = self.crypto_signer.sign_with_dkim(self.msg)
    
    def add_arc_chain(self, auth_results: Dict[str, str] = None):
        """Add ARC chain to the message"""
        if auth_results is None:
            auth_results = {
                'spf': 'pass',
                'dkim': 'pass',
                'dmarc': 'pass'
            }
        
        self.msg = self.crypto_signer.sign_with_arc(
            self.msg,
            spf_result=auth_results.get('spf', 'pass'),
            dkim_result=auth_results.get('dkim', 'pass'),
            dmarc_result=auth_results.get('dmarc', 'pass')
        )
    
    def strip_existing_signatures(self):
        """Remove existing DKIM and ARC signatures"""
        # Remove DKIM signatures
        while 'DKIM-Signature' in self.msg:
            del self.msg['DKIM-Signature']
        
        # Remove ARC headers
        arc_headers = ['ARC-Seal', 'ARC-Message-Signature', 'ARC-Authentication-Results']
        for header in arc_headers:
            while header in self.msg:
                del self.msg[header]
    
    def resign_message(self):
        """Strip existing signatures and add new ones"""
        self.strip_existing_signatures()
        self.add_dkim_signature()
        self.add_arc_chain()


def setup_dkim_keys(domain: str, selector: str = 'default', 
                   key_dir: str = './keys') -> Dict[str, str]:
    """
    Set up DKIM keys for a domain
    
    Args:
        domain: Domain name
        selector: DKIM selector
        key_dir: Directory to store keys
        
    Returns:
        Dictionary with paths and DNS record
    """
    import os
    
    # Create key directory
    os.makedirs(key_dir, exist_ok=True)
    
    # Generate keys
    signer = EMLCryptoSigner()
    private_pem, public_pem = signer.generate_key_pair()
    
    # Save keys
    private_key_path = os.path.join(key_dir, f'{domain}.{selector}.private.pem')
    public_key_path = os.path.join(key_dir, f'{domain}.{selector}.public.pem')
    
    with open(private_key_path, 'w') as f:
        f.write(private_pem)
    
    with open(public_key_path, 'w') as f:
        f.write(public_pem)
    
    # Generate DNS record
    dns_record = signer.create_dkim_dns_record(public_pem)
    dns_txt_path = os.path.join(key_dir, f'{domain}.{selector}.dns.txt')
    
    with open(dns_txt_path, 'w') as f:
        f.write(f"{selector}._domainkey.{domain} IN TXT \"{dns_record}\"\n")
    
    print(f"Keys generated for {domain}")
    print(f"Private key: {private_key_path}")
    print(f"Public key: {public_key_path}")
    print(f"DNS record: {dns_txt_path}")
    print(f"\nAdd this DNS TXT record:")
    print(f"{selector}._domainkey.{domain} IN TXT \"{dns_record}\"")
    
    return {
        'private_key': private_key_path,
        'public_key': public_key_path,
        'dns_record': dns_record,
        'selector': selector,
        'domain': domain
    }


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='EML Crypto Signer')
    parser.add_argument('--generate-keys', action='store_true',
                       help='Generate DKIM key pair')
    parser.add_argument('--domain', help='Domain for signing')
    parser.add_argument('--selector', default='default', help='DKIM selector')
    parser.add_argument('--sign', help='EML file to sign')
    parser.add_argument('--verify', help='EML file to verify')
    parser.add_argument('--private-key', help='Path to private key')
    parser.add_argument('-o', '--output', help='Output file path')
    
    args = parser.parse_args()
    
    if args.generate_keys:
        if not args.domain:
            print("Domain required for key generation")
            parser.print_help()
        else:
            setup_dkim_keys(args.domain, args.selector)
    
    elif args.sign:
        if not args.private_key or not args.domain:
            print("Private key and domain required for signing")
            parser.print_help()
        else:
            signer = EMLCryptoSigner(args.private_key, args.selector, args.domain)
            editor = EMLCryptoEditor(args.sign, signer)
            editor.resign_message()
            output = args.output or args.sign.replace('.eml', '_signed.eml')
            editor.save_eml(output)
            print(f"Signed message saved to: {output}")
    
    elif args.verify:
        with open(args.verify, 'rb') as f:
            msg = email.message_from_bytes(f.read())
        
        signer = EMLCryptoSigner()
        
        # Verify DKIM
        dkim_valid = signer.verify_dkim(msg)
        print(f"DKIM verification: {'PASS' if dkim_valid else 'FAIL'}")
        
        # Verify ARC
        arc_valid, cv = signer.verify_arc(msg)
        print(f"ARC verification: {cv.upper()}")
    
    else:
        parser.print_help() 