document.addEventListener('DOMContentLoaded', () => {
    const priceEl = document.getElementById('live-price');
    const marginEl = document.getElementById('available-margin');
    const chartContainer = document.getElementById('chart-container');
    const statusMsg = document.getElementById('status-message');
    const form = document.getElementById('trade-form');
    const tabs = document.querySelectorAll('.tab');
    const orderTypeInput = document.getElementById('order-type');
    const priceGroup = document.getElementById('price-group');
    const sideInput = document.getElementById('side');
    const buyBtn = document.getElementById('buy-btn');
    const sellBtn = document.getElementById('sell-btn');

    const chart = LightweightCharts.createChart(chartContainer, {
        width: chartContainer.clientWidth,
        height: chartContainer.clientHeight,
        layout: { background: { type: 'solid', color: '#0b0e11' }, textColor: '#848E9C' },
        grid: { vertLines: { color: '#2b3139' }, horzLines: { color: '#2b3139' } },
        crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
        timeScale: { timeVisible: true, secondsVisible: false },
    });
    
    const candleSeries = chart.addCandlestickSeries({
        upColor: '#0ECB81', downColor: '#F6465D', borderDownColor: '#F6465D', borderUpColor: '#0ECB81', wickDownColor: '#F6465D', wickUpColor: '#0ECB81',
    });

    window.addEventListener('resize', () => {
        chart.resize(chartContainer.clientWidth, chartContainer.clientHeight);
    });

    async function loadHistoricalCandles() {
        try {
            const res = await fetch('https://testnet.binancefuture.com/fapi/v1/klines?symbol=BTCUSDT&interval=1m&limit=200');
            const data = await res.json();
            const formattedData = data.map(d => ({
                time: d[0] / 1000, open: parseFloat(d[1]), high: parseFloat(d[2]), low: parseFloat(d[3]), close: parseFloat(d[4])
            }));
            candleSeries.setData(formattedData);
        } catch (error) { console.error('Failed to load historical candles:', error); }
    }
    loadHistoricalCandles();

    const ws = new WebSocket('wss://stream.binancefuture.com/ws/btcusdt@kline_1m');
    ws.onmessage = (event) => {
        const kline = JSON.parse(event.data).k;
        candleSeries.update({
            time: kline.t / 1000, open: parseFloat(kline.o), high: parseFloat(kline.h), low: parseFloat(kline.l), close: parseFloat(kline.c)
        });
        priceEl.innerText = parseFloat(kline.c).toFixed(2);
        priceEl.style.color = parseFloat(kline.c) >= parseFloat(kline.o) ? '#0ECB81' : '#F6465D';
    };

    async function fetchBalance() {
        try {
            const res = await fetch('/api/balance');
            const data = await res.json();
            if (data.availableMargin) {
                marginEl.innerText = `${parseFloat(data.availableMargin).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})} USDT`;
            }
        } catch (e) { console.error("Balance fetch error:", e); }
    }
    fetchBalance();
    setInterval(fetchBalance, 10000);

    tabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            tabs.forEach(t => t.classList.remove('active'));
            e.target.classList.add('active');
            orderTypeInput.value = e.target.getAttribute('data-type');
            priceGroup.style.display = orderTypeInput.value === 'LIMIT' ? 'block' : 'none';
        });
    });

    const tpSlCheckbox = document.getElementById('use-tpsl');
    const tpslInputs = document.getElementById('tpsl-inputs');
    tpSlCheckbox.addEventListener('change', (e) => {
        tpslInputs.style.display = e.target.checked ? 'block' : 'none';
    });

    buyBtn.addEventListener('click', () => { sideInput.value = 'BUY'; submitTrade(); });
    sellBtn.addEventListener('click', () => { sideInput.value = 'SELL'; submitTrade(); });

    function logToConsole(msg, isError=false) {
        const time = new Date().toLocaleTimeString();
        statusMsg.innerHTML = `<span style="color: #848E9C">[${time}]</span> <span style="color: ${isError ? '#F6465D' : '#0ECB81'}">${msg}</span>`;
    }

    async function submitTrade() {
        const payload = {
            symbol: 'BTCUSDT', side: sideInput.value, type: orderTypeInput.value,
            quantity: document.getElementById('quantity').value, price: document.getElementById('price').value
        };
        logToConsole(`Sending ${payload.side} order...`);
        try {
            const res = await fetch('/api/trade', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.status === 'success') {
                logToConsole(`FILLED: ${payload.side} ${payload.quantity} BTC`);
                fetchBalance();
            } else {
                logToConsole(`ERROR: ${data.message}`, true);
            }
        } catch (error) { logToConsole(`ERROR: ${error.message}`, true); }
    }
    
    document.getElementById('algo-switch').addEventListener('change', async (e) => {
        const isActive = e.target.checked;
        logToConsole(isActive ? "Starting Algo Engine..." : "Stopping Algo Engine...", !isActive);
        try {
            await fetch('/api/algo/toggle', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ active: isActive }) });
        } catch (error) { e.target.checked = !isActive; logToConsole("Algo toggle failed.", true); }
    });
});
