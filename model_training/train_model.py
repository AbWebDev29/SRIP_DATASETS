#!/usr/bin/env python3
"""
Complete ML Pipeline: Data Aggregation, Feature Extraction & Random Forest Training
Loads 3 distinct CSV sources, cleans domains, extracts 10 lexical features,
trains balanced RandomForestClassifier, and exports joblib pickle.

IMPORTANT: Includes Top-Tier Global Safe Domain Allowlist Override to prevent
false positives on legitimate complex URLs from trusted brands.
"""

import os
import sys
import re
import pandas as pd
import numpy as np
import joblib
from urllib.parse import urlparse
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

# ============================================================================
# TOP-TIER GLOBAL SAFE DOMAIN ALLOWLIST
# These domains are absolutely trusted and will be forced to label=0 during
# training to prevent the model from building false-positive rules.
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


def extract_domain_from_url(url):
    """Extract domain from URL string, handling various input formats."""
    if not url or not isinstance(url, str):
        return None
    
    url = url.strip().lower()
    
    # Handle URLs without protocol
    if not url.startswith(('http://', 'https://', 'ftp://')):
        url = 'http://' + url
    
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        if not domain:
            return None
        # Remove port if present
        domain = domain.split(':')[0]
        return domain if domain else None
    except Exception:
        return None


def extract_lexical_features(url):
    """
    Extract exactly 10 lexical features from a URL.
    Features must match exactly the order used during model training.
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
        
        # Feature extraction
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


def load_and_normalize_dataset(csv_file, url_column, label_column=None, label_value=None):
    """
    Load CSV, extract domains, drop duplicates, and prepare labels.
    
    Args:
        csv_file: Path to CSV file
        url_column: Name of column containing URLs
        label_column: Column name for labels (if present in CSV)
        label_value: Fixed label value (if using fixed label for entire dataset)
    
    Returns:
        DataFrame with 'domain' and 'label' columns
    """
    try:
        df = pd.read_csv(csv_file)
        print(f"Loaded {csv_file}: {len(df)} rows")
        
        # Auto-detect URL column if not found
        if url_column not in df.columns:
            url_column = df.columns[0]
            print(f"  URL column not found as '{url_column}', using first column: {url_column}")
        
        # Extract domains
        df['domain'] = df[url_column].apply(extract_domain_from_url)
        
        # Drop rows with None domains
        df = df.dropna(subset=['domain'])
        
        # Handle labels
        if label_column and label_column in df.columns:
            df['label'] = df[label_column]
        elif label_value is not None:
            df['label'] = label_value
        else:
            print(f"  Warning: No label assigned for {csv_file}")
            return None
        
        # Drop duplicates based on domain
        df = df.drop_duplicates(subset=['domain'])
        
        # Keep only domain and label
        df = df[['domain', 'label']]
        
        print(f"  After normalization: {len(df)} unique domains")
        return df
    
    except Exception as e:
        print(f"Error loading {csv_file}: {e}")
        return None


def prepare_training_data(base_path):
    """Load and aggregate all three data sources.
    
    CRITICAL: Forces any URL from trusted domains to label=0 (Safe)
    to prevent the model from building false-positive rules.
    """
    print("\n=== LOADING AND NORMALIZING DATA ===\n")
    
    datasets = []
    
    # Load domain_dataset_10k.csv (has label column)
    df1 = load_and_normalize_dataset(
        os.path.join(base_path, 'domain_dataset_10k.csv'),
        url_column='domain',
        label_column='label'
    )
    if df1 is not None:
        datasets.append(df1)
    
    # Load phi_url.csv (malicious - label=1)
    df2 = load_and_normalize_dataset(
        os.path.join(base_path, 'phi_url.csv'),
        url_column='phish_url',
        label_value=1  # Phishing URLs
    )
    if df2 is not None:
        datasets.append(df2)
    
    # Load saf_url.csv (safe - label=0)
    df3 = load_and_normalize_dataset(
        os.path.join(base_path, 'saf_url.csv'),
        url_column='saf_url',
        label_value=0  # Safe URLs
    )
    if df3 is not None:
        datasets.append(df3)
    
    # Aggregate all datasets
    combined_df = pd.concat(datasets, ignore_index=True)
    
    # Remove duplicates, keeping the last occurrence
    combined_df = combined_df.drop_duplicates(subset=['domain'], keep='last')
    
    # ========================================================================
    # TRUSTED DOMAIN OVERRIDE: Force all trusted domains to label=0
    # This prevents the model from building false-positive rules based on
    # URL structure alone. Legitimate complex URLs from Google, Apple, etc.
    # will ALWAYS be labeled as safe during training.
    # ========================================================================
    print("Applying Trusted Domain Allowlist Override...")
    trusted_count = 0
    for idx, row in combined_df.iterrows():
        domain = row['domain']
        if is_trusted_domain(domain):
            if combined_df.at[idx, 'label'] != 0:
                combined_df.at[idx, 'label'] = 0
                trusted_count += 1
    
    if trusted_count > 0:
        print(f"  Overridden {trusted_count} rows to label=0 (trusted domains)\n")
    
    print(f"Combined dataset: {len(combined_df)} total unique domains")
    print(f"Label distribution:\n{combined_df['label'].value_counts()}\n")
    
    return combined_df


def extract_features_for_dataset(domains_df):
    """Extract all 10 lexical features for the dataset."""
    print("=== EXTRACTING LEXICAL FEATURES ===\n")
    
    feature_list = []
    invalid_count = 0
    
    # Define feature column order (CRITICAL: Must match inference order)
    feature_columns = [
        'url_length',
        'domain_length',
        'path_length',
        'qty_dot_domain',
        'qty_hyphen_domain',
        'qty_underline_domain',
        'qty_digit_domain',
        'has_at_symbol',
        'has_double_slash_path',
        'is_punycode'
    ]
    
    for idx, row in domains_df.iterrows():
        domain = row['domain']
        features = extract_lexical_features(domain)
        
        if features is None:
            invalid_count += 1
            continue
        
        feature_list.append(features)
    
    print(f"Extracted features for {len(feature_list)} domains")
    if invalid_count > 0:
        print(f"Skipped {invalid_count} domains due to extraction errors\n")
    
    # Create DataFrame with features
    features_df = pd.DataFrame(feature_list)
    
    # Ensure columns exist in correct order
    features_df = features_df[feature_columns]
    
    # Add label back
    features_df['label'] = domains_df['label'].iloc[:len(features_df)].values
    
    print(f"Final feature matrix shape: {features_df.shape}")
    print(f"Feature columns: {list(features_df.columns[:-1])}\n")
    
    return features_df, feature_columns


def train_model(features_df, feature_columns):
    """Train Random Forest with balanced class weights."""
    print("=== TRAINING RANDOM FOREST ===\n")
    
    X = features_df[feature_columns]
    y = features_df['label']
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"Training set: {len(X_train)} samples")
    print(f"Test set: {len(X_test)} samples")
    print(f"Training label distribution: {y_train.value_counts().to_dict()}\n")
    
    # Train model
    model = RandomForestClassifier(
        n_estimators=100,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1,
        max_depth=15
    )
    
    print("Training model...")
    model.fit(X_train, y_train)
    
    # Evaluate
    train_score = model.score(X_train, y_train)
    test_score = model.score(X_test, y_test)
    
    print(f"Training accuracy: {train_score:.4f}")
    print(f"Test accuracy: {test_score:.4f}\n")
    
    # Feature importance
    importances = model.feature_importances_
    feature_importance_df = pd.DataFrame({
        'feature': feature_columns,
        'importance': importances
    }).sort_values('importance', ascending=False)
    
    print("Top 5 Feature Importances:")
    print(feature_importance_df.head())
    print()
    
    return model


def save_model_pipeline(model, feature_columns, output_path):
    """Save model and feature columns as joblib pickle."""
    print(f"=== SAVING MODEL ===\n")
    
    pipeline = {
        'model': model,
        'features': feature_columns
    }
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    joblib.dump(pipeline, output_path)
    
    print(f"Model saved to: {output_path}")
    print(f"Pipeline contains: model object + {len(feature_columns)} feature names\n")


def main():
    """Execute complete pipeline."""
    print("="*60)
    print("PHISHING DETECTION: ML TRAINING PIPELINE v2")
    print("="*60 + "\n")
    
    base_path = '/Users/anvibansal/SRIP'
    output_path = '/Users/anvibansal/SRIP/model_training/phishing_rf_model.pkl'
    
    # Step 1: Load and normalize data
    combined_df = prepare_training_data(base_path)
    
    if len(combined_df) == 0:
        print("ERROR: No data loaded. Check CSV files and paths.")
        sys.exit(1)
    
    # Step 2: Extract features
    features_df, feature_columns = extract_features_for_dataset(combined_df)
    
    if len(features_df) == 0:
        print("ERROR: No features extracted. Check domain format.")
        sys.exit(1)
    
    # Step 3: Train model
    model = train_model(features_df, feature_columns)
    
    # Step 4: Save pipeline
    save_model_pipeline(model, feature_columns, output_path)
    
    print("="*60)
    print("TRAINING COMPLETE ✓")
    print("="*60)


if __name__ == '__main__':
    main()

