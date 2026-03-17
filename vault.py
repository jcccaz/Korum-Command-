# CONFIDENTIAL - TRADE SECRET
# Proprietary KorumOS source code. Access is limited to authorized personnel
# and collaborators operating under written confidentiality obligations.

"""
KorumOS Vault Service — S3 Presigned Upload Authorization

"Authorization, Not Carriage" — Flask never touches file bytes.
The backend authorizes uploads via presigned POST, the browser uploads
directly to S3, and the async pipeline handles extraction.

Every vault operation is recorded in the Decision Ledger.
"""

import hashlib
import os
import uuid
from datetime import datetime

import boto3
from botocore.config import Config as BotoConfig

from db import db
from models import VaultDocument

# ── Configuration ────────────────────────────────────────────────────────
S3_BUCKET = os.getenv('S3_BUCKET_NAME', 'korum-vault')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
VAULT_MAX_SIZE = 50 * 1024 * 1024  # 50MB

ALLOWED_CONTENT_TYPES = {
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # .docx
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',        # .xlsx
    'application/vnd.openxmlformats-officedocument.presentationml.presentation', # .pptx
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp',
}

# Extension → content type mapping for validation
EXT_CONTENT_MAP = {
    '.pdf': 'application/pdf',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
    '.png': 'image/png', '.gif': 'image/gif', '.webp': 'image/webp',
}


def _get_s3_client():
    """Create an S3 client using environment credentials."""
    return boto3.client(
        's3',
        region_name=AWS_REGION,
        config=BotoConfig(signature_version='s3v4'),
    )


def vault_available():
    """Check if S3 vault is configured (env vars present)."""
    return bool(os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY'))


def initialize_vault_upload(user_id, mission_id, filename, content_type, size_bytes=None):
    """Authorize a direct-to-S3 upload and return presigned POST fields.

    Args:
        user_id: Authenticated user ID
        mission_id: Mission/thread UUID (can be None for standalone uploads)
        filename: Original filename (hashed, never stored raw)
        content_type: MIME type — must be in allowlist
        size_bytes: Declared file size (optional, validated by S3 conditions)

    Returns:
        dict: {vault_doc_id, presigned_url, presigned_fields, s3_key}

    Raises:
        ValueError: If content_type is not allowed or size exceeds limit
    """
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError(f"Content type not allowed: {content_type}")

    if size_bytes and size_bytes > VAULT_MAX_SIZE:
        raise ValueError(f"File exceeds {VAULT_MAX_SIZE // (1024*1024)}MB limit")

    # Generate S3 key — structured for audit and lifecycle policies
    now = datetime.utcnow()
    file_uuid = str(uuid.uuid4())
    # Sanitize filename for S3 key (keep extension only)
    ext = ''
    if '.' in filename:
        ext = '.' + filename.rsplit('.', 1)[-1].lower()
    s3_key = f"vault/{mission_id or 'unscoped'}/{now.year}/{now.month:02d}/{file_uuid}{ext}"

    # Hash the filename — never store raw filenames
    filename_hash = hashlib.sha256(filename.encode()).hexdigest()

    # Create VaultDocument record
    vault_doc = VaultDocument(
        id=file_uuid,
        mission_id=mission_id,
        user_id=user_id,
        s3_key=s3_key,
        filename_hash=filename_hash,
        content_type=content_type,
        size_bytes=size_bytes,
        status='authorized',
    )
    db.session.add(vault_doc)
    db.session.commit()

    # Generate presigned POST
    s3 = _get_s3_client()
    conditions = [
        ['content-length-range', 1, VAULT_MAX_SIZE],
        {'Content-Type': content_type},
    ]
    presigned = s3.generate_presigned_post(
        Bucket=S3_BUCKET,
        Key=s3_key,
        Conditions=conditions,
        Fields={'Content-Type': content_type},
        ExpiresIn=600,  # 10 minutes to complete upload
    )

    print(f"[VAULT] Authorized upload: {file_uuid[:8]} | type={content_type} | key={s3_key}")

    return {
        'vault_doc_id': file_uuid,
        'presigned_url': presigned['url'],
        'presigned_fields': presigned['fields'],
        's3_key': s3_key,
    }


def confirm_upload(vault_doc_id):
    """Verify the file landed in S3 and update status.

    Args:
        vault_doc_id: UUID of the VaultDocument

    Returns:
        VaultDocument instance

    Raises:
        ValueError: If document not found or not in 'authorized' state
    """
    vault_doc = VaultDocument.query.get(vault_doc_id)
    if not vault_doc:
        raise ValueError(f"Vault document not found: {vault_doc_id}")
    if vault_doc.status != 'authorized':
        raise ValueError(f"Document not in authorized state: {vault_doc.status}")

    # Verify object exists in S3
    s3 = _get_s3_client()
    try:
        head = s3.head_object(Bucket=S3_BUCKET, Key=vault_doc.s3_key)
        vault_doc.size_bytes = head.get('ContentLength', vault_doc.size_bytes)
    except s3.exceptions.ClientError:
        vault_doc.status = 'failed'
        vault_doc.error_detail = 'S3 object not found after upload'
        db.session.commit()
        raise ValueError("Upload verification failed — object not found in S3")

    vault_doc.status = 'uploaded'
    db.session.commit()

    print(f"[VAULT] Upload confirmed: {vault_doc_id[:8]} | size={vault_doc.size_bytes}")
    return vault_doc


def get_vault_document(vault_doc_id):
    """Fetch a VaultDocument by ID."""
    return VaultDocument.query.get(vault_doc_id)


def stream_from_s3(s3_key):
    """Stream an object's bytes from S3.

    Returns:
        bytes: Raw file content
    """
    s3 = _get_s3_client()
    response = s3.get_object(Bucket=S3_BUCKET, Key=s3_key)
    return response['Body'].read()
