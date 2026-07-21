document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const livePriceEl = document.getElementById('live-price');
    const marginEl = document.getElementById('available-margin');
    const statusMsg = document.getElementById('status-message');
    const posDataEl = document.getElementById('pos-data');
    
    // Gauges
    const rsiVal = document.getElementById('rsi-val');
    const rsiBar = document.getElementById('rsi-bar');
    const macdVal = document.getElementById('macd-val');
    const macdBar = document.getElementById('macd-bar');
    const bbVal = document.getElementById('bb-val');
    const bbBar = document.getElementById('bb-bar');
    const coreStatus = document.getElementById('core-status');
    const bodyEl = document.getElementById('app-body');

    // Chart
    const chartContainer = document.getElementById('chart-container');
    const chart = LightweightCharts.createChart(chartContainer, {
        autoSize: true,
        layout: { background: { type: 'solid', color: 'transparent' }, textColor: '#888888' },
        grid: { vertLines: { color: 'rgba(255,255,255,0.05)' }, horzLines: { color: 'rgba(255,255,255,0.05)' } },
        crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
        timeScale: { timeVisible: true, secondsVisible: false },
    });
    const candleSeries = chart.addCandlestickSeries({
        upColor: '#00ff88', downColor: '#ff3366', borderDownColor: '#ff3366', borderUpColor: '#00ff88', wickDownColor: '#ff3366', wickUpColor: '#00ff88',
    });

    // Load Historical Candles
    async function loadCandles() {
        try {
            const res = await fetch('https://testnet.binancefuture.com/fapi/v1/klines?symbol=BTCUSDT&interval=1m&limit=100');
            const data = await res.json();
            candleSeries.setData(data.map(d => ({ time: d[0] / 1000, open: parseFloat(d[1]), high: parseFloat(d[2]), low: parseFloat(d[3]), close: parseFloat(d[4]) })));
        } catch (e) { }
    }
    loadCandles();

    // WebSocket (Price & Orderbook)
    const ws = new WebSocket('wss://stream.binancefuture.com/stream?streams=btcusdt@kline_1m/btcusdt@depth10@100ms');
    let lastPrice = 0;
    ws.onmessage = (event) => {
        const payload = JSON.parse(event.data);
        if (payload.stream === 'btcusdt@kline_1m') {
            const k = payload.data.k;
            const c = parseFloat(k.c);
            candleSeries.update({ time: k.t / 1000, open: parseFloat(k.o), high: parseFloat(k.h), low: parseFloat(k.l), close: c });
            
            // Flash Price Animation
            livePriceEl.innerText = c.toFixed(2);
            if (c > lastPrice) { livePriceEl.className = 'stat-value flash-up'; setTimeout(()=> livePriceEl.className = 'stat-value text-cyan', 500); }
            else if (c < lastPrice) { livePriceEl.className = 'stat-value flash-down'; setTimeout(()=> livePriceEl.className = 'stat-value text-cyan', 500); }
            lastPrice = c;
        }
        else if (payload.stream === 'btcusdt@depth10@100ms') {
            renderOrderbook(payload.data);
        }
    };

    function renderOrderbook(data) {
        const asksEl = document.getElementById('ob-asks');
        const bidsEl = document.getElementById('ob-bids');
        const spreadEl = document.getElementById('ob-spread');
        
        let asksHtml = '';
        // Asks (Reverse so highest is at top)
        [...data.a].reverse().slice(-5).forEach(ask => {
            asksHtml += `<div class="ob-row"><span>${parseFloat(ask[0]).toFixed(1)}</span><span class="ob-amt">${parseFloat(ask[1]).toFixed(3)}</span></div>`;
        });
        asksEl.innerHTML = asksHtml;

        let bidsHtml = '';
        data.b.slice(0, 5).forEach(bid => {
            bidsHtml += `<div class="ob-row"><span>${parseFloat(bid[0]).toFixed(1)}</span><span class="ob-amt">${parseFloat(bid[1]).toFixed(3)}</span></div>`;
        });
        bidsEl.innerHTML = bidsHtml;

        if(data.a[0] && data.b[0]) {
            const spread = parseFloat(data.a[0][0]) - parseFloat(data.b[0][0]);
            spreadEl.innerText = spread.toFixed(2);
        }
    }

    // Engine State Polling
    async function pollEngineState() {
        try {
            const res = await fetch('/api/algo/state');
            const state = await res.json();
            
            // Render Neural Gauges
            rsiVal.innerText = state.rsi.toFixed(2);
            const rsiPct = Math.min(Math.max(state.rsi, 0), 100);
            rsiBar.style.width = `${rsiPct}%`;
            if (state.rsi < 35) rsiBar.style.backgroundColor = '#00ff88'; // Buy Zone
            else if (state.rsi > 65) rsiBar.style.backgroundColor = '#ff3366'; // Sell Zone
            else rsiBar.style.backgroundColor = '#888';

            const macdDiff = state.macd - state.macd_signal;
            macdVal.innerText = macdDiff.toFixed(2);
            macdBar.style.width = macdDiff > 0 ? '75%' : '25%';
            macdBar.style.backgroundColor = macdDiff > 0 ? '#00ff88' : '#ff3366';

            // BB
            let bbPos = 50;
            if (state.bb_upper > state.bb_lower) {
                bbPos = ((state.price - state.bb_lower) / (state.bb_upper - state.bb_lower)) * 100;
            }
            bbPos = Math.min(Math.max(bbPos, 0), 100);
            bbVal.innerText = `${bbPos.toFixed(1)}%`;
            bbBar.style.width = `${bbPos}%`;
            bbBar.style.backgroundColor = bbPos < 10 ? '#00ff88' : (bbPos > 90 ? '#ff3366' : '#888');

            // Panic Mode
            if (state.panic_mode) {
                bodyEl.classList.add('panic-mode');
                coreStatus.className = 'core-status panic';
                coreStatus.innerText = '⚠ PANIC MODE ACTIVE ⚠';
            } else {
                bodyEl.classList.remove('panic-mode');
                const isAlgoOn = document.getElementById('algo-switch').checked;
                coreStatus.className = isAlgoOn ? 'core-status active' : 'core-status';
                coreStatus.innerText = isAlgoOn ? 'SYSTEM ARMED & ANALYZING' : 'SYSTEM STANDBY';
            }

            // Position Tracker
            if (state.position) {
                posDataEl.innerHTML = `<div class="pos-active">
                    <div class="pos-row"><span style="color:${state.position === 'BUY' ? '#00ff88' : '#ff3366'}">${state.position}</span></div>
                    <div class="pos-row"><span>Status</span><span>Monitoring for Exit</span></div>
                </div>`;
            } else {
                posDataEl.innerHTML = 'NO ACTIVE POSITIONS';
            }

        } catch (e) {}
    }
    setInterval(pollEngineState, 1000);

    // Logs Polling
    async function pollLogs() {
        try {
            const res = await fetch('/api/logs');
            const data = await res.json();
            if (data.logs) {
                statusMsg.innerHTML = data.logs.map(l => {
                    let cls = '';
                    if(l.includes('BUY')) cls = 'buy';
                    if(l.includes('SELL')) cls = 'sell';
                    if(l.includes('PANIC') || l.includes('ERROR')) cls = 'panic';
                    return `<div class="log-entry ${cls}">${l}</div>`;
                }).join('');
                statusMsg.scrollTop = statusMsg.scrollHeight;
            }
        } catch (e) {}
    }
    setInterval(pollLogs, 2000);

    // Balance Polling
    async function fetchBalance() {
        try {
            const res = await fetch('/api/balance');
            const data = await res.json();
            if (data.availableMargin) {
                marginEl.innerText = `${parseFloat(data.availableMargin).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})} USDT`;
            }
        } catch (e) { }
    }
    fetchBalance();
    setInterval(fetchBalance, 10000);

    // Toggles & Presets
    document.getElementById('algo-switch').addEventListener('change', async (e) => {
        await fetch('/api/algo/toggle', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ active: e.target.checked }) });
    });

    document.querySelectorAll('.preset-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.getElementById('quantity').value = e.target.getAttribute('data-val');
        });
    });

    // Panic Button
    document.getElementById('kill-switch').addEventListener('click', async () => {
        try {
            await fetch('/api/algo/panic', { method: 'POST' });
        } catch (e) { }
    });

    // Manual Trade
    async function submitTrade(side) {
        const payload = {
            symbol: 'BTCUSDT', side: side, type: document.getElementById('order-type').value,
            quantity: document.getElementById('quantity').value
        };
        try {
            await fetch('/api/trade', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
            fetchBalance();
        } catch (error) { }
    }
    document.getElementById('buy-btn').addEventListener('click', () => submitTrade('BUY'));
    document.getElementById('sell-btn').addEventListener('click', () => submitTrade('SELL'));
});
