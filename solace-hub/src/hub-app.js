// Diagram: 04-hub-lifecycle
(function() {
  'use strict';

  if (window.__solaceHubEnhancerInstalled) {
    return;
  }
  window.__solaceHubEnhancerInstalled = true;

  var API = 'http://localhost:8888';

  function get(path) {
    return fetch(API + path).then(function(r) { return r.json(); });
  }

  function postEvalResult(payload) {
    return fetch(API + '/api/v1/hub/eval-result', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    }).catch(function() {});
  }

  function hubStateSnapshot() {
    var active = document.querySelector('.sb-tab.sb-tab--active[data-tab]');
    return {
      active_tab: active ? active.dataset.tab : null,
      tabs: Array.from(document.querySelectorAll('.sb-tab[data-tab]')).map(function(tab) {
        return {
          id: tab.dataset.tab,
          active: tab.classList.contains('sb-tab--active'),
          bound: tab.dataset.enhancedBound === '1'
        };
      }),
      visible_panels: Array.from(document.querySelectorAll('.hub-tab-panel')).filter(function(panel) {
        return !panel.hidden && panel.style.display !== 'none';
      }).map(function(panel) {
        return panel.id;
      }),
      topbar_user: document.getElementById('topbar-user') ? document.getElementById('topbar-user').textContent : null,
      version_badge: document.getElementById('hub-version-badge') ? document.getElementById('hub-version-badge').textContent : null,
      theme: document.documentElement.getAttribute('data-theme') || 'dark'
    };
  }

  function setActiveTabState(tabId) {
    document.querySelectorAll('.sb-tab[data-tab]').forEach(function(tab) {
      var selected = tab.dataset.tab === tabId;
      tab.classList.toggle('sb-tab--active', selected);
      tab.setAttribute('aria-selected', selected ? 'true' : 'false');
    });

    document.querySelectorAll('.hub-tab-panel').forEach(function(panel) {
      var selected = panel.id === 'tab-' + tabId;
      panel.hidden = !selected;
      panel.style.display = selected ? 'block' : 'none';
      panel.classList.toggle('sh-tab-panel-hidden', !selected);
    });
  }

  function runTabSideEffects(tabId) {
    if (tabId === 'sessions' && typeof window.refreshSessionsTab === 'function') {
      try { window.refreshSessionsTab(); } catch (e) {}
    }
    if (tabId === 'events' && typeof window.refreshEvents === 'function') {
      try { window.refreshEvents(); } catch (e) {}
    }
    if (tabId === 'settings' && typeof window.refreshSettings === 'function') {
      try { window.refreshSettings(); } catch (e) {}
    }
  }

  function activateHubTab(tabId) {
    setActiveTabState(tabId);
    runTabSideEffects(tabId);
    return hubStateSnapshot();
  }

  function executeHubCommand(command) {
    if (!command || typeof command !== 'object') {
      throw new Error('Hub command must be an object');
    }

    switch (command.op) {
      case 'get_state':
        return hubStateSnapshot();
      case 'set_active_tab':
        return activateHubTab(command.tab);
      case 'click_selector': {
        var element = document.querySelector(command.selector);
        if (!element) {
          throw new Error('Selector not found: ' + command.selector);
        }
        if (element.matches('.sb-tab[data-tab]')) {
          return activateHubTab(element.dataset.tab);
        }
        element.click();
        return hubStateSnapshot();
      }
      case 'get_text': {
        var target = document.querySelector(command.selector);
        if (!target) {
          throw new Error('Selector not found: ' + command.selector);
        }
        return {
          selector: command.selector,
          text: target.textContent || ''
        };
      }
      default:
        throw new Error('Unsupported hub command: ' + command.op);
    }
  }

  function installThemeSync() {
    document.querySelectorAll('.sb-theme-btn').forEach(function(btn) {
      if (btn.dataset.enhancedBound === '1') {
        return;
      }
      btn.dataset.enhancedBound = '1';
      btn.addEventListener('click', function() {
        document.documentElement.setAttribute('data-theme', btn.dataset.theme);
        if (document.body) {
          document.body.setAttribute('data-theme', btn.dataset.theme);
        }
      }, true);
    });
  }

  function installTabDelegation() {
    var tablist = document.querySelector('.sb-tabs[role="tablist"]');
    if (!tablist || tablist.dataset.enhancedBound === '1') {
      return;
    }

    tablist.dataset.enhancedBound = '1';

    var handler = function(e) {
      var tab = e.target.closest('.sb-tab[data-tab]');
      if (!tab) {
        return;
      }
      e.preventDefault();
      e.stopPropagation();
      activateHubTab(tab.dataset.tab);
    };

    tablist.addEventListener('click', handler, true);
    tablist.addEventListener('pointerup', handler, true);
    tablist.addEventListener('keydown', function(e) {
      var tab = e.target.closest('.sb-tab[data-tab]');
      if (!tab) {
        return;
      }
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        activateHubTab(tab.dataset.tab);
      }
    }, true);

    document.querySelectorAll('.sb-tab[data-tab]').forEach(function(tab) {
      tab.dataset.enhancedBound = '1';
    });

    var active = document.querySelector('.sb-tab.sb-tab--active[data-tab]') ||
      document.querySelector('.sb-tab[data-tab]');
    if (active) {
      activateHubTab(active.dataset.tab);
    }
  }

  function pollPendingHubCommands() {
    return get('/api/v1/hub/pending-js').then(function(payload) {
      var raw = payload && (payload.command || payload.js);
      if (!raw) {
        return;
      }

      var requestId = payload.request_id || null;

      try {
        var command = JSON.parse(raw);
        return postEvalResult({
          request_id: requestId,
          ok: true,
          result: executeHubCommand(command)
        });
      } catch (err) {
        return postEvalResult({
          request_id: requestId,
          ok: false,
          error: err ? String(err.message || err) : 'Hub command failed',
          result: {
            hint: 'Hub accepts structured JSON commands such as {"op":"set_active_tab","tab":"overview"}'
          }
        });
      }
    }).catch(function() {});
  }

  installThemeSync();
  installTabDelegation();

  document.addEventListener('DOMContentLoaded', function() {
    installThemeSync();
    installTabDelegation();
  });
  window.addEventListener('load', function() {
    installThemeSync();
    installTabDelegation();
  });

  setTimeout(pollPendingHubCommands, 200);
  setInterval(pollPendingHubCommands, 1000);
})();
