import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import json
from datetime import datetime
import base64
from PIL import Image, ImageTk
from io import BytesIO

class ChatWindow:
    
    def __init__(self, parent_app, other_user, product_name=None, auto_message=None):
        self.app = parent_app
        self.other_user = other_user
        self.product_name = product_name
        self.window = tk.Toplevel(parent_app.root)
        self.window.title(f"Chat with {other_user}")
        self.window.geometry("500x600")
        self.window.configure(bg=parent_app.bg_dark)
        self.has_unread = False
        self.displayed_message_ids = set()
        self.proposal_denied = False
        
        self.setup_ui()
        self.load_history()
        self.check_online_status()
        self.start_polling()
        self.start_status_polling()
        
        if auto_message:
            self.window.after(500, lambda: self.send_auto_message(auto_message))
    
    def setup_ui(self):
        header = tk.Frame(self.window, bg=self.app.bg_medium)
        header.pack(fill=tk.X, pady=(0, 10))
        
        header_left = tk.Frame(header, bg=self.app.bg_medium)
        header_left.pack(side=tk.LEFT, padx=20, pady=15)
        
        self.chat_title_label = tk.Label(header_left, text=f"💬 {self.other_user}",
                font=('Segoe UI', 14, 'bold'),
                bg=self.app.bg_medium,
                fg=self.app.text_light)
        self.chat_title_label.pack(side=tk.LEFT)
        
        self.status_label = tk.Label(header_left, text="● Checking...",
                                     font=('Segoe UI', 9),
                                     bg=self.app.bg_medium,
                                     fg="#94a3b8")
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        tk.Button(header, text="👤 Profile",
                 command=self.show_profile,
                 font=('Segoe UI', 9, 'bold'),
                 bg=self.app.accent,
                 fg='white',
                 border=0,
                 padx=10,
                 pady=5).pack(side=tk.RIGHT, padx=20)
        
        self.check_online_status()
        
        self.chat_display = scrolledtext.ScrolledText(
            self.window, 
            height=20, 
            state=tk.DISABLED,
            font=('Segoe UI', 10),
            bg=self.app.card_bg,
            fg=self.app.text_light,
            wrap=tk.WORD
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.chat_display.tag_config("me", foreground="#4ade80")
        self.chat_display.tag_config("them", foreground="#60a5fa")
        
        input_frame = tk.Frame(self.window, bg=self.app.bg_dark)
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.msg_entry = tk.Entry(input_frame, font=('Segoe UI', 10))
        self.msg_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        self.msg_entry.bind('<Return>', lambda e: self.send_message())
        
        tk.Button(input_frame, text="Send",
                 command=self.send_message,
                 font=('Segoe UI', 10, 'bold'),
                 bg=self.app.accent,
                 fg='white',
                 border=0,
                 padx=15,
                 pady=8).pack(side=tk.LEFT, padx=5)
        
        # Propose Purchase button - available in all chats
        tk.Button(input_frame, text="📋 Propose",
                 command=self.show_proposal_dialog,
                 font=('Segoe UI', 9, 'bold'),
                 bg="#4ade80",
                 fg='white',
                 border=0,
                 padx=10,
                 pady=8).pack(side=tk.LEFT)
        
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def load_history(self):
        """Load chat history from server"""
        def do_load():
            try:
                with self.app.client_lock:
                    self.app.client.send("6".encode('utf-8'))
                    # Pad recipient to 1024 bytes for consistency
                    recipient_padded = self.other_user.encode('utf-8').ljust(1024, b'\0')
                    self.app.client.send(recipient_padded)
                    
                    response = self.app.client.recv(1).decode('utf-8')
                    if response == '1':
                        length = int.from_bytes(self.app.client.recv(16), 'big')
                        data = b""
                        while len(data) < length:
                            packet = self.app.client.recv(4096)
                            if not packet:
                                break
                            data += packet
                        
                        if data:
                            history = json.loads(data.decode('utf-8'))
                            self.app.root.after(0, lambda: self.display_history(history))
                            
                            # Mark messages from this user as read
                            self.mark_messages_read()
            except Exception as e:
                print(f"Error loading history: {e}")
        
        threading.Thread(target=do_load, daemon=True).start()
    
    def mark_messages_read(self):
        """Mark all messages from other_user as read"""
        def do_mark():
            try:
                with self.app.client_lock:
                    self.app.client.send("30".encode('utf-8'))  # Mark read command
                    sender_padded = self.other_user.encode('utf-8').ljust(1024, b'\0')
                    self.app.client.send(sender_padded)
                    self.app.client.recv(1)  # Acknowledgment
                    # Update local unread count
                    if self.other_user in self.app.unread_messages:
                        self.app.unread_messages[self.other_user] = 0
            except Exception as e:
                print(f"Error marking messages read: {e}")
        
        threading.Thread(target=do_mark, daemon=True).start()
    
    def display_history(self, history):
        """Display chat history"""
        if not self.window.winfo_exists():
            return
        
        self.chat_display.config(state=tk.NORMAL)
        for sender, message, timestamp in history:
            # Track message by creating unique ID from sender+message+timestamp
            msg_id = f"{sender}:{message[:50]}:{timestamp}"
            self.displayed_message_ids.add(msg_id)
            
            if sender == self.app.username:
                self.chat_display.insert(tk.END, f"You: {message}\n", "me")
            else:
                self.chat_display.insert(tk.END, f"{sender}: {message}\n", "them")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
    
    def send_message(self):
        """Send message to server"""
        message = self.msg_entry.get().strip()
        if not message:
            return
        
        # Clear unread indicator when user types
        if self.has_unread:
            self.chat_title_label.config(text=f"💬 {self.other_user}")
            self.has_unread = False
        
        # Check if this is a CONFIRM or DENY response
        is_confirmation = (message.upper() == "CONFIRM")
        is_denial = (message.upper() == "DENY")
        
        # Display immediately
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"You: {message}\n", "me")
        
        # Handle DENY
        if is_denial:
            self.proposal_denied = True
            self.chat_display.insert(tk.END, "❌ Purchase proposal cancelled\n", "me")
        
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
        self.msg_entry.delete(0, tk.END)
        
        # If seller confirmed, process the purchase (only if not denied)
        if is_confirmation and self.product_name and not self.proposal_denied:
            self.handle_purchase_confirmation()
        elif is_confirmation and self.proposal_denied:
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.insert(tk.END, "⚠️ Cannot confirm - proposal was denied\n", "me")
            self.chat_display.config(state=tk.DISABLED)
            return  # Don't send the CONFIRM message
        
        # Send to server
        def do_send():
            try:
                with self.app.client_lock:
                    self.app.client.send("7".encode('utf-8'))
                    # Pad recipient to 1024 bytes
                    recipient_padded = self.other_user.encode('utf-8').ljust(1024, b'\0')
                    self.app.client.send(recipient_padded)
                    # Pad message to 4096 bytes
                    message_padded = message.encode('utf-8').ljust(4096, b'\0')
                    self.app.client.send(message_padded)
                    response = self.app.client.recv(1).decode('utf-8')
                    
                    if response != '1':
                        print(f"Server response: {response}")
            except Exception as e:
                print(f"Send error: {e}")
                import traceback
                traceback.print_exc()
        
        threading.Thread(target=do_send, daemon=True).start()
    
    def show_error(self, msg):
        """Show error in chat"""
        if self.window.winfo_exists():
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.insert(tk.END, f"✗ Error: {msg}\n")
            self.chat_display.config(state=tk.DISABLED)
    
    def poll_messages(self):
        """Check for new messages"""
        if not self.window.winfo_exists():
            return
        
        def check():
            try:
                with self.app.client_lock:
                    self.app.client.send("21".encode('utf-8'))
                    # Pad recipient to 1024 bytes
                    recipient_padded = self.other_user.encode('utf-8').ljust(1024, b'\0')
                    self.app.client.send(recipient_padded)
                    
                    response = self.app.client.recv(1).decode('utf-8')
                    if response == '1':
                        length = int.from_bytes(self.app.client.recv(16), 'big')
                        data = b""
                        while len(data) < length:
                            packet = self.app.client.recv(4096)
                            if not packet:
                                break
                            data += packet
                        
                        if data:
                            messages = json.loads(data.decode('utf-8'))
                            self.app.root.after(0, lambda: self.display_new_messages(messages))
            except Exception as e:
                print(f"Poll error: {e}")
        
        threading.Thread(target=check, daemon=True).start()
    
    def display_new_messages(self, messages):
        """Display newly received messages"""
        try:
            if not self.window.winfo_exists():
                return
        except:
            # Window has been destroyed
            return
        
        if not messages:
            return
        
        new_messages_added = False
        try:
            self.chat_display.config(state=tk.NORMAL)
        except:
            # Widget destroyed
            return
        
        for sender, message, timestamp in messages:
            # Check if this message was already displayed
            msg_id = f"{sender}:{message[:50]}:{timestamp}"
            if msg_id in self.displayed_message_ids:
                continue  # Skip duplicate
            
            self.displayed_message_ids.add(msg_id)
            new_messages_added = True
            self.chat_display.insert(tk.END, f"{sender}: {message}\n", "them")
            
            # Check for proposal - if buyer sent it, check for seller's response
            if message.strip().upper() == "CONFIRM":
                # Seller confirmed! Process the purchase (only if not denied)
                if not self.proposal_denied:
                    self.handle_purchase_confirmation()
                else:
                    self.chat_display.insert(tk.END, "⚠️ Proposal was already denied\n", "them")
            elif message.strip().upper() == "DENY":
                self.proposal_denied = True
                self.chat_display.insert(tk.END, "❌ Purchase proposal cancelled\n", "them")
            elif "PURCHASE PROPOSAL" in message:
                # Reset denial flag for new proposal
                self.proposal_denied = False
                # Received a proposal - show instructions
                self.chat_display.insert(tk.END, "→ Type CONFIRM or DENY to respond\n")
        
        # Show notification for new messages
        if new_messages_added:
            self.window.bell()  # System beep
            self.window.attributes('-topmost', True)
            self.window.after(100, lambda: self.window.attributes('-topmost', False))
            
            # Add red dot to chat title
            self.chat_title_label.config(text=f"🔴 💬 {self.other_user}")
            self.has_unread = True
        
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
    
    def extract_product(self, message):
        """Extract product name from message"""
        for line in message.split('\n'):
            if 'Product:' in line:
                return line.split(':', 1)[1].strip()
        return None
    
    def handle_purchase_confirmation(self):
        """Handle purchase confirmation - decrement stock and show rating dialog"""
        if not self.product_name:
            messagebox.showwarning("No Product", "No product context for this purchase")
            return
        
        def process():
            try:
                # Send stock decrement command
                with self.app.client_lock:
                    self.app.client.send("25".encode('utf-8'))
                    
                    purchase_data = json.dumps({
                        'product_name': self.product_name,
                        'seller': self.other_user,
                        'quantity': 1
                    })
                    
                    self.app.client.send(len(purchase_data).to_bytes(16, 'big'))
                    self.app.client.sendall(purchase_data.encode('utf-8'))
                    response = self.app.client.recv(1).decode('utf-8')
                    
                    if response == '1':
                        # Success! Show rating dialog
                        try:
                            if self.window.winfo_exists():
                                self.app.root.after(0, lambda: self.show_rating_dialog(self.product_name))
                        except:
                            pass
                        self.app.root.after(0, lambda: messagebox.showinfo("Success", "Purchase confirmed! Stock updated."))
                    else:
                        self.app.root.after(0, lambda: messagebox.showerror("Error", "Failed to update stock - product may be out of stock"))
            except Exception as e:
                print(f"Error processing confirmation: {e}")
                self.app.root.after(0, lambda: messagebox.showerror("Error", str(e)))
        
        threading.Thread(target=process, daemon=True).start()
    
    def start_polling(self):
        """Start polling for new messages"""
        def poll_loop():
            try:
                if self.window.winfo_exists():
                    self.poll_messages()
                    self.window.after(2000, poll_loop)
            except:
                # Window destroyed, stop polling
                return
        
        try:
            self.window.after(2000, poll_loop)
        except:
            pass
    
    def show_proposal_dialog(self):
        """Show purchase proposal dialog"""
        dialog = tk.Toplevel(self.window)
        dialog.title("Propose Purchase")
        dialog.geometry("400x320")
        dialog.configure(bg=self.app.bg_dark)
        dialog.transient(self.window)
        dialog.grab_set()
        
        tk.Label(dialog, text="📋 Purchase Proposal",
                font=('Segoe UI', 16, 'bold'),
                bg=self.app.bg_dark,
                fg=self.app.accent).pack(pady=20)
        
        # Product
        tk.Label(dialog, text="Product:",
                bg=self.app.bg_dark,
                fg=self.app.text_light).pack()
        prod_entry = tk.Entry(dialog, width=35)
        if self.product_name:
            prod_entry.insert(0, self.product_name)
        else:
            prod_entry.insert(0, "Enter product name")
        prod_entry.pack(pady=5)
        
        # Quantity
        tk.Label(dialog, text="Quantity:",
                bg=self.app.bg_dark,
                fg=self.app.text_light).pack()
        qty_entry = tk.Entry(dialog, width=35)
        qty_entry.insert(0, "1")
        qty_entry.pack(pady=5)
        
        # Date
        tk.Label(dialog, text="Pickup Date (YYYY-MM-DD):",
                bg=self.app.bg_dark,
                fg=self.app.text_light).pack()
        date_entry = tk.Entry(dialog, width=35)
        date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        date_entry.pack(pady=5)
        
        # Location label
        tk.Label(dialog, text="📍 Location: AUB Main Gate",
                font=('Segoe UI', 10, 'bold'),
                bg=self.app.accent,
                fg='white').pack(pady=15, fill=tk.X)
        
        def send():
            prod = prod_entry.get().strip()
            qty = qty_entry.get().strip()
            date = date_entry.get().strip()
            
            if not all([prod, qty, date]):
                messagebox.showerror("Error", "Fill all fields")
                return
            
            # Save product name for future confirmations
            self.product_name = prod
            # Reset denial flag for new proposal
            self.proposal_denied = False
            
            proposal_msg = (
                f"📋 PURCHASE PROPOSAL\n"
                f"━━━━━━━━━━━━━━\n"
                f"Product: {prod}\n"
                f"Quantity: {qty}\n"
                f"Date: {date}\n"
                f"Location: AUB Main Gate\n"
                f"━━━━━━━━━━━━━━\n"
                f"Type CONFIRM to accept or DENY to reject"
            )
            
            dialog.destroy()
            
            # Send through normal message system
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.insert(tk.END, f"You:\n{proposal_msg}\n\n", "me")
            self.chat_display.config(state=tk.DISABLED)
            self.chat_display.see(tk.END)
            
            def do_send():
                try:
                    with self.app.client_lock:
                        self.app.client.send("7".encode('utf-8'))
                        # Pad recipient to 1024 bytes
                        recipient_padded = self.other_user.encode('utf-8').ljust(1024, b'\0')
                        self.app.client.send(recipient_padded)
                        # Pad message to 4096 bytes
                        message_padded = proposal_msg.encode('utf-8').ljust(4096, b'\0')
                        self.app.client.send(message_padded)
                        self.app.client.recv(1)
                except Exception as e:
                    print(f"Error sending proposal: {e}")
            
            threading.Thread(target=do_send, daemon=True).start()
        
        tk.Button(dialog, text="Send Proposal",
                 command=send,
                 bg=self.app.accent,
                 fg='white',
                 font=('Segoe UI', 11, 'bold'),
                 border=0,
                 padx=20,
                 pady=10).pack(pady=15)
    
    def show_rating_dialog(self, product_name):
        """Show rating dialog after purchase confirmation"""
        dialog = tk.Toplevel(self.window)
        dialog.title("Rate Purchase")
        dialog.geometry("550x550")
        dialog.configure(bg=self.app.bg_dark)
        dialog.transient(self.window)
        dialog.grab_set()
        
        tk.Label(dialog, text="⭐ Rate Your Purchase",
                font=('Segoe UI', 16, 'bold'),
                bg=self.app.bg_dark,
                fg=self.app.accent).pack(pady=20)
        
        tk.Label(dialog, text=f"Product: {product_name}",
                bg=self.app.bg_dark,
                fg=self.app.text_light).pack(pady=5)
        
        tk.Label(dialog, text=f"Seller: {self.other_user}",
                bg=self.app.bg_dark,
                fg=self.app.text_light).pack(pady=5)
        
        # Single rating (applies to both product and seller)
        tk.Label(dialog, text="\nOverall Rating:",
                font=('Segoe UI', 12, 'bold'),
                bg=self.app.bg_dark,
                fg=self.app.text_light).pack(pady=15)
        
        tk.Label(dialog, text="(Applies to both product and seller)",
                font=('Segoe UI', 9),
                bg=self.app.bg_dark,
                fg=self.app.text_secondary).pack(pady=5)
        
        rating = tk.IntVar(value=5)
        for i in range(1, 6):
            tk.Radiobutton(dialog, text="⭐" * i,
                          variable=rating,
                          value=i,
                          bg=self.app.bg_dark,
                          fg=self.app.text_light,
                          selectcolor=self.app.card_bg,
                          font=('Segoe UI', 11)).pack(pady=2)
        
        def submit():
            def do_submit():
                try:
                    selected_rating = rating.get()
                    with self.app.client_lock:
                        self.app.client.send("22".encode('utf-8'))
                        rating_data = json.dumps({
                            'product_name': product_name,
                            'seller': self.other_user,
                            'buyer': self.app.username,
                            'product_rating': selected_rating,
                            'seller_rating': selected_rating  # Same rating for both
                        })
                        self.app.client.send(len(rating_data).to_bytes(16, 'big'))
                        self.app.client.sendall(rating_data.encode('utf-8'))
                        self.app.client.recv(1)
                    
                    self.app.root.after(0, lambda: dialog.destroy())
                    self.app.root.after(0, lambda: messagebox.showinfo("Success", f"Rated {selected_rating} stars!"))
                except Exception as e:
                    print(f"Rating error: {e}")
            
            threading.Thread(target=do_submit, daemon=True).start()
        
        tk.Button(dialog, text="Submit",
                 command=submit,
                 bg=self.app.accent,
                 fg='white',
                 font=('Segoe UI', 11, 'bold'),
                 border=0,
                 padx=30,
                 pady=10).pack(pady=20)
    
    def send_auto_message(self, message):
        """Send an automatic message (for purchase notifications)"""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"You: {message}\n", "me")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
        
        def do_send():
            try:
                with self.app.client_lock:
                    self.app.client.send("7".encode('utf-8'))
                    recipient_padded = self.other_user.encode('utf-8').ljust(1024, b'\0')
                    self.app.client.send(recipient_padded)
                    message_padded = message.encode('utf-8').ljust(4096, b'\0')
                    self.app.client.send(message_padded)
                    self.app.client.recv(1)
            except Exception as e:
                print(f"Error sending auto message: {e}")
        
        threading.Thread(target=do_send, daemon=True).start()
    
    def check_online_status(self):
        """Check if user is online or offline"""
        def check():
            try:
                with self.app.client_lock:
                    self.app.client.send("16".encode('utf-8'))
                    username_padded = self.other_user.encode('utf-8').ljust(1024, b'\0')
                    self.app.client.send(username_padded)
                    response = self.app.client.recv(1).decode('utf-8')
                    
                    is_online = (response == '1')
                    self.app.root.after(0, lambda: self.update_status(is_online))
            except Exception as e:
                print(f"Error checking status: {e}")
        
        threading.Thread(target=check, daemon=True).start()
    
    def update_status(self, is_online):
        """Update status display - Online or Offline only"""
        if not self.window.winfo_exists():
            return
        
        if is_online:
            self.status_label.config(text="● Online", fg="#4ade80")
        else:
            self.status_label.config(text="○ Offline", fg="#94a3b8")
    
    def start_status_polling(self):
        """Periodically check status"""
        def poll_status():
            if self.window.winfo_exists():
                self.check_online_status()
                self.window.after(10000, poll_status)  # Check every 10 seconds
        
        self.window.after(3000, poll_status)  # First check after 3 seconds
    
    def show_profile(self):
        """Show user profile in a new window"""
        profile_window = tk.Toplevel(self.window)
        profile_window.title(f"{self.other_user}'s Profile")
        profile_window.geometry("600x800")
        profile_window.configure(bg=self.app.bg_dark)
        profile_window.transient(self.window)
        
        # Header
        tk.Label(profile_window, text=f"👤 {self.other_user}",
                font=('Segoe UI', 20, 'bold'),
                bg=self.app.bg_dark,
                fg=self.app.accent).pack(pady=20)
        
        # Loading message
        loading_label = tk.Label(profile_window, text="Loading profile...",
                                bg=self.app.bg_dark,
                                fg=self.app.text_light)
        loading_label.pack(pady=20)
        
        def load_profile():
            try:
                with self.app.client_lock:
                    self.app.client.send("18".encode('utf-8'))
                    username_padded = self.other_user.encode('utf-8').ljust(1024, b'\0')
                    self.app.client.send(username_padded)
                    
                    response = self.app.client.recv(4096).decode('utf-8')
                    
                    if response.startswith("profile:"):
                        profile_data = json.loads(response[8:])
                        self.app.root.after(0, lambda: self.display_profile(profile_window, loading_label, profile_data))
                    else:
                        self.app.root.after(0, lambda: loading_label.config(text="Failed to load profile"))
            except Exception as e:
                print(f"Error loading profile: {e}")
                self.app.root.after(0, lambda: loading_label.config(text=f"Error: {e}"))
        
        threading.Thread(target=load_profile, daemon=True).start()
    
    def display_profile(self, window, loading_label, profile):
        """Display profile information"""
        if not window.winfo_exists():
            return
        
        loading_label.destroy()
        
        # Profile picture
        pfp_frame = tk.Frame(window, bg=self.app.card_bg)
        pfp_frame.pack(pady=10, padx=20, fill=tk.X)
        
        if profile.get('profile_picture'):
            try:
                img_data = base64.b64decode(profile['profile_picture'])
                img = Image.open(BytesIO(img_data))
                img.thumbnail((150, 150))
                photo = ImageTk.PhotoImage(img)
                img_label = tk.Label(pfp_frame, image=photo, bg=self.app.card_bg)
                img_label.image = photo
                img_label.pack(pady=10)
            except:
                tk.Label(pfp_frame, text="👤",
                        font=('Segoe UI', 60),
                        bg=self.app.card_bg,
                        fg=self.app.text_secondary).pack(pady=10)
        else:
            tk.Label(pfp_frame, text="👤",
                    font=('Segoe UI', 60),
                    bg=self.app.card_bg,
                    fg=self.app.text_secondary).pack(pady=10)
        
        # Real name
        if profile.get('real_name'):
            tk.Label(window, text=profile['real_name'],
                    font=('Segoe UI', 16),
                    bg=self.app.bg_dark,
                    fg=self.app.text_light).pack(pady=5)
        
        # Bio
        if profile.get('bio'):
            tk.Label(window, text="Bio:",
                    font=('Segoe UI', 11, 'bold'),
                    bg=self.app.bg_dark,
                    fg=self.app.text_light).pack(pady=(15, 5))
            bio_text = tk.Text(window, height=4, width=50,
                              font=('Segoe UI', 10),
                              bg=self.app.card_bg,
                              fg=self.app.text_light,
                              wrap=tk.WORD)
            bio_text.pack(pady=5, padx=20)
            bio_text.insert("1.0", profile['bio'])
            bio_text.config(state=tk.DISABLED)
        
        # Display current and previous products from profile data
        current_prods = profile.get('current_products', [])
        previous_prods = profile.get('previous_products', [])
        
        if current_prods:
            tk.Label(window, text="📦 Current Products",
                    font=('Segoe UI', 14, 'bold'),
                    bg=self.app.bg_dark,
                    fg=self.app.text_light).pack(pady=(20, 5))
            for prod in current_prods:
                prod_frame = tk.Frame(window, bg=self.app.card_bg)
                prod_frame.pack(fill=tk.X, padx=20, pady=3)
                tk.Label(prod_frame, text=f"{prod['product_name']} - ${prod['price']} | ⭐{prod['rating']:.1f} | Stock: {prod['quantity']}",
                        font=('Segoe UI', 10),
                        bg=self.app.card_bg,
                        fg=self.app.text_light).pack(anchor="w", padx=10, pady=5)
        
        if previous_prods:
            tk.Label(window, text="📦 Previous Products (Sold Out)",
                    font=('Segoe UI', 14, 'bold'),
                    bg=self.app.bg_dark,
                    fg=self.app.text_secondary).pack(pady=(15, 5))
            for prod in previous_prods:
                prod_frame = tk.Frame(window, bg=self.app.card_bg)
                prod_frame.pack(fill=tk.X, padx=20, pady=3)
                tk.Label(prod_frame, text=f"{prod['product_name']} - ${prod['price']} | ⭐{prod['rating']:.1f} (SOLD)",
                        font=('Segoe UI', 10),
                        bg=self.app.card_bg,
                        fg=self.app.text_secondary).pack(anchor="w", padx=10, pady=5)
        
        if not current_prods and not previous_prods:
            tk.Label(window, text="No products listed",
                    bg=self.app.bg_dark,
                    fg=self.app.text_secondary).pack(pady=20)
    

    
    def on_close(self):
        """Handle window close"""
        try:
            if self.other_user in self.app.active_chats:
                del self.app.active_chats[self.other_user]
        except:
            pass
        try:
            self.window.destroy()
        except:
            pass
