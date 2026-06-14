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

## 📈 Future Improvements

- Real-time Android SMS ingestion
- Monthly spending insights
- Subscription detection
- Recurring payment analysis
- Multi-language SMS support
- Enhanced merchant recognition
- REST API deployment

---

## 🔴 App Working Screenshots

# Working of Flask Backend:
<img width="1482" height="458" alt="image" src="https://github.com/user-attachments/assets/0af695b9-a263-402f-a215-8c5e7cf6b2da" />


# Main Interface:
<img width="1475" height="786" alt="image" src="https://github.com/user-attachments/assets/53a74338-609d-4172-877c-9e9e1ffa7b97" />


# Smart Insights Tab Feature:
<img width="902" height="722" alt="image" src="https://github.com/user-attachments/assets/a735a5cb-c717-4d44-8cfa-8e2bb329a3c4" />


# SMS Parsing and Transaction extraction in JSON Format:
<img width="1493" height="543" alt="image" src="https://github.com/user-attachments/assets/8ac86f58-20e1-4ce6-87bc-41601b176fc1" />
<img width="887" height="487" alt="image" src="https://github.com/user-attachments/assets/64eccc28-af5d-4fe0-92ce-1ec7a4601bc4" />


# Transactions Section:
<img width="1478" height="507" alt="image" src="https://github.com/user-attachments/assets/8e08a57c-2608-43e0-89b5-54ded787c64b" />


# Category Section:
<img width="1480" height="507" alt="image" src="https://github.com/user-attachments/assets/eec1b9b9-64e2-48a5-9dd4-6d0d979de411" />


# Light Mode Preview
<img width="1482" height="860" alt="image" src="https://github.com/user-attachments/assets/d3a9a708-6d65-435a-a78f-d72bc46b9321" />

---

## 📄 License

This project is licensed under the MIT License.
