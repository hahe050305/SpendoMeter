"""
Stage 5 — Full Pipeline
Chains filter → extract → resolve into one function
"""
import joblib, re, json, sys, os

# ── FIX 1: Absolute path so it works when called from server.py ──
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'sms_filter_model.pkl')

# ── FIX 2: Add scripts/ to path so imports work ──
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from extract_fields   import extract_fields
from merchant_resolve import resolve_merchant   # FIX 3: removed "datasets.scripts." prefix

_pipeline = None

def load_model():
    global _pipeline
    if _pipeline is None:
        _pipeline = joblib.load(MODEL_PATH)
    return _pipeline

def preprocess(text):
    text = str(text).lower()
    text = re.sub(r'\b\d{10,}\b',                         'LONGNUM',  text)
    text = re.sub(r'(?:rs\.?|inr|₹)\s*[\d,]+(?:\.\d+)?', 'AMOUNT',   text)
    text = re.sub(r'\*{2}\d{4}|\*\*\d{4}|xx\d{4}',       'ACCTMASK', text)
    text = re.sub(r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b',  'DATE',     text)
    text = re.sub(r'[\w.\-]+@[a-z]+',                     'UPIID',    text)
    text = re.sub(r'https?://\S+',                         'URL',      text)
    return re.sub(r'\s+', ' ', text).strip()

def run(sms_body, sender=''):
    model      = load_model()
    processed  = preprocess(sms_body)
    prob       = model.predict_proba([processed])[0]
    label      = model.predict([processed])[0]
    confidence = round(float(max(prob)) * 100, 1)

    if label == 0:
        return {'is_transaction': False, 'confidence': confidence}

    fields = extract_fields(sms_body, sender)

    merchant, category = resolve_merchant(
        upi_id       = fields.get('upi_id'),
        merchant_raw = fields.get('merchant_raw'),
        sms_body     = sms_body,
    )

    return {
        'is_transaction': True,
        'confidence':     confidence,
        'txn_type':       fields['txn_type'],
        'amount':         fields['amount'],
        'bank':           fields['bank'],
        'account_last4':  fields['account_last4'],
        'upi_ref':        fields['upi_ref'],
        'upi_id':         fields['upi_id'],
        'merchant':       merchant,
        'category':       category,
        'date':           fields['date'],
        'raw_sms':        sms_body[:120],
    }

if __name__ == '__main__':
    test_sms = [
        ("HDFC Bank: Rs 400.80 debited from a/c **2823 on 25-07-23 to VPA bookmyshow@axb UPI Ref No 320605383121. Not you? Call 18002586161", "AX-HDFCBK"),
        ("Amt Sent Rs.106.90 From HDFC Bank A/C *2823 To NSDL BILLDESK On 21-04 Ref 411291768471", "AX-HDFCBK"),
        ("UPI LITE Top-up amounting to Rs.200.00 successful. Ref No 526600106661 - HDFC Bank",      "AX-HDFCBK"),
        ("SURPRISE!!! MicroCourse Flash Rs.1 Sale is LIVE! Hey HARISH, Get Vedantu MicroCourse",    "BT-VDNATU"),
        ("Your OTP is 847291. Valid 10 mins. Do not share.",                                         "AD-HDFCBK"),
    ]
    print("="*60)
    for sms, sender in test_sms:
        result = run(sms, sender)
        print(json.dumps(result, indent=2))
        print("-"*60)