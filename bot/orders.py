from .client import BinanceFuturesClient
from .validators import validate_symbol, validate_side, validate_positive_number, validate_order_type
from .logging_config import logger

def execute_order(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: float = None,
    stop_price: float = None
) -> dict:
    """
    Validates inputs and executes the order via the client.
    """
    try:
        # Validate inputs
        val_symbol = validate_symbol(symbol)
        val_side = validate_side(side)
        val_order_type = validate_order_type(order_type)
        val_quantity = validate_positive_number(quantity, "Quantity")
        
        val_price = None
        if val_order_type in ['LIMIT', 'STOP', 'TAKE_PROFIT']:
            val_price = validate_positive_number(price, "Price")
            
        val_stop_price = None
        if val_order_type in ['STOP_MARKET', 'TAKE_PROFIT_MARKET', 'STOP', 'TAKE_PROFIT']:
            val_stop_price = validate_positive_number(stop_price, "Stop Price")
            
        logger.info(f"Validations passed for {val_order_type} {val_side} {val_symbol}.")
        
        # Initialize client (will pick up credentials from env vars)
        client = BinanceFuturesClient()
        
        # Place order
        response = client.place_order(
            symbol=val_symbol,
            side=val_side,
            order_type=val_order_type,
            quantity=val_quantity,
            price=val_price,
            stop_price=val_stop_price
        )
        return response
        
    except ValueError as ve:
        logger.error(f"Validation Error: {ve}")
        raise
    except Exception as e:
        logger.error(f"Order Execution Failed: {e}")
        raise
