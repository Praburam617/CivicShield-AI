from functools import wraps
from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, Blueprint
from flask_login import login_required, current_user
from sqlalchemy import or_
from app import db
from app.models import Report, ReportUpdate, User, Evidence, Notification, OfficerProfile
from app.forms import ReportUpdateForm
from app.services.audit import log_audit
from app.services.notification import send_notification

bp = Blueprint('officer', __name__, url_prefix='/officer')


def officer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access the Officer Portal.', 'warning')
            return redirect(url_for('auth.login'))
        if not (current_user.is_officer or current_user.is_admin_user):
            flash('Access restricted to authorized police officers.', 'danger')
            return redirect(url_for('user.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def get_officer_assigned_filter():
    """Return SQLAlchemy filter strictly matching cases assigned to current officer."""
    return or_(
        Report.assigned_officer_id == current_user.id,
        Report.assigned_officer_profile.has(user_id=current_user.id)
    )


def is_officer_authorized_for_case(report):
    """Verify that current_user is either an admin or the strictly assigned officer."""
    if current_user.is_admin_user:
        return True
    if report.assigned_officer_id == current_user.id:
        return True
    if report.officer_profile_id and report.assigned_officer_profile and report.assigned_officer_profile.user_id == current_user.id:
        return True
    return False


@bp.route('/dashboard')
@login_required
@officer_required
def dashboard():
    assigned_query = Report.query.filter(get_officer_assigned_filter(), Report.is_draft == False)

    total_assigned = assigned_query.count()
    under_investigation = assigned_query.filter_by(status='Under Investigation').count()
    evidence_collected = assigned_query.filter_by(status='Evidence Collected').count()
    action_required = assigned_query.filter_by(status='Action Required').count()
    resolved_count = assigned_query.filter(Report.status.in_(['Resolved', 'Closed'])).count()

    recent_cases = assigned_query.order_by(Report.updated_at.desc()).limit(8).all()

    return render_template(
        'officer/dashboard.html',
        title='Officer Dashboard',
        total_assigned=total_assigned,
        under_investigation=under_investigation,
        evidence_collected=evidence_collected,
        action_required=action_required,
        resolved_count=resolved_count,
        recent_cases=recent_cases
    )


@bp.route('/cases')
@login_required
@officer_required
def assigned_cases():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '').strip()
    search = request.args.get('search', '').strip()

    # Strictly limit to cases assigned to current officer
    query = Report.query.filter(get_officer_assigned_filter(), Report.is_draft == False)

    if status and status != 'All':
        query = query.filter(Report.status == status)

    if search:
        query = query.filter(
            or_(
                Report.complaint_number.ilike(f"%{search}%"),
                Report.title.ilike(f"%{search}%"),
                Report.crime_category.ilike(f"%{search}%")
            )
        )

    cases = query.order_by(Report.updated_at.desc()).paginate(page=page, per_page=15)

    return render_template(
        'officer/assigned_cases.html',
        title='My Assigned Cases',
        cases=cases,
        current_status=status,
        search=search
    )


@bp.route('/case/<int:report_id>')
@login_required
@officer_required
def view_case(report_id):
    report = Report.query.get_or_404(report_id)

    # Enforce case ownership
    if not is_officer_authorized_for_case(report):
        log_audit(
            action='UNAUTHORIZED_OFFICER_ACCESS_ATTEMPT',
            user_id=current_user.id,
            resource_type='report',
            resource_id=report.id,
            details=f"Officer {current_user.username} tried to view unassigned case #{report.complaint_number}"
        )
        flash("Access denied. You are only authorized to access cases specifically assigned to your profile.", "danger")
        return redirect(url_for('officer.assigned_cases'))

    form = ReportUpdateForm()
    form.status.data = report.status

    return render_template(
        'officer/view_case.html',
        title=f"Case Docket #{report.complaint_number}",
        report=report,
        form=form
    )


@bp.route('/case/<int:report_id>/update', methods=['POST'])
@login_required
@officer_required
def update_case(report_id):
    report = Report.query.get_or_404(report_id)

    if not is_officer_authorized_for_case(report):
        log_audit(
            action='UNAUTHORIZED_OFFICER_UPDATE_ATTEMPT',
            user_id=current_user.id,
            resource_type='report',
            resource_id=report.id,
            details=f"Officer {current_user.username} tried to update unassigned case #{report.complaint_number}"
        )
        flash("Access denied. You cannot modify a case not assigned to you.", "danger")
        return redirect(url_for('officer.assigned_cases'))

    form = ReportUpdateForm()

    if form.validate_on_submit():
        new_status = form.status.data
        remarks = form.remarks.data.strip() if form.remarks.data else ''
        is_internal = form.is_internal.data

        old_status = report.status
        report.status = new_status
        report.status_updated_at = datetime.utcnow()
        report.updated_at = datetime.utcnow()

        # Update active case count for officer profile
        if report.assigned_officer_profile:
            report.assigned_officer_profile.recalculate_active_cases()

        # Record timeline update
        update_entry = ReportUpdate(
            report_id=report.id,
            status=new_status,
            remarks=remarks or f"Status changed from {old_status} to {new_status}.",
            is_internal=is_internal,
            updated_by_id=current_user.id
        )
        db.session.add(update_entry)
        db.session.commit()

        # Re-sync case count after commit
        if report.assigned_officer_profile:
            report.assigned_officer_profile.recalculate_active_cases()
            db.session.commit()

        # Send in-app notification to citizen if not an internal note
        if not is_internal:
            send_notification(
                user_id=report.user_id,
                title=f"Case Status Update: #{report.complaint_number}",
                message=f"Your complaint status was updated to '{new_status}'. Remarks: {remarks or 'Investigation progressing.'}",
                report_id=report.id,
                category='status_update'
            )

        log_audit(
            action='OFFICER_CASE_UPDATED',
            user_id=current_user.id,
            resource_type='report',
            resource_id=report.id,
            details=f"Officer {current_user.username} updated status of #{report.complaint_number} to {new_status} (Internal: {is_internal})"
        )

        flash(f"Case #{report.complaint_number} updated to {new_status} successfully.", "success")
    else:
        flash("Invalid form submission. Please verify your remarks.", "danger")

    return redirect(url_for('officer.view_case', report_id=report.id))


@bp.route('/case/<int:report_id>/request-info', methods=['POST'])
@login_required
@officer_required
def request_citizen_info(report_id):
    report = Report.query.get_or_404(report_id)

    if not is_officer_authorized_for_case(report):
        flash("Access denied. You cannot request information on this case.", "danger")
        return redirect(url_for('officer.assigned_cases'))

    instructions = request.form.get('instructions', '').strip()

    if not instructions:
        flash("Please provide clear instructions for the requested information.", "warning")
        return redirect(url_for('officer.view_case', report_id=report.id))

    report.status = 'Action Required'
    report.status_updated_at = datetime.utcnow()

    update_entry = ReportUpdate(
        report_id=report.id,
        status='Action Required',
        remarks=f"Officer requested additional details: {instructions}",
        is_internal=False,
        updated_by_id=current_user.id
    )
    db.session.add(update_entry)
    db.session.commit()

    send_notification(
        user_id=report.user_id,
        title=f"Action Required on Complaint #{report.complaint_number}",
        message=f"Investigating officer requested additional details: '{instructions}'. Please review your complaint docket.",
        report_id=report.id,
        category='info_requested'
    )

    log_audit(
        action='OFFICER_INFO_REQUESTED',
        user_id=current_user.id,
        resource_type='report',
        resource_id=report.id,
        details=f"Officer {current_user.username} requested additional information from citizen for #{report.complaint_number}"
    )

    flash("Information request sent to citizen successfully.", "info")
    return redirect(url_for('officer.view_case', report_id=report.id))
