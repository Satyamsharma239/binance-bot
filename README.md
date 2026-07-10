# Binance Algorithmic Trading Bot (Production Ready)

A premium, full-stack Algorithmic Trading Application that connects directly to the Binance Futures Testnet (USDT-M). Built with a Wall-Street-grade architecture including **Live WebSockets**, **RSI Algorithmic Auto-Pilot**, and **TradingView Lightweight Charts**.

This repository is **fully containerized via Docker**, comprehensively unit-tested with **Pytest**, and utilizes **GitHub Actions CI/CD** for continuous integration.

## Advanced Features

- **Live TradingView Charts:** Real interactive candlestick charts built with the official `lightweight-charts` API.
- **Binance WebSockets:** Lightning-fast tick data streamed directly to the frontend with zero polling delay.
- **Algorithmic Auto-Pilot (RSI):** A background pandas-based algorithmic engine that calculates the Relative Strength Index (RSI) in real-time to execute autonomous Oversold/Overbought entries.
- **Advanced Order Types:** Built-in OCO (Take Profit & Stop Loss) management directly from the dashboard.
- **Professional Dashboard:** Strict, dark-mode grid layout mimicking real exchange terminals (like Binance and Kraken).

## DevOps & Production Deployment

This project is built for professional deployment.

### 1. Run with Docker (Recommended)
You can deploy the entire application instantly using Docker.
```bash
docker-compose up --build -d
```
The server will start autonomously on `http://localhost:5001`.

### 2. Run Locally (Virtual Environment)
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```
Open `http://localhost:5001`.

## Automated Testing (CI/CD)

This project has strict test coverage. To run the tests locally:
```bash
PYTHONPATH=. pytest tests/ -v
```
A GitHub Actions workflow is included (`.github/workflows/test.yml`). Every commit pushed to `main` automatically triggers the CI/CD pipeline to verify the Algorithmic Engine and Flask endpoints.

## Environment Variables
Create a `.env` file in the root directory:
```env
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_api_secret_here
```
