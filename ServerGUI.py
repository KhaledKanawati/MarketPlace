import socket
import threading
import json
import sqlite3
import base64
import os

conn = sqlite3.connect('marketplace.db')
cursor = conn.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS productList (
    product_name TEXT NOT NULL,
    user_name TEXT NOT NULL,
    image BLOB,
    description TEXT NOT NULL,
    price REAL,
    rating REAL DEFAULT 0,
    quantity INTEGER DEFAULT 1,
    numberOfRating INTEGER DEFAULT 0,
    UNIQUE(product_name, user_name)
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS infoList (
    username TEXT UNIQUE,
    password TEXT NOT NULL,
    real_name TEXT,
    email TEXT,
    address TEXT,
    portNumber TEXT,
    profile_picture BLOB,
    bio TEXT
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS userPr (
    username TEXT NOT NULL,
    product_name TEXT NOT NULL
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS buyers (
    seller_username TEXT NOT NULL,
    product_name TEXT NOT NULL,
    buyer_username TEXT NOT NULL,
    rating INTEGER
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender TEXT NOT NULL,
    receiver TEXT NOT NULL,
    message TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_read INTEGER DEFAULT 0
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    buyer TEXT NOT NULL,
    seller TEXT NOT NULL,
    product TEXT NOT NULL,
    date TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS product_ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL,
    seller TEXT NOT NULL,
    buyer TEXT NOT NULL,
    rating INTEGER NOT NULL,
    review TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS buyer_ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    buyer TEXT NOT NULL,
    rating INTEGER NOT NULL,
    rated_by TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)""")

conn.commit()
cursor.close()
conn.close()

online_users = {}
active_chats = {}

def get_connection():
    connection = sqlite3.connect('marketplace.db')
    return connection

def user_exists(username):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM infoList WHERE LOWER(username) = LOWER(?)", (username,))
    user_record = cursor.fetchone()
    cursor.close()
    conn.close()
    return user_record is not None

def verify_password(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM infoList WHERE LOWER(username) = LOWER(?)", (username,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result and result[0] == password

def create_user(username, password, real_name):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO infoList (username, password, real_name) VALUES (?, ?, ?)",
                      (username, password, real_name))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except:
        cursor.close()
        conn.close()
        return False

def get_all_products():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT product_name, user_name, rating, price, image FROM productList WHERE quantity > 0")
    products = cursor.fetchall()
    cursor.close()
    conn.close()
    
    result = {}
    for product_name, user_name, rating, price, image in products:
        if user_name not in result:
            result[user_name] = []
        image_b64 = base64.b64encode(image).decode('utf-8') if image else None
        result[user_name].append((product_name, rating, price, image_b64))
    
    return result

def get_product_info(product_name, seller=None):
    conn = get_connection()
    cursor = conn.cursor()
    if seller:
        cursor.execute("SELECT user_name, image, description, price, quantity FROM productList WHERE product_name = ? AND user_name = ?",
                      (product_name, seller))
    else:
        cursor.execute("SELECT user_name, image, description, price, quantity FROM productList WHERE product_name = ?",
                      (product_name,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result

def product_exists(product_name, seller=None):
    conn = get_connection()
    cursor = conn.cursor()
    if seller:
        cursor.execute("SELECT * FROM productList WHERE product_name = ? AND user_name = ?", (product_name, seller))
    else:
        cursor.execute("SELECT * FROM productList WHERE product_name = ?", (product_name,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result is not None

def add_product(product_name, username, image, description, price, quantity):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT quantity FROM productList WHERE product_name = ? AND user_name = ?",
                      (product_name, username))
        existing = cursor.fetchone()
        
        if existing:
            new_quantity = existing[0] + quantity
            cursor.execute("""UPDATE productList 
                             SET quantity = ?, image = COALESCE(?, image), 
                                 description = ?, price = ? 
                             WHERE product_name = ? AND user_name = ?""",
                          (new_quantity, image, description, price, product_name, username))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        else:
            cursor.execute("""INSERT INTO productList 
                             (product_name, user_name, image, description, price, quantity) 
                             VALUES (?, ?, ?, ?, ?, ?)""",
                          (product_name, username, image, description, price, quantity))
            cursor.execute("INSERT INTO userPr (username, product_name) VALUES (?, ?)",
                          (username, product_name))
            conn.commit()
            cursor.close()
            conn.close()
            return True
    except Exception as e:
        print(f"Error in add_product: {e}")
        cursor.close()
        conn.close()
        return False

def get_user_purchase_history(username):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT product_name, buyer_username FROM buyers WHERE seller_username = ?", (username,))
    purchases = cursor.fetchall()
    cursor.close()
    conn.close()
    
    result = {}
    result[username] = [(f"{product_name} - bought by {buyer}") for product_name, buyer in purchases]
    return result

def store_message(sender, receiver, message):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO chat_messages (sender, receiver, message) VALUES (?, ?, ?)",
                      (sender, receiver, message))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except:
        cursor.close()
        conn.close()
        return False

def get_unread_messages(username):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, sender, message, timestamp FROM chat_messages WHERE receiver = ? AND is_read = 0 ORDER BY timestamp",
                  (username,))
    messages = cursor.fetchall()
    cursor.close()
    conn.close()
    return messages

def mark_messages_read(username, sender=None):
    conn = get_connection()
    cursor = conn.cursor()
    if sender:
        cursor.execute("UPDATE chat_messages SET is_read = 1 WHERE receiver = ? AND sender = ?",
                      (username, sender))
    else:
        cursor.execute("UPDATE chat_messages SET is_read = 1 WHERE receiver = ?", (username,))
    conn.commit()
    cursor.close()
    conn.close()

def get_chat_history(user1, user2, limit=50):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT sender, message, timestamp FROM chat_messages 
                     WHERE (sender = ? AND receiver = ?) OR (sender = ? AND receiver = ?)
                     ORDER BY timestamp DESC LIMIT ?""",
                  (user1, user2, user2, user1, limit))
    messages = cursor.fetchall()
    cursor.close()
    conn.close()
    return list(reversed(messages))

def register_online_user(username, client_socket, address, port):
    online_users[username] = {
        'socket': client_socket,
        'port': port,
        'address': address
    }
    print(f"User {username} is now online (P2P port: {port})")

def unregister_online_user(username):
    if username in online_users:
        del online_users[username]
        print(f"User {username} is now offline")

def get_user_connection_info(username):
    if username in online_users:
        return online_users[username]
    return None

def get_conversations(username):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""SELECT DISTINCT 
                     CASE WHEN sender = ? THEN receiver ELSE sender END as conversation_partner
                     FROM chat_messages 
                     WHERE sender = ? OR receiver = ?""",
                  (username, username, username))
    
    conversation_list = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return conversation_list

def get_seller_products(seller):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT product_name, rating, price, image, quantity FROM productList WHERE user_name = ?",
                  (seller,))
    products = cursor.fetchall()
    cursor.close()
    conn.close()
    
    result = []
    for product_name, rating, price, image, quantity in products:
        image_b64 = base64.b64encode(image).decode('utf-8') if image else None
        result.append((product_name, rating, price, image_b64, quantity))
    return result

def delete_product(product_name, username):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT user_name FROM productList WHERE product_name = ? AND user_name = ?", 
                      (product_name, username))
        result = cursor.fetchone()
        if not result:
            cursor.close()
            conn.close()
            return False
        
        cursor.execute("DELETE FROM productList WHERE product_name = ? AND user_name = ?", 
                      (product_name, username))
        cursor.execute("DELETE FROM userPr WHERE product_name = ? AND username = ?", 
                      (product_name, username))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting product: {e}")
        cursor.close()
        conn.close()
        return False

def decrement_product_stock(product_name, seller, quantity=1):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT quantity FROM productList WHERE product_name = ? AND user_name = ?", 
                      (product_name, seller))
        check_result = cursor.fetchone()
        if not check_result:
            print(f"ERROR: Product '{product_name}' not found for seller '{seller}'")
            cursor.close()
            conn.close()
            return None
        
        current_stock = check_result[0]
        if current_stock < quantity:
            print(f"ERROR: Insufficient stock for '{product_name}' by '{seller}'. Current: {current_stock}, Requested: {quantity}")
            cursor.close()
            conn.close()
            return None
        
        cursor.execute("UPDATE productList SET quantity = quantity - ? WHERE product_name = ? AND user_name = ?",
                      (quantity, product_name, seller))
        conn.commit()
        
        cursor.execute("SELECT quantity FROM productList WHERE product_name = ? AND user_name = ?", 
                      (product_name, seller))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result[0] if result else None  # Return None on error, 0 is valid
    except Exception as e:
        print(f"Error decrementing stock: {e}")
        cursor.close()
        conn.close()
        return None  # Return None to indicate error

def check_already_purchased(buyer, product_name, seller):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM buyers WHERE buyer_username = ? AND product_name = ? AND seller_username = ?",
                  (buyer, product_name, seller))
    count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return count > 0

def create_transaction(buyer, seller, product, date, quantity):
    import uuid
    trans_id = str(uuid.uuid4())[:8]
    
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""INSERT INTO transactions 
                         (id, buyer, seller, product, date, quantity, status) 
                         VALUES (?, ?, ?, ?, ?, ?, 'pending')""",
                      (trans_id, buyer, seller, product, date, quantity))
        conn.commit()
        cursor.close()
        conn.close()
        return trans_id
    except Exception as e:
        print(f"Error creating transaction: {e}")
        cursor.close()
        conn.close()
        return None

def get_user_transactions(username, other_user=None):
    conn = get_connection()
    cursor = conn.cursor()
    
    if other_user:
        cursor.execute("""SELECT id, buyer, seller, product, date, quantity, status 
                         FROM transactions 
                         WHERE (buyer = ? AND seller = ?) OR (buyer = ? AND seller = ?)
                         ORDER BY created_at DESC""",
                      (username, other_user, other_user, username))
    else:
        cursor.execute("""SELECT id, buyer, seller, product, date, quantity, status 
                         FROM transactions 
                         WHERE buyer = ? OR seller = ?
                         ORDER BY created_at DESC""",
                      (username, username))
    
    transactions = cursor.fetchall()
    cursor.close()
    conn.close()
    
    result = []
    for trans in transactions:
        trans_id, buyer, seller, product, date, quantity, status = trans
        result.append({
            'id': trans_id,
            'buyer': buyer,
            'seller': seller,
            'product': product,
            'date': date,
            'quantity': quantity,
            'status': status
        })
    return result

def update_transaction_status(trans_id, status):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE transactions SET status = ? WHERE id = ?",
                      (status, trans_id))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except:
        cursor.close()
        conn.close()
        return False

def complete_purchase(trans_id, product_name, product_rating, buyer_rating):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT buyer, seller, quantity FROM transactions WHERE id = ?", (trans_id,))
        trans = cursor.fetchone()
        if not trans:
            cursor.close()
            conn.close()
            return False
        
        buyer, seller, quantity = trans
        
        cursor.execute("UPDATE transactions SET status = 'completed' WHERE id = ?", (trans_id,))
        
        cursor.execute("INSERT INTO buyers (seller_username, product_name, buyer_username, rating) VALUES (?, ?, ?, ?)",
                      (seller, product_name, buyer, product_rating))
        
        cursor.execute("SELECT rating, numberOfRating FROM productList WHERE product_name = ? AND user_name = ?", 
                      (product_name, seller))
        prod = cursor.fetchone()
        if prod:
            current_rating, num_ratings = prod
            new_num_ratings = num_ratings + 1
            new_rating = ((current_rating * num_ratings) + product_rating) / new_num_ratings
            cursor.execute("UPDATE productList SET rating = ?, numberOfRating = ? WHERE product_name = ? AND user_name = ?",
                          (new_rating, new_num_ratings, product_name, seller))
        
        cursor.execute("UPDATE productList SET quantity = quantity - ? WHERE product_name = ? AND user_name = ?",
                      (quantity, product_name, seller))
        
        cursor.execute("INSERT INTO product_ratings (product_name, seller, buyer, rating) VALUES (?, ?, ?, ?)",
                      (product_name, seller, buyer, product_rating))
        
        cursor.execute("INSERT INTO buyer_ratings (buyer, rating, rated_by) VALUES (?, ?, ?)",
                      (buyer, buyer_rating, seller))
        
        cursor.execute("INSERT INTO buyer_ratings (buyer, rating, rated_by) VALUES (?, ?, ?)",
                      (seller, product_rating, buyer))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error completing purchase: {e}")
        cursor.close()
        conn.close()
        return False

def get_user_profile(username):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT real_name, profile_picture, bio FROM infoList WHERE LOWER(username) = LOWER(?)", (username,))
        user_info = cursor.fetchone()
        if not user_info:
            cursor.close()
            conn.close()
            return None
        
        real_name = str(user_info[0]) if user_info[0] else "User"
        profile_picture_blob = user_info[1] if len(user_info) > 1 else None
        bio = str(user_info[2]) if (len(user_info) > 2 and user_info[2]) else ""
        
        profile_picture = None
        if profile_picture_blob:
            try:
                profile_picture = base64.b64encode(profile_picture_blob).decode('utf-8')
            except Exception as e:
                print(f"Error encoding profile picture: {e}")
                profile_picture = None
        
        cursor.execute("SELECT AVG(rating) FROM buyer_ratings WHERE LOWER(buyer) = LOWER(?)", (username,))
        avg_rating_result = cursor.fetchone()
        avg_rating = avg_rating_result[0] if avg_rating_result and avg_rating_result[0] else 0.0
        
        cursor.execute("""SELECT product_name, price, rating, numberOfRating, quantity 
                         FROM productList 
                         WHERE LOWER(user_name) = LOWER(?) AND quantity > 0""", (username,))
        current_products = []
        try:
            for row in cursor.fetchall():
                if row and len(row) >= 5:
                    current_products.append({
                        'product_name': row[0] if row[0] else "Unknown",
                        'price': float(row[1]) if row[1] else 0.0,
                        'rating': float(row[2]) if row[2] else 0.0,
                        'numberOfRating': int(row[3]) if row[3] else 0,
                        'quantity': int(row[4]) if row[4] else 0
                    })
        except Exception as e:
            print(f"Error processing current products: {e}")
            current_products = []
        
        cursor.execute("""SELECT product_name, price, rating, numberOfRating, quantity 
                         FROM productList 
                         WHERE LOWER(user_name) = LOWER(?) AND quantity = 0""", (username,))
        previous_products = []
        try:
            for row in cursor.fetchall():
                if row and len(row) >= 5:
                    previous_products.append({
                        'product_name': row[0] if row[0] else "Unknown",
                        'price': float(row[1]) if row[1] else 0.0,
                        'rating': float(row[2]) if row[2] else 0.0,
                        'numberOfRating': int(row[3]) if row[3] else 0,
                        'quantity': int(row[4]) if row[4] else 0
                    })
        except Exception as e:
            print(f"Error processing previous products: {e}")
            previous_products = []
        
        cursor.close()
        conn.close()
        
        return {
            'real_name': str(real_name) if real_name else "User",
            'profile_picture': str(profile_picture) if profile_picture else None,
            'bio': str(bio) if bio else "",
            'avg_rating': float(avg_rating) if avg_rating else 0.0,
            'current_products': current_products,
            'previous_products': previous_products
        }
    except Exception as e:
        print(f"Error getting user profile: {e}")
        cursor.close()
        conn.close()
        return None

def update_user_profile(username, real_name, bio, profile_picture_b64):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        profile_picture_blob = None
        if profile_picture_b64:
            profile_picture_blob = base64.b64decode(profile_picture_b64)
        
        cursor.execute("""UPDATE infoList 
                         SET real_name = ?, bio = ?, profile_picture = ? 
                         WHERE LOWER(username) = LOWER(?)""",
                      (real_name, bio, profile_picture_blob, username))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating profile: {e}")
        cursor.close()
        conn.close()
        return False

def handle_client(client_socket, address):
    print(f"Client connected from {address}")
    username = None
    
    try:
        auth_choice = client_socket.recv(1024).decode('utf-8').lower()
        
        if auth_choice == "yes":
            username = client_socket.recv(1024).decode('utf-8').lower()
            if user_exists(username):
                client_socket.send(b'1')
            else:
                client_socket.send(b'0')
                return
            
            password = client_socket.recv(1024).decode('utf-8')
            if verify_password(username, password):
                if username in online_users:
                    client_socket.send(b'0')
                    return
                client_socket.send(b'1')
            else:
                client_socket.send(b'0')
                return
            
            client_socket.recv(1024)
            client_socket.send(b"Login successful!")
            
            register_online_user(username, client_socket, address, 0)
        
        elif auth_choice == "no":
            username = client_socket.recv(1024).decode('utf-8').lower()
            if not user_exists(username):
                client_socket.send(b'1')
            else:
                client_socket.send(b'0')
                return
            
            user_data = client_socket.recv(1024).decode('utf-8')
            real_name, password = user_data.split('|')
            
            if create_user(username, password, real_name):
                client_socket.send(b"Account created successfully!")
                client_socket.recv(1024)
                register_online_user(username, client_socket, address, 0)
            else:
                client_socket.send(b"Error creating account")
                return
        
        while True:
            try:
                request_code = client_socket.recv(1024).decode('utf-8')
                
                if not request_code:
                    break
            except Exception as receive_error:
                print(f"Error receiving request: {receive_error}")
                break
            
            try:
                if request_code == "1":
                    # Check for purchase history
                    history = get_user_purchase_history(username)
                    if history[username]:
                        client_socket.send(b'1')
                        history_json = json.dumps(history)
                        client_socket.send(len(history_json).to_bytes(16, 'big'))
                        client_socket.sendall(history_json.encode('utf-8'))
                    else:
                        client_socket.send(b'0')
                    
                    # Wait for ready signal
                    client_socket.recv(1024)
                    
                    # Send product list
                    products = get_all_products()
                    products_json = json.dumps(products)
                    client_socket.send(len(products_json).to_bytes(16, 'big'))
                    client_socket.sendall(products_json.encode('utf-8'))
            
                elif request_code == "2":
                    product_name = client_socket.recv(1024).decode('utf-8').strip('\x00').strip()
                    
                    client_socket.send(b'1')
                    
                    data_length = int.from_bytes(client_socket.recv(16), 'big')
                    product_data = b""
                    
                    # Receive product data in chunks (for large images)
                    while len(product_data) < data_length:
                        chunk = client_socket.recv(4096)
                        if not chunk:
                            break
                        product_data += chunk
                    
                    try:
                        # Parse product data: name|image|description|price|quantity
                        data_str = json.loads(product_data.decode('utf-8'))
                        parts = data_str.split('|')
                        prod_name, image_b64, description, price, quantity = parts
                        
                        # Decode base64 image if present
                        if image_b64 != "No Image":
                            image_binary = base64.b64decode(image_b64)
                        else:
                            image_binary = None
                        
                        # Add product to database (will restock if already exists for this seller)
                        if add_product(prod_name, username, image_binary, description, float(price), int(quantity)):
                            client_socket.send(b'1')  # Success
                            print(f"Product '{prod_name}' added by {username}")
                        else:
                            client_socket.send(b'0')  # Failure
                    except Exception as e:
                        print(f"Error adding product: {e}")
                        client_socket.send(b'0')  # Send failure response
            
                elif request_code == "3":  # Product details request
                    # Receive product name and seller (format: "product_name|seller")
                    data = client_socket.recv(1024).decode('utf-8').strip('\x00').strip()
                    
                    # Parse data - check if seller is included
                    if '|' in data:
                        product_name, seller = data.split('|', 1)
                    else:
                        # Backwards compatibility - no seller specified
                        product_name = data
                        seller = None
                    
                    if product_exists(product_name, seller):
                        client_socket.send(b'1')
                        
                        product_info = get_product_info(product_name, seller)
                        seller_name, image, description, price, quantity = product_info
                        
                        info_str = f"{seller_name}|{description}|{price}|{quantity}"
                        client_socket.send(info_str.encode('utf-8'))
                        
                        # Wait for acknowledgment
                        client_socket.recv(1024)
                        
                        # Send image
                        if image:
                            client_socket.send(len(image).to_bytes(16, 'big'))
                            client_socket.sendall(image)
                        else:
                            image_data = b"No Image"
                            client_socket.send(len(image_data).to_bytes(16, 'big'))
                            client_socket.sendall(image_data)
                    else:
                        client_socket.send(b'0')
            
                elif request_code == "4":  # History request
                    history = get_user_purchase_history(username)
                    if history is not None:
                        client_socket.send(b'1')
                        history_json = json.dumps(history)
                        client_socket.send(len(history_json).to_bytes(16, 'big'))
                        client_socket.sendall(history_json.encode('utf-8'))
                    else:
                        client_socket.send(b'0')
            
                elif request_code == "5":  # Get unread messages
                    messages = get_unread_messages(username)
                    if messages:
                        client_socket.send(b'1')
                        messages_json = json.dumps(messages)
                        client_socket.send(len(messages_json).to_bytes(16, 'big'))
                        client_socket.sendall(messages_json.encode('utf-8'))
                    else:
                        client_socket.send(b'0')
                
                elif request_code == "6":  # Get chat history with user
                    other_user = client_socket.recv(1024).decode('utf-8').strip('\x00').strip()
                    history = get_chat_history(username, other_user)
                    if history:
                        client_socket.send(b'1')
                        history_json = json.dumps(history)
                        client_socket.send(len(history_json).to_bytes(16, 'big'))
                        client_socket.sendall(history_json.encode('utf-8'))
                    else:
                        client_socket.send(b'0')
                
                elif request_code == "7":  # Send message - simple store
                    try:
                        recipient = client_socket.recv(1024).decode('utf-8').strip('\x00').strip()
                        message = client_socket.recv(4096).decode('utf-8').strip('\x00').strip()
                        
                        # Store the message
                        store_message(username, recipient, message)
                        
                        # Send acknowledgment
                        client_socket.send(b'1')
                    except Exception as e:
                        print(f"Error in command 7: {e}")
                        client_socket.send(b'0')
                
                elif request_code == "8":  # Register P2P port (deprecated - user registered on login)
                    port = int(client_socket.recv(1024).decode('utf-8'))
                    # Update port if needed
                    if username in online_users:
                        online_users[username]['port'] = port
                
                elif request_code == "17":  # Store chat message for history
                    recipient = client_socket.recv(1024).decode('utf-8')
                    message = client_socket.recv(4096).decode('utf-8')
                    
                    # Store message in database
                    if store_message(username, recipient, message):
                        client_socket.send(b'1')  # Success
                    else:
                        client_socket.send(b'0')  # Failed
                
                elif request_code == "9":  # Logout
                    unregister_online_user(username)
                    break
                
                elif request_code == "10":  # Get conversations
                    conversations = get_conversations(username)
                    conv_json = json.dumps(conversations)
                    client_socket.send(len(conv_json).to_bytes(16, 'big'))
                    client_socket.sendall(conv_json.encode('utf-8'))
                
                elif request_code == "11":  # Get seller's products
                    seller = client_socket.recv(1024).decode('utf-8').strip('\x00')
                    products = get_seller_products(seller)
                    # Convert to list of dicts for easier JSON handling
                    product_list = [{'name': p[0], 'rating': p[1], 'price': p[2], 'image': p[3]} for p in products]
                    products_json = json.dumps(product_list)
                    client_socket.send(b'1')  # Send success response first
                    client_socket.send(len(products_json).to_bytes(16, 'big'))
                    client_socket.sendall(products_json.encode('utf-8'))
                
                elif request_code == "12":  # Create purchase proposal
                    length = int.from_bytes(client_socket.recv(16), 'big')
                    proposal_data = b""
                    while len(proposal_data) < length:
                        packet = client_socket.recv(4096)
                        if not packet:
                            break
                        proposal_data += packet
                    
                    proposal = json.loads(proposal_data.decode('utf-8'))
                    trans_id = create_transaction(
                        proposal['buyer'],
                        proposal['seller'],
                        proposal['product'],
                        proposal['date'],
                        proposal['quantity']
                    )
                    
                    if trans_id:
                        client_socket.send(trans_id.encode('utf-8'))
                    else:
                        client_socket.send(b'error')
                
                elif request_code == "13":  # Check transactions with user
                    other_user = client_socket.recv(1024).decode('utf-8')
                    transactions = get_user_transactions(username, other_user)
                    
                    if transactions:
                        client_socket.send(b'1')
                        trans_json = json.dumps(transactions)
                        client_socket.send(len(trans_json).to_bytes(16, 'big'))
                        client_socket.sendall(trans_json.encode('utf-8'))
                    else:
                        client_socket.send(b'0')
                
                elif request_code == "14":  # Respond to transaction
                    trans_id = client_socket.recv(1024).decode('utf-8')
                    response = client_socket.recv(1024).decode('utf-8')
                    
                    if update_transaction_status(trans_id, response):
                        client_socket.send(b'1')
                    else:
                        client_socket.send(b'0')
                
                elif request_code == "15":  # Complete purchase with product and buyer ratings
                    trans_id = client_socket.recv(1024).decode('utf-8').strip('\x00').strip()
                    product_name = client_socket.recv(1024).decode('utf-8').strip('\x00').strip()
                    product_rating = int(client_socket.recv(1024).decode('utf-8').strip('\x00').strip())
                    buyer_rating = int(client_socket.recv(1024).decode('utf-8').strip('\x00').strip())
                    
                    if complete_purchase(trans_id, product_name, product_rating, buyer_rating):
                        client_socket.send(b'1')
                    else:
                        client_socket.send(b'0')
                
                elif request_code == "16":  # Check if user is online
                    check_username = client_socket.recv(1024).decode('utf-8').strip('\x00')
                    if check_username in online_users:
                        client_socket.send(b'1')  # Online
                    else:
                        client_socket.send(b'0')  # Offline
                
                elif request_code == "18":  # Get user profile
                    profile_username = client_socket.recv(1024).decode('utf-8').strip('\x00').strip()
                    profile = get_user_profile(profile_username)
                    
                    if profile:
                        try:
                            # Ensure all string fields are properly encoded
                            if profile.get('bio') is None:
                                profile['bio'] = ""
                            if profile.get('real_name') is None:
                                profile['real_name'] = "User"
                            
                            profile_json = json.dumps(profile, ensure_ascii=False)
                            profile_bytes = profile_json.encode('utf-8')
                            
                            # Send success indicator
                            client_socket.send(b'1')
                            # Send length prefix (16 bytes)
                            client_socket.send(len(profile_bytes).to_bytes(16, 'big'))
                            # Send actual data
                            client_socket.sendall(profile_bytes)
                        except Exception as e:
                            print(f"Error encoding profile: {e}")
                            client_socket.send(b'0')
                    else:
                        client_socket.send(b'0')
                
                elif request_code == "19":  # Update user profile
                    length = int.from_bytes(client_socket.recv(16), 'big')
                    profile_data = b""
                    while len(profile_data) < length:
                        packet = client_socket.recv(4096)
                        if not packet:
                            break
                        profile_data += packet
                    
                    profile_info = json.loads(profile_data.decode('utf-8'))
                    
                    if update_user_profile(
                        username,
                        profile_info.get('real_name'),
                        profile_info.get('bio'),
                        profile_info.get('profile_picture')
                    ):
                        client_socket.send(b'1')
                    else:
                        client_socket.send(b'0')
                
                elif request_code == "20":  # Store received message (from P2P chat)
                    sender = client_socket.recv(1024).decode('utf-8')
                    message = client_socket.recv(4096).decode('utf-8')
                    
                    # Store message with sender as sender and current user as receiver
                    if store_message(sender, username, message):
                        client_socket.send(b'1')  # Success
                    else:
                        client_socket.send(b'0')  # Failed
                
                elif request_code == "21":  # Get new messages from specific user
                    other_user = client_socket.recv(1024).decode('utf-8').strip('\x00').strip()
                    
                    # Get unread messages from other_user to this user
                    conn_db = get_connection()
                    cursor = conn_db.cursor()
                    cursor.execute("""SELECT sender, message, timestamp FROM chat_messages 
                                     WHERE sender = ? AND receiver = ? AND is_read = 0
                                     ORDER BY timestamp ASC""",
                                  (other_user, username))
                    new_messages = cursor.fetchall()
                    
                    if new_messages:
                        # Mark as read
                        cursor.execute("""UPDATE chat_messages SET is_read = 1 
                                         WHERE sender = ? AND receiver = ? AND is_read = 0""",
                                      (other_user, username))
                        conn_db.commit()
                        
                        client_socket.send(b'1')
                        messages_json = json.dumps(new_messages)
                        client_socket.send(len(messages_json).to_bytes(16, 'big'))
                        client_socket.sendall(messages_json.encode('utf-8'))
                    else:
                        client_socket.send(b'0')
                    
                    cursor.close()
                    conn_db.close()
                
                elif request_code == "22":  # Submit ratings for purchase
                    # Receive rating data
                    rating_length = int.from_bytes(client_socket.recv(16), 'big')
                    rating_data = b""
                    while len(rating_data) < rating_length:
                        packet = client_socket.recv(4096)
                        if not packet:
                            break
                        rating_data += packet
                    
                    try:
                        rating_info = json.loads(rating_data.decode('utf-8'))
                        product_name = rating_info['product_name']
                        seller = rating_info['seller']
                        buyer = rating_info['buyer']
                        product_rating = rating_info['product_rating']
                        seller_rating = rating_info['seller_rating']
                        
                        conn_db = get_connection()
                        cursor = conn_db.cursor()
                        
                        # Add product rating to product_ratings table with seller info
                        cursor.execute("""INSERT INTO product_ratings (product_name, seller, buyer, rating, timestamp)
                                         VALUES (?, ?, ?, ?, datetime('now'))""",
                                      (product_name, seller, buyer, product_rating))
                        
                        # Add seller rating to buyer_ratings table (re-purpose for seller ratings)
                        # Note: buyer_ratings table is used for all user ratings
                        cursor.execute("""INSERT INTO buyer_ratings (buyer, rating, rated_by, timestamp)
                                         VALUES (?, ?, ?, datetime('now'))""",
                                      (seller, seller_rating, buyer))
                        
                        # Update average product rating for THIS SPECIFIC SELLER'S product only
                        cursor.execute("""SELECT rating, numberOfRating FROM productList 
                                         WHERE product_name = ? AND user_name = ?""",
                                      (product_name, seller))
                        prod = cursor.fetchone()
                        if prod:
                            current_rating, num_ratings = prod
                            new_num_ratings = num_ratings + 1
                            new_rating = ((current_rating * num_ratings) + product_rating) / new_num_ratings
                            cursor.execute("""UPDATE productList SET rating = ?, numberOfRating = ? 
                                             WHERE product_name = ? AND user_name = ?""",
                                          (new_rating, new_num_ratings, product_name, seller))
                        
                        conn_db.commit()
                        cursor.close()
                        conn_db.close()
                        
                        client_socket.send(b'1')
                    except Exception as e:
                        print(f"Error saving ratings: {e}")
                        client_socket.send(b'0')
                
                elif request_code == "23":  # Delete product (owner only)
                    product_name = client_socket.recv(1024).decode('utf-8').strip('\x00')
                    if delete_product(product_name, username):
                        client_socket.send(b'1')
                    else:
                        client_socket.send(b'0')
                
                elif request_code == "24":  # Check if already purchased
                    # Receive product name and seller (format: "product_name|seller")
                    data = client_socket.recv(1024).decode('utf-8').strip('\x00')
                    
                    # Parse data - check if seller is included
                    if '|' in data:
                        product_name, seller = data.split('|', 1)
                    else:
                        # Backwards compatibility
                        product_name = data
                        seller = None
                    
                    if seller and check_already_purchased(username, product_name, seller):
                        client_socket.send(b'1')  # Already purchased from this seller
                    else:
                        client_socket.send(b'0')  # Not purchased from this seller
                
                elif request_code == "25":  # Decrement stock after confirmed purchase
                    length = int.from_bytes(client_socket.recv(16), 'big')
                    data = b""
                    while len(data) < length:
                        packet = client_socket.recv(4096)
                        if not packet:
                            break
                        data += packet
                    
                    try:
                        purchase_info = json.loads(data.decode('utf-8'))
                        product_name = purchase_info['product_name']
                        seller = purchase_info['seller']  # REQUIRED - identifies which seller's product
                        quantity = purchase_info.get('quantity', 1)
                        
                        print(f"Stock reduction request: product={product_name}, seller={seller}, buyer={username}, qty={quantity}")
                        
                        # Decrement stock for this specific seller's product
                        remaining = decrement_product_stock(product_name, seller, quantity)
                        if remaining is not None and remaining >= 0:
                            # Record the purchase with seller info
                            conn_db = get_connection()
                            cursor = conn_db.cursor()
                            cursor.execute("INSERT INTO buyers (seller_username, product_name, buyer_username) VALUES (?, ?, ?)",
                                          (seller, product_name, username))
                            conn_db.commit()
                            cursor.close()
                            conn_db.close()
                            
                            print(f"Stock reduced successfully. Remaining: {remaining}")
                            client_socket.send(b'1')  # Success even if stock is now 0
                        else:
                            print(f"Failed to reduce stock for {product_name} by {seller}")
                            client_socket.send(b'0')  # Failed or negative stock
                    except Exception as e:
                        print(f"Error decrementing stock for {seller}'s {product_name}: {e}")
                        client_socket.send(b'0')
                
                elif request_code == "26":  # Register active chat window
                    other_user = client_socket.recv(1024).decode('utf-8').strip('\x00').strip()
                    if username not in active_chats:
                        active_chats[username] = set()
                    active_chats[username].add(other_user)
                    client_socket.send(b'1')
                    print(f"{username} opened chat with {other_user}")
                
                elif request_code == "27":  # Unregister active chat window
                    other_user = client_socket.recv(1024).decode('utf-8').strip('\x00').strip()
                    if username in active_chats:
                        active_chats[username].discard(other_user)
                        if not active_chats[username]:
                            del active_chats[username]
                    client_socket.send(b'1')
                    print(f"{username} closed chat with {other_user}")
                
                elif request_code == "28":  # Check detailed user status (in chat, online, or offline)
                    check_user = client_socket.recv(1024).decode('utf-8').strip('\x00').strip()
                    
                    # Check if user has chat open with requester
                    in_chat = username in active_chats and check_user in active_chats.get(username, set())
                    other_has_chat = check_user in active_chats and username in active_chats.get(check_user, set())
                    
                    if in_chat or other_has_chat:
                        client_socket.send(b'2')  # In chat
                    elif check_user in online_users:
                        client_socket.send(b'1')  # Online
                    else:
                        client_socket.send(b'0')  # Offline
                
                elif request_code == "29":  # Check if user has new messages since last interaction
                    check_user = client_socket.recv(1024).decode('utf-8').strip('\x00').strip()
                    
                    # Check if there are unread messages from this user
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""SELECT COUNT(*) FROM chat_messages 
                                    WHERE receiver = ? AND sender = ? AND is_read = 0""",
                                 (username, check_user))
                    count = cursor.fetchone()[0]
                    cursor.close()
                    conn.close()
                    
                    if count > 0:
                        client_socket.send(b'1')  # Has new messages
                    else:
                        client_socket.send(b'0')  # No new messages
                
                elif request_code == "30":  # Mark messages as read from specific sender
                    sender = client_socket.recv(1024).decode('utf-8').strip('\x00').strip()
                    mark_messages_read(username, sender)
                    client_socket.send(b'1')  # Acknowledgment
                
                elif request_code == "31":  # Update user profile
                    length = int.from_bytes(client_socket.recv(16), 'big')
                    data = b""
                    while len(data) < length:
                        packet = client_socket.recv(4096)
                        if not packet:
                            break
                        data += packet
                    
                    try:
                        profile_data = json.loads(data.decode('utf-8'))
                        prof_username = profile_data.get('username')
                        real_name = profile_data.get('real_name')
                        bio = profile_data.get('bio')
                        profile_picture = profile_data.get('profile_picture')
                        
                        if update_user_profile(prof_username, real_name, bio, profile_picture):
                            client_socket.send(b'1')  # Success
                        else:
                            client_socket.send(b'0')  # Failed
                    except Exception as e:
                        print(f"Error updating profile: {e}")
                        client_socket.send(b'0')
                
                elif request_code == "32":  # Update product details
                    length = int.from_bytes(client_socket.recv(16), 'big')
                    data = b""
                    while len(data) < length:
                        packet = client_socket.recv(4096)
                        if not packet:
                            break
                        data += packet
                    
                    try:
                        update_data = json.loads(data.decode('utf-8'))
                        product_name = update_data.get('product_name')
                        quantity = update_data.get('quantity')
                        price = update_data.get('price')
                        description = update_data.get('description')
                        image_b64 = update_data.get('image')
                        
                        conn = get_connection()
                        cursor = conn.cursor()
                        
                        # Verify ownership - check for THIS user's product specifically
                        cursor.execute("SELECT user_name FROM productList WHERE product_name = ? AND user_name = ?", 
                                      (product_name, username))
                        result = cursor.fetchone()
                        
                        if result:
                            # Update THIS user's product only
                            if image_b64:
                                image_blob = base64.b64decode(image_b64)
                                cursor.execute("""UPDATE productList 
                                                SET quantity = ?, price = ?, description = ?, image = ?
                                                WHERE product_name = ? AND user_name = ?""",
                                             (quantity, price, description, image_blob, product_name, username))
                            else:
                                cursor.execute("""UPDATE productList 
                                                SET quantity = ?, price = ?, description = ?
                                                WHERE product_name = ? AND user_name = ?""",
                                             (quantity, price, description, product_name, username))
                            
                            conn.commit()
                            cursor.close()
                            conn.close()
                            print(f"Product '{product_name}' updated by {username}")
                            client_socket.send(b'1')  # Success
                        else:
                            cursor.close()
                            conn.close()
                            print(f"Failed to update: {username} does not own product '{product_name}'")
                            client_socket.send(b'0')  # Not owner or doesn't exist
                    except Exception as e:
                        print(f"Error updating product: {e}")
                        import traceback
                        traceback.print_exc()
                        client_socket.send(b'0')
                
                elif request_code == "b":  # Buy request - placeholder for chat functionality
                    # This needs to be implemented with the buying flow
                    pass
                
            except Exception as e:
                print(f"Error handling request '{request_code}': {e}")
                import traceback
                traceback.print_exc()
                try:
                    client_socket.send(b'0')  # Send error response
                except:
                    break
    
    except Exception as e:
        print(f"Error handling client: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Unregister user if they were online
        if username:
            unregister_online_user(username)
            # Clean up active chats
            if username in active_chats:
                del active_chats[username]
        try:
            client_socket.close()
        except:
            pass
        print(f"Client disconnected: {address}")

def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    port = int(input("Enter server port (1024-65535): "))
    
    if port < 1024 or port > 65535:
        print("Invalid port")
        return
    
    server_socket.bind((socket.gethostbyname(socket.gethostname()), port))
    server_socket.listen(5)
    
    print(f"Server listening on port {port}")
    print(f"Server address: {socket.gethostbyname(socket.gethostname())}:{port}")
    
    try:
        while True:
            client_socket, address = server_socket.accept()
            client_thread = threading.Thread(target=handle_client, args=(client_socket, address))
            client_thread.daemon = True
            client_thread.start()
    except KeyboardInterrupt:
        print("\nServer shutting down...")
    finally:
        server_socket.close()

if __name__ == "__main__":
    main()
