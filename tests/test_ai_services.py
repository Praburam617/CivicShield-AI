from app.ai.classifier import get_classifier
from app.ai.assistant import get_assistant

def test_ai_classifier_predictions():
    """Verify scikit-learn classifier pipeline and categories."""
    classifier = get_classifier()

    # Phishing / Online Fraud
    r1 = classifier.predict("Someone sent me a fraudulent bank website link and drained my account via OTP phishing.")
    assert r1['category'] == 'Cyber Crime'
    assert r1['confidence'] > 50.0

    # Physical assault
    r2 = classifier.predict("A man physically attacked me with a stick causing severe bleeding and facial injuries.")
    assert r2['category'] == 'Assault'

    # Empty text handling
    r3 = classifier.predict("")
    assert r3['category'] == 'Other'
    assert r3['confidence'] == 0.0


def test_bilingual_assistant_en_and_ta():
    """Verify citizen assistance knowledge engine for English and Tamil."""
    assistant = get_assistant()

    # English query
    ans_en = assistant.answer_query("How do I file a complaint?", lang="en")
    assert ans_en['matched'] is True
    assert 'File New Complaint' in ans_en['answer']

    # Tamil query
    ans_ta = assistant.answer_query("புகார் அளிப்பது எப்படி?", lang="ta")
    assert ans_ta['matched'] is True
    assert 'File New Complaint' in ans_ta['answer']


def test_api_ai_endpoints(client):
    """Test REST API endpoints for classification and assistance."""
    # Test /api/ai/classify
    resp_clf = client.post('/api/ai/classify', json={
        'text': 'A speeding car hit an auto rickshaw on the highway and fled the scene.'
    })
    assert resp_clf.status_code == 200
    data_clf = resp_clf.get_json()
    assert data_clf['success'] is True
    assert data_clf['category'] == 'Traffic Violation'

    # Test /api/ai/help
    resp_help = client.post('/api/ai/help', json={
        'query': 'What evidence can I upload?',
        'lang': 'en'
    })
    assert resp_help.status_code == 200
    data_help = resp_help.get_json()
    assert data_help['success'] is True
    assert '16 MB' in data_help['answer']
