from flask import Blueprint, request, jsonify
from flask_login import current_user
from sqlalchemy import func
from datetime import datetime, timedelta
from app import db, limiter
from app.models import Report, Notification
from app.ai.classifier import get_classifier
from app.ai.assistant import get_assistant

bp = Blueprint('api', __name__, url_prefix='/api')


@bp.route('/ai/classify', methods=['POST'])
@limiter.limit("40 per minute")
def classify_complaint():
    """Predict crime category based on complaint narrative."""
    data = request.get_json(silent=True) or {}
    text = data.get('text', '').strip()

    if not text or len(text) < 5:
        return jsonify({
            'success': False,
            'category': 'Other',
            'confidence': 0.0,
            'is_ml': False,
            'alternatives': [],
            'explanation': 'Please enter a few words describing the incident.'
        })

    classifier = get_classifier()
    result = classifier.predict(text)

    return jsonify({
        'success': True,
        'category': result['category'],
        'confidence': result['confidence'],
        'is_ml': result['is_ml'],
        'alternatives': result['alternatives'],
        'explanation': result['explanation']
    })


@bp.route('/ai/help', methods=['POST'])
@limiter.limit("40 per minute")
def citizen_help():
    """Bilingual citizen assistance endpoint (English & Tamil)."""
    data = request.get_json(silent=True) or {}
    query = data.get('query', '').strip()
    lang = data.get('lang', 'en').strip().lower()
    if lang not in ('en', 'ta'):
        lang = 'en'

    assistant = get_assistant()
    answer_data = assistant.answer_query(query, lang=lang)

    return jsonify({
        'success': True,
        **answer_data
    })


@bp.route('/ai/suggested-questions', methods=['GET'])
def suggested_questions():
    """Return categorized suggested assistance questions."""
    lang = request.args.get('lang', 'en').strip().lower()
    if lang not in ('en', 'ta'):
        lang = 'en'
    assistant = get_assistant()
    return jsonify({
        'success': True,
        'lang': lang,
        'questions': assistant.get_suggested_questions(lang)
    })


@bp.route('/notifications/unread-count')
def unread_notifications_count():
    """Check unread notifications count for live badge."""
    if not current_user.is_authenticated:
        return jsonify({'unread_count': 0})
    count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({'unread_count': count})


@bp.route('/analytics/summary')
def analytics_summary():
    """Return live JSON data for Chart.js rendering."""
    # Status Counts
    status_counts = dict(
        db.session.query(Report.status, func.count(Report.id))
        .filter(Report.is_draft == False)
        .group_by(Report.status)
        .all()
    )

    # Top Categories
    category_counts = dict(
        db.session.query(Report.crime_category, func.count(Report.id))
        .filter(Report.is_draft == False)
        .group_by(Report.crime_category)
        .order_by(func.count(Report.id).desc())
        .limit(8)
        .all()
    )

    # Monthly Trends (last 6 months)
    six_months_ago = datetime.utcnow() - timedelta(days=180)
    monthly_rows = (
        db.session.query(
            func.strftime('%Y-%m', Report.created_at).label('month'),
            func.count(Report.id).label('count')
        )
        .filter(Report.created_at >= six_months_ago, Report.is_draft == False)
        .group_by('month')
        .order_by('month')
        .all()
    )
    monthly_trends = {m[0]: m[1] for m in monthly_rows}

    return jsonify({
        'success': True,
        'status_counts': status_counts,
        'category_counts': category_counts,
        'monthly_trends': monthly_trends
    })


@bp.route('/stations/officers', methods=['GET'])
@bp.route('/stations/<path:station_name>/officers', methods=['GET'])
def get_station_officers(station_name=None):
    """Return active police officers directory for the selected station."""
    from app.models import OfficerProfile
    import urllib.parse

    selected_station = station_name or request.args.get('station', '')
    if selected_station:
        selected_station = urllib.parse.unquote(selected_station).strip()

    if not selected_station:
        return jsonify({'success': False, 'station': '', 'count': 0, 'officers': []})

    officers = OfficerProfile.query.filter_by(
        police_station=selected_station,
        is_available=True
    ).order_by(OfficerProfile.designation.asc(), OfficerProfile.name.asc()).all()

    return jsonify({
        'success': True,
        'station': selected_station,
        'count': len(officers),
        'officers': [
            {
                'id': o.id,
                'name': o.name,
                'designation': o.designation,
                'badge_number': o.badge_number,
                'department': o.department,
                'active_case_count': o.active_case_count,
                'has_account': o.has_account
            }
            for o in officers
        ]
    })

