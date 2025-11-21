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
        self.root.geometry("750x650")
        self.root.resizable(True, True)
        
        # Configure modern style
        style = ttk.Style()
        style.theme_use('clam')  # Modern theme
        style.configure('Title.TLabel', font=('Segoe UI', 14, 'bold'))
        style.configure('Status.TLabel', font=('Segoe UI', 9))
        style.configure('Heading.TLabel', font=('Segoe UI', 10, 'bold'))
        
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
        # Main container with minimal padding
        main_frame = ttk.Frame(self.root, padding="8")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Modern header with icon
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 12))
        
        # Icon and title
        title_container = ttk.Frame(header_frame)
        title_container.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
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
                    img = img.resize((28, 28), Image.Resampling.LANCZOS)
                    self.icon_photo = ImageTk.PhotoImage(img)
                    icon_label = ttk.Label(title_container, image=self.icon_photo)
                    icon_label.pack(side=tk.LEFT, padx=(0, 8))
            except Exception:
                pass
        
        title_label = ttk.Label(title_container, text="YaP Mic Pass Ult - Client", 
                               style='Title.TLabel')
        title_label.pack(side=tk.LEFT)
        
        # Status indicator in header
        self.header_status = ttk.Label(header_frame, text="●", font=('Segoe UI', 12),
                                      foreground='gray')
        self.header_status.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Use notebook (tabs) for better organization
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 8))
        main_frame.rowconfigure(1, weight=1)
        
        # Connection Tab
        connection_tab = ttk.Frame(notebook, padding="10")
        notebook.add(connection_tab, text="Connection")
        connection_tab.columnconfigure(1, weight=1)
        
        # Connection settings in compact grid
        ttk.Label(connection_tab, text="Server Host:", width=15, anchor=tk.W).grid(row=0, column=0, sticky=tk.W, pady=4)
        self.host_var = tk.StringVar(value="localhost")
        host_entry = ttk.Entry(connection_tab, textvariable=self.host_var)
        host_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(8, 0), pady=4)
        
        ttk.Label(connection_tab, text="Port:", width=15, anchor=tk.W).grid(row=1, column=0, sticky=tk.W, pady=4)
        self.port_var = tk.StringVar(value="5000")
        port_entry = ttk.Entry(connection_tab, textvariable=self.port_var, width=15)
        port_entry.grid(row=1, column=1, sticky=tk.W, padx=(8, 0), pady=4)
        
        # Audio Device Tab
        device_tab = ttk.Frame(notebook, padding="10")
        notebook.add(device_tab, text="Audio Device")
        device_tab.columnconfigure(1, weight=1)
        
        ttk.Label(device_tab, text="Microphone:", width=15, anchor=tk.W).grid(row=0, column=0, sticky=tk.W, pady=4)
        device_select_frame = ttk.Frame(device_tab)
        device_select_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(8, 0), pady=4)
        device_select_frame.columnconfigure(0, weight=1)
        
        self.device_var = tk.StringVar()
        self.device_combo = ttk.Combobox(device_select_frame, textvariable=self.device_var, 
                                        state="readonly")
        self.device_combo.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        refresh_button = ttk.Button(device_select_frame, text="🔄", width=3,
                                    command=self.refresh_devices)
        refresh_button.grid(row=0, column=1, padx=(5, 0))
        
        # Audio Settings Tab
        settings_tab = ttk.Frame(notebook, padding="10")
        notebook.add(settings_tab, text="Audio Settings")
        settings_tab.columnconfigure(1, weight=1)
        
        # Quality preset (most important, at top)
        ttk.Label(settings_tab, text="Quality Preset:", width=18, anchor=tk.W).grid(row=0, column=0, sticky=tk.W, pady=6)
        self.quality_var = tk.StringVar(value="balanced")
        quality_frame = ttk.Frame(settings_tab)
        quality_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(8, 0), pady=6)
        quality_frame.columnconfigure(0, weight=1)
        
        quality_combo = ttk.Combobox(quality_frame, textvariable=self.quality_var,
                                    values=["low_latency", "balanced", "high_quality"],
                                    state="readonly", width=25)
        quality_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        quality_combo.bind('<<ComboboxSelected>>', self._on_quality_change)
        
        self.quality_info_label = ttk.Label(quality_frame, text="~30-60ms latency",
                                           font=('Segoe UI', 8), foreground="gray")
        self.quality_info_label.pack(side=tk.LEFT, padx=(8, 0))
        
        # Sample rate
        ttk.Label(settings_tab, text="Sample Rate:", width=18, anchor=tk.W).grid(row=1, column=0, sticky=tk.W, pady=6)
        self.sample_rate_var = tk.StringVar(value="44100")
        sample_rate_combo = ttk.Combobox(settings_tab, textvariable=self.sample_rate_var,
                                        values=["8000", "16000", "22050", "44100", "48000"],
                                        state="readonly", width=25)
        sample_rate_combo.grid(row=1, column=1, sticky=tk.W, padx=(8, 0), pady=6)
        
        # Channels
        ttk.Label(settings_tab, text="Channels:", width=18, anchor=tk.W).grid(row=2, column=0, sticky=tk.W, pady=6)
        self.channels_var = tk.StringVar(value="1")
        channels_combo = ttk.Combobox(settings_tab, textvariable=self.channels_var,
                                     values=["1", "2"], state="readonly", width=25)
        channels_combo.grid(row=2, column=1, sticky=tk.W, padx=(8, 0), pady=6)
        
        # Chunk size
        ttk.Label(settings_tab, text="Chunk Size:", width=18, anchor=tk.W).grid(row=3, column=0, sticky=tk.W, pady=6)
        self.chunk_var = tk.StringVar(value="128")
        chunk_entry = ttk.Entry(settings_tab, textvariable=self.chunk_var, width=25)
        chunk_entry.grid(row=3, column=1, sticky=tk.W, padx=(8, 0), pady=6)
        ttk.Label(settings_tab, text="(64-256, lower = less latency)", 
                 font=('Segoe UI', 8), foreground="gray").grid(row=3, column=2, sticky=tk.W, padx=(8, 0))
        
        # Volume control
        ttk.Label(settings_tab, text="Volume:", width=18, anchor=tk.W).grid(row=4, column=0, sticky=tk.W, pady=6)
        volume_frame = ttk.Frame(settings_tab)
        volume_frame.grid(row=4, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=(8, 0), pady=6)
        volume_frame.columnconfigure(0, weight=1)
        
        self.volume_var = tk.DoubleVar(value=1.0)
        volume_scale = ttk.Scale(volume_frame, from_=0.0, to=2.0, 
                                variable=self.volume_var, orient=tk.HORIZONTAL)
        volume_scale.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 8))
        
        self.volume_label = ttk.Label(volume_frame, text="100%", width=5)
        self.volume_label.grid(row=0, column=1)
        
        self.volume_var.trace('w', self._update_volume_label)
        
        # Control buttons (outside tabs, always visible)
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=2, column=0, columnspan=2, pady=(0, 8))
        
        self.connect_button = ttk.Button(control_frame, text="▶ Connect", 
                                        command=self.toggle_connection, width=18)
        self.connect_button.pack(side=tk.LEFT, padx=4)
        
        # Status indicators (compact)
        status_container = ttk.Frame(main_frame)
        status_container.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 8))
        status_container.columnconfigure(0, weight=1)
        status_container.columnconfigure(2, weight=1)
        
        self.connection_status_label = ttk.Label(status_container, text="● Disconnected", 
                                                foreground="red", style='Status.TLabel')
        self.connection_status_label.grid(row=0, column=0, sticky=tk.W, padx=4)
        
        self.streaming_status_label = ttk.Label(status_container, text="● Not Streaming", 
                                               foreground="gray", style='Status.TLabel')
        self.streaming_status_label.grid(row=0, column=2, sticky=tk.W, padx=4)
        
        # Log frame (more compact)
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="6")
        log_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # Log text area with modern styling
        log_container = ttk.Frame(log_frame)
        log_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_container.columnconfigure(0, weight=1)
        log_container.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_container, height=8, width=70, 
                                                  wrap=tk.WORD, state=tk.DISABLED,
                                                  font=('Consolas', 9), relief=tk.FLAT)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Compact log controls
        log_controls = ttk.Frame(log_frame)
        log_controls.grid(row=1, column=0, sticky=tk.E, pady=(4, 0))
        
        clear_button = ttk.Button(log_controls, text="Clear", width=8, command=self.clear_log)
        clear_button.pack(side=tk.LEFT)
    
    def refresh_devices(self):
        """Refresh list of available audio input devices."""
        try:
            audio = pyaudio.PyAudio()
            devices = []
            device_names = []
            
            for i in range(audio.get_device_count()):
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
            
            audio.terminate()
            
            self.audio_devices = devices
            self.device_combo['values'] = device_names
            
            # Select default device if available
            if device_names:
                try:
                    default_audio = pyaudio.PyAudio()
                    default_info = default_audio.get_default_input_device_info()
                    default_index = default_info['index']
                    default_audio.terminate()
                    
                    for i, dev in enumerate(devices):
                        if dev['index'] == default_index:
                            self.device_combo.current(i)
                            break
                except:
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
        status_indicator = "●"
        if status_type == "connection":
            status_text = f"{status_indicator} {value}"
            self.connection_status_label.config(text=status_text, foreground=color or "black")
            # Update header status
            if color == "green":
                self.header_status.config(text="●", foreground="green")
            elif color == "red":
                self.header_status.config(text="●", foreground="red")
            elif color == "orange":
                self.header_status.config(text="●", foreground="orange")
        elif status_type == "streaming":
            status_text = f"{status_indicator} {value}"
            self.streaming_status_label.config(text=status_text, foreground=color or "black")
    
    def _update_volume_label(self, *args):
        """Update volume label when scale changes."""
        volume = self.volume_var.get()
        percentage = int(volume * 100)
        self.volume_label.config(text=f"{percentage}%")
    
    def _on_quality_change(self, event=None):
        """Handle quality preset change."""
        quality = self.quality_var.get()
        
        # Update chunk size and sample rate based on quality
        if quality == 'low_latency':
            self.chunk_var.set("128")
            self.sample_rate_var.set("22050")
            self.quality_info_label.config(text="~15-30ms latency")
        elif quality == 'balanced':
            self.chunk_var.set("128")
            self.sample_rate_var.set("44100")
            self.quality_info_label.config(text="~30-60ms latency")
        elif quality == 'high_quality':
            self.chunk_var.set("512")
            self.sample_rate_var.set("44100")
            self.quality_info_label.config(text="~60-100ms latency")
    
    def _on_volume_change(self, *args):
        """Handle real-time volume changes during streaming."""
        if self.client and self.running:
            volume = self.volume_var.get()
            self.client.set_volume(volume)
    
    def _estimate_latency(self):
        """Estimate latency based on current settings."""
        if not self.client:
            return "?"
        
        # Calculate latency components
        chunk_latency = (self.client.chunk_size / self.client.sample_rate) * 1000  # ms
        network_latency = 5 if self.client.quality == 'low_latency' else 10  # estimated
        processing_latency = 2 if self.client.quality == 'low_latency' else 5
        
        total = int(chunk_latency * 2 + network_latency + processing_latency)  # *2 for client+server buffers
        return total
    
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
            quality = self.quality_var.get()
            
            if chunk_size < 64 or chunk_size > 2048:
                messagebox.showerror("Error", "Chunk size must be between 64 and 2048 (lower = less latency)")
                return
            
            if volume < 0.0 or volume > 2.0:
                messagebox.showerror("Error", "Volume must be between 0.0 and 2.0")
                return
            
            if sample_rate not in [8000, 16000, 22050, 44100, 48000]:
                messagebox.showerror("Error", "Sample rate must be one of: 8000, 16000, 22050, 44100, 48000")
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
                volume=volume,
                quality=quality
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
                    self.log_message(f"Chunk size: {self.client.chunk_size} frames", "info")
                    self.log_message(f"Quality: {self.client.quality}", "info")
                    self.log_message(f"Volume: {int(self.client.volume * 100)}%", "info")
                    self.log_message(f"Estimated latency: ~{self._estimate_latency()}ms", "info")
                    
                    # Update button and status
                    self.root.after(0, lambda: self.connect_button.config(text="■ Disconnect", state=tk.NORMAL))
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
                    self.root.after(0, lambda: self.connect_button.config(text="▶ Connect", state=tk.NORMAL))
                    self.running = False
            else:
                self.log_message("Failed to connect to server", "error")
                self.update_status("connection", "Disconnected", "red")
                self.root.after(0, lambda: self.connect_button.config(text="▶ Connect", state=tk.NORMAL))
                self.running = False
                
        except Exception as e:
            self.log_message(f"Client error: {e}", "error")
            self.update_status("connection", "Disconnected", "red")
            self.update_status("streaming", "Not Streaming", "gray")
            self.root.after(0, lambda: self.connect_button.config(text="▶ Connect", state=tk.NORMAL))
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
        self.connect_button.config(text="▶ Connect", state=tk.NORMAL)
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
