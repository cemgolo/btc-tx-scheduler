from flask import Flask, request, jsonify, render_template
from file_manager import load_transactions, save_transaction, delete_transaction
from broadcaster import broadcast_transaction
from signer import generate_private_key, sign_transaction
from utils import public_key_to_address
from pathlib import Path
from datetime import datetime
from utils import get_current_time


app = Flask(__name__)
TX_DIR = Path('transactions')

transactions = []

@app.route('/')
def home():
    return render_template("index.html", transactions=transactions)

@app.route('/schedule', methods=['POST'])
def create_transaction():
    mnemonic = request.form.get('mnemonic')
    address_choice = request.form.get('address_choice')
    recipient_address = None

    if address_choice == 'direct':
        recipient_address = request.form.get('recipient_address')
    elif address_choice == 'public_key':
        public_key_hex = request.form.get('public_key')
        try:
            public_key_bytes = bytes.fromhex(public_key_hex)
            recipient_address = public_key_to_address(public_key_bytes)
        except ValueError:
            return jsonify({'error': 'Invalid public key format'}), 400

    if not recipient_address:
        return jsonify({'error': 'Recipient address is required'}), 400

    amount = request.form.get('amount')
    fee_rate = request.form.get('fee_rate')
    scheduled_time_str = request.form.get('scheduled_time')

    try:
        key = generate_private_key(mnemonic)
    except ValueError as ve:
        return jsonify({'error': f"Invalid mnemonic: {ve}"}), 400

    unspents = key.get_unspents()
    if not unspents:
        return jsonify({'error': 'No unspent transactions available'}), 400

    outputs = [(recipient_address, amount, 'btc')]
    try:
        unsigned_tx_hex = key.create_transaction(
            outputs, fee=0, absolute_fee=True, unspents=unspents, combine=True
        )
        estimated_size = len(unsigned_tx_hex) // 2
        total_fee_satoshis = int(fee_rate * estimated_size)
        signed_tx_hex = sign_transaction(key, outputs, total_fee_satoshis, unspents)
    except ValueError as ve:
        return jsonify({'error': f"Error creating transaction: {ve}"}), 400

    try:
        scheduled_time = datetime.strptime(scheduled_time_str, '%Y-%m-%dT%H:%M')
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400

    tx_filename = save_transaction(signed_tx_hex, scheduled_time_str)
    print(f"Transaction created and saved as: {tx_filename.name}")

    transaction = {
        'mnemonic': mnemonic,
        'recipient_address': recipient_address,
        'amount': amount,
        'fee_rate': fee_rate,
        'scheduled_time': scheduled_time.strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'pending'
    }

    transactions.append(transaction)

    return jsonify({'success': True, 'transaction': transaction})

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
    
def delete_transaction_cli():
    tx_id = request.form.get('tx_id').strip()
    tx_file = Path('transactions') / tx_id
    if tx_file.exists():
        delete_transaction(tx_file)
        jsonify({"message": "Transaction deleted successfully."}), 200
    else:
        jsonify({"error": "Transaction not found."}), 404

def check_and_broadcast_transactions():
    transactions = load_transactions()
    now = get_current_time()
    for tx in transactions:
        if tx['scheduled_time'] <= now:
            print(f"Broadcasting transaction ID: {tx['file'].name}")
            try:
                broadcast_transaction(tx['signed_tx_hex'])
                delete_transaction(tx['file'])
                print(f"Transaction {tx['file'].name} broadcasted successfully.")
            except Exception as e:
                print(f"Error broadcasting transaction {tx['file'].name}: {e}")

if __name__ == '__main__':
    TX_DIR.mkdir(exist_ok=True)
    app.run(debug=True)
