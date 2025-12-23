# Marketplace Application

## Quick Start

```bash
git clone <repository-url>
cd Project
pip install -r requirements.txt
python ServerGUI.py    # Terminal 1 - Enter port (e.g., 5000)
python MarketplaceGUI.py    # Terminal 2 - Connect to server port
```

## About

Online marketplace with chat, product listings, and transaction management built with Python and Tkinter.

**Features:** User authentication, product browsing, real-time chat, purchase proposals, ratings system

## How It Works

**Server** (`ServerGUI.py`) - Manages authentication, database, and all client requests
**Client** (`MarketplaceGUI.py`) - GUI for browsing, listing products, and managing your account  
**Chat** (`ChatSystem.py`) - Messaging interface between users

Database (SQLite) is created automatically on first run.

## Usage

1. Sign up or log in
2. Browse products or list your own items
3. Chat with sellers about products
4. Submit and confirm purchase proposals
5. Rate products and sellers after transactions
