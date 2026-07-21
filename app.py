from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

# MUST LOAD DOTENV FIRST
load_dotenv()

from bot.client import BinanceFuturesClient
from bot.orders import execute_order
from bot.algo import algo_engine

app = Flask(__name__)

# Initialize client globally
try:
    client = BinanceFuturesClient()
except Exception as e:
    client = None
    print(f"Warning: Failed to initialize Binance Client. {e}")

@app.route('/')
def index():
    """Renders the main dashboard HTML."""
    return render_template('index.html')

@app.route('/api/balance', methods=['GET'])
def get_balance():
    """Returns the user's USDT balance and available margin."""
    if not client:
        return jsonify({'error': 'Client not initialized. Check API keys.'}), 500
    try:
        balance_data = client.get_balance()
        return jsonify(balance_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/trade', methods=['POST'])
def trade():
    """Executes a trade order."""
    data = request.json
    symbol = data.get('symbol')
    side = data.get('side')
    order_type = data.get('type')
    quantity = float(data.get('quantity', 0))
    price = data.get('price')

    try:
        if price: price = float(price)
        response = execute_order(
            symbol=symbol.upper(),
            side=side.upper(),
            order_type=order_type.upper(),
            quantity=quantity,
            price=price
        )
        return jsonify({'status': 'success', 'data': response})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/algo/toggle', methods=['POST'])
def toggle_algo():
    """Toggles the RSI algorithmic trading engine."""
    data = request.json
    active = data.get('active', False)
    
    if active:
        algo_engine.start()
        return jsonify({'status': 'success', 'message': 'Algo Engine Started'})
    else:
        algo_engine.stop()
        return jsonify({'status': 'success', 'message': 'Algo Engine Stopped'})

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Returns the recent logs from the Algo Engine."""
    return jsonify({'logs': algo_engine.logs})

@app.route('/api/algo/state', methods=['GET'])
def get_algo_state():
    """Returns the live state of the Neural Core."""
    return jsonify(algo_engine.state)

@app.route('/api/algo/panic', methods=['POST'])
def trigger_panic():
    """Manual kill switch override."""
    algo_engine.kill_switch()
    return jsonify({'status': 'success', 'message': 'PANIC MODE ACTIVATED. ALL POSITIONS LIQUIDATED.'})

if __name__ == '__main__':
    # Run the Flask app on port 5001 to avoid macOS AirPlay conflicts
    app.run(debug=True, port=5001)
