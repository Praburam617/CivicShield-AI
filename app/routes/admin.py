import io
from functools import wraps
from datetime import datetime, timedelta
from flask import render_template, redirect, url_for, flash, request, Response, send_file, Blueprint
from flask_login import login_required, current_user
from sqlalchemy import func, or_
from app import db
from config import Config
from app.models import Report, User, ReportUpdate, AuditLog, PoliceStation, CrimeCategory, OfficerProfile
from app.forms import ReportUpdateForm, OfficerAssignmentForm, UserRoleForm, OfficerProfileForm, OfficerProvisionAccountForm
from app.services.audit import log_audit
from app.services.notification import send_notification
from app.services.reports import build_filtered_query, generate_complaints_csv, generate_complaints_pdf

bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin_user:
            flash('Access restricted to system administrators.', 'danger')
            return redirect(url_for('auth.index'))
        return f(*args, **kwargs)
    return decorated_function


@bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    total_complaints = Report.query.filter_by(is_draft=False).count()
    pending_count = Report.query.filter_by(status='Pending', is_draft=False).count()
    investigating_count = Report.query.filter(Report.status.in_(['Under Investigation', 'Evidence Collected', 'Action Required'])).count()
    resolved_count = Report.query.filter(Report.status.in_(['Resolved', 'Closed'])).count()
    rejected_count = Report.query.filter_by(status='Rejected').count()
    
    total_citizens = User.query.filter_by(role='citizen').count()
    total_officers = User.query.filter_by(role='officer').count()
    total_officers_directory = OfficerProfile.query.count()

    recent_complaints = Report.query.filter_by(is_draft=False).order_by(Report.created_at.desc()).limit(7).all()

    # Category breakdown
    category_counts = (
        db.session.query(Report.crime_category, func.count(Report.id))
        .filter(Report.is_draft == False)
        .group_by(Report.crime_category)
        .order_by(func.count(Report.id).desc())
        .limit(8)
        .all()
    )

    # Monthly trends (last 6 months)
    six_months_ago = datetime.utcnow() - timedelta(days=180)
    monthly_trends = (
        db.session.query(
            func.strftime('%Y-%m', Report.created_at).label('month'),
            func.count(Report.id).label('count')
        )
        .filter(Report.created_at >= six_months_ago, Report.is_draft == False)
        .group_by('month')
        .order_by('month')
        .all()
    )

    return render_template(
        'admin/dashboard.html',
        title='Administrator Dashboard',
        total_complaints=total_complaints,
        pending_count=pending_count,
        investigating_count=investigating_count,
        resolved_count=resolved_count,
        rejected_count=rejected_count,
        total_citizens=total_citizens,
        total_officers=total_officers,
        total_officers_directory=total_officers_directory,
        recent_complaints=recent_complaints,
        category_counts=category_counts,
        monthly_trends=monthly_trends
    )


@bp.route('/complaints')
@bp.route('/reports')
@login_required
@admin_required
def manage_complaints():
    page = request.args.get('page', 1, type=int)
    filters = {
        'search': request.args.get('search', ''),
        'status': request.args.get('status', ''),
        'category': request.args.get('category', ''),
        'district': request.args.get('district', ''),
        'station': request.args.get('station', ''),
        'officer': request.args.get('officer', ''),
        'date_from': request.args.get('date_from', ''),
        'date_to': request.args.get('date_to', ''),
        'sort_by': request.args.get('sort_by', 'created_at_desc')
    }

    query = build_filtered_query(filters)
    reports = query.paginate(page=page, per_page=15)
    officers = User.query.filter((User.role == 'officer') | (User.is_admin == True)).all()

    return render_template(
        'admin/manage_complaints.html',
        title='All Complaints Management',
        reports=reports,
        filters=filters,
        officers=officers
    )


@bp.route('/complaint/<int:report_id>')
@bp.route('/report/<int:report_id>')
@login_required
@admin_required
def view_complaint(report_id):
    report = Report.query.get_or_404(report_id)
    update_form = ReportUpdateForm()
    update_form.status.data = report.status
    update_form.remarks.data = report.admin_remarks

    # Display only active officers belonging to that complaint's police station
    station_officers = OfficerProfile.query.filter_by(
        police_station=report.police_station,
        is_available=True
    ).order_by(OfficerProfile.designation.asc(), OfficerProfile.name.asc()).all()

    # Fallback if no officers exist for that station
    if not station_officers:
        station_officers = OfficerProfile.query.filter_by(is_available=True).order_by(OfficerProfile.police_station.asc(), OfficerProfile.name.asc()).all()

    return render_template(
        'admin/view_complaint.html',
        title=f"Complaint #{report.complaint_number}",
        report=report,
        update_form=update_form,
        station_officers=station_officers
    )


@bp.route('/complaint/<int:report_id>/update', methods=['POST'])
@login_required
@admin_required
def update_complaint(report_id):
    report = Report.query.get_or_404(report_id)
    new_status = request.form.get('status', '').strip()
    remarks = request.form.get('remarks', '').strip()
    is_internal = request.form.get('is_internal') == 'y'

    if not new_status:
        flash("Please select a valid status.", "warning")
        return redirect(url_for('admin.view_complaint', report_id=report.id))

    old_status = report.status
    report.status = new_status
    report.admin_remarks = remarks
    report.status_updated_at = datetime.utcnow()
    report.updated_at = datetime.utcnow()

    # Update active case count for assigned officer profile if status changed to resolved/closed/rejected
    if report.assigned_officer_profile:
        report.assigned_officer_profile.recalculate_active_cases()

    update_entry = ReportUpdate(
        report_id=report.id,
        status=new_status,
        remarks=remarks or f"Status changed from {old_status} to {new_status} by Admin.",
        is_internal=is_internal,
        updated_by_id=current_user.id
    )
    db.session.add(update_entry)
    db.session.commit()

    if not is_internal:
        send_notification(
            user_id=report.user_id,
            title=f"Complaint Status Update: #{report.complaint_number}",
            message=f"Your complaint status was changed to '{new_status}'. Remarks: {remarks or 'Updated by administrative authority.'}",
            report_id=report.id,
            category='status_update'
        )

    log_audit(
        action='ADMIN_REPORT_UPDATED',
        user_id=current_user.id,
        resource_type='report',
        resource_id=report.id,
        details=f"Admin updated complaint #{report.complaint_number} status to {new_status}"
    )

    flash(f"Complaint #{report.complaint_number} updated successfully.", "success")
    return redirect(url_for('admin.view_complaint', report_id=report.id))


@bp.route('/complaint/<int:report_id>/assign', methods=['POST'])
@login_required
@admin_required
def assign_officer(report_id):
    report = Report.query.get_or_404(report_id)
    officer_profile_id = request.form.get('officer_profile_id', type=int)
    notes = request.form.get('notes', '').strip()

    if not officer_profile_id:
        raw_id = request.form.get('officer_id', type=int)
        if raw_id:
            off_prof = OfficerProfile.query.get(raw_id)
            if off_prof:
                officer_profile_id = off_prof.id
            else:
                user_prof = OfficerProfile.query.filter_by(user_id=raw_id).first()
                if user_prof:
                    officer_profile_id = user_prof.id

    if not officer_profile_id:
        flash("Please select an officer from the list.", "warning")
        return redirect(url_for('admin.view_complaint', report_id=report.id))

    officer = OfficerProfile.query.get_or_404(officer_profile_id)

    # Validate that officer belongs to the complaint's police station
    if officer.police_station != report.police_station:
        flash(f"Officer {officer.name} belongs to '{officer.police_station}', but this complaint is under '{report.police_station}'.", "danger")
        return redirect(url_for('admin.view_complaint', report_id=report.id))

    if not officer.is_available:
        flash(f"Officer {officer.name} is currently marked as unavailable for new assignments.", "warning")
        return redirect(url_for('admin.view_complaint', report_id=report.id))

    prev_officer = report.assigned_officer_profile

    # Assign officer profile
    report.officer_profile_id = officer.id
    report.assigned_officer = f"{officer.designation} {officer.name}"

    # If officer has linked user account, link it
    if officer.user_id:
        report.assigned_officer_id = officer.user_id
    else:
        report.assigned_officer_id = None

    if report.status == 'Pending':
        report.status = 'Under Investigation'

    report.status_updated_at = datetime.utcnow()
    report.updated_at = datetime.utcnow()

    update_entry = ReportUpdate(
        report_id=report.id,
        status=report.status,
        remarks=f"Assigned to {officer.designation} {officer.name} ({officer.badge_number}). {notes}".strip(),
        is_internal=False,
        updated_by_id=current_user.id
    )
    db.session.add(update_entry)
    db.session.commit()

    # Recalculate case counts
    officer.recalculate_active_cases()
    if prev_officer and prev_officer.id != officer.id:
        prev_officer.recalculate_active_cases()
    db.session.commit()

    # Notify Citizen
    send_notification(
        user_id=report.user_id,
        title=f"Officer Assigned: #{report.complaint_number}",
        message=f"{officer.designation} {officer.name} ({officer.badge_number}) has been assigned to investigate your complaint.",
        report_id=report.id,
        category='officer_assigned'
    )

    # Notify Officer if they have an active user account
    if officer.user_id:
        send_notification(
            user_id=officer.user_id,
            title=f"New Case Assignment: #{report.complaint_number}",
            message=f"You have been assigned to investigate case #{report.complaint_number} ({report.crime_category}) at {report.police_station}.",
            report_id=report.id,
            category='officer_assigned'
        )

    log_audit(
        action='OFFICER_ASSIGNED',
        user_id=current_user.id,
        resource_type='report',
        resource_id=report.id,
        details=f"Assigned {officer.designation} {officer.name} ({officer.badge_number}) to complaint #{report.complaint_number}"
    )

    flash(f"Assigned {officer.designation} {officer.name} ({officer.badge_number}) to complaint #{report.complaint_number}.", "success")
    return redirect(url_for('admin.view_complaint', report_id=report.id))


@bp.route('/officers')
@login_required
@admin_required
def manage_officers():
    page = request.args.get('page', 1, type=int)
    station_filter = request.args.get('station', '').strip()
    availability_filter = request.args.get('available', '').strip()
    account_filter = request.args.get('account', '').strip()
    search = request.args.get('search', '').strip()

    query = OfficerProfile.query
    if station_filter and station_filter != 'All':
        query = query.filter_by(police_station=station_filter)
    if availability_filter in ('true', '1'):
        query = query.filter_by(is_available=True)
    elif availability_filter in ('false', '0'):
        query = query.filter_by(is_available=False)
    if account_filter == 'linked':
        query = query.filter(OfficerProfile.user_id.isnot(None))
    elif account_filter == 'unlinked':
        query = query.filter(OfficerProfile.user_id.is_(None))
    if search:
        query = query.filter(
            or_(
                OfficerProfile.name.ilike(f"%{search}%"),
                OfficerProfile.badge_number.ilike(f"%{search}%"),
                OfficerProfile.designation.ilike(f"%{search}%"),
                OfficerProfile.department.ilike(f"%{search}%")
            )
        )

    officers = query.order_by(OfficerProfile.police_station.asc(), OfficerProfile.designation.asc(), OfficerProfile.name.asc()).paginate(page=page, per_page=15)
    stations = Config.POLICE_STATIONS

    return render_template(
        'admin/manage_officers.html',
        title='Police Officer Directory Management',
        officers=officers,
        stations=stations,
        current_station=station_filter,
        current_available=availability_filter,
        current_account=account_filter,
        search=search
    )


@bp.route('/officers/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_officer():
    form = OfficerProfileForm()
    if form.validate_on_submit():
        badge = form.badge_number.data.strip().upper()
        if OfficerProfile.query.filter_by(badge_number=badge).first():
            flash(f"Officer with badge number '{badge}' already exists.", "danger")
            return render_template('admin/edit_officer.html', title='Add New Officer Profile', form=form, is_create=True)

        officer = OfficerProfile(
            name=form.name.data.strip(),
            badge_number=badge,
            designation=form.designation.data,
            department=form.department.data.strip(),
            police_station=form.police_station.data,
            is_available=form.is_available.data,
            active_case_count=0
        )
        db.session.add(officer)
        db.session.commit()

        log_audit(
            action='OFFICER_PROFILE_CREATED',
            user_id=current_user.id,
            resource_type='officer_profile',
            resource_id=officer.id,
            details=f"Created officer profile {officer.designation} {officer.name} ({officer.badge_number})"
        )

        flash(f"Officer profile for '{officer.name}' created successfully.", "success")
        return redirect(url_for('admin.manage_officers'))

    return render_template('admin/edit_officer.html', title='Add New Officer Profile', form=form, is_create=True)


@bp.route('/officers/<int:officer_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_officer(officer_id):
    officer = OfficerProfile.query.get_or_404(officer_id)
    form = OfficerProfileForm(obj=officer)

    if form.validate_on_submit():
        badge = form.badge_number.data.strip().upper()
        existing = OfficerProfile.query.filter_by(badge_number=badge).first()
        if existing and existing.id != officer.id:
            flash(f"Badge number '{badge}' is already in use by another officer.", "danger")
            return render_template('admin/edit_officer.html', title=f"Edit Officer: {officer.name}", form=form, officer=officer, is_create=False)

        officer.name = form.name.data.strip()
        officer.badge_number = badge
        officer.designation = form.designation.data
        officer.department = form.department.data.strip()
        officer.police_station = form.police_station.data
        officer.is_available = form.is_available.data
        db.session.commit()

        # Synchronize linked user if present
        if officer.user:
            officer.user.full_name = officer.name
            officer.user.badge_number = officer.badge_number
            officer.user.department = officer.department
            officer.user.police_station = officer.police_station
            db.session.commit()

        log_audit(
            action='OFFICER_PROFILE_UPDATED',
            user_id=current_user.id,
            resource_type='officer_profile',
            resource_id=officer.id,
            details=f"Updated officer profile {officer.name} ({officer.badge_number})"
        )

        flash(f"Officer profile '{officer.name}' updated successfully.", "success")
        return redirect(url_for('admin.manage_officers'))

    return render_template('admin/edit_officer.html', title=f"Edit Officer: {officer.name}", form=form, officer=officer, is_create=False)


@bp.route('/officers/<int:officer_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_officer_status(officer_id):
    officer = OfficerProfile.query.get_or_404(officer_id)
    officer.is_available = not officer.is_available
    db.session.commit()

    status_str = "available" if officer.is_available else "unavailable"
    log_audit(
        action='OFFICER_AVAILABILITY_TOGGLED',
        user_id=current_user.id,
        resource_type='officer_profile',
        resource_id=officer.id,
        details=f"Officer {officer.name} marked {status_str}"
    )

    flash(f"Officer {officer.name} is now marked as {status_str}.", "info")
    return redirect(url_for('admin.manage_officers'))


@bp.route('/officers/<int:officer_id>/provision-account', methods=['GET', 'POST'])
@login_required
@admin_required
def provision_officer_account(officer_id):
    officer = OfficerProfile.query.get_or_404(officer_id)
    if officer.user_id:
        flash(f"Officer {officer.name} already has a linked login account ({officer.user.username}).", "info")
        return redirect(url_for('admin.manage_officers'))

    form = OfficerProvisionAccountForm()
    if request.method == 'GET':
        clean_user = officer.name.lower().replace(' ', '.').replace("'", '')
        form.username.data = clean_user
        form.email.data = f"{clean_user}@civicshield.example"

    if form.validate_on_submit():
        username = form.username.data.strip()
        email = form.email.data.strip().lower()

        if User.query.filter_by(username=username).first():
            flash(f"Username '{username}' is already taken.", "danger")
            return render_template('admin/provision_officer.html', title=f"Provision Login: {officer.name}", officer=officer, form=form)

        if User.query.filter_by(email=email).first():
            flash(f"Email '{email}' is already registered.", "danger")
            return render_template('admin/provision_officer.html', title=f"Provision Login: {officer.name}", officer=officer, form=form)

        new_user = User(
            username=username,
            email=email,
            full_name=officer.name,
            role='officer',
            badge_number=officer.badge_number,
            department=officer.department,
            police_station=officer.police_station,
            is_admin=False,
            is_active=True
        )
        new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.flush()

        officer.user_id = new_user.id
        db.session.commit()

        log_audit(
            action='OFFICER_ACCOUNT_PROVISIONED',
            user_id=current_user.id,
            resource_type='user',
            resource_id=new_user.id,
            details=f"Admin created login account '{username}' for officer {officer.name} ({officer.badge_number})"
        )

        flash(f"Login account created for {officer.name}! Username: {username}", "success")
        return redirect(url_for('admin.manage_officers'))

    return render_template('admin/provision_officer.html', title=f"Provision Login: {officer.name}", officer=officer, form=form)



@bp.route('/users')
@login_required
@admin_required
def manage_users():
    page = request.args.get('page', 1, type=int)
    role_filter = request.args.get('role', '').strip()
    search = request.args.get('search', '').strip()

    query = User.query
    if role_filter and role_filter != 'All':
        query = query.filter_by(role=role_filter)
    if search:
        query = query.filter(
            or_(
                User.username.ilike(f"%{search}%"),
                User.full_name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.badge_number.ilike(f"%{search}%")
            )
        )

    users = query.order_by(User.created_at.desc()).paginate(page=page, per_page=15)
    return render_template(
        'admin/manage_users.html',
        title='User & Officer Management',
        users=users,
        current_role=role_filter,
        search=search
    )


@bp.route('/user/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserRoleForm(obj=user)

    if form.validate_on_submit():
        user.role = form.role.data
        user.badge_number = form.badge_number.data.strip() if form.badge_number.data else None
        user.department = form.department.data.strip() if form.department.data else None
        user.police_station = form.police_station.data if form.police_station.data else None
        user.is_active = form.is_active.data
        user.is_admin = (form.role.data == 'admin')
        db.session.commit()

        log_audit(
            action='USER_ROLE_UPDATED',
            user_id=current_user.id,
            resource_type='user',
            resource_id=user.id,
            details=f"Admin updated user {user.username} (Role: {user.role}, Active: {user.is_active})"
        )

        flash(f"User permissions for '{user.username}' updated successfully.", "success")
        return redirect(url_for('admin.manage_users'))

    return render_template('admin/edit_user.html', title=f"Edit Permissions: {user.username}", user=user, form=form)


@bp.route('/user/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot deactivate your own administrative account.", "danger")
        return redirect(url_for('admin.manage_users'))

    user.is_active = not user.is_active
    db.session.commit()

    status_str = "activated" if user.is_active else "deactivated"
    log_audit(
        action='USER_STATUS_TOGGLED',
        user_id=current_user.id,
        resource_type='user',
        resource_id=user.id,
        details=f"User {user.username} was {status_str}"
    )

    flash(f"User {user.username} has been {status_str}.", "info")
    return redirect(url_for('admin.manage_users'))


@bp.route('/analytics')
@bp.route('/statistics')
@login_required
@admin_required
def analytics():
    # Reports by status
    status_distribution = (
        db.session.query(Report.status, func.count(Report.id))
        .filter(Report.is_draft == False)
        .group_by(Report.status)
        .all()
    )

    # Reports by category
    category_distribution = (
        db.session.query(Report.crime_category, func.count(Report.id))
        .filter(Report.is_draft == False)
        .group_by(Report.crime_category)
        .order_by(func.count(Report.id).desc())
        .all()
    )

    # Reports by district
    district_distribution = (
        db.session.query(Report.district, func.count(Report.id))
        .filter(Report.is_draft == False)
        .group_by(Report.district)
        .order_by(func.count(Report.id).desc())
        .all()
    )

    # Monthly resolution stats
    monthly_data = (
        db.session.query(
            func.strftime('%Y-%m', Report.created_at).label('month'),
            func.count(Report.id).label('total'),
            func.sum(db.case((Report.status.in_(['Resolved', 'Closed']), 1), else_=0)).label('resolved')
        )
        .filter(Report.is_draft == False)
        .group_by('month')
        .order_by('month')
        .limit(12)
        .all()
    )

    return render_template(
        'admin/analytics.html',
        title='Crime Analytics & Reporting Trends',
        status_distribution=status_distribution,
        category_distribution=category_distribution,
        district_distribution=district_distribution,
        monthly_data=monthly_data
    )


@bp.route('/audit-logs')
@login_required
@admin_required
def audit_logs():
    page = request.args.get('page', 1, type=int)
    action_filter = request.args.get('action', '').strip()
    search = request.args.get('search', '').strip()

    query = AuditLog.query
    if action_filter:
        query = query.filter_by(action=action_filter)
    if search:
        query = query.filter(
            or_(
                AuditLog.action.ilike(f"%{search}%"),
                AuditLog.details.ilike(f"%{search}%"),
                AuditLog.ip_address.ilike(f"%{search}%")
            )
        )

    logs = query.order_by(AuditLog.timestamp.desc()).paginate(page=page, per_page=25)
    actions = [r[0] for r in db.session.query(AuditLog.action).distinct().all()]

    return render_template(
        'admin/audit_logs.html',
        title='System Audit Logs',
        logs=logs,
        actions=actions,
        current_action=action_filter,
        search=search
    )


@bp.route('/export/csv')
@login_required
@admin_required
def export_csv():
    filters = {
        'search': request.args.get('search', ''),
        'status': request.args.get('status', ''),
        'category': request.args.get('category', ''),
        'district': request.args.get('district', ''),
        'station': request.args.get('station', ''),
        'officer': request.args.get('officer', ''),
        'date_from': request.args.get('date_from', ''),
        'date_to': request.args.get('date_to', ''),
        'sort_by': request.args.get('sort_by', 'created_at_desc')
    }

    query = build_filtered_query(filters)
    reports = query.all()

    csv_data = generate_complaints_csv(reports)
    log_audit(
        action='REPORTS_EXPORTED_CSV',
        user_id=current_user.id,
        resource_type='report',
        details=f"Exported {len(reports)} complaints to CSV"
    )

    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=CivicShield_Complaints_{timestamp}.csv"}
    )


@bp.route('/export/pdf')
@login_required
@admin_required
def export_pdf():
    filters = {
        'search': request.args.get('search', ''),
        'status': request.args.get('status', ''),
        'category': request.args.get('category', ''),
        'district': request.args.get('district', ''),
        'station': request.args.get('station', ''),
        'officer': request.args.get('officer', ''),
        'date_from': request.args.get('date_from', ''),
        'date_to': request.args.get('date_to', ''),
        'sort_by': request.args.get('sort_by', 'created_at_desc')
    }

    query = build_filtered_query(filters)
    reports = query.limit(200).all()

    summary = f"Status: {filters.get('status') or 'All'}, Category: {filters.get('category') or 'All'}"
    pdf_buffer = generate_complaints_pdf(reports, filter_summary=summary)

    log_audit(
        action='REPORTS_EXPORTED_PDF',
        user_id=current_user.id,
        resource_type='report',
        details=f"Exported {len(reports)} complaints to PDF report"
    )

    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f"CivicShield_Report_{timestamp}.pdf",
        mimetype='application/pdf'
    )
