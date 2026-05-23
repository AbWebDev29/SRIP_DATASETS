import datetime
import ssl
import socket
import tldextract
import Levenshtein
import pandas as pd
from sklearn.model_selection import train_test_split
import whois
import warnings

# Optional: Silence external library warnings if they clutter your terminal
warnings.filterwarnings("ignore", category=UserWarning, module='whois')

# ==========================================
# CONFIGURATION & REFERENCE POOL
# ==========================================
TARGET_BRANDS = ["google.com", "microsoft.com", "paypal.com", "vit.ac.in"]

# FIX: Used .top_domain_under_public_suffix instead of deprecated .registered_domain
TARGET_DOMAINS = [tldextract.extract(url).top_domain_under_public_suffix for url in TARGET_BRANDS]

# ==========================================
# FEATURE EXTRACTION LAYERS
# ==========================================

def extract_features(url: str, check_external: bool = False) -> dict:
    """
    Parses a raw URL string and extracts Layer A, B, and (optionally) C features.
    """
    features = {}
    
    # Pre-parse URL using updated tldextract attributes
    ext = tldextract.extract(url)
    domain = ext.top_domain_under_public_suffix if ext.top_domain_under_public_suffix else ext.domain
    full_domain = f"{ext.subdomain}.{ext.top_domain_under_public_suffix}" if ext.subdomain else ext.top_domain_under_public_suffix
    path = url.split(full_domain)[-1] if full_domain in url else ""

    # ------------------------------------------
    # LAYER A: Lexical / Structural Features
    # ------------------------------------------
    features['url_length'] = len(url)
    features['domain_length'] = len(full_domain)
    features['path_length'] = len(path)
    
    features['qty_dot_domain'] = full_domain.count('.')
    features['qty_hyphen_domain'] = full_domain.count('-')
    features['qty_underline_domain'] = full_domain.count('_')
    features['qty_digit_domain'] = sum(c.isdigit() for c in full_domain)
    
    features['has_at_symbol'] = 1 if '@' in path else 0
    features['has_double_slash_path'] = 1 if '//' in path else 0

    # ------------------------------------------
    # LAYER B: Algorithmic Similarity Heuristics
    # ------------------------------------------
    max_levenshtein_ratio = 0.0
    max_jaro_winkler_score = 0.0
    
    for target in TARGET_DOMAINS:
        lev_ratio = Levenshtein.ratio(domain, target)
        if lev_ratio > max_levenshtein_ratio:
            max_levenshtein_ratio = lev_ratio
            
        jw_score = Levenshtein.jaro_winkler(domain, target)
        if jw_score > max_jaro_winkler_score:
            max_jaro_winkler_score = jw_score
            
    features['max_levenshtein_ratio'] = max_levenshtein_ratio
    features['max_jaro_winkler_score'] = max_jaro_winkler_score
    
    features['is_punycode'] = 1 if ext.domain.startswith('xn--') else 0

    # ------------------------------------------
    # LAYER C: External Network Metadata
    # ------------------------------------------
    features['domain_age_days'] = -1
    features['ssl_valid_days'] = -1
    
    if check_external and full_domain:
        # 1. Domain Age via WHOIS
        try:
            w = whois.whois(full_domain)
            creation_date = w.creation_date
            if isinstance(creation_date, list):
                creation_date = creation_date[0]
            
            if isinstance(creation_date, datetime.datetime):
                age = (datetime.datetime.now() - creation_date).days
                features['domain_age_days'] = max(0, age)
        except Exception:
            features['domain_age_days'] = -1
            
        # 2. SSL Certificate Validity
        try:
            context = ssl.create_default_context()
            with socket.create_connection((full_domain, 443), timeout=3) as sock:
                with context.wrap_socket(sock, server_hostname=full_domain) as ssock:
                    cert = ssock.getpeercert()
                    not_after_str = cert['notAfter']
                    expiry_date = datetime.datetime.strptime(not_after_str, '%b %d %H:%M:%S %Y %Z')
                    remaining_days = (expiry_date - datetime.datetime.now()).days
                    features['ssl_valid_days'] = max(0, remaining_days)
        except Exception:
            features['ssl_valid_days'] = -1

    return features

# ==========================================
# STEP 2 & 3: MATRIX GENERATION & SPLITTING
# ==========================================

def process_dataset_to_matrices(raw_data_list: list, include_network: bool = False):
    """
    Processes raw inputs, builds the Pandas DataFrame, saves to CSV, 
    and returns X and y train/test matrices with fallback safety for tiny sets.
    """
    processed_rows = []
    
    print("⏳ Extracting features from dataset...")
    for url, label in raw_data_list:
        feat_dict = extract_features(url, check_external=include_network)
        feat_dict['url'] = url
        feat_dict['is_phishing'] = label
        processed_rows.append(feat_dict)
        
    df = pd.DataFrame(processed_rows)
    
    output_filename = "processed_features.csv"
    df.to_csv(output_filename, index=False)
    print(f"✅ Saved processed feature matrix to {output_filename}")
    
    X = df.drop(columns=['url', 'is_phishing'])
    y = df['is_phishing']
    
    # --- FIX: Safe Stratified Split Check ---
    # Determine the minimum instances of each class
    class_counts = y.value_counts()
    min_class_count = class_counts.min() if len(class_counts) > 1 else 0
    expected_test_samples = len(df) * 0.20

    # Stratification fails if expected test samples per class layout is mathematically impossible
    if min_class_count < 2 or expected_test_samples < 2:
        print("⚠️  Dataset too small for reliable stratification. Falling back to simple split.")
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.25, random_state=42 # Slightly higher test size to ensure at least 1 sample drops in
        )
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.20, stratify=y, random_state=42
        )
    
    print(f"📊 Matrix generation complete!")
    print(f"   Training shape: {X_train.shape}")
    print(f"   Testing shape : {X_test.shape}")
    
    return X_train, X_test, y_train, y_test

# ==========================================
# PIPELINE RUNNER
# ==========================================
if __name__ == "__main__":
    mock_dataset = [
        ("https://xn--vtop-43da.vit.ac.in/bali/login.php", 1), 
        ("https://www.google.com/search?q=python", 0),          
        ("http://paypal-security-update-alert.com/login", 1),  
        ("https://vit.ac.in/admissions", 0)                    
    ]
    
    X_train, X_test, y_train, y_test = process_dataset_to_matrices(mock_dataset, include_network=False)
    
    print("\nSample processed vector row layout:")
    print(X_train.head(1).to_dict(orient='records')[0])