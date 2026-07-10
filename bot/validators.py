from typing import Union

def validate_symbol(symbol: str) -> str:
    """Validates and formats the trading symbol."""
    if not symbol or len(symbol) < 3:
        raise ValueError("Symbol must be at least 3 characters long.")
    return symbol.upper()

def validate_side(side: str) -> str:
    """Validates the order side (BUY or SELL)."""
    side = side.upper()
    if side not in ["BUY", "SELL"]:
        raise ValueError("Side must be either 'BUY' or 'SELL'.")
    return side

def validate_positive_number(value: Union[float, str, None], name: str) -> float:
    """Validates that a value is a positive number."""
    if value is None:
        raise ValueError(f"{name} cannot be None.")
    try:
        float_val = float(value)
        if float_val <= 0:
            raise ValueError(f"{name} must be strictly positive.")
        return float_val
    except ValueError:
        raise ValueError(f"{name} must be a valid number.")

def validate_order_type(order_type: str) -> str:
    """Validates the order type."""
    order_type = order_type.upper()
    valid_types = ["MARKET", "LIMIT", "STOP", "STOP_MARKET", "TAKE_PROFIT", "TAKE_PROFIT_MARKET"]
    if order_type not in valid_types:
        raise ValueError(f"Order type must be one of {valid_types}.")
    return order_type
