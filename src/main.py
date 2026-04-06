import time
import threading
import controller
from netutil import NetworkUtility
from controller import run_flask_server

def message_worker(net_util):
    print("[Worker] Message retry worker started.")
    while True:
        try:
            if controller.db_manager and controller.my_onion_address:
                pending = controller.db_manager.get_pending_messages()

                for msg in pending:
                    target_onion = controller.db_manager.get_onion_for_chat(msg['chat_id'])
                    if not target_onion:
                        continue

                    payload = {
                        "sender_onion": controller.my_onion_address,
                        "text": msg['content'],
                        "timestamp": msg['timestamp']
                    }
                    
                    print(f"[Worker] Attempting to send message {msg['id']} to {target_onion}")
                    success = net_util.send_message(target_onion, payload)
                    
                    if success:
                        # refresh status in DB
                        with controller.db_manager._get_conn() as conn:
                            conn.execute("UPDATE message SET status = 'OUTGOING_RECEIVED' WHERE id = ?", (msg['id'],))
                            conn.commit()
                        print(f"[Worker] Message {msg['id']} successfully delivered.")
            
        except Exception as e:
            print(f"[Worker] Error: {e}")
        
        time.sleep(5)

if __name__ == '__main__':
    net_util = NetworkUtility()
    
    threading.Thread(target=message_worker, args=(net_util,), daemon=True).start()

    run_flask_server(port=5000, net_util=net_util)