import threading
import time
import pandas as pd
import pandas_ta as ta
from bot.client import BinanceFuturesClient

class AlgoEngine:
    def __init__(self):
        self.is_running = False
        self.thread = None
        self.client = BinanceFuturesClient()
        self.symbol = 'BTCUSDT'
        self.quantity = 0.005
        self.interval = '1m'

    def start(self):
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
            print("Algo Engine Started.")

    def stop(self):
        if self.is_running:
            self.is_running = False
            if self.thread:
                self.thread.join(timeout=2)
            print("Algo Engine Stopped.")

    def _run_loop(self):
        while self.is_running:
            try:
                self._check_signals()
            except Exception as e:
                print(f"Algo error: {e}")
            for _ in range(10):
                if not self.is_running: break
                time.sleep(1)

    def _check_signals(self):
        klines = self.client.client.futures_klines(symbol=self.symbol, interval=self.interval, limit=100)
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume', 
            'close_time', 'quote_asset_volume', 'trades', 
            'taker_buy_base', 'taker_buy_quote', 'ignore'
        ])
        df['close'] = df['close'].astype(float)
        df['RSI'] = df.ta.rsi(length=14)
        
        latest_rsi = df['RSI'].iloc[-2]
        current_price = df['close'].iloc[-1]
        
        print(f"[ALGO] {self.symbol} - Price: {current_price} | RSI: {latest_rsi:.2f}")

        if latest_rsi < 30:
            print(f"*** BUY SIGNAL (Oversold): RSI {latest_rsi:.2f} < 30 ***")
        elif latest_rsi > 70:
            print(f"*** SELL SIGNAL (Overbought): RSI {latest_rsi:.2f} > 70 ***")

algo_engine = AlgoEngine()
