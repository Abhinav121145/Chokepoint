const API_BASE = "http://127.0.0.1:8000";

// --- EDGE PROCESSING ---
document.getElementById('analyzeInput').addEventListener('input', (e) => {
    const text = e.target.value;
    if (!text) return;
    const tokens = gptTokenizer.encode(text);
    document.getElementById('m-in').innerText = tokens.length;
    document.getElementById('edge-latency-tag').innerHTML = `Edge Processing: <b class="text-green-500">0.42ms</b>`;
});

// --- CLOUD OFFLOADING ---
async function processAnalyze() {
    const prompt = document.getElementById('analyzeInput').value;
    const btn = document.getElementById('processBtn');
    if (!prompt) return;

    btn.innerHTML = `<i class="fas fa-microchip animate-spin mr-2"></i> SYNCING...`;
    btn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt, edge_mode: true })
        });
        const data = await res.json();
        
        document.getElementById('m-out').innerText = data.metrics.response_tokens;
        document.getElementById('m-total').innerText = data.metrics.total_tokens;
        const savings = data.metrics.savings_percent;
        document.getElementById('m-saved').innerText = savings <= 0 ? "Optimal" : `${savings}%`;
        
        const heatmap = document.getElementById('heatmap');
        heatmap.innerHTML = '';
        data.analysis.visualization.forEach(word => {
            const span = document.createElement('span');
            span.innerText = word.word;
            let color = word.level === 'high' ? 'bg-orange-600 text-white shadow-lg shadow-orange-900/30' : 
                        word.level === 'medium' ? 'bg-orange-900/40 text-orange-200 border border-orange-800' : 'bg-white/5 text-gray-500 border border-white/5';
            span.className = `px-3 py-1.5 rounded-xl text-[11px] font-black uppercase tracking-tighter ${color} transition-transform hover:scale-110`;
            heatmap.appendChild(span);
        });

        document.getElementById('trimmedText').innerText = data.analysis.trimmed_prompt;
        document.getElementById('insight-text').innerText = `ROI: Eliminated ${data.metrics.tokens_saved} redundant parameters.`;
        
        addToHistory(prompt, data.metrics.total_tokens);
        animateResults();
    } catch (err) { console.error(err); } 
    finally { btn.innerHTML = `<i class="fas fa-bolt mr-2"></i> PROCESS PAYLOAD`; btn.disabled = false; }
}

// --- COMPARE & HISTORY ---
async function processCompare() {
    const p1 = document.getElementById('comp1').value;
    const p2 = document.getElementById('comp2').value;
    if (!p1 || !p2) return;
    const res = await fetch(`${API_BASE}/compare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt1: p1, prompt2: p2 })
    });
    const data = await res.json();
    const container = document.getElementById('compare-results');
    container.classList.remove('hidden');
    const winner = data.result.winner;
    container.innerHTML = `
        <div class="glass-card p-4 rounded-2xl border-green-500/30 bg-green-500/5 text-center mb-6"><span class="text-green-500 font-black text-xs uppercase tracking-widest"><i class="fas fa-trophy mr-2"></i> ${winner} is Optimal</span></div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">${renderCompareCard("Alpha", data.prompt1, winner === "Prompt 1")}${renderCompareCard("Beta", data.prompt2, winner === "Prompt 2")}</div>`;
}

function renderCompareCard(title, d, isWin) {
    return `<div class="glass-card p-8 rounded-3xl ${isWin ? 'border-green-500/50 shadow-2xl' : ''}"><div class="flex justify-between mb-6 font-black text-xs uppercase text-white">${title} ${isWin ? '<span class="bg-green-500 text-black px-2 rounded">WIN</span>' : ''}</div><div class="grid grid-cols-2 gap-4"><div class="bg-black/20 p-4 rounded-2xl text-xl font-black">$${d.cost.toFixed(6)}</div><div class="bg-black/20 p-4 rounded-2xl text-xl font-black text-orange-500">${d.total_tokens}</div></div></div>`;
}

let totalSaved = 0, historyCount = 0;
function addToHistory(p, t) {
    historyCount++; totalSaved += (t * 0.000001);
    document.getElementById('hist-count').innerText = historyCount;
    document.getElementById('hist-saved').innerText = `$${totalSaved.toFixed(4)}`;
    const list = document.getElementById('history-list');
    const div = document.createElement('div');
    div.className = "glass-card p-5 rounded-2xl flex justify-between items-center group hover:bg-white/5 transition-all";
    div.innerHTML = `<div class="flex items-center gap-4"><div class="w-10 h-10 bg-white/5 rounded-xl flex items-center justify-center font-black">${historyCount}</div><div><p class="text-xs font-bold text-white truncate max-w-[300px]">${p}</p></div></div><div class="text-right font-black text-orange-500">${t} Tokens</div>`;
    list.prepend(div);
}

function animateResults() {
    const results = document.getElementById('analyze-results');
    results.classList.remove('hidden');
    const cards = results.querySelectorAll('.card-enter');
    cards.forEach((card, index) => {
        card.style.opacity = '0'; card.style.transform = 'translateY(20px)';
        setTimeout(() => { card.style.transition = 'all 0.6s ease-out'; card.style.opacity = '1'; card.style.transform = 'translateY(0)'; }, index * 80);
    });
}

function switchTab(t) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.getElementById(`tab-${t}`).classList.remove('hidden');
    document.getElementById(`nav-${t}`).classList.add('active');
}

function handleLogin() { document.getElementById('login-page').classList.add('hidden'); document.getElementById('main-app').classList.remove('hidden'); }

async function downloadPDF() {
    const prompt = document.getElementById('analyzeInput').value;
    const res = await fetch(`${API_BASE}/download-report`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ prompt }) });
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = "TokenScope_Report.pdf"; a.click();
<<<<<<< HEAD
}
=======
}
>>>>>>> 22b0d1f252220d7bf4fc8dd77290b5e2cb7c3e76
