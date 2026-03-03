(function() {
    if (document.getElementById('solace-top-rail')) return;

    /* ── Top Rail: Value Dashboard + Delight Engine ─────────────────────
       Shows: [logo] [dot] [STATE] [app] | [rotating stats + delight]
       Replaces boring URL with value created by Solace Browser.
       Channel [7] — Context + Tools. Rung: 65537.
    ──────────────────────────────────────────────────────────────────── */

    var rail = document.createElement('div');
    rail.id = 'solace-top-rail';
    rail.style.cssText = 'position:fixed;top:0;left:0;right:0;height:32px;background:linear-gradient(90deg,#081019 0%,#0d1b2a 50%,#081019 100%);color:#fff;display:flex;align-items:center;padding:0 12px;font-family:system-ui;font-size:12px;z-index:99999;box-shadow:0 2px 8px rgba(0,0,0,0.4);';

    /* Left: Home button + State */
    var leftGroup = document.createElement('div');
    leftGroup.style.cssText = 'display:flex;align-items:center;flex-shrink:0;gap:6px;';

    /* YinYang home button — always takes you back to Solace Browser home */
    var homeBtn = document.createElement('button');
    homeBtn.id = 'solace-home-btn';
    homeBtn.style.cssText = 'background:none;border:none;cursor:pointer;padding:0 4px 0 0;display:flex;align-items:center;gap:4px;color:#64c4ff;font-size:11px;font-weight:700;letter-spacing:0.03em;opacity:0.9;transition:opacity 0.2s;';
    homeBtn.title = 'Back to Solace Browser Home';
    var yyGlyph = document.createElement('span');
    yyGlyph.style.cssText = 'font-size:15px;line-height:1;';
    yyGlyph.textContent = '\u262F';
    var homeLabel = document.createElement('span');
    homeLabel.textContent = 'Solace';
    homeBtn.appendChild(yyGlyph);
    homeBtn.appendChild(homeLabel);
    homeBtn.addEventListener('mouseenter', function() { homeBtn.style.opacity = '1'; });
    homeBtn.addEventListener('mouseleave', function() { homeBtn.style.opacity = '0.9'; });
    homeBtn.addEventListener('click', function() {
        /* Navigate to Solace Browser home — works both locally and via cloud */
        var homeUrl = 'http://localhost:3000/home.html';
        if (location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') {
            homeUrl = 'http://localhost:3000/home.html';
        }
        window.location.href = homeUrl;
    });
    leftGroup.appendChild(homeBtn);

    /* Separator */
    var sep = document.createElement('span');
    sep.style.cssText = 'color:#1e3048;font-size:14px;';
    sep.textContent = '\u2502';
    leftGroup.appendChild(sep);

    var dot = document.createElement('span');
    dot.id = 'solace-state-dot';
    dot.style.cssText = 'margin-right:8px;width:8px;height:8px;border-radius:50%;background:#666;display:inline-block;transition:background 0.3s;';
    leftGroup.appendChild(dot);

    var stateText = document.createElement('span');
    stateText.id = 'solace-state-text';
    stateText.style.cssText = 'font-weight:600;letter-spacing:0.5px;';
    stateText.textContent = 'IDLE';
    leftGroup.appendChild(stateText);

    var appLabel = document.createElement('span');
    appLabel.id = 'solace-app-label';
    appLabel.style.cssText = 'margin-left:8px;opacity:0.7;font-size:11px;';
    leftGroup.appendChild(appLabel);

    rail.appendChild(leftGroup);

    /* Center: Rotating value stats + delight */
    var centerGroup = document.createElement('div');
    centerGroup.id = 'solace-value-display';
    centerGroup.style.cssText = 'margin-left:auto;margin-right:auto;display:flex;align-items:center;gap:16px;opacity:0.85;font-size:11px;';
    rail.appendChild(centerGroup);

    /* Right: Compact page indicator */
    var rightGroup = document.createElement('span');
    rightGroup.id = 'solace-page-indicator';
    rightGroup.style.cssText = 'margin-left:auto;opacity:0.4;font-size:10px;flex-shrink:0;max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';
    rail.appendChild(rightGroup);

    document.documentElement.appendChild(rail);
    document.body.style.marginTop = '32px';

    /* ── Session Stats (updated via postMessage) ────────────────────── */
    var stats = {
        pages_visited: 0,
        llm_calls: 0,
        tokens_used: 0,
        cost_usd: 0,
        tokens_saved: 0,
        savings_pct: 0,
        recipes_replayed: 0,
        evidence_captured: 0,
        session_start: Date.now()
    };

    /* ── Delight Content (rotating) ─────────────────────────────────── */
    var DELIGHT_POOL = [
        /* Fun facts */
        {type:'fact', icon:'\u2728', text:'Recipe replay costs $0.001 vs $0.08 for LLM — 80x cheaper'},
        {type:'fact', icon:'\ud83d\udcca', text:'PZip compresses evidence 66:1 — storage costs $0.00032/user/mo'},
        {type:'fact', icon:'\ud83d\udd12', text:'Your evidence is SHA-256 hash-chained — tamper-evident by design'},
        {type:'fact', icon:'\ud83c\udf0d', text:'OAuth3: the first open standard for AI agency delegation'},
        {type:'fact', icon:'\ud83d\udee1\ufe0f', text:'Sealed store: 0% malware (vs 20% in open plugin stores)'},
        {type:'fact', icon:'\u26a1', text:'LLM called ONCE at preview, never during execution — 50% cheaper'},
        {type:'fact', icon:'\ud83c\udfc6', text:'Part 11 Architected: evidence chains exceed FDA requirements'},
        /* Tips */
        {type:'tip', icon:'\ud83d\udca1', text:'Tip: Use --part11 flag for automatic evidence capture'},
        {type:'tip', icon:'\ud83d\udca1', text:'Tip: Recipes get cheaper every time — first run discovers, replays are free'},
        {type:'tip', icon:'\ud83d\udca1', text:'Tip: E-sign any document with /api/v1/esign/token'},
        {type:'tip', icon:'\ud83d\udca1', text:'Tip: Push alerts notify you when tasks complete — even in other tabs'},
        /* Motivational */
        {type:'quote', icon:'\ud83d\udc09', text:'"Absorb what is useful, discard what is useless" — Bruce Lee'},
        {type:'quote', icon:'\ud83d\udc09', text:'"Intelligence = Memory \u00d7 Care \u00d7 Iteration" — SW5.0'},
        {type:'quote', icon:'\ud83d\udc09', text:'"Trust me is not evidence. Only the record is evidence." — Solace'},
        {type:'quote', icon:'\ud83d\udc09', text:'"Evidence is not a feature. It\'s how the system breathes."'},
        /* Feature updates */
        {type:'update', icon:'\ud83d\ude80', text:'New: OAuth3 e-signatures with hash-chained evidence'},
        {type:'update', icon:'\ud83d\ude80', text:'New: 5 pricing tiers from $0 to $188/mo'},
        {type:'update', icon:'\ud83d\ude80', text:'New: Push alerts — toast, popup, and takeover channels'},
        {type:'update', icon:'\ud83d\ude80', text:'New: Download standalone binary at solaceagi.com/download'}
    ];

    var delightIndex = 0;
    var showingStats = true;

    function formatCost(usd) {
        if (usd < 0.01) return '$0.00';
        return '$' + usd.toFixed(2);
    }

    function formatTokens(n) {
        if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
        if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
        return n.toString();
    }

    function sessionDuration() {
        var secs = Math.floor((Date.now() - stats.session_start) / 1000);
        var mins = Math.floor(secs / 60);
        var hrs = Math.floor(mins / 60);
        if (hrs > 0) return hrs + 'h ' + (mins % 60) + 'm';
        if (mins > 0) return mins + 'm ' + (secs % 60) + 's';
        return secs + 's';
    }

    function renderStats() {
        var display = document.getElementById('solace-value-display');
        if (!display) return;

        if (showingStats) {
            /* Show value metrics */
            var items = [
                '\ud83d\udcc4 ' + stats.pages_visited + ' pages',
                '\ud83e\udde0 ' + stats.llm_calls + ' LLM calls',
                '\ud83d\udcb0 ' + formatCost(stats.cost_usd),
                '\ud83d\udcb5 ' + stats.savings_pct + '% saved',
                '\u23f1\ufe0f ' + sessionDuration()
            ];

            if (stats.recipes_replayed > 0) {
                items.push('\ud83d\udd01 ' + stats.recipes_replayed + ' replays');
            }
            if (stats.evidence_captured > 0) {
                items.push('\ud83d\udcdd ' + stats.evidence_captured + ' evidence');
            }

            while (display.firstChild) display.removeChild(display.firstChild);
            items.forEach(function(item) {
                var span = document.createElement('span');
                span.textContent = item;
                span.style.cssText = 'white-space:nowrap;';
                display.appendChild(span);
            });
        } else {
            /* Show delight content */
            var d = DELIGHT_POOL[delightIndex % DELIGHT_POOL.length];
            while (display.firstChild) display.removeChild(display.firstChild);
            var span = document.createElement('span');
            span.textContent = d.icon + ' ' + d.text;
            span.style.cssText = 'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:600px;transition:opacity 0.5s;';
            display.appendChild(span);
            delightIndex++;
        }
    }

    /* Alternate between stats and delight every 8 seconds */
    renderStats();
    setInterval(function() {
        showingStats = !showingStats;
        renderStats();
    }, 8000);

    /* Update page indicator */
    var pageEl = document.getElementById('solace-page-indicator');
    if (pageEl) pageEl.textContent = location.hostname;

    /* ── State Colors + Pulse ───────────────────────────────────────── */
    var COLOR_MAP = {
        TRIGGER:'#4a9eff', INTENT:'#4a9eff', BUDGET_CHECK:'#4a9eff',
        PREVIEW:'#4a9eff', PREVIEW_READY:'#f5a623', APPROVED:'#4a9eff',
        REJECTED:'#e74c3c', TIMEOUT:'#e74c3c', COOLDOWN:'#f5a623',
        E_SIGN:'#4a9eff', SEALED:'#4a9eff', EXECUTING:'#4a9eff',
        DONE:'#27ae60', FAILED:'#e74c3c', BLOCKED:'#e74c3c',
        SEALED_ABORT:'#e74c3c', EVIDENCE_SEAL:'#27ae60',
        idle:'#666', listening:'#64c4ff', processing:'#64c4ff',
        intent_classified:'#4a9eff', preview_generating:'#f5a623',
        preview_ready:'#f5a623', cooldown:'#f5a623', approved:'#27ae60',
        sealed:'#27ae60', executing:'#27ae60', done:'#27ae60',
        blocked:'#e74c3c', error:'#e74c3c'
    };

    var PULSE_STATES = ['EXECUTING','PREVIEW','BUDGET_CHECK','processing','preview_generating'];

    /* ── Message Listener (state + stats updates) ───────────────────── */
    window.addEventListener('message', function(e) {
        if (!e.data) return;

        /* FSM state updates */
        if (e.data.type === 'yinyang_state') {
            var dotEl = document.getElementById('solace-state-dot');
            var textEl = document.getElementById('solace-state-text');
            var labelEl = document.getElementById('solace-app-label');
            if (!dotEl || !textEl) return;

            var state = e.data.state || 'IDLE';
            textEl.textContent = state;
            if (labelEl) labelEl.textContent = e.data.app_name || '';
            dotEl.style.background = COLOR_MAP[state] || '#666';

            if (PULSE_STATES.indexOf(state) >= 0) {
                dotEl.style.animation = 'solace-pulse 1s infinite';
            } else {
                dotEl.style.animation = 'none';
            }
        }

        /* Stats updates from backend */
        if (e.data.type === 'yinyang_stats') {
            if (e.data.pages_visited !== undefined) stats.pages_visited = e.data.pages_visited;
            if (e.data.llm_calls !== undefined) stats.llm_calls = e.data.llm_calls;
            if (e.data.tokens_used !== undefined) stats.tokens_used = e.data.tokens_used;
            if (e.data.cost_usd !== undefined) stats.cost_usd = e.data.cost_usd;
            if (e.data.tokens_saved !== undefined) stats.tokens_saved = e.data.tokens_saved;
            if (e.data.savings_pct !== undefined) stats.savings_pct = e.data.savings_pct;
            if (e.data.recipes_replayed !== undefined) stats.recipes_replayed = e.data.recipes_replayed;
            if (e.data.evidence_captured !== undefined) stats.evidence_captured = e.data.evidence_captured;
            renderStats();
        }
    });

    /* Track page visits */
    stats.pages_visited++;
    var observer = new MutationObserver(function() {
        var newUrl = location.hostname;
        var indEl = document.getElementById('solace-page-indicator');
        if (indEl && indEl.textContent !== newUrl) {
            indEl.textContent = newUrl;
            stats.pages_visited++;
        }
    });
    observer.observe(document, {childList: true, subtree: true});

    /* Inject animations */
    var style = document.createElement('style');
    style.textContent = '@keyframes solace-pulse{0%,100%{opacity:1}50%{opacity:0.4}}';
    document.head.appendChild(style);
})();
