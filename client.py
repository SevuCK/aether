#!/usr/bin/env python3
"""
P2P Chat Client over Tor Hidden Services
- Creates hidden service endpoint for receiving messages
- Connects to peer hidden services via Tor SOCKS proxy
- Full-duplex message exchange
"""

import socket
import threading
import sys
from stem.control import Controller
from stem.util import term
import socks
import random


class TorP2PClient:
    def __init__(self, control_port=9051, socks_port=9050, local_port=None):
        """
        Initialize Tor P2P Chat Client

        Args:
            control_port: Tor control port (default 9051)
            socks_port: Tor SOCKS proxy port (default 9050)
            local_port: Local listening port for hidden service
        """
        self.control_port = control_port
        self.socks_port = socks_port
        # if no port provided, pick a random high port but still allow explicit override
        self.local_port = local_port or random.randint(49152, 65535)
        self.controller = None
        self.onion_address = None
        self.server_socket = None
        self.running = True

    def connect_to_tor(self):
        """Authenticate with Tor control port"""
        try:
            self.controller = Controller.from_port(port=self.control_port)
            self.controller.authenticate()
            print(term.format("Connected to Tor daemon", term.Color.GREEN))
        except Exception as e:
            print(term.format(f"[ERROR]Failed to connect to Tor: {e}", term.Color.RED))
            sys.exit(1)

    def create_hidden_service(self):
        """Create ephemeral hidden service and retrieve onion address"""
        try:
            mapping = {80: self.local_port}
            response = self.controller.create_ephemeral_hidden_service(
                mapping,
                await_publication=True
            )
            self.onion_address = response.service_id
            print(term.format(
                f"[INFO] Hidden Service Created: {self.onion_address}.onion -> 127.0.0.1:{self.local_port}",
                term.Color.GREEN
            ))
            return self.onion_address
        except Exception as e:
            print(term.format(f"[ERROR]Failed to create hidden service: {e}", term.Color.RED))
            sys.exit(1)

    def start_server(self):
        """Start listening for incoming connections on hidden service"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('127.0.0.1', self.local_port))
            self.server_socket.listen(5)
            print(term.format(
                f"Listening on 127.0.0.1:{self.local_port}",
                term.Color.GREEN
            ))

            # Start accepting connections in background thread
            threading.Thread(target=self._accept_connections, daemon=True).start()
        except Exception as e:
            print(term.format(f"[ERROR]Failed to start server: {e}", term.Color.RED))
            sys.exit(1)

    def _accept_connections(self):
        """Accept incoming peer connections"""
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                threading.Thread(
                    target=self._handle_peer_connection,
                    args=(conn, addr),
                    daemon=True
                ).start()
            except OSError:
                break
            except Exception as e:
                print(f"[!] Connection error: {e}")

    def _handle_peer_connection(self, conn, addr):
        """Handle incoming message from peer"""
        try:
            data = conn.recv(4096).decode('utf-8')
            if data:
                print(f"\n[Peer]: {data}")
                print("You: ", end="", flush=True)
        except Exception as e:
            print(f"[!] Error receiving message: {e}")
        finally:
            conn.close()

    def send_message(self, peer_onion_address, message):
        """
        Send message to peer through Tor SOCKS proxy

        Args:
            peer_onion_address: Peer's .onion address (with or without .onion suffix)
            message: Message to send
        """
        # normalize onion hostname
        peer_addr = peer_onion_address.strip()
        if peer_addr.endswith(".onion"):
            peer_addr = peer_addr[:-6]  # remove suffix
        hostname = f"{peer_addr}.onion"

        try:
            # Create SOCKS proxy socket
            sock = socks.socksocket()
            sock.set_proxy(socks.SOCKS5, "127.0.0.1", self.socks_port)
            sock.settimeout(20)

            # Connect to peer's hidden service on virtual port 80
            sock.connect((hostname, 80))

            # Send message
            sock.sendall(message.encode('utf-8'))
            print(term.format("Message sent", term.Color.GREEN))
            sock.close()
        except socket.timeout:
            print(term.format("[ALERT] Connection timeout. Peer may be offline.", term.Color.RED))
        except Exception as e:
            print(term.format(f"[ERROR]Failed to send message: {e}", term.Color.RED))

    def run(self):
        """Main chat loop"""
        self.connect_to_tor()
        onion = self.create_hidden_service()
        self.start_server()

        print("\n" + "=" * 60)
        print(term.format("P2P Chat Ready", term.Color.GREEN))
        print("=" * 60)
        print(f"Your address: {term.format(f'{onion}.onion', term.Color.CYAN)}")
        print(f"Share this with peers to receive messages")
        print("\nCommands:")
        print("  /send <peer_onion> <message> — Send message to peer")
        print("  /quit — Exit chat")
        print("=" * 60 + "\n")

        try:
            while self.running:
                user_input = input("You: ").strip()

                if user_input.startswith('/send'):
                    parts = user_input.split(None, 2)
                    if len(parts) < 3:
                        print("[INFO] Usage: /send <peer_onion> <message>")
                        continue
                    peer_addr = parts[1]
                    msg = parts[2]
                    self.send_message(peer_addr, msg)

                elif user_input == '/quit':
                    self.running = False
                    break

                elif user_input:
                    print("[ERROR] Unknown command. Use /send or /quit")

        except KeyboardInterrupt:
            self.running = False
            print("\nChat closed")
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        try:
            if self.server_socket:
                self.server_socket.close()
            if self.controller:
                self.controller.close()
        except Exception as e:
            print(f"[ERROR] Cleanup error: {e}")


if __name__ == '__main__':
    # optional CLI arg: local_port
    if len(sys.argv) > 1:
        lp = int(sys.argv[1])
    else:
        lp = None

    client = TorP2PClient(local_port=lp)
    client.run()
