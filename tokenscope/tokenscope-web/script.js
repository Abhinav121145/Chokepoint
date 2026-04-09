const API_BASE = "http://127.0.0.1:8000";

// 1. LOGIN
function handleLogin() {
    const email = document.getElementById('login-email').value;
    const pass = document.getElementById('login-pass').value;
    if (email && pass) {
        document.getElementById('login-page').style.display = 'none';
        document.getElementById('main-app').classList.remove('hidden');
    } else {
        alert("Enter credentials.");
    }
}

// 2. TABS
function switchTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
    document.getElementById(`tab-${tabId}`).classList.remove('hidden');
    document.getElementById(`nav-${tabId}`).classList.add('active');
}

// 3. ANALYZE
async function processAnalyze() {
    const prompt = document.getElementById('analyzeInput').value;
    if (!prompt) return;

    try {
        const res = await fetch(`${API_BASE}/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: prompt })
        });
        const data = await res.json();
        
        document.getElementById('analyze-results').classList.remove('hidden');
        
        // Update Stats
        document.getElementById('m-in').innerText = data.metrics.prompt_tokens;
        document.getElementById('m-out').innerText = data.metrics.response_tokens;
        document.getElementById('m-total').innerText = data.metrics.total_tokens;
        document.getElementById('m-cost').innerText = `$${data.metrics.cost_estimate.toFixed(4)}`;

        // Heatmap
        const heatmap = document.getElementById('heatmap');
        heatmap.innerHTML = '';
        data.analysis.visualization.forEach(word => {
            const span = document.createElement('span');
            span.innerText = word.word;
            let color = 'bg-gray-800 text-gray-500';
            if(word.level === 'high') color = 'bg-orange-600 text-white';
            if(word.level === 'medium') color = 'bg-orange-900/40 text-orange-200 border border-orange-800';
            span.className = `px-2 py-1 rounded text-sm font-medium ${color}`;
            heatmap.appendChild(span);
        });

        document.getElementById('trimmedText').innerText = data.analysis.trimmed_prompt;
        const savings = Math.round((data.metrics.tokens_saved / data.metrics.prompt_tokens) * 100);
        document.getElementById('m-saved').innerText = `${savings}%`;

        // Breakdown
        const sys = 56, ctx = 409, qry = data.metrics.prompt_tokens;
        const total = sys + ctx + qry;
        document.getElementById('bar-system').style.width = `${(sys/total)*100}%`;
        document.getElementById('bar-context').style.width = `${(ctx/total)*100}%`;
        document.getElementById('bar-query').style.width = `${(qry/total)*100}%`;
        document.getElementById('val-system').innerText = `${sys} tokens`;
        document.getElementById('val-context').innerText = `${ctx} tokens`;
        document.getElementById('val-query').innerText = `${qry} tokens`;

        addToHistory(prompt, data.metrics.total_tokens);
    } catch (err) {
        console.error("Fetch failed", err);
    }
}

// 4. COMPARE
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
    container.innerHTML = `
        <div class="bg-orange-900/10 border border-orange-500/30 p-4 rounded-xl mb-6 text-center text-orange-500 font-bold">
            Winner: ${data.result.winner}
        </div>
        <div class="grid grid-cols-2 gap-4">
            <div class="stat-card border ${data.result.winner === 'Prompt 1' ? 'border-orange-500' : 'border-gray-800'}">
                <h4 class="text-white font-bold mb-2">Prompt A</h4>
                <p class="text-xs">Tokens: ${data.prompt1.total_tokens}</p>
            </div>
            <div class="stat-card border ${data.result.winner === 'Prompt 2' ? 'border-orange-500' : 'border-gray-800'}">
                <h4 class="text-white font-bold mb-2">Prompt B</h4>
                <p class="text-xs">Tokens: ${data.prompt2.total_tokens}</p>
            </div>
        </div>
    `;
}

// 5. MISC
async function downloadPDF() {
    const prompt = document.getElementById('analyzeInput').value;
    const res = await fetch(`${API_BASE}/download-report`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt })
    });
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = "Report.pdf"; a.click();
}

function addToHistory(p, t) {
    const list = document.getElementById('history-list');
    if (list.querySelector('p')) list.innerHTML = '';
    const div = document.createElement('div');
    div.className = "bg-[#1c1f26] border border-gray-800 p-3 rounded-xl flex justify-between items-center text-xs";
    div.innerHTML = `<span>${p.substring(0, 30)}...</span><span class="text-orange-500">${t} tokens</span>`;
    list.prepend(div);
}