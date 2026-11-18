import os
import random
import string
from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, current_app, send_file, Blueprint
from flask_login import login_required, current_user
from app import db
from app.models import Report, ReportUpdate, Evidence, Notification, User
from app.forms import ComplaintForm
from app.services.audit import log_audit
from app.services.notification import send_notification
from app.services.evidence import save_evidence_file
from app.services.reports import generate_single_complaint_docket_pdf

bp = Blueprint('user', __name__)


def generate_complaint_reference() -> str:
    """Generate unique CivicShield complaint reference (e.g., CS-2026-847291)."""
    prefix = 'CS'
    year = datetime.utcnow().strftime('%Y')
    while True:
        digits = ''.join(random.choices(string.digits, k=6))
        ref = f"{prefix}-{year}-{digits}"
        if not Report.query.filter_by(complaint_number=ref).first():
            return ref


@bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin_user:
        return redirect(url_for('admin.dashboard'))
    elif current_user.is_officer:
        return redirect(url_for('officer.dashboard'))

    # Calculate live statistics from actual authorized database records
    user_reports = Report.query.filter_by(user_id=current_user.id)
    total_complaints = user_reports.filter_by(is_draft=False).count()
    pending_count = user_reports.filter_by(status='Pending', is_draft=False).count()
    active_count = user_reports.filter(
        Report.status.in_(['Verified', 'Assigned', 'Under Investigation', 'Evidence Collected', 'Action Required']),
        Report.is_draft == False
    ).count()
    resolved_count = user_reports.filter(
        Report.status.in_(['Resolved', 'Closed']),
        Report.is_draft == False
    ).count()

    recent_complaints = user_reports.filter_by(is_draft=False).order_by(Report.created_at.desc()).limit(5).all()

    # Find the single most recent status update across all complainant's reports
    latest_update = (
        ReportUpdate.query
        .join(Report, ReportUpdate.report_id == Report.id)
        .filter(Report.user_id == current_user.id, ReportUpdate.is_internal == False)
        .order_by(ReportUpdate.created_at.desc())
        .first()
    )

    return render_template(
        'dashboard/user_dashboard.html',
        title='Citizen Dashboard',
        total_complaints=total_complaints,
        pending_count=pending_count,
        active_count=active_count,
        resolved_count=resolved_count,
        recent_complaints=recent_complaints,
        latest_update=latest_update
    )


@bp.route('/submit-report', methods=['GET', 'POST'])
@login_required
def submit_report():
    if current_user.is_admin_user:
        return redirect(url_for('admin.dashboard'))
    elif current_user.is_officer:
        return redirect(url_for('officer.dashboard'))

    form = ComplaintForm()

    if form.validate_on_submit():
        is_draft = form.save_as_draft.data == 'true'
        ref_number = generate_complaint_reference()

        report = Report(
            complaint_number=ref_number,
            user_id=current_user.id,
            title=form.title.data.strip(),
            description=form.description.data.strip(),
            crime_category=form.crime_category.data,
            incident_date=form.incident_date.data,
            district=form.district.data,
            incident_location=form.incident_location.data.strip(),
            police_station=form.police_station.data,
            status='Draft' if is_draft else 'Pending',
            is_draft=is_draft
        )
        db.session.add(report)
        db.session.commit()

        # Handle multiple evidence files safely
        uploaded_files = request.files.getlist('evidence_files')
        upload_count = 0
        for f in uploaded_files:
            if f and f.filename and f.filename.strip():
                try:
                    save_evidence_file(f, report.id)
                    upload_count += 1
                except Exception as e:
                    flash(f"Warning: File '{f.filename}' could not be processed: {e}", 'warning')

        # Add initial timeline update if finalized
        if not is_draft:
            initial_update = ReportUpdate(
                report_id=report.id,
                status='Pending',
                remarks='Complaint registered successfully. Docket generated and forwarded to police station review.',
                is_internal=False,
                updated_by_id=current_user.id
            )
            db.session.add(initial_update)
            db.session.commit()

            # Create notification
            send_notification(
                user_id=current_user.id,
                title="Complaint Successfully Filed",
                message=f"Your complaint #{report.complaint_number} has been registered and is pending station review.",
                report_id=report.id,
                category='status_update'
            )

            log_audit(
                action='REPORT_SUBMITTED',
                user_id=current_user.id,
                resource_type='report',
                resource_id=report.id,
                details=f"Complaint #{report.complaint_number} filed ({report.crime_category}, {upload_count} files)"
            )

            flash(f"Your complaint has been submitted successfully! Your tracking reference is {report.complaint_number}", 'success')
            return redirect(url_for('user.report_detail', report_id=report.id))
        else:
            flash(f"Draft saved successfully with reference #{report.complaint_number}", 'info')
            return redirect(url_for('user.my_reports'))

    return render_template('reports/submit_report.html', title='File a Complaint', form=form)


@bp.route('/my-reports')
@login_required
def my_reports():
    if current_user.is_admin_user:
        return redirect(url_for('admin.dashboard'))
    elif current_user.is_officer:
        return redirect(url_for('officer.assigned_cases'))

    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '').strip()

    query = Report.query.filter_by(user_id=current_user.id, is_draft=False)
    if status_filter:
        query = query.filter_by(status=status_filter)

    reports = query.order_by(Report.created_at.desc()).paginate(page=page, per_page=10)

    return render_template(
        'reports/my_reports.html',
        title='My Complaints',
        reports=reports,
        current_status=status_filter
    )


@bp.route('/report/<int:report_id>')
@login_required
def report_detail(report_id):
    report = Report.query.get_or_404(report_id)

    # Authorization Check
    if report.user_id != current_user.id and not current_user.is_admin_user and not current_user.is_officer:
        log_audit(
            action='UNAUTHORIZED_REPORT_ACCESS_ATTEMPT',
            user_id=current_user.id,
            resource_type='report',
            resource_id=report_id,
            details=f"User {current_user.username} tried to view report #{report.complaint_number}"
        )
        flash('You do not have permission to view this complaint docket.', 'danger')
        return redirect(url_for('user.dashboard'))

    # Complainants only see non-internal timeline updates
    visible_updates = [upd for upd in report.updates if not upd.is_internal or current_user.is_admin_user or current_user.is_officer]

    return render_template(
        'reports/report_detail.html',
        title=f'Complaint #{report.complaint_number}',
        report=report,
        updates=visible_updates
    )


@bp.route('/report/<int:report_id>/export-pdf')
@login_required
def export_complaint_pdf(report_id):
    report = Report.query.get_or_404(report_id)

    if report.user_id != current_user.id and not current_user.is_admin_user and not current_user.is_officer:
        flash('Unauthorized to download this case docket.', 'danger')
        return redirect(url_for('user.dashboard'))

    pdf_stream = generate_single_complaint_docket_pdf(report)
    log_audit(
        action='REPORT_DOCKET_EXPORTED_PDF',
        user_id=current_user.id,
        resource_type='report',
        resource_id=report_id,
        details=f"Docket PDF exported for #{report.complaint_number}"
    )

    safe_filename = f"Docket_{report.complaint_number.replace('/', '_').replace('-', '_')}.pdf"
    return send_file(
        pdf_stream,
        as_attachment=True,
        download_name=safe_filename,
        mimetype='application/pdf'
    )


@bp.route('/track-report', methods=['GET', 'POST'])
def track_report():
    if current_user.is_authenticated and current_user.is_officer:
        flash("Officers review case records via the Assigned Cases portal.", "info")
        return redirect(url_for('officer.assigned_cases'))
    if current_user.is_authenticated and current_user.is_admin_user:
        flash("Administrators review case records via All Complaints.", "info")
        return redirect(url_for('admin.manage_complaints'))

    complaint_number = request.args.get('complaint_number', '').strip() or request.form.get('complaint_number', '').strip()
    report = None

    if complaint_number:
        # Search by exact complaint number
        report = Report.query.filter(
            (Report.complaint_number.ilike(complaint_number))
        ).first()

        if report:
            # If user is logged in and not admin/officer, verify ownership or show public-safe timeline
            if current_user.is_authenticated and report.user_id != current_user.id and not current_user.is_admin_user and not current_user.is_officer:
                flash("Complaint found. Showing public status overview.", "info")
        else:
            flash(f"No complaint record found matching reference '{complaint_number}'. Please check the format.", "danger")

    return render_template(
        'reports/track_report.html',
        title='Track Complaint Progress',
        report=report,
        complaint_number=complaint_number
    )


@bp.route('/notifications')
@login_required
def notifications():
    page = request.args.get('page', 1, type=int)
    notifs = (
        Notification.query
        .filter_by(user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .paginate(page=page, per_page=15)
    )
    return render_template('reports/notifications.html', title='My Notifications', notifications=notifs)


@bp.route('/notifications/mark-read/<int:notif_id>', methods=['POST'])
@login_required
def mark_notification_read(notif_id):
    notif = Notification.query.filter_by(id=notif_id, user_id=current_user.id).first_or_404()
    notif.is_read = True
    db.session.commit()
    return redirect(request.referrer or url_for('user.notifications'))


@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        if full_name:
            current_user.full_name = full_name
            # If officer profile exists, update profile name as well
            if hasattr(current_user, 'officer_profile') and current_user.officer_profile:
                current_user.officer_profile.name = full_name
        if phone:
            current_user.phone = phone
        db.session.commit()
        flash('Profile information updated successfully.', 'success')
        return redirect(url_for('user.profile'))

    return render_template('user/profile.html', title='User Profile')



@bp.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    flash('All notifications marked as read.', 'success')
    return redirect(request.referrer or url_for('user.notifications'))
