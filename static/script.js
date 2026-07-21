document.addEventListener('DOMContentLoaded', () => {
    // 3D Parallax Mouse Tracking
    const scene = document.getElementById('spatial-scene');
    document.addEventListener('mousemove', (e) => {
        const x = (e.clientX / window.innerWidth - 0.5) * 10; // max 10 deg rotation
        const y = (e.clientY / window.innerHeight - 0.5) * -10;
        scene.style.transform = `rotateY(${x}deg) rotateX(${y}deg)`;
    });

    // Elements
    const livePriceEl = document.getElementById('live-price');
    const marginEl = document.getElementById('available-margin');
    const statusMsg = document.getElementById('status-message');
    const posDataEl = document.getElementById('pos-data');
    
    // Gauges
    const rsiVal = document.getElementById('rsi-val');
    const rsiArc = document.getElementById('rsi-arc');
    const macdVal = document.getElementById('macd-val');
    const macdArc = document.getElementById('macd-arc');
    const bbVal = document.getElementById('bb-val');
    const bbArc = document.getElementById('bb-bar'); // bb-arc
    const coreStatus = document.getElementById('core-status');
    const bodyEl = document.getElementById('app-body');

    // SVG Math Engine (Circumference = 2 * PI * r)
    // r = 40, C = 251.2
    function setGauge(arcEl, percent, color) {
        if(!arcEl) return;
        const radius = 40;
        const circumference = 2 * Math.PI * radius;
        // SVG starts at 0, offset pushes it back.
        const offset = circumference - (percent / 100) * circumference;
        arcEl.style.strokeDashoffset = offset;
        arcEl.style.stroke = color;
    }

    // Chart
    let chart, candleSeries;
    try {
        const chartContainer = document.getElementById('chart-container');
        chart = LightweightCharts.createChart(chartContainer, {
            autoSize: true,
            layout: { background: { type: 'solid', color: 'transparent' }, textColor: '#777777' },
            grid: { vertLines: { color: 'rgba(255,255,255,0.02)' }, horzLines: { color: 'rgba(255,255,255,0.02)' } },
            crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
            timeScale: { timeVisible: true, secondsVisible: false },
        });
        candleSeries = chart.addCandlestickSeries({
            upColor: '#00ff88', downColor: '#ff3366', borderDownColor: '#ff3366', borderUpColor: '#00ff88', wickDownColor: '#ff3366', wickUpColor: '#00ff88',
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

    // WebSocket (Price & Orderbook)
    try {
        const ws = new WebSocket('wss://stream.binancefuture.com/stream?streams=btcusdt@kline_1m/btcusdt@depth10@100ms');
        let lastPrice = 0;
        ws.onmessage = (event) => {
            const payload = JSON.parse(event.data);
            if (payload.stream === 'btcusdt@kline_1m') {
                const k = payload.data.k;
                const c = parseFloat(k.c);
                if(candleSeries) candleSeries.update({ time: k.t / 1000, open: parseFloat(k.o), high: parseFloat(k.h), low: parseFloat(k.l), close: c });
                
                livePriceEl.innerText = c.toFixed(2);
                if (c > lastPrice) { livePriceEl.className = 'stat-value flash-up'; setTimeout(()=> livePriceEl.className = 'stat-value text-cyan', 400); }
                else if (c < lastPrice) { livePriceEl.className = 'stat-value flash-down'; setTimeout(()=> livePriceEl.className = 'stat-value text-cyan', 400); }
                lastPrice = c;
            }
            else if (payload.stream === 'btcusdt@depth10@100ms') {
                renderOrderbook(payload.data);
            }
        };
    } catch(e) {}

    function renderOrderbook(data) {
        const asksEl = document.getElementById('ob-asks');
        const bidsEl = document.getElementById('ob-bids');
        const spreadEl = document.getElementById('ob-spread');
        
        try {
            let asksHtml = '';
            if(data.a && data.a.length) {
                [...data.a].reverse().slice(-5).forEach(ask => {
                    asksHtml += `<div class="ob-row"><span>${parseFloat(ask[0]).toFixed(1)}</span><span class="ob-amt">${parseFloat(ask[1]).toFixed(3)}</span></div>`;
                });
                asksEl.innerHTML = asksHtml;
            }

            let bidsHtml = '';
            if(data.b && data.b.length) {
                data.b.slice(0, 5).forEach(bid => {
                    bidsHtml += `<div class="ob-row"><span>${parseFloat(bid[0]).toFixed(1)}</span><span class="ob-amt">${parseFloat(bid[1]).toFixed(3)}</span></div>`;
                });
                bidsEl.innerHTML = bidsHtml;
            }

            if(data.a && data.a[0] && data.b && data.b[0]) {
                const spread = parseFloat(data.a[0][0]) - parseFloat(data.b[0][0]);
                spreadEl.innerText = spread.toFixed(2);
            }
        } catch(e) {}
    }

    // Engine State Polling
    async function pollEngineState() {
        try {
            const res = await fetch('/api/algo/state');
            const state = await res.json();
            
            // RSI
            rsiVal.innerText = state.rsi.toFixed(1);
            let rsiColor = '#777';
            if(state.rsi < 35) rsiColor = '#00ff88';
            else if (state.rsi > 65) rsiColor = '#ff3366';
            setGauge(rsiArc, state.rsi, rsiColor);

            // MACD
            const macdDiff = state.macd - state.macd_signal;
            macdVal.innerText = macdDiff > 0 ? '+'+macdDiff.toFixed(2) : macdDiff.toFixed(2);
            let macdPct = 50 + (macdDiff * 10);
            macdPct = Math.min(Math.max(macdPct, 0), 100);
            setGauge(macdArc, macdPct, macdDiff > 0 ? '#00ff88' : '#ff3366');

            // BB
            let bbPos = 50;
            if (state.bb_upper > state.bb_lower) {
                bbPos = ((state.price - state.bb_lower) / (state.bb_upper - state.bb_lower)) * 100;
            }
            bbPos = Math.min(Math.max(bbPos, 0), 100);
            bbVal.innerText = bbPos.toFixed(0);
            const bbEl = document.getElementById('bb-arc');
            setGauge(bbEl, bbPos, bbPos < 10 ? '#00ff88' : (bbPos > 90 ? '#ff3366' : '#777'));

            // Panic Mode
            if (state.panic_mode) {
                bodyEl.classList.add('panic-mode');
                coreStatus.className = 'core-status active';
                coreStatus.style.color = '#ff0000';
                coreStatus.innerText = '⚠ PANIC MODE ACTIVE ⚠';
            } else {
                bodyEl.classList.remove('panic-mode');
                const isAlgoOn = document.getElementById('algo-switch').checked;
                coreStatus.className = isAlgoOn ? 'core-status active' : 'core-status';
                coreStatus.style.color = isAlgoOn ? '#00ff88' : '#777';
                coreStatus.innerText = isAlgoOn ? 'SYSTEM ARMED' : 'SYSTEM STANDBY';
            }

            // Position Tracker
            if (state.position) {
                posDataEl.innerHTML = `<div class="pos-active">
                    <div class="pos-row"><span style="color:${state.position === 'BUY' ? '#00ff88' : '#ff3366'}">${state.position}</span></div>
                    <div class="pos-row"><span>Status</span><span>Monitoring</span></div>
                </div>`;
            } else {
                posDataEl.innerHTML = 'NONE';
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
