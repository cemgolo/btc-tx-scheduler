from flask import Flask, request, jsonify, render_template
from file_manager import load_transactions, save_transaction, delete_transaction
from broadcaster import broadcast_transaction
from signer import generate_private_key, sign_transaction
from utils import get_current_time
import os
from pathlib import Path

# Initialize Flask app
app = Flask(__name__)
TX_DIR = Path('transactions')

@app.route('/')
def home():
    return render_template("index.html")  # Render a simple homepage (described below)

@app.route('/transactions', methods=['GET'])
def list_transactions():
    # Load transactions and format for display
    transactions = load_transactions()
    formatted = [
        {
            "id": tx["file"].name,
            "scheduled_time": tx["scheduled_time"].strftime("%Y-%m-%d %H:%M:%S"),
            "status": "pending"
        }
        for tx in transactions
    ]
    return jsonify(formatted)

@app.route('/schedule', methods=['POST'])
def schedule_transaction():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        # Extract and validate input
        mnemonic_words = data["mnemonic"]
        recipient_address = data["recipient"]
        amount = float(data["amount"])
        fee_rate = float(data["fee_rate"])
        scheduled_time_str = data["scheduled_time"]

        # Generate private key and sign transaction
        key = generate_private_key(mnemonic_words)
        unspents = key.get_unspents()
        if not unspents:
            return jsonify({"error": "No unspent transactions available"}), 400
        outputs = [(recipient_address, amount, 'btc')]
        unsigned_tx_hex = key.create_transaction(
            outputs, fee=0, absolute_fee=True, unspents=unspents, combine=True
        )
        estimated_size = len(unsigned_tx_hex) // 2
        total_fee_satoshis = int(fee_rate * estimated_size)
        signed_tx_hex = sign_transaction(key, outputs, total_fee_satoshis, unspents)

        # Save transaction
        tx_filename = save_transaction(signed_tx_hex, scheduled_time_str)
        return jsonify({"message": f"Transaction saved as {tx_filename.name}"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/broadcast', methods=['POST'])
def broadcast_transaction_cli():
    data = request.get_json()
    if not data or "id" not in data:
        return jsonify({"error": "Transaction ID is required"}), 400

    tx_id = data["id"]
    tx_file = TX_DIR / tx_id
    if tx_file.exists():
        with open(tx_file, 'r') as f:
            tx_data = json.load(f)
            signed_tx_hex = tx_data['signed_tx_hex']
            try:
                broadcast_transaction(signed_tx_hex)
                delete_transaction(tx_file)
                return jsonify({"message": "Transaction broadcasted successfully"}), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"error": "Transaction not found"}), 404

if __name__ == '__main__':
    # Ensure transaction directory exists
    TX_DIR.mkdir(exist_ok=True)

    # Run the Flask app
    app.run(debug=True)
