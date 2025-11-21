#!/usr/bin/env python3
"""
YaP Mic Pass Ult - Client GUI
Graphical interface for the client application.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import queue
import sys
import os

# Suppress ALSA warnings (PyAudio tries multiple backends, these are harmless)
if hasattr(sys, '_getframe'):
    # Only suppress if not in debug mode
    if '--debug' not in sys.argv and '-v' not in sys.argv:
        # Save original stderr
        _original_stderr = sys.stderr
        
        class FilteredStderr:
            """Filter out ALSA/JACK warnings while keeping errors."""
            def __init__(self, original):
                self.original = original
            
            def write(self, text):
                # Filter out common ALSA/JACK warnings
                if any(keyword in text.lower() for keyword in [
                    'alsa lib', 'jack server', 'cannot connect to server socket',
                    'unknown pcm', 'unable to open slave', 'jackshmreadwriteptr',
                    'pcm_dsnoop', 'pcm_dmix', 'pcm_oss', 'pcm_a52', 'pcm_usb_stream',
                    'pcm_jack_open'
                ]):
                    return  # Suppress these warnings
                self.original.write(text)
            
            def flush(self):
                self.original.flush()
            
            def __getattr__(self, name):
                return getattr(self.original, name)
        
        # Only filter if we're not in a terminal that might want to see errors
        if not sys.stderr.isatty() or os.getenv('SUPPRESS_ALSA_WARNINGS', '1') == '1':
            sys.stderr = FilteredStderr(_original_stderr)

import pyaudio

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

# Import client functionality
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from client import MicStreamClient

class ClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("YaP Mic Pass Ult - Client")
        self.root.geometry("700x600")
        self.root.resizable(True, True)
        
        # Set window icon
        self._set_window_icon()
        
        # Client instance
        self.client = None
        self.client_thread = None
        self.running = False
        
        # Message queue for thread-safe GUI updates
        self.message_queue = queue.Queue()
        
        # Audio devices
        self.audio_devices = []
        
        # System tray
        self.tray_icon = None
        self.tray_thread = None
        self.hidden_to_tray = False
        
        # Setup UI
        self.create_widgets()
        
        # Load audio devices
        self.refresh_devices()
        
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
        
        title_label = ttk.Label(title_frame, text="YaP Mic Pass Ult - Client", 
                               font=("Arial", 14, "bold"))
        title_label.grid(row=0, column=1)
        
        # Connection frame - two columns for compact layout
        connection_frame = ttk.LabelFrame(main_frame, text="Server Connection", padding="6")
        connection_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 6))
        connection_frame.columnconfigure(1, weight=1)
        connection_frame.columnconfigure(3, weight=1)
        
        # Server host
        ttk.Label(connection_frame, text="Host:").grid(row=0, column=0, sticky=tk.W, pady=3)
        self.host_var = tk.StringVar(value="localhost")
        host_entry = ttk.Entry(connection_frame, textvariable=self.host_var, width=25)
        host_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 10), pady=3)
        
        # Server port
        ttk.Label(connection_frame, text="Port:").grid(row=0, column=2, sticky=tk.W, pady=3)
        self.port_var = tk.StringVar(value="5000")
        port_entry = ttk.Entry(connection_frame, textvariable=self.port_var, width=12)
        port_entry.grid(row=0, column=3, sticky=tk.W, padx=(5, 0), pady=3)
        
        # Audio device frame - more compact
        device_frame = ttk.LabelFrame(main_frame, text="Audio Device", padding="6")
        device_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 6))
        device_frame.columnconfigure(1, weight=1)
        
        # Device selection
        ttk.Label(device_frame, text="Microphone:").grid(row=0, column=0, sticky=tk.W, pady=3)
        device_select_frame = ttk.Frame(device_frame)
        device_select_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=3)
        device_select_frame.columnconfigure(0, weight=1)
        
        self.device_var = tk.StringVar()
        self.device_combo = ttk.Combobox(device_select_frame, textvariable=self.device_var, 
                                        state="readonly", width=35)
        self.device_combo.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        refresh_button = ttk.Button(device_select_frame, text="Refresh", 
                                    command=self.refresh_devices, width=8)
        refresh_button.grid(row=0, column=1, padx=(5, 0))
        
        # Audio settings frame - two column layout
        settings_frame = ttk.LabelFrame(main_frame, text="Audio Settings", padding="6")
        settings_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 6))
        settings_frame.columnconfigure(1, weight=1)
        settings_frame.columnconfigure(3, weight=1)
        
        # Sample rate
        ttk.Label(settings_frame, text="Sample Rate:").grid(row=0, column=0, sticky=tk.W, pady=3)
        self.sample_rate_var = tk.StringVar(value="44100")
        sample_rate_combo = ttk.Combobox(settings_frame, textvariable=self.sample_rate_var,
                                        values=["8000", "16000", "22050", "44100", "48000"],
                                        state="readonly", width=15)
        sample_rate_combo.grid(row=0, column=1, sticky=tk.W, padx=(5, 10), pady=3)
        
        # Channels
        ttk.Label(settings_frame, text="Channels:").grid(row=0, column=2, sticky=tk.W, pady=3)
        self.channels_var = tk.StringVar(value="1")
        channels_combo = ttk.Combobox(settings_frame, textvariable=self.channels_var,
                                     values=["1", "2"], state="readonly", width=8)
        channels_combo.grid(row=0, column=3, sticky=tk.W, padx=(5, 0), pady=3)
        
        # Chunk size
        ttk.Label(settings_frame, text="Chunk Size:").grid(row=1, column=0, sticky=tk.W, pady=3)
        self.chunk_var = tk.StringVar(value="128")
        chunk_entry = ttk.Entry(settings_frame, textvariable=self.chunk_var, width=15)
        chunk_entry.grid(row=1, column=1, sticky=tk.W, padx=(5, 10), pady=3)
        
        # Volume control
        ttk.Label(settings_frame, text="Volume:").grid(row=1, column=2, sticky=tk.W, pady=3)
        volume_frame = ttk.Frame(settings_frame)
        volume_frame.grid(row=1, column=3, sticky=(tk.W, tk.E), padx=(5, 0), pady=3)
        volume_frame.columnconfigure(0, weight=1)
        
        self.volume_var = tk.DoubleVar(value=1.0)
        volume_scale = ttk.Scale(volume_frame, from_=0.0, to=2.0, 
                                variable=self.volume_var, orient=tk.HORIZONTAL,
                                length=120)
        volume_scale.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        self.volume_label = ttk.Label(volume_frame, text="100%", width=5)
        self.volume_label.grid(row=0, column=1, sticky=tk.W)
        
        # Update volume label when scale changes
        self.volume_var.trace('w', self._update_volume_label)
        
        # Control and Status frame - combined for space
        control_status_frame = ttk.LabelFrame(main_frame, text="Control & Status", padding="6")
        control_status_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 6))
        control_status_frame.columnconfigure(2, weight=1)
        
        # Connect/Disconnect button
        self.connect_button = ttk.Button(control_status_frame, text="▶ Connect", 
                                        command=self.toggle_connection, width=12)
        self.connect_button.grid(row=0, column=0, padx=(0, 15), pady=3)
        
        # Connection status - inline
        ttk.Label(control_status_frame, text="Connection:", font=("Arial", 9)).grid(row=0, column=1, sticky=tk.W, padx=(0, 5))
        self.connection_status_label = ttk.Label(control_status_frame, text="Disconnected", 
                                                foreground="red", font=("Arial", 9, "bold"))
        self.connection_status_label.grid(row=0, column=2, sticky=tk.W, padx=(0, 15))
        
        # Streaming status - inline
        ttk.Label(control_status_frame, text="Streaming:", font=("Arial", 9)).grid(row=0, column=3, sticky=tk.W, padx=(0, 5))
        self.streaming_status_label = ttk.Label(control_status_frame, text="Not Streaming", 
                                               foreground="gray", font=("Arial", 9))
        self.streaming_status_label.grid(row=0, column=4, sticky=tk.W)
        
        # Log frame - reduced height
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="6")
        log_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 6))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
        # Log text area - smaller
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, width=70, 
                                                  wrap=tk.WORD, state=tk.DISABLED, font=("Courier", 9))
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Log controls
        log_controls = ttk.Frame(log_frame)
        log_controls.grid(row=1, column=0, sticky=tk.E, pady=(3, 0))
        
        clear_button = ttk.Button(log_controls, text="Clear", command=self.clear_log, width=8)
        clear_button.pack(side=tk.LEFT, padx=2)
    
    def refresh_devices(self):
        """Refresh list of available audio input devices."""
        try:
            # Suppress ALSA warnings during device enumeration
            old_stderr = sys.stderr
            try:
                with open(os.devnull, 'w') as devnull:
                    sys.stderr = devnull
                    audio = pyaudio.PyAudio()
            finally:
                sys.stderr = old_stderr
            
            devices = []
            device_names = []
            
            for i in range(audio.get_device_count()):
                try:
                    info = audio.get_device_info_by_index(i)
                    if info['maxInputChannels'] > 0:
                        device_name = f"{i}: {info['name']}"
                        devices.append({
                            'index': i,
                            'name': info['name'],
                            'channels': info['maxInputChannels'],
                            'sample_rate': int(info['defaultSampleRate'])
                        })
                        device_names.append(device_name)
                except:
                    continue
            
            audio.terminate()
            
            self.audio_devices = devices
            self.device_combo['values'] = device_names
            
            # Select default device if available
            if device_names:
                try:
                    old_stderr = sys.stderr
                    try:
                        with open(os.devnull, 'w') as devnull:
                            sys.stderr = devnull
                            default_audio = pyaudio.PyAudio()
                            default_info = default_audio.get_default_input_device_info()
                            default_index = default_info['index']
                            default_audio.terminate()
                    finally:
                        sys.stderr = old_stderr
                    
                    for i, dev in enumerate(devices):
                        if dev['index'] == default_index:
                            self.device_combo.current(i)
                            break
                except:
                    if device_names:
                        self.device_combo.current(0)
            
            self.log_message(f"Found {len(devices)} audio input device(s)", "info")
            
        except Exception as e:
            self.log_message(f"Error refreshing devices: {e}", "error")
            messagebox.showerror("Error", f"Failed to refresh audio devices: {e}")
    
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
        if status_type == "connection":
            self.connection_status_label.config(text=value, foreground=color or "black")
        elif status_type == "streaming":
            self.streaming_status_label.config(text=value, foreground=color or "black")
    
    def _update_volume_label(self, *args):
        """Update volume label when scale changes."""
        volume = self.volume_var.get()
        percentage = int(volume * 100)
        self.volume_label.config(text=f"{percentage}%")
    
    def _on_volume_change(self, *args):
        """Handle real-time volume changes during streaming."""
        if self.client and self.running:
            volume = self.volume_var.get()
            self.client.set_volume(volume)
    
    def clear_log(self):
        """Clear log text area."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def toggle_connection(self):
        """Connect or disconnect from server."""
        if not self.running:
            self.connect()
        else:
            self.disconnect()
    
    def connect(self):
        """Connect to server and start streaming."""
        try:
            # Validate inputs
            host = self.host_var.get().strip()
            if not host:
                messagebox.showerror("Error", "Server host cannot be empty")
                return
            
            port = int(self.port_var.get())
            if port < 1 or port > 65535:
                messagebox.showerror("Error", "Port must be between 1 and 65535")
                return
            
            # Get selected device
            device_selection = self.device_var.get()
            if not device_selection:
                messagebox.showerror("Error", "Please select a microphone device")
                return
            
            # Extract device index
            device_index = int(device_selection.split(":")[0])
            
            # Get audio settings
            sample_rate = int(self.sample_rate_var.get())
            channels = int(self.channels_var.get())
            chunk_size = int(self.chunk_var.get())
            volume = float(self.volume_var.get())
            
            if chunk_size < 64 or chunk_size > 2048:
                messagebox.showerror("Error", "Chunk size must be between 64 and 2048 (lower = less latency)")
                return
            
            if volume < 0.0 or volume > 2.0:
                messagebox.showerror("Error", "Volume must be between 0.0 and 2.0")
                return
            
            # Disable controls
            self.connect_button.config(state=tk.DISABLED)
            
            # Create client instance
            self.client = MicStreamClient(
                server_host=host,
                server_port=port,
                sample_rate=sample_rate,
                channels=channels,
                chunk_size=chunk_size,
                device_index=device_index,
                volume=volume
            )
            
            # Start client in thread
            self.running = True
            self.client_thread = threading.Thread(target=self._run_client, daemon=True)
            self.client_thread.start()
            
            self.log_message(f"Connecting to {host}:{port}...", "info")
            self.update_status("connection", "Connecting...", "orange")
            
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {e}")
            self.connect_button.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start client: {e}")
            self.connect_button.config(state=tk.NORMAL)
            self.running = False
    
    def _run_client(self):
        """Run client in background thread."""
        try:
            if self.client.connect_to_server():
                self.update_status("connection", "Connected", "green")
                self.log_message("Connected to server", "success")
                
                if self.client.send_audio_config():
                    self.log_message("Audio configuration sent", "info")
                    
                    # Get device info for logging
                    device_name = "Unknown"
                    if self.audio_devices:
                        for dev in self.audio_devices:
                            if dev['index'] == self.client.device_index:
                                device_name = dev['name']
                                break
                    
                    self.log_message(f"Streaming from: {device_name}", "info")
                    self.log_message(f"Sample rate: {self.client.sample_rate} Hz, "
                                   f"Channels: {self.client.channels}", "info")
                    self.log_message(f"Volume: {int(self.client.volume * 100)}%", "info")
                    
                    # Update button and status
                    self.root.after(0, lambda: self.connect_button.config(text="Disconnect", state=tk.NORMAL))
                    self.update_status("streaming", "Streaming", "green")
                    self.log_message("Streaming audio...", "success")
                    
                    # Enable real-time volume adjustment (remove old trace first if exists)
                    try:
                        self.volume_var.trace_remove("write", self.volume_var.trace_info()[0][0])
                    except:
                        pass
                    self.volume_trace_id = self.volume_var.trace('w', self._on_volume_change)
                    
                    # Start streaming
                    self.client.stream_audio()
                    
                else:
                    self.log_message("Failed to send audio configuration", "error")
                    self.update_status("connection", "Disconnected", "red")
                    self.root.after(0, lambda: self.connect_button.config(text="Connect", state=tk.NORMAL))
                    self.running = False
            else:
                self.log_message("Failed to connect to server", "error")
                self.update_status("connection", "Disconnected", "red")
                self.root.after(0, lambda: self.connect_button.config(text="Connect", state=tk.NORMAL))
                self.running = False
                
        except Exception as e:
            self.log_message(f"Client error: {e}", "error")
            self.update_status("connection", "Disconnected", "red")
            self.update_status("streaming", "Not Streaming", "gray")
            self.root.after(0, lambda: self.connect_button.config(text="Connect", state=tk.NORMAL))
            self.running = False
    
    def disconnect(self):
        """Disconnect from server."""
        self.running = False
        self.log_message("Disconnecting...", "info")
        
        if self.client:
            self.client.running = False
            self.client.cleanup()
        
        self.update_status("connection", "Disconnected", "red")
        self.update_status("streaming", "Not Streaming", "gray")
        self.connect_button.config(text="Connect", state=tk.NORMAL)
        self.log_message("Disconnected", "info")
    
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
                tray_image = Image.new('RGB', (64, 64), color='blue')
            
            # Create menu
            menu = pystray.Menu(
                pystray.MenuItem('Show Window', self.show_window),
                pystray.MenuItem('Quit', self.quit_application)
            )
            
            # Create tray icon
            self.tray_icon = pystray.Icon("YaP Mic Pass Ult Client", tray_image, 
                                         "YaP Mic Pass Ult - Client", menu)
            
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
            self.disconnect()
        
        if self.tray_icon:
            self.tray_icon.stop()
        
        self.root.quit()
        self.root.destroy()
    
    def on_closing(self, event=None):
        """Handle window close event - always minimize to tray."""
        if HAS_PYSTRAY and self.tray_icon:
            # Minimize to tray instead of closing
            self.hide_to_tray()
            return "break"  # Prevent default close behavior
        else:
            # No tray support, ask to quit
            if self.running:
                if messagebox.askokcancel("Quit", "Client is connected. Disconnect and quit?"):
                    self.disconnect()
                    self.root.destroy()
            else:
                self.root.destroy()
    
    def on_minimize(self, event=None):
        """Handle window minimize event - minimize to tray."""
        if HAS_PYSTRAY and self.tray_icon:
            self.hide_to_tray()
            return "break"  # Prevent default minimize behavior

def main():
    root = tk.Tk()
    app = ClientGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
