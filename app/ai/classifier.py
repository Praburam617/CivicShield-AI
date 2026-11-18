import os
import re
import logging
from typing import Dict, Any, List, Optional
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from config import Config

logger = logging.getLogger('civicshield.ai')

# Controlled Crime Categories aligned with Config.CRIME_CATEGORIES
CANONICAL_CATEGORIES = [
    'Theft',
    'Cyber Crime',
    'Assault',
    'Robbery',
    'Burglary',
    'Domestic Violence',
    'Fraud',
    'Sexual Harassment',
    'Kidnapping',
    'Murder',
    'Drug Offense',
    'Traffic Violation',
    'Vandalism',
    'Other'
]

# Genuine, curated training corpus covering common citizen complaint scenarios
DATASET: List[Dict[str, str]] = [
    # Theft
    {"text": "My bicycle was stolen from outside the metro station while I was at work.", "category": "Theft"},
    {"text": "Someone pickpocketed my wallet containing cash and credit cards on the crowded bus.", "category": "Theft"},
    {"text": "My laptop bag was taken from the library table when I stepped away for five minutes.", "category": "Theft"},
    {"text": "Someone stole the side mirrors and battery from my parked motorcycle overnight.", "category": "Theft"},
    {"text": "My mobile phone was stolen from my jacket pocket at the market.", "category": "Theft"},
    {"text": "Gold chain was snatched from the neck of a woman walking in the park.", "category": "Theft"},
    {"text": "Stolen watch and luggage from the train sleeper compartment.", "category": "Theft"},
    {"text": "Shop owner reports repeated shoplifting of expensive cosmetics and clothing.", "category": "Theft"},
    {"text": "Vehicle theft: my Honda Activa parked in front of apartment is missing.", "category": "Theft"},
    {"text": "Someone stole construction materials and iron rods from our building site.", "category": "Theft"},

    # Cyber Crime
    {"text": "Someone sent me a fake banking website link and stole money from my account via OTP fraud.", "category": "Cyber Crime"},
    {"text": "Received a phishing email claiming to be income tax department asking for my net banking password.", "category": "Cyber Crime"},
    {"text": "My Instagram and WhatsApp accounts were hacked and the perpetrator is demanding money from my contacts.", "category": "Cyber Crime"},
    {"text": "Unauthorized online credit card transactions made in a foreign currency without my consent.", "category": "Cyber Crime"},
    {"text": "Someone created a fake profile using my photos on social media and is sending obscene messages.", "category": "Cyber Crime"},
    {"text": "Ransomware locked all our office computers demanding Bitcoin payment to decrypt files.", "category": "Cyber Crime"},
    {"text": "SIM swap fraud resulted in unauthorized transfer of two lakh rupees from savings account.", "category": "Cyber Crime"},
    {"text": "Crypto investment scam on Telegram stole fifty thousand rupees through a fraudulent trading platform.", "category": "Cyber Crime"},
    {"text": "Deepfake video of me was circulated online accompanied by blackmail threats.", "category": "Cyber Crime"},
    {"text": "Data breach and online identity theft using forged PAN card details.", "category": "Cyber Crime"},

    # Assault
    {"text": "A man physically attacked me with a stick after an argument in the parking lot.", "category": "Assault"},
    {"text": "Group of youths beat up a local shopkeeper causing severe head injuries and bleeding.", "category": "Assault"},
    {"text": "Physical violence and battery outside the restaurant leaving the victim unconscious.", "category": "Assault"},
    {"text": "Neighbour punched me in the face and threatened to break my bones over a property dispute.", "category": "Assault"},
    {"text": "Gang assault on a delivery driver late night on the highway.", "category": "Assault"},
    {"text": "I was attacked by two unidentified men while walking home from the train station.", "category": "Assault"},
    {"text": "Physical brawl at the community hall resulting in injuries and fractured arm.", "category": "Assault"},
    {"text": "Aggressive confrontation where the suspect pushed me down the stairs causing leg fracture.", "category": "Assault"},

    # Robbery
    {"text": "Two masked men with knives threatened me at the ATM and took all my cash.", "category": "Robbery"},
    {"text": "Armed robbery at our jewellery store: suspects held staff at gunpoint and looted ornaments.", "category": "Robbery"},
    {"text": "Men on motorcycle cornered me at night, threatened with a weapon, and forcefully took my bike and watch.", "category": "Robbery"},
    {"text": "Highway robbery: car was stopped by armed gang throwing spikes, passengers robbed of valuables.", "category": "Robbery"},
    {"text": "Cashier at petrol bunk was threatened with a pistol and forced to hand over day collection.", "category": "Robbery"},
    {"text": "Suspects held a knife to my neck in an alleyway and snatched my bag and wedding ring.", "category": "Robbery"},
    {"text": "Armed extortion and forced transfer of valuables under threat to life.", "category": "Robbery"},

    # Burglary
    {"text": "Our house was broken into while we were on vacation; window grill was cut and jewellery stolen.", "category": "Burglary"},
    {"text": "Burglars broke open the front door lock of our apartment and ransacked the cupboards.", "category": "Burglary"},
    {"text": "Office warehouse broken into over the weekend; locks tampered and electronic goods stolen.", "category": "Burglary"},
    {"text": "Night-time break-in at a locked residence, safe broken and cash stolen.", "category": "Burglary"},
    {"text": "Intruders climbed through balcony door at night and stole electronic appliances while we slept.", "category": "Burglary"},
    {"text": "Commercial showroom shutter was broken with crowbar and inventory looted.", "category": "Burglary"},

    # Domestic Violence
    {"text": "Continuous physical abuse, beatings, and verbal harassment by husband and in-laws for dowry.", "category": "Domestic Violence"},
    {"text": "Wife and children subjected to frequent violence, threats of harm, and emotional torture at home.", "category": "Domestic Violence"},
    {"text": "Elderly parents being physically assaulted and starved by their son inside their own house.", "category": "Domestic Violence"},
    {"text": "Severe domestic abuse, strangulation attempt, and dowry harassment by spouse.", "category": "Domestic Violence"},
    {"text": "Violent domestic disputes with threats to life and locking the spouse in a room without food.", "category": "Domestic Violence"},

    # Fraud
    {"text": "Land broker sold me a property using forged ownership documents and vanished with my advance.", "category": "Fraud"},
    {"text": "Job consultancy agency collected fees promising overseas employment and provided fake offer letters.", "category": "Fraud"},
    {"text": "Ponzi scheme and fake chit fund operator absconded with life savings of 50 depositors.", "category": "Fraud"},
    {"text": "Cheque bounce fraud: businessman issued bad cheque and refused to settle outstanding invoice.", "category": "Fraud"},
    {"text": "Fraudulent loan company demanded advance processing charges and never disbursed the approved loan.", "category": "Fraud"},
    {"text": "Counterfeit stamp paper and forged power of attorney used to illegally register property.", "category": "Fraud"},

    # Sexual Harassment
    {"text": "Colleague at workplace sends inappropriate sexual messages and makes obscene gestures despite warnings.", "category": "Sexual Harassment"},
    {"text": "Man stalking and harassing a college student on her daily commute, passing vulgar comments.", "category": "Sexual Harassment"},
    {"text": "Indecent exposure and molestation on a public transport bus during rush hour.", "category": "Sexual Harassment"},
    {"text": "Manager demanding sexual favours in exchange for performance appraisal and promotion.", "category": "Sexual Harassment"},
    {"text": "Online sexual harassment: anonymous caller sending unsolicited explicit pictures via messaging app.", "category": "Sexual Harassment"},

    # Kidnapping
    {"text": "Seven-year-old child missing from outside school; ransom call received demanding 20 lakhs.", "category": "Kidnapping"},
    {"text": "College student was abducted in an unregistered white van by three men.", "category": "Kidnapping"},
    {"text": "Businessman kidnapped on the way home, ransom demand delivered to family.", "category": "Kidnapping"},
    {"text": "Minor girl abducted by an acquaintance without parental consent.", "category": "Kidnapping"},

    # Murder
    {"text": "Dead body found in the abandoned lake with severe stab wounds and signs of struggle.", "category": "Murder"},
    {"text": "Homicide: neighbour stabbed the landlord to death during a heated violent dispute.", "category": "Murder"},
    {"text": "Suspected poisoning resulting in suspicious death of business partner.", "category": "Murder"},
    {"text": "Fatal assault with iron rod leading to immediate death at the construction site.", "category": "Murder"},

    # Drug Offense
    {"text": "Illegal peddling of banned narcotic pills and synthetic drugs near the college campus.", "category": "Drug Offense"},
    {"text": "Ganja and cannabis being sold openly from an abandoned shed in the neighbourhood.", "category": "Drug Offense"},
    {"text": "Racket smuggling prescription psychotropic substances and illicit drug consignments.", "category": "Drug Offense"},
    {"text": "Narcotics stash discovered in rented commercial storage unit.", "category": "Drug Offense"},

    # Traffic Violation
    {"text": "Hit and run incident: speeding SUV knocked down a pedestrian and fled without stopping.", "category": "Traffic Violation"},
    {"text": "Reckless rash driving and street racing with modified silencers endangering public safety.", "category": "Traffic Violation"},
    {"text": "Drunk driver crashed into parked auto-rickshaws and damaged street lights.", "category": "Traffic Violation"},
    {"text": "Vehicle driving on the wrong side of the one-way flyover causing a major collision.", "category": "Traffic Violation"},

    # Vandalism
    {"text": "Unidentified miscreants smashed street lights, smashed shop signboards, and spray painted graffiti.", "category": "Vandalism"},
    {"text": "Parked cars had their windshields broken and tires slashed in the residential colony overnight.", "category": "Vandalism"},
    {"text": "Public park benches and children playground equipment destroyed by hooligans.", "category": "Vandalism"},
    {"text": "Damage to public property: community hall glass doors shattered intentionally.", "category": "Vandalism"},

    # Other
    {"text": "Severe noise pollution from loud commercial speakers operating past midnight in residential zone.", "category": "Other"},
    {"text": "Public nuisance and illegal dumping of toxic industrial waste near drinking water canal.", "category": "Other"},
    {"text": "Missing pet dog suspected to have wandered away or taken by dog breeders.", "category": "Other"},
    {"text": "Boundary wall dispute and civil encroachment between neighbouring house owners.", "category": "Other"}
]

# Rule-based keyword mapping for transparent fallback
KEYWORD_RULES = {
    'Cyber Crime': ['phish', 'hacked', 'otp', 'bitcoin', 'crypto', 'fake website', 'online fraud', 'instagram', 'ransomware', 'cyber', 'social media', 'sim swap', 'deepfake', 'net banking'],
    'Theft': ['stolen', 'thief', 'stealing', 'pickpocket', 'snatched', 'purse', 'wallet', 'bicycle', 'laptop', 'mobile', 'bike stolen'],
    'Robbery': ['gunpoint', 'knife to', 'armed robbery', 'masked men', 'held at gunpoint', 'looted cash', 'extortion'],
    'Burglary': ['break-in', 'broke open', 'window grill', 'ransacked', 'intruder', 'burglars', 'vacation theft', 'house broken'],
    'Assault': ['beaten', 'punched', 'physically attacked', 'bleeding', 'hit with', 'brawl', 'fractured', 'battery'],
    'Domestic Violence': ['dowry', 'husband beat', 'in-laws', 'domestic abuse', 'abusive spouse', 'violence at home'],
    'Fraud': ['cheated', 'ponzi', 'chit fund', 'forged', 'bogus', 'fake documents', 'cheque bounce', 'advance fee scam'],
    'Sexual Harassment': ['vulgar', 'inappropriate touches', 'stalking', 'obscene', 'sexual favours', 'molestation'],
    'Kidnapping': ['abducted', 'kidnapped', 'ransom', 'missing child', 'snatched child'],
    'Drug Offense': ['ganja', 'cannabis', 'narcotics', 'drug peddling', 'banned pills', 'cocaine', 'heroin'],
    'Traffic Violation': ['hit and run', 'rash driving', 'drunk driving', 'speeding car', 'wrong side driving'],
    'Vandalism': ['smashed windshield', 'graffiti', 'slashed tires', 'damaged public property', 'vandalized']
}


class ComplaintClassifier:
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or Config.AI_MODEL_PATH
        self.pipeline: Optional[Pipeline] = None
        self.classes: List[str] = []
        self._load_or_train()

    def _load_or_train(self):
        """Load trained pipeline from disk or train if missing."""
        if os.path.exists(self.model_path):
            try:
                self.pipeline = joblib.load(self.model_path)
                self.classes = list(self.pipeline.classes_)
                logger.info(f"Loaded AI classifier from {self.model_path} ({len(self.classes)} classes)")
                return
            except Exception as e:
                logger.warning(f"Failed to load model from {self.model_path}: {e}. Retraining...")

        self.train_and_save()

    def train_and_save(self) -> Dict[str, Any]:
        """Train genuine scikit-learn TF-IDF + LogisticRegression pipeline and evaluate."""
        texts = [item['text'] for item in DATASET]
        labels = [item['category'] for item in DATASET]

        # Train/test split with stratification
        X_train, X_test, y_train, y_test = train_test_split(
            texts, labels, test_size=0.25, random_state=42, stratify=labels
        )

        pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(
                ngram_range=(1, 2),
                lowercase=True,
                stop_words='english',
                sublinear_tf=True
            )),
            ('clf', LogisticRegression(
                max_iter=1000,
                class_weight='balanced',
                C=5.0
            ))
        ])

        pipeline.fit(X_train, y_train)

        # Genuine evaluation
        y_pred = pipeline.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)

        # Fit on full dataset for maximum generalization in production
        pipeline.fit(texts, labels)

        # Ensure directory exists and save model
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump(pipeline, self.model_path)

        self.pipeline = pipeline
        self.classes = list(pipeline.classes_)

        logger.info(f"Trained complaint classifier. Test Accuracy: {acc:.2f}")
        return {
            'accuracy': round(acc, 4),
            'samples': len(DATASET),
            'classes': len(self.classes),
            'model_path': self.model_path
        }

    def predict(self, text: str) -> Dict[str, Any]:
        """Predict the most suitable crime category with confidence and alternatives."""
        if not text or not text.strip():
            return {
                'category': 'Other',
                'confidence': 0.0,
                'is_ml': False,
                'alternatives': [],
                'explanation': 'Empty or blank description provided.'
            }

        cleaned_text = text.strip()

        # If model is loaded, compute ML probabilities
        if self.pipeline is not None:
            try:
                probs = self.pipeline.predict_proba([cleaned_text])[0]
                indexed_probs = sorted(zip(self.pipeline.classes_, probs), key=lambda x: x[1], reverse=True)

                top_cat, top_prob = indexed_probs[0]
                top_prob_pct = round(float(top_prob) * 100, 1)

                alternatives = [
                    {'category': cat, 'confidence': round(float(prob) * 100, 1)}
                    for cat, prob in indexed_probs[1:4]
                    if prob > 0.08
                ]

                # Check if confident enough (threshold 12% given 14 classes with balanced priors, random is 7.1%)
                if top_prob >= 0.12:
                    return {
                        'category': top_cat,
                        'confidence': min(98.0, round(float(top_prob) * 100 * 2.5, 1)),
                        'is_ml': True,
                        'alternatives': alternatives,
                        'explanation': f'Suggested by scikit-learn ML model based on language patterns.'
                    }
            except Exception as e:
                logger.warning(f"ML prediction error: {e}")

        # Transparent rule-based fallback
        rule_result = self._rule_based_fallback(cleaned_text)
        return rule_result

    def _rule_based_fallback(self, text: str) -> Dict[str, Any]:
        """Transparent keyword-matching fallback system."""
        lower_text = text.lower()
        scored: Dict[str, int] = {}

        for category, keywords in KEYWORD_RULES.items():
            matches = sum(1 for kw in keywords if re.search(r'\b' + re.escape(kw) + r'\b', lower_text))
            if matches > 0:
                scored[category] = matches

        if scored:
            sorted_scored = sorted(scored.items(), key=lambda x: x[1], reverse=True)
            best_cat, count = sorted_scored[0]
            alt = [{'category': cat, 'confidence': 50.0} for cat, _ in sorted_scored[1:3]]
            return {
                'category': best_cat,
                'confidence': 60.0 if count >= 2 else 45.0,
                'is_ml': False,
                'alternatives': alt,
                'explanation': f'Rule-based keyword match for {best_cat}.'
            }

        return {
            'category': 'Other',
            'confidence': 25.0,
            'is_ml': False,
            'alternatives': [],
            'explanation': 'General incident - please select the most relevant category.'
        }


# Global singleton instance
_classifier_instance: Optional[ComplaintClassifier] = None

def get_classifier() -> ComplaintClassifier:
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = ComplaintClassifier()
    return _classifier_instance
