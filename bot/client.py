import os
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
from .logging_config import logger

class BinanceFuturesClient:
    """Wrapper for Binance Futures Testnet client."""
    
    def __init__(self, api_key: str = None, api_secret: str = None):
        self.api_key = api_key or os.getenv("BINANCE_API_KEY")
        self.api_secret = api_secret or os.getenv("BINANCE_API_SECRET")
        
        if not self.api_key or not self.api_secret:
            logger.error("API credentials missing.")
            raise ValueError("API Key and Secret must be provided or set as environment variables.")
        
        try:
            # Initialize the client for Binance Futures Testnet
            self.client = Client(
                self.api_key, 
                self.api_secret, 
                testnet=True  # Ensure we are using the testnet
            )
            # Switch to Futures testnet URL specifically just in case python-binance default testnet is spot
            # Actually python-binance handles futures testnet URL automatically if you call futures_ methods
            # But let's be explicit and safe if needed, though Client init with testnet=True handles the base URL.
            logger.info("Successfully initialized Binance Futures Testnet client.")
        except Exception as e:
            logger.error(f"Failed to initialize client: {str(e)}")
            raise
    
    def place_order(self, symbol: str, side: str, order_type: str, quantity: float, price: float = None, stop_price: float = None):
        """
        Sends an order to Binance Futures Testnet.
        """
        try:
            params = {
                'symbol': symbol,
                'side': side,
                'type': order_type,
                'quantity': quantity
            }
            
            if price and order_type in ['LIMIT', 'STOP', 'TAKE_PROFIT']:
                params['timeInForce'] = 'GTC'
                params['price'] = price
                
            if stop_price and order_type in ['STOP_MARKET', 'TAKE_PROFIT_MARKET', 'STOP', 'TAKE_PROFIT']:
                params['stopPrice'] = stop_price

            logger.info(f"Sending order request: {params}")
            
            # Using futures_create_order for USDT-M Futures
            response = self.client.futures_create_order(**params)
            logger.info(f"Order successful. Response: {response}")
            return response
            
        except BinanceAPIException as e:
            logger.error(f"Binance API Exception: Status {e.status_code} - {e.message}")
            raise
        except BinanceRequestException as e:
            logger.error(f"Binance Request Exception: {e.message}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during order placement: {str(e)}")
            raise

    def get_server_time(self):
        """Test connectivity by fetching server time."""
        try:
            time_res = self.client.futures_time()
            return time_res
        except Exception as e:
            logger.error(f"Failed to fetch server time: {e}")
            raise
