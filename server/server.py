#!/usr/bin/env python3
"""
YaP Mic Pass Ult - Server
Receives audio stream from client and outputs it to a virtual audio input device.
"""

import socket
import sys
import argparse
import signal
import platform
import subprocess
import threading
import queue
import os
import tempfile
import time

class MicStreamServer:
    def __init__(self, port=5000, virtual_device_name="YaP-Mic-Pass-Ult", 
                 use_pulseaudio=True):
        self.port = port
        self.virtual_device_name = virtual_device_name
        self.use_pulseaudio = use_pulseaudio and platform.system() == "Linux"
        self.running = False
        self.server_socket = None
        self.client_socket = None
        # Balanced queue for smooth audio (prevent choppiness)
        self.audio_queue = queue.Queue(maxsize=5)
        self.sample_rate = 44100
        self.channels = 1
        self.chunk_size = 128
        self.quality = 'balanced'
        self.last_audio_data = None  # For interpolation if frame is lost
        self.pulseaudio_module_index = None
        self.pipe_path = None
        self.pipe_file = None
        self.virtual_source_name = None
        self.virtual_source_index = None
        self.device_volume = 1.0
        self.write_count = 0  # Counter for periodic flushing
        
    def setup_virtual_device_linux(self):
        """Set up virtual audio input device on Linux using PulseAudio pipe-source."""
        if not self.use_pulseaudio:
            return False
            
        try:
            # Check if PulseAudio is available
            subprocess.run(["pactl", "--version"], 
                         check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Warning: PulseAudio not found. Virtual device setup may fail.")
            return False
        
        try:
            # Check if our virtual source already exists
            result = subprocess.run(
                ["pactl", "list", "short", "sources"],
                capture_output=True,
                text=True
            )
            
            if self.virtual_device_name in result.stdout:
                print(f"Virtual audio source '{self.virtual_device_name}' already exists.")
                # Try to find and clean up existing module
                self.cleanup_existing_module()
            
            # Create a named pipe (FIFO) for audio data
            pipe_dir = tempfile.gettempdir()
            self.pipe_path = os.path.join(pipe_dir, f"{self.virtual_device_name}.pipe")
            
            # Remove pipe if it exists
            if os.path.exists(self.pipe_path):
                os.remove(self.pipe_path)
            
            # Create FIFO pipe
            os.mkfifo(self.pipe_path)
            print(f"Created named pipe: {self.pipe_path}")
            
            # Create pipe-source module with low latency settings
            # Format: s16le = signed 16-bit little-endian, which matches paInt16
            # We'll update the sample rate after receiving config from client
            cmd = [
                "pactl", "load-module", "module-pipe-source",
                f"source_name={self.virtual_device_name}",
                f"file={self.pipe_path}",
                "format=s16le",
                "rate=44100",  # Will be updated after client config
                "channels=1",  # Will be updated after client config
                "source_properties=device.description=\"" + self.virtual_device_name + "\""
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Get module index for cleanup
            module_index = result.stdout.strip()
            if module_index:
                self.pulseaudio_module_index = module_index
                print(f"Created virtual audio source: {self.virtual_device_name}")
                print(f"Module index: {module_index}")
                
                # Wait a moment for the source to be fully created
                time.sleep(0.5)
                
                # Find and configure the source (unmute and set volume)
                self._configure_virtual_source()
                
                print(f"\nVirtual input device is now available!")
                print(f"Select '{self.virtual_device_name}' as your microphone input in applications.")
                return True
            else:
                print("Warning: Could not get PulseAudio module index")
                return False
                
        except subprocess.CalledProcessError as e:
            print(f"Error creating virtual audio source: {e}", file=sys.stderr)
            if e.stderr:
                print(f"Error details: {e.stderr.decode()}", file=sys.stderr)
            # Clean up pipe if module loading failed
            if self.pipe_path and os.path.exists(self.pipe_path):
                try:
                    os.remove(self.pipe_path)
                except:
                    pass
            return False
        except Exception as e:
            print(f"Unexpected error setting up virtual device: {e}", file=sys.stderr)
            if self.pipe_path and os.path.exists(self.pipe_path):
                try:
                    os.remove(self.pipe_path)
                except:
                    pass
            return False
    
    def cleanup_existing_module(self):
        """Clean up existing PulseAudio module for this virtual device."""
        try:
            mod_result = subprocess.run(
                ["pactl", "list", "short", "modules"],
                capture_output=True,
                text=True
            )
            for line in mod_result.stdout.strip().split('\n'):
                if self.virtual_device_name in line and "pipe-source" in line:
                    parts = line.split('\t')
                    if parts:
                        old_module_index = parts[0]
                        subprocess.run(
                            ["pactl", "unload-module", old_module_index],
                            capture_output=True
                        )
                        print(f"Unloaded existing module {old_module_index}")
        except Exception as e:
            pass  # Ignore errors during cleanup
    
    def _get_source_name(self):
        """Get the full PulseAudio source name for the virtual device."""
        try:
            result = subprocess.run(
                ["pactl", "list", "short", "sources"],
                capture_output=True,
                text=True,
                check=True
            )
            
            for line in result.stdout.strip().split('\n'):
                if self.virtual_device_name in line:
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        # Store source info for later use
                        self.virtual_source_index = parts[0]
                        self.virtual_source_name = parts[1]
                        return parts[1]
            return None
        except Exception as e:
            print(f"Error getting source name: {e}")
            return None
    
    def set_virtual_device_volume(self, volume):
        """Set volume for the virtual device (0.0 to 2.0)."""
        self.device_volume = max(0.0, min(2.0, volume))
        # PulseAudio volume is in 0-65536 range (where 65536 = 100%)
        pulse_volume = int(self.device_volume * 65536)
        
        source_name = self.virtual_source_name or self.virtual_device_name
        source_index = self.virtual_source_index
        
        success = False
        
        # Try with source name
        if source_name:
            try:
                subprocess.run(
                    ["pactl", "set-source-volume", source_name, str(pulse_volume)],
                    capture_output=True,
                    check=True
                )
                success = True
            except subprocess.CalledProcessError:
                pass
        
        # Try with source index as fallback
        if not success and source_index:
            try:
                subprocess.run(
                    ["pactl", "set-source-volume", source_index, str(pulse_volume)],
                    capture_output=True,
                    check=True
                )
                success = True
            except subprocess.CalledProcessError:
                pass
        
        if not success:
            print(f"Warning: Could not set virtual device volume to {int(self.device_volume * 100)}%")
    
    def _configure_virtual_source(self):
        """Configure the virtual source: unmute and set volume."""
        # Get both source name and index for maximum compatibility
        source_name = self._get_source_name()
        source_index = None
        
        # Get source index
        try:
            result = subprocess.run(
                ["pactl", "list", "short", "sources"],
                capture_output=True,
                text=True,
                check=True
            )
            for line in result.stdout.strip().split('\n'):
                if self.virtual_device_name in line:
                    parts = line.split('\t')
                    if parts:
                        source_index = parts[0]
                        if not source_name and len(parts) >= 2:
                            source_name = parts[1]
                        break
        except Exception as e:
            print(f"Error getting source info: {e}")
        
        if not source_name:
            source_name = self.virtual_device_name
            print(f"Warning: Could not find source name, using: {source_name}")
        
        # Try to configure using both name and index
        success = False
        
        # Try with source name first
        if source_name:
            try:
                # Unmute the source (0 = unmute, 1 = mute)
                subprocess.run(
                    ["pactl", "set-source-mute", source_name, "0"],
                    capture_output=True,
                    check=True
                )
                # Set volume using device_volume setting (65536 is 100% in PulseAudio's internal units)
                pulse_volume = int(self.device_volume * 65536)
                subprocess.run(
                    ["pactl", "set-source-volume", source_name, str(pulse_volume)],
                    capture_output=True,
                    check=True
                )
                print(f"Configured virtual source (unmuted, volume set to {int(self.device_volume * 100)}%): {source_name}")
                success = True
            except subprocess.CalledProcessError as e:
                print(f"Warning: Could not configure using source name: {e}")
        
        # Try with source index as fallback
        if not success and source_index:
            try:
                subprocess.run(
                    ["pactl", "set-source-mute", source_index, "0"],
                    capture_output=True,
                    check=True
                )
                pulse_volume = int(self.device_volume * 65536)
                subprocess.run(
                    ["pactl", "set-source-volume", source_index, str(pulse_volume)],
                    capture_output=True,
                    check=True
                )
                print(f"Configured virtual source using index: {source_index} (volume: {int(self.device_volume * 100)}%)")
                success = True
            except subprocess.CalledProcessError as e:
                print(f"Warning: Could not configure using source index: {e}")
        
        # Verify the configuration
        time.sleep(0.2)  # Small delay for PulseAudio to process
        try:
            verify_result = subprocess.run(
                ["pactl", "list", "sources", "short"],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Check if muted and try again if needed
            for line in verify_result.stdout.strip().split('\n'):
                if (source_name and source_name in line) or \
                   (self.virtual_device_name in line) or \
                   (source_index and line.startswith(source_index + '\t')):
                    if '[MUTED]' in line or 'muted: yes' in line.lower():
                        print(f"Warning: Source is still muted, attempting to unmute again...")
                        # Try multiple times with different methods
                        for attempt in range(3):
                            time.sleep(0.2)
                            try:
                                if source_index:
                                    subprocess.run(
                                        ["pactl", "set-source-mute", source_index, "0"],
                                        capture_output=True,
                                        check=True
                                    )
                                if source_name:
                                    subprocess.run(
                                        ["pactl", "set-source-mute", source_name, "0"],
                                        capture_output=True,
                                        check=True
                                    )
                            except:
                                pass
                    break
        except Exception as e:
            print(f"Warning: Could not verify source configuration: {e}")
        
        if not success:
            print(f"Warning: Could not fully configure virtual source. You may need to unmute it manually:")
            print(f"  pactl set-source-mute {source_name if source_name else source_index} 0")
    
    def update_pipe_source_config(self):
        """Update the pipe-source configuration with actual audio parameters."""
        # We can't easily update a pipe-source after creation, but we can recreate it
        # For now, we'll just ensure the client sends data in the format we specified
        # The pipe-source expects s16le format which we'll write
        pass
    
    def start_server(self):
        """Start the server socket."""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Disable Nagle's algorithm for low latency (TCP_NODELAY)
            self.server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            # Set socket buffer sizes for lower latency
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8192)
            self.server_socket.bind(('0.0.0.0', self.port))
            self.server_socket.listen(1)
            print(f"Server listening on port {self.port}")
            print("Waiting for client connection...")
            return True
        except OSError as e:
            print(f"Error starting server: {e}", file=sys.stderr)
            if "Address already in use" in str(e):
                print(f"Port {self.port} is already in use. Try a different port with --port option.")
            return False
        except Exception as e:
            print(f"Unexpected error starting server: {e}", file=sys.stderr)
            return False
    
    def accept_client(self):
        """Accept a client connection."""
        try:
            # Set timeout for accept so we can check if server should still be running
            self.server_socket.settimeout(1.0)
            self.client_socket, client_address = self.server_socket.accept()
            # Configure client socket for low latency
            self.client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8192)
            # Keep socket blocking for reliable data reception
            self.client_socket.setblocking(True)
            print(f"Client connected from {client_address[0]}:{client_address[1]}")
            return True
        except socket.timeout:
            # Timeout is expected when checking if server should continue
            return False
        except Exception as e:
            print(f"Error accepting client: {e}")
            return False
    
    def receive_audio_config(self):
        """Receive audio configuration from client."""
        try:
            # Set timeout for config reception (5 seconds should be enough)
            self.client_socket.settimeout(5.0)
            
            # Receive config line - read until we get a newline
            buffer = b""
            max_length = 256  # Reasonable max length for config line
            while b"\n" not in buffer and len(buffer) < max_length:
                try:
                    data = self.client_socket.recv(1)
                    if not data:
                        print("Error: Connection closed while receiving config")
                        return False
                    buffer += data
                except socket.timeout:
                    print("Error: Timeout waiting for audio configuration")
                    return False
            
            if len(buffer) >= max_length:
                print("Error: Config line too long")
                return False
            
            if not buffer:
                print("Error: Empty config received")
                return False
            
            # Decode and parse config
            try:
                config_line = buffer.decode('utf-8').strip()
            except UnicodeDecodeError as e:
                print(f"Error: Failed to decode config line: {e}")
                return False
            
            if not config_line.startswith("CONFIG:"):
                print(f"Error: Invalid config format. Received: {config_line[:50]}")
                return False
            
            parts = config_line.split(":")
            if len(parts) < 4:
                print(f"Error: Config has insufficient parts. Expected 4+, got {len(parts)}")
                return False
            
            # Parse config values
            try:
                self.sample_rate = int(parts[1])
                self.channels = int(parts[2])
                self.chunk_size = int(parts[3])
                self.quality = parts[4] if len(parts) >= 5 else 'balanced'
                
                # Validate values
                if self.sample_rate < 8000 or self.sample_rate > 96000:
                    print(f"Error: Invalid sample rate: {self.sample_rate}")
                    return False
                if self.channels < 1 or self.channels > 2:
                    print(f"Error: Invalid channel count: {self.channels}")
                    return False
                if self.chunk_size < 64 or self.chunk_size > 4096:
                    print(f"Error: Invalid chunk size: {self.chunk_size}")
                    return False
                
                print(f"Audio configuration received:")
                print(f"  Sample rate: {self.sample_rate} Hz")
                print(f"  Channels: {self.channels}")
                print(f"  Chunk size: {self.chunk_size}")
                print(f"  Quality: {self.quality}")
                
                # Adjust queue size based on quality (but keep minimum buffer for smooth playback)
                if self.quality == 'low_latency':
                    # Small queue but not too small to prevent choppiness
                    self.audio_queue = queue.Queue(maxsize=3)
                elif self.quality == 'high_quality':
                    # Larger queue for high quality
                    self.audio_queue = queue.Queue(maxsize=8)
                else:
                    # Balanced - enough buffer for smooth audio
                    self.audio_queue = queue.Queue(maxsize=5)
                
                # Reset timeout for streaming (will be set in stream_audio_from_client)
                self.client_socket.settimeout(None)
                return True
                
            except ValueError as e:
                print(f"Error: Failed to parse config values: {e}")
                return False
                
        except socket.timeout:
            print("Error: Timeout receiving audio configuration")
            return False
        except socket.error as e:
            print(f"Error: Socket error receiving config: {e}")
            return False
        except Exception as e:
            print(f"Error receiving config: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def audio_writer_thread(self):
        """Thread that writes audio from queue to the named pipe."""
        if not self.pipe_path:
            print("Error: No pipe path available for writing audio")
            return
        
        try:
            # Open the pipe for writing (this will block until something reads from it)
            print(f"Opening pipe for writing: {self.pipe_path}")
            print("Waiting for application to connect to virtual device...")
            print("Note: The pipe will block until an application selects this virtual device as input.")
            
            # Open pipe with minimal buffering (small buffer for smooth audio)
            # buffering=0 causes issues, use small buffer instead
            try:
                self.pipe_file = open(self.pipe_path, 'wb', buffering=4096)
                print("Pipe opened successfully. Streaming audio...")
            except IOError as e:
                print(f"Error: Could not open pipe for writing: {e}")
                print("This might happen if the pipe doesn't exist or there's a permission issue.")
                return
            except Exception as e:
                print(f"Error opening pipe: {e}")
                import traceback
                traceback.print_exc()
                return
            
            while self.running or not self.audio_queue.empty():
                try:
                    # Get audio data from queue (balanced timeout for smooth audio)
                    timeout = 0.01 if self.quality == 'low_latency' else 0.02
                    try:
                        audio_data = self.audio_queue.get(timeout=timeout)
                        self.last_audio_data = audio_data  # Store last frame
                    except queue.Empty:
                        # If queue is empty, repeat last frame to prevent audio dropouts
                        if self.last_audio_data:
                            audio_data = self.last_audio_data
                        else:
                            continue
                    
                    # Write to pipe - ensure continuous audio stream
                    try:
                        # Write complete frame
                        bytes_written = self.pipe_file.write(audio_data)
                        
                        # Ensure all data is written
                        if bytes_written < len(audio_data):
                            # Write remaining data
                            remaining = audio_data[bytes_written:]
                            while remaining:
                                written = self.pipe_file.write(remaining)
                                remaining = remaining[written:]
                        
                        # Flush periodically to ensure smooth playback
                        self.write_count += 1
                        flush_interval = 3 if self.quality == 'low_latency' else 5
                        if self.write_count % flush_interval == 0:
                            self.pipe_file.flush()
                    except BrokenPipeError:
                        print("\nPipe broken - application disconnected from virtual device.")
                        print("Reconnect an application to continue streaming.")
                        break
                    except Exception as e:
                        print(f"Error writing to pipe: {e}")
                        break
                    
                except queue.Empty:
                    # Check if we should continue waiting
                    if not self.running:
                        break
                    continue
                except Exception as e:
                    print(f"Error in audio writer thread: {e}")
                    break
                    
        except Exception as e:
            print(f"Error opening pipe: {e}")
            print("Make sure an application is connected to the virtual device.")
        finally:
            if self.pipe_file:
                try:
                    self.pipe_file.close()
                except:
                    pass
            # Recreate pipe if needed for next connection
            if self.pipe_path and os.path.exists(self.pipe_path):
                try:
                    os.remove(self.pipe_path)
                    os.mkfifo(self.pipe_path)
                except:
                    pass
    
    def stream_audio_from_client(self):
        """Receive and process audio stream from client."""
        writer_thread = threading.Thread(target=self.audio_writer_thread, daemon=True)
        writer_thread.start()
        
        print("\nStreaming audio... (Press Ctrl+C to stop)\n")
        
        try:
            while self.running:
                try:
                    # Calculate expected data size
                    data_size = self.chunk_size * self.channels * 2  # 2 bytes per sample (16-bit)
                    
                    # Receive audio data (ensure complete frames for smooth audio)
                    # Set reasonable timeout for reliable data reception
                    self.client_socket.settimeout(0.1)  # Longer timeout to ensure complete frames
                    
                    try:
                        # Receive complete frame
                        data = b''
                        remaining = data_size
                        
                        while remaining > 0:
                            chunk = self.client_socket.recv(remaining)
                            if not chunk:
                                if len(data) == 0:
                                    print("\nClient disconnected (no data received).")
                                    break
                                # Partial data - pad with silence to prevent audio glitches
                                padding = b'\x00' * remaining
                                data = data + padding
                                break
                            data += chunk
                            remaining -= len(chunk)
                        
                        if not data or len(data) == 0:
                            print("\nClient disconnected (empty data).")
                            break
                        
                        # Ensure we have exactly the expected size (critical for smooth audio)
                        if len(data) < data_size:
                            # Pad with silence if incomplete (prevents choppy audio)
                            padding = b'\x00' * (data_size - len(data))
                            data = data + padding
                        elif len(data) > data_size:
                            # This shouldn't happen, but handle it
                            data = data[:data_size]
                            
                    except socket.timeout:
                        # Timeout - continue but don't skip frames (maintains audio continuity)
                        # This is normal if client isn't sending fast enough
                        continue
                    except socket.error as e:
                        print(f"\nConnection error receiving audio: {e}")
                        import traceback
                        traceback.print_exc()
                        break
                    except Exception as e:
                        print(f"\nUnexpected error receiving audio: {e}")
                        import traceback
                        traceback.print_exc()
                        break
                    
                    # Validate audio data size before queuing
                    expected_size = self.chunk_size * self.channels * 2
                    if len(data) != expected_size:
                        # Pad or truncate to expected size for smooth playback
                        if len(data) < expected_size:
                            # Pad with silence (better than choppy audio)
                            padding = b'\x00' * (expected_size - len(data))
                            data = data + padding
                        elif len(data) > expected_size:
                            # Truncate if oversized
                            data = data[:expected_size]
                    
                    # Queue audio for writing to pipe (smooth buffering)
                    try:
                        self.audio_queue.put_nowait(data)
                    except queue.Full:
                        # Drop old frames strategically to prevent latency buildup
                        # But maintain minimum buffer for smooth playback
                        dropped = 0
                        # Keep at least 2 frames in queue for smooth audio
                        min_buffer = 2 if self.quality == 'low_latency' else 3
                        max_drop = max(1, self.audio_queue.qsize() - min_buffer)
                        
                        while dropped < max_drop:
                            try:
                                _ = self.audio_queue.get_nowait()
                                dropped += 1
                            except queue.Empty:
                                break
                        
                        # Add new frame
                        try:
                            self.audio_queue.put_nowait(data)
                        except queue.Full:
                            # If still full, drop one more and add (maintains continuity)
                            try:
                                _ = self.audio_queue.get_nowait()
                                self.audio_queue.put_nowait(data)
                            except queue.Empty:
                                pass
                    
                except socket.error as e:
                    print(f"\nConnection error: {e}")
                    break
                except Exception as e:
                    print(f"\nError receiving audio: {e}")
                    break
        
        except KeyboardInterrupt:
            print("\nStopping server...")
        finally:
            self.running = False
            # Wait for writer thread to finish
            writer_thread.join(timeout=3)
    
    def cleanup(self):
        """Clean up resources."""
        self.running = False
        
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        if self.pipe_file:
            try:
                self.pipe_file.close()
            except:
                pass
        
        # Clean up PulseAudio module
        if self.pulseaudio_module_index:
            try:
                subprocess.run(
                    ["pactl", "unload-module", self.pulseaudio_module_index],
                    capture_output=True
                )
                print(f"Unloaded PulseAudio module {self.pulseaudio_module_index}")
            except Exception as e:
                print(f"Warning: Could not unload PulseAudio module: {e}")
        
        # Clean up named pipe
        if self.pipe_path and os.path.exists(self.pipe_path):
            try:
                os.remove(self.pipe_path)
                print(f"Removed named pipe: {self.pipe_path}")
            except Exception as e:
                print(f"Warning: Could not remove pipe: {e}")
    
    def run(self):
        """Run the server."""
        # Set up virtual device
        if platform.system() == "Linux":
            if not self.setup_virtual_device_linux():
                print("Error: Virtual device setup failed.")
                print("Make sure PulseAudio is installed and running.")
                return False
        elif platform.system() == "Windows":
            print("Warning: Virtual device setup for Windows is not yet implemented.")
            print("Windows support would require VB-Audio Virtual Cable or similar.")
            return False
        else:
            print(f"Warning: Virtual device setup for {platform.system()} is not yet implemented.")
            return False
        
        if not self.start_server():
            return False
        
        # Set up signal handler
        def signal_handler(sig, frame):
            print("\nShutting down server...")
            self.cleanup()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        self.running = True
        
        try:
            while self.running:
                if self.accept_client():
                    if self.receive_audio_config():
                        self.stream_audio_from_client()
                    
                    # Close client connection
                    if self.client_socket:
                        self.client_socket.close()
                        self.client_socket = None
                    
                    # Reset pipe connection for next client
                    if self.pipe_file:
                        self.pipe_file.close()
                        self.pipe_file = None
                    
                    # Recreate pipe for next connection
                    if self.pipe_path and not os.path.exists(self.pipe_path):
                        try:
                            os.mkfifo(self.pipe_path)
                        except:
                            pass
                    
                    print("\nWaiting for next client connection...")
                else:
                    break
        except KeyboardInterrupt:
            self.cleanup()
        
        return True

def main():
    parser = argparse.ArgumentParser(
        description="YaP Mic Pass Ult - Server (Receive audio stream and output to virtual device)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Server port (default: 5000)"
    )
    parser.add_argument(
        "--name",
        default="YaP-Mic-Pass-Ult",
        help="Virtual device name (default: YaP-Mic-Pass-Ult)"
    )
    parser.add_argument(
        "--volume",
        type=float,
        default=1.0,
        help="Virtual device volume (0.0-2.0, default: 1.0)"
    )
    parser.add_argument(
        "--no-pulseaudio",
        action="store_true",
        help="Disable PulseAudio virtual device (Linux only)"
    )
    
    args = parser.parse_args()
    
    # Validate volume
    if args.volume < 0.0 or args.volume > 2.0:
        print("Error: Volume must be between 0.0 and 2.0")
        sys.exit(1)
    
    server = MicStreamServer(
        port=args.port,
        virtual_device_name=args.name,
        use_pulseaudio=not args.no_pulseaudio
    )
    
    # Set initial volume
    server.device_volume = args.volume
    
    success = server.run()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()