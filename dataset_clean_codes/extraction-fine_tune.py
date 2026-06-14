import pandas as pd
import re
import os
import json
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIG — update paths if yours differ
# ─────────────────────────────────────────────
INPUT_FILE  = 'datasets/sms_transactions_review.csv'
ALL_FILE    = 'datasets/sms_raw_all.csv'
OUTPUT_FILE = 'datasets/sms_labelled_clean.csv'
REPORT_FILE = 'datasets/cleaning_report.txt'

# ─────────────────────────────────────────────
# BANK SENDER ID REGISTRY
# Indian DLT-registered bank sender IDs
# ─────────────────────────────────────────────
BANK_SENDER_MAP = {
    'hdfcbk': 'HDFC',
    'sbiinb': 'SBI',
    'sbi':    'SBI',
    'icicib': 'ICICI',
    'icici':  'ICICI',
    'axisbk': 'Axis',
    'axis':   'Axis',
    'kotakb': 'Kotak',
    'kotak':  'Kotak',
    'canbnk': 'Canara',
    'pnbsms': 'PNB',
    'pnb':    'PNB',
    'boiind': 'BOI',
    'centbk': 'Central Bank',
    'idbibn': 'IDBI',
    'idbi':   'IDBI',
    'yesbnk': 'Yes Bank',
    'idfcbk': 'IDFC',
    'idfc':   'IDFC',
    'rblbnk': 'RBL',
    'indusb': 'IndusInd',
    'paytmb': 'Paytm',
    'paytm':  'Paytm',
    'aubank': 'AU Bank',
    'scbnk':  'Standard Chartered',
    'hsbc':   'HSBC',
    'citi':   'Citibank',
    'bobaroda': 'Bank of Baroda',
    'baroda': 'Bank of Baroda',
    'unionbk': 'Union Bank',
    'syndbk': 'Syndicate Bank',
    'fedbk':  'Federal Bank',
    'federal': 'Federal Bank',
    'tmbank': 'Tamilnad Mercantile',
    'kvbank': 'Karur Vysya',
    'lvbank': 'Lakshmi Vilas',
    'dbs':    'DBS',
    'ucobnk': 'UCO Bank',
}

# ─────────────────────────────────────────────
# SPAM SENDER PATTERNS — always false positive
# ─────────────────────────────────────────────
SPAM_SENDER_PATTERNS = [
    'vedantu', 'byjus', 'byju', 'unacad', 'toppr',
    'dream11', 'rummy', 'poker', 'casino', 'betway',
    'myntra', 'flipkrt', 'amazon', 'meesho',
    'zomato', 'swiggy', 'dunzo',   # as senders = marketing, not txn
    'naukri', 'shine', 'monster',
    'jiooff', 'airtel', 'vodafone', 'voda', 'bsnl',  # telecom promo
    'irctc',   # IRCTC as sender = booking confirm, not bank txn
    'info', 'alert', 'promo', 'offer', 'deals',
]

# ─────────────────────────────────────────────
# STRONG TRANSACTION KEYWORDS
# At least one must be present in the SMS body
# ─────────────────────────────────────────────
STRONG_TXN_KEYWORDS = [
    'debited', 'credited',
    'debit alert', 'credit alert',
    'a/c xx', 'ac xx', 'acct xx', 'account ending',
    'upi ref', 'upi/ref', 'upi txn',
    'neft ref', 'imps ref', 'txn ref', 'ref no',
    'withdrawn from', 'transfer to', 'transfer of',
    'payment of rs', 'payment of inr', 'payment of ₹',
    'paid to', 'paid via',
    'your a/c', 'your ac',
    'sent rs', 'sent inr',
    'received rs', 'received inr',
    'purchase of',
    'emi of',
    'balance is rs', 'avl bal',
]

# Keywords that disqualify a message immediately
DISQUALIFY_KEYWORDS = [
    'otp', 'one time password', 'verification code',
    'do not share', 'never share',
    'sale is calling', 'flash sale', 'limited offer',
    'click here', 'download now', 'install app',
    'win cash', 'earn cash', 'bonus cash',
    'course at rs', 'course @ rs',
    'guess what', 'exciting offer',
    'congratulations you', 'you have won',
]

# ─────────────────────────────────────────────
# AMOUNT PATTERNS
# ─────────────────────────────────────────────
AMOUNT_PATTERNS = [
    r'(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d{1,2})?)',
    r'([\d,]+(?:\.\d{1,2})?)\s*(?:rs\.?|inr|₹)',
    r'amount[:\s]+(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d{1,2})?)',
    r'for\s+(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d{1,2})?)',
]

# ─────────────────────────────────────────────
# EXTRACTION FUNCTIONS
# ─────────────────────────────────────────────

def detect_bank(sender, body):
    sender = str(sender).lower()
    body   = body.lower()
    for code, name in BANK_SENDER_MAP.items():
        if code in sender:
            return name
    # Fallback: search body for bank names
    for code, name in BANK_SENDER_MAP.items():
        if name.lower() in body:
            return name
    return 'Unknown'


def extract_amount(body):
    body_lower = body.lower()
    for pattern in AMOUNT_PATTERNS:
        match = re.search(pattern, body_lower)
        if match:
            raw = match.group(1).replace(',', '')
            try:
                amount = float(raw)
                # Filter out junk: Rs.1 course ads etc.
                if amount < 1 or amount > 10000000:
                    continue
                return amount
            except:
                continue
    return None


def extract_txn_type(body):
    body_lower = body.lower()
    debit_words  = ['debit', 'debited', 'withdrawn', 'paid', 'payment',
                    'purchase', 'sent', 'transfer to', 'emi deducted']
    credit_words = ['credit', 'credited', 'received', 'refund',
                    'cashback', 'transfer from', 'deposit']
    for w in debit_words:
        if w in body_lower:
            return 'debit'
    for w in credit_words:
        if w in body_lower:
            return 'credit'
    return 'unknown'


def extract_account_last4(body):
    patterns = [
        r'a/?c\s*[xX*]+(\d{4})',
        r'account\s*[xX*]+(\d{4})',
        r'ac\s*[xX*]+(\d{4})',
        r'acct\s*[xX*]+(\d{4})',
        r'ending\s+(?:with\s+)?(\d{4})',
        r'no\.\s*[xX*]+(\d{4})',
    ]
    for p in patterns:
        m = re.search(p, body, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def extract_upi_ref(body):
    patterns = [
        r'upi\s*ref\s*(?:no\.?)?[:\s]*(\d{8,})',
        r'ref\s*no\.?[:\s]*(\d{8,})',
        r'ref#?[:\s]*(\d{8,})',
        r'txn\s*(?:id|ref)?[:\s]*(\d{8,})',
        r'transaction\s*(?:id|ref)?[:\s]*(\d{8,})',
    ]
    for p in patterns:
        m = re.search(p, body, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def extract_upi_id(body):
    # UPI VPA pattern: something@bankcode
    m = re.search(r'[\w.\-]+@[a-z]+', body, re.IGNORECASE)
    return m.group(0) if m else None


def extract_merchant_raw(body):
    """
    Try to pull merchant name from common SMS patterns.
    E.g. "paid to SWIGGY" or "to VPA swiggy@icici"
    """
    patterns = [
        r'paid\s+to\s+([A-Za-z0-9 ]{3,30})',
        r'to\s+vpa\s+([\w.\-]+@[a-z]+)',
        r'at\s+([A-Z][A-Za-z0-9 ]{2,25})\s+on',
        r'to\s+([A-Z][A-Za-z ]{2,20})\s+(?:via|ref|upi)',
        r'for\s+([A-Z][A-Za-z ]{2,20})\s+(?:purchase|order)',
    ]
    for p in patterns:
        m = re.search(p, body, re.IGNORECASE)
        if m:
            raw = m.group(1).strip()
            if len(raw) > 2:
                return raw
    return None


def extract_date(body, fallback_date=None):
    patterns = [
        r'(\d{2}[-/]\d{2}[-/]\d{4})',
        r'(\d{2}[-/]\d{2}[-/]\d{2})',
        r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})',
    ]
    for p in patterns:
        m = re.search(p, body, re.IGNORECASE)
        if m:
            return m.group(1)
    return fallback_date


# ─────────────────────────────────────────────
# CLASSIFIER — is this a genuine transaction?
# ─────────────────────────────────────────────

def classify_transaction(row):
    body   = str(row.get('body', '')).lower()
    sender = str(row.get('address', '')).lower()

    # Hard disqualify — spam senders
    if any(s in sender for s in SPAM_SENDER_PATTERNS):
        return 0, 'spam_sender'

    # Hard disqualify — body contains disqualifying phrases
    if any(kw in body for kw in DISQUALIFY_KEYWORDS):
        return 0, 'disqualify_keyword'

    # Must contain at least one strong transaction keyword
    has_strong = any(kw in body for kw in STRONG_TXN_KEYWORDS)
    if not has_strong:
        return 0, 'no_strong_keyword'

    # Must have a valid amount (not just Rs.1 type junk)
    amount = extract_amount(str(row.get('body', '')))
    if amount is None:
        return 0, 'no_valid_amount'
    if amount < 5:
        return 0, 'amount_too_small'

    # Must be from a known bank sender OR body has bank ref keywords
    is_bank = any(code in sender for code in BANK_SENDER_MAP.keys())
    has_ref = any(kw in body for kw in ['upi ref', 'neft ref', 'imps ref',
                                          'ref no', 'txn id', 'transaction id'])
    if not is_bank and not has_ref:
        return 0, 'no_bank_sender_or_ref'

    return 1, 'genuine_transaction'


# ─────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────

def main():
    report_lines = []
    report_lines.append(f"SMS Dataset Cleaning Report")
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("=" * 60)

    # Load input
    if not os.path.exists(INPUT_FILE):
        print(f"ERROR: {INPUT_FILE} not found.")
        print("Make sure you ran the extraction script first.")
        return

    df = pd.read_csv(INPUT_FILE)
    original_count = len(df)
    report_lines.append(f"Input rows loaded     : {original_count}")

    # Standardise column names (handle slight variations)
    df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
    body_col    = next((c for c in df.columns if 'body' in c), None)
    address_col = next((c for c in df.columns if 'address' in c or 'sender' in c), None)
    date_col    = next((c for c in df.columns if 'date' in c), None)

    if not body_col:
        print("ERROR: Could not find SMS body column. Check your CSV column names.")
        return

    df = df.rename(columns={
        body_col:    'body',
        address_col: 'address',
    })

    if date_col and date_col not in ['body', 'address']:
        df = df.rename(columns={date_col: 'raw_date'})

    # Drop rows with empty body
    df = df.dropna(subset=['body'])
    df['body'] = df['body'].astype(str).str.strip()
    df = df[df['body'].str.len() > 10]

    # Run classifier on every row
    results = df.apply(classify_transaction, axis=1)
    df['is_transaction'] = [r[0] for r in results]
    df['rejection_reason'] = [r[1] for r in results]

    # Split
    txn_df    = df[df['is_transaction'] == 1].copy()
    nontxn_df = df[df['is_transaction'] == 0].copy()

    report_lines.append(f"Genuine transactions  : {len(txn_df)}")
    report_lines.append(f"Rejected (non-txn)    : {len(nontxn_df)}")
    report_lines.append("")

    # Rejection breakdown
    report_lines.append("Rejection reasons:")
    reason_counts = nontxn_df['rejection_reason'].value_counts()
    for reason, count in reason_counts.items():
        report_lines.append(f"  {reason:<30} {count}")
    report_lines.append("")

    # Run extraction on genuine transactions
    print(f"Extracting fields from {len(txn_df)} transaction SMS...")

    txn_df['amount']        = txn_df['body'].apply(extract_amount)
    txn_df['txn_type']      = txn_df['body'].apply(extract_txn_type)
    txn_df['bank']          = txn_df.apply(lambda r: detect_bank(r.get('address',''), r['body']), axis=1)
    txn_df['account_last4'] = txn_df['body'].apply(extract_account_last4)
    txn_df['upi_ref']       = txn_df['body'].apply(extract_upi_ref)
    txn_df['upi_id']        = txn_df['body'].apply(extract_upi_id)
    txn_df['merchant_raw']  = txn_df['body'].apply(extract_merchant_raw)
    txn_df['date_extracted'] = txn_df['body'].apply(extract_date)

    # Extraction coverage stats
    report_lines.append("Extraction coverage (out of genuine transactions):")
    fields = ['amount', 'txn_type', 'bank', 'account_last4', 'upi_ref', 'upi_id', 'merchant_raw']
    for f in fields:
        filled = txn_df[f].notna().sum()
        pct    = round(filled / len(txn_df) * 100, 1) if len(txn_df) > 0 else 0
        report_lines.append(f"  {f:<20} {filled}/{len(txn_df)} ({pct}%)")
    report_lines.append("")

    # Build final labelled dataset
    # Include both transaction + non-transaction rows for classifier training
    # Non-txn rows get NaN for extraction fields

    final_cols = ['body', 'address', 'is_transaction',
                  'txn_type', 'amount', 'bank',
                  'account_last4', 'upi_ref', 'upi_id',
                  'merchant_raw', 'date_extracted', 'rejection_reason']

    # Add missing columns to nontxn_df
    for col in ['txn_type', 'amount', 'bank', 'account_last4',
                'upi_ref', 'upi_id', 'merchant_raw', 'date_extracted']:
        nontxn_df[col] = None

    final_df = pd.concat([txn_df[final_cols], nontxn_df[final_cols]], ignore_index=True)
    final_df = final_df.sort_values('is_transaction', ascending=False).reset_index(drop=True)

    # Save
    os.makedirs('datasets', exist_ok=True)
    final_df.to_csv(OUTPUT_FILE, index=False)

    # Also save a separate clean transactions-only file for extraction model training
    txn_only = txn_df[final_cols].reset_index(drop=True)
    txn_only.to_csv('datasets/sms_transactions_clean.csv', index=False)

    report_lines.append(f"Output files saved:")
    report_lines.append(f"  {OUTPUT_FILE}               ← full labelled dataset (use for classifier training)")
    report_lines.append(f"  datasets/sms_transactions_clean.csv  ← transactions only (use for extraction model)")
    report_lines.append("")

    # Sample preview
    report_lines.append("Sample genuine transactions found:")
    report_lines.append("-" * 60)
    for _, row in txn_df.head(5).iterrows():
        report_lines.append(f"BODY    : {str(row['body'])[:80]}")
        report_lines.append(f"BANK    : {row['bank']}  |  TYPE: {row['txn_type']}  |  AMOUNT: {row['amount']}")
        report_lines.append(f"UPI REF : {row['upi_ref']}  |  MERCHANT: {row['merchant_raw']}")
        report_lines.append("")

    # Write report
    report_text = "\n".join(report_lines)
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(report_text)

    # Print summary to terminal
    print("\n" + "=" * 60)
    print("CLEANING COMPLETE")
    print("=" * 60)
    print(f"Total input SMS        : {original_count}")
    print(f"Genuine transactions   : {len(txn_df)}")
    print(f"Non-transactions       : {len(nontxn_df)}")
    print(f"\nOutput saved to        : {OUTPUT_FILE}")
    print(f"Transactions only      : datasets/sms_transactions_clean.csv")
    print(f"Full report            : {REPORT_FILE}")
    print("=" * 60)
    print("\nNext step: open data/sms_transactions_clean.csv")
    print("Review 10-20 rows manually to verify extraction accuracy.")
    print("Then come back to train the filter model.")


if __name__ == '__main__':
    main()