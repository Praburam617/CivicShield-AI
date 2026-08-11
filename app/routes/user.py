from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Report, ReportUpdate
from app.forms import ReportForm
from flask import Blueprint
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import random
import string

bp = Blueprint('user', __name__)

def generate_complaint_number():
    """Generate unique complaint number"""
    prefix = 'FIR'
    year = datetime.now().strftime('%Y')
    random_digits = ''.join(random.choices(string.digits, k=6))
    complaint_number = f"{prefix}/{year}/{random_digits}"
    
    # Ensure uniqueness
    while Report.query.filter_by(complaint_number=complaint_number).first():
        random_digits = ''.join(random.choices(string.digits, k=6))
        complaint_number = f"{prefix}/{year}/{random_digits}"
    
    return complaint_number

def save_evidence_file(file):
    """Save uploaded evidence file"""
    if file and file.filename:
        filename = secure_filename(file.filename)
        # Add timestamp to filename to avoid conflicts
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return filename
    return None

@bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin:
        return redirect(url_for('admin.dashboard'))
    
    # Get recent reports
    recent_reports = Report.query.filter_by(user_id=current_user.id).order_by(Report.created_at.desc()).limit(5).all()
    total_reports = Report.query.filter_by(user_id=current_user.id).count()
    
    # Count by status
    pending_count = Report.query.filter_by(user_id=current_user.id, status='Pending').count()
    investigating_count = Report.query.filter_by(user_id=current_user.id, status='Under Investigation').count()
    resolved_count = Report.query.filter_by(user_id=current_user.id, status='Resolved').count()
    
    return render_template('dashboard/user_dashboard.html', 
                         title='Dashboard',
                         recent_reports=recent_reports,
                         total_reports=total_reports,
                         pending_count=pending_count,
                         investigating_count=investigating_count,
                         resolved_count=resolved_count)

@bp.route('/submit-report', methods=['GET', 'POST'])
@login_required
def submit_report():
    if current_user.is_admin:
        return redirect(url_for('admin.dashboard'))
    
    form = ReportForm()
    if form.validate_on_submit():
        # Save evidence file if uploaded
        evidence_file = save_evidence_file(form.evidence_file.data)
        
        # Create new report
        report = Report(
            complaint_number=generate_complaint_number(),
            user_id=current_user.id,
            title=form.title.data,
            description=form.description.data,
            crime_category=form.crime_category.data,
            incident_date=form.incident_date.data,
            incident_location=form.incident_location.data,
            police_station=form.police_station.data,
            evidence_file=evidence_file,
            status='Pending'
        )
        
        db.session.add(report)
        db.session.commit()
        
        # Create initial update
        update = ReportUpdate(
            report_id=report.id,
            status='Pending',
            remarks='Complaint submitted successfully'
        )
        db.session.add(update)
        db.session.commit()
        
        flash(f'Complaint submitted successfully! Your complaint number is {report.complaint_number}', 'success')
        return redirect(url_for('user.my_reports'))
    
    return render_template('reports/submit_report.html', title='Submit Complaint', form=form)

@bp.route('/my-reports')
@login_required
def my_reports():
    if current_user.is_admin:
        return redirect(url_for('admin.dashboard'))
    
    page = request.args.get('page', 1, type=int)
    reports = Report.query.filter_by(user_id=current_user.id).order_by(Report.created_at.desc()).paginate(page=page, per_page=10)
    
    return render_template('reports/my_reports.html', title='My Complaints', reports=reports)

@bp.route('/report/<int:report_id>')
@login_required
def report_detail(report_id):
    report = Report.query.get_or_404(report_id)
    
    # Check if user owns this report or is admin
    if report.user_id != current_user.id and not current_user.is_admin:
        flash('You do not have permission to view this complaint.', 'danger')
        return redirect(url_for('user.dashboard'))
    
    return render_template('reports/report_detail.html', title='Complaint Details', report=report)

@bp.route('/track-report', methods=['GET', 'POST'])
@login_required
def track_report():
    if current_user.is_admin:
        return redirect(url_for('admin.dashboard'))
    
    complaint_number = None
    report = None
    
    if request.method == 'POST':
        complaint_number = request.form.get('complaint_number')
        report = Report.query.filter_by(complaint_number=complaint_number, user_id=current_user.id).first()
        
        if not report:
            flash('No complaint found with this number!', 'danger')
    
    return render_template('reports/track_report.html', title='Track Complaint', report=report, complaint_number=complaint_number)