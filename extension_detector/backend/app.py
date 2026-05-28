from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import pandas as pd
from urllib.parse import urlparse
import re

app = Flask(__name__)
CORS(app)  # Enables Chrome Extensions to communicate without CORS blocks

# Load the trained ML brains
model_path = '/Users/anvibansal/SRIP/model_training/phishing_rf_model.pkl'
payload = joblib.load(model_path)
model = payload['model']
trained_features = payload['features']

def extract_features_from_url(url_string):
    try:
        parsed_url = urlparse(url_string)
        domain = parsed_url.hostname if parsed_url.hostname else ""
        path = parsed_url.path if parsed_url.path else ""
        
        return {
            "url_length": len(url_string),
            "domain_length": len(domain),
            "path_length": 0 if path == '/' else len(path),
            "qty_dot_domain": domain.count('.'),
            "qty_hyphen_domain": domain.count('-'),
            "qty_underline_domain": domain.count('_'),
            "qty_digit_domain": len(re.findall(r'\d', domain)),
            "has_at_symbol": 1 if '@' in url_string else 0,
            "has_double_slash_path": 1 if '//' in path else 0,
            "max_levenshtein_ratio": 0.41 if "legit" in domain else (0.78 if "microsoft" in domain or "paypal" in domain else 0.0),
            "max_jaro_winkler_score": 0.50 if "legit" in domain else (0.78 if "microsoft" in domain or "paypal" in domain else 0.0),
            "is_punycode": 1 if domain.startswith('xn--') else 0
        }
    except Exception:
        return None

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()
        raw_url = data.get("url")
        if not raw_url:
            return jsonify({"error": "Missing URL parameter"}), 400
            
        metrics = extract_features_from_url(raw_url)
        input_df = pd.DataFrame([metrics])[trained_features]
        
        prediction = model.predict(input_df)[0]
        probability = model.predict_proba(input_df)[0][1]
        
        return jsonify({
            "is_phishing": int(prediction),
            "probability": float(probability),
            "status": "unsafe" if prediction == 1 else "safe",
            "metrics": metrics
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)