import xml.etree.ElementTree as ET
import pandas as pd
import re

def parse_sms_xml(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    records = []
    for sms in root.findall('sms'):
        records.append({
            'address':  sms.get('address'),   # sender ID e.g. "DM-HDFCBK"
            'date':     sms.get('date'),
            'body':     sms.get('body'),
            'type':     sms.get('type'),       # 1=received, 2=sent
        })
    
    return pd.DataFrame(records)

def is_likely_transaction(row):
    body = row['body'].lower()
    sender = str(row['address']).lower()
    
    # Bank sender IDs in India follow DLT format: XX-BANKCODE
    bank_sender_pattern = r'^[a-z]{2}-[a-z]+'
    is_bank_sender = bool(re.match(bank_sender_pattern, sender))
    
    # Transaction keywords
    txn_keywords = ['debited', 'credited', 'debit', 'credit',
                    'inr', 'rs.', '₹', 'upi', 'neft', 'imps',
                    'withdrawn', 'transfer', 'payment', 'paid']
    has_txn_keyword = any(kw in body for kw in txn_keywords)
    
    return 1 if (is_bank_sender and has_txn_keyword) else 0

# Run it
df = parse_sms_xml('sms-20260612113850.xml')
print(f"Total SMS: {len(df)}")

# Auto-label (not perfect — you'll correct these manually)
df['is_transaction'] = df.apply(is_likely_transaction, axis=1)

# Split to review
txn_df  = df[df['is_transaction'] == 1]
other_df = df[df['is_transaction'] == 0]

print(f"Auto-labelled transactions: {len(txn_df)}")
print(f"Auto-labelled non-transactions: {len(other_df)}")

# Save two CSVs — one to verify labels, one as training data
df.to_csv('sms_raw_all.csv', index=False)
txn_df.to_csv('sms_transactions_review.csv', index=False)

print("\nSample transaction SMS found:")
print(txn_df['body'].head(10).to_string())