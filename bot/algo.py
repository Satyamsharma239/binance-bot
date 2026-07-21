import threading
import time
import sqlite3
import pandas as pd
import pandas_ta as ta
from bot.client import BinanceFuturesClient

class QuantEngineV4:
    """Institutional Grade Algorithmic Trading Engine with Panic / Volatility Protection"""
    
    def __init__(self):
        self.is_running = False
        self.thread = None
        self.client = BinanceFuturesClient()
        self.symbol = 'BTCUSDT'
        self.interval = '1m'
        self.logs = []
        
        # State Management
        self.position_side = None
        self.entry_price = 0.0
        self.position_qty = 0.0
        
        # Risk Parameters
        self.risk_pct = 0.02
        self.tp_pct = 0.015
        self.sl_pct = 0.0075
        
        # Neural Core State (Exposed to UI)
        self.state = {
            'rsi': 50.0,
            'macd': 0.0,
            'macd_signal': 0.0,
            'bb_upper': 0.0,
            'bb_lower': 0.0,
            'price': 0.0,
            'panic_mode': False,
            'position': None
        }
        
        # Panic Engine variables
        self.panic_mode_until = 0
        self.price_history_1m = [] # Track last 60 seconds of prices for velocity
        
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect('trades.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS trades
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      time TEXT, symbol TEXT, side TEXT, 
                      quantity REAL, entry_price REAL, exit_price REAL, pnl REAL)''')
        conn.commit()
        conn.close()

    def log(self, msg):
        time_str = time.strftime("%H:%M:%S")
        formatted = f"[{time_str}] {msg}"
        print(formatted)
        self.logs.append(formatted)
        if len(self.logs) > 50:
            self.logs.pop(0)

    def start(self):
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
            self.log("Quant Engine V4 (Neural Core) Started.")

    def stop(self):
        if self.is_running:
            self.is_running = False
            if self.thread:
                self.thread.join(timeout=2)
            self.log("Quant Engine V4 Halted.")

    def kill_switch(self):
        """EMERGENCY OVERRIDE: Liquidate everything and halt."""
        self.log("!!! MANUAL KILL SWITCH ACTIVATED !!!")
        self.state['panic_mode'] = True
        self.panic_mode_until = time.time() + 300 # Lock for 5 mins
        if self.position_side:
            # Force exit at market price
            price = self.state['price']
            self._exit_trade(price, "KILL SWITCH PANIC")
        self.stop()

    def _check_panic(self, current_price):
        """Monitors for Flash Crashes / Flash Pumps (>1.5% in 60 seconds)"""
        now = time.time()
        self.price_history_1m.append((now, current_price))
        # Keep only last 60 seconds
        self.price_history_1m = [p for p in self.price_history_1m if now - p[0] <= 60]
        
        if len(self.price_history_1m) > 5:
            oldest_price = self.price_history_1m[0][1]
            pct_change = abs((current_price - oldest_price) / oldest_price)
            
            if pct_change > 0.015: # 1.5% move in under 1 minute is a flash event
                self.log(f"!!! FLASH VOLATILITY DETECTED ({pct_change*100:.2f}%) !!! ENTERING PANIC MODE.")
                self.state['panic_mode'] = True
                self.panic_mode_until = time.time() + 300 # Cool down for 5 mins
                if self.position_side:
                    self._exit_trade(current_price, "VOLATILITY PANIC DUMP")
                return True
                
        if time.time() < self.panic_mode_until:
            return True
            
        self.state['panic_mode'] = False
        return False

    def _run_loop(self):
        while self.is_running:
            try:
                self._execute_cycle()
            except Exception as e:
                self.log(f"CRITICAL ERROR: {e}")
            for _ in range(5): # Faster tick rate for the Neural Core UI
                if not self.is_running: break
                time.sleep(1)

    def _execute_cycle(self):
        klines = self.client.client.futures_klines(symbol=self.symbol, interval=self.interval, limit=100)
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume', 
            'close_time', 'qav', 'trades', 'tbb', 'tbq', 'ignore'
        ])
        df['close'] = df['close'].astype(float)
        
        # Calculate Indicators
        df['RSI'] = df.ta.rsi(length=14)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        df.ta.bbands(length=20, std=2, append=True)
        
        latest = df.iloc[-2]
        current_price = df['close'].iloc[-1]
        
        rsi = latest['RSI']
        macd_line = latest.get('MACD_12_26_9', 0)
        signal_line = latest.get('MACDs_12_26_9', 0)
        bb_lower = latest.get('BBL_20_2.0_2.0', 0)
        bb_upper = latest.get('BBU_20_2.0_2.0', 0)

        # Update Live State for the UI
        self.state.update({
            'rsi': rsi if not pd.isna(rsi) else 50,
            'macd': macd_line if not pd.isna(macd_line) else 0,
            'macd_signal': signal_line if not pd.isna(signal_line) else 0,
            'bb_upper': bb_upper if not pd.isna(bb_upper) else current_price,
            'bb_lower': bb_lower if not pd.isna(bb_lower) else current_price,
            'price': current_price,
            'position': self.position_side
        })

        if pd.isna(rsi) or pd.isna(macd_line):
            return

        # PANIC OVERRIDE
        if self._check_panic(current_price):
            return # Block all further action until panic subsides

        # 1. Position Management
        if self.position_side:
            self._manage_open_position(current_price)
            return

        # 2. Confluence Entry Logic
        if rsi < 35 and macd_line > signal_line and current_price <= bb_lower * 1.001:
            self.log(f"*** NEURAL LOCK: BUY ALIGNMENT *** RSI={rsi:.2f}")
            self._enter_trade('BUY', current_price)
            
        elif rsi > 65 and macd_line < signal_line and current_price >= bb_upper * 0.999:
            self.log(f"*** NEURAL LOCK: SELL ALIGNMENT *** RSI={rsi:.2f}")
            self._enter_trade('SELL', current_price)

    def _enter_trade(self, side, current_price):
        try:
            balance = self.client.get_balance()
            margin = float(balance.get('availableMargin', 0))
            if margin <= 0: return

            risk_amount = margin * self.risk_pct
            qty = round(risk_amount / current_price, 3)
            if qty < 0.001: qty = 0.001

            self.log(f"Allocating {risk_amount:.2f} USDT -> Size: {qty} BTC")
            from bot.orders import execute_order
            execute_order(self.symbol, side, 'MARKET', qty)
            
            self.position_side = side
            self.entry_price = current_price
            self.position_qty = qty
            self.state['position'] = side
            self.log(f"[{side}] EXECUTED AT {current_price}")
        except Exception as e:
            self.log(f"Execution Error: {e}")

    def _manage_open_position(self, current_price):
        if not self.position_side: return
        take_profit = self.entry_price * (1 + self.tp_pct) if self.position_side == 'BUY' else self.entry_price * (1 - self.tp_pct)
        stop_loss = self.entry_price * (1 - self.sl_pct) if self.position_side == 'BUY' else self.entry_price * (1 + self.sl_pct)
            
        if self.position_side == 'BUY':
            if current_price >= take_profit: self._exit_trade(current_price, "TAKE PROFIT")
            elif current_price <= stop_loss: self._exit_trade(current_price, "STOP LOSS")
        else:
            if current_price <= take_profit: self._exit_trade(current_price, "TAKE PROFIT")
            elif current_price >= stop_loss: self._exit_trade(current_price, "STOP LOSS")

    def _exit_trade(self, exit_price, reason):
        self.log(f"*** EXITING POSITION: {reason} at {exit_price} ***")
        try:
            close_side = 'SELL' if self.position_side == 'BUY' else 'BUY'
            from bot.orders import execute_order
            execute_order(self.symbol, close_side, 'MARKET', self.position_qty)
            
            pnl = (exit_price - self.entry_price) * self.position_qty if self.position_side == 'BUY' else (self.entry_price - exit_price) * self.position_qty
            self.log(f"CLOSED. PNL: {pnl:.2f} USDT")
            
            conn = sqlite3.connect('trades.db')
            c = conn.cursor()
            c.execute("INSERT INTO trades (time, symbol, side, quantity, entry_price, exit_price, pnl) VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (time.strftime("%Y-%m-%d %H:%M:%S"), self.symbol, self.position_side, self.position_qty, self.entry_price, exit_price, pnl))
            conn.commit()
            conn.close()
        except Exception as e:
            self.log(f"Exit Error: {e}")
        finally:
            self.position_side = None
            self.entry_price = 0.0
            self.position_qty = 0.0
            self.state['position'] = None

algo_engine = QuantEngineV4()
