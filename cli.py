import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint
from dotenv import load_dotenv

from bot.orders import execute_order

# Load environment variables from .env file
load_dotenv()

app = typer.Typer(help="Binance Futures Testnet Trading Bot CLI")
console = Console()

def display_summary(symbol: str, side: str, order_type: str, quantity: float, price: Optional[float] = None, stop_price: Optional[float] = None):
    """Displays a summary of the order being requested."""
    table = Table(show_header=True, header_style="bold magenta", title="Order Request Summary")
    table.add_column("Parameter", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Symbol", symbol.upper())
    table.add_row("Side", side.upper())
    table.add_row("Order Type", order_type.upper())
    table.add_row("Quantity", str(quantity))
    
    if price:
        table.add_row("Price", str(price))
    if stop_price:
        table.add_row("Stop Price", str(stop_price))
        
    console.print(table)
    console.print("\n")

def display_response(response: dict):
    """Displays the API response details."""
    table = Table(show_header=True, header_style="bold yellow", title="Order Response Details")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="green")
    
    # Extracting relevant fields as per requirements
    keys_to_show = ['orderId', 'symbol', 'status', 'clientOrderId', 'price', 'origQty', 'executedQty', 'avgPrice', 'type', 'side']
    
    for key in keys_to_show:
        if key in response:
            table.add_row(key, str(response[key]))
            
    console.print(table)
    console.print(Panel("[bold green]Order Placed Successfully![/bold green]", expand=False))

@app.command()
def market(
    symbol: str = typer.Argument(..., help="Trading pair symbol (e.g., BTCUSDT)"),
    side: str = typer.Argument(..., help="Order side (BUY or SELL)"),
    quantity: float = typer.Argument(..., help="Quantity to trade")
):
    """Place a Market Order."""
    try:
        display_summary(symbol, side, "MARKET", quantity)
        response = execute_order(symbol, side, "MARKET", quantity)
        display_response(response)
    except Exception as e:
        console.print(Panel(f"[bold red]Failed to place Market Order:[/bold red]\n{str(e)}", expand=False))
        raise typer.Exit(code=1)

@app.command()
def limit(
    symbol: str = typer.Argument(..., help="Trading pair symbol (e.g., BTCUSDT)"),
    side: str = typer.Argument(..., help="Order side (BUY or SELL)"),
    quantity: float = typer.Argument(..., help="Quantity to trade"),
    price: float = typer.Argument(..., help="Limit price")
):
    """Place a Limit Order."""
    try:
        display_summary(symbol, side, "LIMIT", quantity, price)
        response = execute_order(symbol, side, "LIMIT", quantity, price)
        display_response(response)
    except Exception as e:
        console.print(Panel(f"[bold red]Failed to place Limit Order:[/bold red]\n{str(e)}", expand=False))
        raise typer.Exit(code=1)

@app.command()
def stop_limit(
    symbol: str = typer.Argument(..., help="Trading pair symbol (e.g., BTCUSDT)"),
    side: str = typer.Argument(..., help="Order side (BUY or SELL)"),
    quantity: float = typer.Argument(..., help="Quantity to trade"),
    price: float = typer.Argument(..., help="Limit price"),
    stop_price: float = typer.Argument(..., help="Stop trigger price")
):
    """Place a Stop-Limit Order."""
    try:
        display_summary(symbol, side, "STOP", quantity, price, stop_price)
        # Type 'STOP' in Binance Futures requires both price and stopPrice
        response = execute_order(symbol, side, "STOP", quantity, price, stop_price)
        display_response(response)
    except Exception as e:
        console.print(Panel(f"[bold red]Failed to place Stop-Limit Order:[/bold red]\n{str(e)}", expand=False))
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
