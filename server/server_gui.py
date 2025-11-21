#!/usr/bin/env python3
"""
YaP Mic Pass Ult - Server GUI
Graphical interface for the server application.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import queue
import sys
import os
import socket

# Try to import PIL for icon support
try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Try to import pystray for system tray support
try:
    import pystray
    HAS_PYSTRAY = True
except ImportError:
    HAS_PYSTRAY = False

# Import server functionality
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from server import MicStreamServer

class ServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("YaP Mic Pass Ult - Server")
        self.root.geometry("700x550")
        self.root.resizable(True, True)
        
        # Set window icon
        self._set_window_icon()
        
        # Server instance
        self.server = None
        self.server_thread = None
        self.running = False
        
        # Message queue for thread-safe GUI updates
        self.message_queue = queue.Queue()
        
        # System tray
        self.tray_icon = None
        self.tray_thread = None
        self.hidden_to_tray = False
        
        # Setup UI
        self.create_widgets()
        
        # Start checking message queue
        self.check_queue()
        
        # Setup system tray if available
        if HAS_PYSTRAY:
            self.setup_system_tray()
        
        # Handle window close and minimize events
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Also intercept minimize event (when minimize button is clicked)
        if HAS_PYSTRAY:
            # Handle iconify event (minimize button clicked)
            self.root.bind('<Map>', self.on_window_map)
            # Override the iconify behavior
            self.root.bind_class('Tk', '<Unmap>', self.on_window_unmap)
            
            # Also handle when window is iconified via button
            def on_iconify(event=None):
                if self.root.state() == 'iconic':
                    if not self.hidden_to_tray:
                        self.root.after(50, self.hide_to_tray)
                return "break" if HAS_PYSTRAY and self.tray_icon else None
            
            # Use protocol for iconify
            self.root.bind('<Unmap>', on_iconify)
    
    def _set_window_icon(self):
        """Set the window icon from icon file."""
        try:
            # Try different icon locations
            icon_paths = [
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", "icon.png"),
                os.path.join(os.path.dirname(__file__), "..", "icons", "icon.png"),
                os.path.join(os.path.dirname(__file__), "icons", "icon.png"),
            ]
            
            icon_path = None
            for path in icon_paths:
                if os.path.exists(path):
                    icon_path = path
                    break
            
            if icon_path:
                # Try iconbitmap first (for .ico files), then use PhotoImage for PNG
                try:
                    if icon_path.endswith('.ico'):
                        self.root.iconbitmap(icon_path)
                    elif HAS_PIL:
                        img = Image.open(icon_path)
                        self.icon_img = ImageTk.PhotoImage(img)
                        self.root.iconphoto(True, self.icon_img)
                except:
                    pass
        except Exception as e:
            # Icon setting is optional, don't fail if it doesn't work
            pass
    
    def create_widgets(self):
        # Main container with reduced padding
        main_frame = ttk.Frame(self.root, padding="8")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Title with icon - more compact
        title_frame = ttk.Frame(main_frame)
        title_frame.grid(row=0, column=0, columnspan=2, pady=(0, 8))
        
        # Try to load and display icon
        if HAS_PIL:
            try:
                icon_paths = [
                    os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", "icon.png"),
                    os.path.join(os.path.dirname(__file__), "..", "icons", "icon.png"),
                    os.path.join(os.path.dirname(__file__), "icons", "icon.png"),
                ]
                
                icon_path = None
                for path in icon_paths:
                    if os.path.exists(path):
                        icon_path = path
                        break
                
                if icon_path:
                    img = Image.open(icon_path)
                    img = img.resize((32, 32), Image.Resampling.LANCZOS)
                    self.icon_photo = ImageTk.PhotoImage(img)
                    icon_label = ttk.Label(title_frame, image=self.icon_photo)
                    icon_label.grid(row=0, column=0, padx=(0, 10))
            except Exception:
                pass  # Continue without icon if it fails
        
        title_label = ttk.Label(title_frame, text="YaP Mic Pass Ult - Server", 
                               font=("Arial", 14, "bold"))
        title_label.grid(row=0, column=1)
        
        # Configuration frame - two column layout
        config_frame = ttk.LabelFrame(main_frame, text="Configuration", padding="6")
        config_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 6))
        config_frame.columnconfigure(1, weight=1)
        config_frame.columnconfigure(3, weight=1)
        
        # Port configuration
        ttk.Label(config_frame, text="Port:").grid(row=0, column=0, sticky=tk.W, pady=3)
        self.port_var = tk.StringVar(value="5000")
        port_entry = ttk.Entry(config_frame, textvariable=self.port_var, width=12)
        port_entry.grid(row=0, column=1, sticky=tk.W, padx=(5, 15), pady=3)
        
        # Virtual device name
        ttk.Label(config_frame, text="Device Name:").grid(row=0, column=2, sticky=tk.W, pady=3)
        self.device_name_var = tk.StringVar(value="YaP-Mic-Pass-Ult")
        device_entry = ttk.Entry(config_frame, textvariable=self.device_name_var, width=20)
        device_entry.grid(row=0, column=3, sticky=(tk.W, tk.E), padx=(5, 0), pady=3)
        
        # Volume control for virtual device
        ttk.Label(config_frame, text="Volume:").grid(row=1, column=0, sticky=tk.W, pady=3)
        volume_frame = ttk.Frame(config_frame)
        volume_frame.grid(row=1, column=1, columnspan=3, sticky=(tk.W, tk.E), padx=(5, 0), pady=3)
        volume_frame.columnconfigure(0, weight=1)
        
        self.device_volume_var = tk.DoubleVar(value=1.0)
        volume_scale = ttk.Scale(volume_frame, from_=0.0, to=2.0,
                                variable=self.device_volume_var, orient=tk.HORIZONTAL,
                                length=150)
        volume_scale.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        self.device_volume_label = ttk.Label(volume_frame, text="100%", width=5)
        self.device_volume_label.grid(row=0, column=1, sticky=tk.W)
        
        # Update volume label and apply to device
        self.device_volume_var.trace('w', self._update_device_volume)
        
        # Control and Status frame - combined
        control_status_frame = ttk.LabelFrame(main_frame, text="Control & Status", padding="6")
        control_status_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 6))
        control_status_frame.columnconfigure(2, weight=1)
        control_status_frame.columnconfigure(4, weight=1)
        control_status_frame.columnconfigure(6, weight=1)
        
        # Start/Stop button
        self.start_stop_button = ttk.Button(control_status_frame, text="▶ Start Server", 
                                           command=self.toggle_server, width=12)
        self.start_stop_button.grid(row=0, column=0, padx=(0, 15), pady=3)
        
        # Server status
        ttk.Label(control_status_frame, text="Server:", font=("Arial", 9)).grid(row=0, column=1, sticky=tk.W, padx=(0, 5))
        self.server_status_label = ttk.Label(control_status_frame, text="Stopped", 
                                            foreground="red", font=("Arial", 9, "bold"))
        self.server_status_label.grid(row=0, column=2, sticky=tk.W, padx=(0, 15))
        
        # Client connection status
        ttk.Label(control_status_frame, text="Client:", font=("Arial", 9)).grid(row=0, column=3, sticky=tk.W, padx=(0, 5))
        self.client_status_label = ttk.Label(control_status_frame, text="Not Connected", 
                                            foreground="gray", font=("Arial", 9))
        self.client_status_label.grid(row=0, column=4, sticky=tk.W, padx=(0, 15))
        
        # Virtual device status
        ttk.Label(control_status_frame, text="Device:", font=("Arial", 9)).grid(row=0, column=5, sticky=tk.W, padx=(0, 5))
        self.device_status_label = ttk.Label(control_status_frame, text="Not Created", 
                                            foreground="gray", font=("Arial", 9))
        self.device_status_label.grid(row=0, column=6, sticky=tk.W)
        
        # Log frame - reduced height
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="6")
        log_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 6))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # Log text area - smaller
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, width=70, 
                                                  wrap=tk.WORD, state=tk.DISABLED, font=("Courier", 9))
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Log controls
        log_controls = ttk.Frame(log_frame)
        log_controls.grid(row=1, column=0, sticky=tk.E, pady=(3, 0))
        
        clear_button = ttk.Button(log_controls, text="Clear", command=self.clear_log, width=8)
        clear_button.pack(side=tk.LEFT, padx=2)
    
    def log_message(self, message, level="info"):
        """Add message to log (thread-safe)."""
        self.message_queue.put(("log", message, level))
    
    def update_status(self, status_type, value, color=None):
        """Update status labels (thread-safe)."""
        self.message_queue.put(("status", status_type, value, color))
    
    def check_queue(self):
        """Check message queue for thread-safe GUI updates."""
        try:
            while True:
                msg = self.message_queue.get_nowait()
                if msg[0] == "log":
                    _, message, level = msg
                    self._add_log(message, level)
                elif msg[0] == "status":
                    _, status_type, value, color = msg
                    self._update_status(status_type, value, color)
        except queue.Empty:
            pass
        
        # Schedule next check
        self.root.after(100, self.check_queue)
    
    def _add_log(self, message, level="info"):
        """Add message to log text area."""
        self.log_text.config(state=tk.NORMAL)
        
        # Color coding
        if level == "error":
            tag = "error"
            self.log_text.tag_config("error", foreground="red")
        elif level == "success":
            tag = "success"
            self.log_text.tag_config("success", foreground="green")
        elif level == "warning":
            tag = "warning"
            self.log_text.tag_config("warning", foreground="orange")
        else:
            tag = "info"
            self.log_text.tag_config("info", foreground="black")
        
        self.log_text.insert(tk.END, message + "\n", tag)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def _update_status(self, status_type, value, color=None):
        """Update status label."""
        if status_type == "server":
            self.server_status_label.config(text=value, foreground=color or "black")
        elif status_type == "client":
            self.client_status_label.config(text=value, foreground=color or "black")
        elif status_type == "device":
            self.device_status_label.config(text=value, foreground=color or "black")
    
    def _update_device_volume(self, *args):
        """Update virtual device volume when scale changes."""
        if not self.server or not self.running:
            return
        
        volume = self.device_volume_var.get()
        percentage = int(volume * 100)
        self.device_volume_label.config(text=f"{percentage}%")
        
        # Apply volume to virtual device
        if self.server:
            self.server.set_virtual_device_volume(volume)
    
    def clear_log(self):
        """Clear log text area."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def toggle_server(self):
        """Start or stop the server."""
        if not self.running:
            self.start_server()
        else:
            self.stop_server()
    
    def start_server(self):
        """Start the server in a separate thread."""
        try:
            port = int(self.port_var.get())
            if port < 1 or port > 65535:
                messagebox.showerror("Error", "Port must be between 1 and 65535")
                return
            
            device_name = self.device_name_var.get().strip()
            if not device_name:
                messagebox.showerror("Error", "Device name cannot be empty")
                return
            
            # Disable controls
            self.start_stop_button.config(state=tk.DISABLED)
            
            # Create server instance
            self.server = MicStreamServer(
                port=port,
                virtual_device_name=device_name,
                use_pulseaudio=True
            )
            
            # Make sure server running flag is set
            self.server.running = True
            
            # Start server in thread
            self.running = True
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.start()
            
            self.log_message("Starting server...", "info")
            self.update_status("server", "Starting...", "orange")
            
        except ValueError:
            messagebox.showerror("Error", "Port must be a number")
            self.start_stop_button.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start server: {e}")
            self.start_stop_button.config(state=tk.NORMAL)
            self.running = False
    
    def _setup_server_logging(self):
        """Redirect server output to GUI log."""
        # We'll catch log messages through the server's behavior
        pass
    
    def _run_server(self):
        """Run server in background thread with GUI integration."""
        # We need to override the server's run method behavior to integrate with GUI
        try:
            # Set up virtual device first
            import platform
            if platform.system() == "Linux":
                if self.server.setup_virtual_device_linux():
                    self.update_status("device", "Created", "green")
                    self.log_message(f"Virtual device '{self.server.virtual_device_name}' created", "success")
                    # Configure the source (unmute, set volume) - already done in setup_virtual_device_linux
                else:
                    self.update_status("device", "Failed", "red")
                    self.log_message("Failed to create virtual device", "error")
                    self.running = False
                    self.root.after(0, lambda: self.start_stop_button.config(text="Start Server", state=tk.NORMAL))
                    return
            
            if self.server.start_server():
                self.update_status("server", "Running", "green")
                self.log_message(f"Server listening on port {self.server.port}", "success")
                self.root.after(0, lambda: self.start_stop_button.config(text="Stop Server", state=tk.NORMAL))
                
                # Now handle connections
                while self.running and self.server.running:
                    try:
                        if self.server.accept_client():
                            self.update_status("client", "Connected", "green")
                            self.log_message("Client connected", "success")
                            
                            if self.server.receive_audio_config():
                                self.log_message("Audio configuration received", "info")
                                self.log_message(f"  Sample rate: {self.server.sample_rate} Hz", "info")
                                self.log_message(f"  Channels: {self.server.channels}", "info")
                                
                                # Stream audio
                                self._stream_audio()
                            
                            # Close connection
                            if self.server.client_socket:
                                self.server.client_socket.close()
                                self.server.client_socket = None
                            
                            self.update_status("client", "Not Connected", "gray")
                            self.log_message("Client disconnected", "info")
                            
                            # Reset pipe for next connection
                            if self.server.pipe_file:
                                self.server.pipe_file.close()
                                self.server.pipe_file = None
                            
                            # Recreate pipe for next connection
                            if self.server.pipe_path and not os.path.exists(self.server.pipe_path):
                                try:
                                    os.mkfifo(self.server.pipe_path)
                                except:
                                    pass
                            
                            self.log_message("Waiting for next client connection...", "info")
                    except Exception as e:
                        if self.running:
                            self.log_message(f"Connection error: {e}", "error")
                        break
            else:
                self.log_message("Failed to start server", "error")
                self.update_status("server", "Failed", "red")
                self.running = False
                self.root.after(0, lambda: self.start_stop_button.config(text="Start Server", state=tk.NORMAL))
                
        except Exception as e:
            self.log_message(f"Server error: {e}", "error")
            self.update_status("server", "Error", "red")
            self.running = False
            self.root.after(0, lambda: self.start_stop_button.config(text="Start Server", state=tk.NORMAL))
    
    def _stream_audio(self):
        """Stream audio from client."""
        import threading
        
        writer_thread = threading.Thread(target=self.server.audio_writer_thread, daemon=True)
        writer_thread.start()
        
        self.log_message("Streaming audio...", "info")
        
        try:
            while self.running and self.server.running:
                try:
                    data_size = self.server.chunk_size * self.server.channels * 2
                    data = self.server.client_socket.recv(data_size)
                    
                    if not data:
                        break
                    
                    try:
                        self.server.audio_queue.put_nowait(data)
                    except queue.Full:
                        try:
                            self.server.audio_queue.get_nowait()
                            self.server.audio_queue.put_nowait(data)
                        except queue.Empty:
                            pass
                    
                except socket.error as e:
                    self.log_message(f"Connection error: {e}", "error")
                    break
                except Exception as e:
                    self.log_message(f"Streaming error: {e}", "error")
                    break
        
        except Exception as e:
            self.log_message(f"Error in audio stream: {e}", "error")
        finally:
            self.server.running = False
            writer_thread.join(timeout=3)
    
    def stop_server(self):
        """Stop the server."""
        self.running = False
        self.log_message("Stopping server...", "info")
        
        if self.server:
            self.server.running = False
            self.server.cleanup()
            self.server = None
        
        self.update_status("server", "Stopped", "red")
        self.update_status("client", "Not Connected", "gray")
        self.update_status("device", "Not Created", "gray")
        self.root.after(0, lambda: self.start_stop_button.config(text="Start Server", state=tk.NORMAL))
        self.log_message("Server stopped", "info")
    
    def setup_system_tray(self):
        """Setup system tray icon and menu."""
        if not HAS_PYSTRAY:
            return
        
        try:
            # Try to load icon for tray
            icon_paths = [
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", "icon.png"),
                os.path.join(os.path.dirname(__file__), "..", "icons", "icon.png"),
                os.path.join(os.path.dirname(__file__), "icons", "icon.png"),
            ]
            
            tray_image = None
            for path in icon_paths:
                if os.path.exists(path):
                    try:
                        tray_image = Image.open(path)
                        tray_image = tray_image.resize((64, 64), Image.Resampling.LANCZOS)
                        break
                    except:
                        pass
            
            # Fallback to a simple icon if image loading fails
            if not tray_image:
                tray_image = Image.new('RGB', (64, 64), color='red')
            
            # Create menu
            menu = pystray.Menu(
                pystray.MenuItem('Show Window', self.show_window),
                pystray.MenuItem('Quit', self.quit_application)
            )
            
            # Create tray icon
            self.tray_icon = pystray.Icon("YaP Mic Pass Ult Server", tray_image, 
                                         "YaP Mic Pass Ult - Server", menu)
            
            # Start tray in separate thread
            self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
            self.tray_thread.start()
        except Exception as e:
            print(f"Warning: Could not setup system tray: {e}")
            self.tray_icon = None
    
    def show_window(self, icon=None, item=None):
        """Show the main window."""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.hidden_to_tray = False
    
    def on_window_unmap(self, event=None):
        """Handle window unmapping (minimizing)."""
        if event and event.widget == self.root:
            # Check if window is being minimized (iconified)
            if HAS_PYSTRAY and self.tray_icon and not self.hidden_to_tray:
                # Small delay to check window state
                self.root.after(100, lambda: self.check_and_hide_to_tray())
    
    def check_and_hide_to_tray(self):
        """Check if window should be hidden to tray."""
        try:
            # If window is still iconified, hide to tray
            if self.root.state() == 'iconic' and not self.hidden_to_tray:
                self.hide_to_tray()
        except:
            pass
    
    def on_window_map(self, event=None):
        """Handle window mapping (restoring)."""
        if event.widget == self.root:
            self.hidden_to_tray = False
    
    def hide_to_tray(self):
        """Hide window to system tray."""
        if self.tray_icon:
            self.root.withdraw()
            self.hidden_to_tray = True
    
    def quit_application(self, icon=None, item=None):
        """Quit the application."""
        if self.running:
            self.stop_server()
        
        if self.tray_icon:
            self.tray_icon.stop()
        
        self.root.after(500, lambda: (self.root.quit(), self.root.destroy()))
    
    def on_closing(self, event=None):
        """Handle window close event - always minimize to tray."""
        if HAS_PYSTRAY and self.tray_icon:
            # Minimize to tray instead of closing
            self.hide_to_tray()
            return "break"  # Prevent default close behavior
        else:
            # No tray support, ask to quit
            if self.running:
                if messagebox.askokcancel("Quit", "Server is running. Stop and quit?"):
                    self.stop_server()
                    self.root.after(500, self.root.destroy)  # Give cleanup time
                else:
                    return "break"  # Don't close if user cancels
            else:
                self.root.destroy()
    
    def on_minimize(self, event=None):
        """Handle window minimize event - minimize to tray."""
        if HAS_PYSTRAY and self.tray_icon:
            self.hide_to_tray()
            return "break"  # Prevent default minimize behavior

def main():
    root = tk.Tk()
    app = ServerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
