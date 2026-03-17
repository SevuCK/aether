import logging
import json
from flask import Flask, request, jsonify
from dbmgr import DatabaseManager
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
app.logger.setLevel(logging.INFO)

db_manager = None
network_utility = None
my_onion_address = None

# ==========================================
# CHATS Endpoints (Frontend -> Backend)
# ==========================================
@app.route('/allChats/', methods=['GET'])
def get_all_chats():
    """Gibt alle Chats inklusive der letzten Nachricht zurück."""
    if not db_manager:
        return jsonify({"error": "Database not initialized"}), 500

    chats = db_manager.get_all_chats_with_last_message()
    return jsonify({"chats": chats}), 200


@app.route('/chat/<int:chat_id>', methods=['GET'])
def get_chat_messages(chat_id):
    """Gibt alle Nachrichten eines spezifischen Chats zurück."""
    if not db_manager:
        return jsonify({"error": "Database not initialized"}), 500

    messages = db_manager.get_messages_for_chat(chat_id)
    return jsonify({"chat_id": chat_id, "messages": messages}), 200


@app.route('/chat/<int:chat_id>', methods=['DELETE'])
def clear_chat_history(chat_id):
    """Löscht den gesamten Nachrichtenverlauf eines Chats."""
    if not db_manager:
        return jsonify({"error": "Database not initialized"}), 500

    db_manager.clear_chat_history(chat_id)
    return jsonify({"status": "success", "message": f"History for chat {chat_id} cleared"}), 200


@app.route('/chat/export/<int:chat_id>', methods=['GET'])
def export_chat(chat_id):
    """Exportiert einen spezifischen Chat als JSON."""
    if not db_manager:
        return jsonify({"error": "Database not initialized"}), 500

    messages = db_manager.get_messages_for_chat(chat_id)
    export_data = {
        "chat_id": chat_id,
        "messages": messages
    }
    # TECH DEBT: perhaps return downloadable file in the future
    return jsonify({"status": "success", "export": export_data}), 200


# ==========================================
# CONTACTS Endpoints (Frontend -> Backend)
# ==========================================
@app.route('/contacts', methods=['POST'])
def create_contact():
    """Erstellt einen neuen Kontakt."""
    data = request.json
    if not data or not data.get('alias') or not data.get('onion_adress'):
        return jsonify({"error": "alias and onion_adress are required"}), 400

    contact_id, chat_id = db_manager.create_contact(
        data['alias'], data['onion_adress'])

    if contact_id is None:
        return jsonify({"error": "Contact with this onion address already exists"}), 409

    return jsonify({"status": "success", "contact_id": contact_id, "chat_id": chat_id}), 201


@app.route('/contacts/<int:contact_id>', methods=['DELETE'])
def delete_contact(contact_id):
    """Löscht einen Kontakt und den dazugehörigen Chat (via CASCADE)."""
    db_manager.delete_contact(contact_id)
    return jsonify({"status": "success", "message": f"Contact {contact_id} deleted"}), 200


@app.route('/contacts/alias', methods=['POST'])
def update_contact_alias():
    """Aktualisiert den Alias eines existierenden Kontakts."""
    data = request.json
    if not data or not data.get('contact_id') or not data.get('alias'):
        return jsonify({"error": "contact_id and alias are required"}), 400

    db_manager.update_alias(data['contact_id'], data['alias'])
    return jsonify({"status": "success"}), 200


# ==========================================
# MESSAGES Endpoints (Frontend -> Backend)
# ==========================================
@app.route('/chats/messages/<int:chat_id>/<int:message_id>', methods=['DELETE'])
def delete_specific_message(chat_id, message_id):
    """Löscht eine spezifische Nachricht aus einem Chat."""
    db_manager.delete_message(message_id, chat_id)
    return jsonify({"status": "success", "chat_id": chat_id, "message_id": message_id}), 200


@app.route('/chats/messages', methods=['POST'])
def send_message():
    """
    Speichert eine ausgehende Nachricht und versendet sie über das Tor-Netzwerk.
    """
    data = request.json
    if not data or not data.get('chat_id') or not data.get('message'):
        return jsonify({"error": "chat_id and message object are required"}), 400

    chat_id = data['chat_id']
    msg_content = data['message'].get('content')
    msg_timestamp = data['message'].get('timestamp')

    # get contact addr from db
    target_onion = db_manager.get_onion_for_chat(chat_id)
    if not target_onion:
        return jsonify({"error": "Chat or associated contact not found"}), 404

    # send via tor
    payload = {
        "sender_onion": my_onion_address,
        "text": msg_content,
        "timestamp": msg_timestamp
    }

    success = False
    if network_utility:
        success = network_utility.send_message(target_onion, payload)

    if success:
        # mark as "sent" in db
        db_manager.save_message(
            chat_id, msg_content, msg_timestamp, status="OUTGOING_RECEIVED", sender="me")
        return jsonify({"status": "success", "message": "Message sent via Tor"}), 200
    else:
        # mark as "error" in db
        db_manager.save_message(chat_id, msg_content,
                                msg_timestamp, status="FAILED", sender="me")
        return jsonify({"error": "Failed to send message via Tor network"}), 503

# ==========================================
# P2P Endpoints (Tor-Network -> Backend)
# ==========================================
@app.route('/api/receive_message', methods=['POST'])
def receive_message_from_peer():
    """
    Dieser Endpunkt wird von ANDEREN Tor-Clients aufgerufen.
    Der Traffic kommt via Tor Hidden Service rein.
    """
    data = request.json
    if not data or not data.get('sender_onion') or not data.get('text'):
        return jsonify({"error": "Invalid payload"}), 400

    sender_onion = data.get('sender_onion')
    text = data.get('text')
    timestamp = data.get('timestamp')

    app.logger.info(f"\n[Tor P2P] New message from {sender_onion}")

    # check if chat with onion addr exists
    chat_id = db_manager.get_chat_id_by_onion(sender_onion)

    # create cintact if unknown otherwise message will be dropped immediately
    if not chat_id:
        app.logger.info("[*] Unknown sender. Creating new contact...")
        contact_id, chat_id = db_manager.create_contact(
            "unknown", sender_onion)

    # save msg
    if chat_id:
        db_manager.save_message(chat_id, text, timestamp,
                                status="INCOMING_UNREAD", sender=sender_onion)
        return jsonify({"status": "ok"}), 200
    else:
        return jsonify({"error": "Internal database error"}), 500

# ==========================================
# SYSTEM / SETUP
# ==========================================
@app.route('/system/info', methods=['GET'])
def get_system_info():
    """Gibt dem Frontend die eigene Onion-Adresse zurück."""
    return jsonify({
        "status": "ready" if my_onion_address else "starting",
        "onion_address": my_onion_address
    }), 200


# ==========================================
# AUTH ENDPOINTS
# ==========================================

@app.route('/auth/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password') # placeholder for SQLCipher key
    
    if not username:
        return jsonify({"error": "Username is required"}), 400
        
    db_file = f"{username}.aetherdb"
    temp_db = DatabaseManager(db_file) # initialize User DB
    return jsonify({"status": "success", "message": "Profile created."}), 201

@app.route('/auth/login', methods=['POST'])
def login():
    global db_manager, network_utility, my_onion_address
    data = request.json
    username = data.get('username')
    
    if not username:
        return jsonify({"error": "Username is required"}), 400
        
    app.logger.info(f"[*] Login attempt for user: {username}")
    
    db_file = f"{username}.aetherdb"
    db_manager = DatabaseManager(db_file)
    
    identity = db_manager.load_identity()
    
    if identity and my_onion_address == identity['onion_address']:
        app.logger.info("[*] Tor Service already runing for this user. Skipping Bootstrapping.")
        return jsonify({"status": "success", "message": "Database unlocked."}), 200

    # delete old Tor instance from memory if present upon ogin
    if my_onion_address and network_utility and hasattr(network_utility, 'controller'):
        try:
            network_utility.controller.remove_ephemeral_hidden_service(my_onion_address)
            app.logger.info(f"[*] Deleted Tor-Service ({my_onion_address}) from memory")
        except Exception as e:
            app.logger.warning(f"[*] Error removing old Tor Service: {e}")
    
    if identity:
        app.logger.info("[*] Load existing Tor identity...")
        onion, key_type, private_key = network_utility.start_onion_service(
            flask_port=5000,
            key_type=identity['key_type'],
            private_key=identity['private_key']
        )
    else:
        app.logger.info("[*] Creating new Tor Identity for this user...")
        onion, key_type, private_key = network_utility.start_onion_service(flask_port=5000)
        if onion:
            db_manager.save_identity(onion, key_type, private_key)
            
    if onion:
        my_onion_address = onion
        return jsonify({"status": "success", "message": "Database unlocked."}), 200
    else:
        return jsonify({"error": "Tor Service failed to start"}), 500


# ==========================================
# RUNNER
# ==========================================
def run_flask_server(port, net_util):
    """Starts Flask Server and only injetcs netutil"""
    global network_utility
    network_utility = net_util

    app.logger.info(f"[*] Initializing System... waiting for user login to start Tor service.")
    app.logger.info(f"[*] Start API Controller on Port {port}...")
    
    app.run(host='0.0.0.0', port=port, use_reloader=False)