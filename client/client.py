#!/usr/bin/env python3
"""
YaP Mic Pass Ult - Client
Captures microphone audio and streams it to the server.
"""

import socket
import pyaudio
import sys
import argparse
import signal
import time
import struct

# Try to import numpy for faster volume processing, fallback to struct if not available
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

class MicStreamClient:
    def __init__(self, server_host='localhost', server_port=5000, 
                 sample_rate=44100, channels=1, chunk_size=128, 
                 device_index=None, volume=1.0, quality='balanced'):
        self.server_host = server_host
        self.server_port = server_port
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.device_index = device_index
        self.volume = max(0.0, min(2.0, volume))  # Clamp between 0.0 and 2.0
        self.quality = quality  # 'low_latency', 'balanced', 'high_quality'
        self.running = False
        self.socket = None
        self.audio = None
        self.stream = None
        
        # Apply quality presets
        self._apply_quality_preset()
    
    def set_volume(self, volume):
        """Set volume/gain (0.0 to 2.0)."""
        self.volume = max(0.0, min(2.0, volume))
    
    def _apply_quality_preset(self):
        """Apply quality preset settings for latency optimization."""
        if self.quality == 'low_latency':
            # Ultra low latency: smaller chunks, lower sample rate
            if self.chunk_size > 128:
                self.chunk_size = 128
            if self.sample_rate > 22050:
                self.sample_rate = 22050
        elif self.quality == 'high_quality':
            # High quality: larger chunks, higher sample rate
            if self.chunk_size < 512:
                self.chunk_size = 512
            if self.sample_rate < 44100:
                self.sample_rate = 44100
        # 'balanced' uses user-provided settings
    
    def set_quality(self, quality):
        """Set quality preset: 'low_latency', 'balanced', or 'high_quality'."""
        if quality in ['low_latency', 'balanced', 'high_quality']:
            self.quality = quality
            self._apply_quality_preset()
    
    def set_sample_rate(self, sample_rate):
        """Dynamically change sample rate (requires reconnection)."""
        self.sample_rate = sample_rate
        
    def list_audio_devices(self):
        """List all available audio input devices."""
        audio = pyaudio.PyAudio()
        devices = []
        print("\nAvailable audio input devices:")
        print("-" * 70)
        print(f"{'Index':<8} {'Name':<40} {'Channels':<10} {'Sample Rate':<15}")
        print("-" * 70)
        
        for i in range(audio.get_device_count()):
            info = audio.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                devices.append({
                    'index': i,
                    'name': info['name'],
                    'channels': info['maxInputChannels'],
                    'sample_rate': int(info['defaultSampleRate'])
                })
                print(f"{i:<8} {info['name']:<40} {info['maxInputChannels']:<10} {int(info['defaultSampleRate']):<15}")
        
        audio.terminate()
        print("-" * 70)
        return devices
    
    def connect_to_server(self):
        """Establish connection to the server."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Disable Nagle's algorithm for low latency (TCP_NODELAY)
            self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            # Set socket buffer sizes for lower latency
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 8192)
            # Set connection timeout
            self.socket.settimeout(10.0)
            self.socket.connect((self.server_host, self.server_port))
            # Remove timeout after connection (will be set during streaming)
            self.socket.settimeout(None)
            print(f"Connected to server at {self.server_host}:{self.server_port}")
            return True
        except socket.timeout:
            print(f"Error: Connection timeout to server at {self.server_host}:{self.server_port}")
            print("Make sure the server is running and accessible.")
            return False
        except ConnectionRefusedError:
            print(f"Error: Could not connect to server at {self.server_host}:{self.server_port}")
            print("Make sure the server is running.")
            return False
        except socket.gaierror as e:
            print(f"Error: Could not resolve hostname '{self.server_host}': {e}")
            return False
        except Exception as e:
            print(f"Error connecting to server: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def send_audio_config(self):
        """Send audio configuration to server."""
        try:
            if not self.socket:
                print("Error: Socket not connected")
                return False
            
            config = {
                'sample_rate': self.sample_rate,
                'channels': self.channels,
                'chunk_size': self.chunk_size,
                'quality': self.quality
            }
            config_str = f"CONFIG:{config['sample_rate']}:{config['channels']}:{config['chunk_size']}:{config['quality']}\n"
            
            # Send config with timeout
            self.socket.settimeout(5.0)
            try:
                bytes_sent = self.socket.sendall(config_str.encode('utf-8'))
                print(f"Audio configuration sent: {config_str.strip()}")
                # Remove timeout after sending (use blocking mode for streaming)
                self.socket.settimeout(None)
                # Ensure socket is ready for streaming
                self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                print("Socket configured for streaming")
                return True
            except socket.timeout:
                print("Error: Timeout sending audio configuration")
                return False
            except socket.error as e:
                print(f"Error: Socket error sending config: {e}")
                return False
        except Exception as e:
            print(f"Error sending config: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def stream_audio(self):
        """Capture and stream microphone audio to server."""
        self.audio = pyaudio.PyAudio()
        
        try:
            # Open audio stream with minimal latency settings
            # Use smallest possible buffer for lowest latency
            frames_per_buffer = min(self.chunk_size, 64)  # Cap at 64 for ultra-low latency
            
            print(f"Opening audio stream...")
            print(f"  Device index: {self.device_index}")
            print(f"  Sample rate: {self.sample_rate} Hz")
            print(f"  Channels: {self.channels}")
            print(f"  Chunk size: {self.chunk_size} frames")
            print(f"  Frames per buffer: {frames_per_buffer}")
            
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=frames_per_buffer,
                stream_callback=None,
                start=False
            )
            
            # Start stream immediately to minimize initial latency
            self.stream.start_stream()
            print(f"Audio stream started successfully")
            
            device_info = self.audio.get_device_info_by_index(
                self.device_index if self.device_index is not None 
                else self.audio.get_default_input_device_info()['index']
            )
            print(f"Streaming from: {device_info['name']}")
            print(f"Sample rate: {self.sample_rate} Hz, Channels: {self.channels}")
            print("Streaming audio... (Press Ctrl+C to stop)\n")
            
            self.running = True
            
            # Buffer for smooth audio transmission
            frame_count = 0
            expected_size = self.chunk_size * self.channels * 2  # Bytes per chunk
            
            print(f"Expected audio frame size: {expected_size} bytes")
            
            while self.running:
                try:
                    # Read audio data (must be complete frame)
                    data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                    
                    if not data:
                        print("Warning: No audio data read from stream")
                        continue
                    
                    # Validate audio data size
                    if len(data) != expected_size:
                        print(f"Warning: Audio frame size mismatch. Expected {expected_size}, got {len(data)}")
                        # If partial read, pad with silence to maintain audio continuity
                        if len(data) < expected_size:
                            padding = b'\x00' * (expected_size - len(data))
                            data = data + padding
                        # If oversize, truncate (shouldn't happen)
                        elif len(data) > expected_size:
                            data = data[:expected_size]
                    
                    # Check if audio data contains actual sound (not just silence)
                    # Calculate RMS (Root Mean Square) to detect audio level
                    if frame_count == 0 or frame_count % 500 == 0:  # Check every 500 frames
                        if HAS_NUMPY:
                            audio_array = np.frombuffer(data, dtype=np.int16)
                            rms = np.sqrt(np.mean(audio_array.astype(np.float32)**2))
                            max_level = np.max(np.abs(audio_array))
                            # Normalize RMS to 0-100 scale (32767 is max for int16)
                            rms_percent = (rms / 32767.0) * 100
                            if frame_count == 0:
                                print(f"Audio level monitoring enabled (RMS: {rms_percent:.1f}%, Peak: {max_level})")
                            elif rms_percent < 0.1:
                                print(f"Warning: Very low audio level detected (RMS: {rms_percent:.1f}%). Microphone may be muted or not capturing audio.")
                        else:
                            # Fallback: check if all samples are zero or very close to zero
                            samples = struct.unpack(f'<{len(data)//2}h', data)
                            max_sample = max(abs(s) for s in samples)
                            if max_sample < 100:  # Very quiet threshold
                                if frame_count == 0:
                                    print(f"Audio level: Peak sample = {max_sample}")
                                else:
                                    print(f"Warning: Very low audio level (peak: {max_sample}). Microphone may be muted.")
                    
                    # Apply volume/gain if not 1.0 (inline for speed)
                    if self.volume != 1.0:
                        if HAS_NUMPY:
                            # Fast path using numpy (vectorized, in-place when possible)
                            audio_array = np.frombuffer(data, dtype=np.int16)
                            audio_array = (audio_array.astype(np.float32) * self.volume).astype(np.int16)
                            np.clip(audio_array, -32768, 32767, out=audio_array)
                            data = audio_array.tobytes()
                        else:
                            # Fallback using struct (slower but no dependencies)
                            samples = struct.unpack(f'<{len(data)//2}h', data)
                            samples = [int(max(-32768, min(32767, s * self.volume))) for s in samples]
                            data = struct.pack(f'<{len(samples)}h', *samples)
                    
                    # Send to server - ensure complete transmission
                    try:
                        # Use sendall to ensure all data is sent (prevents choppy audio)
                        self.socket.sendall(data)
                        frame_count += 1
                        
                        # Debug output every 100 frames
                        if frame_count % 100 == 0:
                            print(f"Sent {frame_count} audio frames...")
                            
                    except socket.error as e:
                        # If send fails, break to handle disconnection
                        print(f"\nConnection lost while sending: {e}")
                        import traceback
                        traceback.print_exc()
                        break
                    
                except OSError as e:
                    # Audio device error
                    print(f"\nAudio device error: {e}")
                    import traceback
                    traceback.print_exc()
                    break
                except socket.error as e:
                    print(f"\nConnection lost: {e}")
                    import traceback
                    traceback.print_exc()
                    break
                except Exception as e:
                    print(f"\nError streaming audio: {e}")
                    import traceback
                    traceback.print_exc()
                    break
                    
        except OSError as e:
            print(f"Error opening audio device: {e}")
            if "No default input device" in str(e):
                print("Please specify an audio input device using --list and --device options.")
            import traceback
            traceback.print_exc()
            return False
        except Exception as e:
            print(f"Error initializing audio stream: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            self.cleanup()
        
        return True
    
    def cleanup(self):
        """Clean up resources."""
        self.running = False
        
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except:
                pass
        
        if self.audio:
            try:
                self.audio.terminate()
            except:
                pass
        
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
    
    def run(self):
        """Run the client."""
        if not self.connect_to_server():
            return False
        
        if not self.send_audio_config():
            return False
        
        # Set up signal handler
        def signal_handler(sig, frame):
            print("\nStopping client...")
            self.cleanup()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        return self.stream_audio()

def main():
    parser = argparse.ArgumentParser(
        description="YaP Mic Pass Ult - Client (Stream microphone to server)"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Server hostname or IP (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Server port (default: 5000)"
    )
    parser.add_argument(
        "--device",
        type=int,
        default=None,
        help="Audio input device index (use --list to see available devices)"
    )
    parser.add_argument(
        "--rate",
        type=int,
        default=44100,
        help="Sample rate in Hz (default: 44100)"
    )
    parser.add_argument(
        "--channels",
        type=int,
        default=1,
        choices=[1, 2],
        help="Number of audio channels (default: 1)"
    )
    parser.add_argument(
        "--chunk",
        type=int,
        default=128,
        help="Chunk size in frames (default: 128, lower = less latency but more CPU)"
    )
    parser.add_argument(
        "--volume",
        type=float,
        default=1.0,
        help="Volume/gain multiplier (0.0-2.0, default: 1.0)"
    )
    parser.add_argument(
        "--quality",
        type=str,
        choices=['low_latency', 'balanced', 'high_quality'],
        default='balanced',
        help="Quality preset: low_latency (fastest), balanced (default), high_quality (best audio)"
    )
    parser.add_argument(
        "--rate",
        type=int,
        default=44100,
        help="Sample rate in Hz (default: 44100, lower = less latency)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available audio input devices and exit"
    )
    
    args = parser.parse_args()
    
    client = MicStreamClient(
        server_host=args.host,
        server_port=args.port,
        sample_rate=args.rate,
        channels=args.channels,
        chunk_size=args.chunk,
        device_index=args.device,
        volume=args.volume,
        quality=args.quality
    )
    
    if args.list:
        client.list_audio_devices()
        return
    
    success = client.run()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
