#!/usr/bin/env python3
"""
Random Forest Estimator Scaling & Training Overhead Analysis Engine (fig3.py)
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
# 3. RUN ESTIMATOR OVERHEAD BENCHMARK
# =====================================================================
print("\n" + "="*50)
print("  EXECUTING TRAINING SCALABILITY OVERHEAD BENCHMARK")
print("="*50)

tree_counts = [50, 100, 150, 200, 250, 300]
training_times = []

for t in tree_counts:
    print(f"[*] Training Random Forest Architecture with n_estimators={t}...")
    model = RandomForestClassifier(
        n_estimators=t, 
        max_depth=15,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1  # Accelerate using all available core threads
    )
    
    # Isolate training timer sequence
    start = time.time()
    model.fit(X_train, y_train)
    end = time.time()
    
    elapsed_time = end - start
    training_times.append(elapsed_time)
    print(f"    -> Complete! Execution overhead: {elapsed_time:.3f} seconds\n")

# =====================================================================
# 4. GENERATE HIGH-RESOLUTION VISUAL PLOT (PUBLICATION GRADE)
# =====================================================================
fig, ax = plt.subplots(figsize=(7.5, 5), dpi=300)

# Render scalability trajectory line using distinct styling
ax.plot(
    tree_counts, 
    training_times, 
    marker='o', 
    linestyle='-', 
    color='#2ca02c',  # Distinct forest green accent
    linewidth=2, 
    markersize=7,
    label='Training Pipeline Cost'
)

# Render numeric calculation values cleanly adjacent to each coordinate vertex
for t, duration in zip(tree_counts, training_times):
    ax.annotate(
        f"{duration:.2f}s",
        xy=(t, duration),
        xytext=(0, 8),  # 8 points vertical offset positioning
        textcoords="offset points",
        ha='center',
        fontsize=9,
        fontweight='bold',
        bbox=dict(boxstyle="round,pad=0.2", fc="#e1f5fe", alpha=0.4, ec="#b3e5fc", lw=0.5)
    )

# Labeling, Margins & Layout Hierarchy
ax.set_xlabel("Number of Decision Trees ($n\_estimators$)", fontsize=11, fontweight='bold', labelpad=10)
ax.set_ylabel("Total Training Execution Overhead (seconds)", fontsize=11, fontweight='bold', labelpad=10)
ax.set_title("Architecture Computational Complexity: Training Time vs. Tree Density", fontsize=12, fontweight='bold', pad=15)

# Design Elements: Render background structural grids
ax.set_axisbelow(True)
ax.grid(True, linestyle='--', alpha=0.5, color='#cccccc')

# Explicitly map the evaluated intervals to the X-Axis ticks
ax.set_xticks(tree_counts)

# Smooth graph margins
plt.tight_layout()

# Save finalized diagram asset
output_dir = os.path.join(bp, 'model_training')
os.makedirs(output_dir, exist_ok=True)
figure_path = os.path.join(output_dir, 'figure5_training.png')

plt.savefig(figure_path, dpi=300, bbox_inches='tight')
print("="*50)
print(f"[✓] SUCCESS: Tree density scalability graph generated and saved:\n    -> {figure_path}")
print("="*50 + "\n")
plt.show()