import io
import csv
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import or_, desc, asc
from app import db
from app.models import Report, User, PoliceStation, CrimeCategory
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def sanitize_csv_cell(value: Any) -> str:
    """Protect against CSV formula injection (DDE/Excel/Calc injection)."""
    if value is None:
        return ""
    str_val = str(value)
    if str_val and str_val[0] in ('=', '+', '-', '@', '\t', '\r'):
        return f"'{str_val}"
    return str_val


def build_filtered_query(filters: Dict[str, Any], base_query=None):
    """Construct filtered SQLAlchemy query based on search & filter parameters."""
    query = base_query if base_query is not None else Report.query

    # Search keyword
    search = filters.get('search', '').strip()
    if search:
        like_term = f"%{search}%"
        query = query.outerjoin(User, Report.user_id == User.id).filter(
            or_(
                Report.complaint_number.ilike(like_term),
                Report.title.ilike(like_term),
                Report.description.ilike(like_term),
                Report.incident_location.ilike(like_term),
                Report.police_station.ilike(like_term),
                Report.crime_category.ilike(like_term),
                User.username.ilike(like_term),
                User.full_name.ilike(like_term),
                User.email.ilike(like_term)
            )
        )

    # Specific filters
    status = filters.get('status', '').strip()
    if status and status != 'All':
        query = query.filter(Report.status == status)

    category = filters.get('category', '').strip()
    if category and category != 'All':
        query = query.filter(Report.crime_category == category)

    district = filters.get('district', '').strip()
    if district and district != 'All':
        query = query.filter(Report.district == district)

    station = filters.get('station', '').strip()
    if station and station != 'All':
        query = query.filter(Report.police_station == station)

    officer = filters.get('officer', '').strip()
    if officer and officer != 'All':
        query = query.filter(
            or_(
                Report.assigned_officer.ilike(f"%{officer}%"),
                Report.assigned_officer_id == int(officer) if officer.isdigit() else False
            )
        )

    # Date range filters
    date_from = filters.get('date_from', '').strip()
    if date_from:
        try:
            dt_from = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Report.created_at >= dt_from)
        except ValueError:
            pass

    date_to = filters.get('date_to', '').strip()
    if date_to:
        try:
            dt_to = datetime.strptime(f"{date_to} 23:59:59", '%Y-%m-%d %H:%M:%S')
            query = query.filter(Report.created_at <= dt_to)
        except ValueError:
            pass

    # Exclude drafts from general administrative & search reports
    query = query.filter(Report.is_draft == False)

    # Sorting
    sort_by = filters.get('sort_by', 'created_at_desc')
    if sort_by == 'created_at_asc':
        query = query.order_by(Report.created_at.asc())
    elif sort_by == 'incident_date_desc':
        query = query.order_by(Report.incident_date.desc())
    elif sort_by == 'status':
        query = query.order_by(Report.status.asc())
    else:
        query = query.order_by(Report.created_at.desc())

    return query


def generate_complaints_csv(reports: List[Report]) -> str:
    """Generate formula-safe CSV string from a list of complaint reports."""
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # Header row
    headers = [
        "Complaint Reference",
        "Title",
        "Crime Category",
        "Incident Date",
        "District",
        "Police Station",
        "Status",
        "Assigned Officer",
        "Complainant Username",
        "Complainant Name",
        "Submission Date",
        "Last Updated"
    ]
    writer.writerow(headers)

    for r in reports:
        complainant_username = r.complainant.username if r.complainant else "N/A"
        complainant_name = r.complainant.full_name if r.complainant else "N/A"
        officer = r.assigned_officer or (r.officer_user.full_name if r.officer_user else "Unassigned")
        
        row = [
            sanitize_csv_cell(r.complaint_number),
            sanitize_csv_cell(r.title),
            sanitize_csv_cell(r.crime_category),
            sanitize_csv_cell(r.incident_date.strftime('%Y-%m-%d %H:%M') if r.incident_date else ""),
            sanitize_csv_cell(r.district),
            sanitize_csv_cell(r.police_station),
            sanitize_csv_cell(r.status),
            sanitize_csv_cell(officer),
            sanitize_csv_cell(complainant_username),
            sanitize_csv_cell(complainant_name),
            sanitize_csv_cell(r.created_at.strftime('%Y-%m-%d %H:%M:%S') if r.created_at else ""),
            sanitize_csv_cell(r.status_updated_at.strftime('%Y-%m-%d %H:%M:%S') if r.status_updated_at else "")
        ]
        writer.writerow(row)

    return output.getvalue()


def generate_complaints_pdf(reports: List[Report], filter_summary: str = "All Complaints") -> io.BytesIO:
    """Generate professional PDF summary report using reportlab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#1E293B')
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#64748B')
    )
    cell_style = ParagraphStyle(
        'CellText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10
    )
    header_cell_style = ParagraphStyle(
        'HeaderCell',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white
    )

    elements = []

    # Title & Branding
    elements.append(Paragraph("CivicShield AI", title_style))
    elements.append(Paragraph("Smart Crime Reporting & Complaint Management System — Audit & Analytics Report", subtitle_style))
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#2563EB'), spaceAfter=12))

    # Meta Summary Box
    now_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
    summary_text = f"<b>Generated On:</b> {now_str} &nbsp;|&nbsp; <b>Filter Scope:</b> {filter_summary} &nbsp;|&nbsp; <b>Total Records:</b> {len(reports)}"
    elements.append(Paragraph(summary_text, subtitle_style))
    elements.append(Spacer(1, 14))

    # Table Data
    table_data = [[
        Paragraph("Complaint #", header_cell_style),
        Paragraph("Category", header_cell_style),
        Paragraph("Title", header_cell_style),
        Paragraph("District / Station", header_cell_style),
        Paragraph("Status", header_cell_style),
        Paragraph("Date", header_cell_style),
        Paragraph("Officer", header_cell_style)
    ]]

    for r in reports[:150]:  # Cap for PDF page sanity
        officer = r.assigned_officer or (r.officer_user.full_name if r.officer_user else "Unassigned")
        date_str = r.created_at.strftime('%Y-%m-%d') if r.created_at else ""
        table_data.append([
            Paragraph(r.complaint_number, cell_style),
            Paragraph(r.crime_category, cell_style),
            Paragraph(r.title[:35] + ("..." if len(r.title) > 35 else ""), cell_style),
            Paragraph(f"{r.district}<br/>{r.police_station}", cell_style),
            Paragraph(r.status, cell_style),
            Paragraph(date_str, cell_style),
            Paragraph(officer[:20], cell_style)
        ])

    table = Table(table_data, colWidths=[85, 75, 125, 110, 65, 55, 65])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563EB')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')])
    ]))

    elements.append(table)
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("<i>Confidential — For Authorized Public Service and Law Enforcement Review Only. CivicShield AI Demonstration System.</i>", subtitle_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer


def generate_single_complaint_docket_pdf(report: Report) -> io.BytesIO:
    """Generate an official complaint docket dossier PDF for a single report."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocketTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#1E293B')
    )
    header_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#2563EB')
    )
    body_style = ParagraphStyle(
        'DocketBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#334155')
    )
    bold_style = ParagraphStyle(
        'DocketBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#1E293B')
    )
    subtitle_style = ParagraphStyle(
        'DocketSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#64748B')
    )

    elements = []

    # Title & Header
    elements.append(Paragraph("CivicShield AI — Complaint Case Docket", title_style))
    elements.append(Paragraph(f"Reference Number: <b>{report.complaint_number}</b> &nbsp;|&nbsp; Status: <b>{report.status}</b>", body_style))
    elements.append(Spacer(1, 8))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563EB'), spaceAfter=14))

    # Basic Info Table
    info_data = [
        [Paragraph("Complaint Title:", bold_style), Paragraph(report.title, body_style)],
        [Paragraph("Crime Category:", bold_style), Paragraph(report.crime_category, body_style)],
        [Paragraph("Date of Incident:", bold_style), Paragraph(report.incident_date.strftime('%Y-%m-%d %H:%M') if report.incident_date else "N/A", body_style)],
        [Paragraph("Submission Date:", bold_style), Paragraph(report.created_at.strftime('%Y-%m-%d %H:%M UTC'), body_style)],
        [Paragraph("District:", bold_style), Paragraph(report.district, body_style)],
        [Paragraph("Incident Location:", bold_style), Paragraph(report.incident_location, body_style)],
        [Paragraph("Assigned Station:", bold_style), Paragraph(report.police_station, body_style)],
        [Paragraph("Assigned Officer:", bold_style), Paragraph(report.assigned_officer or (report.officer_user.full_name if report.officer_user else "Pending Assignment"), body_style)],
        [Paragraph("Complainant:", bold_style), Paragraph(f"{report.complainant.full_name} ({report.complainant.email})", body_style)]
    ]

    t_info = Table(info_data, colWidths=[130, 400])
    t_info.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F8FAFC'))
    ]))
    elements.append(t_info)
    elements.append(Spacer(1, 14))

    # Description
    elements.append(Paragraph("Incident Description", header_style))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(report.description, body_style))
    elements.append(Spacer(1, 14))

    # Evidence summary
    elements.append(Paragraph("Submitted Supporting Evidence", header_style))
    elements.append(Spacer(1, 4))
    if report.evidence_items:
        ev_items = []
        for ev in report.evidence_items:
            size_kb = round(ev.file_size / 1024, 1) if ev.file_size else 0
            ev_items.append([
                Paragraph(ev.original_filename, body_style),
                Paragraph(ev.file_type, body_style),
                Paragraph(f"{size_kb} KB", body_style),
                Paragraph(ev.uploaded_at.strftime('%Y-%m-%d %H:%M'), body_style)
            ])
        t_ev = Table([[Paragraph("Filename", bold_style), Paragraph("Type", bold_style), Paragraph("Size", bold_style), Paragraph("Uploaded", bold_style)]] + ev_items, colWidths=[200, 110, 80, 140])
        t_ev.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9'))
        ]))
        elements.append(t_ev)
    else:
        elements.append(Paragraph("No supporting evidence documents attached.", body_style))
    elements.append(Spacer(1, 14))

    # Investigation History Timeline
    elements.append(Paragraph("Investigation & Case Timeline", header_style))
    elements.append(Spacer(1, 4))
    if report.updates:
        update_rows = [[
            Paragraph("Timestamp", bold_style),
            Paragraph("Status", bold_style),
            Paragraph("Remarks", bold_style)
        ]]
        for upd in report.updates:
            # Skip internal notes in public docket
            if not upd.is_internal:
                update_rows.append([
                    Paragraph(upd.created_at.strftime('%Y-%m-%d %H:%M'), body_style),
                    Paragraph(upd.status, body_style),
                    Paragraph(upd.remarks or "Status updated", body_style)
                ])
        t_upd = Table(update_rows, colWidths=[120, 110, 300])
        t_upd.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9'))
        ]))
        elements.append(t_upd)
    else:
        elements.append(Paragraph("No timeline updates recorded.", body_style))

    elements.append(Spacer(1, 25))
    elements.append(Paragraph("<i>This electronic case docket was generated by CivicShield AI. Official police FIR registration is subject to verification under applicable statutory law.</i>", subtitle_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer
