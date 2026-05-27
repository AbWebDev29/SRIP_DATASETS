import os
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
import joblib

def train_phishing_detector():
    # 1. Paths to your files (Update paths if necessary)
    features_csv = "/Users/anvibansal/SRIP/extraction_pipeline/extracted_features_output.csv"
    dataset_csv = "/Users/anvibansal/SRIP/domain_dataset_10k.csv" # or wherever domain_dataset_10k.csv is saved
    model_output_path = "phishing_rf_model.pkl"
    
    # Fallback to local files if absolute path is different
    if not os.path.exists(features_csv):
        features_csv = "extracted_features_output.csv"
    if not os.path.exists(dataset_csv):
        dataset_csv = "domain_dataset_10k.csv"

    print(f"[*] Loading features from: {features_csv}")
    print(f"[*] Loading source labels from: {dataset_csv}")
    
    # 2. Read the files
    df_features = pd.read_csv(features_csv)
    df_dataset = pd.read_csv(dataset_csv)
    
    # 3. Clean duplicates to avoid artifact rows
    df_features = df_features.drop_duplicates(subset=['original_url'])
    df_dataset = df_dataset.drop_duplicates(subset=['domain'])
    
    # 4. Merge datasets on the domain strings
    print("[*] Merging datasets to attach target labels...")
    merged_df = pd.merge(
        df_features, 
        df_dataset[['domain', 'label']], 
        left_on='original_url', 
        right_on='domain', 
        how='inner'
    )
    print(f"[+] Successfully matched {merged_df.shape[0]} unique rows with labels.")
    
    # 5. Separate features and target
    target_col = 'label'
    # Drop columns that are text or redundant identifiers
    columns_to_drop = [target_col, 'original_url', 'domain']
    feature_cols = [col for col in merged_df.columns if col not in columns_to_drop]
    
    print(f"[*] Extracting {len(feature_cols)} training features...")
    
    X = merged_df[feature_cols]
    y = merged_df[target_col]
    
    # 6. Split Data (80% Train, 20% Test)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"[*] Data split complete. Training: {X_train.shape[0]}, Testing: {X_test.shape[0]}")
    
    # 7. Train Random Forest Classifier
    print("[*] Initializing and training Random Forest Classifier...")
    rf_model = RandomForestClassifier(
        n_estimators=100, 
        max_depth=15, 
        random_state=42, 
        n_jobs=-1
    )
    rf_model.fit(X_train, y_train)
    print("[+] Model training complete.")
    
    # 8. Evaluate performance
    y_pred = rf_model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    print("\n" + "="*60)
    print("🚀 MODEL PERFORMANCE EVALUATION")
    print("="*60)
    print(f"Overall Classification Accuracy: {accuracy * 100:.2f}%")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=['Safe (0)', 'Phishing (1)']))
    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
    print("="*60 + "\n")
    
    # 9. Save both the model and the feature list structure for Flask API consumption
    model_payload = {
        'model': rf_model,
        'features': feature_cols
    }
    joblib.dump(model_payload, model_output_path)
    print(f"[+] Production-ready model payload saved to: {model_output_path}")

if __name__ == "__main__":
    train_phishing_detector()