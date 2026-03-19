// Diagram: 04-hub-lifecycle
// Extracted from styleguide.html inline <script> blocks
(function() {
  'use strict';

  // ─── App Icons Grid (dynamically generated) ───
  (function(){
    var icons = [
      'amazon','aws','bluesky','chatgpt','claude','discord','dropbox',
      'facebook','gemini','github','gmail','google-calendar',
      'google-drive','google-search','hackernews','instagram','jira',
      'line','linkedin','mastodon','medium','messenger',
      'netflix','notion','openai','pinterest','podcast','reddit',
      'shopify','signal','skype','slack','snapchat','spotify',
      'stripe','substack','teams','telegram','threads','tiktok',
      'trello','twitch','twitter','viber','weather','wechat',
      'whats-app','x','youtube','zoom'
    ];
    var grid = document.getElementById('app-icons-grid');
    if (!grid) return;
    icons.forEach(function(name) {
      var ext = ['gmail','instagram','medium','pinterest',
                 'podcast','reddit','twitter','weather','whats-app','youtube']
                 .indexOf(name) >= 0 ? 'jpg' : 'png';
      var div = document.createElement('div');
      div.className = 'sg-icon-cell';
      var img = document.createElement('img');
      img.src = 'icons/apps/' + name + '.' + ext;
      img.className = 'sg-icon-img';
      img.onerror = function() { img.style.display = 'none'; };
      div.appendChild(img);
      var br = document.createElement('br');
      div.appendChild(br);
      var label = document.createElement('small');
      label.className = 'sb-text-muted sg-icon-label';
      label.textContent = name;
      div.appendChild(label);
      grid.appendChild(div);
    });
  })();

  // ─── Tab switching (from solace-browser-backup/schedule-core.js) ───
  function setupTabs(container) {
    var tabs = [].slice.call(container.querySelectorAll('.sb-tab'));
    var panels = container.parentElement.querySelectorAll('.sb-tab-panel');

    tabs.forEach(function(btn, idx) {
      btn.addEventListener('click', function() {
        tabs.forEach(function(b) {
          b.classList.toggle('sb-tab--active', b === btn);
          b.setAttribute('aria-selected', b === btn);
        });
        panels.forEach(function(p) {
          p.hidden = p.id !== 'panel-' + btn.dataset.view;
        });
      });

      btn.addEventListener('keydown', function(e) {
        var next;
        if (e.key === 'ArrowRight') next = tabs[(idx + 1) % tabs.length];
        else if (e.key === 'ArrowLeft') next = tabs[(idx - 1 + tabs.length) % tabs.length];
        if (next) { e.preventDefault(); next.focus(); next.click(); }
      });
    });
  }

  var tabContainers = document.querySelectorAll('.sb-tabs');
  tabContainers.forEach(setupTabs);

  // ─── Hover-edit (from crio study_data_template pattern) ───
  // Click on text OR pen icon → shows input, auto-focus
  // Blur or Enter → saves, hides input, updates display text
  // Escape → cancels, restores original value
  document.querySelectorAll('.sb-editable').forEach(function(el) {
    var display = el.querySelector('.sb-editable-display');
    var input = el.querySelector('.sb-editable-input');
    var pen = el.querySelector('.sb-editable-pen');

    function startEdit() {
      el.classList.add('sb-editable--editing');
      input.value = display.textContent;
      input.focus();
      input.select();
    }

    // Click on display text → edit (crio pattern: click to edit)
    display.addEventListener('click', startEdit);

    // Click on pen icon → edit
    pen.addEventListener('click', startEdit);

    input.addEventListener('blur', function() {
      el.classList.remove('sb-editable--editing');
      display.textContent = input.value;
    });

    input.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') input.blur();
      if (e.key === 'Escape') { input.value = display.textContent; input.blur(); }
    });
  });

  // ─── Theme toggle ───
  document.querySelectorAll('.sb-theme-btn').forEach(function(btn) {
    btn.addEventListener('click', function() {
      document.documentElement.setAttribute('data-theme', btn.dataset.theme);
      document.querySelectorAll('.sb-theme-btn').forEach(function(b) {
        b.classList.toggle('sb-theme-btn--active', b === btn);
      });
    });
  });

  // ─── Sortable drag-and-drop ───
  (function() {
    var list = document.getElementById('sortable-list');
    if (!list) return;
    var dragItem = null;
    list.querySelectorAll('.sb-sortable-item').forEach(function(item) {
      item.addEventListener('dragstart', function(e) {
        dragItem = item;
        item.style.opacity = '0.4';
        e.dataTransfer.effectAllowed = 'move';
      });
      item.addEventListener('dragend', function() {
        item.style.opacity = '1';
        dragItem = null;
        list.querySelectorAll('.sb-sortable-item').forEach(function(el) { el.style.borderTop = ''; });
      });
      item.addEventListener('dragover', function(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        if (item !== dragItem) {
          item.style.borderTop = '3px solid var(--sb-accent)';
        }
      });
      item.addEventListener('dragleave', function() {
        item.style.borderTop = '';
      });
      item.addEventListener('drop', function(e) {
        e.preventDefault();
        item.style.borderTop = '';
        if (dragItem && item !== dragItem) {
          list.insertBefore(dragItem, item);
        }
      });
    });
  })();

  // ─── Mermaid init (render all <pre class="mermaid"> blocks) ───
  if (typeof mermaid !== 'undefined') {
    mermaid.initialize({ startOnLoad: true, theme: 'dark', themeVariables: {
      primaryColor: '#1a2d47', primaryTextColor: '#e8ecf2', primaryBorderColor: '#78b9ff',
      lineColor: '#78b9ff', secondaryColor: '#2d5016', tertiaryColor: '#4a2d16',
      fontFamily: 'Segoe UI, system-ui, sans-serif', fontSize: '14px'
    }});
  }
  // ─── Mermaid pan/zoom/fullscreen ───
  document.querySelectorAll('.sb-card .mermaid').forEach(function(pre) {
    var card = pre.closest('.sb-card');
    if (!card || pre.closest('.sb-mermaid-wrap')) return;
    var wrap = document.createElement('div');
    wrap.className = 'sb-mermaid-wrap';
    var inner = document.createElement('div');
    inner.className = 'sb-mermaid-inner';
    pre.parentNode.insertBefore(wrap, pre);
    inner.appendChild(pre);
    wrap.appendChild(inner);
    // Controls
    var controls = document.createElement('div');
    controls.className = 'sb-mermaid-controls';
    controls.innerHTML = '<button class="sb-mermaid-ctrl" data-action="zoomin" title="Zoom in">+</button>' +
      '<button class="sb-mermaid-ctrl" data-action="zoomout" title="Zoom out">−</button>' +
      '<button class="sb-mermaid-ctrl" data-action="reset" title="Reset">↺</button>' +
      '<button class="sb-mermaid-ctrl" data-action="fullscreen" title="Fullscreen">⛶</button>';
    wrap.appendChild(controls);
    // State
    var scale = 1, tx = 0, ty = 0, dragging = false, startX = 0, startY = 0;
    function applyTransform() { inner.style.transform = 'translate(' + tx + 'px,' + ty + 'px) scale(' + scale + ')'; }
    controls.addEventListener('click', function(e) {
      var action = e.target.dataset.action;
      if (action === 'zoomin') { scale = Math.min(scale * 1.3, 5); applyTransform(); }
      if (action === 'zoomout') { scale = Math.max(scale / 1.3, 0.2); applyTransform(); }
      if (action === 'reset') { scale = 1; tx = 0; ty = 0; applyTransform(); }
      if (action === 'fullscreen') {
        if (wrap.classList.contains('sb-mermaid-fullscreen')) {
          wrap.classList.remove('sb-mermaid-fullscreen');
          e.target.textContent = '⛶';
        } else {
          wrap.classList.add('sb-mermaid-fullscreen');
          e.target.textContent = '✕';
        }
      }
    });
    wrap.addEventListener('mousedown', function(e) { if (e.target.closest('.sb-mermaid-controls')) return; dragging = true; startX = e.clientX - tx; startY = e.clientY - ty; });
    document.addEventListener('mousemove', function(e) { if (!dragging) return; tx = e.clientX - startX; ty = e.clientY - startY; applyTransform(); });
    document.addEventListener('mouseup', function() { dragging = false; });
    wrap.addEventListener('wheel', function(e) { e.preventDefault(); scale *= e.deltaY < 0 ? 1.1 : 0.9; scale = Math.max(0.2, Math.min(5, scale)); applyTransform(); }, { passive: false });
  });

  window.renderMermaidEditor = function() {
    var code = document.getElementById('mermaid-editor').value;
    var preview = document.getElementById('mermaid-preview');
    preview.innerHTML = '';
    var id = 'mermaid-live-' + Date.now();
    preview.innerHTML = '<pre class="mermaid" id="' + id + '">' + code + '</pre>';
    if (typeof mermaid !== 'undefined') { mermaid.run({ nodes: [document.getElementById(id)] }); }
  };

  // ─── Toast notifications ───
  window.showToast = function(message, type) {
    var container = document.getElementById('toast-container');
    var toast = document.createElement('div');
    toast.className = 'sb-toast sb-toast--' + (type || 'success');
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(function() { toast.style.opacity = '0'; toast.style.transform = 'translateY(20px)'; setTimeout(function() { toast.remove(); }, 300); }, 3000);
  };

  // ─── Copy button delegation ───
  document.addEventListener('click', function(e) {
    var actionEl = e.target.closest('[data-action]');
    if (actionEl) {
      var action = actionEl.dataset.action;
      if (action === 'copyHash') {
        actionEl.textContent = 'Copied \u2713';
        actionEl.classList.add('sb-copy-btn--done');
        setTimeout(function() {
          actionEl.textContent = 'Copy';
          actionEl.classList.remove('sb-copy-btn--done');
        }, 2000);
        return;
      }
      if (action === 'openModal') {
        var modal = document.getElementById(actionEl.dataset.modalId);
        if (modal) modal.hidden = false;
        return;
      }
      if (action === 'closeModal') {
        var modal = e.target.closest('.sb-modal-overlay');
        if (modal) modal.hidden = true;
        return;
      }
      if (action === 'showToast') {
        var msg = actionEl.dataset.toastMsg || '';
        var type = actionEl.dataset.toastType || 'success';
        window.showToast(msg, type);
        return;
      }
      if (typeof window[action] === 'function') {
        e.preventDefault();
        window[action](e);
        return;
      }
    }
  });

  // ─── Language switcher (from solaceagi.com pattern) ───
  var langToggle = document.getElementById('languageToggle');
  var langMenu = document.getElementById('languageMenu');
  if (langToggle && langMenu) {
    langToggle.addEventListener('click', function(e) {
      e.stopPropagation();
      var willOpen = !langMenu.classList.contains('active');
      if (willOpen) { langMenu.removeAttribute('hidden'); }
      langMenu.classList.toggle('active', willOpen);
      langToggle.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
      if (!willOpen) { langMenu.setAttribute('hidden', ''); }
    });
    document.addEventListener('click', function(e) {
      if (!langToggle.contains(e.target) && !langMenu.contains(e.target)) {
        langMenu.classList.remove('active');
        langToggle.setAttribute('aria-expanded', 'false');
        langMenu.setAttribute('hidden', '');
      }
    });
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') {
        langMenu.classList.remove('active');
        langToggle.setAttribute('aria-expanded', 'false');
        langMenu.setAttribute('hidden', '');
      }
    });
  }

  // ─── DataTables init (sorting + search + pagination) ───
  if (typeof jQuery !== 'undefined' && jQuery.fn.DataTable) {
    jQuery('#demo-table').DataTable({
      paging: true,
      searching: true,
      ordering: true,
      pageLength: 10,
      language: { search: 'Filter:' },
      dom: 'ftip'
    });
    // Style DataTables to match our theme
    var dtStyle = document.createElement('style');
    dtStyle.textContent = [
      '.dataTables_wrapper { color: var(--sb-text); font-family: var(--sb-font); }',
      '.dataTables_filter input { background: var(--sb-surface-strong) !important; border: 1px solid var(--sb-border) !important; color: var(--sb-text) !important; padding: 6px 10px !important; border-radius: var(--sb-radius) !important; font-size: 0.9rem; }',
      '.dataTables_info { color: var(--sb-text-muted) !important; font-size: 0.8rem; }',
      '.dataTables_paginate .paginate_button { color: var(--sb-text-muted) !important; border: 1px solid var(--sb-border) !important; background: var(--sb-surface) !important; border-radius: var(--sb-radius-sm) !important; }',
      '.dataTables_paginate .paginate_button.current { background: var(--sb-accent) !important; color: var(--sb-on-accent) !important; border-color: var(--sb-accent) !important; }',
      '.dataTables_paginate .paginate_button:hover { background: var(--sb-surface-hover) !important; color: var(--sb-text) !important; }',
      'table.dataTable thead th { cursor: pointer; }',
      'table.dataTable thead .sorting::after { content: " \u21C5"; opacity: 0.3; }',
      'table.dataTable thead .sorting_asc::after { content: " \u2191"; }',
      'table.dataTable thead .sorting_desc::after { content: " \u2193"; }',
    ].join('\n');
    document.head.appendChild(dtStyle);
  }

  // ─── amCharts 5 — all chart types ───
  if (typeof am5 !== 'undefined') {
    am5.ready(function() {
      var accent = 0x78b9ff;
      var success = 0x55d7aa;
      var warning = 0xffd479;
      var danger = 0xff7b7b;

      function themes(root) {
        root.setThemes([am5themes_Dark.new(root), am5themes_Animated.new(root)]);
      }

      // 1. BAR — Weekly App Runs
      (function() {
        var root = am5.Root.new('chart-bar');
        themes(root);
        var chart = root.container.children.push(am5xy.XYChart.new(root, { panX:false, panY:false }));
        chart.set('cursor', am5xy.XYCursor.new(root, { behavior:'none' }));
        var xAxis = chart.xAxes.push(am5xy.CategoryAxis.new(root, { categoryField:'day', renderer:am5xy.AxisRendererX.new(root,{minGridDistance:30}) }));
        var yAxis = chart.yAxes.push(am5xy.ValueAxis.new(root, { renderer:am5xy.AxisRendererY.new(root,{}) }));
        var series = chart.series.push(am5xy.ColumnSeries.new(root, { name:'Runs', xAxis:xAxis, yAxis:yAxis, valueYField:'runs', categoryXField:'day', tooltip:am5.Tooltip.new(root,{labelText:'{day}: {runs} runs'}) }));
        series.columns.template.setAll({ cornerRadiusTL:4, cornerRadiusTR:4, fill:am5.color(accent), stroke:am5.color(accent) });
        var data = [{day:'Mon',runs:12},{day:'Tue',runs:18},{day:'Wed',runs:24},{day:'Thu',runs:15},{day:'Fri',runs:30},{day:'Sat',runs:8},{day:'Sun',runs:5}];
        xAxis.data.setAll(data); series.data.setAll(data); series.appear(1000); chart.appear(1000,100);
      })();

      // 2. LINE — Evidence Growth
      (function() {
        var root = am5.Root.new('chart-line');
        themes(root);
        var chart = root.container.children.push(am5xy.XYChart.new(root, { panX:true, panY:false }));
        chart.set('cursor', am5xy.XYCursor.new(root, { behavior:'none', xAxis:undefined, yAxis:undefined }));
        var xAxis = chart.xAxes.push(am5xy.CategoryAxis.new(root, { categoryField:'date', renderer:am5xy.AxisRendererX.new(root,{minGridDistance:80}) }));
        xAxis.get('renderer').labels.template.setAll({ rotation:-45, centerX:am5.percent(100), centerY:am5.percent(50), fontSize:12 });
        var yAxis = chart.yAxes.push(am5xy.ValueAxis.new(root, { renderer:am5xy.AxisRendererY.new(root,{}) }));
        var series = chart.series.push(am5xy.LineSeries.new(root, { name:'Evidence', xAxis:xAxis, yAxis:yAxis, valueYField:'count', categoryXField:'date', tooltip:am5.Tooltip.new(root,{labelText:'{count} entries'}) }));
        series.strokes.template.setAll({ strokeWidth:3 });
        series.set('fill', am5.color(success));
        series.set('stroke', am5.color(success));
        var data = [{date:'Mar 1',count:8200},{date:'Mar 5',count:9100},{date:'Mar 8',count:10400},{date:'Mar 10',count:11200},{date:'Mar 12',count:12100},{date:'Mar 14',count:13200},{date:'Mar 15',count:13741}];
        xAxis.data.setAll(data); series.data.setAll(data); series.appear(1000); chart.appear(1000,100);
      })();

      // 3. DONUT — Budget Usage
      (function() {
        var root = am5.Root.new('chart-donut');
        themes(root);
        var PieChart = am5percent ? am5percent.PieChart : (am5.percent && am5.percent.PieChart);
        var PieSeries = am5percent ? am5percent.PieSeries : (am5.percent && am5.percent.PieSeries);
        if (!PieChart) { document.getElementById('chart-donut').textContent = 'PieChart module not loaded'; return; }
        var chart = root.container.children.push(PieChart.new(root, { innerRadius: am5.percent(60) }));
        var series = chart.series.push(PieSeries.new(root, { valueField:'value', categoryField:'category', tooltip:am5.Tooltip.new(root,{labelText:'{category}: {value}'}) }));
        series.slices.template.setAll({ cornerRadius:5, strokeWidth:2, stroke:am5.color(0x0f1e33) });
        series.data.setAll([
          {category:'Used (32)', value:32, sliceSettings:{fill:am5.color(accent)}},
          {category:'Remaining (968)', value:968, sliceSettings:{fill:am5.color(0x1a2d47)}}
        ]);
        series.slices.template.adapters.add('fill', function(fill, target) {
          return target.dataItem && target.dataItem.dataContext.sliceSettings ? target.dataItem.dataContext.sliceSettings.fill : fill;
        });
        series.appear(1000); chart.appear(1000,100);
      })();

      // 4. HORIZONTAL BAR — Apps per Domain
      (function() {
        var root = am5.Root.new('chart-hbar');
        themes(root);
        var chart = root.container.children.push(am5xy.XYChart.new(root, { panX:false, panY:false }));
        chart.set('cursor', am5xy.XYCursor.new(root, { behavior:'none' }));
        var yAxis = chart.yAxes.push(am5xy.CategoryAxis.new(root, { categoryField:'domain', renderer:am5xy.AxisRendererY.new(root,{inversed:true,minGridDistance:20}) }));
        var xAxis = chart.xAxes.push(am5xy.ValueAxis.new(root, { renderer:am5xy.AxisRendererX.new(root,{}) }));
        var series = chart.series.push(am5xy.ColumnSeries.new(root, { name:'Apps', xAxis:xAxis, yAxis:yAxis, valueXField:'apps', categoryYField:'domain', tooltip:am5.Tooltip.new(root,{labelText:'{domain}: {apps} apps'}) }));
        series.columns.template.setAll({ cornerRadiusTR:4, cornerRadiusBR:4, height:am5.percent(60), fill:am5.color(success), stroke:am5.color(success) });
        var data = [{domain:'google.com',apps:5},{domain:'linkedin.com',apps:3},{domain:'mail.google.com',apps:2},{domain:'github.com',apps:1},{domain:'reddit.com',apps:1},{domain:'x.com',apps:2},{domain:'news.ycombinator.com',apps:1}];
        yAxis.data.setAll(data); series.data.setAll(data); series.appear(1000); chart.appear(1000,100);
      })();

      // 5. STACKED BAR — Agent Usage
      (function() {
        var root = am5.Root.new('chart-stacked');
        themes(root);
        var chart = root.container.children.push(am5xy.XYChart.new(root, { panX:false, panY:false }));
        chart.set('cursor', am5xy.XYCursor.new(root, { behavior:'none' }));
        chart.set('legend', am5.Legend.new(root, { centerX:am5.percent(50), x:am5.percent(50) }));
        var xAxis = chart.xAxes.push(am5xy.CategoryAxis.new(root, { categoryField:'agent', renderer:am5xy.AxisRendererX.new(root,{minGridDistance:30}) }));
        var yAxis = chart.yAxes.push(am5xy.ValueAxis.new(root, { renderer:am5xy.AxisRendererY.new(root,{}) }));
        function addSeries(name, field, color) {
          var s = chart.series.push(am5xy.ColumnSeries.new(root, { name:name, xAxis:xAxis, yAxis:yAxis, valueYField:field, categoryXField:'agent', stacked:true, tooltip:am5.Tooltip.new(root,{labelText:'{name}: {valueY}'}) }));
          s.columns.template.setAll({ fill:am5.color(color), stroke:am5.color(color), cornerRadiusTL:2, cornerRadiusTR:2 });
          return s;
        }
        var s1 = addSeries('Generate', 'generate', accent);
        var s2 = addSeries('Chat', 'chat', success);
        var s3 = addSeries('Code', 'code', warning);
        var data = [{agent:'claude',generate:45,chat:30,code:25},{agent:'codex',generate:20,chat:10,code:50},{agent:'gemini',generate:15,chat:25,code:10},{agent:'copilot',generate:5,chat:5,code:30},{agent:'cursor',generate:3,chat:2,code:20},{agent:'aider',generate:2,chat:1,code:15}];
        xAxis.data.setAll(data); s1.data.setAll(data); s2.data.setAll(data); s3.data.setAll(data);
        s1.appear(1000); s2.appear(1000); s3.appear(1000); chart.appear(1000,100);
      })();

      // 6. AREA — Response Time
      (function() {
        var root = am5.Root.new('chart-area');
        themes(root);
        var chart = root.container.children.push(am5xy.XYChart.new(root, { panX:true, panY:false }));
        chart.set('cursor', am5xy.XYCursor.new(root, { behavior:'none' }));
        var xAxis = chart.xAxes.push(am5xy.CategoryAxis.new(root, { categoryField:'time', renderer:am5xy.AxisRendererX.new(root,{minGridDistance:40}) }));
        var yAxis = chart.yAxes.push(am5xy.ValueAxis.new(root, { renderer:am5xy.AxisRendererY.new(root,{}) }));
        var SeriesType = am5xy.SmoothedXLineSeries || am5xy.LineSeries;
        var series = chart.series.push(SeriesType.new(root, { name:'ms', xAxis:xAxis, yAxis:yAxis, valueYField:'ms', categoryXField:'time', tooltip:am5.Tooltip.new(root,{labelText:'{ms}ms'}) }));
        series.fills.template.setAll({ visible:true, fillOpacity:0.3 });
        series.set('fill', am5.color(warning));
        series.set('stroke', am5.color(warning));
        series.strokes.template.setAll({ strokeWidth:2 });
        var data = [{time:'12:00',ms:45},{time:'12:05',ms:52},{time:'12:10',ms:38},{time:'12:15',ms:120},{time:'12:20',ms:65},{time:'12:25',ms:42},{time:'12:30',ms:48},{time:'12:35',ms:55},{time:'12:40',ms:40},{time:'12:45',ms:35}];
        xAxis.data.setAll(data); series.data.setAll(data); series.appear(1000); chart.appear(1000,100);
      })();

    });
  }

})();
