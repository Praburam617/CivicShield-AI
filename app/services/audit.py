from flask import request
from app import db
from app.models import AuditLog


def log_audit(action: str, user_id=None, resource_type=None, resource_id=None, details=None):
    """Record an audit log entry with client IP address."""
    try:
        ip = request.remote_addr if request else '127.0.0.1'
        if request and request.headers.get('X-Forwarded-For'):
            ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()

        log_entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            details=details,
            ip_address=ip
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
