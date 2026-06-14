"""
Stage 2 — Train SMS Transaction Filter Model
Input : data/sms_labelled_clean.csv
Output: models/sms_filter_model.pkl
"""

import pandas as pd
import numpy as np
import joblib, os, re
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

INPUT_FILE   = 'sms_labelled_clean.csv'
MODEL_OUTPUT = 'sms_filter_model.pkl'

# ── PREPROCESSING ──────────────────────────────────────────
def preprocess(text):
    text = str(text).lower()
    text = re.sub(r'\b\d{10,}\b',                        'LONGNUM',  text)
    text = re.sub(r'(?:rs\.?|inr|₹)\s*[\d,]+(?:\.\d+)?','AMOUNT',   text)
    text = re.sub(r'\*{2}\d{4}|\*\*\d{4}|xx\d{4}',      'ACCTMASK', text)
    text = re.sub(r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b', 'DATE',     text)
    text = re.sub(r'[\w.\-]+@[a-z]+',                    'UPIID',    text)
    text = re.sub(r'https?://\S+',                        'URL',      text)
    text = re.sub(r'\s+',                                 ' ',        text).strip()

    # Add inside preprocess(), after the existing lines:
    text = re.sub(r'aval bal', 'avl bal', text)
    text = re.sub(r'\bac\s+xx', 'a/c xx', text)   # normalise "Ac XX" → "a/c xx"
    return text


# ── LOAD ───────────────────────────────────────────────────
df = pd.read_csv(INPUT_FILE)
df = df.dropna(subset=['body', 'is_transaction'])
df['is_transaction'] = df['is_transaction'].astype(int)
df['processed']      = df['body'].apply(preprocess)

print(f"Dataset: {len(df)} rows")
print(f"  Transactions     : {df['is_transaction'].sum()}")
print(f"  Non-transactions : {(df['is_transaction']==0).sum()}\n")

X = df['processed']
y = df['is_transaction']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# ── MODEL ──────────────────────────────────────────────────
pipeline = Pipeline([
    ('tfidf', TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=3000,
        sublinear_tf=True,
        min_df=2,
    )),
    ('clf', LogisticRegression(
        max_iter=1000,
        C=1.0,
        class_weight='balanced'
    ))
])

pipeline.fit(X_train, y_train)

# ── EVALUATE ───────────────────────────────────────────────
y_pred    = pipeline.predict(X_test)
acc       = accuracy_score(y_test, y_pred)
cv_scores = cross_val_score(pipeline, X, y, cv=5, scoring='f1')
cm        = confusion_matrix(y_test, y_pred)
report    = classification_report(
                y_test, y_pred,
                target_names=['Non-Transaction','Transaction'])

print(f"{'='*50}")
print(f"TEST ACCURACY  : {acc*100:.1f}%")
print(f"CROSS-VAL F1   : {cv_scores.mean()*100:.1f}% ± {cv_scores.std()*100:.1f}%")
print(f"{'='*50}\n")
print(report)
print("Confusion Matrix:")
print(f"  True Neg  (spam correctly blocked)  : {cm[0][0]}")
print(f"  False Pos (spam passed as txn)      : {cm[0][1]}")
print(f"  False Neg (real txn missed)         : {cm[1][0]}")
print(f"  True Pos  (real txn caught)         : {cm[1][1]}")

# ── TOP FEATURES ───────────────────────────────────────────
print("\nTop 12 words → TRANSACTION:")
feat   = pipeline.named_steps['tfidf'].get_feature_names_out()
coefs  = pipeline.named_steps['clf'].coef_[0]
top_t  = np.argsort(coefs)[-12:][::-1]
for i in top_t:
    print(f"  {feat[i]:<28} {coefs[i]:+.3f}")

print("\nTop 12 words → NOT TRANSACTION:")
top_nt = np.argsort(coefs)[:12]
for i in top_nt:
    print(f"  {feat[i]:<28} {coefs[i]:+.3f}")

# ── SAVE ───────────────────────────────────────────────────
os.makedirs('models', exist_ok=True)
joblib.dump(pipeline, MODEL_OUTPUT)
print(f"\nModel saved → {MODEL_OUTPUT}")

# ── LIVE TEST ──────────────────────────────────────────────
print("\n--- Live Test ---")
samples = [
    ("HDFC Bank: Rs 400.80 debited from a/c **2823 on 25-07-23 to VPA bookmyshow@axb UPI Ref No 320605383121",  "TRANSACTION"),
    ("UPI LITE Top-up amounting to Rs.200.00 has been successful. Ref No 530000934769 - HDFC Bank",             "TRANSACTION"),
    ("Ac XX3035 Debited with Rs.500000.00, 27-11-2025. Aval Bal Rs.20000.00 CR. Helpline 18001800 - PNB",       "TRANSACTION"),
    ("SURPRISE!!! MicroCourse Flash Rs. 1 Sale is LIVE! Hey HARISH, Get Vedantu MicroCourse @ just Rs. 1",      "NOT TRANSACTION"),
    ("Your OTP for login is 847291. Valid for 10 mins. Do not share with anyone.",                               "NOT TRANSACTION"),
    ("Dear 99443420XX, Get Rs.5500 in Your Rummy Account. Welcome Bonus!",                                       "NOT TRANSACTION"),
]

all_correct = True
for sms, expected in samples:
    pred  = pipeline.predict([preprocess(sms)])[0]
    prob  = pipeline.predict_proba([preprocess(sms)])[0]
    label = 'TRANSACTION' if pred == 1 else 'NOT TRANSACTION'
    ok    = '✓' if label == expected else '✗'
    if label != expected: all_correct = False
    print(f"  {ok} [{label}] {int(max(prob)*100)}%  {sms[:65]}...")

print(f"\n{'All live tests passed ✓' if all_correct else 'Some tests failed — check dataset labels'}")
print("\nNext: run 03_extract_fields.py")