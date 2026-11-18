import os
from flask import Blueprint, abort, send_file, request, current_app, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models import Evidence, Report
from app.services.evidence import can_access_evidence, get_evidence_path
from app.services.audit import log_audit

bp = Blueprint('evidence', __name__, url_prefix='/evidence')


@bp.route('/<int:evidence_id>')
@login_required
def view_evidence(evidence_id):
    """Securely serve evidence file after authenticating user ownership or officer authorization."""
    evidence = Evidence.query.get_or_404(evidence_id)
    report = Report.query.get_or_404(evidence.report_id)

    if not can_access_evidence(current_user, report):
        log_audit(
            action='UNAUTHORIZED_EVIDENCE_ACCESS_ATTEMPT',
            user_id=current_user.id,
            resource_type='evidence',
            resource_id=evidence_id,
            details=f"User {current_user.username} denied access to evidence #{evidence_id} of #{report.complaint_number}"
        )
        abort(403)

    file_path = get_evidence_path(evidence)
    if not file_path or not os.path.exists(file_path):
        flash("Evidence file is not available on storage server.", "danger")
        return redirect(url_for('user.report_detail', report_id=report.id))

    log_audit(
        action='EVIDENCE_ACCESSED',
        user_id=current_user.id,
        resource_type='evidence',
        resource_id=evidence_id,
        details=f"Evidence #{evidence_id} ({evidence.original_filename}) accessed for complaint #{report.complaint_number}"
    )

    as_attachment = request.args.get('download', '0') == '1'
    return send_file(
        file_path,
        mimetype=evidence.file_type or 'application/octet-stream',
        as_attachment=as_attachment,
        download_name=evidence.original_filename
    )
