# ML-Powered Phishing Detection System
## A Real-Time Lexical Analysis Research Project

[![Status](https://img.shields.io/badge/Status-Production_Ready-brightgreen.svg)]()
[![Version](https://img.shields.io/badge/Version-2.0-blue.svg)]()
[![Model](https://img.shields.io/badge/Model-Random_Forest-orange.svg)]()
[![License](https://img.shields.io/badge/License-MIT-green.svg)]()

---

## 📌 Abstract

This research project presents a real-time, machine learning-powered system for detecting phishing websites using purely lexical URL analysis. By eliminating the need for external database lookups or semantic content analysis, the system achieves sub-second inference times while maintaining high accuracy. The architecture consists of a trained Random Forest model, a lightweight Flask backend API, and a Manifest V3 Chrome Extension that allows users to perform on-demand URL scanning without background race conditions.

---

## 🎯 Research Objective

The primary objective of this project is to develop and evaluate a low-latency phishing detection mechanism that relies entirely on structural (lexical) features of a URL. 

**Key Goals:**
1. **Feature Alignment:** Ensure 100% synchronization of feature extraction logic between the offline model training pipeline and the real-time inference server.
2. **Privacy-Preserving:** Perform detection locally or via a controlled proxy without sending full page content or sensitive DOM data to external entities.
3. **High-Performance:** Achieve inference latency under 100ms per URL.

---

## 🧪 Methodology

### 1. Data Aggregation & Preprocessing
The model is trained on a proprietary dataset aggregated from three primary sources. The data undergoes rigorous deduplication and balancing to prevent class skew and overfitting.

### 2. Feature Engineering
The core of the detection mechanism relies on exactly **10 deterministic lexical features** extracted in a fixed, invariant order to guarantee alignment between training and serving:

1. `url_length`: Total length of the URL string.
2. `domain_length`: Total length of the extracted domain.
3. `path_length`: Total length of the URL path.
4. `qty_dot_domain`: Frequency of `.` in the domain.
5. `qty_hyphen_domain`: Frequency of `-` in the domain.
6. `qty_underline_domain`: Frequency of `_` in the domain.
7. `qty_digit_domain`: Count of numerical digits in the domain.
8. `has_at_symbol`: Binary flag for presence of `@` (credential passing).
9. `has_double_slash_path`: Binary flag for `//` in the path (redirects).
10. `is_punycode`: Binary flag for `xn--` (homograph attacks).

### 3. Model Architecture
- **Algorithm:** `RandomForestClassifier`
- **Hyperparameters:** 100 Estimators, Max Depth 15, Balanced Class Weights.
- **Training Time:** ~5-30 seconds (depending on hardware).
- **Inference Time:** 10-50ms.

---

## 🏗 System Architecture

The project is structured into three decoupled components to ensure scalability and ease of deployment.

```text
User Browser
    ↓
Chrome Extension (popup.js)  <-- [Manifest V3, On-Demand Execution]
    ↓ Click "Analyze URL" button
    ↓
POST /predict (http://127.0.0.1:5000)
    ↓
Flask Backend (app.py)       <-- [Feature Extraction & Inference API]
    ↓
extract_lexical_features()   <-- [Guaranteed 10-Feature Alignment]
    ↓
RandomForest Model           <-- [Loaded from .pkl]
    ↓
Prediction: {is_phishing, probability, status}
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Google Chrome (Version 90+)
- Python dependencies: `pandas`, `scikit-learn`, `joblib`, `flask`, `flask-cors`

### 1. Train the Model
Generate the Random Forest `.pkl` model by running the training pipeline.
```bash
cd model_training
python3 train_model.py
```
*Expected Output: A `phishing_rf_model.pkl` file (~5MB) generated in the directory.*

### 2. Start the Inference Server
Launch the Flask API backend to serve predictions.
```bash
cd extension_detector/backend
python3 app.py
```
*Expected Output: Server listening on `http://127.0.0.1:5000`.*

### 3. Load the Chrome Extension
1. Open Google Chrome and navigate to `chrome://extensions/`.
2. Toggle **Developer mode** (top right corner).
3. Click **Load unpacked**.
4. Select the `extension_detector/extension/` directory.
5. Pin the extension. Navigate to any website and click **"Analyze URL"** to test.

---

## 📡 API Specification

### Endpoint: `POST /predict`
Evaluates a URL and returns a phishing probability.

**Request:**
```json
{
  "url": "https://example.com"
}
```

**Response:**
```json
{
  "is_phishing": 0,
  "probability": 0.042,
  "status": "safe"
}
```

### Endpoint: `GET /health`
Validates the backend status and model readiness.

**Response:**
```json
{
  "status": "ok",
  "model_loaded": true
}
```

---

## 📊 Key Findings & System Performance

Extensive testing of the V2 pipeline yielded the following metrics:
- **Zero Race Conditions:** Migrating from background automated scanning to an on-demand manual click model resolved critical lifecycle bugs and `TypeError` exceptions.
- **Latency:** Complete roundtrip from extension click to UI update is consistently **<500ms**, with Flask processing taking **20-100ms**.
- **Robustness:** Strict enforcement of the 10-feature lexical array shapes between `train_model.py` and `app.py` eradicated previous inference feature-mismatch errors.

---

## 📚 Supplementary Documentation

This project contains over 100KB of comprehensive architectural and developmental documentation:

- [`00_READ_ME_FIRST.md`](00_READ_ME_FIRST.md): Master navigation and overview.
- [`ARCHITECTURE_GUIDE.md`](ARCHITECTURE_GUIDE.md): Detailed system design and flow diagrams.
- [`TECHNICAL_SPECIFICATION.md`](TECHNICAL_SPECIFICATION.md): Deep-dive into extraction and routing mechanics.
- [`FINAL_VALIDATION_CHECKLIST.md`](FINAL_VALIDATION_CHECKLIST.md): Quality assurance matrix.

---
*Developed as an applied research project in machine learning and cybersecurity.*
