"""
Flask Backend — SpendSense
Run: python server.py
Opens at: http://localhost:5000
"""

from flask import Flask, request, jsonify, send_from_directory
import sqlite3, os, sys, csv
from datetime import datetime, timedelta

# ── PATH SETUP ─────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.path.join(BASE_DIR, 'spendsense.db')
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'sms_filter_model.pkl')
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))

app = Flask(__name__, static_folder=BASE_DIR)

# ── LAZY MODEL LOAD ────────────────────────────────────────
_pipeline = None
def get_pipeline():
    global _pipeline
    if _pipeline is None:
        import joblib
        _pipeline = joblib.load(MODEL_PATH)
    return _pipeline

# ── DATABASE SETUP ─────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            raw_sms       TEXT,
            sender        TEXT,
            txn_type      TEXT,
            amount        REAL,
            bank          TEXT,
            account_last4 TEXT,
            upi_ref       TEXT,
            upi_id        TEXT,
            merchant      TEXT,
            category      TEXT,
            txn_date      TEXT,
            source        TEXT DEFAULT "manual",
            created_at    TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_transaction(data, source='manual'):
    conn = sqlite3.connect(DB_PATH)
    now  = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn.execute('''
        INSERT INTO transactions
        (raw_sms, sender, txn_type, amount, bank, account_last4,
         upi_ref, upi_id, merchant, category, txn_date, source, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (
        data.get('raw_sms'),   data.get('sender'),
        data.get('txn_type'),  data.get('amount'),
        data.get('bank'),      data.get('account_last4'),
        data.get('upi_ref'),   data.get('upi_id'),
        data.get('merchant'),  data.get('category'),
        data.get('date'),      source, now,
    ))
    conn.commit()
    conn.close()

def fetch_transactions(limit=200, category=None, txn_type=None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    query = 'SELECT * FROM transactions WHERE 1=1'
    args  = []
    if category:
        query += ' AND category=?'; args.append(category)
    if txn_type:
        query += ' AND txn_type=?'; args.append(txn_type)
    query += ' ORDER BY created_at DESC LIMIT ?'
    args.append(limit)
    rows = conn.execute(query, args).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def fetch_summary():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    total = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM transactions WHERE txn_type='debit'"
    ).fetchone()[0]

    month_start = datetime.now().replace(day=1).strftime('%Y-%m-%d')
    month_total = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM transactions WHERE txn_type='debit' AND created_at>=?",
        (month_start,)
    ).fetchone()[0]

    week_start = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    week_total = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM transactions WHERE txn_type='debit' AND created_at>=?",
        (week_start,)
    ).fetchone()[0]

    cat_rows = conn.execute(
        "SELECT category, COALESCE(SUM(amount),0) as total FROM transactions WHERE txn_type='debit' GROUP BY category ORDER BY total DESC"
    ).fetchall()

    bank_rows = conn.execute(
        "SELECT bank, COUNT(*) as cnt FROM transactions GROUP BY bank ORDER BY cnt DESC"
    ).fetchall()

    trend_rows = conn.execute(
        "SELECT DATE(created_at) as day, COALESCE(SUM(amount),0) as total FROM transactions WHERE txn_type='debit' AND created_at>=? GROUP BY day ORDER BY day",
        ((datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),)
    ).fetchall()

    txn_count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    conn.close()

    return {
        'total_spent':  round(total, 2),
        'month_total':  round(month_total, 2),
        'week_total':   round(week_total, 2),
        'txn_count':    txn_count,
        'by_category':  [{'category': r['category'] or 'Uncategorised', 'total': round(r['total'],2)} for r in cat_rows],
        'by_bank':      [{'bank': r['bank'] or 'Unknown', 'count': r['cnt']} for r in bank_rows],
        'daily_trend':  [{'day': r['day'], 'total': round(r['total'],2)} for r in trend_rows],
    }

# ── PIPELINE RUN ───────────────────────────────────────────
def run_pipeline(sms_body, sender=''):
    try:
        # scripts/ is already in sys.path — import directly, no "scripts." prefix
        from run_pipeline     import run
    except ImportError as e:
        return {'error': f'Pipeline import failed: {str(e)}'}
    result = run(sms_body, sender)
    result['sender'] = sender
    return result

# ── ROUTES ─────────────────────────────────────────────────

@app.route('/')
def index():
    # Find index.html — checks root and Ui/ subfolder
    for candidate in ['index.html', 'AppUI.html', os.path.join('Ui','index.html')]:
        full = os.path.join(BASE_DIR, candidate)
        if os.path.exists(full):
            return send_from_directory(os.path.dirname(full) or BASE_DIR,
                                       os.path.basename(full))
    return f"index.html not found in {BASE_DIR}", 404

@app.route('/api/parse', methods=['POST'])
def parse_sms():
    data   = request.get_json()
    sms    = data.get('sms', '').strip()
    sender = data.get('sender', '').strip()
    if not sms:
        return jsonify({'error': 'No SMS text provided'}), 400
    result = run_pipeline(sms, sender)
    if result.get('is_transaction'):
        save_transaction(result, source=data.get('source', 'manual'))
    return jsonify(result)

@app.route('/api/parse-batch', methods=['POST'])
def parse_batch():
    data    = request.get_json()
    items   = data.get('messages', [])
    saved   = 0
    skipped = 0
    for item in items:
        sms    = item.get('sms', '').strip()
        sender = item.get('sender', '').strip()
        if not sms:
            continue
        result = run_pipeline(sms, sender)
        if result.get('is_transaction'):
            save_transaction(result, source='batch')
            saved += 1
        else:
            skipped += 1
    return jsonify({'saved': saved, 'skipped': skipped})

@app.route('/api/load-csv', methods=['GET'])
def load_csv():
    # Checks dataset_extract/ first, then data/, then root
    candidates = [
        os.path.join(BASE_DIR, 'dataset_extract', 'sms_transactions_clean.csv'),
        os.path.join(BASE_DIR, 'data',             'sms_transactions_clean.csv'),
        os.path.join(BASE_DIR,                     'sms_transactions_clean.csv'),
    ]
    csv_path = next((p for p in candidates if os.path.exists(p)), None)
    if not csv_path:
        return jsonify({'error': f'sms_transactions_clean.csv not found. Checked: dataset_extract/, data/, root'}), 404

    messages = []
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            body   = row.get('body', '').strip()
            sender = row.get('address', '').strip()
            if body:
                messages.append({'sms': body, 'sender': sender})
    return jsonify({'messages': messages, 'count': len(messages)})

@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    limit    = int(request.args.get('limit', 200))
    category = request.args.get('category')
    txn_type = request.args.get('type')
    return jsonify(fetch_transactions(limit, category, txn_type))

@app.route('/api/summary', methods=['GET'])
def get_summary():
    return jsonify(fetch_summary())

@app.route('/api/delete/<int:txn_id>', methods=['DELETE'])
def delete_transaction(txn_id):
    conn = sqlite3.connect(DB_PATH)
    conn.execute('DELETE FROM transactions WHERE id=?', (txn_id,))
    conn.commit()
    conn.close()
    return jsonify({'deleted': txn_id})

@app.route('/api/categories', methods=['GET'])
def get_categories():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute('SELECT DISTINCT category FROM transactions ORDER BY category').fetchall()
    conn.close()
    return jsonify([r[0] for r in rows if r[0]])

# ── MAIN ── (ALL routes must be defined ABOVE this line) ───
if __name__ == '__main__':
    init_db()
    print("\n" + "="*50)
    print("  SpendSense is running!")
    print("  Open: http://localhost:5000")
    print("="*50 + "\n")
    app.run(debug=True, port=5000)