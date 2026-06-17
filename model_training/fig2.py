#!/usr/bin/env python3
"""
Real-time Inference Latency Evaluation Engine (fig2.py)
"""
import os
import time
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

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
# 2. STRATIFIED SAMPLING & MATRIX PREPARATION
# =====================================================================
print(f"[*] Dataset contains {len(master_df):,} rows. Sampling 20,000 stratified rows for benchmark pipeline...")

clean_df = master_df[FEATURE_COLUMNS + [target_col]].dropna()

# Manually slice safe and phishing pools to avoid index drops
safe_pool = clean_df[clean_df[target_col] == 0]
phish_pool = clean_df[clean_df[target_col] == 1]

# Sample up to 10k items per class
safe_sample = safe_pool.sample(n=min(len(safe_pool), 10000), random_state=42)
phish_sample = phish_pool.sample(n=min(len(phish_pool), 10000), random_state=42)

df_safe = pd.concat([safe_sample, phish_sample], axis=0).sample(frac=1, random_state=42).reset_index(drop=True)

X = df_safe[FEATURE_COLUMNS]
y = df_safe[target_col].astype(int)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# =====================================================================
# 3. INITIALIZE & TRAIN THE PROPOSED ARCHITECTURE
# =====================================================================
print("\n" + "="*50)
print("  EXECUTING PROPOSED RF TRAINING PHASE")
print("="*50)
print("[*] Training Random Forest (Proposed)...")

model = RandomForestClassifier(
    n_estimators=100, 
    max_depth=15, 
    class_weight='balanced', 
    random_state=42, 
    n_jobs=-1
)
model.fit(X_train, y_train)
print("[✓] Model training completed successfully.")

# =====================================================================
# 4. LATENCY TESTING BENCHMARK
# =====================================================================
print("\n" + "="*50)
print("  RUNNING BATCH SIZE INFERENCE LATENCY BENCHMARK")
print("="*50)

batch_sizes = [1, 10, 20, 50, 100]
latencies = []

for batch in batch_sizes:
    sample_batch = X_test[:batch]
    
    # Measure execution duration window precisely
    start = time.time()
    model.predict(sample_batch)
    end = time.time()
    
    latency = (end - start) * 1000  # Convert to milliseconds
    latencies.append(latency)
    print(f"    -> Batch Size: {batch:<3} | Latency: {latency:.2f} ms")

# =====================================================================
# 5. GENERATE HIGH-RESOLUTION VISUAL PLOT (PUBLICATION GRADE)
# =====================================================================
fig, ax = plt.subplots(figsize=(7.5, 5), dpi=300)

# Render line plot with professional accents
ax.plot(
    batch_sizes, 
    latencies, 
    marker='o', 
    linestyle='-', 
    color='#1f77b4', 
    linewidth=2, 
    markersize=7,
    label='Random Forest (Proposed)'
)

# Add precision data callout annotations at each coordinate vertex
for b, l in zip(batch_sizes, latencies):
    ax.annotate(
        f"{l:.1f}ms",
        xy=(b, l),
        xytext=(0, 8),  # 8 points vertical offset
        textcoords="offset points",
        ha='center',
        fontsize=9,
        fontweight='bold',
        bbox=dict(boxstyle="round,pad=0.2", fc="yellow", alpha=0.3, ec="orange", lw=0.5)
    )

# Labeling & Structure
ax.set_xlabel("Batch Size (Simultaneous Evaluated Request Payload)", fontsize=11, fontweight='bold', labelpad=10)
ax.set_ylabel("Inference Turnaround Overhead Latency (ms)", fontsize=11, fontweight='bold', labelpad=10)
ax.set_title("System Scalability Matrix: Latency vs. Request Batch Size", fontsize=12, fontweight='bold', pad=15)

# Design Elements: Setup subtle background grids
ax.set_axisbelow(True)
ax.grid(True, linestyle='--', alpha=0.5, color='#cccccc')

# Set specific X ticks to keep it readable
ax.set_xticks(batch_sizes)

plt.tight_layout()

# Save image file to your dedicated sub-folder
output_dir = os.path.join(bp, 'model_training')
os.makedirs(output_dir, exist_ok=True)
figure_path = os.path.join(output_dir, 'figure4_latency.png')

plt.savefig(figure_path, dpi=300, bbox_inches='tight')
print("\n" + "="*50)
print(f"[✓] SUCCESS: Latency scale graph generated and saved:\n    -> {figure_path}")
print("="*50 + "\n")
plt.show()