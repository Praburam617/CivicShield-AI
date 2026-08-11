from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Report, User, ReportUpdate
from app.forms import ReportUpdateForm
from flask import Blueprint
from functools import wraps
from datetime import datetime
from sqlalchemy import func, or_

bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if (
            not current_user.is_authenticated
            or not current_user.is_admin
            or not current_user.is_active
        ):
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('auth.index'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # Statistics
    total_reports = Report.query.count()
    pending_reports = Report.query.filter_by(status='Pending').count()
    investigating_reports = Report.query.filter_by(status='Under Investigation').count()
    evidence_collected_reports = Report.query.filter_by(status='Evidence Collected').count()
    resolved_reports = Report.query.filter_by(status='Resolved').count()
    rejected_reports = Report.query.filter_by(status='Rejected').count()
    total_users = User.query.count()
    
    # Recent reports
    recent_reports = Report.query.order_by(Report.created_at.desc()).limit(10).all()
    
    # Reports by category
    categories = db.session.query(Report.crime_category, func.count(Report.id)).group_by(Report.crime_category).all()
    
    return render_template('dashboard/admin_dashboard.html',
                         title='Admin Dashboard',
                         total_reports=total_reports,
                         pending_reports=pending_reports,
                         investigating_reports=investigating_reports,
                         evidence_collected_reports=evidence_collected_reports,
                         resolved_reports=resolved_reports,
                         rejected_reports=rejected_reports,
                         total_users=total_users,
                         recent_reports=recent_reports,
                         categories=categories)

@bp.route('/reports')
@login_required
@admin_required
def manage_reports():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    search = request.args.get('search', '').strip()
    
    query = Report.query
    if status:
        query = query.filter_by(status=status)
    if search:
        like_term = f'%{search}%'
        query = query.join(User).filter(
            or_(
                Report.complaint_number.ilike(like_term),
                Report.title.ilike(like_term),
                Report.crime_category.ilike(like_term),
                Report.police_station.ilike(like_term),
                User.username.ilike(like_term),
                User.full_name.ilike(like_term),
                User.email.ilike(like_term)
            )
        )
    
    reports = query.order_by(Report.created_at.desc()).paginate(page=page, per_page=20)
    
    return render_template(
        'admin/manage_reports.html',
        title='Manage Complaints',
        reports=reports,
        current_status=status,
        search=search
    )

@bp.route('/report/<int:report_id>')
@login_required
@admin_required
def view_report(report_id):
    report = Report.query.get_or_404(report_id)
    form = ReportUpdateForm()
    
    # Pre-populate form
    form.status.data = report.status
    form.assigned_officer.data = report.assigned_officer
    form.remarks.data = report.admin_remarks
    
    return render_template('admin/view_report.html', title='View Complaint', report=report, form=form)

@bp.route('/report/<int:report_id>/update', methods=['POST'])
@login_required
@admin_required
def update_report(report_id):
    report = Report.query.get_or_404(report_id)
    form = ReportUpdateForm()
    
    if form.validate_on_submit():
        apply_report_update(
            report=report,
            new_status=form.status.data,
            assigned_officer=form.assigned_officer.data,
            remarks=form.remarks.data
        )
        flash(f'Complaint #{report.complaint_number} has been updated successfully!', 'success')
    else:
        flash('Unable to update complaint. Please check the form values and try again.', 'danger')
    
    return redirect(url_for('admin.view_report', report_id=report.id))


@bp.route('/report/<int:report_id>/quick-update', methods=['POST'])
@login_required
@admin_required
def quick_update_report(report_id):
    report = Report.query.get_or_404(report_id)
    new_status = request.form.get('status', '').strip()
    assigned_officer = request.form.get('assigned_officer', '').strip() or None
    remarks = request.form.get('remarks', '').strip() or None

    valid_statuses = {choice[0] for choice in ReportUpdateForm().status.choices}
    if new_status not in valid_statuses:
        flash('Invalid complaint status selected.', 'danger')
        return redirect(url_for('admin.manage_reports'))

    apply_report_update(
        report=report,
        new_status=new_status,
        assigned_officer=assigned_officer,
        remarks=remarks
    )
    flash(f'Complaint #{report.complaint_number} moved to {new_status}.', 'success')
    return redirect(url_for('admin.manage_reports', status=request.args.get('status', ''), search=request.args.get('search', '')))

@bp.route('/users')
@login_required
@admin_required
def manage_users():
    page = request.args.get('page', 1, type=int)
    users = User.query.order_by(User.created_at.desc()).paginate(page=page, per_page=20)
    
    return render_template('admin/manage_users.html', title='Manage Users', users=users)

@bp.route('/user/<int:user_id>/toggle-status')
@login_required
@admin_required
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('You cannot deactivate your own account!', 'danger')
        return redirect(url_for('admin.manage_users'))
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User {user.username} has been {status}!', 'success')
    
    return redirect(url_for('admin.manage_users'))

@bp.route('/statistics')
@login_required
@admin_required
def statistics():
    from datetime import datetime, timedelta
    
    # Reports by date (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    reports_by_date = db.session.query(
        func.date(Report.created_at).label('date'),
        func.count(Report.id).label('count')
    ).filter(Report.created_at >= thirty_days_ago).group_by(func.date(Report.created_at)).all()
    
    # Reports by police station
    reports_by_station = db.session.query(
        Report.police_station,
        func.count(Report.id).label('count')
    ).group_by(Report.police_station).all()
    
    # Reports by status
    reports_by_status = db.session.query(
        Report.status,
        func.count(Report.id).label('count')
    ).group_by(Report.status).all()
    
    return render_template('admin/statistics.html',
                         title='Statistics',
                         reports_by_date=reports_by_date,
                         reports_by_station=reports_by_station,
                         reports_by_status=reports_by_status)


def apply_report_update(report, new_status, assigned_officer=None, remarks=None):
    old_status = report.status
    report.status = new_status
    report.assigned_officer = assigned_officer
    report.admin_remarks = remarks
    report.status_updated_at = datetime.utcnow()

    if old_status == new_status:
        history_remarks = remarks or 'Complaint details updated by admin.'
    else:
        history_remarks = f"Status changed from {old_status} to {new_status}."
        if remarks:
            history_remarks = f"{history_remarks} Remarks: {remarks}"

    update = ReportUpdate(
        report_id=report.id,
        status=new_status,
        remarks=history_remarks
    )

    db.session.add(update)
    db.session.commit()
