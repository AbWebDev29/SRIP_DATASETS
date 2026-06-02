#!/usr/bin/env python3
"""
ML Pipeline v4.0: 5 CSV Sources · 13 Lexical Features · Full-URL Feature Extraction · Balanced RF
────────────────────────────────────────────────────────────────────────────────
FIX: Training-Serving Feature Skew
  Previous versions dropped the original URL and extracted features from the
  domain string only, which collapsed path_length to 0 and qty_slash_url to 2
  for every legitimate row.  This version retains the full URL through the
  entire pipeline and extracts features from it, matching the serving path in
  backend/app.py exactly.
"""
import os, sys, re
import pandas as pd
import numpy as np
import joblib
from urllib.parse import urlparse
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

TRUSTED_SAFE_DOMAINS = [
    'google.com','apple.com','icloud.com','microsoft.com','outlook.com',
    'github.com','wikipedia.org','amazon.com','yahoo.com','facebook.com',
    'instagram.com','twitter.com','linkedin.com','reddit.com',
    'stackoverflow.com','medium.com','youtube.com','netflix.com',
    'dropbox.com','slack.com','zoom.us','openai.com','notion.so','figma.com',
]

FEATURE_COLUMNS = [
    'url_length','domain_length','path_length','qty_dot_domain',
    'qty_hyphen_domain','qty_underline_domain','qty_digit_domain',
    'has_at_symbol','has_double_slash_path','is_punycode',
    'qty_slash_url','qty_dot_url','has_http_in_path',
]

def is_trusted_domain(hostname):
    if not hostname: return False
    h = hostname.lower()
    for t in TRUSTED_SAFE_DOMAINS:
        if h == t or h.endswith('.' + t): return True
    return False

def extract_domain(url):
    if not url or not isinstance(url, str): return None
    url = url.strip().lower()
    if not url.startswith(('http://','https://','ftp://')): url = 'http://' + url
    try:
        d = urlparse(url).netloc.split(':')[0]
        return d if d else None
    except: return None

def extract_features(url):
    """Extract exactly 13 lexical features from a FULL URL.
    This function is identical to `extract_lexical_features` in backend/app.py
    so training and serving use the same feature vector."""
    if not url or not isinstance(url, str): return None
    url = url.strip().lower()
    if not url.startswith(('http://','https://','ftp://')): url = 'http://' + url
    try:
        p = urlparse(url); domain = p.netloc.split(':')[0]; path = p.path
        if not domain: return None
        return {
            'url_length': len(url),
            'domain_length': len(domain),
            'path_length': len(path),
            'qty_dot_domain': domain.count('.'),
            'qty_hyphen_domain': domain.count('-'),
            'qty_underline_domain': domain.count('_'),
            'qty_digit_domain': sum(c.isdigit() for c in domain),
            'has_at_symbol': int('@' in url),
            'has_double_slash_path': int('//' in path),
            'is_punycode': int('xn--' in domain),
            'qty_slash_url': url.count('/'),
            'qty_dot_url': url.count('.'),
            'has_http_in_path': int('http' in path.lower()),
        }
    except: return None

def auto_url_col(df):
    for c in df.columns:
        if c.strip().lower() in ('url','site','phish_url','domain','uri','link'): return c
    return df.columns[0]

def auto_label_col(df):
    for c in df.columns:
        if c.strip().lower() in ('label','status','class','classlabel','target'): return c
    return None

def norm_label(val):
    if isinstance(val,(int,float)): return int(val)
    s = str(val).strip().lower()
    if s in ('1','phishing','bad','malicious','unsafe','suspicious'): return 1
    if s in ('0','safe','good','benign','legitimate'): return 0
    try: return int(float(s))
    except: return None

# ─── DATA LOADERS ────────────────────────────────────────────────────────────
# Each loader now returns df[['url', 'domain', 'label']]
# 'url' = the full original URL string (used for feature extraction)
# 'domain' = extracted hostname (used for dedup & allowlist matching)
# If a source only has bare domains, 'url' is set = 'domain' as a safe fallback.

def load_generic(path):
    """Load a generic CSV with auto-detected URL and label columns."""
    try:
        df = pd.read_csv(path, on_bad_lines='skip')
        print(f"  Loaded {os.path.basename(path)}: {len(df)} rows")
        uc = auto_url_col(df)
        df['url'] = df[uc].astype(str).str.strip()
        df['domain'] = df['url'].apply(extract_domain)
        lc = auto_label_col(df)
        if lc:
            df['label'] = df[lc].apply(norm_label)
        else:
            fn = os.path.basename(path).lower()
            df['label'] = 1 if ('phish' in fn or 'phi' in fn or 'mal' in fn) else 0
        df = df.dropna(subset=['domain','label']); df['label'] = df['label'].astype(int)
        # Fallback: if the raw value looks like a bare domain (no slashes), copy domain→url
        df['url'] = df.apply(
            lambda r: r['domain'] if '/' not in str(r['url']).replace('http://','').replace('https://','').strip('/') else r['url'],
            axis=1
        )
        print(f"    → {len(df)} usable"); return df[['url','domain','label']]
    except Exception as e:
        print(f"  ERROR {path}: {e}"); return pd.DataFrame(columns=['url','domain','label'])

def load_saf_url(path):
    """Load saf_url.csv — index,domain format. Domains only; url = domain fallback."""
    try:
        df = pd.read_csv(path, header=None, names=['idx','raw'], on_bad_lines='skip')
        print(f"  Loaded saf_url.csv: {len(df)} rows")
        df['domain'] = df['raw'].apply(extract_domain)
        df['label'] = 0
        df = df.dropna(subset=['domain'])
        # saf_url only has bare domains → copy domain into url as fallback
        df['url'] = df['domain']
        print(f"    → {len(df)} usable"); return df[['url','domain','label']]
    except Exception as e:
        print(f"  ERROR {path}: {e}"); return pd.DataFrame(columns=['url','domain','label'])

def load_phi_url(path):
    """Load phi_url.csv — has full URLs in the first column."""
    try:
        df = pd.read_csv(path, on_bad_lines='skip')
        print(f"  Loaded phi_url.csv: {len(df)} rows")
        uc = auto_url_col(df)
        df['url'] = df[uc].astype(str).str.strip()
        df['domain'] = df['url'].apply(extract_domain)
        df['label'] = 1
        df = df.dropna(subset=['domain'])
        print(f"    → {len(df)} usable"); return df[['url','domain','label']]
    except Exception as e:
        print(f"  ERROR {path}: {e}"); return pd.DataFrame(columns=['url','domain','label'])

def main():
    print("="*60+"\n  PHISHING DETECTION: ML PIPELINE v4.0  (Full-URL Skew Fix)\n"+"="*60)
    bp = '/Users/anvibansal/SRIP'
    files = {
        'domain_dataset_10k.csv': load_generic,
        'phi_url.csv': load_phi_url,
        'saf_url.csv': load_saf_url,
        'phishing_data.csv': load_generic,
        'phishing_site_urls.csv': load_generic,
    }
    dfs = []
    print("\n--- PHASE 1: LOADING 5 CSV SOURCES ---")
    for fn, loader in files.items():
        p = os.path.join(bp, fn)
        if os.path.isfile(p): dfs.append(loader(p))
        else: print(f"  SKIP (missing): {fn}")

    combined = pd.concat(dfs, ignore_index=True)
    print(f"\n  Raw aggregated: {len(combined)}")
    combined = combined.drop_duplicates(subset=['domain'], keep='last')
    print(f"  After dedup: {len(combined)}")

    # --- ALLOWLIST OVERRIDE ---
    mask = combined['domain'].apply(is_trusted_domain)
    ov = int((combined.loc[mask,'label']!=0).sum())
    combined.loc[mask,'label'] = 0
    if ov: print(f"  Allowlist override: {ov} rows → label=0")

    print(f"  Label dist:\n{combined['label'].value_counts().to_string()}")
    if len(combined)>=15000: print(f"  ✓ Scale OK: {len(combined)} ≥ 15k")

    out_csv = os.path.join(bp, 'final_processed_dataset.csv')
    combined.to_csv(out_csv, index=False)
    print(f"\n--- PHASE 2: EXPORTED CLEAN DATASET → {out_csv} ({len(combined)} rows) ---")

    # ── PHASE 3: EXTRACT 13 FEATURES FROM FULL URL ─────────────────────────
    print("\n--- PHASE 3: EXTRACTING 13 FEATURES FROM FULL URLs & CREATING MASTER CSV ---")
    recs, labs, skip = [], [], 0
    for _, r in combined.iterrows():
        f = extract_features(r['url'])          # ← FIX: use full URL, not domain
        if f is None: skip+=1; continue
        f['domain_name'] = r['domain']  # Inject string index for master spreadsheet readability
        recs.append(f)
        labs.append(r['label'])
        
    # Build complete consolidated DataFrame
    master_features_df = pd.DataFrame(recs)
    master_features_df['label'] = labs
    
    # Re-order columns cleanly: domain identifier, then features, then final target label
    ordered_cols = ['domain_name'] + FEATURE_COLUMNS + ['label']
    master_features_df = master_features_df[ordered_cols]
    
    # 🚀 EXPORT: Save the full master matrix file (String IDs + Lexical Vectors + Binary Target Labels)
    out_master_csv = os.path.join(bp, 'master_features_dataset.csv')
    master_features_df.to_csv(out_master_csv, index=False)
    print(f"  ✓ SUCCESS: Master Features Matrix saved → {out_master_csv}")
    print(f"  Matrix Shape: {master_features_df.shape} (skipped {skip} bad structures)")

    # ── Sanity check: verify path_length and qty_slash_url are no longer collapsed ──
    safe_rows = master_features_df[master_features_df['label'] == 0]
    avg_path = safe_rows['path_length'].mean()
    avg_slash = safe_rows['qty_slash_url'].mean()
    print(f"\n  [SKEW CHECK] Safe-label rows → avg path_length={avg_path:.2f}, avg qty_slash_url={avg_slash:.2f}")
    if avg_path < 0.5 and avg_slash < 2.5:
        print("  ⚠  WARNING: path_length and qty_slash_url still look collapsed. Check your URL sources.")
    else:
        print("  ✓ Feature distributions look healthy — skew eliminated.")

    print("\n--- PHASE 4: TRAINING RF (balanced) ---")
    X = master_features_df[FEATURE_COLUMNS]
    y = master_features_df['label']
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    print(f"  Train Set Size: {len(Xtr)}  |  Test Set Size: {len(Xte)}")
    
    mdl = RandomForestClassifier(n_estimators=100, class_weight='balanced',
                                  random_state=42, n_jobs=-1, max_depth=15)
    mdl.fit(Xtr, ytr)
    print(f"  Train acc: {mdl.score(Xtr, ytr):.4f}")
    print(f"  Test acc:  {mdl.score(Xte, yte):.4f}")
    
    imp = sorted(zip(FEATURE_COLUMNS, mdl.feature_importances_), key=lambda x: -x[1])
    print("  Importances:")
    for n, v in imp: print(f"    {n:.<30s} {v:.4f}")

    # --- PHASE 5: EXPORT MODEL BINARY & WEIGHT RANKINGS ---
    out_pkl = os.path.join(bp, 'model_training', 'phishing_rf_model.pkl')
    os.makedirs(os.path.dirname(out_pkl), exist_ok=True)
    joblib.dump({'model': mdl, 'features': FEATURE_COLUMNS}, out_pkl)
    print(f"\n--- PHASE 5A: SAVED BINARY MODEL → {out_pkl} ---")

    out_model_csv = os.path.join(bp, 'model_training', 'phishing_rf_model_features.csv')
    importance_df = pd.DataFrame([
        {'rank': idx + 1, 'feature_name': name, 'weight_importance': weight}
        for idx, (name, weight) in enumerate(imp)
    ])
    importance_df.to_csv(out_model_csv, index=False)
    print(f"--- PHASE 5B: EXPORTED MODEL INSIGHTS CSV → {out_model_csv} ---")
    
    print("\n"+"="*60+"\n  ✓ TRAINING & ALL EXPORTS COMPLETE  (v4.0 — Skew Fixed)\n"+"="*60)

if __name__ == '__main__':
    main()