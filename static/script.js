document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const livePriceEl = document.getElementById('live-price');
    const priceChangeEl = document.getElementById('price-change');
    const marginEl = document.getElementById('available-margin');
    const posDataEl = document.getElementById('pos-data');
    const coreStatus = document.getElementById('core-status');
    
    // Manual Trade Tabs
    const tabBtns = document.querySelectorAll('.tab-btn');
    const sideInput = document.getElementById('side');
    const executeBtn = document.getElementById('execute-btn');
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            tabBtns.forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            const side = e.target.getAttribute('data-side');
            sideInput.value = side;
            
            if (side === 'SELL') {
                executeBtn.classList.add('sell-mode');
                executeBtn.innerText = 'Sell Bitcoin';
            } else {
                executeBtn.classList.remove('sell-mode');
                executeBtn.innerText = 'Buy Bitcoin';
            }
        });
    });

    // Chart Initialization (Light theme)
    let chart, candleSeries;
    try {
        const chartContainer = document.getElementById('chart-container');
        chart = LightweightCharts.createChart(chartContainer, {
            autoSize: true,
            layout: { background: { type: 'solid', color: '#ffffff' }, textColor: '#64748b' },
            grid: { vertLines: { color: '#f1f5f9' }, horzLines: { color: '#f1f5f9' } },
            crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
            timeScale: { timeVisible: true, secondsVisible: false, borderColor: '#e2e8f0' },
            rightPriceScale: { borderColor: '#e2e8f0' }
        });
        candleSeries = chart.addCandlestickSeries({
            upColor: '#00b87c', downColor: '#ef4444', borderDownColor: '#ef4444', borderUpColor: '#00b87c', wickDownColor: '#ef4444', wickUpColor: '#00b87c',
        });

        async function loadCandles() {
            try {
                const res = await fetch('https://testnet.binancefuture.com/fapi/v1/klines?symbol=BTCUSDT&interval=1m&limit=100');
                const data = await res.json();
                candleSeries.setData(data.map(d => ({ time: d[0] / 1000, open: parseFloat(d[1]), high: parseFloat(d[2]), low: parseFloat(d[3]), close: parseFloat(d[4]) })));
            } catch (e) {}
        }
        loadCandles();
    } catch (e) {
        console.error("Chart Init Error", e);
    }

    // WebSocket (Price Updates)
    let lastPrice = 0;
    try {
        const ws = new WebSocket('wss://stream.binancefuture.com/stream?streams=btcusdt@kline_1m/btcusdt@ticker');
        ws.onmessage = (event) => {
            const payload = JSON.parse(event.data);
            if (payload.stream === 'btcusdt@kline_1m') {
                const k = payload.data.k;
                const c = parseFloat(k.c);
                if(candleSeries) candleSeries.update({ time: k.t / 1000, open: parseFloat(k.o), high: parseFloat(k.h), low: parseFloat(k.l), close: c });
                
                livePriceEl.innerText = `$${c.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
                if (c > lastPrice) { livePriceEl.className = 'live-price flash-up'; setTimeout(()=> livePriceEl.className = 'live-price', 500); }
                else if (c < lastPrice) { livePriceEl.className = 'live-price flash-down'; setTimeout(()=> livePriceEl.className = 'live-price', 500); }
                lastPrice = c;
            } else if (payload.stream === 'btcusdt@ticker') {
                const change = parseFloat(payload.data.P); // Price change percent
                priceChangeEl.innerText = `${change > 0 ? '+' : ''}${change.toFixed(2)}%`;
                priceChangeEl.className = change >= 0 ? 'price-change positive' : 'price-change negative';
            }
        };
    } catch(e) {}

    // Engine State Polling
    async function pollEngineState() {
        try {
            const res = await fetch('/api/algo/state');
            const state = await res.json();
            
            // Panic Mode check
            if (state.panic_mode) {
                coreStatus.innerHTML = `<i data-feather="alert-triangle" class="status-icon" style="color:#ef4444;"></i> <span style="color:#ef4444; font-weight:600;">Safety Lock Active</span>`;
                feather.replace();
                return;
            }

            // Autopilot Status
            const isAlgoOn = document.getElementById('algo-switch').checked;
            if (isAlgoOn) {
                coreStatus.innerHTML = `<i data-feather="activity" class="status-icon"></i> <span>Autopilot is actively trading.</span>`;
            } else {
                coreStatus.innerHTML = `<i data-feather="moon" class="status-icon" style="color:#64748b;"></i> <span style="color:#64748b;">Autopilot is paused.</span>`;
            }
            feather.replace();

            // Portfolio Rendering
            if (state.position) {
                const sideClass = state.position === 'BUY' ? 'pos-buy' : 'pos-sell';
                const pnlMock = (Math.random() * 5).toFixed(2); // Simulated PNL display since we don't stream real entry price in state yet
                posDataEl.innerHTML = `
                    <div class="active-pos">
                        <div>
                            <div style="font-weight:600; font-size:16px; margin-bottom:4px;">BTC/USDT</div>
                            <span class="pos-side ${sideClass}">${state.position}</span>
                        </div>
                        <div class="pos-details">
                            <span style="font-size:12px; color:#64748b; margin-bottom:2px;">Current Return</span>
                            <span class="pos-pnl" style="color: ${state.position === 'BUY' ? '#00b87c' : '#ef4444'}">Live Active</span>
                        </div>
                    </div>`;
            } else {
                posDataEl.innerHTML = `
                    <div class="empty-state">
                        <i data-feather="briefcase" class="empty-icon"></i>
                        <p>No active investments right now.</p>
                    </div>`;
                feather.replace();
            }

        } catch (e) {}
    }
    setInterval(pollEngineState, 1500);

    // Balance Polling
    async function fetchBalance() {
        try {
            const res = await fetch('/api/balance');
            const data = await res.json();
            if (data.availableMargin) {
                // Convert to a local currency format or keep USDT
                marginEl.innerText = `${parseFloat(data.availableMargin).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})} USDT`;
            }
        } catch (e) { }
    }
    fetchBalance();
    setInterval(fetchBalance, 10000);

    // Toggles
    document.getElementById('algo-switch').addEventListener('change', async (e) => {
        await fetch('/api/algo/toggle', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ active: e.target.checked }) });
        pollEngineState();
    });

    // Panic Button (Safety)
    document.getElementById('kill-switch').addEventListener('click', async () => {
        try {
            await fetch('/api/algo/panic', { method: 'POST' });
            alert("Safety Protocol Activated. All positions closed.");
        } catch (e) { }
    });

    // Manual Trade Execution
    document.getElementById('execute-btn').addEventListener('click', async () => {
        const side = document.getElementById('side').value;
        const qty = document.getElementById('quantity').value;
        const payload = {
            symbol: 'BTCUSDT', side: side, type: document.getElementById('order-type').value,
            quantity: qty
        };
        try {
            await fetch('/api/trade', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
            alert(`${side} order placed successfully!`);
            fetchBalance();
        } catch (error) { 
            alert("Error placing order.");
        }
    });
});
