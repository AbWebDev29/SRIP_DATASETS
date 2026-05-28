from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import pandas as pd
from urllib.parse import urlparse
import os
import sys

app = Flask(__name__)
# Enable explicit cross-origin resource sharing for the extension
CORS(app, resources={r"/*": {"origins": "*"}})

# ============================================================================
# TOP-TIER GLOBAL SAFE DOMAIN ALLOWLIST OVERRIDE
# These domains are absolutely trusted and will bypass ML prediction entirely.
# Any URL from these domains will be instantly returned as safe (0% risk).
# This prevents false positives on legitimate complex URLs from known brands.
# ============================================================================
TRUSTED_SAFE_DOMAINS = [
    'google.com',
    'gemini.google.com',
    'mail.google.com',
    'drive.google.com',
    'docs.google.com',
    'apple.com',
    'icloud.com',
    'microsoft.com',
    'outlook.com',
    'github.com',
    'wikipedia.org',
    'amazon.com',
    'aws.amazon.com',
    'console.aws.amazon.com',
    'yahoo.com',
    'facebook.com',
    'instagram.com',
    'twitter.com',
    'linkedin.com',
    'reddit.com',
    'stackoverflow.com',
    'medium.com',
    'youtube.com',
    'netflix.com',
    'dropbox.com',
    'slack.com',
    'zoom.us',
    'openai.com',
    'notion.so',
    'figma.com',
]


def is_trusted_domain(hostname):
    """
    Check if hostname matches or is a subdomain of any trusted safe domain.
    
    Args:
        hostname: Domain name (e.g., "gemini.google.com" or "google.com")
    
    Returns:
        True if hostname is in trusted list or is a subdomain of trusted domain
    """
    if not hostname:
        return False
    
    hostname_lower = hostname.lower()
    
    for trusted in TRUSTED_SAFE_DOMAINS:
        trusted_lower = trusted.lower()
        # Exact match
        if hostname_lower == trusted_lower:
            return True
        # Subdomain match (must end with .trusted, not just contain it)
        if hostname_lower.endswith('.' + trusted_lower):
            return True
    
    return False


# Load the trained model payload safely
model_path = '/Users/anvibansal/SRIP/model_training/phishing_rf_model.pkl'

# Check if model file exists
if not os.path.exists(model_path):
    print(f"ERROR: Model file not found at {model_path}")
    sys.exit(1)

try:
    payload = joblib.load(model_path)
    model = payload['model']
    trained_features = payload['features']  # This contains the exact 10 clean features in order
    print(f"Model loaded successfully. Features: {trained_features}")
except Exception as e:
    print(f"ERROR loading model: {e}")
    sys.exit(1)


def extract_lexical_features(url):
    """
    Extract exactly 10 lexical features from a URL.
    MUST match the exact order and logic from train_model.py.
    """
    if not url or not isinstance(url, str):
        return None
    
    url = url.strip().lower()
    
    # Normalize URL format for parsing
    if not url.startswith(('http://', 'https://', 'ftp://')):
        url = 'http://' + url
    
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.split(':')[0]  # Remove port
        path = parsed.path
        
        if not domain:
            return None
        
        # Feature extraction - EXACT ORDER matters
        features = {}
        
        # 1. url_length: Total length of the full URL
        features['url_length'] = len(url)
        
        # 2. domain_length: Length of domain part
        features['domain_length'] = len(domain)
        
        # 3. path_length: Length of path part
        features['path_length'] = len(path)
        
        # 4. qty_dot_domain: Count of dots in domain
        features['qty_dot_domain'] = domain.count('.')
        
        # 5. qty_hyphen_domain: Count of hyphens in domain
        features['qty_hyphen_domain'] = domain.count('-')
        
        # 6. qty_underline_domain: Count of underscores in domain
        features['qty_underline_domain'] = domain.count('_')
        
        # 7. qty_digit_domain: Count of digits in domain
        features['qty_digit_domain'] = sum(1 for c in domain if c.isdigit())
        
        # 8. has_at_symbol: Boolean flag for @ presence in full URL
        features['has_at_symbol'] = int('@' in url)
        
        # 9. has_double_slash_path: Boolean flag for // in path (after domain)
        features['has_double_slash_path'] = int('//' in path)
        
        # 10. is_punycode: Check if domain contains 'xn--' (punycode indicator)
        features['is_punycode'] = int('xn--' in domain)
        
        return features
    
    except Exception as e:
        print(f"Error extracting features from '{url}': {e}")
        return None


@app.route('/predict', methods=['POST', 'OPTIONS'])
def predict():
    """
    POST endpoint to predict phishing status of a URL.
    Expects JSON payload: {"url": "https://example.com"}
    
    CRITICAL: Implements Top-Tier Global Safe Domain Allowlist Override.
    If the URL's domain matches any trusted brand, returns safe immediately
    without ML model evaluation.
    
    Returns JSON: {"is_phishing": 0|1, "probability": 0.0-1.0, "status": "safe"|"unsafe"}
    """
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Parse request
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400
        
        raw_url = data.get("url")
        if not raw_url:
            return jsonify({"error": "No URL provided"}), 400
        
        # ====================================================================
        # STEP 1: TRUSTED DOMAIN ALLOWLIST OVERRIDE
        # Before ML model evaluation, check if URL is from a trusted domain.
        # If yes, return safe immediately (bypass ML entirely).
        # ====================================================================
        try:
            parsed_check = urlparse(raw_url if raw_url.startswith(('http://', 'https://')) else 'http://' + raw_url)
            hostname = parsed_check.netloc.split(':')[0].lower()
            
            if is_trusted_domain(hostname):
                # Trusted domain detected - return safe immediately
                print(f"[ALLOWLIST OVERRIDE] Trusted domain: {hostname}")
                return jsonify({
                    "is_phishing": 0,
                    "probability": 0.0,
                    "status": "safe"
                }), 200
        except Exception as e:
            print(f"Warning: Error checking trusted domains: {e}")
            # Continue to ML model if allowlist check fails
        
        # ====================================================================
        # STEP 2: EXTRACT FEATURES (for non-trusted URLs)
        # Use ML model to evaluate unknown/untrusted URLs.
        # ====================================================================
        features = extract_lexical_features(raw_url)
        if features is None:
            return jsonify({"error": "Failed to parse URL"}), 400
        
        # Create DataFrame with features in the correct order
        input_df = pd.DataFrame([features])[trained_features]
        
        # Make prediction
        prediction = model.predict(input_df)[0]
        probabilities = model.predict_proba(input_df)[0]
        
        # Probability of phishing class (label=1)
        probability = float(probabilities[1])
        
        # Return JSON response with exact schema
        return jsonify({
            "is_phishing": int(prediction),
            "probability": probability,
            "status": "unsafe" if int(prediction) == 1 else "safe"
        }), 200
    
    except Exception as e:
        print(f"Error in /predict endpoint: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "model_loaded": True}), 200


if __name__ == '__main__':
    print("="*60)
    print("PHISHING DETECTION: FLASK BACKEND v2")
    print("="*60)
    print(f"Model loaded: {trained_features}")
    print("Starting server on http://127.0.0.1:5000")
    print("="*60 + "\n")
    app.run(debug=True, port=5000, use_reloader=False)