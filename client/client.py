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
                 sample_rate=44100, channels=1, chunk_size=256, 
                 device_index=None, volume=1.0):
        self.server_host = server_host
        self.server_port = server_port
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.device_index = device_index
        self.volume = max(0.0, min(2.0, volume))  # Clamp between 0.0 and 2.0
        self.running = False
        self.socket = None
        self.audio = None
        self.stream = None
    
    def set_volume(self, volume):
        """Set volume/gain (0.0 to 2.0)."""
        self.volume = max(0.0, min(2.0, volume))
        
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
            self.socket.connect((self.server_host, self.server_port))
            print(f"Connected to server at {self.server_host}:{self.server_port}")
            return True
        except ConnectionRefusedError:
            print(f"Error: Could not connect to server at {self.server_host}:{self.server_port}")
            print("Make sure the server is running.")
            return False
        except Exception as e:
            print(f"Error connecting to server: {e}")
            return False
    
    def send_audio_config(self):
        """Send audio configuration to server."""
        config = {
            'sample_rate': self.sample_rate,
            'channels': self.channels,
            'chunk_size': self.chunk_size
        }
        config_str = f"CONFIG:{config['sample_rate']}:{config['channels']}:{config['chunk_size']}\n"
        try:
            self.socket.sendall(config_str.encode())
            return True
        except Exception as e:
            print(f"Error sending config: {e}")
            return False
    
    def stream_audio(self):
        """Capture and stream microphone audio to server."""
        self.audio = pyaudio.PyAudio()
        
        try:
            # Open audio stream with minimal latency settings
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=self.chunk_size,
                stream_callback=None,
                start=False
            )
            
            # Start stream immediately to minimize initial latency
            self.stream.start_stream()
            
            device_info = self.audio.get_device_info_by_index(
                self.device_index if self.device_index is not None 
                else self.audio.get_default_input_device_info()['index']
            )
            print(f"Streaming from: {device_info['name']}")
            print(f"Sample rate: {self.sample_rate} Hz, Channels: {self.channels}")
            print("Streaming audio... (Press Ctrl+C to stop)\n")
            
            self.running = True
            
            while self.running:
                try:
                    # Read audio data
                    data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                    
                    # Apply volume/gain if not 1.0 (inline for speed)
                    if self.volume != 1.0:
                        if HAS_NUMPY:
                            # Fast path using numpy (vectorized)
                            audio_array = np.frombuffer(data, dtype=np.int16).astype(np.float32)
                            audio_array = audio_array * self.volume
                            audio_array = np.clip(audio_array, -32768.0, 32767.0).astype(np.int16)
                            data = audio_array.tobytes()
                        else:
                            # Fallback using struct (slower but no dependencies)
                            samples = struct.unpack(f'<{len(data)//2}h', data)
                            samples = [int(max(-32768, min(32767, s * self.volume))) for s in samples]
                            data = struct.pack(f'<{len(samples)}h', *samples)
                    
                    # Send to server immediately (no buffering)
                    try:
                        self.socket.sendall(data)
                    except socket.error:
                        # If send fails, break to handle disconnection
                        break
                    
                except socket.error as e:
                    print(f"\nConnection lost: {e}")
                    break
                except Exception as e:
                    print(f"\nError streaming audio: {e}")
                    break
                    
        except OSError as e:
            print(f"Error opening audio device: {e}")
            if "No default input device" in str(e):
                print("Please specify an audio input device using --list and --device options.")
            return False
        except Exception as e:
            print(f"Error initializing audio stream: {e}")
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
        default=256,
        help="Chunk size in frames (default: 256, lower = less latency but more CPU)"
    )
    parser.add_argument(
        "--volume",
        type=float,
        default=1.0,
        help="Volume/gain multiplier (0.0-2.0, default: 1.0)"
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
        volume=args.volume
    )
    
    if args.list:
        client.list_audio_devices()
        return
    
    success = client.run()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
