import os
import re
import json
import logging
from typing import Dict, Any, List, Optional
import requests
from config import Config

logger = logging.getLogger('civicshield.ai.assistant')

# Structured Bilingual Knowledge Base (English & Tamil)
KNOWLEDGE_BASE: List[Dict[str, Any]] = [
    {
        "id": "how_to_register",
        "keywords": ["register", "sign up", "create account", "join", "registration", "account", "பதிவு", "கணக்கு", "உள்நுழை"],
        "category": "Account & Registration",
        "en": {
            "question": "How do I create an account on CivicShield AI?",
            "answer": "Click 'Register' in the top right menu. Enter your Full Name, Username, Email, and Phone Number, and choose a secure password. Routine registration does NOT require Aadhaar or sensitive identification documents. Once registered, log in to access your dashboard.",
            "steps": [
                "Click 'Register' on the top navigation bar",
                "Fill in your name, unique username, email, and phone",
                "Set a strong password (minimum 6 characters)",
                "Submit and sign in from the Login page"
            ]
        },
        "ta": {
            "question": "CivicShield AI-ல் புதிய கணக்கு எவ்வாறு தொடங்குவது?",
            "answer": "மேல் மெனுவில் உள்ள 'Register' பொத்தானை கிளிக் செய்யவும். உங்கள் முழு பெயர், பயனர் பெயர் (Username), மின்னஞ்சல் மற்றும் தொலைபேசி எண்ணை உள்ளிட்டு கடவுச்சொல்லை அமைக்கவும். கணக்கு தொடங்க ஆதார் அட்டை தேவையில்லை. பதிவு செய்தவுடன் உள்நுழைந்து புகார்களை சமர்ப்பிக்கலாம்.",
            "steps": [
                "மேல் மெனுவில் 'Register' என்பதை கிளிக் செய்யவும்",
                "பெயர், மின்னஞ்சல், தொலைபேசி எண் ஆகியவற்றை உள்ளிடவும்",
                "வலுவான கடவுச்சொல்லை உருவாக்கவும்",
                "சமர்ப்பித்து Login பக்கத்தின் மூலம் உள்நுழையவும்"
            ]
        }
    },
    {
        "id": "how_to_file",
        "keywords": ["file complaint", "submit report", "report incident", "how to report", "new complaint", "புகார்", "புகார் அளிக்க", "புகார் செய்வது", "புகார் அளிப்பது", "சமர்ப்பிக்க"],
        "category": "Filing Complaints",
        "en": {
            "question": "How do I file a crime complaint?",
            "answer": "Log in to your citizen dashboard and click 'File New Complaint'. Follow the guided 4-step wizard: Step 1 (Incident title, description, category with AI suggestion), Step 2 (Location, district, and police station), Step 3 (Upload photos/documents), and Step 4 (Review and submit). You will immediately receive a unique complaint reference number.",
            "steps": [
                "Step 1: Enter incident title, date/time, and description",
                "Step 2: Provide incident district, area, and police station",
                "Step 3: Upload supporting images or PDF documents",
                "Step 4: Review entered details and confirm submission"
            ]
        },
        "ta": {
            "question": "ஒரு குற்றப் புகாரை எவ்வாறு பதிவு செய்வது?",
            "answer": "உங்கள் கணக்கில் உள்நுழைந்து 'File New Complaint' என்பதை கிளிக் செய்யவும். 4 எளிய படிகள் உள்ளன: 1) சம்பவத்தின் விவரங்கள் மற்றும் வகை (AI பரிந்துரையுடன்), 2) மாவட்டம் மற்றும் காவல் நிலையம், 3) ஆதாரங்கள் (புகைப்படம்/PDF), 4) சரிபார்த்து சமர்ப்பித்தல். சமர்ப்பித்தவுடன் தனித்துவமான புகார் குறிப்பு எண் வழங்கப்படும்.",
            "steps": [
                "படி 1: சம்பவத்தின் தலைப்பு, தேதி மற்றும் விவரங்களை உள்ளிடவும்",
                "படி 2: சம்பவம் நடந்த இடம், மாவட்டம் மற்றும் காவல் நிலையத்தை தேர்வு செய்யவும்",
                "படி 3: புகைப்படங்கள் அல்லது PDF ஆதாரங்களை பதிவேற்றவும்",
                "படி 4: அனைத்து விவரங்களையும் சரிபார்த்து சமர்ப்பிக்கவும்"
            ]
        }
    },
    {
        "id": "choose_category",
        "keywords": ["category", "crime type", "which category", "classify", "crime category", "குற்ற வகை", "வகை தேர்வு"],
        "category": "Filing Complaints",
        "en": {
            "question": "How do I choose the correct crime category?",
            "answer": "CivicShield AI analyzes your complaint description in real-time and provides a discreet category suggestion (e.g. online scams -> Cyber Crime, house break-in -> Burglary). You can click 'Apply Suggestion' to accept it or choose any category from the dropdown menu manually.",
            "steps": [
                "Type your complaint description clearly in Step 1",
                "Review the AI-suggested category displayed below the field",
                "Click 'Apply' to accept or select a different category from the dropdown"
            ]
        },
        "ta": {
            "question": "சரியான குற்ற வகையை எவ்வாறு தேர்வு செய்வது?",
            "answer": "உங்கள் புகார் விளக்கத்தை தட்டச்சு செய்யும்போது, CivicShield AI தானாகவே பொருத்தமான வகையை பரிந்துரைக்கும் (எ.கா: இணைய மோசடி -> Cyber Crime, வீடு உடைப்பு -> Burglary). நீங்கள் அந்த பரிந்துரையை ஏற்கலாம் அல்லது கீழ்தோன்றும் மெனுவிலிருந்து வேறு வகையை தேர்வு செய்யலாம்.",
            "steps": [
                "படி 1-ல் உங்கள் புகார் விவரத்தை உள்ளிடவும்",
                "கீழே தோன்றும் AI பரிந்துரையை பார்க்கவும்",
                "'Apply' கொடுத்து ஏற்கலாம் அல்லது பட்டியலிலிருந்து தேர்வு செய்யலாம்"
            ]
        }
    },
    {
        "id": "evidence_guidelines",
        "keywords": ["evidence", "upload", "photos", "pdf", "file size", "attachment", "documents", "ஆதாரம்", "சான்றுகள்", "கோப்பு பதிவேற்றம்"],
        "category": "Evidence",
        "en": {
            "question": "What evidence can I upload and what are the file limits?",
            "answer": "You can upload JPG, PNG, WEBP images or PDF documents up to 16 MB each. You may upload multiple files (e.g. photos of damage, transaction receipts, screenshots, invoices). All uploaded files are stored securely in protected storage and accessible only by you and authorized investigating officers.",
            "steps": [
                "Supported formats: JPG, PNG, WEBP, PDF",
                "Maximum file size: 16 MB per file",
                "Multiple files can be attached and previewed before final submission",
                "Sensitive files are never exposed in public static folders"
            ]
        },
        "ta": {
            "question": "என்ன வகையான ஆதாரங்களை பதிவேற்றலாம்? அளவு வரம்பு என்ன?",
            "answer": "JPG, PNG, WEBP புகைப்படங்கள் மற்றும் PDF ஆவணங்களை பதிவேற்றலாம். ஒரு கோப்பின் அதிகபட்ச அளவு 16 MB. பல கோப்புகளை பதிவேற்றலாம் (எ.கா: சேதத்தின் படங்கள், வங்கி ரசீதுகள், ஸ்கிரீன்ஷாட்கள்). அனைத்து கோப்புகளும் பாதுகாப்பான சேமிப்பகத்தில் வைக்கப்படும்.",
            "steps": [
                "ஏற்கப்படும் வடிவங்கள்: JPG, PNG, WEBP, PDF",
                "அதிகபட்ச அளவு: கோப்புக்கு 16 MB",
                "சமர்ப்பிக்கும் முன் புகைப்பட முன்னோட்டத்தை (Preview) காணலாம்",
                "கோப்புகள் முழு பாதுகாப்போடு பராமரிக்கப்படும்"
            ]
        }
    },
    {
        "id": "track_status",
        "keywords": ["track", "status", "check progress", "complaint number", "reference", "நிலை அறிதல்", "கண்காணிப்பு", "புகார் எண்"],
        "category": "Tracking & Status",
        "en": {
            "question": "How do I track my complaint and what do the statuses mean?",
            "answer": "Go to 'Track Complaint' and enter your complaint reference number (e.g. FIR/2026/... or CS-2026-...). You can view the full progress timeline: Pending (submitted), Verified (initial review complete), Assigned (assigned to an officer), Under Investigation (active investigation), Evidence Collected (witnesses/evidence recorded), Action Required (further details requested from you), and Resolved / Closed.",
            "steps": [
                "Pending: Complaint submitted, awaiting station review",
                "Under Investigation: Investigating officer actively working on the case",
                "Evidence Collected: Key proofs and statements gathered",
                "Action Required: Officer requires more details or documents from you",
                "Resolved: Case inquiry concluded and resolved"
            ]
        },
        "ta": {
            "question": "புகாரின் நிலையை எவ்வாறு கண்காணிப்பது? நிலைகளின் பொருள் என்ன?",
            "answer": "'Track Complaint' பக்கத்திற்கு சென்று உங்கள் புகார் எண்ணை உள்ளிடவும். நிலைகளின் விளக்கம்: Pending (சமர்ப்பிக்கப்பட்டது), Under Investigation (விசாரணையில் உள்ளது), Evidence Collected (ஆதாரங்கள் சேகரிக்கப்பட்டன), Action Required (உங்களிடம் கூடுதல் தகவல் கோரப்பட்டுள்ளது), Resolved (தீர்க்கப்பட்டது).",
            "steps": [
                "Pending: புகார் பெறப்பட்டு பரிசீலனையில் உள்ளது",
                "Under Investigation: அதிகாரி விசாரணையை தொடங்கியுள்ளார்",
                "Action Required: கூடுதல் தகவல் அல்லது ஆவணம் தேவைப்படுகிறது",
                "Resolved: விசாரணை நிறைவடைந்து தீர்வு காணப்பட்டது"
            ]
        }
    },
    {
        "id": "fir_difference",
        "keywords": ["fir", "official fir", "court", "police station", "legal", "சட்டபூர்வ", "முதல் தகவல் அறிக்கை"],
        "category": "Legal & Platform Notice",
        "en": {
            "question": "Is a CivicShield AI complaint reference the same as an official police FIR?",
            "answer": "No. A CivicShield AI reference number is an online complaint tracking docket. An official First Information Report (FIR) is a formal statutory document registered under Section 154 of the Code of Criminal Procedure by a designated police officer at a police station. For emergency situations or grave cognizable crimes requiring immediate police response, please call 112 or visit the nearest police station immediately.",
            "steps": [
                "CivicShield reference: Platform intake and tracking docket",
                "Police FIR: Official statutory registration by police authorities",
                "Emergency hotline: Dial 112 (National Emergency) or 100"
            ]
        },
        "ta": {
            "question": "இணையதள புகார் குறிப்பு எண் காவல் நிலைய FIR-க்கு சமமானதா?",
            "answer": "இல்லை. CivicShield AI குறிப்பு எண் என்பது இணையத்தில் புகாரை கண்காணிக்கும் எண் மட்டுமே. உத்தியோகபூர்வ FIR (முதல் தகவல் அறிக்கை) என்பது காவல் நிலைய அதிகாரியால் பதிவு செய்யப்படும் சட்டபூர்வ ஆவணம் ஆகும். அவசர காலங்களில் உடனடியாக 112 அல்லது 100 என்ற எண்ணை தொடர்பு கொள்ளவும்.",
            "steps": [
                "இணைய குறிப்பு எண்: புகார் பரிசீலனைக்கான ஆவணம்",
                "காவல் நிலைய FIR: சட்டபூர்வ பதிவு",
                "அவசர உதவிக்கு: 112 அல்லது 100-ஐ அழைக்கவும்"
            ]
        }
    },
    {
        "id": "student_demo_notice",
        "keywords": ["demo", "real", "actual police", "disclaimer", "student project", "விளக்கம்", "மாதிரி"],
        "category": "Platform Information",
        "en": {
            "question": "Is this an official police department website?",
            "answer": "No. CivicShield AI is a comprehensive portfolio and demonstration web application developed to showcase full-stack Python web development, modern database architecture, role-based workflows, and practical AI integration. It is not affiliated with any official law enforcement agency. Do not submit sensitive national security information.",
            "steps": [
                "Platform purpose: Technology demonstration & portfolio",
                "Real emergencies: Contact local authorities or call 112"
            ]
        },
        "ta": {
            "question": "இது அதிகாரப்பூர்வ காவல் துறை இணையதளமா?",
            "answer": "இல்லை. CivicShield AI என்பது முழுமையான தொழில்நுட்ப மாதிரி (Demonstration Project) ஆகும். இது அதிகாரப்பூர்வ காவல் துறையுடன் இணைக்கப்படவில்லை. அவசர குற்றங்களுக்கு உங்கள் பகுதி காவல் நிலையத்தையோ அல்லது 112 என்ற அவசர எண்ணையோ தொடர்பு கொள்ளவும்.",
            "steps": [
                "நோக்கம்: தொழில்நுட்ப செயல்விளக்கம்",
                "அவசர உதவிக்கு: பகுதி காவல் நிலையம் அல்லது 112"
            ]
        }
    }
]


class BilingualAssistant:
    def __init__(self, ollama_url: Optional[str] = None):
        self.ollama_url = ollama_url or Config.OLLAMA_API_URL
        self.kb = KNOWLEDGE_BASE

    def get_suggested_questions(self, lang: str = "en") -> List[Dict[str, str]]:
        """Return list of common suggested questions in requested language."""
        lang_key = "ta" if lang == "ta" else "en"
        return [
            {
                "id": item["id"],
                "category": item["category"],
                "question": item[lang_key]["question"]
            }
            for item in self.kb
        ]

    def answer_query(self, query: str, lang: str = "en") -> Dict[str, Any]:
        """Find the most relevant answer via structured intent matching, or local Ollama if configured."""
        if not query or not query.strip():
            return self._default_response(lang)

        lang_key = "ta" if lang == "ta" else "en"
        clean_query = query.strip().lower()

        # Step 1: Structured Knowledge Base Keyword & Token Matching
        best_match = None
        highest_score = 0

        for item in self.kb:
            score = 0
            # Keyword matches - longer multi-word phrases give higher weight
            for kw in item["keywords"]:
                kw_clean = kw.lower()
                if kw_clean in clean_query:
                    score += 5 if " " in kw_clean else 2
                elif clean_query in kw_clean and len(clean_query) >= 3:
                    score += 3
            # Target question exact/substring overlap
            target_q = item[lang_key]["question"].lower()
            if clean_query in target_q:
                score += 8
            for word in clean_query.split():
                if len(word) >= 3 and word in target_q:
                    score += 1

            if score > highest_score:
                highest_score = score
                best_match = item

        # If confident match found in structured knowledge base
        if best_match and highest_score >= 2:
            content = best_match[lang_key]
            return {
                "matched": True,
                "intent_id": best_match["id"],
                "category": best_match["category"],
                "question": content["question"],
                "answer": content["answer"],
                "steps": content.get("steps", []),
                "source": "knowledge_base",
                "lang": lang_key
            }

        # Step 2: Optional local Ollama inference if configured & available
        ollama_response = self._try_ollama_query(query, lang_key)
        if ollama_response:
            return ollama_response

        # Step 3: Safe fallback with helpful suggested topics
        return self._fallback_response(query, lang_key)

    def _try_ollama_query(self, query: str, lang_key: str) -> Optional[Dict[str, Any]]:
        """Attempt safe local Ollama query with strict safety prompt and low timeout."""
        try:
            system_prompt = (
                "You are CivicShield AI Assistant, an informative guide for a citizen crime reporting portal. "
                "Provide a brief, factual, helpful answer (under 80 words). "
                "Never invent legal advice, court orders, or fake police actions. "
                "Clearly remind that emergencies require calling 112."
            )
            if lang_key == "ta":
                system_prompt += " Answer strictly in clear, polite Tamil."
            else:
                system_prompt += " Answer strictly in clear English."

            payload = {
                "model": Config.OLLAMA_MODEL,
                "prompt": f"{system_prompt}\nUser Question: {query}\nAnswer:",
                "stream": False,
                "options": {"temperature": 0.2, "num_predict": 120}
            }

            resp = requests.post(self.ollama_url, json=payload, timeout=2.0)
            if resp.status_code == 200:
                data = resp.json()
                answer = data.get("response", "").strip()
                if answer:
                    return {
                        "matched": True,
                        "intent_id": "ollama_inference",
                        "category": "AI Guidance",
                        "question": query,
                        "answer": answer,
                        "steps": [],
                        "source": "ollama_local",
                        "lang": lang_key
                    }
        except Exception:
            pass  # Seamless fallback to structured assistance without failing or stalling

        return None

    def _default_response(self, lang_key: str) -> Dict[str, Any]:
        if lang_key == "ta":
            return {
                "matched": False,
                "intent_id": "default",
                "category": "உதவி",
                "question": "எப்படி உதவலாம்?",
                "answer": "CivicShield AI உதவி மையத்திற்கு வரவேற்கிறோம். கணக்கு தொடங்குதல், புகார் அளித்தல், அல்லது புகார் நிலை அறிதல் பற்றி கீழே உள்ள வினாக்களை தேர்ந்தெடுக்கவும்.",
                "steps": [],
                "source": "knowledge_base",
                "lang": "ta"
            }
        return {
            "matched": False,
            "intent_id": "default",
            "category": "Help Desk",
            "question": "How can we help?",
            "answer": "Welcome to CivicShield AI Assistance. Choose a topic below or type your question about filing complaints, uploading evidence, or tracking status.",
            "steps": [],
            "source": "knowledge_base",
            "lang": "en"
        }

    def _fallback_response(self, query: str, lang_key: str) -> Dict[str, Any]:
        if lang_key == "ta":
            return {
                "matched": False,
                "intent_id": "fallback",
                "category": "பொது உதவி",
                "question": query,
                "answer": "மன்னிக்கவும், உங்கள் கேள்விக்கான நேரடி பதில் கிடைக்கவில்லை. புகார் அளிப்பது, ஆதாரங்கள் பதிவேற்றுவது, அல்லது நிலை அறிதல் ஆகிய தலைப்புகளில் கீழே கொடுக்கப்பட்டுள்ள வினாக்களை பார்க்கவும். அவசர உதவிக்கு 112 என்ற எண்ணை அழைக்கவும்.",
                "steps": [
                    "புகார் அளிக்க: கணக்கில் உள்நுழைந்து 'File New Complaint' செல்லவும்",
                    "நிலை அறிய: 'Track Complaint' பக்கத்தில் குறிப்பு எண்ணை உள்ளிடவும்",
                    "அவசர உதவி: உடனடியாக 112 அல்லது 100-ஐ அழைக்கவும்"
                ],
                "source": "knowledge_base",
                "lang": "ta"
            }
        return {
            "matched": False,
            "intent_id": "fallback",
            "category": "General Assistance",
            "question": query,
            "answer": "We couldn't find a direct match for your specific query. Please review our common topics below regarding registration, filing a complaint, evidence guidelines, and tracking your complaint progress. For emergencies, please dial 112 immediately.",
            "steps": [
                "To file a report: Log in and click 'File New Complaint'",
                "To track progress: Visit 'Track Complaint' and enter your reference number",
                "For emergencies: Contact local police or dial 112 immediately"
            ],
            "source": "knowledge_base",
            "lang": "en"
        }


# Global singleton instance
_assistant_instance: Optional[BilingualAssistant] = None

def get_assistant() -> BilingualAssistant:
    global _assistant_instance
    if _assistant_instance is None:
        _assistant_instance = BilingualAssistant()
    return _assistant_instance
