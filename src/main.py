import sys
from netutil import NetworkUtility
from controller import run_flask_server

if __name__ == '__main__':
    print("="*40)
    print("Start Aether P2P Tor Node")
    print("="*40)

    net_util = NetworkUtility(tor_control_port=9051, tor_socks_port=9050)

    try:
        run_flask_server(port=5000, net_util=net_util)
    except KeyboardInterrupt:
        print("\n[!] Stopping P2P Client")
    finally:
        net_util.stop()
        sys.exit(0)