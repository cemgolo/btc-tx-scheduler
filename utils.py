from datetime import datetime
import hashlib
import base58

def get_current_time() -> datetime:
    return datetime.now()

def public_key_to_address(public_key: bytes) -> str:
    sha256 = hashlib.sha256(public_key).digest()
    ripemd160 = hashlib.new('ripemd160', sha256).digest()
    versioned_payload = b'\x00' + ripemd160
    checksum = hashlib.sha256(hashlib.sha256(versioned_payload).digest()).digest()[:4]
    address_payload = versioned_payload + checksum
    address = base58.b58encode(address_payload).decode('utf-8')
    
    return address
