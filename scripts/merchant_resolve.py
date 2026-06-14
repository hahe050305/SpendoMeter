"""
Stage 4 — Merchant + Category Resolver
Looks up UPI ID / merchant name → human label + category
"""
import re

# ── LOOKUP TABLE ───────────────────────────────────────────
# Extend this as you encounter new merchants
MERCHANT_MAP = {
    # Food
    'swiggy':       ('Swiggy',        'Food & Dining'),
    'zomato':       ('Zomato',        'Food & Dining'),
    'dominos':      ('Dominos',       'Food & Dining'),
    'pizzahut':     ('Pizza Hut',     'Food & Dining'),
    'mcdonalds':    ('McDonalds',     'Food & Dining'),
    'kfc':          ('KFC',           'Food & Dining'),
    # Transport
    'uber':         ('Uber',          'Transport'),
    'ola':          ('Ola',           'Transport'),
    'rapido':       ('Rapido',        'Transport'),
    'irctc':        ('IRCTC',         'Travel'),
    'makemytrip':   ('MakeMyTrip',    'Travel'),
    'goibibo':      ('Goibibo',       'Travel'),
    # Entertainment
    'netflix':      ('Netflix',       'Entertainment'),
    'spotify':      ('Spotify',       'Entertainment'),
    'hotstar':      ('Hotstar',       'Entertainment'),
    'bookmyshow':   ('BookMyShow',    'Entertainment'),
    'primevideo':   ('Prime Video',   'Entertainment'),
    # Shopping
    'amazon':       ('Amazon',        'Shopping'),
    'flipkart':     ('Flipkart',      'Shopping'),
    'myntra':       ('Myntra',        'Shopping'),
    'meesho':       ('Meesho',        'Shopping'),
    # Utilities
    'bsnl':         ('BSNL',          'Utilities'),
    'airtel':       ('Airtel',        'Utilities'),
    'jio':          ('Jio',           'Utilities'),
    'bescom':       ('BESCOM',        'Utilities'),
    'tneb':         ('TNEB',          'Utilities'),
    'tangedco':     ('TNEB',          'Utilities'),
    'gpayrecharge': ('Recharge',      'Utilities'),
    # Finance
    'nsdl':         ('NSDL',          'Finance'),
    'billdesk':     ('BillDesk',      'Finance'),
    'lic':          ('LIC',           'Insurance'),
    'bajaj':        ('Bajaj Finance', 'Finance'),
    # Education
    'byjus':        ('Byjus',         'Education'),
    'unacademy':    ('Unacademy',     'Education'),
    'coursera':     ('Coursera',      'Education'),
    # Grocery
    'bigbasket':    ('BigBasket',     'Groceries'),
    'blinkit':      ('Blinkit',       'Groceries'),
    'zepto':        ('Zepto',         'Groceries'),
    'dmart':        ('DMart',         'Groceries'),
    # Health
    'pharmeasy':    ('PharmEasy',     'Health'),
    'netmeds':      ('Netmeds',       'Health'),
    'practo':       ('Practo',        'Health'),
    # P2P banks (common UPI handles)
    'okaxis':       (None,            'Transfer'),
    'okicici':      (None,            'Transfer'),
    'okhdfcbank':   (None,            'Transfer'),
    'oksbi':        (None,            'Transfer'),
    'ptaxis':       (None,            'Transfer'),
    'pthdfc':       (None,            'Transfer'),
    'ybl':          (None,            'Transfer'),
    'ibl':          (None,            'Transfer'),
}

def resolve_merchant(upi_id=None, merchant_raw=None, sms_body=None):
    """
    Returns (merchant_name, category)
    Priority: UPI ID lookup → body keyword scan → fallback
    """
    search_text = ' '.join(filter(None, [
        str(upi_id or '').lower(),
        str(merchant_raw or '').lower(),
        str(sms_body or '').lower()[:120],
    ]))

    for keyword, (name, category) in MERCHANT_MAP.items():
        if keyword in search_text:
            # For P2P bank handles, check if it's actually a person
            if category == 'Transfer' and upi_id:
                handle = str(upi_id).split('@')[0]
                if re.match(r'^\d{10}$', handle):
                    return ('P2P Transfer', 'Transfer')
                else:
                    return (handle.title(), 'Transfer')
            return (name or merchant_raw, category)

    # Fallback — classify by SMS body keywords
    body = str(sms_body or '').lower()
    if any(w in body for w in ['recharge', 'topup', 'top up', 'top-up', 'lite']):
        return ('Recharge/Top-up', 'Utilities')
    if any(w in body for w in ['emi', 'loan', 'insurance', 'premium']):
        return ('Loan/EMI', 'Finance')
    if any(w in body for w in ['salary', 'stipend', 'payroll']):
        return ('Salary', 'Income')
    if any(w in body for w in ['atm', 'cash', 'withdraw']):
        return ('ATM Withdrawal', 'Cash')
    if any(w in body for w in ['neft', 'imps', 'rtgs']):
        return ('Bank Transfer', 'Transfer')

    return ('Unknown', 'Uncategorised')


if __name__ == '__main__':
    tests = [
        ('bookmyshow@axb',          None,           None),
        ('9489511377@ptaxis',        None,           None),
        ('nithishkumar2140@okaxis',  None,           None),
        (None,                       'nsdl billdesk','Amt Sent Rs.106.90 To NSDL BILLDESK'),
        (None,                       None,           'UPI LITE Top-up Rs.200 successful'),
        (None,                       None,           'Ac XX3035 Debited Rs.500000 NEFT'),
    ]
    for upi, raw, body in tests:
        name, cat = resolve_merchant(upi, raw, body)
        print(f"  UPI:{str(upi):<30} → {name:<20} [{cat}]")