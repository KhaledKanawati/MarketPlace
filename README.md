## Quick Start

```bash
git clone <repository-url>
cd Project
pip install -r requirements.txt
python ServerGUI.py    # Terminal 1
python MarketplaceGUI.py    # Terminal 2
```

## About

Online marketplace with chat, product listings, and transaction management built with Python, used as a marketplace for AUB students.

**Features:** User authentication, product browsing, real-time chat, purchase proposals, ratings system

## How It Works

**Server** (`ServerGUI.py`) - Manages authentication, database, and all client requests, is hardcoded to port 100001, can change to any viable port, just make sure change follows in client.
**Client** (`MarketplaceGUI.py`) - GUI for browsing, listing products, and managing your account  
**Chat** (`ChatSystem.py`) - Messaging interface between users

Database (SQLite) is created automatically on first run.

## Usage

1. Sign up or log in
2. Browse products or list your own items
3. Chat with sellers about products
4. Submit and confirm purchase proposals
5. Rate products and sellers after transactions


## Demonstration And Demo

Sign-up/Login:

<img width="1169" height="648" alt="image" src="https://github.com/user-attachments/assets/83c45724-92d1-407b-8c8c-f088cec742e2" />


Main Page:

<img width="1188" height="570" alt="image" src="https://github.com/user-attachments/assets/bddb6c71-cedf-4187-8277-6b35d1d0f537" />


Viewing Product:

<img width="1178" height="761" alt="image" src="https://github.com/user-attachments/assets/44d6bf18-8c24-48db-a4ea-f5d75772406e" />


Messaging:

<img width="494" height="594" alt="image" src="https://github.com/user-attachments/assets/2c980a3f-fdd8-4aa7-9a46-56feb002e56e" />

Sending Purchase Proposal:

<img width="410" height="299" alt="image" src="https://github.com/user-attachments/assets/c0c7cbc6-9cc7-4760-9630-8d1ff45d28a4" />

Rating After Purchase:

<img width="539" height="529" alt="image" src="https://github.com/user-attachments/assets/69a7ebe6-5dc9-436f-acca-799a2a53fb19" />

Viewing Profile of Seller:


<img width="1178" height="780" alt="image" src="https://github.com/user-attachments/assets/0a3e03df-39b5-497d-943a-222b4fb60a6c" />


Sales History From Seller:

<img width="1182" height="476" alt="image" src="https://github.com/user-attachments/assets/3fea1f8b-0f24-4009-99c6-091514195214" />

