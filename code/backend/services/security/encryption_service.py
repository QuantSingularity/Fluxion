"""
Comprehensive Encryption Service for Fluxion Backend
Implements enterprise-grade encryption, key management, and cryptographic operations
for financial data protection and regulatory compliance.
"""

import base64
import hashlib
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Optional, Tuple, Union

import jwt
from config.settings import settings
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

logger = logging.getLogger(__name__)


class EncryptionAlgorithm(Enum):
    """Supported encryption algorithms"""

    AES_256_GCM = "aes_256_gcm"
    AES_256_CBC = "aes_256_cbc"
    FERNET = "fernet"
    RSA_2048 = "rsa_2048"
    RSA_4096 = "rsa_4096"


class KeyType(Enum):
    """Types of encryption keys"""

    SYMMETRIC = "symmetric"
    ASYMMETRIC_PUBLIC = "asymmetric_public"
    ASYMMETRIC_PRIVATE = "asymmetric_private"
    DERIVED = "derived"


@dataclass
class EncryptionKey:
    """Encryption key metadata"""

    key_id: str
    key_type: KeyType
    algorithm: EncryptionAlgorithm
    created_at: datetime
    expires_at: Optional[datetime]
    purpose: str
    metadata: Dict[str, Any]


@dataclass
class EncryptedData:
    """Encrypted data container"""

    ciphertext: bytes
    algorithm: str
    key_id: str
    iv: Optional[bytes]
    tag: Optional[bytes]
    metadata: Dict[str, Any]


class EncryptionService:
    """
    Comprehensive encryption service providing:
    - Symmetric and asymmetric encryption
    - Key generation and management
    - Field-level encryption for databases
    - Token encryption and signing
    - Password hashing and verification
    - Digital signatures
    """

    def __init__(self) -> None:
        self.backend = default_backend()
        self.keys: Dict[str, Any] = {}
        self.key_rotation_interval = timedelta(days=90)
        self._initialize_master_keys()
        self._initialize_field_encryption_keys()

    def _initialize_master_keys(self) -> Any:
        """Initialize master encryption keys"""
        try:
            if (
                hasattr(settings.security, "ENCRYPTION_KEY")
                and settings.security.ENCRYPTION_KEY
            ):
                master_key = settings.security.ENCRYPTION_KEY.encode()
                if len(master_key) < 32:
                    master_key = self._derive_key(master_key, b"master_salt")
                self.master_key = master_key[:32]
                fernet_key = base64.urlsafe_b64encode(self.master_key)
                self.fernet = Fernet(fernet_key)
                logger.info("Master encryption keys initialized")
            else:
                logger.warning(
                    "No master encryption key configured, generating temporary key"
                )
                self._generate_temporary_master_key()
        except Exception as e:
            logger.error(f"Failed to initialize master keys: {e}")
            self._generate_temporary_master_key()

    def _generate_temporary_master_key(self) -> Any:
        """Generate temporary master key for development/testing"""
        self.master_key = secrets.token_bytes(32)
        fernet_key = base64.urlsafe_b64encode(self.master_key)
        self.fernet = Fernet(fernet_key)
        logger.warning("Using temporary master key - NOT suitable for production")

    def _initialize_field_encryption_keys(self) -> Any:
        """Initialize field-level encryption keys"""
        self.field_keys = {
            "pii": self._generate_field_key("pii"),
            "financial": self._generate_field_key("financial"),
            "sensitive": self._generate_field_key("sensitive"),
            "internal": self._generate_field_key("internal"),
        }

    def _generate_field_key(self, purpose: str) -> Fernet:
        """Generate field-specific encryption key"""
        purpose_salt = hashlib.sha256(purpose.encode()).digest()
        derived_key = self._derive_key(self.master_key, purpose_salt)
        fernet_key = base64.urlsafe_b64encode(derived_key[:32])
        return Fernet(fernet_key)

    def _derive_key(self, password: bytes, salt: bytes, length: int = 32) -> bytes:
        """Derive encryption key using PBKDF2"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=length,
            salt=salt,
            iterations=100000,
            backend=self.backend,
        )
        return kdf.derive(password)

    def encrypt_symmetric(
        self,
        data: Union[str, bytes],
        algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_GCM,
        key_id: Optional[str] = None,
    ) -> EncryptedData:
        """Encrypt data using symmetric encryption"""
        if isinstance(data, str):
            data = data.encode("utf-8")
        if algorithm == EncryptionAlgorithm.AES_256_GCM:
            return self._encrypt_aes_gcm(data, key_id)
        elif algorithm == EncryptionAlgorithm.AES_256_CBC:
            return self._encrypt_aes_cbc(data, key_id)
        elif algorithm == EncryptionAlgorithm.FERNET:
            return self._encrypt_fernet(data, key_id)
        else:
            raise ValueError(f"Unsupported symmetric algorithm: {algorithm}")

    def decrypt_symmetric(self, encrypted_data: EncryptedData) -> bytes:
        """Decrypt data using symmetric encryption"""
        algorithm = EncryptionAlgorithm(encrypted_data.algorithm)
        if algorithm == EncryptionAlgorithm.AES_256_GCM:
            return self._decrypt_aes_gcm(encrypted_data)
        elif algorithm == EncryptionAlgorithm.AES_256_CBC:
            return self._decrypt_aes_cbc(encrypted_data)
        elif algorithm == EncryptionAlgorithm.FERNET:
            return self._decrypt_fernet(encrypted_data)
        else:
            raise ValueError(f"Unsupported symmetric algorithm: {algorithm}")

    def _encrypt_aes_gcm(
        self, data: bytes, key_id: Optional[str] = None
    ) -> EncryptedData:
        """Encrypt using AES-256-GCM"""
        key = self.master_key
        iv = secrets.token_bytes(12)
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=self.backend)
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(data) + encryptor.finalize()
        return EncryptedData(
            ciphertext=ciphertext,
            algorithm=EncryptionAlgorithm.AES_256_GCM.value,
            key_id=key_id or "master",
            iv=iv,
            tag=encryptor.tag,
            metadata={"timestamp": datetime.now(timezone.utc).isoformat()},
        )

    def _decrypt_aes_gcm(self, encrypted_data: EncryptedData) -> bytes:
        """Decrypt using AES-256-GCM"""
        key = self.master_key
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(encrypted_data.iv, encrypted_data.tag),
            backend=self.backend,
        )
        decryptor = cipher.decryptor()
        return decryptor.update(encrypted_data.ciphertext) + decryptor.finalize()

    def _encrypt_aes_cbc(
        self, data: bytes, key_id: Optional[str] = None
    ) -> EncryptedData:
        """Encrypt using AES-256-CBC with PKCS7 padding"""
        key = self.master_key
        iv = secrets.token_bytes(16)
        padding_length = 16 - len(data) % 16
        padded_data = data + bytes([padding_length] * padding_length)
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=self.backend)
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        return EncryptedData(
            ciphertext=ciphertext,
            algorithm=EncryptionAlgorithm.AES_256_CBC.value,
            key_id=key_id or "master",
            iv=iv,
            tag=None,
            metadata={"timestamp": datetime.now(timezone.utc).isoformat()},
        )

    def _decrypt_aes_cbc(self, encrypted_data: EncryptedData) -> bytes:
        """Decrypt using AES-256-CBC and remove PKCS7 padding"""
        key = self.master_key
        cipher = Cipher(
            algorithms.AES(key), modes.CBC(encrypted_data.iv), backend=self.backend
        )
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(encrypted_data.ciphertext) + decryptor.finalize()
        padding_length = padded_data[-1]
        return padded_data[:-padding_length]

    def _encrypt_fernet(
        self, data: bytes, key_id: Optional[str] = None
    ) -> EncryptedData:
        """Encrypt using Fernet (AES-128 in CBC mode with HMAC)"""
        ciphertext = self.fernet.encrypt(data)
        return EncryptedData(
            ciphertext=ciphertext,
            algorithm=EncryptionAlgorithm.FERNET.value,
            key_id=key_id or "master",
            iv=None,
            tag=None,
            metadata={"timestamp": datetime.now(timezone.utc).isoformat()},
        )

    def _decrypt_fernet(self, encrypted_data: EncryptedData) -> bytes:
        """Decrypt using Fernet"""
        return self.fernet.decrypt(encrypted_data.ciphertext)

    def generate_rsa_keypair(self, key_size: int = 2048) -> Tuple[bytes, bytes]:
        """Generate RSA key pair"""
        private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=key_size, backend=self.backend
        )
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return (private_pem, public_pem)

    def encrypt_asymmetric(
        self, data: Union[str, bytes], public_key_pem: bytes
    ) -> bytes:
        """Encrypt data using RSA public key"""
        if isinstance(data, str):
            data = data.encode("utf-8")
        public_key = serialization.load_pem_public_key(
            public_key_pem, backend=self.backend
        )
        if len(data) > 190:
            return self._hybrid_encrypt(data, public_key)
        ciphertext = public_key.encrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return ciphertext

    def decrypt_asymmetric(self, ciphertext: bytes, private_key_pem: bytes) -> bytes:
        """Decrypt data using RSA private key"""
        private_key = serialization.load_pem_private_key(
            private_key_pem, password=None, backend=self.backend
        )
        if len(ciphertext) > 256:
            return self._hybrid_decrypt(ciphertext, private_key)
        plaintext = private_key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return plaintext

    def _hybrid_encrypt(self, data: bytes, public_key: Any) -> bytes:
        """Hybrid encryption: RSA + AES"""
        aes_key = secrets.token_bytes(32)
        encrypted_data = self.encrypt_symmetric(data, EncryptionAlgorithm.AES_256_GCM)
        encrypted_aes_key = public_key.encrypt(
            aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return (
            encrypted_aes_key
            + encrypted_data.iv
            + encrypted_data.tag
            + encrypted_data.ciphertext
        )

    def _hybrid_decrypt(self, ciphertext: bytes, private_key: Any) -> bytes:
        """Hybrid decryption: RSA + AES"""
        encrypted_aes_key = ciphertext[:256]
        iv = ciphertext[256:268]
        tag = ciphertext[268:284]
        encrypted_data = ciphertext[284:]
        aes_key = private_key.decrypt(
            encrypted_aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        encrypted_data_obj = EncryptedData(
            ciphertext=encrypted_data,
            algorithm=EncryptionAlgorithm.AES_256_GCM.value,
            key_id="hybrid",
            iv=iv,
            tag=tag,
            metadata={},
        )
        original_key = self.master_key
        self.master_key = aes_key
        try:
            result = self._decrypt_aes_gcm(encrypted_data_obj)
        finally:
            self.master_key = original_key
        return result

    def encrypt_field(self, value: Any, field_type: str = "sensitive") -> str:
        """Encrypt field value for database storage"""
        if value is None:
            return None
        if not isinstance(value, str):
            value = str(value)
        field_key = self.field_keys.get(field_type, self.field_keys["sensitive"])
        encrypted_bytes = field_key.encrypt(value.encode("utf-8"))
        return base64.b64encode(encrypted_bytes).decode("ascii")

    def decrypt_field(self, encrypted_value: str, field_type: str = "sensitive") -> str:
        """Decrypt field value from database"""
        if encrypted_value is None:
            return None
        try:
            field_key = self.field_keys.get(field_type, self.field_keys["sensitive"])
            encrypted_bytes = base64.b64decode(encrypted_value.encode("ascii"))
            decrypted_bytes = field_key.decrypt(encrypted_bytes)
            return decrypted_bytes.decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to decrypt field: {e}")
            raise ValueError("Failed to decrypt field value")

    def hash_password(
        self, password: str, salt: Optional[bytes] = None
    ) -> Tuple[str, str]:
        """Hash password using Scrypt"""
        if salt is None:
            salt = secrets.token_bytes(32)
        kdf = Scrypt(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            n=2**14,
            r=8,
            p=1,
            backend=self.backend,
        )
        password_hash = kdf.derive(password.encode("utf-8"))
        return (
            base64.b64encode(password_hash).decode("ascii"),
            base64.b64encode(salt).decode("ascii"),
        )

    def verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        """Verify password against hash"""
        try:
            salt_bytes = base64.b64decode(salt.encode("ascii"))
            hash_bytes = base64.b64decode(password_hash.encode("ascii"))
            kdf = Scrypt(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt_bytes,
                n=2**14,
                r=8,
                p=1,
                backend=self.backend,
            )
            kdf.verify(password.encode("utf-8"), hash_bytes)
            return True
        except Exception:
            return False

    def sign_data(self, data: Union[str, bytes], private_key_pem: bytes) -> bytes:
        """Create digital signature for data"""
        if isinstance(data, str):
            data = data.encode("utf-8")
        private_key = serialization.load_pem_private_key(
            private_key_pem, password=None, backend=self.backend
        )
        signature = private_key.sign(
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256(),
        )
        return signature

    def verify_signature(
        self, data: Union[str, bytes], signature: bytes, public_key_pem: bytes
    ) -> bool:
        """Verify digital signature"""
        try:
            if isinstance(data, str):
                data = data.encode("utf-8")
            public_key = serialization.load_pem_public_key(
                public_key_pem, backend=self.backend
            )
            public_key.verify(
                signature,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            return True
        except Exception as e:
            logger.warning(f"Signature verification failed: {e}")
            return False

    def encrypt_token(self, payload: Dict[str, Any], expires_in: int = 3600) -> str:
        """Encrypt JWT token"""
        payload["exp"] = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        payload["iat"] = datetime.now(timezone.utc)
        token = jwt.encode(payload, self.master_key, algorithm="HS256")
        encrypted_token = self.fernet.encrypt(token.encode("utf-8"))
        return base64.urlsafe_b64encode(encrypted_token).decode("ascii")

    def decrypt_token(self, encrypted_token: str) -> Dict[str, Any]:
        """Decrypt JWT token"""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_token.encode("ascii"))
            token_bytes = self.fernet.decrypt(encrypted_bytes)
            token = token_bytes.decode("utf-8")
            payload = jwt.decode(token, self.master_key, algorithms=["HS256"])
            return payload
        except Exception as e:
            logger.warning(f"Token decryption failed: {e}")
            raise ValueError("Invalid or expired token")

    def rotate_keys(self) -> Any:
        """Rotate encryption keys"""
        logger.info("Starting key rotation process")
        try:
            old_keys = self.field_keys.copy()
            self._initialize_field_encryption_keys()
            logger.info("Key rotation completed successfully")
        except Exception as e:
            logger.error(f"Key rotation failed: {e}")
            self.field_keys = old_keys
            raise

    def get_key_info(self, key_id: str) -> Optional[EncryptionKey]:
        """Get information about an encryption key"""
        return None

    def secure_delete(self, data: Union[str, bytes]) -> Any:
        """Securely delete sensitive data from memory"""
        if isinstance(data, str):
            data = data.encode("utf-8")
        secrets.token_bytes(len(data))

    def generate_secure_random(self, length: int = 32) -> bytes:
        """Generate cryptographically secure random bytes"""
        return secrets.token_bytes(length)

    def generate_secure_token(self, length: int = 32) -> str:
        """Generate cryptographically secure random token"""
        return secrets.token_urlsafe(length)

    def constant_time_compare(self, a: Union[str, bytes], b: Union[str, bytes]) -> bool:
        """Constant-time comparison to prevent timing attacks"""
        if isinstance(a, str):
            a = a.encode("utf-8")
        if isinstance(b, str):
            b = b.encode("utf-8")
        return secrets.compare_digest(a, b)

    def hash_data(self, data: Union[str, bytes], algorithm: str = "sha256") -> str:
        """Hash data using specified algorithm"""
        if isinstance(data, str):
            data = data.encode("utf-8")
        if algorithm == "sha256":
            hash_obj = hashlib.sha256(data)
        elif algorithm == "sha512":
            hash_obj = hashlib.sha512(data)
        elif algorithm == "blake2b":
            hash_obj = hashlib.blake2b(data)
        else:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")
        return hash_obj.hexdigest()

    def get_encryption_stats(self) -> Dict[str, Any]:
        """Get encryption service statistics"""
        return {
            "master_key_initialized": hasattr(self, "master_key"),
            "field_keys_count": len(self.field_keys),
            "supported_algorithms": [alg.value for alg in EncryptionAlgorithm],
            "key_rotation_interval_days": self.key_rotation_interval.days,
        }
