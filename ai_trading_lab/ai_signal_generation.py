"""
AI Signal Generation Script
- Loads the trained classifier (rf_signal_classifier.joblib)
- Loads new weekly data with features (as produced by data_prep.py)
- Predicts entry/exit signals for the next week
- Outputs predictions as CSV (ai_signals.csv)
"""
import os
import glob
import pandas as pd
import joblib

# --- CONFIG ---
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'rf_signal_classifier.joblib')
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
OUTPUT_CSV = os.path.join(os.path.dirname(__file__), 'ai_signals.csv')
FEATURES = ['rsi_14', 'atr_21', 'sma_20', 'ema_20']

# --- LOAD MODEL ---
clf = joblib.load(MODEL_PATH)

# --- LOAD DATA ---
all_files = glob.glob(os.path.join(DATA_DIR, '*.csv'))
df_list = [pd.read_csv(f, index_col=0, parse_dates=True) for f in all_files]
df = pd.concat(df_list)
df = df.sort_index()

# --- PREDICT SIGNALS ---
latest_data = df.groupby('symbol').tail(1) if 'symbol' in df.columns else df.tail(len(all_files))
X_pred = latest_data[FEATURES]
preds = clf.predict(X_pred)
probs = clf.predict_proba(X_pred)[:,1]

# --- OUTPUT ---
latest_data = latest_data.copy()
latest_data['ai_signal'] = preds
latest_data['ai_signal_prob'] = probs

cols_to_save = ['ai_signal', 'ai_signal_prob'] + [c for c in latest_data.columns if c not in ['ai_signal','ai_signal_prob']]
latest_data[cols_to_save].to_csv(OUTPUT_CSV)
print(f"AI signals saved to {OUTPUT_CSV}")
