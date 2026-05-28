import joblib

# Load your custom model payload package
payload = joblib.load('/Users/anvibansal/SRIP/model_training/phishing_rf_model.pkl')

print("--- Model Payload Package Contents ---")
print("Keys stored in file:", payload.keys())
print("Expected Features List:", payload['features'])
print("\n--- Under-the-Hood Classifier Properties ---")
print("Model Object Type:", type(payload['model']))
print("Number of Trees (Estimators):", payload['model'].n_estimators)
print("Max Depth Allowed:", payload['model'].max_depth)
print("Classes Learned:", payload['model'].classes_)  # Should output [0, 1]