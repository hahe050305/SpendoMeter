import pandas as pd

df = pd.read_csv('sms_transactions_clean.csv')

# Fix 1 — UPI LITE top-ups are debits
mask_topup = df['body'].str.contains('top-up|top up|lite', case=False, na=False)
df.loc[mask_topup & (df['txn_type'] == 'unknown'), 'txn_type'] = 'debit'

# Fix 2 — Remove failed transactions
mask_failed = df['body'].str.contains('has failed|payment failed|txn failed', case=False, na=False)
print(f"Removing {mask_failed.sum()} failed transaction rows:")
print(df[mask_failed]['body'].str[:80].to_string())
df = df[~mask_failed].reset_index(drop=True)

# Fix 3 — Normalise date format (25-07-23 and 20/11/24 → DD-MM-YYYY)
def normalise_date(d):
    if pd.isna(d): return None
    d = str(d).strip().replace('/', '-')
    parts = d.split('-')
    if len(parts) == 3 and len(parts[2]) == 2:
        parts[2] = '20' + parts[2]
    return '-'.join(parts)

df['date_extracted'] = df['date_extracted'].apply(normalise_date)

# Fix 4 — Tag P2P transfers vs merchant payments
def tag_p2p(upi_id):
    if pd.isna(upi_id): return 'unknown'
    upi_id = str(upi_id).lower()
    # Phone number based UPI IDs = P2P
    if any(upi_id.startswith(str(d)) for d in range(6, 10)):
        return 'p2p'
    # Known merchants
    merchants = ['bookmyshow', 'swiggy', 'zomato', 'gpay', 'paytm',
                 'irctc', 'netflix', 'amazon', 'flipkart', 'uber', 'ola']
    if any(m in upi_id for m in merchants):
        return 'merchant'
    return 'unknown'

df['transfer_type'] = df['upi_id'].apply(tag_p2p)

# Save
df.to_csv('sms_transactions_clean.csv', index=False)

print(f"\nFixed dataset: {len(df)} rows")
print(f"txn_type split:\n{df['txn_type'].value_counts().to_string()}")
print(f"\ntransfer_type split:\n{df['transfer_type'].value_counts().to_string()}")
print(f"\nDate sample:\n{df['date_extracted'].dropna().head(5).to_string()}")
print("\nDone. Now run 02_train_filter.py")