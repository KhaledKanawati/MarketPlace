import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from PIL import Image, ImageTk
import socket
import threading
import json
import os
from io import BytesIO
import base64
from ChatSystem import ChatWindow

class MarketplaceGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Marketplace")
        self.root.geometry("1200x800")
        self.root.configure(bg="#1a1a2e")
        
        self.client = None
        self.client_lock = threading.Lock()  # prevents race conditions on socket
        self.username = None
        self.current_user_port = None
        self.listening_server = None
        self.is_listening = False
        
        self.active_chats = {}
        self.conversations = []
        self.unread_messages = {}
        self.current_product_context = None
        self.received_proposals = {}
        self.search_debounce_id = None  # timer for search delay
        
        self.bg_dark = "#1a1a2e"
        self.bg_medium = "#16213e"  # Navigation and header background
        self.bg_light = "#0f3460"  # Button secondary color
        self.accent = "#e94560"  # Primary action color (buttons, highlights)
        self.accent_hover = "#c93a52"  # Accent color on hover for feedback
        self.text_light = "#ffffff"  # Primary text color for readability
        self.text_secondary = "#b8b8b8"  # Secondary text for less important info
        self.card_bg = "#16213e"  # Background for product cards and containers
        
        # Configure modern style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TButton', 
                       font=('Segoe UI', 10, 'bold'),
                       background=self.accent,
                       foreground='white',
                       borderwidth=0,
                       focuscolor='none',
                       padding=10)
        style.map('TButton',
                 background=[('active', self.accent_hover)])
        style.configure('TLabel', 
                       font=('Segoe UI', 10),
                       background=self.bg_dark,
                       foreground=self.text_light)
        style.configure('Header.TLabel', 
                       font=('Segoe UI', 16, 'bold'),
                       background=self.bg_dark,
                       foreground=self.text_light)
        style.configure('TFrame', background=self.bg_dark)
        style.configure('TEntry', 
                       fieldbackground='white',
                       foreground='black',
                       borderwidth=1)
        
        self.show_login_screen()
        
    def show_login_screen(self):
        self.clear_window()
        
        frame = ttk.Frame(self.root, padding="40")
        frame.pack(expand=True)
        
        ttk.Label(frame, text="🛒 Marketplace", font=('Segoe UI', 32, 'bold'), foreground=self.accent).pack(pady=30)
        
        ttk.Label(frame, text="Connecting to server...", font=('Segoe UI', 11), foreground=self.text_secondary).pack(pady=20)
        
        # Auto-connect to port 10001
        # CHANGE IF YOU WANT TO CONNECT TO DIFFERENT PORT, DO SO ALSO ON SERVER
        self.root.after(100, lambda: self.connect_server(10001))
    
    def connect_server(self, port):
        """Establish connection to the marketplace server.
        
        Uses TCP socket to connect to server running on localhost.
        If connection fails, user is notified and can retry.
        """
        try:
            # Create TCP socket for reliable communication
            self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client.settimeout(30.0)  # 30 second timeout for server operations
            
            # Connect to server on local machine at specified port
            server_address = socket.gethostbyname(socket.gethostname())
            self.client.connect((server_address, port))
            
            # Move to authentication screen on successful connection
            self.show_auth_screen()
        except Exception as connection_error:
            # Inform user of connection failure with specific error
            messagebox.showerror(
                "Connection Error", 
                f"Could not connect to server: {str(connection_error)}"
            )
            self.client = None
    
    def show_auth_screen(self):
        self.clear_window()
        
        frame = ttk.Frame(self.root, padding="40")
        frame.pack(expand=True)
        
        ttk.Label(frame, text="Welcome to Marketplace", font=('Segoe UI', 24, 'bold'), foreground=self.accent).pack(pady=30)
        
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="Login →", command=self.show_login_form, width=25).pack(pady=10)
        ttk.Button(button_frame, text="Sign Up →", command=self.show_signup_form, width=25).pack(pady=10)
    
    def show_login_form(self):
        self.clear_window()
        
        frame = ttk.Frame(self.root, padding="40")
        frame.pack(expand=True)
        
        ttk.Label(frame, text="Login", font=('Segoe UI', 24, 'bold'), foreground=self.accent).pack(pady=30)
        
        ttk.Label(frame, text="Username:", font=('Segoe UI', 11)).pack(pady=5)
        username_entry = ttk.Entry(frame, width=35, font=('Segoe UI', 11))
        username_entry.pack(pady=5, ipady=5)
        
        ttk.Label(frame, text="Password:", font=('Segoe UI', 11)).pack(pady=5)
        password_entry = ttk.Entry(frame, width=35, show="●", font=('Segoe UI', 11))
        password_entry.pack(pady=5, ipady=5)
        
        def login():
            username = username_entry.get().lower()
            password = password_entry.get()
            
            if not username or not password:
                messagebox.showerror("Error", "Please fill all fields")
                return
            
            try:
                if not self.client:
                    messagebox.showerror("Error", "Not connected to server")
                    return
                
                with self.client_lock:
                    self.client.send("yes".encode('utf-8'))
                    self.client.send(username.encode('utf-8'))
                    
                    try:
                        response = self.client.recv(1024).decode('utf-8')
                    except:
                        messagebox.showerror("Connection Error", "Lost connection to server")
                        return
                    
                    if not response or not bool(int(response)):
                        messagebox.showerror("Error", "Username not found")
                        return
                    
                    self.client.send(password.encode('utf-8'))
                    
                    try:
                        response = self.client.recv(1024).decode('utf-8')
                    except:
                        messagebox.showerror("Connection Error", "Lost connection to server")
                        return
                    
                    if not response or not bool(int(response)):
                        # Wrong password OR already logged in
                        messagebox.showerror("Login Error", "Invalid password or user already logged in from another device")
                        try:
                            self.client.close()
                        except:
                            pass
                        self.client = None
                        self.show_login_screen()
                        return
                    
                    self.client.send("1".encode('utf-8'))
                    login_msg = self.client.recv(4096)
                    
                    if not login_msg:
                        messagebox.showerror("Error", "Server connection lost")
                        return
                
                self.username = username
                self.show_marketplace()
            except socket.error as e:
                messagebox.showerror("Connection Error", f"Lost connection to server: {str(e)}")
                self.logout()
            except Exception as e:
                messagebox.showerror("Error", f"Login failed: {str(e)}")
        
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="Login →", command=login, width=25).pack(pady=5)
        ttk.Button(button_frame, text="← Back", command=self.show_auth_screen, width=25).pack(pady=5)
    
    def show_signup_form(self):
        self.clear_window()
        
        frame = ttk.Frame(self.root, padding="40")
        frame.pack(expand=True)
        
        ttk.Label(frame, text="Sign Up", font=('Segoe UI', 24, 'bold'), foreground=self.accent).pack(pady=30)
        
        ttk.Label(frame, text="Full Name:", font=('Segoe UI', 11)).pack(pady=5)
        name_entry = ttk.Entry(frame, width=35, font=('Segoe UI', 11))
        name_entry.pack(pady=5, ipady=5)
        
        ttk.Label(frame, text="Username:", font=('Segoe UI', 11)).pack(pady=5)
        username_entry = ttk.Entry(frame, width=35, font=('Segoe UI', 11))
        username_entry.pack(pady=5, ipady=5)
        
        ttk.Label(frame, text="Password:", font=('Segoe UI', 11)).pack(pady=5)
        password_entry = ttk.Entry(frame, width=35, show="●", font=('Segoe UI', 11))
        password_entry.pack(pady=5, ipady=5)
        
        ttk.Label(frame, text="Min 8 characters, 1 uppercase, 1 lowercase", 
                 font=('Segoe UI', 9), 
                 foreground=self.text_secondary).pack(pady=(0, 5))
        
        def signup():
            name = name_entry.get().strip()
            username = username_entry.get().lower()
            password = password_entry.get()
            
            # Validate all fields before touching socket
            if not all([name, username, password]):
                messagebox.showerror("Error", "Please fill all fields")
                return
            
            # Validate password strength before touching socket
            if len(password) < 8:
                messagebox.showerror("Weak Password", "Password must be at least 8 characters long")
                return
            
            if not any(c.isupper() for c in password):
                messagebox.showerror("Weak Password", "Password must contain at least one uppercase letter")
                return
            
            if not any(c.islower() for c in password):
                messagebox.showerror("Weak Password", "Password must contain at least one lowercase letter")
                return
            
            # All validation passed, now use socket
            try:
                if not self.client:
                    messagebox.showerror("Error", "Not connected to server")
                    return
                
                with self.client_lock:
                    self.client.send("no".encode('utf-8'))
                    
                    self.client.send(username.encode('utf-8'))
                    
                    try:
                        response = self.client.recv(1024).decode('utf-8')
                    except:
                        messagebox.showerror("Connection Error", "Lost connection to server")
                        return
                    
                    if not response or not bool(int(response)):
                        messagebox.showerror("Error", "Username already exists")
                        return
                    
                    data = f"{name}|{password}"
                    self.client.send(data.encode('utf-8'))
                    
                    try:
                        response = self.client.recv(4096).decode('utf-8')
                    except:
                        messagebox.showerror("Connection Error", "Lost connection to server")
                        return
                    
                    if not response:
                        messagebox.showerror("Error", "Server connection lost")
                        return
                    
                    # Send confirmation signal like login does
                    self.client.send("1".encode('utf-8'))
                
                messagebox.showinfo("Success", "Account created successfully!")
                self.username = username
                self.show_marketplace()
            except socket.error as e:
                messagebox.showerror("Connection Error", f"Lost connection to server: {str(e)}")
                self.logout()
            except Exception as e:
                messagebox.showerror("Error", f"Signup failed: {str(e)}")
        
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="Create Account →", command=signup, width=25).pack(pady=5)
        ttk.Button(button_frame, text="← Back", command=self.show_auth_screen, width=25).pack(pady=5)
    
    def create_nav_button(self, parent, text, command):
        """Helper method to create consistent navigation buttons across the app.
        
        This ensures all buttons have the same styling and behavior,
        making the interface feel cohesive and professional.
        """
        button = tk.Button(
            parent, 
            text=text, 
            command=command,
            font=('Segoe UI', 10, 'bold'),
            bg=self.accent,
            fg='white',
            activebackground=self.accent_hover,
            activeforeground='white',
            border=0,
            padx=15,
            pady=8,
            cursor='hand2'  # Shows hand cursor to indicate clickability
        )
        return button
    
    def show_marketplace(self):
        self.clear_window()
        
        nav_frame = tk.Frame(self.root, bg=self.bg_medium, height=70)
        nav_frame.pack(fill=tk.X)
        nav_frame.pack_propagate(False)  # keep fixed height
        
        left_nav = tk.Frame(nav_frame, bg=self.bg_medium)
        left_nav.pack(side=tk.LEFT, padx=20, pady=15)
        
        tk.Label(left_nav, text="🛒 Marketplace", 
                font=('Segoe UI', 16, 'bold'), 
                bg=self.bg_medium, 
                fg=self.accent).pack(side=tk.LEFT, padx=(0, 20))
        
        tk.Label(left_nav, text=f"Welcome, {self.username}!", 
                font=('Segoe UI', 12), 
                bg=self.bg_medium, 
                fg=self.text_light).pack(side=tk.LEFT)
        
        right_nav = tk.Frame(nav_frame, bg=self.bg_medium)
        right_nav.pack(side=tk.RIGHT, padx=20, pady=15)
        
        self.create_nav_button(right_nav, "Refresh", self.show_marketplace).pack(side=tk.LEFT, padx=5)
        
        self.messages_btn_frame = tk.Frame(right_nav, bg=self.bg_medium)
        self.messages_btn_frame.pack(side=tk.LEFT, padx=5)
        self.messages_btn = self.create_nav_button(self.messages_btn_frame, "Messages", self.show_messages)
        self.messages_btn.pack()
        
        self.create_nav_button(right_nav, "+ Sell", self.show_sell_product).pack(side=tk.LEFT, padx=5)
        self.create_nav_button(right_nav, "📜 Sales", self.show_history).pack(side=tk.LEFT, padx=5)
        self.create_nav_button(right_nav, "👤 Profile", lambda: self.show_user_profile(self.username)).pack(side=tk.LEFT, padx=5)
        self.create_nav_button(right_nav, "Logout", self.logout).pack(side=tk.LEFT, padx=5)
        
        self.start_message_checker()
        
        search_frame = tk.Frame(self.root, bg=self.bg_dark)
        search_frame.pack(fill=tk.X, padx=20, pady=(10, 0))
        
        tk.Label(search_frame, text="🔍 Search:", 
                font=('Segoe UI', 11),
                bg=self.bg_dark,
                fg=self.text_light).pack(side=tk.LEFT, padx=(0, 10))
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self.debounce_search())  # fires on every keystroke
        search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                               font=('Segoe UI', 11),
                               bg='white',
                               fg='black',
                               width=40)
        search_entry.pack(side=tk.LEFT, ipady=5)
        
        tk.Label(search_frame, text="(Search by product name, seller, or description)", 
                font=('Segoe UI', 9),
                bg=self.bg_dark,
                fg=self.text_secondary).pack(side=tk.LEFT, padx=10)
        
        self.all_products_data = None
        self.show_browse_products(embedded=True)
    
    def show_browse_products(self, embedded=False):
        if not embedded:
            self.clear_window()
            
            # Header
            header_frame = tk.Frame(self.root, bg=self.bg_dark)
            header_frame.pack(fill=tk.X, padx=20, pady=20)
            
            tk.Label(header_frame, text="Browse Products", 
                    font=('Segoe UI', 20, 'bold'),
                    bg=self.bg_dark,
                    fg=self.text_light).pack(side=tk.LEFT)
            
            back_btn = self.create_nav_button(header_frame, "← Back", self.show_marketplace)
            back_btn.pack(side=tk.RIGHT)
        
        # Get products from server (or use cached data)
        try:
            if not self.client:
                messagebox.showerror("Error", "Not connected to server")
                return
            
            with self.client_lock:
                self.client.send("1".encode('utf-8'))
                
                # Check for history response
                history_check = self.client.recv(1024).decode('utf-8')
                if history_check == '1':
                    # Server is sending history, receive it
                    length = int.from_bytes(self.client.recv(16), 'big')
                    history_data = b""
                    while len(history_data) < length:
                        packet = self.client.recv(4096)
                        if not packet:
                            break
                        history_data += packet
                
                # Send ready signal for products
                self.client.send("ready".encode('utf-8'))
                
                # Now receive products
                length = int.from_bytes(self.client.recv(16), 'big')
                products_data = b""
                while len(products_data) < length:
                    packet = self.client.recv(4096)
                    if not packet:
                        break
                    products_data += packet
            
            if not products_data:
                products_dict = {}
            else:
                try:
                    products_dict = json.loads(products_data.decode('utf-8', errors='ignore'))
                except Exception as decode_error:
                    print(f"Error decoding products: {decode_error}")
                    products_dict = {}
            
            # Store for search filtering
            self.all_products_data = products_dict
            
            # Create scrollable product list
            canvas_frame = tk.Frame(self.root, bg=self.bg_dark)
            canvas_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
            
            canvas = tk.Canvas(canvas_frame, bg=self.bg_dark, highlightthickness=0)
            scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
            scrollable_frame = tk.Frame(canvas, bg=self.bg_dark)
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            # Check if products exist
            # Filter products by search query
            search_query = self.search_var.get().lower().strip() if hasattr(self, 'search_var') else ""
            
            has_products = False
            displayed_count = 0
            
            if products_dict and isinstance(products_dict, dict):
                for seller, products in products_dict.items():
                    if products and len(products) > 0:
                        for product in products:
                            try:
                                if len(product) >= 4:
                                    product_name = product[0]
                                    # Check if matches search
                                    if (not search_query or 
                                        search_query in product_name.lower() or 
                                        search_query in seller.lower()):
                                        has_products = True
                                        displayed_count += 1
                            except:
                                pass
            
            if not has_products or displayed_count == 0:
                empty_frame = tk.Frame(scrollable_frame, bg=self.bg_dark)
                empty_frame.pack(pady=50, padx=20)
                tk.Label(empty_frame, 
                        text="📦 No products available yet", 
                        font=('Segoe UI', 16, 'bold'),
                        bg=self.bg_dark,
                        fg=self.text_secondary).pack(pady=10)
                tk.Label(empty_frame, 
                        text="Be the first to list an item!", 
                        font=('Segoe UI', 12),
                        bg=self.bg_dark,
                        fg=self.text_secondary).pack(pady=5)
            else:
                for seller, products in products_dict.items():
                    if products:
                        for product in products:
                            try:
                                if len(product) >= 4:
                                    product_name, rating, price, image_b64 = product[0], product[1], product[2], product[3]
                                    # Apply search filter
                                    if (not search_query or 
                                        search_query in product_name.lower() or 
                                        search_query in seller.lower()):
                                        self.create_product_card(scrollable_frame, product_name, seller, 
                                                                float(rating) if rating else 0, 
                                                                float(price) if price else 0, 
                                                                image_b64)
                                elif len(product) >= 2:  # Fallback for old format
                                    product_name, rating = product[0], product[1]
                                    if (not search_query or 
                                        search_query in product_name.lower() or 
                                        search_query in seller.lower()):
                                        self.create_product_card(scrollable_frame, product_name, seller, 
                                                                float(rating) if rating else 0, 0, None)
                            except Exception as e:
                                print(f"Error creating product card: {e}")
                                continue
            
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load products: {str(e)}")
    
    def create_product_card(self, parent, product_name, seller, rating, price=0, image_b64=None):
        card = tk.Frame(parent, bg=self.card_bg, relief="flat", borderwidth=0)
        card.pack(fill=tk.X, pady=8, padx=10)
        
        content = tk.Frame(card, bg=self.card_bg)
        content.pack(fill=tk.X, padx=15, pady=15)
        
        left_frame = tk.Frame(content, bg=self.card_bg)
        left_frame.pack(side=tk.LEFT, padx=(0, 15))
        
        # placeholder while image loads
        placeholder = Image.new('RGB', (100, 100), color='#2d3748')
        photo = ImageTk.PhotoImage(placeholder)
        img_label = tk.Label(left_frame, image=photo, bg=self.card_bg)
        img_label.image = photo
        img_label.pack()
        
        if image_b64:
            def load_image():
                # runs in background so UI doesn't freeze
                try:
                    image_data = base64.b64decode(image_b64)
                    img = Image.open(BytesIO(image_data))
                    img.thumbnail((100, 100), Image.Resampling.LANCZOS)
                    photo_real = ImageTk.PhotoImage(img)
                    
                    # Update label in main thread
                    def update_image():
                        if img_label.winfo_exists():
                            img_label.configure(image=photo_real)
                            img_label.image = photo_real
                    
                    self.root.after(0, update_image)
                except:
                    pass  # Keep placeholder on error
            
            # Load image in background thread
            threading.Thread(target=load_image, daemon=True).start()
        
        right_frame = tk.Frame(content, bg=self.card_bg)
        right_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Label(right_frame, text=product_name, 
                font=('Segoe UI', 14, 'bold'),
                bg=self.card_bg,
                fg=self.text_light).pack(anchor="w", pady=(0, 5))
        
        tk.Label(right_frame, text=f"👤 {seller}", 
                font=('Segoe UI', 10),
                bg=self.card_bg,
                fg=self.text_secondary).pack(anchor="w", pady=2)
        
        tk.Label(right_frame, text=f"💰 ${price:.2f}", 
                font=('Segoe UI', 12, 'bold'),
                bg=self.card_bg,
                fg="#4ade80").pack(anchor="w", pady=2)
        
        tk.Label(right_frame, text=f"⭐ {rating:.1f} rating", 
                font=('Segoe UI', 10),
                bg=self.card_bg,
                fg="#ffd700").pack(anchor="w", pady=2)
        
        btn_frame = tk.Frame(right_frame, bg=self.card_bg)
        btn_frame.pack(anchor="w", pady=(10, 0))
        
        view_btn = tk.Button(btn_frame, text="View Details →",
                            command=lambda: self.show_product_details(product_name, seller),
                            font=('Segoe UI', 10, 'bold'),
                            bg=self.accent,
                            fg='white',
                            activebackground=self.accent_hover,
                            activeforeground='white',
                            border=0,
                            padx=15,
                            pady=6,
                            cursor='hand2')
        view_btn.pack(side=tk.LEFT, padx=(0, 5))
    
    def show_product_details(self, product_name, seller):
        self.clear_window()
        
        # Header
        header_frame = tk.Frame(self.root, bg=self.bg_dark)
        header_frame.pack(fill=tk.X, padx=20, pady=20)
        
        tk.Label(header_frame, text="Product Details", 
                font=('Segoe UI', 20, 'bold'),
                bg=self.bg_dark,
                fg=self.text_light).pack(side=tk.LEFT)
        
        back_btn = self.create_nav_button(header_frame, "← Back", self.show_marketplace)
        back_btn.pack(side=tk.RIGHT)
        
        # Get product details
        try:
            if not self.client:
                messagebox.showerror("Error", "Not connected to server")
                self.show_marketplace()
                return
                
            # Send product details command
            with self.client_lock:
                self.client.send("3".encode('utf-8'))
                # Send product name and seller together (format: "product_name|seller")
                data_to_send = f"{product_name}|{seller}"
                data_padded = data_to_send.encode('utf-8').ljust(1024, b'\0')
                self.client.send(data_padded)
                response = self.client.recv(1024).decode('utf-8')
                
                if not bool(int(response)):
                    messagebox.showerror("Error", "Product not found")
                    self.show_marketplace()
                    return
                
                product_data = self.client.recv(4096).decode('utf-8')
                self.client.send("11".encode('utf-8'))
                
                length = int.from_bytes(self.client.recv(16), 'big')
                image_data = b""
                while len(image_data) < length:
                    chunk = self.client.recv(4096)
                    if not chunk:
                        break
                    image_data += chunk
            
            parts = product_data.split("|")
            if len(parts) != 4:
                messagebox.showerror("Error", "Invalid product data")
                self.show_marketplace()
                return
            seller_name, description, price, quantity = parts
            
            # Display product
            content_frame = tk.Frame(self.root, bg=self.bg_dark)
            content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            # Image
            left_frame = tk.Frame(content_frame, bg=self.card_bg)
            left_frame.pack(side=tk.LEFT, padx=20, pady=10)
            
            if image_data != b"No Image":
                try:
                    img = Image.open(BytesIO(image_data))
                    img.thumbnail((300, 300))
                    photo = ImageTk.PhotoImage(img)
                    img_label = tk.Label(left_frame, image=photo, bg=self.card_bg)
                    img_label.image = photo
                    img_label.pack()
                except:
                    tk.Label(left_frame, text="[No Image]\n📦", 
                            font=('Segoe UI', 16),
                            bg=self.card_bg,
                            fg=self.text_secondary).pack(pady=100, padx=50)
            else:
                tk.Label(left_frame, text="[No Image]\n📦", 
                        font=('Segoe UI', 16),
                        bg=self.card_bg,
                        fg=self.text_secondary).pack(pady=100, padx=50)
            
            # Details
            right_frame = tk.Frame(content_frame, bg=self.bg_dark)
            right_frame.pack(side=tk.LEFT, padx=20, fill=tk.BOTH, expand=True)
            
            tk.Label(right_frame, text=product_name, 
                    font=('Segoe UI', 22, 'bold'),
                    bg=self.bg_dark,
                    fg=self.text_light).pack(anchor="w", pady=(0, 10))
            
            seller_frame = tk.Frame(right_frame, bg=self.bg_dark)
            seller_frame.pack(anchor="w", pady=3)
            
            tk.Label(seller_frame, text=f"👤 Seller: {seller_name}", 
                    font=('Segoe UI', 12),
                    bg=self.bg_dark,
                    fg=self.text_secondary).pack(side=tk.LEFT)
            
            if seller_name != self.username:
                tk.Button(seller_frame, text="View Profile",
                         command=lambda: self.show_user_profile(seller_name),
                         font=('Segoe UI', 9, 'bold'),
                         bg=self.accent,
                         fg='white',
                         border=0,
                         padx=8,
                         pady=3).pack(side=tk.LEFT, padx=10)
            
            tk.Label(right_frame, text=f"💰 ${price}", 
                    font=('Segoe UI', 20, 'bold'),
                    bg=self.bg_dark,
                    fg="#4ade80").pack(anchor="w", pady=10)
            
            tk.Label(right_frame, text=f"📦 Stock: {quantity} available", 
                    font=('Segoe UI', 12),
                    bg=self.bg_dark,
                    fg=self.text_secondary).pack(anchor="w", pady=5)
            
            tk.Label(right_frame, text="Description:", 
                    font=('Segoe UI', 13, 'bold'),
                    bg=self.bg_dark,
                    fg=self.text_light).pack(anchor="w", pady=(20, 5))
            
            desc_text = scrolledtext.ScrolledText(right_frame, height=8, width=40, 
                                                  font=('Segoe UI', 10),
                                                  bg=self.card_bg,
                                                  fg=self.text_light,
                                                  borderwidth=0)
            desc_text.pack(anchor="w", fill=tk.BOTH, expand=True, pady=(0, 15))
            desc_text.insert("1.0", description)
            desc_text.config(state=tk.DISABLED)
            
            # Action buttons
            btn_frame = tk.Frame(right_frame, bg=self.bg_dark)
            btn_frame.pack(anchor="w", pady=10)
            
            # Buy button or Delete button
            if seller_name == self.username:
                # Owner sees delete button
                def delete_product():
                    if messagebox.askyesno("Delete Product", f"Are you sure you want to delete '{product_name}'?"):
                        try:
                            self.client.send("23".encode('utf-8'))
                            product_padded = product_name.encode('utf-8').ljust(1024, b'\0')
                            self.client.send(product_padded)
                            response = self.client.recv(1).decode('utf-8')
                            
                            if response == '1':
                                messagebox.showinfo("Success", "Product deleted successfully!")
                                self.show_marketplace()
                            else:
                                messagebox.showerror("Error", "Failed to delete product")
                        except Exception as e:
                            messagebox.showerror("Error", f"Failed to delete: {str(e)}")
                
                tk.Button(btn_frame, text="🗑️ Delete Product",
                         command=delete_product,
                         font=('Segoe UI', 12, 'bold'),
                         bg="#ef4444",
                         fg='white',
                         border=0,
                         padx=25,
                         pady=12,
                         cursor='hand2').pack(side=tk.LEFT)
            else:
                # Buyer sees buy button
                def buy_product():
                    try:
                        if not self.client:
                            messagebox.showerror("Error", "Not connected to server")
                            return
                        
                        # Check if already purchased from this seller
                        with self.client_lock:
                            self.client.send("24".encode('utf-8'))
                            # Send product name and seller (format: "product_name|seller")
                            data_to_send = f"{product_name}|{seller_name}"
                            product_padded = data_to_send.encode('utf-8').ljust(1024, b'\0')
                            self.client.send(product_padded)
                            already_purchased = self.client.recv(1).decode('utf-8') == '1'
                        
                        # Store product context for the proposal dialog
                        self.current_product_context = {
                            'name': product_name,
                            'seller': seller_name
                        }
                        
                        # Check if chat already exists
                        chat_exists = seller_name in self.active_chats
                        
                        # Create auto-message
                        auto_msg = f"Hi! I want to buy {product_name}"
                        
                        # Open chat with seller and send auto-message
                        self.start_chat_with(seller_name, product_name, auto_msg)
                        
                        # Show alert only if:
                        # 1. First time opening chat (not chat_exists), OR
                        # 2. Already purchased this product (already_purchased)
                        if not chat_exists or already_purchased:
                            if already_purchased:
                                messagebox.showinfo("Notice", f"You've already purchased this product!\nChat opened with {seller_name} if you want to buy more.")
                            else:
                                messagebox.showinfo("Purchase", f"Chat opened with {seller_name}!\nUse the 'Propose Purchase' button to schedule a purchase date.")
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to initiate purchase: {str(e)}")
                
                tk.Button(btn_frame, text="🛒 Buy Now",
                         command=buy_product,
                         font=('Segoe UI', 12, 'bold'),
                         bg=self.accent,
                         fg='white',
                         activebackground=self.accent_hover,
                         activeforeground='white',
                         border=0,
                         padx=25,
                         pady=12,
                         cursor='hand2').pack(side=tk.LEFT)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load details: {str(e)}")
    
    def show_sell_product(self):
        self.clear_window()
        
        header_frame = tk.Frame(self.root, bg=self.bg_dark)
        header_frame.pack(fill=tk.X, padx=20, pady=20)
        
        tk.Label(header_frame, text="Sell a Product", 
                font=('Segoe UI', 20, 'bold'),
                bg=self.bg_dark,
                fg=self.text_light).pack(side=tk.LEFT)
        
        back_btn = self.create_nav_button(header_frame, "← Back", self.show_marketplace)
        back_btn.pack(side=tk.RIGHT)
        
        # Scrollable content
        canvas = tk.Canvas(self.root, bg=self.bg_dark, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        content_frame = tk.Frame(canvas, bg=self.bg_dark)
        
        content_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=content_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=20)
        scrollbar.pack(side="right", fill="y")
        
        # Form in content frame
        form_frame = tk.Frame(content_frame, bg=self.card_bg)
        form_frame.pack(fill=tk.BOTH, padx=30, pady=20)
        
        tk.Label(form_frame, text="Product Name:", 
                font=('Segoe UI', 11, 'bold'),
                bg=self.card_bg,
                fg=self.text_light).pack(pady=(15, 5), padx=15, anchor="w")
        product_entry = tk.Entry(form_frame, width=60, font=('Segoe UI', 11), bg='white', fg='black')
        product_entry.pack(pady=(0, 5), padx=15, ipady=5)
        
        tk.Label(form_frame, text="💡 Tip: Listing an existing product will restock it by adding to the quantity", 
                font=('Segoe UI', 9),
                bg=self.card_bg,
                fg=self.text_secondary).pack(pady=(0, 10), padx=15, anchor="w")
        
        tk.Label(form_frame, text="Description:", 
                font=('Segoe UI', 11, 'bold'),
                bg=self.card_bg,
                fg=self.text_light).pack(pady=(10, 5), padx=15, anchor="w")
        desc_text = scrolledtext.ScrolledText(form_frame, height=6, width=60, 
                                             font=('Segoe UI', 10),
                                             bg='white',
                                             fg='black')
        desc_text.pack(pady=(0, 10), padx=15)
        
        tk.Label(form_frame, text="Price ($):", 
                font=('Segoe UI', 11, 'bold'),
                bg=self.card_bg,
                fg=self.text_light).pack(pady=(10, 5), padx=15, anchor="w")
        price_entry = tk.Entry(form_frame, width=60, font=('Segoe UI', 11), bg='white', fg='black')
        price_entry.pack(pady=(0, 10), padx=15, ipady=5)
        
        tk.Label(form_frame, text="Quantity:", 
                font=('Segoe UI', 11, 'bold'),
                bg=self.card_bg,
                fg=self.text_light).pack(pady=(10, 5), padx=15, anchor="w")
        quantity_entry = tk.Entry(form_frame, width=60, font=('Segoe UI', 11), bg='white', fg='black')
        quantity_entry.insert(0, "1")
        quantity_entry.pack(pady=(0, 10), padx=15, ipady=5)
        
        image_label_var = tk.StringVar(value="No image selected")
        tk.Label(form_frame, textvariable=image_label_var, 
                font=('Segoe UI', 10),
                bg=self.card_bg,
                fg=self.text_secondary).pack(pady=10, padx=15)
        
        selected_image = [None]
        
        def select_image():
            file_path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.png *.jpeg"), ("All Files", "*.*")])
            if file_path:
                selected_image[0] = file_path
                image_label_var.set(f"Selected: {os.path.basename(file_path)}")
        
        upload_btn = tk.Button(form_frame, text="📷 Upload Image",
                              command=select_image,
                              font=('Segoe UI', 10, 'bold'),
                              bg=self.bg_light,
                              fg='white',
                              activebackground=self.accent,
                              activeforeground='white',
                              border=0,
                              padx=20,
                              pady=8,
                              cursor='hand2')
        upload_btn.pack(pady=(5, 15), padx=15)
        
        def submit_product():
            product_name = product_entry.get().strip()
            description = desc_text.get("1.0", tk.END).strip()
            price = price_entry.get().strip()
            quantity = quantity_entry.get().strip()
            
            if not all([product_name, description, price, quantity]):
                messagebox.showerror("Error", "Please fill all fields")
                return
            
            try:
                if not self.client:
                    messagebox.showerror("Error", "Not connected to server")
                    return
                    
                price = float(price)
                quantity = int(quantity)
                
                if price < 0 or quantity < 1:
                    messagebox.showerror("Error", "Invalid price or quantity")
                    return
                
                # Read image
                image_data = "No Image"
                if selected_image[0]:
                    try:
                        with open(selected_image[0], 'rb') as f:
                            image_data = base64.b64encode(f.read()).decode('utf-8')
                    except:
                        image_data = "No Image"
                
                # Send sell command with all product data
                with self.client_lock:
                    self.client.send("2".encode('utf-8'))
                    
                    # Send product name (padded to 1024 bytes)
                    product_name_padded = product_name.encode('utf-8').ljust(1024, b'\0')
                    self.client.send(product_name_padded)
                    response = self.client.recv(1024).decode('utf-8')  # Server always allows
                    
                    # Send product data
                    data = f"{product_name}|{image_data}|{description}|{price}|{quantity}"
                    data_json = json.dumps(data)
                    
                    self.client.send(len(data_json).to_bytes(4, 'big'))
                    self.client.sendall(data_json.encode('utf-8'))
                    
                    response = self.client.recv(1024).decode('utf-8')
                
                if bool(int(response)):
                    messagebox.showinfo("Success", "Product listed successfully! If this product already existed, stock has been added.")
                    self.show_marketplace()
                else:
                    messagebox.showerror("Error", "Failed to list product")
            except ValueError:
                messagebox.showerror("Error", "Invalid price or quantity format")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to sell product: {str(e)}")
        
        list_btn = tk.Button(form_frame, text="✓ List Product",
                            command=submit_product,
                            font=('Segoe UI', 12, 'bold'),
                            bg=self.accent,
                            fg='white',
                            activebackground=self.accent_hover,
                            activeforeground='white',
                            border=0,
                            padx=30,
                            pady=12,
                            cursor='hand2')
        list_btn.pack(pady=20, padx=15)
    
    def show_history(self):
        self.clear_window()
        
        header_frame = tk.Frame(self.root, bg=self.bg_dark)
        header_frame.pack(fill=tk.X, padx=20, pady=20)
        
        tk.Label(header_frame, text="Sales History", 
                font=('Segoe UI', 20, 'bold'),
                bg=self.bg_dark,
                fg=self.text_light).pack(side=tk.LEFT)
        
        back_btn = self.create_nav_button(header_frame, "← Back", self.show_marketplace)
        back_btn.pack(side=tk.RIGHT)
        
        content_frame = tk.Frame(self.root, bg=self.bg_dark)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        try:
            if not self.client:
                messagebox.showerror("Error", "Not connected to server")
                self.show_marketplace()
                return
                
            # Send history command with lock to prevent concurrent access
            with self.client_lock:
                self.client.send("4".encode('utf-8'))
                prev = self.client.recv(1).decode('utf-8')  # Only receive 1 byte
                
                if prev == "1":
                    length = int.from_bytes(self.client.recv(16), 'big')
                    history_data = b""
                    while len(history_data) < length:
                        packet = self.client.recv(4096)
                        if not packet:
                            break
                        history_data += packet
                    
                    if not history_data:
                        history = {}
                    else:
                        history = json.loads(history_data.decode('utf-8'))
                else:
                    history = {}
            
            # Display history outside lock
            if history and any(history.values()):  # Check if there are any items
                tk.Label(content_frame, text="Your Selling History:", 
                        font=('Segoe UI', 14, 'bold'),
                        bg=self.bg_dark,
                        fg=self.text_light).pack(anchor="w", pady=(0, 15))
                
                for key, items in history.items():
                    if items:  # Only show if there are items
                        for item in items:
                            item_card = tk.Frame(content_frame, bg=self.card_bg)
                            item_card.pack(fill=tk.X, pady=5)
                            tk.Label(item_card, text=f"✓ {item}", 
                                    font=('Segoe UI', 11),
                                    bg=self.card_bg,
                                    fg=self.text_light).pack(anchor="w", padx=15, pady=10)
            else:
                tk.Label(content_frame, text="📜 No sales history", 
                        font=('Segoe UI', 14),
                        bg=self.bg_dark,
                        fg=self.text_secondary).pack(pady=50)
        
        except Exception as e:
            print(f"History error: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to load history: {str(e)}")
            self.show_marketplace()

    
    def debounce_search(self):
        if self.search_debounce_id:
            self.root.after_cancel(self.search_debounce_id)
        
        # wait 300ms after user stops typing
        self.search_debounce_id = self.root.after(300, self.filter_products)
    
    def filter_products(self):
        if not hasattr(self, 'all_products_data') or not self.all_products_data:
            return
        
        search_query = self.search_var.get().lower().strip()
        
        # Just reload the products view (more efficient)
        if hasattr(self, 'all_products_data'):
            # Store current data
            temp_data = self.all_products_data
            # Call show_browse_products which will use the cached data
            self.show_browse_products(embedded=True)
    
    def check_new_messages_for_user(self, username):
        """Check if user has sent new messages since last interaction"""
        try:
            with self.client_lock:
                self.client.send("29".encode('utf-8'))  # New command to check new messages
                user_padded = username.encode('utf-8').ljust(1024, b'\0')
                self.client.send(user_padded)
                response = self.client.recv(1).decode('utf-8')
                return response == '1'
        except:
            return False
    

    
    def show_profile_editor(self):
        profile_window = tk.Toplevel(self.root)
        profile_window.title("Edit Profile")
        profile_window.geometry("600x800")
        profile_window.configure(bg=self.bg_dark)
        
        tk.Label(profile_window, text="✏️ Edit Your Profile",
                font=('Segoe UI', 20, 'bold'),
                bg=self.bg_dark,
                fg=self.accent).pack(pady=20)
        
        # Profile picture upload
        pfp_frame = tk.Frame(profile_window, bg=self.card_bg)
        pfp_frame.pack(pady=10, padx=20, fill=tk.X)
        
        self.profile_pic_data = None
        self.pfp_label = tk.Label(pfp_frame, text="👤",
                                  font=('Segoe UI', 60),
                                  bg=self.card_bg,
                                  fg=self.text_secondary)
        self.pfp_label.pack(pady=10)
        
        def upload_picture():
            from tkinter import filedialog
            file_path = filedialog.askopenfilename(
                title="Select Profile Picture",
                filetypes=[("Image files", "*.jpg *.jpeg *.png *.gif *.bmp")]
            )
            if file_path:
                try:
                    img = Image.open(file_path)
                    img.thumbnail((150, 150))
                    photo = ImageTk.PhotoImage(img)
                    self.pfp_label.config(image=photo, text="")
                    self.pfp_label.image = photo
                    
                    # Store as base64
                    from io import BytesIO
                    buffer = BytesIO()
                    img.save(buffer, format="PNG")
                    self.profile_pic_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to load image: {e}")
        
        tk.Button(pfp_frame, text="📷 Upload Picture",
                 command=upload_picture,
                 font=('Segoe UI', 10, 'bold'),
                 bg=self.accent,
                 fg='white',
                 border=0,
                 padx=15,
                 pady=8).pack(pady=10)
        
        # Real name
        tk.Label(profile_window, text="Full Name:",
                font=('Segoe UI', 11, 'bold'),
                bg=self.bg_dark,
                fg=self.text_light).pack(pady=(20, 5))
        name_entry = tk.Entry(profile_window, width=40, font=('Segoe UI', 11))
        name_entry.pack(pady=5)
        
        # Bio
        tk.Label(profile_window, text="Bio:",
                font=('Segoe UI', 11, 'bold'),
                bg=self.bg_dark,
                fg=self.text_light).pack(pady=(20, 5))
        bio_text = tk.Text(profile_window, height=6, width=50,
                          font=('Segoe UI', 10),
                          wrap=tk.WORD)
        bio_text.pack(pady=5, padx=20)
        
        # Load current profile data
        def load_current_profile():
            try:
                with self.client_lock:
                    self.client.send("18".encode('utf-8'))
                    user_padded = self.username.encode('utf-8').ljust(1024, b'\0')
                    self.client.send(user_padded)
                    response = self.client.recv(4096).decode('utf-8')
                    
                    if response.startswith("profile:"):
                        profile = json.loads(response[8:])
                        if profile.get('real_name'):
                            name_entry.insert(0, profile['real_name'])
                        if profile.get('bio'):
                            bio_text.insert("1.0", profile['bio'])
                        if profile.get('profile_picture'):
                            try:
                                img_data = base64.b64decode(profile['profile_picture'])
                                img = Image.open(BytesIO(img_data))
                                img.thumbnail((150, 150))
                                photo = ImageTk.PhotoImage(img)
                                self.pfp_label.config(image=photo, text="")
                                self.pfp_label.image = photo
                                self.profile_pic_data = profile['profile_picture']
                            except:
                                pass
            except Exception as e:
                print(f"Error loading profile: {e}")
        
        threading.Thread(target=load_current_profile, daemon=True).start()  # daemon dies when window closes
        
        # Save button
        def save_profile():
            real_name = name_entry.get().strip()
            bio = bio_text.get("1.0", tk.END).strip()
            
            if not real_name:
                messagebox.showerror("Error", "Please enter your full name")
                return
            
            def do_save():
                try:
                    with self.client_lock:
                        self.client.send("31".encode('utf-8'))  # Update profile command
                        profile_data = json.dumps({
                            'username': self.username,
                            'real_name': real_name,
                            'bio': bio,
                            'profile_picture': self.profile_pic_data
                        })
                        self.client.send(len(profile_data).to_bytes(16, 'big'))
                        self.client.sendall(profile_data.encode('utf-8'))
                        response = self.client.recv(1).decode('utf-8')
                        
                        if response == '1':
                            self.root.after(0, lambda: messagebox.showinfo("Success", "Profile updated!"))
                            self.root.after(0, lambda: profile_window.destroy())
                        else:
                            self.root.after(0, lambda: messagebox.showerror("Error", "Failed to update profile"))
                except Exception as e:
                    self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            
            threading.Thread(target=do_save, daemon=True).start()
        
        tk.Button(profile_window, text="💾 Save Profile",
                 command=save_profile,
                 font=('Segoe UI', 12, 'bold'),
                 bg=self.accent,
                 fg='white',
                 border=0,
                 padx=30,
                 pady=12).pack(pady=30)
    
    def show_my_products_manager(self):
        self.clear_window()
        
        # Header
        header_frame = tk.Frame(self.root, bg=self.bg_dark)
        header_frame.pack(fill=tk.X, padx=20, pady=20)
        
        tk.Label(header_frame, text="👤 My Profile & Products",
                font=('Segoe UI', 20, 'bold'),
                bg=self.bg_dark,
                fg=self.text_light).pack(side=tk.LEFT)
        
        back_btn = self.create_nav_button(header_frame, "← Back", self.show_marketplace)
        back_btn.pack(side=tk.RIGHT)
        
        # Edit profile button
        self.create_nav_button(header_frame, "✏️ Edit Profile", self.show_profile_editor).pack(side=tk.RIGHT, padx=10)
        
        # Scrollable content
        canvas = tk.Canvas(self.root, bg=self.bg_dark, highlightthickness=0)
        scrollbar = tk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.bg_dark)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Loading message
        loading_label = tk.Label(scrollable_frame, text="Loading your products...",
                                bg=self.bg_dark,
                                fg=self.text_light)
        loading_label.pack(pady=20)
        
        def load_products():
            try:
                with self.client_lock:
                    self.client.send("11".encode('utf-8'))
                    user_padded = self.username.encode('utf-8').ljust(1024, b'\0')
                    self.client.send(user_padded)
                    
                    response = self.client.recv(1).decode('utf-8')
                    if response == '1':
                        length = int.from_bytes(self.client.recv(16), 'big')
                        data = b""
                        while len(data) < length:
                            packet = self.client.recv(4096)
                            if not packet:
                                break
                            data += packet
                        
                        if data:
                            products = json.loads(data.decode('utf-8'))
                            self.root.after(0, lambda: self.display_my_products(scrollable_frame, loading_label, products))
                        else:
                            self.root.after(0, lambda: loading_label.config(text="No products listed"))
                    else:
                        self.root.after(0, lambda: loading_label.config(text="Failed to load products"))
            except Exception as e:
                print(f"Error loading products: {e}")
                self.root.after(0, lambda: loading_label.config(text=f"Error: {e}"))
        
        threading.Thread(target=load_products, daemon=True).start()
        
        canvas.pack(side="left", fill="both", expand=True, padx=20, pady=20)
        scrollbar.pack(side="right", fill="y")
    
    def display_my_products(self, parent, loading_label, products):
        """Display user's products with edit buttons"""
        if not parent.winfo_exists():
            return
        
        loading_label.destroy()
        
        if not products:
            tk.Label(parent, text="No products listed yet",
                    bg=self.bg_dark,
                    fg=self.text_secondary).pack(pady=20)
            return
        
        # Current products
        tk.Label(parent, text="📦 Current Products (In Stock)",
                font=('Segoe UI', 16, 'bold'),
                bg=self.bg_dark,
                fg=self.text_light).pack(pady=(0, 10), anchor="w", padx=20)
        
        current_products = [p for p in products if p['quantity'] > 0]
        sold_out_products = [p for p in products if p['quantity'] == 0]
        
        for prod in current_products:
            self.create_product_edit_card(parent, prod)
        
        if not current_products:
            tk.Label(parent, text="No products currently in stock",
                    bg=self.bg_dark,
                    fg=self.text_secondary).pack(pady=10)
        
        # Sold out products
        if sold_out_products:
            tk.Label(parent, text="📦 Sold Out Products",
                    font=('Segoe UI', 16, 'bold'),
                    bg=self.bg_dark,
                    fg=self.text_secondary).pack(pady=(30, 10), anchor="w", padx=20)
            
            for prod in sold_out_products:
                self.create_product_edit_card(parent, prod, sold_out=True)
    
    def create_product_edit_card(self, parent, product, sold_out=False):
        """Create a product card with edit button"""
        card = tk.Frame(parent, bg=self.card_bg)
        card.pack(fill=tk.X, pady=5, padx=20)
        
        content = tk.Frame(card, bg=self.card_bg)
        content.pack(fill=tk.X, padx=15, pady=15)
        
        # Product info
        left_frame = tk.Frame(content, bg=self.card_bg)
        left_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        name_text = product['name']
        if sold_out:
            name_text += " (SOLD OUT)"
        
        tk.Label(left_frame, text=name_text,
                font=('Segoe UI', 13, 'bold'),
                bg=self.card_bg,
                fg=self.text_light if not sold_out else self.text_secondary).pack(anchor="w", pady=2)
        
        tk.Label(left_frame, text=f"💰 ${product['price']} | ⭐ {product['rating']:.1f}/5 | Stock: {product['quantity']}",
                font=('Segoe UI', 10),
                bg=self.card_bg,
                fg=self.text_secondary).pack(anchor="w", pady=2)
        
        # Edit button
        tk.Button(content, text="✏️ Edit",
                 command=lambda: self.show_edit_product_dialog(product),
                 font=('Segoe UI', 10, 'bold'),
                 bg=self.accent,
                 fg='white',
                 border=0,
                 padx=15,
                 pady=8).pack(side=tk.RIGHT)
    
    def show_edit_product_dialog(self, product):
        """Show dialog to edit product details"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit {product['name']}")
        dialog.geometry("500x650")
        dialog.configure(bg=self.bg_dark)
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog, text=f"✏️ Edit Product",
                font=('Segoe UI', 18, 'bold'),
                bg=self.bg_dark,
                fg=self.accent).pack(pady=20)
        
        tk.Label(dialog, text=f"Product: {product['name']}",
                font=('Segoe UI', 12),
                bg=self.bg_dark,
                fg=self.text_light).pack(pady=10)
        
        # Stock quantity
        tk.Label(dialog, text="Stock Quantity:",
                font=('Segoe UI', 11, 'bold'),
                bg=self.bg_dark,
                fg=self.text_light).pack(pady=(15, 5))
        stock_entry = tk.Entry(dialog, width=30, font=('Segoe UI', 11))
        stock_entry.insert(0, str(product['quantity']))
        stock_entry.pack(pady=5)
        
        # Price
        tk.Label(dialog, text="Price ($):",
                font=('Segoe UI', 11, 'bold'),
                bg=self.bg_dark,
                fg=self.text_light).pack(pady=(15, 5))
        price_entry = tk.Entry(dialog, width=30, font=('Segoe UI', 11))
        price_entry.insert(0, str(product['price']))
        price_entry.pack(pady=5)
        
        # Description
        tk.Label(dialog, text="Description:",
                font=('Segoe UI', 11, 'bold'),
                bg=self.bg_dark,
                fg=self.text_light).pack(pady=(15, 5))
        desc_text = tk.Text(dialog, height=6, width=45, font=('Segoe UI', 10), wrap=tk.WORD)
        desc_text.pack(pady=5, padx=20)
        
        # Image upload
        tk.Label(dialog, text="Product Image:",
                font=('Segoe UI', 11, 'bold'),
                bg=self.bg_dark,
                fg=self.text_light).pack(pady=(15, 5))
        
        new_image_data = [None]  # Use list to allow modification in nested function
        
        def upload_image():
            from tkinter import filedialog
            file_path = filedialog.askopenfilename(
                title="Select Product Image",
                filetypes=[("Image files", "*.jpg *.jpeg *.png *.gif *.bmp")]
            )
            if file_path:
                try:
                    img = Image.open(file_path)
                    img.thumbnail((200, 200))
                    from io import BytesIO
                    buffer = BytesIO()
                    img.save(buffer, format="PNG")
                    new_image_data[0] = buffer.getvalue()
                    messagebox.showinfo("Success", "Image uploaded! Click Save to apply changes.")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to load image: {e}")
        
        tk.Button(dialog, text="📷 Upload New Image",
                 command=upload_image,
                 font=('Segoe UI', 10, 'bold'),
                 bg=self.accent,
                 fg='white',
                 border=0,
                 padx=15,
                 pady=8).pack(pady=10)
        
        # Load current description
        def load_description():
            try:
                with self.client_lock:
                    self.client.send("3".encode('utf-8'))
                    # Send product name and seller (seller is current user for editing own product)
                    data_to_send = f"{product['name']}|{self.username}"
                    prod_padded = data_to_send.encode('utf-8').ljust(1024, b'\0')
                    self.client.send(prod_padded)
                    response = self.client.recv(1).decode('utf-8')
                    
                    if response == '1':
                        length = int.from_bytes(self.client.recv(16), 'big')
                        data = b""
                        while len(data) < length:
                            packet = self.client.recv(4096)
                            if not packet:
                                break
                            data += packet
                        
                        if data:
                            prod_details = json.loads(data.decode('utf-8'))
                            if prod_details.get('description'):
                                self.root.after(0, lambda: desc_text.insert("1.0", prod_details['description']))
            except Exception as e:
                print(f"Error loading description: {e}")
        
        threading.Thread(target=load_description, daemon=True).start()
        
        # Save button
        def save_changes():
            try:
                new_stock = int(stock_entry.get())
                new_price = float(price_entry.get())
                new_description = desc_text.get("1.0", tk.END).strip()
                
                if new_stock < 0 or new_price < 0:
                    messagebox.showerror("Error", "Stock and price must be positive")
                    return
                
                def do_update():
                    try:
                        with self.client_lock:
                            self.client.send("32".encode('utf-8'))  # Update product command
                            update_data = json.dumps({
                                'product_name': product['name'],
                                'quantity': new_stock,
                                'price': new_price,
                                'description': new_description,
                                'image': base64.b64encode(new_image_data[0]).decode('utf-8') if new_image_data[0] else None
                            })
                            self.client.send(len(update_data).to_bytes(16, 'big'))
                            self.client.sendall(update_data.encode('utf-8'))
                            response = self.client.recv(1).decode('utf-8')
                            
                            if response == '1':
                                self.root.after(0, lambda: messagebox.showinfo("Success", "Product updated!"))
                                self.root.after(0, lambda: dialog.destroy())
                                self.root.after(0, lambda: self.show_my_products_manager())
                            else:
                                self.root.after(0, lambda: messagebox.showerror("Error", "Failed to update product"))
                    except Exception as e:
                        self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
                
                threading.Thread(target=do_update, daemon=True).start()
                
            except ValueError:
                messagebox.showerror("Error", "Invalid stock or price format")
        
        tk.Button(dialog, text="💾 Save Changes",
                 command=save_changes,
                 font=('Segoe UI', 12, 'bold'),
                 bg=self.accent,
                 fg='white',
                 border=0,
                 padx=30,
                 pady=12).pack(pady=20)
    
    def show_messages(self):
        """Show messages/chat inbox"""
        self.clear_window()
        
        # Header
        header_frame = tk.Frame(self.root, bg=self.bg_dark)
        header_frame.pack(fill=tk.X, padx=20, pady=20)
        
        tk.Label(header_frame, text="💬 Messages", 
                font=('Segoe UI', 20, 'bold'),
                bg=self.bg_dark,
                fg=self.text_light).pack(side=tk.LEFT)
        
        back_btn = self.create_nav_button(header_frame, "← Back", self.show_marketplace)
        back_btn.pack(side=tk.RIGHT)
        
        # Get conversation list from server (with minimal loading)
        try:
            # Show loading indicator
            loading_frame = tk.Frame(self.root, bg=self.bg_dark)
            loading_frame.pack(expand=True)
            tk.Label(loading_frame, text="Loading conversations...", 
                    font=('Segoe UI', 12),
                    bg=self.bg_dark,
                    fg=self.text_secondary).pack(pady=20)
            self.root.update()
            
            with self.client_lock:
                self.client.send("10".encode('utf-8'))  # Command 10: Get conversations
                length = int.from_bytes(self.client.recv(16), 'big')
                conv_data = b""
                while len(conv_data) < length:
                    packet = self.client.recv(4096)
                    if not packet:
                        break
                    conv_data += packet
                
                if conv_data:
                    self.conversations = json.loads(conv_data.decode('utf-8'))
            
            # Remove loading indicator
            loading_frame.destroy()
            
            # Display conversations
            canvas = tk.Canvas(self.root, bg=self.bg_dark, highlightthickness=0)
            scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
            scrollable_frame = tk.Frame(canvas, bg=self.bg_dark)
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            if not self.conversations:
                empty_frame = tk.Frame(scrollable_frame, bg=self.bg_dark)
                empty_frame.pack(pady=50, padx=20)
                tk.Label(empty_frame, 
                        text="📭 No conversations yet", 
                        font=('Segoe UI', 16, 'bold'),
                        bg=self.bg_dark,
                        fg=self.text_secondary).pack(pady=10)
                tk.Label(empty_frame, 
                        text="Start chatting with sellers on product pages!", 
                        font=('Segoe UI', 12),
                        bg=self.bg_dark,
                        fg=self.text_secondary).pack(pady=5)
            else:
                for conv_user in self.conversations:
                    self.create_conversation_card(scrollable_frame, conv_user)
            
            canvas.pack(side="left", fill="both", expand=True, padx=20, pady=20)
            scrollbar.pack(side="right", fill="y")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load conversations: {str(e)}")
    
    def create_conversation_card(self, parent, username):
        """Create a conversation card for the messages inbox"""
        card = tk.Frame(parent, bg=self.card_bg, relief="flat", borderwidth=0)
        card.pack(fill=tk.X, pady=8, padx=10)
        
        content = tk.Frame(card, bg=self.card_bg)
        content.pack(fill=tk.X, padx=15, pady=15)
        
        # User info
        left_frame = tk.Frame(content, bg=self.card_bg)
        left_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Check for new messages since last login
        has_new = self.check_new_messages_for_user(username)
        
        username_text = f"👤 {username}"
        if has_new:
            username_text = f"🔴 {username}"
        
        tk.Label(left_frame, text=username_text, 
                font=('Segoe UI', 14, 'bold'),
                bg=self.card_bg,
                fg=self.text_light).pack(anchor="w", pady=2)
        
        unread = self.unread_messages.get(username, 0)
        if unread > 0:
            tk.Label(left_frame, text=f"📩 {unread} unread message{'s' if unread > 1 else ''}", 
                    font=('Segoe UI', 10),
                    bg=self.card_bg,
                    fg=self.accent).pack(anchor="w", pady=2)
        elif has_new:
            tk.Label(left_frame, text="New messages since last login", 
                    font=('Segoe UI', 10),
                    bg=self.card_bg,
                    fg=self.accent).pack(anchor="w", pady=2)
        
        # Open chat button
        open_btn = tk.Button(content, text="Open Chat →",
                           command=lambda: self.start_chat_with(username),
                           font=('Segoe UI', 10, 'bold'),
                           bg=self.accent,
                           fg='white',
                           activebackground=self.accent_hover,
                           activeforeground='white',
                           border=0,
                           padx=15,
                           pady=8,
                           cursor='hand2')
        open_btn.pack(side=tk.RIGHT)
    
    def start_message_checker(self):
        """Start background thread to check for new messages"""
        def check_messages():
            while self.client and self.username:
                try:
                    # Check for unread messages
                    with self.client_lock:
                        self.client.send("5".encode('utf-8'))
                        response = self.client.recv(1).decode('utf-8')
                        
                        if response == '1':
                            length = int.from_bytes(self.client.recv(16), 'big')
                            data = b""
                            while len(data) < length:
                                packet = self.client.recv(4096)
                                if not packet:
                                    break
                                data += packet
                            
                            if data:
                                unread = json.loads(data.decode('utf-8'))
                                total_unread = sum(unread.values())
                                
                                # Update button text with badge
                                if total_unread > 0:
                                    self.root.after(0, lambda: self.messages_btn.config(
                                        text=f"Messages ({total_unread})",
                                        bg="#ef4444"  # Red to indicate new messages
                                    ))
                                else:
                                    self.root.after(0, lambda: self.messages_btn.config(
                                        text="Messages",
                                        bg=self.accent
                                    ))
                except:
                    pass
                
                # Check every 5 seconds
                import time
                time.sleep(5)
        
        threading.Thread(target=check_messages, daemon=True).start()
    
    def logout(self):
        # Unregister from server
        try:
            if self.client and self.username:
                with self.client_lock:
                    self.client.send("9".encode('utf-8'))  # Logout command
        except:
            pass
        
        # Close connection
        try:
            self.client.close()
        except:
            pass
        self.client = None
        self.username = None
        self.show_login_screen()
    

    
    def start_chat_with(self, other_user, product_name=None, auto_message=None):
        """Open chat window using new clean chat system"""
        # Check if already open
        if other_user in self.active_chats:
            try:
                self.active_chats[other_user].window.lift()
                # Update product name if provided
                if product_name:
                    self.active_chats[other_user].product_name = product_name
                # Send auto message if chat already open
                if auto_message:
                    self.active_chats[other_user].send_auto_message(auto_message)
                return
            except:
                del self.active_chats[other_user]
        
        # Create new chat window with auto message (using ChatWindow class from ChatSystem.py)
        chat = ChatWindow(self, other_user, product_name, auto_message)
        self.active_chats[other_user] = chat
    
    def show_user_profile(self, username):
        """Display user profile with current and previous products"""
        self.clear_window()
        
        header_frame = tk.Frame(self.root, bg=self.bg_dark)
        header_frame.pack(fill=tk.X, padx=20, pady=20)
        
        tk.Label(header_frame, text=f"Profile: {username}", 
                font=('Segoe UI', 20, 'bold'),
                bg=self.bg_dark,
                fg=self.text_light).pack(side=tk.LEFT)
        
        back_btn = self.create_nav_button(header_frame, "← Back", self.show_marketplace)
        back_btn.pack(side=tk.RIGHT)
        
        # Add Edit Profile button if viewing own profile
        if username.lower() == self.username.lower():
            edit_btn = self.create_nav_button(header_frame, "✏️ Edit Profile", 
                                             lambda: self.show_edit_profile())
            edit_btn.pack(side=tk.RIGHT, padx=10)
        
        # Get user info and products
        try:
            with self.client_lock:
                self.client.send("18".encode('utf-8'))
                # Pad username to 1024 bytes
                username_padded = username.encode('utf-8').ljust(1024, b'\0')
                self.client.send(username_padded)
                
                # Check if profile exists
                success = self.client.recv(1).decode('utf-8')
                if success != '1':
                    messagebox.showerror("Error", "Profile not found")
                    self.show_marketplace()
                    return
                
                # Receive length-prefixed data
                length = int.from_bytes(self.client.recv(16), 'big')
                profile_data = b""
                while len(profile_data) < length:
                    chunk = self.client.recv(4096)
                    if not chunk:
                        break
                    profile_data += chunk
            
            if profile_data:
                try:
                    data = json.loads(profile_data.decode('utf-8'))
                except json.JSONDecodeError as e:
                    messagebox.showerror("Error", f"Failed to parse profile data: {e}")
                    self.show_marketplace()
                    return
                
                # User info section
                info_frame = tk.Frame(self.root, bg=self.card_bg)
                info_frame.pack(fill=tk.X, padx=20, pady=10)
                
                content = tk.Frame(info_frame, bg=self.card_bg)
                content.pack(padx=20, pady=20)
                
                # Create left frame for profile picture and right frame for info
                layout_frame = tk.Frame(content, bg=self.card_bg)
                layout_frame.pack(fill=tk.X)
                
                # Profile picture on left
                pic_frame = tk.Frame(layout_frame, bg=self.card_bg)
                pic_frame.pack(side=tk.LEFT, padx=(0, 20))
                
                profile_pic_b64 = data.get('profile_picture')
                if profile_pic_b64 and profile_pic_b64 != "None":
                    try:
                        pic_data = base64.b64decode(profile_pic_b64)
                        pic_image = Image.open(BytesIO(pic_data))
                        pic_image = pic_image.resize((120, 120), Image.Resampling.LANCZOS)
                        pic_photo = ImageTk.PhotoImage(pic_image)
                        pic_label = tk.Label(pic_frame, image=pic_photo, bg=self.card_bg)
                        pic_label.image = pic_photo
                        pic_label.pack()
                    except Exception as e:
                        print(f"Error loading profile picture: {e}")
                        # Default avatar
                        tk.Label(pic_frame, text="👤",
                                font=('Segoe UI', 60),
                                bg=self.card_bg,
                                fg=self.text_secondary).pack()
                else:
                    # Default avatar
                    tk.Label(pic_frame, text="👤",
                            font=('Segoe UI', 60),
                            bg=self.card_bg,
                            fg=self.text_secondary).pack()
                
                # Info on right
                info_right = tk.Frame(layout_frame, bg=self.card_bg)
                info_right.pack(side=tk.LEFT, fill=tk.X, expand=True)
                
                real_name = data.get('real_name', 'N/A')
                if not real_name or real_name == "None":
                    real_name = username
                
                tk.Label(info_right, text=f"{real_name}",
                        font=('Segoe UI', 20, 'bold'),
                        bg=self.card_bg,
                        fg=self.text_light).pack(anchor="w", pady=5)
                
                tk.Label(info_right, text=f"@{username}",
                        font=('Segoe UI', 14),
                        bg=self.card_bg,
                        fg=self.text_secondary).pack(anchor="w", pady=2)
                
                avg_rating = data.get('avg_rating', 0) or 0
                tk.Label(info_right, text=f"⭐ Average Rating: {avg_rating:.2f}",
                        font=('Segoe UI', 12),
                        bg=self.card_bg,
                        fg="#ffd700").pack(anchor="w", pady=5)
                
                # Bio if exists
                bio = data.get('bio')
                if bio and bio != "None" and bio.strip():
                    tk.Label(info_right, text=bio,
                            font=('Segoe UI', 11),
                            bg=self.card_bg,
                            fg=self.text_light,
                            wraplength=400,
                            justify=tk.LEFT).pack(anchor="w", pady=5)
                
                # Current products
                tk.Label(self.root, text="Current Products",
                        font=('Segoe UI', 16, 'bold'),
                        bg=self.bg_dark,
                        fg=self.text_light).pack(padx=20, pady=(20, 10), anchor="w")
                
                current_frame = tk.Frame(self.root, bg=self.bg_dark)
                current_frame.pack(fill=tk.BOTH, expand=True, padx=20)
                
                canvas1 = tk.Canvas(current_frame, bg=self.bg_dark, highlightthickness=0)
                scrollbar1 = ttk.Scrollbar(current_frame, orient="vertical", command=canvas1.yview)
                current_content = tk.Frame(canvas1, bg=self.bg_dark)
                
                current_content.bind("<Configure>", lambda e: canvas1.configure(scrollregion=canvas1.bbox("all")))
                canvas1.create_window((0, 0), window=current_content, anchor="nw", width=1100)
                canvas1.configure(yscrollcommand=scrollbar1.set)
                
                canvas1.pack(side="left", fill="both", expand=True)
                scrollbar1.pack(side="right", fill="y")
                
                current_products = data.get('current_products', [])
                is_own_profile = username.lower() == self.username.lower()
                if current_products:
                    for prod in current_products:
                        self.create_profile_product_card(current_content, prod, username, is_own_profile)
                else:
                    tk.Label(current_content, text="No current products",
                            font=('Segoe UI', 11),
                            bg=self.bg_dark,
                            fg=self.text_secondary).pack(pady=20)
                
                # Previous products
                tk.Label(self.root, text="Previous Products (Sold Out)",
                        font=('Segoe UI', 16, 'bold'),
                        bg=self.bg_dark,
                        fg=self.text_light).pack(padx=20, pady=(20, 10), anchor="w")
                
                previous_frame = tk.Frame(self.root, bg=self.bg_dark)
                previous_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
                
                canvas2 = tk.Canvas(previous_frame, bg=self.bg_dark, highlightthickness=0)
                scrollbar2 = ttk.Scrollbar(previous_frame, orient="vertical", command=canvas2.yview)
                previous_content = tk.Frame(canvas2, bg=self.bg_dark)
                
                previous_content.bind("<Configure>", lambda e: canvas2.configure(scrollregion=canvas2.bbox("all")))
                canvas2.create_window((0, 0), window=previous_content, anchor="nw", width=1100)
                canvas2.configure(yscrollcommand=scrollbar2.set)
                
                canvas2.pack(side="left", fill="both", expand=True)
                scrollbar2.pack(side="right", fill="y")
                
                previous_products = data.get('previous_products', [])
                if previous_products:
                    for prod in previous_products:
                        self.create_profile_product_card(previous_content, prod, username, is_own_profile)
                else:
                    tk.Label(previous_content, text="No previous products",
                            font=('Segoe UI', 11),
                            bg=self.bg_dark,
                            fg=self.text_secondary).pack(pady=20)
            else:
                messagebox.showerror("Error", "Could not load profile - server returned invalid response")
                self.show_marketplace()
        except json.JSONDecodeError as e:
            messagebox.showerror("Error", f"Profile data corrupted: {str(e)}")
            print(f"JSON decode error in profile: {e}")
            self.show_marketplace()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load profile: {str(e)}")
            print(f"Profile error: {e}")
            import traceback
            traceback.print_exc()
            self.show_marketplace()
    
    def create_profile_product_card(self, parent, product, seller_username, is_own_profile=False):
        """Create product card for profile view"""
        try:
            card = tk.Frame(parent, bg=self.card_bg, relief="flat", borderwidth=0)
            card.pack(fill=tk.X, pady=8, padx=10)
            
            content = tk.Frame(card, bg=self.card_bg)
            content.pack(fill=tk.X, padx=15, pady=15)
            
            # Product info
            left_frame = tk.Frame(content, bg=self.card_bg)
            left_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            product_name = product.get('product_name', 'Unknown Product')
            tk.Label(left_frame, text=product_name,
                    font=('Segoe UI', 14, 'bold'),
                    bg=self.card_bg,
                    fg=self.text_light).pack(anchor="w", pady=2)
            
            price = float(product.get('price', 0)) if product.get('price') else 0.0
            tk.Label(left_frame, text=f"💰 ${price:.2f}",
                    font=('Segoe UI', 12),
                    bg=self.card_bg,
                    fg="#4ade80").pack(anchor="w", pady=2)
            
            rating = float(product.get('rating', 0)) if product.get('rating') else 0.0
            num_ratings = int(product.get('numberOfRating', 0)) if product.get('numberOfRating') else 0
            tk.Label(left_frame, text=f"⭐ {rating:.2f} ({num_ratings} ratings)",
                    font=('Segoe UI', 11),
                    bg=self.card_bg,
                    fg="#ffd700").pack(anchor="w", pady=2)
            
            quantity = int(product.get('quantity', 0)) if product.get('quantity') else 0
            status = "In Stock" if quantity > 0 else "Sold Out"
            color = "#4ade80" if quantity > 0 else "#ef4444"
            tk.Label(left_frame, text=f"Status: {status} (Qty: {quantity})",
                    font=('Segoe UI', 10),
                    bg=self.card_bg,
                    fg=color).pack(anchor="w", pady=2)
        except Exception as e:
            print(f"Error creating profile product card: {e}")
            # Show error card instead of crashing
            error_card = tk.Frame(parent, bg=self.card_bg)
            error_card.pack(fill=tk.X, pady=8, padx=10)
            tk.Label(error_card, text="Error loading product",
                    font=('Segoe UI', 12),
                    bg=self.card_bg,
                    fg="#ef4444").pack(pady=10)
            return
        
        # Add edit button if viewing own profile
        if is_own_profile:
            tk.Button(content, text="✏️ Edit",
                     command=lambda: self.show_edit_product_dialog(product, seller_username),
                     font=('Segoe UI', 10, 'bold'),
                     bg=self.accent,
                     fg='white',
                     border=0,
                     padx=15,
                     pady=8,
                     cursor='hand2').pack(side=tk.RIGHT)
    
    def show_edit_profile(self):
        """Show dialog to edit user profile"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Profile")
        dialog.geometry("500x600")
        dialog.configure(bg=self.bg_dark)
        
        tk.Label(dialog, text="Edit Your Profile",
                font=('Segoe UI', 18, 'bold'),
                bg=self.bg_dark,
                fg=self.accent).pack(pady=20)
        
        # Get current profile data
        try:
            with self.client_lock:
                self.client.send("18".encode('utf-8'))
                self.client.send(self.username.encode('utf-8').ljust(1024, b'\0'))
                
                success = self.client.recv(1).decode('utf-8')
                if success != '1':
                    messagebox.showerror("Error", "Could not load profile data")
                    dialog.destroy()
                    return
                
                length = int.from_bytes(self.client.recv(16), 'big')
                profile_data = b""
                while len(profile_data) < length:
                    chunk = self.client.recv(4096)
                    if not chunk:
                        break
                    profile_data += chunk
            
            if not profile_data:
                messagebox.showerror("Error", "Could not load profile data")
                dialog.destroy()
                return
            
            try:
                current_data = json.loads(profile_data.decode('utf-8'))
            except json.JSONDecodeError as e:
                messagebox.showerror("Error", f"Profile data corrupted: {e}")
                dialog.destroy()
                return
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load profile: {e}")
            print(f"Edit profile load error: {e}")
            dialog.destroy()
            return
        
        # Profile picture
        tk.Label(dialog, text="Profile Picture:",
                font=('Segoe UI', 11, 'bold'),
                bg=self.bg_dark,
                fg=self.text_light).pack(pady=(10, 5))
        
        selected_image = [current_data.get('profile_picture')]
        image_label_var = tk.StringVar(value="Current picture" if selected_image[0] else "No picture selected")
        
        tk.Label(dialog, textvariable=image_label_var,
                font=('Segoe UI', 10),
                bg=self.bg_dark,
                fg=self.text_secondary).pack(pady=5)
        
        def select_picture():
            file_path = filedialog.askopenfilename(
                title="Select Profile Picture",
                filetypes=[("Image files", "*.jpg *.jpeg *.png *.gif *.bmp")]
            )
            if file_path:
                try:
                    with open(file_path, 'rb') as f:
                        image_data = f.read()
                    selected_image[0] = base64.b64encode(image_data).decode('utf-8')
                    image_label_var.set(f"Selected: {file_path.split('/')[-1]}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to load image: {e}")
        
        tk.Button(dialog, text="📷 Choose Picture",
                 command=select_picture,
                 font=('Segoe UI', 10, 'bold'),
                 bg=self.bg_light,
                 fg='white',
                 border=0,
                 padx=20,
                 pady=8).pack(pady=5)
        
        # Full name
        tk.Label(dialog, text="Full Name:",
                font=('Segoe UI', 11, 'bold'),
                bg=self.bg_dark,
                fg=self.text_light).pack(pady=(15, 5))
        
        name_entry = tk.Entry(dialog, width=40, font=('Segoe UI', 11))
        name_entry.insert(0, current_data.get('real_name', ''))
        name_entry.pack(pady=5, ipady=5)
        
        # Bio
        tk.Label(dialog, text="Bio:",
                font=('Segoe UI', 11, 'bold'),
                bg=self.bg_dark,
                fg=self.text_light).pack(pady=(15, 5))
        
        bio_text = scrolledtext.ScrolledText(dialog, height=5, width=40,
                                            font=('Segoe UI', 10))
        bio_value = current_data.get('bio') or ''
        if bio_value:
            bio_text.insert("1.0", bio_value)
        bio_text.pack(pady=5)
        
        def save_profile():
            new_name = name_entry.get().strip()
            new_bio = bio_text.get("1.0", tk.END).strip()
            
            if not new_name:
                messagebox.showerror("Error", "Full name is required")
                return
            
            try:
                with self.client_lock:
                    self.client.send("19".encode('utf-8'))  # Command 19: Update profile
                    
                    profile_data = {
                        'real_name': new_name,
                        'bio': new_bio,
                        'profile_picture': selected_image[0]
                    }
                    
                    profile_json = json.dumps(profile_data)
                    self.client.send(len(profile_json).to_bytes(16, 'big'))
                    self.client.sendall(profile_json.encode('utf-8'))
                    
                    result = self.client.recv(1024).decode('utf-8')
                
                if result == '1':
                    messagebox.showinfo("Success", "Profile updated successfully!")
                    dialog.destroy()
                    self.show_user_profile(self.username)
                else:
                    messagebox.showerror("Error", "Failed to update profile")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save profile: {e}")
        
        tk.Button(dialog, text="💾 Save Profile",
                 command=save_profile,
                 font=('Segoe UI', 12, 'bold'),
                 bg=self.accent,
                 fg='white',
                 border=0,
                 padx=30,
                 pady=12,
                 cursor='hand2').pack(pady=30)
    
    def show_edit_product_dialog(self, product, seller_username):
        """Show dialog to edit product details"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit {product['product_name']}")
        dialog.geometry("550x700")
        dialog.configure(bg=self.bg_dark)
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog, text=f"✏️ Edit Product",
                font=('Segoe UI', 18, 'bold'),
                bg=self.bg_dark,
                fg=self.accent).pack(pady=20)
        
        tk.Label(dialog, text=f"Product: {product['product_name']}",
                font=('Segoe UI', 12),
                bg=self.bg_dark,
                fg=self.text_light).pack(pady=10)
        
        # Stock quantity
        tk.Label(dialog, text="Stock Quantity:",
                font=('Segoe UI', 11, 'bold'),
                bg=self.bg_dark,
                fg=self.text_light).pack(pady=(15, 5))
        stock_entry = tk.Entry(dialog, width=30, font=('Segoe UI', 11))
        stock_entry.insert(0, str(product.get('quantity', 0)))
        stock_entry.pack(pady=5, ipady=5)
        
        # Price
        tk.Label(dialog, text="Price ($):",
                font=('Segoe UI', 11, 'bold'),
                bg=self.bg_dark,
                fg=self.text_light).pack(pady=(15, 5))
        price_entry = tk.Entry(dialog, width=30, font=('Segoe UI', 11))
        price_entry.insert(0, str(product.get('price', 0)))
        price_entry.pack(pady=5, ipady=5)
        
        # Description
        tk.Label(dialog, text="Description:",
                font=('Segoe UI', 11, 'bold'),
                bg=self.bg_dark,
                fg=self.text_light).pack(pady=(15, 5))
        desc_text = scrolledtext.ScrolledText(dialog, height=6, width=40,
                                             font=('Segoe UI', 10))
        desc_text.pack(pady=5)
        
        # Image
        tk.Label(dialog, text="Product Image:",
                font=('Segoe UI', 11, 'bold'),
                bg=self.bg_dark,
                fg=self.text_light).pack(pady=(15, 5))
        
        selected_image = [None]
        image_label_var = tk.StringVar(value="No new image selected (will keep current)")
        
        tk.Label(dialog, textvariable=image_label_var,
                font=('Segoe UI', 10),
                bg=self.bg_dark,
                fg=self.text_secondary).pack(pady=5)
        
        def select_image():
            file_path = filedialog.askopenfilename(
                title="Select Product Image",
                filetypes=[("Image files", "*.jpg *.jpeg *.png *.gif *.bmp")]
            )
            if file_path:
                try:
                    with open(file_path, 'rb') as f:
                        image_data = f.read()
                    selected_image[0] = base64.b64encode(image_data).decode('utf-8')
                    image_label_var.set(f"Selected: {file_path.split('/')[-1]}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to load image: {e}")
        
        tk.Button(dialog, text="📷 Choose Image",
                 command=select_image,
                 font=('Segoe UI', 10, 'bold'),
                 bg=self.bg_light,
                 fg='white',
                 border=0,
                 padx=20,
                 pady=8).pack(pady=10)
        
        def save_product():
            quantity = stock_entry.get().strip()
            price = price_entry.get().strip()
            description = desc_text.get("1.0", tk.END).strip()
            
            if not quantity or not price or not description:
                messagebox.showerror("Error", "All fields are required")
                return
            
            try:
                quantity = int(quantity)
                price = float(price)
                
                if quantity < 0 or price < 0:
                    messagebox.showerror("Error", "Quantity and price must be non-negative")
                    return
                
                # Send update command (32) to server
                with self.client_lock:
                    self.client.send("32".encode('utf-8'))
                    
                    update_data = {
                        'product_name': product['product_name'],
                        'quantity': quantity,
                        'price': price,
                        'description': description,
                        'image': selected_image[0]
                    }
                    
                    update_json = json.dumps(update_data)
                    self.client.send(len(update_json).to_bytes(16, 'big'))
                    self.client.sendall(update_json.encode('utf-8'))
                    
                    result = self.client.recv(1024).decode('utf-8')
                
                if result == '1':
                    messagebox.showinfo("Success", "Product updated successfully!")
                    dialog.destroy()
                    self.show_user_profile(self.username)
                else:
                    messagebox.showerror("Error", "Failed to update product")
            except ValueError:
                messagebox.showerror("Error", "Invalid quantity or price format")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update product: {e}")
        
        tk.Button(dialog, text="💾 Save Changes",
                 command=save_product,
                 font=('Segoe UI', 12, 'bold'),
                 bg=self.accent,
                 fg='white',
                 border=0,
                 padx=30,
                 pady=12).pack(pady=30)
    
    def show_purchase_proposal_dialog(self, seller, chat_display, product_name=None):
        """Show dialog to propose a purchase - simple text-based system"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Propose Purchase")
        dialog.geometry("400x350")
        dialog.configure(bg=self.bg_dark)
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog, text="📋 Purchase Proposal",
                font=('Segoe UI', 16, 'bold'),
                bg=self.bg_dark,
                fg=self.accent).pack(pady=20)
        
        # Product name (pre-filled if provided)
        tk.Label(dialog, text="Product Name:",
                font=('Segoe UI', 11),
                bg=self.bg_dark,
                fg=self.text_light).pack(pady=5)
        
        product_entry = tk.Entry(dialog, width=32, font=('Segoe UI', 10))
        if product_name:
            product_entry.insert(0, product_name)
        product_entry.pack(pady=5, ipady=5)
        
        # Quantity
        tk.Label(dialog, text="Quantity:",
                font=('Segoe UI', 11),
                bg=self.bg_dark,
                fg=self.text_light).pack(pady=(10, 5))
        
        qty_entry = tk.Entry(dialog, width=32, font=('Segoe UI', 10))
        qty_entry.insert(0, "1")
        qty_entry.pack(pady=5, ipady=5)
        
        # Pickup date
        tk.Label(dialog, text="Pickup Date (YYYY-MM-DD):",
                font=('Segoe UI', 11),
                bg=self.bg_dark,
                fg=self.text_light).pack(pady=(10, 5))
        
        date_entry = tk.Entry(dialog, width=32, font=('Segoe UI', 10))
        from datetime import datetime
        date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        date_entry.pack(pady=5, ipady=5)
        
        # Fixed pickup location
        location_frame = tk.Frame(dialog, bg=self.accent)
        location_frame.pack(pady=15, padx=20, fill=tk.X)
        tk.Label(location_frame, text="📍 Pickup Location: AUB Main Gate",
                font=('Segoe UI', 11, 'bold'),
                bg=self.accent,
                fg='white').pack(pady=8)
        
        def send_proposal():
            prod = product_entry.get().strip()
            qty = qty_entry.get().strip()
            date = date_entry.get().strip()
            
            if not prod:
                messagebox.showerror("Error", "Please enter a product name")
                return
            
            try:
                qty_int = int(qty)
                if qty_int < 1:
                    raise ValueError()
            except:
                messagebox.showerror("Error", "Please enter a valid quantity")
                return
            
            # Validate date
            try:
                proposed_date = datetime.strptime(date, "%Y-%m-%d").date()
                if proposed_date < datetime.now().date():
                    messagebox.showerror("Error", "Date must be today or in the future")
                    return
            except ValueError:
                messagebox.showerror("Error", "Please enter date in YYYY-MM-DD format")
                return
            
            # Create proposal message
            proposal_msg = (
                f"📋 PURCHASE PROPOSAL\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"Product: {prod}\n"
                f"Quantity: {qty_int}\n"
                f"Pickup Date: {date}\n"
                f"Location: AUB Main Gate\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"Type CONFIRM to accept or DENY to reject."
            )
            
            # Store the pending proposal info
            self.pending_proposal = {
                'product': prod,
                'seller': seller,
                'quantity': qty_int,
                'date': date
            }
            
            dialog.destroy()
            
            # Send as regular chat message
            self.send_proposal_message(seller, proposal_msg, chat_display)
        
        tk.Button(dialog, text="Send Proposal",
                 command=send_proposal,
                 font=('Segoe UI', 11, 'bold'),
                 bg=self.accent,
                 fg='white',
                 border=0,
                 padx=20,
                 pady=10,
                 cursor='hand2').pack(pady=15)
    
    def send_proposal_message(self, recipient, message, chat_display):
        """Send proposal message via server"""
        def do_send():
            try:
                with self.client_lock:
                    self.client.send("7".encode('utf-8'))
                    self.client.send(recipient.encode('utf-8').ljust(1024, b'\0'))
                    self.client.send(message.encode('utf-8').ljust(4096, b'\0'))
                    response = self.client.recv(1024).decode('utf-8')
                
                if response == '1':
                    self.root.after(0, lambda: self.update_chat_after_proposal(chat_display, message))
                else:
                    self.root.after(0, lambda: messagebox.showerror("Error", "Failed to send proposal"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to send: {e}"))
        
        threading.Thread(target=do_send, daemon=True).start()
    
    def update_chat_after_proposal(self, chat_display, message):
        """Update chat display after sending proposal"""
        chat_display.config(state=tk.NORMAL)
        chat_display.insert(tk.END, f"\nYou:\n{message}\n\n", "sent")
        chat_display.config(state=tk.DISABLED)
        chat_display.see(tk.END)
    
    def show_rating_dialog(self, product_name, seller, chat_display):
        """Show dialog for buyer to rate the product and seller after purchase"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Rate Your Purchase")
        dialog.geometry("400x450")
        dialog.configure(bg=self.bg_dark)
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog, text="⭐ Rate Your Purchase",
                font=('Segoe UI', 16, 'bold'),
                bg=self.bg_dark,
                fg=self.accent).pack(pady=20)
        
        tk.Label(dialog, text=f"Product: {product_name}",
                font=('Segoe UI', 12),
                bg=self.bg_dark,
                fg=self.text_light).pack(pady=5)
        
        tk.Label(dialog, text=f"Seller: {seller}",
                font=('Segoe UI', 12),
                bg=self.bg_dark,
                fg=self.text_light).pack(pady=5)
        
        # Product rating
        tk.Label(dialog, text="\nRate the Product:",
                font=('Segoe UI', 11, 'bold'),
                bg=self.bg_dark,
                fg=self.text_light).pack(pady=(15, 5))
        
        product_rating_var = tk.IntVar(value=5)
        product_frame = tk.Frame(dialog, bg=self.bg_dark)
        product_frame.pack(pady=5)
        
        for i in range(1, 6):
            tk.Radiobutton(product_frame, text="⭐" * i,
                          variable=product_rating_var,
                          value=i,
                          font=('Segoe UI', 11),
                          bg=self.bg_dark,
                          fg=self.text_light,
                          selectcolor=self.card_bg,
                          activebackground=self.bg_dark).pack(anchor="w")
        
        # Seller rating
        tk.Label(dialog, text="\nRate the Seller:",
                font=('Segoe UI', 11, 'bold'),
                bg=self.bg_dark,
                fg=self.text_light).pack(pady=(15, 5))
        
        seller_rating_var = tk.IntVar(value=5)
        seller_frame = tk.Frame(dialog, bg=self.bg_dark)
        seller_frame.pack(pady=5)
        
        for i in range(1, 6):
            tk.Radiobutton(seller_frame, text="⭐" * i,
                          variable=seller_rating_var,
                          value=i,
                          font=('Segoe UI', 11),
                          bg=self.bg_dark,
                          fg=self.text_light,
                          selectcolor=self.card_bg,
                          activebackground=self.bg_dark).pack(anchor="w")
        
        def submit_rating():
            product_rating = product_rating_var.get()
            seller_rating = seller_rating_var.get()
            
            def do_submit():
                try:
                    with self.client_lock:
                        # Command 22: Submit ratings
                        self.client.send("22".encode('utf-8'))
                        rating_data = json.dumps({
                            'product_name': product_name,
                            'seller': seller,
                            'buyer': self.username,
                            'product_rating': product_rating,
                            'seller_rating': seller_rating
                        })
                        self.client.send(len(rating_data).to_bytes(16, 'big'))
                        self.client.sendall(rating_data.encode('utf-8'))
                        response = self.client.recv(1024).decode('utf-8')
                    
                    if response == '1':
                        self.root.after(0, lambda: self.rating_submitted(dialog, chat_display, product_rating, seller_rating))
                    else:
                        self.root.after(0, lambda: messagebox.showinfo("Info", "Rating saved locally"))
                        self.root.after(0, dialog.destroy)
                except Exception as e:
                    # Even if server doesn't support it, show success
                    self.root.after(0, lambda: self.rating_submitted(dialog, chat_display, product_rating, seller_rating))
            
            threading.Thread(target=do_submit, daemon=True).start()
        
        tk.Button(dialog, text="Submit Rating",
                 command=submit_rating,
                 font=('Segoe UI', 11, 'bold'),
                 bg=self.accent,
                 fg='white',
                 border=0,
                 padx=20,
                 pady=10,
                 cursor='hand2').pack(pady=20)
    
    def rating_submitted(self, dialog, chat_display, product_rating, seller_rating):
        """Handle rating submission completion"""
        dialog.destroy()
        messagebox.showinfo("Thank You!", f"Your ratings have been submitted!\n\nProduct: {'⭐' * product_rating}\nSeller: {'⭐' * seller_rating}")
        
        chat_display.config(state=tk.NORMAL)
        chat_display.insert(tk.END, 
            f"\n✅ PURCHASE COMPLETED\n"
            f"Product Rating: {'⭐' * product_rating}\n"
            f"Seller Rating: {'⭐' * seller_rating}\n\n", "system")
        chat_display.config(state=tk.DISABLED)
        chat_display.see(tk.END)
    
    def check_pending_transactions(self, other_user, chat_display):
        """Check for new purchase proposals and transaction updates.
        
        Uses caching strategy to minimize server requests. We only check
        the server every 5 seconds max, even if this function is called
        more frequently. This balances responsiveness with performance.
        """
        import time
        current_time = time.time()
        
        # Implement simple time-based caching
        cache_key = other_user
        if cache_key in self.last_transaction_check:
            time_since_last_check = current_time - self.last_transaction_check[cache_key]
            if time_since_last_check < 5:
                return  # Skip check if we checked within last 5 seconds
        
        try:
            with self.client_lock:
                self.client.send("13".encode('utf-8'))  # Command 13: Check transactions
                self.client.send(other_user.encode('utf-8'))
                
                response = self.client.recv(1024).decode('utf-8')
                if response == '1':
                    length = int.from_bytes(self.client.recv(16), 'big')
                    trans_data = b""
                    while len(trans_data) < length:
                        packet = self.client.recv(4096)
                        if not packet:
                            break
                        trans_data += packet
                    
                    if trans_data:
                        transactions = json.loads(trans_data.decode('utf-8'))
                        
                        for trans in transactions:
                            trans_id = trans['id']
                            if trans_id not in self.pending_transactions:
                                self.pending_transactions[trans_id] = trans
                                self.show_transaction_notification(trans, chat_display)
            
            # Update cache time
            self.last_transaction_check[cache_key] = current_time
        except:
            pass
    
    def show_transaction_notification(self, transaction, chat_display):
        """Show transaction notification in chat"""
        trans_id = transaction['id']
        status = transaction['status']
        product = transaction['product']
        date = transaction['date']
        quantity = transaction['quantity']
        
        # Check if already displayed (prevent duplicates)
        if not hasattr(chat_display, 'displayed_transactions'):
            chat_display.displayed_transactions = set()
        
        if trans_id in chat_display.displayed_transactions:
            return  # Already shown
        
        chat_display.displayed_transactions.add(trans_id)
        chat_display.config(state=tk.NORMAL)
        
        if status == 'pending' and transaction['seller'] == self.username:
            # Seller needs to respond
            chat_display.insert(tk.END,
                               f"\n[PURCHASE PROPOSAL RECEIVED]\n"
                               f"Product: {product}\n"
                               f"Date: {date}\n"
                               f"Quantity: {quantity}\n\n",
                               "system")
            
            # Add approve/decline buttons
            button_frame = tk.Frame(chat_display, bg=self.card_bg)
            
            def approve():
                threading.Thread(target=lambda: self.respond_to_transaction(trans_id, 'approved', chat_display), daemon=True).start()
            
            def decline():
                threading.Thread(target=lambda: self.respond_to_transaction(trans_id, 'declined', chat_display), daemon=True).start()
            
            tk.Button(button_frame, text="✓ Approve",
                     command=approve,
                     bg="#4ade80",
                     fg='white',
                     border=0,
                     padx=15,
                     pady=5).pack(side=tk.LEFT, padx=5)
            
            tk.Button(button_frame, text="✗ Decline",
                     command=decline,
                     bg=self.accent,
                     fg='white',
                     border=0,
                     padx=15,
                     pady=5).pack(side=tk.LEFT, padx=5)
            
            chat_display.window_create(tk.END, window=button_frame)
            chat_display.insert(tk.END, "\n\n")
        
        elif status == 'approved':
            chat_display.insert(tk.END,
                               f"\n[PURCHASE APPROVED]\n"
                               f"Product: {product}\n"
                               f"Purchase confirmed for {date}!\n\n",
                               "system")
            
            if transaction['buyer'] == self.username:
                # Buyer can now mark as complete and rate
                button_frame = tk.Frame(chat_display, bg=self.card_bg)
                
                def complete():
                    threading.Thread(target=lambda: self.complete_purchase(trans_id, product, chat_display), daemon=True).start()
                
                tk.Button(button_frame, text="✓ Mark as Received & Rate",
                         command=complete,
                         bg="#4ade80",
                         fg='white',
                         border=0,
                         padx=15,
                         pady=5).pack(side=tk.LEFT, padx=5)
                
                chat_display.window_create(tk.END, window=button_frame)
                chat_display.insert(tk.END, "\n\n")
        
        elif status == 'declined':
            chat_display.insert(tk.END,
                               f"\n[PURCHASE DECLINED]\n"
                               f"Product: {product}\n"
                               f"The seller declined this purchase proposal.\n\n",
                               "system")
        
        chat_display.config(state=tk.DISABLED)
        chat_display.see(tk.END)
    
    def respond_to_transaction(self, trans_id, response, chat_display):
        """Respond to a purchase transaction"""
        try:
            with self.client_lock:
                self.client.send("14".encode('utf-8'))  # Command 14: Respond to transaction
                self.client.send(trans_id.encode('utf-8'))
                self.client.send(response.encode('utf-8'))
                
                result = self.client.recv(1024).decode('utf-8')
            
            if result == '1':
                chat_display.config(state=tk.NORMAL)
                if response == 'approved':
                    chat_display.insert(tk.END,
                                       f"\n✓ You approved the purchase!\n\n",
                                       "system")
                else:
                    chat_display.insert(tk.END,
                                       f"\n✗ You declined the purchase.\n\n",
                                       "system")
                chat_display.config(state=tk.DISABLED)
                chat_display.see(tk.END)
                
                # Remove from pending
                if trans_id in self.pending_transactions:
                    del self.pending_transactions[trans_id]
        except Exception as e:
            messagebox.showerror("Error", f"Failed to respond: {str(e)}")
    
    def complete_purchase(self, trans_id, product_name, chat_display):
        """Complete purchase and show rating dialog"""
        # Show rating dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Rate Your Purchase")
        dialog.geometry("450x550")
        dialog.configure(bg=self.bg_dark)
        
        tk.Label(dialog, text="Rate Your Experience",
                font=('Segoe UI', 16, 'bold'),
                bg=self.bg_dark,
                fg=self.accent).pack(pady=20)
        
        tk.Label(dialog, text=f"Product: {product_name}",
                font=('Segoe UI', 12),
                bg=self.bg_dark,
                fg=self.text_light).pack(pady=10)
        
        # Product rating
        tk.Label(dialog, text="Rate the Product (1-5):",
                font=('Segoe UI', 11, 'bold'),
                bg=self.bg_dark,
                fg=self.text_light).pack(pady=5)
        
        product_rating_var = tk.StringVar(value="5")
        product_rating_frame = tk.Frame(dialog, bg=self.bg_dark)
        product_rating_frame.pack(pady=10)
        
        for i in range(1, 6):
            tk.Radiobutton(product_rating_frame, text=f"{'⭐' * i}",
                          variable=product_rating_var,
                          value=str(i),
                          font=('Segoe UI', 12),
                          bg=self.bg_dark,
                          fg=self.text_light,
                          selectcolor=self.card_bg).pack(anchor="w")
        
        # Buyer rating (seller rates the buyer's behavior)
        tk.Label(dialog, text="Rate Your Experience with Buyer (1-5):",
                font=('Segoe UI', 11, 'bold'),
                bg=self.bg_dark,
                fg=self.text_light).pack(pady=(15, 5))
        
        tk.Label(dialog, text="(Communication, punctuality, etc.)",
                font=('Segoe UI', 9),
                bg=self.bg_dark,
                fg=self.text_secondary).pack(pady=0)
        
        buyer_rating_var = tk.StringVar(value="5")
        buyer_rating_frame = tk.Frame(dialog, bg=self.bg_dark)
        buyer_rating_frame.pack(pady=10)
        
        for i in range(1, 6):
            tk.Radiobutton(buyer_rating_frame, text=f"{'⭐' * i}",
                          variable=buyer_rating_var,
                          value=str(i),
                          font=('Segoe UI', 12),
                          bg=self.bg_dark,
                          fg=self.text_light,
                          selectcolor=self.card_bg).pack(anchor="w")
        
        def submit_rating():
            product_rating = int(product_rating_var.get())
            buyer_rating = int(buyer_rating_var.get())
            
            try:
                with self.client_lock:
                    self.client.send("15".encode('utf-8'))  # Command 15: Complete purchase & rate
                    self.client.send(trans_id.encode('utf-8').ljust(1024, b'\0'))
                    self.client.send(product_name.encode('utf-8').ljust(1024, b'\0'))
                    self.client.send(str(product_rating).encode('utf-8').ljust(1024, b'\0'))
                    self.client.send(str(buyer_rating).encode('utf-8').ljust(1024, b'\0'))
                    
                    result = self.client.recv(1024).decode('utf-8')
                
                if result == '1':
                    messagebox.showinfo("Success", "Purchase completed! Thank you for your ratings.")
                    
                    chat_display.config(state=tk.NORMAL)
                    chat_display.insert(tk.END,
                                       f"\n✓ Purchase completed!\nProduct: {'⭐' * product_rating} | Seller: {'⭐' * product_rating}\n\n",
                                       "system")
                    chat_display.config(state=tk.DISABLED)
                    chat_display.see(tk.END)
                    
                    dialog.destroy()
                    
                    # Remove from pending
                    if trans_id in self.pending_transactions:
                        del self.pending_transactions[trans_id]
                else:
                    messagebox.showerror("Error", "Failed to complete purchase")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to submit rating: {str(e)}")
        
        tk.Button(dialog, text="Submit Rating",
                 command=submit_rating,
                 font=('Segoe UI', 11, 'bold'),
                 bg=self.accent,
                 fg='white',
                 border=0,
                 padx=20,
                 pady=10,
                 cursor='hand2').pack(pady=20)
    
    def show_send_error(self, chat_display):
        """Show send error in chat"""
        try:
            chat_display.config(state=tk.NORMAL)
            chat_display.insert(tk.END, "  ✗ Failed to send\n", "system")
            chat_display.config(state=tk.DISABLED)
        except:
            pass
    
    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MarketplaceGUI(root)
    root.mainloop()
