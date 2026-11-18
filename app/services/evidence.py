import os
import uuid
from typing import Optional, Tuple
from werkzeug.utils import secure_filename
from PIL import Image
from flask import current_app
from app import db
from app.models import Evidence, Report, User
from app.services.audit import log_audit
from config import Config


def validate_file_content(file_storage) -> Tuple[bool, str]:
    """Validate both file extension and actual binary payload to prevent spoofing."""
    if not file_storage or not file_storage.filename:
        return False, "No file provided"

    filename = file_storage.filename
    if '.' not in filename:
        return False, "File must have an extension"

    ext = filename.rsplit('.', 1)[1].lower()
    if ext not in Config.ALLOWED_EXTENSIONS:
        return False, f"File extension '{ext}' is not permitted. Allowed: {', '.join(Config.ALLOWED_EXTENSIONS)}"

    # Read leading bytes to inspect magic signature
    file_storage.seek(0)
    header = file_storage.read(2048)
    file_storage.seek(0)

    if ext == 'pdf':
        if not header.startswith(b'%PDF-'):
            return False, "Invalid PDF file structure"
    else:
        # Validate image integrity with Pillow
        try:
            img = Image.open(file_storage)
            img.verify()
            file_storage.seek(0)
        except Exception:
            file_storage.seek(0)
            return False, "Corrupted or invalid image file"

    return True, "Valid"


def save_evidence_file(file_storage, report_id: int) -> Optional[Evidence]:
    """Save an evidence file into protected storage and record in database."""
    is_valid, msg = validate_file_content(file_storage)
    if not is_valid:
        raise ValueError(msg)

    orig_name = secure_filename(file_storage.filename)
    ext = orig_name.rsplit('.', 1)[1].lower() if '.' in orig_name else 'dat'
    unique_name = f"{uuid.uuid4().hex}_{orig_name}"
    
    upload_dir = current_app.config['PROTECTED_UPLOAD_FOLDER']
    os.makedirs(upload_dir, exist_ok=True)
    destination = os.path.join(upload_dir, unique_name)

    file_storage.seek(0, os.SEEK_END)
    size = file_storage.tell()
    file_storage.seek(0)

    file_storage.save(destination)

    mime = 'application/pdf' if ext == 'pdf' else f'image/{ext}'
    evidence = Evidence(
        report_id=report_id,
        filename=unique_name,
        original_filename=orig_name,
        file_type=mime,
        file_size=size
    )
    db.session.add(evidence)
    db.session.commit()
    return evidence


def can_access_evidence(user: User, report: Report) -> bool:
    """RBAC check: Complainant, Assigned Officer, or Admin can access."""
    if not user.is_authenticated:
        return False
    if user.is_admin_user:
        return True
    if report.user_id == user.id:
        return True
    if user.is_officer:
        # Officer assigned to this case or officer in same station
        if report.assigned_officer_id == user.id:
            return True
        if user.police_station and report.police_station == user.police_station:
            return True
        if report.assigned_officer and (user.username.lower() in report.assigned_officer.lower() or (user.full_name and user.full_name.lower() in report.assigned_officer.lower())):
            return True
    return False


def get_evidence_path(evidence: Evidence) -> Optional[str]:
    """Resolve full filesystem path for an evidence item, checking protected storage then legacy."""
    protected_dir = current_app.config['PROTECTED_UPLOAD_FOLDER']
    primary_path = os.path.join(protected_dir, evidence.filename)
    if os.path.exists(primary_path):
        return primary_path

    # Fallback to legacy folder
    legacy_dir = current_app.config.get('LEGACY_UPLOAD_FOLDER')
    if legacy_dir:
        legacy_path = os.path.join(legacy_dir, evidence.filename)
        if os.path.exists(legacy_path):
            return legacy_path

    return None
