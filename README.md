# Spendometer 💸

An intelligent SMS transaction processing engine that converts raw bank messages into structured financial data.

Spendometer automatically identifies transaction SMS, extracts key details such as amount, bank, account information, UPI references, transaction type, merchant details, and spending categories. It transforms noisy SMS inbox data into machine-readable transaction records that can power expense trackers, finance dashboards, budgeting tools, and personal finance applications.

---

## ✨ Features

- 🔍 Machine Learning-based transaction SMS detection
- 💰 Transaction amount extraction
- 🏦 Bank identification
- 💳 Account number masking & last-4 extraction
- 📱 UPI ID and UPI Reference extraction
- 🏷️ Merchant identification and resolution
- 📊 Credit/Debit transaction classification
- 📂 Automatic spending categorization
- 🚫 OTP, promotional SMS, and spam filtering
- ⚡ End-to-end SMS → Structured JSON pipeline

---

## 🏗️ Pipeline Architecture

```text
Raw SMS
   │
   ▼
Transaction Filter Model
   │
   ├── Non-Transaction → Discard
   │
   ▼
Field Extraction Engine
   │
   ▼
Merchant Resolution
   │
   ▼
Category Assignment
   │
   ▼
Structured Transaction Record
```

---

## 📦 Example Input

```text
HDFC Bank: Rs 400.80 debited from a/c **2823 on 25-07-23 to VPA bookmyshow@axb UPI Ref No 320605383121
```

---

## 📤 Example Output

```json
{
  "is_transaction": true,
  "confidence": 98.4,
  "txn_type": "debit",
  "amount": 400.80,
  "bank": "HDFC",
  "account_last4": "2823",
  "upi_ref": "320605383121",
  "merchant": "BookMyShow",
  "category": "Entertainment"
}
```



---


---

## 🛠️ Tech Stack

- Python
- Pandas
- Scikit-Learn
- Regular Expressions (Regex)
- Joblib

### Machine Learning

- TF-IDF Vectorization
- Logistic Regression Classification

---


---

## 📈 Future Improvements

- Real-time Android SMS ingestion
- Monthly spending insights
- Subscription detection
- Recurring payment analysis
- Multi-language SMS support
- Enhanced merchant recognition
- REST API deployment

---

## 📄 License

This project is licensed under the MIT License.
