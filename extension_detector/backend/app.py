from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import pandas as pd
from urllib.parse import urlparse
import os, sys

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

TRUSTED_SAFE_DOMAINS = [
    'google.com','apple.com','icloud.com','microsoft.com','outlook.com',
    'github.com','wikipedia.org','amazon.com','yahoo.com','facebook.com',
    'instagram.com','twitter.com','linkedin.com','reddit.com',
    'stackoverflow.com','medium.com','youtube.com','netflix.com',
    'dropbox.com','slack.com','zoom.us','openai.com','notion.so','figma.com',
]

FEATURE_COLUMNS = [
    'url_length','domain_length','path_length','qty_dot_domain',
    'qty_hyphen_domain','qty_underline_domain','qty_digit_domain',
    'has_at_symbol','has_double_slash_path','is_punycode',
    'qty_slash_url','qty_dot_url','has_http_in_path',
]

def is_trusted_domain(hostname):
    """Check if hostname matches or is a subdomain of any trusted safe domain."""
    if not hostname: return False
    h = hostname.lower()
    for t in TRUSTED_SAFE_DOMAINS:
        if h == t or h.endswith('.' + t): return True
    return False

# Load the trained model payload
model_path = '/Users/anvibansal/SRIP/model_training/phishing_rf_model.pkl'
if not os.path.exists(model_path):
    print(f"ERROR: Model file not found at {model_path}"); sys.exit(1)
try:
    payload = joblib.load(model_path)
    model = payload['model']
    trained_features = payload['features']
    print(f"Model loaded. Features ({len(trained_features)}): {trained_features}")
except Exception as e:
    print(f"ERROR loading model: {e}"); sys.exit(1)


def extract_lexical_features(url):
    """
    Extract exactly 13 lexical features from a URL.
    MUST match the exact order and logic from train_model.py.
    """
    if not url or not isinstance(url, str): return None
    url = url.strip().lower()
    if not url.startswith(('http://','https://','ftp://')): url = 'http://' + url
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.split(':')[0]
        path = parsed.path
        if not domain: return None
        return {
            'url_length': len(url),
            'domain_length': len(domain),
            'path_length': len(path),
            'qty_dot_domain': domain.count('.'),
            'qty_hyphen_domain': domain.count('-'),
            'qty_underline_domain': domain.count('_'),
            'qty_digit_domain': sum(c.isdigit() for c in domain),
            'has_at_symbol': int('@' in url),
            'has_double_slash_path': int('//' in path),
            'is_punycode': int('xn--' in domain),
            'qty_slash_url': url.count('/'),
            'qty_dot_url': url.count('.'),
            'has_http_in_path': int('http' in path.lower()),
        }
    except Exception as e:
        print(f"Error extracting features from '{url}': {e}"); return None


@app.route('/predict', methods=['POST', 'OPTIONS'])
def predict():
    """
    POST /predict — Predict phishing status of a URL.
    Expects: {"url": "https://example.com"}
    Returns: {"is_phishing": 0|1, "probability": 0.0-1.0, "status": "safe"|"unsafe"}

    ALLOWLIST: Trusted domains bypass ML and return safe immediately.
    """
    if request.method == 'OPTIONS': return '', 200
    try:
        data = request.get_json()
        if not data: return jsonify({"error": "Invalid JSON"}), 400
        raw_url = data.get("url")
        if not raw_url: return jsonify({"error": "No URL provided"}), 400

        # --- ALLOWLIST SHORT-CIRCUIT ---
        try:
            norm = raw_url if raw_url.startswith(('http://','https://')) else 'http://'+raw_url
            hostname = urlparse(norm).netloc.split(':')[0].lower()
            if is_trusted_domain(hostname):
                print(f"[ALLOWLIST] Trusted: {hostname}")
                return jsonify({"is_phishing":0,"probability":0.0,"status":"safe"}), 200
        except: pass

        # --- ML PREDICTION ---
        features = extract_lexical_features(raw_url)
        if features is None: return jsonify({"error": "Failed to parse URL"}), 400
        input_df = pd.DataFrame([features])[trained_features]
        pred = model.predict(input_df)[0]
        prob = float(model.predict_proba(input_df)[0][1])
        return jsonify({
            "is_phishing": int(pred),
            "probability": round(prob, 6),
            "status": "unsafe" if int(pred)==1 else "safe"
        }), 200
    except Exception as e:
        print(f"Error in /predict: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status":"ok","model_loaded":True,"features":len(trained_features)}), 200


if __name__ == '__main__':
    print("="*60)
    print("  PHISHING DETECTION: FLASK BACKEND v3")
    print(f"  Model: {len(trained_features)} features loaded")
    print("  Server: http://127.0.0.1:5000")
    print("="*60)
    app.run(debug=True, port=5000, use_reloader=False)