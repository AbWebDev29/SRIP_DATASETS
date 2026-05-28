import os
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib

def train_phishing_detector():
    features_csv = "/Users/anvibansal/SRIP/extraction_pipeline/extracted_features_output.csv"
    dataset_csv = "/Users/anvibansal/SRIP/domain_dataset_10k.csv"
    model_output_path = "/Users/anvibansal/SRIP/extension_detector/backend/phishing_rf_model.pkl"

    print("[*] Loading datasets...")
    df_features = pd.read_csv(features_csv).drop_duplicates(subset=['original_url'])
    df_dataset = pd.read_csv(dataset_csv).drop_duplicates(subset=['domain'])
    
    print("[*] Merging datasets...")
    merged_df = pd.merge(
        df_features, 
        df_dataset[['domain', 'label']], 
        left_on='original_url', 
        right_on='domain', 
        how='inner'
    )
    
    # WE DROP domain_age_days and ssl_valid_days because they are mostly -1 in your file
    feature_cols = [
        'url_length', 'domain_length', 'path_length', 'qty_dot_domain',
        'qty_hyphen_domain', 'qty_underline_domain', 'qty_digit_domain',
        'has_at_symbol', 'has_double_slash_path', 'max_levenshtein_ratio',
        'max_jaro_winkler_score', 'is_punycode'
    ]
    
    X = merged_df[feature_cols]
    y = merged_df['label']
    
    print(f"[*] Training on {len(feature_cols)} robust lexical features...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Max depth set to 10 to ensure generalization
    rf_model = RandomForestClassifier(
        n_estimators=100, 
        max_depth=10, 
        random_state=42, 
        n_jobs=-1
    )
    rf_model.fit(X_train, y_train)
    
    y_pred = rf_model.predict(X_test)
    print(f"[+] Training complete. Test Accuracy: {accuracy_score(y_test, y_pred) * 100:.2f}%")
    print(classification_report(y_test, y_pred))
    
    # Save model and feature list keys together
    model_payload = {'model': rf_model, 'features': feature_cols}
    joblib.dump(model_payload, model_output_path)
    print(f"[+] Robust model payload saved to: {model_output_path}")

if __name__ == "__main__":
    train_phishing_detector()