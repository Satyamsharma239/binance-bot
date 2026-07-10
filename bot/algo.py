import threading
import time
import sqlite3
import pandas as pd
import pandas_ta as ta
from bot.client import BinanceFuturesClient

class QuantEngineV3:
    """Institutional Grade Algorithmic Trading Engine"""
    
    def __init__(self):
        self.is_running = False
        self.thread = None
        self.client = BinanceFuturesClient()
        self.symbol = 'BTCUSDT'
        self.interval = '1m'
        self.logs = []
        
        # State Management
        self.position_side = None  # 'BUY', 'SELL', or None
        self.entry_price = 0.0
        self.position_qty = 0.0
        
        # Risk Parameters
        self.risk_pct = 0.02 # Risk 2% of available margin per trade
        self.tp_pct = 0.015  # Take profit at 1.5%
        self.sl_pct = 0.0075 # Stop loss at 0.75% (1:2 Risk/Reward)

        self._init_db()

    def _init_db(self):
        """Initialize SQLite database for trade logging."""
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
            self.log("Quant Engine V3 Started. State: ACTIVE")

    def stop(self):
        if self.is_running:
            self.is_running = False
            if self.thread:
                self.thread.join(timeout=2)
            self.log("Quant Engine V3 Stopped. State: HALTED")

    def _run_loop(self):
        while self.is_running:
            try:
                self._execute_cycle()
            except Exception as e:
                self.log(f"CRITICAL ERROR: {e}")
            for _ in range(10):
                if not self.is_running: break
                time.sleep(1)

    def _execute_cycle(self):
        """Core cycle: Fetch data, manage open positions, or look for entries."""
        klines = self.client.client.futures_klines(symbol=self.symbol, interval=self.interval, limit=100)
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume', 
            'close_time', 'qav', 'trades', 'tbb', 'tbq', 'ignore'
        ])
        df['close'] = df['close'].astype(float)
        
        # Calculate Indicators (Confluence Strategy)
        df['RSI'] = df.ta.rsi(length=14)
        macd = df.ta.macd(fast=12, slow=26, signal=9)
        df = pd.concat([df, macd], axis=1)
        bb = df.ta.bbands(length=20, std=2)
        df = pd.concat([df, bb], axis=1)
        
        # Latest completed candle data
        latest = df.iloc[-2]
        current_price = df['close'].iloc[-1]
        
        rsi = latest['RSI']
        macd_line = latest['MACD_12_26_9']
        signal_line = latest['MACDs_12_26_9']
        bb_lower = latest['BBL_20_2.0_2.0']
        bb_upper = latest['BBU_20_2.0_2.0']

        if pd.isna(rsi) or pd.isna(macd_line):
            self.log("Warming up indicators...")
            return

        self.log(f"{self.symbol} | Price: {current_price} | RSI: {rsi:.2f}")

        # 1. Position Management (Exit Logic)
        if self.position_side:
            self._manage_open_position(current_price)
            return

        # 2. Entry Logic (Confluence)
        # LONG CONDITION: RSI Oversold + MACD Bullish Cross + Price near/below Lower BB
        if rsi < 35 and macd_line > signal_line and current_price <= bb_lower * 1.001:
            self.log(f"*** CONFLUENCE BUY SIGNAL *** RSI={rsi:.2f}, MACD Bullish, BB Support")
            self._enter_trade('BUY', current_price)
            
        # SHORT CONDITION: RSI Overbought + MACD Bearish Cross + Price near/above Upper BB
        elif rsi > 65 and macd_line < signal_line and current_price >= bb_upper * 0.999:
            self.log(f"*** CONFLUENCE SELL SIGNAL *** RSI={rsi:.2f}, MACD Bearish, BB Resistance")
            self._enter_trade('SELL', current_price)

    def _enter_trade(self, side, current_price):
        """Calculates dynamic position sizing and enters the trade."""
        try:
            # 1. Fetch available margin
            balance = self.client.get_balance()
            margin = float(balance.get('availableMargin', 0))
            if margin <= 0:
                self.log("Insufficient margin to trade.")
                return

            # 2. Dynamic Position Sizing (Risk 2% of margin)
            risk_amount = margin * self.risk_pct
            qty = risk_amount / current_price
            
            # Binance BTCUSDT min quantity is 0.001
            qty = round(qty, 3)
            if qty < 0.001:
                qty = 0.001 # Fallback to min size

            self.log(f"Risking {risk_amount:.2f} USDT -> Size: {qty} BTC")

            # 3. Execute Trade
            from bot.orders import execute_order
            # In test mode, we might just simulate execution if API keys are strictly for chart watching.
            # But the logic executes the testnet order:
            execute_order(self.symbol, side, 'MARKET', qty)
            
            # 4. Update State
            self.position_side = side
            self.entry_price = current_price
            self.position_qty = qty
            self.log(f"[{side}] Position Opened at {current_price}")
            
        except Exception as e:
            self.log(f"Failed to enter trade: {e}")

    def _manage_open_position(self, current_price):
        """Monitors open position for Take Profit or Stop Loss."""
        if not self.position_side: return
        
        take_profit = 0.0
        stop_loss = 0.0
        
        if self.position_side == 'BUY':
            take_profit = self.entry_price * (1 + self.tp_pct)
            stop_loss = self.entry_price * (1 - self.sl_pct)
            
            if current_price >= take_profit:
                self._exit_trade(current_price, "TAKE PROFIT")
            elif current_price <= stop_loss:
                self._exit_trade(current_price, "STOP LOSS")
                
        elif self.position_side == 'SELL':
            take_profit = self.entry_price * (1 - self.tp_pct)
            stop_loss = self.entry_price * (1 + self.sl_pct)
            
            if current_price <= take_profit:
                self._exit_trade(current_price, "TAKE PROFIT")
            elif current_price >= stop_loss:
                self._exit_trade(current_price, "STOP LOSS")

    def _exit_trade(self, exit_price, reason):
        """Exits trade, resets state, and logs to SQLite."""
        self.log(f"*** CLOSING POSITION: {reason} at {exit_price} ***")
        
        try:
            # Execute closing order (opposite side)
            close_side = 'SELL' if self.position_side == 'BUY' else 'BUY'
            from bot.orders import execute_order
            execute_order(self.symbol, close_side, 'MARKET', self.position_qty)
            
            # Calculate PNL
            pnl = 0.0
            if self.position_side == 'BUY':
                pnl = (exit_price - self.entry_price) * self.position_qty
            else:
                pnl = (self.entry_price - exit_price) * self.position_qty
                
            self.log(f"Trade Closed. PNL: {pnl:.2f} USDT")
            
            # Log to DB
            conn = sqlite3.connect('trades.db')
            c = conn.cursor()
            time_str = time.strftime("%Y-%m-%d %H:%M:%S")
            c.execute("INSERT INTO trades (time, symbol, side, quantity, entry_price, exit_price, pnl) VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (time_str, self.symbol, self.position_side, self.position_qty, self.entry_price, exit_price, pnl))
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.log(f"Failed to exit trade gracefully: {e}")
            
        finally:
            # Reset State
            self.position_side = None
            self.entry_price = 0.0
            self.position_qty = 0.0

algo_engine = QuantEngineV3()
