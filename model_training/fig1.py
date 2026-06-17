#!/usr/bin/env python3
"""
Performance Evaluation Matrix Benchmark Engine (fig1.py) - Bulletproof Index Fix
"""
import os
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.naive_bayes import GaussianNB

# =====================================================================
# 1. LOAD MASTER DATASET & AUTO-DETECT COLUMNS
# =====================================================================
bp = '/Users/anvibansal/SRIP'
master_csv_path = os.path.join(bp, 'master_features_dataset.csv')

if not os.path.exists(master_csv_path):
    print(f"[-] ERROR: Could not find master file at: {master_csv_path}")
    print("    Please run your main training pipeline script first to generate this master CSV.")
    exit(1)

print("[*] Loading master features dataset...")
master_df = pd.read_csv(master_csv_path)

# Clean column names (strip whitespace and convert to lowercase)
master_df.columns = [c.strip().lower() for c in master_df.columns]

# Auto-detect target classification column matching our variations
target_col = None
for c in master_df.columns:
    if c in ('label', 'status', 'class', 'classlabel', 'target'):
        target_col = c
        break

if not target_col:
    target_col = master_df.columns[-1]
    print(f"[!] Warning: Explicit 'label' header wasn't found. Falling back to final column: '{target_col}'")
else:
    print(f"[✓] Detected target label column: '{target_col}'")

# Standardize the 13 canonical features
FEATURE_COLUMNS = [
    'url_length', 'domain_length', 'path_length', 'qty_dot_domain',
    'qty_hyphen_domain', 'qty_underline_domain', 'qty_digit_domain',
    'has_at_symbol', 'has_double_slash_path', 'is_punycode',
    'qty_slash_url', 'qty_dot_url', 'has_http_in_path'
]
FEATURE_COLUMNS = [f.strip().lower() for f in FEATURE_COLUMNS]

# =====================================================================
# 2. BULLETPROOF STRATIFIED SAMPLING (BYPASSES PANDAS GROUPBY BUG)
# =====================================================================
print(f"[*] Dataset contains {len(master_df):,} rows. Extracting 20,000 stratified rows to prevent SVM freeze...")

# Isolate columns cleanly and drop rows with missing values
clean_df = master_df[FEATURE_COLUMNS + [target_col]].dropna()

# Manually slice safe and phishing components to avoid index drops
safe_pool = clean_df[clean_df[target_col] == 0]
phish_pool = clean_df[clean_df[target_col] == 1]

# Extract up to 10,000 rows from each class safely
safe_sample = safe_pool.sample(n=min(len(safe_pool), 10000), random_state=42)
phish_sample = phish_pool.sample(n=min(len(phish_pool), 10000), random_state=42)

# Concatenate them back together into a clean, flat dataframe
df_safe = pd.concat([safe_sample, phish_sample], axis=0).sample(frac=1, random_state=42).reset_index(drop=True)

# Separate features (X) and labels (y) directly from the stable sampled frame
X = df_safe[FEATURE_COLUMNS]
y = df_safe[target_col].astype(int)

# Create stratified train/test matrices from the stable sample
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"    -> Subsampled matrices generated. Train shape: {X_train.shape}, Test shape: {X_test.shape}")

# =====================================================================
# 3. INITIALIZE & RUN COMPARATIVE BENCHMARK
# =====================================================================
models = {
    "Random Forest (Proposed)": RandomForestClassifier(
        n_estimators=100, 
        max_depth=15, 
        class_weight='balanced', 
        random_state=42, 
        n_jobs=-1
    ),
    "SVM (RBF)": SVC(
        kernel='rbf', 
        class_weight='balanced', 
        random_state=42
    ),
    "Naive Bayes": GaussianNB()
}

accuracy_scores = []

print("\n" + "="*50)
print("  EXECUTING COMPARATIVE INFERENCE BENCHMARK")
print("="*50)

for name, model in models.items():
    print(f"[*] Training model target: {name}...")
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred) * 100
    accuracy_scores.append(acc)
    print(f"    -> Test Accuracy: {acc:.2f}%\n")

# =====================================================================
# 4. GENERATE HIGH-RESOLUTION VISUAL GRAPH (PUBLICATION GRADE)
# =====================================================================
fig, ax = plt.subplots(figsize=(7.5, 5), dpi=300)

# Stylized Contrast Layout: Proposed architecture stands out in blue
bar_colors = ['#1f77b4', '#7f7f7f', '#a6a6a6']
model_labels = list(models.keys())

bars = ax.bar(
    model_labels, 
    accuracy_scores, 
    color=bar_colors, 
    width=0.55, 
    edgecolor='black', 
    linewidth=0.8
)

# Typography Labels & Margins
ax.set_xlabel("Classification Architecture Baseline", fontsize=11, fontweight='bold', labelpad=10)
ax.set_ylabel("Inference Classification Accuracy (%)", fontsize=11, fontweight='bold', labelpad=10)
ax.set_title("Empirical Accuracy Performance Comparison Matrix", fontsize=12, fontweight='bold', pad=15)

# Crop graph base layout to clearly contrast subtle efficiency gaps
min_score = min(accuracy_scores)
ax.set_ylim(max(0, min_score - 15), 105)

# Render subtle cross-grid lines behind the bars
ax.set_axisbelow(True)
ax.yaxis.grid(True, linestyle='--', alpha=0.6, color='#cccccc')

# Stamp precision calculation data labels directly on top of each bar
for bar in bars:
    height = bar.get_height()
    ax.annotate(
        f"{height:.2f}%",
        xy=(bar.get_x() + bar.get_width() / 2, height),
        xytext=(0, 4),  
        textcoords="offset points",
        ha='center', 
        va='bottom', 
        fontsize=10, 
        fontweight='bold'
    )

plt.xticks(rotation=15, ha='right', fontsize=10)
plt.yticks(fontsize=10)
plt.tight_layout()

# Save final graphic to model_training subdirectory
output_dir = os.path.join(bp, 'model_training')
os.makedirs(output_dir, exist_ok=True)
figure_path = os.path.join(output_dir, 'figure3_accuracy.png')

plt.savefig(figure_path, dpi=300, bbox_inches='tight')
print("="*50)
print(f"[✓] SUCCESS: Comparative chart generated and saved:\n    -> {figure_path}")
print("="*50+"\n")
plt.show()