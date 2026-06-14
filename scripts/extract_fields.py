"""
Stage 3 — Field Extractor
Takes a raw SMS string → returns structured dict
"""
import re

# ── PATTERNS ───────────────────────────────────────────────
AMOUNT_PATTERNS = [
    r'rs\.?\s*([\d,]+(?:\.\d{1,2})?)',
    r'inr\s*([\d,]+(?:\.\d{1,2})?)',
    r'₹\s*([\d,]+(?:\.\d{1,2})?)',
    r'amount(?:ing)?\s+(?:of\s+)?rs\.?\s*([\d,]+(?:\.\d{1,2})?)',
    r'([\d,]+(?:\.\d{1,2})?)\s*(?:rs|inr)',
]

ACCOUNT_PATTERNS = [
    r'a/?c\s*[*xX]{2,}\s*(\d{4})',
    r'account\s*[*xX]+(\d{4})',
    r'ac\s+xx(\d{4})',
    r'ending\s+(?:with\s+)?(\d{4})',
    r'no\.\s*[*xX]+(\d{4})',
]

UPI_REF_PATTERNS = [
    r'upi\s*ref\s*(?:no\.?)?\s*[:\s]*(\d{8,})',
    r'ref\s*no\.?\s*[:\s]*(\d{8,})',
    r'ref#?\s*(\d{8,})',
    r'txn\s*(?:id|ref)?\s*[:\s]*(\d{8,})',
]

DATE_PATTERNS = [
    r'(\d{2}[-/]\d{2}[-/]\d{4})',
    r'(\d{2}[-/]\d{2}[-/]\d{2})\b',
    r'(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{2,4})',
]

DEBIT_WORDS  = ['debited','debit','withdrawn','paid','sent',
                'transfer to','purchase','top-up','top up','emi']
CREDIT_WORDS = ['credited','credit','received','refund',
                'cashback','transfer from','deposit','added']

BANK_SENDER_MAP = {
    'hdfcbk':'HDFC',  'sbiinb':'SBI',   'sbi':'SBI',
    'icicib':'ICICI', 'icici':'ICICI',  'axisbk':'Axis',
    'kotakb':'Kotak', 'pnbsms':'PNB',   'pnb':'PNB',
    'boiind':'BOI',   'idbibn':'IDBI',  'yesbnk':'Yes Bank',
    'idfcbk':'IDFC',  'rblbnk':'RBL',   'paytmb':'Paytm',
    'paytm':'Paytm',  'aubank':'AU Bank','fedbk':'Federal',
    'tmbank':'TMB',   'kvbank':'KVB',
}

# ── EXTRACTOR ──────────────────────────────────────────────
def extract_fields(sms_body, sender=''):
    body  = str(sms_body)
    lower = body.lower()
    result = {
        'txn_type':      None,
        'amount':        None,
        'bank':          None,
        'account_last4': None,
        'upi_ref':       None,
        'upi_id':        None,
        'merchant_raw':  None,
        'date':          None,
    }

    # txn_type
    if any(w in lower for w in DEBIT_WORDS):
        result['txn_type'] = 'debit'
    elif any(w in lower for w in CREDIT_WORDS):
        result['txn_type'] = 'credit'

    # amount
    for p in AMOUNT_PATTERNS:
        m = re.search(p, lower)
        if m:
            try:
                val = float(m.group(1).replace(',',''))
                if val >= 1:
                    result['amount'] = val
                    break
            except: continue

    # bank — sender first, then body
    sender_l = sender.lower()
    for code, name in BANK_SENDER_MAP.items():
        if code in sender_l:
            result['bank'] = name
            break
    if not result['bank']:
        for code, name in BANK_SENDER_MAP.items():
            if name.lower() in lower:
                result['bank'] = name
                break

    # account last 4
    for p in ACCOUNT_PATTERNS:
        m = re.search(p, lower)
        if m:
            result['account_last4'] = m.group(1)
            break

    # UPI ref
    for p in UPI_REF_PATTERNS:
        m = re.search(p, lower)
        if m:
            result['upi_ref'] = m.group(1)
            break

    # UPI ID (VPA)
    m = re.search(r'[\w.\-]+@[a-z]+', body)
    if m:
        result['upi_id'] = m.group(0)

    # merchant from VPA
    if result['upi_id']:
        vpa = result['upi_id'].lower()
        handle = vpa.split('@')[0]
        # if not a phone number → it's a merchant/name
        if not re.match(r'^\d{10}$', handle):
            result['merchant_raw'] = handle

    # date
    for p in DATE_PATTERNS:
        m = re.search(p, lower)
        if m:
            d = m.group(1).replace('/', '-')
            parts = d.split('-')
            if len(parts[2]) == 2:
                parts[2] = '20' + parts[2]
            result['date'] = '-'.join(parts)
            break

    return result


# ── SELF TEST ──────────────────────────────────────────────
if __name__ == '__main__':
    import json
    samples = [
        ("HDFC Bank: Rs 400.80 debited from a/c **2823 on 25-07-23 to VPA bookmyshow@axb UPI Ref No 320605383121", "AX-HDFCBK"),
        ("Amt Sent Rs.106.90 From HDFC Bank A/C *2823 To NSDL BILLDESK On 21-04 Ref 411291768471",                 "AX-HDFCBK"),
        ("Ac XX3035 Debited with Rs.500000.00, 27-11-2025. Aval Bal Rs.20000.00 CR. Helpline 18001800 - PNB",      "AX-PNBSMS"),
        ("UPI LITE Top-up amounting to Rs.200.00 has been successful. Ref No 526600106661 - HDFC Bank",            "AX-HDFCBK"),
    ]
    for sms, sender in samples:
        result = extract_fields(sms, sender)
        print(f"\nSMS    : {sms[:70]}...")
        print(f"OUTPUT : {json.dumps(result, indent=2)}")