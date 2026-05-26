import datetime
import ssl
import socket
import os
import tldextract
import Levenshtein
import pandas as pd
import whois
import warnings

# Silence external library warnings if they clutter your terminal
warnings.filterwarnings("ignore", category=UserWarning, module='whois')
# ==========================================
# CONFIGURATION & REFERENCE POOL
# ==========================================
TARGET_BRANDS = ["google.com", "microsoft.com", "paypal.com", "vit.ac.in"]

# Extracted top domains for lookalike calculations
TARGET_DOMAINS = [tldextract.extract(url).top_domain_under_public_suffix for url in TARGET_BRANDS]

# ==========================================
# FEATURE EXTRACTION LAYER
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
        if not domain or not target:
            continue
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
# UNLABELED DATASET PROCESSING PIPELINE
# ==========================================

def process_unlabeled_file(file_path: str, include_network: bool = False) -> pd.DataFrame:
    """
    Reads a CSV or Excel file of unlabeled URLs, extracts security features,
    saves the matrix to a CSV, and returns a pure numerical feature matrix X.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"❌ Could not find file at: {file_path}")

    # 1. Load file dynamically based on extension
    print(f"📖 Loading dataset from {file_path}...")
    if file_path.endswith('.csv'):
        df_raw = pd.read_csv(file_path)
    elif file_path.endswith('.xlsx') or file_path.endswith('.xls'):
        df_raw = pd.read_excel(file_path)
    else:
        raise ValueError("❌ Unsupported file format. Please use a .csv or .xlsx file.")
    
    # 2. Smart Column Detection for URLs
    url_col = None
    possible_names = ['url', 'urls', 'domain', 'domains', 'link', 'links', 'address']
    for col in df_raw.columns:
        if str(col).lower().strip() in possible_names:
            url_col = col
            break
            
    if not url_col:
        url_col = df_raw.columns[0]
        print(f"⚠️ Could not find a distinct 'url' column name. Defaulting to the first column: '{url_col}'")

    # 3. Extract Features
    processed_rows = []
    urls_to_process = df_raw[url_col].dropna()
    total_urls = len(urls_to_process)
    
    print(f"⏳ Extracting features from {total_urls} URLs. Please wait...")
    for idx, url in enumerate(urls_to_process, 1):
        url_str = str(url).strip()
        
        # Skip empty strings
        if not url_str:
            continue
            
        feat_dict = extract_features(url_str, check_external=include_network)
        feat_dict['original_url'] = url_str  # Maintained mapping layout
        processed_rows.append(feat_dict)
        
        # Print progress every 50 URLs so you know it hasn't frozen
        if idx % 50 == 0 or idx == total_urls:
            print(f"   Processed {idx}/{total_urls} URLs...")
        
    df_features = pd.DataFrame(processed_rows)
    
    # 4. Save Features to disk
    output_filename = "extracted_features_output.csv"
    df_features.to_csv(output_filename, index=False)
    print(f"✅ Master feature logging saved to: {output_filename}")
    
    # 5. Build pure numerical inference matrix X (Drops string components)
    X = df_features.drop(columns=['original_url'])
    return X

# ==========================================
# PIPELINE RUNNER
# ==========================================
if __name__ == "__main__":
    # 🛑 UPDATE THIS: Put the path to your CSV or Excel file here!
    # Example: "my_links.csv" or "C:/Users/Name/Documents/urls.xlsx"
    YOUR_FILE_PATH = "/Users/anvibansal/SRIP/domain_dataset_10k.csv"
    
    # Optional: Turn this into True if you want to perform live WHOIS/SSL checks 
    # Warning: Turning network checks True on large files will take a long time!
    RUN_NETWORK_CHECKS = False 

    try:
        # Generate the numerical matrix
        X_matrix = process_unlabeled_file(YOUR_FILE_PATH, include_network=RUN_NETWORK_CHECKS)
        
        print("\n📊 Extraction Pipeline Successfully Finished!")
        print(f"   Numerical Matrix Layout Shape: {X_matrix.shape}")
        print("\nSample processed vector row layout:")
        if not X_matrix.empty:
            print(X_matrix.head(1).to_dict(orient='records')[0])
            
        print("\n💡 Next step: You can feed this 'X_matrix' directly into your trained model.predict(X_matrix)")

    except FileNotFoundError:
        print(f"\n💡 [Setup Note]: To test this with your own files, replace 'your_unlabeled_file.csv' at the bottom of the script with your actual file path.")
