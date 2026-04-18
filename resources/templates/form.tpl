<!DOCTYPE html>
<html lang="cs">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Oneplay Server</title>
    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
    <style>
      :root {
        --bg: #0f1117;
        --surface: #1a1d27;
        --surface2: #242836;
        --accent: #6c5ce7;
        --accent-hover: #7c6ef7;
        --text: #e4e6eb;
        --text2: #8b8fa3;
        --border: #2d3143;
        --red: #e74c3c;
        --green: #2ecc71;
        --radius: 10px;
      }
      * { margin: 0; padding: 0; box-sizing: border-box; }
      body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        background: var(--bg);
        color: var(--text);
        min-height: 100vh;
        line-height: 1.5;
      }
      .container {
        max-width: 1000px;
        margin: 0 auto;
        padding: 20px;
      }
      header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 16px 0;
        border-bottom: 1px solid var(--border);
        margin-bottom: 20px;
        flex-wrap: wrap;
        gap: 10px;
      }
      header h1 { font-size: 22px; font-weight: 600; }
      header h1 span { color: var(--accent); }
      header a { color: var(--text2); font-size: 13px; text-decoration: none; transition: 0.2s; }
      header a:hover { color: var(--text); }

      .message {
        background: rgba(231,76,60,0.15);
        color: var(--red);
        padding: 10px 16px;
        border-radius: var(--radius);
        margin-bottom: 16px;
        font-size: 14px;
        border: 1px solid rgba(231,76,60,0.2);
      }

      .actions { display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }
      .btn {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 10px 18px;
        border: 1px solid var(--border);
        border-radius: var(--radius);
        background: var(--surface);
        color: var(--text);
        font-size: 13px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s;
      }
      .btn:hover { background: var(--surface2); border-color: var(--accent); }
      .btn-accent { background: var(--accent); border-color: var(--accent); }
      .btn-accent:hover { background: var(--accent-hover); transform: translateY(-1px); }

      /* Copy Button Logic */
      .copy-btn {
        background: var(--surface2);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 4px 10px;
        cursor: pointer;
        color: var(--text2);
        font-size: 12px;
        transition: all 0.2s;
        white-space: nowrap;
      }
      .copy-btn:hover { border-color: var(--accent); color: var(--accent); }
      .copy-btn.success { border-color: var(--green); color: var(--green); }

      /* Player */
      #player-section {
        display: none;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        overflow: hidden;
        margin-bottom: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
      }
      #player-section.active { display: block; }
      #player-section.idle-state {
        background: transparent;
        border: none;
        box-shadow: none;
        overflow: visible;
      }
      .player-bar {
        padding: 12px 16px;
        background: var(--surface2);
        overflow: hidden;
      }
      .player-bar.video-active {
        margin-top: -1px;
      }
      .player-bar.idle {
        min-height: 72px;
        display: flex;
        align-items: center;
        border: 1px solid var(--border);
        border-radius: var(--radius);
      }
      .player-bar .name { font-weight: 600; font-size: 15px; color: var(--accent); }
      .player-info-wrap { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
      .player-epg-title { font-size: 14px; font-weight: 600; color: var(--text); }
      .player-cover { width: 140px; height: 90px; object-fit: cover; border-radius: 6px; display: none; float: right; margin-left: 12px; margin-bottom: 4px; }
      .player-cover.visible { display: block; }
      .player-desc { font-size: 12px; color: var(--text2); line-height: 1.4; margin: 4px 0 0; display: none; clear: none; }
      .player-desc.visible { display: block; }
      .player-progress-wrap { display: flex; align-items: center; gap: 8px; margin-top: 2px; }
      .player-time { font-size: 11px; color: var(--text2); font-family: monospace; white-space: nowrap; }
      .player-progress { flex: 1; height: 4px; background: var(--border); border-radius: 2px; overflow: hidden; }
      .player-progress-bar { height: 100%; background: var(--accent); border-radius: 2px; width: 0%; transition: width 0.5s ease; }
      .close-btn {
        margin-left: auto;
        cursor: pointer;
        color: var(--text2);
        font-size: 13px;
        padding: 6px 12px;
        border: 1px solid var(--border);
        border-radius: 6px;
        background: rgba(231,76,60,0.1);
        transition: all 0.2s;
      }
      .close-btn:hover { background: var(--red); color: white; border-color: var(--red); }
      .player-video-wrap { position: relative; }
      .player-video-wrap video { width: 100%; background: #000; display: block; aspect-ratio: 16/9; }
      .video-restart {
        position: absolute;
        top: 12px;
        left: 12px;
        z-index: 10;
        width: 40px;
        height: 40px;
        border: none;
        border-radius: 50%;
        background: rgba(0,0,0,0.6);
        color: #fff;
        font-size: 22px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.2s;
        opacity: 0;
        pointer-events: none;
      }
      .player-video-wrap.controls-visible .video-restart { opacity: 1; pointer-events: auto; }
      .video-restart:hover { background: var(--accent); transform: scale(1.1); }
      .video-close {
        position: absolute;
        top: 12px;
        right: 12px;
        z-index: 10;
        width: 40px;
        height: 40px;
        border: none;
        border-radius: 50%;
        background: rgba(0,0,0,0.6);
        color: #fff;
        font-size: 20px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.2s;
        opacity: 0;
        pointer-events: none;
      }
      .player-video-wrap.controls-visible .video-close { opacity: 1; pointer-events: auto; }
      .video-close:hover { background: var(--red); transform: scale(1.1); }

      /* Channels Grid */
      .channels-header { font-size: 12px; color: var(--text2); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; }
      .channel-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 10px; }
      .channel-card {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        padding: 12px;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        cursor: pointer;
        transition: 0.2s;
        text-decoration: none;
        color: var(--text);
      }
      .channel-card:hover { border-color: var(--accent); background: var(--surface2); transform: scale(1.02); }
      .channel-card.playing { border-color: var(--green); background: rgba(46, 204, 113, 0.05); }
      .channel-card img { width: 45px; height: 30px; object-fit: contain; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3)); }
      .ch-meta { flex: 1; min-width: 0; }
      .ch-name { display: block; font-size: 14px; font-weight: 500; }
      .ch-epg { margin-top: 4px; font-size: 12px; color: var(--text2); line-height: 1.35; }
      .ch-epg strong { color: var(--text); font-weight: 500; }
      .ch-epg-empty { margin-top: 4px; font-size: 12px; color: var(--text2); }
      .ch-progress { width: 100%; height: 3px; background: var(--border); border-radius: 2px; margin-top: 6px; overflow: hidden; }
      .ch-progress-bar { height: 100%; background: var(--accent); border-radius: 2px; width: 0%; transition: width 0.5s ease; }
      .ch-catchup { background: none; border: none; color: var(--text2); cursor: pointer; padding: 5px; font-size: 16px; opacity: 0.6; transition: 0.2s; align-self: center; }
      .ch-catchup:hover { color: var(--accent); opacity: 1; }

      /* Catchup modal */
      .catchup-days { display: flex; gap: 4px; margin-bottom: 16px; overflow-x: auto; }
      .catchup-day-btn {
        flex: 1;
        min-width: 0;
        padding: 10px 6px;
        border: 1px solid var(--border);
        border-radius: 8px;
        background: var(--surface);
        color: var(--text2);
        cursor: pointer;
        font-size: 12px;
        font-weight: 500;
        transition: all 0.2s;
        text-align: center;
        line-height: 1.3;
      }
      .catchup-day-btn .day-name { display: block; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }
      .catchup-day-btn .day-date { display: block; font-size: 15px; font-weight: 700; margin-top: 2px; }
      .catchup-day-btn:hover { border-color: var(--accent); color: var(--text); background: var(--surface2); }
      .catchup-day-btn.active { background: var(--accent); border-color: var(--accent); color: #fff; }
      .catchup-list { display: flex; flex-direction: column; gap: 4px; }
      .catchup-item {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 12px;
        border-radius: 6px;
        background: var(--surface);
        border: 1px solid var(--border);
        transition: 0.2s;
        cursor: pointer;
      }
      .catchup-item:hover { border-color: var(--accent); background: var(--surface2); }
      .catchup-item .ci-time { font-size: 12px; color: var(--text); font-family: monospace; white-space: nowrap; min-width: 48px; font-weight: 600; }
      .catchup-item .ci-title { font-size: 13px; color: var(--text); flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .catchup-item .ci-play { font-size: 14px; color: var(--text2); transition: 0.2s; flex-shrink: 0; }
      .catchup-item:hover .ci-play { color: var(--accent); }
      .catchup-loading { text-align: center; color: var(--text2); padding: 20px; font-size: 14px; }

      /* Catchup title logo */
      #catchup-title { display: flex; align-items: center; gap: 12px; }
      #catchup-title img { height: 40px; width: auto; object-fit: contain; }

      /* Modals */
      .modal-overlay {
        display: none;
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(0,0,0,0.85);
        z-index: 200;
        justify-content: center;
        align-items: center;
        backdrop-filter: blur(4px);
      }
      .modal-overlay.active { display: flex; }
      .modal {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        width: 90%;
        max-width: 650px;
        max-height: 85vh;
        overflow: hidden;
        display: flex;
        flex-direction: column;
      }
      .modal-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 20px;
        border-bottom: 1px solid var(--border);
      }
      .modal-body { padding: 20px; overflow-y: auto; }
      .config-row {
        display: flex;
        flex-direction: column;
        padding: 12px 0;
        border-bottom: 1px solid var(--border);
        gap: 4px;
      }
      .config-row:last-child { border-bottom: none; }
      .config-key { color: var(--text2); font-size: 11px; text-transform: uppercase; font-weight: 700; }
      .config-val { font-family: monospace; font-size: 13px; color: var(--accent); word-break: break-all; }
      
      .link-item { display: flex; align-items: center; gap: 10px; margin-top: 5px; }
      .link-item a { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text); text-decoration: none; font-size: 13px; border-bottom: 1px dashed var(--accent); }

      /* Settings Dropdown */
      .settings-wrap {
        position: relative;
      }
      .settings-toggle {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        color: var(--text);
        font-size: 20px;
        padding: 6px 10px;
        cursor: pointer;
        transition: all 0.2s;
        line-height: 1;
      }
      .settings-toggle:hover {
        border-color: var(--accent);
        color: var(--accent);
      }
      .settings-dropdown {
        display: none;
        position: absolute;
        right: 0;
        top: calc(100% + 6px);
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        min-width: 200px;
        z-index: 50;
        box-shadow: 0 8px 24px rgba(0,0,0,0.5);
        overflow: hidden;
      }
      .settings-dropdown.active { display: block; }
      .settings-dropdown .dd-item {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 10px 16px;
        color: var(--text);
        font-size: 13px;
        cursor: pointer;
        border: none;
        background: none;
        width: 100%;
        text-align: left;
        transition: background 0.15s;
      }
      .settings-dropdown .dd-item:hover {
        background: var(--surface2);
      }
      .settings-dropdown .dd-divider {
        height: 1px;
        background: var(--border);
      }

      @media (max-width: 600px) {
        .container { padding: 10px; }
        .channel-grid { grid-template-columns: 1fr; }
        .actions { flex-direction: column; }
        .btn { width: 100%; justify-content: center; }
      }
    </style>
  </head>
  <body>
    <div class="container">
      <header>
        <h1>Oneplay Server {{ version }}</h1>
        <div style="display:flex;align-items:center;gap:12px">
          <a href="https://www.xbmc-kodi.cz/prispevek-oneplay-server" target="_blank">&#128172; Podpora &amp; diskuze &rarr;</a>
          <div class="settings-wrap">
            <button class="settings-toggle" onclick="toggleSettings(event)" title="Nastavení">&#9881;</button>
            <div class="settings-dropdown" id="settings-dropdown">
              <form method="post" action="/" style="display:contents">
                <input type="hidden" name="action" value="reset_channels">
                <button type="submit" class="dd-item">&#8635; Resetovat kanály</button>
              </form>
              <form method="post" action="/" style="display:contents">
                <input type="hidden" name="action" value="reset_session">
                <button type="submit" class="dd-item">&#8635; Resetovat session</button>
              </form>
              <div class="dd-divider"></div>
              <button class="dd-item" onclick="toggleModal('config-modal', true, '/config')">&#9881; Konfigurace</button>
              <button class="dd-item" onclick="toggleModal('links-modal', true)">&#128279; IPTV odkazy</button>
              % if auth_enabled:
              <div class="dd-divider"></div>
              <button class="dd-item" onclick="doLogout()">&#128682; Odhlásit se</button>
              % end
            </div>
          </div>
        </div>
      </header>

      % if message:
      <div class="message">{{ message }}</div>
      % end

      % if warning and not auth_enabled:
      <div class="container" style="color:red">Oneplay Server vždy používejte jen v rámci uzavřené sítě a nevystavujte ho otevřeně do internetu. Podobné použití může být vyhodnocené ze strany poskytovatele služby jako podezřelé. 
      Využijte také možnost alespoň základní formu zapezpečení - nastavení parametrů auth_user a auth_pass, které zapne ověření jménem a heslem.
      </div>
      % end

      <div id="player-section" class="active% if player_enabled: idle-state% end">
        <div class="player-video-wrap" style="display:none">
          <video id="player-video" controls autoplay></video>
          <button class="video-restart" onclick="restartStream()" title="Od začátku">&#8634;</button>
          <button class="video-close" onclick="closePlayer()" title="Zavřít">&#10005;</button>
        </div>
        <div class="player-bar idle"% if not player_enabled: style="display:none"% end>
          <img id="player-cover" class="player-cover" src="" alt="">
          <div class="player-info-wrap">
            <span id="player-info" class="name">Vyberte kanál pro spuštění přehrávače</span>
            <div id="player-progress-wrap" class="player-progress-wrap" style="display:none">
              <span id="player-time-start" class="player-time"></span>
              <div class="player-progress"><div id="player-progress-bar" class="player-progress-bar"></div></div>
              <span id="player-time-end" class="player-time"></span>
            </div>
            <span id="player-epg-title" class="player-epg-title">Přehrávač se otevře po kliknutí na kanál v seznamu níže.</span>
          </div>
          <p id="player-desc" class="player-desc"></p>
        </div>
      </div>

      <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
        <h3 class="channels-header" style="margin-bottom:0">Seznam kanálů</h3>
        <button id="filter-toggle" class="ch-catchup" onclick="toggleFilter()" title="Filtrovat kanály">&#8981;</button>
        <input id="filter-input" type="text" placeholder="Hledat kanál..." oninput="filterChannels()" style="display:none;flex:1;padding:8px 12px;border:1px solid var(--border);border-radius:var(--radius);background:var(--surface);color:var(--text);font-size:13px;outline:none;transition:border-color 0.2s" onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border)'">
      </div>
      <div class="channel-grid">
        % for item in playlist:
        <div class="channel-card" data-channel-id="{{ item['channel_id'] }}" onclick="playChannel('{{ item['slug'] }}', '{{ item['name'] }}', this)">
          <img src="{{ item['logo'] }}" alt="{{ item['name'] }}" loading="lazy">
          <div class="ch-meta">
            <span class="ch-name">{{ item['name'] }}</span>
            <div class="ch-epg" style="display:none"></div>
            <div class="ch-progress" style="display:none"><div class="ch-progress-bar"></div></div>
            <div class="ch-epg-empty">Načítám EPG...</div>
          </div>
          % if not item.get('liveOnly', False):
          <button class="ch-catchup" onclick="event.stopPropagation(); openCatchup('{{ item['channel_id'] }}', '{{ item['name'] }}', '{{ item['slug'] }}', '{{ item['logo'] }}')" title="Archiv">&#9202;</button>
          % end
        </div>
        % end
      </div>

      <div class="modal-overlay" id="links-modal" onclick="closeAllModals(event)">
        <div class="modal">
          <div class="modal-header">
            <h3>&#128279; IPTV odkazy</h3>
            <button class="close-btn" onclick="toggleModal('links-modal', false)">&#10005;</button>
          </div>
          <div class="modal-body">
            <div class="config-row">
              <span class="config-key">M3U Playlist</span>
              <div class="link-item">
                <a href="{{ playlist_url }}" target="_blank">{{ playlist_url }}</a>
                <button class="copy-btn" onclick="copyText('{{ playlist_url }}', this)">Kopírovat</button>
              </div>
            </div>
            <div class="config-row">
              <span class="config-key">TVheadend Playlist</span>
              <div class="link-item">
                <a href="{{ playlist_tvheadend_url }}" target="_blank">{{ playlist_tvheadend_url }}</a>
                <button class="copy-btn" onclick="copyText('{{ playlist_tvheadend_url }}', this)">Kopírovat</button>
              </div>
            </div>
            <div class="config-row">
              <span class="config-key">EPG XMLTV</span>
              <div class="link-item">
                <a href="{{ epg_url }}" target="_blank">{{ epg_url }}</a>
                <button class="copy-btn" onclick="copyText('{{ epg_url }}', this)">Kopírovat</button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="modal-overlay" id="config-modal" onclick="closeAllModals(event)">
        <div class="modal">
          <div class="modal-header">
            <h3>&#9881; Systémová konfigurace</h3>
            <button class="close-btn" onclick="toggleModal('config-modal', false)">&#10005;</button>
          </div>
          <div class="modal-body" id="config-body">
            <p style="color:var(--text2)">Načítám data...</p>
          </div>
        </div>
      </div>
      <div class="modal-overlay" id="catchup-modal" onclick="closeAllModals(event)">
        <div class="modal">
          <div class="modal-header">
            <h3 id="catchup-title">&#9202; Archiv</h3>
            <button class="close-btn" onclick="toggleModal('catchup-modal', false)">&#10005;</button>
          </div>
          <div class="modal-body">
            <div class="catchup-days" id="catchup-days"></div>
            <div id="catchup-content"><p class="catchup-loading">Vyberte den</p></div>
          </div>
        </div>
      </div>
    </div>

    <script>
      const authEnabled = {{ 'true' if auth_enabled else 'false' }};
      const playerEnabled = {{ 'true' if player_enabled else 'false' }};
      let currentHls = null;
      let currentCard = null;

      // Auto-hide video overlay buttons
      (function() {
        let controlsTimer = null;
        const wrap = document.querySelector('.player-video-wrap');
        if (!wrap) return;
        function showControls() {
          wrap.classList.add('controls-visible');
          clearTimeout(controlsTimer);
          controlsTimer = setTimeout(() => wrap.classList.remove('controls-visible'), 3000);
        }
        wrap.addEventListener('mousemove', showControls);
        wrap.addEventListener('mouseenter', showControls);
        wrap.addEventListener('touchstart', showControls, {passive: true});
        wrap.addEventListener('mouseleave', () => {
          clearTimeout(controlsTimer);
          wrap.classList.remove('controls-visible');
        });
      })();

      // Settings dropdown
      function toggleSettings(e) {
        e.stopPropagation();
        document.getElementById('settings-dropdown').classList.toggle('active');
      }
      document.addEventListener('click', function() {
        document.getElementById('settings-dropdown').classList.remove('active');
      });

      function doLogout() {
        const url = window.location.origin.replace('://', '://logout@');
        fetch(url, {headers: {'Authorization': 'Basic ' + btoa('logout:logout')}}).finally(() => {
          window.location.href = url;
        });
      }

      // Funkce pro kopírování s vizuální odezvou
      async function copyText(text, btn) {
        try {
          await navigator.clipboard.writeText(text);
          const originalText = btn.innerHTML;
          btn.innerHTML = btn.tagName === 'BUTTON' && btn.classList.contains('copy-btn') ? 'Zkopírováno!' : '&#9989;';
          btn.classList.add('success');
          setTimeout(() => {
            btn.innerHTML = originalText;
            btn.classList.remove('success');
          }, 2000);
        } catch (err) {
          console.error('Chyba při kopírování', err);
        }
      }

      function formatEpgTime(startts, endts) {
        if (!startts || !endts) return '';
        return formatTime(startts) + ' - ' + formatTime(endts);
      }

      function formatTime(ts) {
        return new Date(parseInt(ts) * 1000).toLocaleTimeString('cs-CZ', {hour:'2-digit', minute:'2-digit', hour12:false});
      }

      function updatePlayerProgress() {
        const section = document.getElementById('player-section');
        const bar = document.getElementById('player-progress-bar');
        if (!section || !bar) return;
        const start = parseInt(section.dataset.epgStart);
        const end = parseInt(section.dataset.epgEnd);
        if (!start || !end) return;
        const now = Date.now() / 1000;
        const pct = Math.min(100, Math.max(0, (now - start) / (end - start) * 100));
        bar.style.width = pct + '%';
      }

      function playChannel(slug, name, card) {
        const section = document.getElementById('player-section');
        const video = document.getElementById('player-video');
        const videoWrap = document.querySelector('.player-video-wrap');
        const playerBar = document.querySelector('.player-bar');
        const info = document.getElementById('player-info');
        const titleEl = document.getElementById('player-epg-title');
        const descEl = document.getElementById('player-desc');
        const coverEl = document.getElementById('player-cover');
        const progressWrap = document.getElementById('player-progress-wrap');
        const timeStart = document.getElementById('player-time-start');
        const timeEnd = document.getElementById('player-time-end');
        const startts = card.dataset.epgStartts;
        const endts = card.dataset.epgEndts;
        const epgTitle = card.dataset.epgTitle;
        const epgDesc = card.dataset.epgDesc;
        const epgCover = card.dataset.epgCover;

        if (!section || !video || !videoWrap || !playerBar || !info || !titleEl || !descEl || !coverEl || !progressWrap || !timeStart || !timeEnd) {
          return;
        }

        info.textContent = `Načítám: ${name}...`;
        info.style.color = '';
        section.classList.remove('idle-state');
        playerBar.classList.remove('idle');
        playerBar.classList.add('video-active');
        videoWrap.style.display = '';
        titleEl.textContent = epgTitle || '';
        if (epgDesc) { descEl.textContent = epgDesc; descEl.classList.add('visible'); } else { descEl.textContent = ''; descEl.classList.remove('visible'); }
        if (epgCover) { coverEl.src = epgCover; coverEl.classList.add('visible'); } else { coverEl.src = ''; coverEl.classList.remove('visible'); }
        if (startts && endts) {
          timeStart.textContent = formatTime(startts);
          timeEnd.textContent = formatTime(endts);
          section.dataset.epgStart = startts;
          section.dataset.epgEnd = endts;
          progressWrap.style.display = '';
          updatePlayerProgress();
        } else {
          progressWrap.style.display = 'none';
        }
        section.classList.add('active');
        section.scrollIntoView({ behavior: 'smooth', block: 'start' });

        if (currentCard) currentCard.classList.remove('playing');
        currentCard = card;
        card.classList.add('playing');

        if (currentHls) {
          currentHls.destroy();
          currentHls = null;
        }

        fetch(`/stream_url/${slug}`, {credentials: 'same-origin'})
          .then(r => {
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
          })
          .then(data => {
            if (data.error || !data.url) {
              throw new Error(data.error || 'Stream není dostupný');
            }
            info.textContent = name;
            
            if (Hls.isSupported()) {
              currentHls = new Hls();
              currentHls.loadSource(data.url);
              currentHls.attachMedia(video);
              currentHls.on(Hls.Events.MANIFEST_PARSED, () => video.play());
            } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
              video.src = data.url;
              video.play();
            }
          })
          .catch(err => {
            info.innerHTML = `Chyba: ${name} &middot; ${err.message}`;
            info.style.color = 'var(--red)';
          });
      }

      function restartStream() {
        const video = document.getElementById('player-video');
        if (!video) return;
        if (video && video.seekable && video.seekable.length > 0) {
          video.currentTime = video.seekable.start(0);
        } else if (video) {
          video.currentTime = 0;
        }
      }

      function closePlayer() {
        const section = document.getElementById('player-section');
        const video = document.getElementById('player-video');
        const videoWrap = document.querySelector('.player-video-wrap');
        const playerBar = document.querySelector('.player-bar');
        const info = document.getElementById('player-info');
        const titleEl = document.getElementById('player-epg-title');
        const descEl = document.getElementById('player-desc');
        const coverEl = document.getElementById('player-cover');
        const progressWrap = document.getElementById('player-progress-wrap');
        if (!section || !video || !videoWrap || !playerBar || !info || !titleEl || !descEl || !coverEl || !progressWrap) return;
        if (currentHls) { currentHls.destroy(); currentHls = null; }
        if (currentCard) { currentCard.classList.remove('playing'); currentCard = null; }
        video.pause();
        video.src = '';
        videoWrap.style.display = 'none';
        playerBar.classList.remove('video-active');
        playerBar.classList.add('idle');
        info.style.color = '';
        info.textContent = playerEnabled ? 'Vyberte kanál pro spuštění přehrávače' : '';
        titleEl.textContent = playerEnabled ? 'Přehrávač se otevře po kliknutí na kanál v seznamu níže.' : '';
        descEl.textContent = '';
        descEl.classList.remove('visible');
        coverEl.src = '';
        coverEl.classList.remove('visible');
        progressWrap.style.display = 'none';
        if (playerEnabled) section.classList.add('idle-state');
        section.classList.add('active');
      }

      function toggleModal(id, show, fetchUrl = null) {
        const modal = document.getElementById(id);
        if (show) {
          modal.classList.add('active');
          if (fetchUrl) {
            const body = document.getElementById('config-body');
            body.innerHTML = 'Načítám...';
            fetch(fetchUrl, {credentials: 'same-origin'})
              .then(r => r.json())
              .then(data => {
                body.innerHTML = Object.entries(data)
                  .map(([k, v]) => `<div class="config-row"><span class="config-key">${k}</span><span class="config-val">${v}</span></div>`)
                  .join('');
              });
          }
        } else {
          modal.classList.remove('active');
        }
      }

      function closeAllModals(e) {
        if (e.target.classList.contains('modal-overlay')) {
          document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('active'));
        }
      }

      // Progress bars
      function updateProgressBars() {
        const now = Date.now() / 1000;
        let needsRefresh = false;
        document.querySelectorAll('.ch-progress').forEach(el => {
          const start = parseInt(el.dataset.start);
          const end = parseInt(el.dataset.end);
          const duration = end - start;
          if (duration <= 0) return;
          if (now >= end) { needsRefresh = true; return; }
          const pct = Math.min(100, Math.max(0, (now - start) / duration * 100));
          el.querySelector('.ch-progress-bar').style.width = pct + '%';
        });
        if (needsRefresh) loadEpg();
      }

      // Catchup
      let catchupChannelId = '';
      let catchupChannelSlug = '';
      let catchupChannelName = '';
      let catchupChannelLogo = '';
      let catchupPrograms = [];
      let catchupCache = {};
      const dayNames = ['Ne', 'Po', 'Út', 'St', 'Čt', 'Pá', 'So'];

      function openCatchup(channelId, channelName, slug, channelLogo) {
        if (catchupChannelId !== channelId) catchupCache = {};
        catchupChannelId = channelId;
        catchupChannelSlug = slug;
        catchupChannelName = channelName;
        catchupChannelLogo = channelLogo;
        document.getElementById('catchup-title').innerHTML = '&#9202; <img src="' + channelLogo + '" alt="' + channelName + '">';
        const daysEl = document.getElementById('catchup-days');
        daysEl.innerHTML = '';
        let firstBtn = null;
        for (let i = 0; i >= -6; i--) {
          const d = new Date();
          d.setDate(d.getDate() + i);
          const dayLabel = i === 0 ? 'Dnes' : (i === -1 ? 'Včera' : dayNames[d.getDay()]);
          const dateLabel = d.getDate() + '.' + (d.getMonth()+1) + '.';
          const btn = document.createElement('button');
          btn.className = 'catchup-day-btn';
          btn.innerHTML = '<span class="day-name">' + dayLabel + '</span><span class="day-date">' + dateLabel + '</span>';
          btn.dataset.offset = i;
          btn.onclick = () => loadCatchupDay(i, btn);
          daysEl.appendChild(btn);
          if (i === 0) firstBtn = btn;
        }
        document.getElementById('catchup-content').innerHTML = '<p class="catchup-loading">Načítám program...</p>';
        toggleModal('catchup-modal', true);
        if (firstBtn) loadCatchupDay(0, firstBtn);
      }

      function loadCatchupDay(offset, btn) {
        document.querySelectorAll('.catchup-day-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const content = document.getElementById('catchup-content');
        const cacheKey = catchupChannelId + '_' + offset;
        if (catchupCache[cacheKey]) {
          renderCatchupPrograms(catchupCache[cacheKey], content);
          return;
        }
        content.innerHTML = '<p class="catchup-loading">Načítám program...</p>';
        fetch('/epg_channel/' + encodeURIComponent(catchupChannelId) + '/' + offset, {credentials: 'same-origin'})
          .then(r => r.json())
          .then(programs => {
            catchupCache[cacheKey] = programs;
            renderCatchupPrograms(programs, content);
          })
          .catch(() => {
            content.innerHTML = '<p class="catchup-loading">Chyba při načítání</p>';
          });
      }

      function renderCatchupPrograms(programs, content) {
        const nowTs = Math.floor(Date.now() / 1000);
        const past = programs.filter(p => p.startts < nowTs).sort((a, b) => b.startts - a.startts);
        if (!past.length) {
          content.innerHTML = '<p class="catchup-loading">Žádné pořady</p>';
          return;
        }
        catchupPrograms = past;
        let html = '<div class="catchup-list">';
        past.forEach((p, idx) => {
          const timeStr = formatTime(p.startts);
          html += '<div class="catchup-item" onclick="playCatchupIdx(' + idx + ')">';
          html += '<span class="ci-time">' + timeStr + '</span>';
          html += '<span class="ci-title">' + escapeHtml(p.title) + '</span>';
          html += '<span class="ci-play">&#9654;</span>';
          html += '</div>';
        });
        html += '</div>';
        content.innerHTML = html;
      }

      function escapeHtml(str) {
        const d = document.createElement('div');
        d.textContent = str;
        return d.innerHTML;
      }

      function playCatchupIdx(idx) {
        const p = catchupPrograms[idx];
        playCatchup(catchupChannelSlug, p.startts, p.endts, p.title, p.description, p.cover);
      }

      function playCatchup(slug, startTs, endTs, title, desc, cover) {
        toggleModal('catchup-modal', false);
        const section = document.getElementById('player-section');
        const video = document.getElementById('player-video');
        const videoWrap = document.querySelector('.player-video-wrap');
        const playerBar = document.querySelector('.player-bar');
        const info = document.getElementById('player-info');
        const titleEl = document.getElementById('player-epg-title');
        const descEl = document.getElementById('player-desc');
        const coverEl = document.getElementById('player-cover');
        const progressWrap = document.getElementById('player-progress-wrap');
        if (!section || !video || !videoWrap || !playerBar || !info || !titleEl || !descEl || !coverEl || !progressWrap) return;

        function formatCatchupDateTime(ts) {
          const d = new Date(parseInt(ts) * 1000);
          return d.toLocaleDateString('cs-CZ', {day:'numeric', month:'numeric'}) + ' ' + d.toLocaleTimeString('cs-CZ', {hour:'2-digit', minute:'2-digit', hour12:false});
        }
        const catchupTimeStr = formatCatchupDateTime(startTs) + ' - ' + formatTime(endTs);
        const catchupTimeLabel = '<span style="font-size:12px;color:var(--text2)">(' + catchupTimeStr + ')</span>';

        info.innerHTML = '&#9202; ' + catchupChannelName + ' ' + catchupTimeLabel;
        info.style.color = '';
        section.classList.remove('idle-state');
        playerBar.classList.remove('idle');
        playerBar.classList.add('video-active');
        videoWrap.style.display = '';
        titleEl.textContent = title;
        if (desc) { descEl.textContent = desc; descEl.classList.add('visible'); } else { descEl.textContent = ''; descEl.classList.remove('visible'); }
        if (cover) { coverEl.src = cover; coverEl.classList.add('visible'); } else { coverEl.src = ''; coverEl.classList.remove('visible'); }
        progressWrap.style.display = 'none';
        section.classList.add('active');
        section.scrollIntoView({ behavior: 'smooth', block: 'start' });

        if (currentCard) { currentCard.classList.remove('playing'); currentCard = null; }
        if (currentHls) { currentHls.destroy(); currentHls = null; }

        fetch('/stream_url/' + slug + '?start_ts=' + startTs + '&end_ts=' + endTs, {credentials: 'same-origin'})
          .then(r => {
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
          })
          .then(data => {
            if (data.error || !data.url) {
              throw new Error(data.error || 'Stream není dostupný');
            }
            info.innerHTML = '&#9202; ' + catchupChannelName + ' ' + catchupTimeLabel;
            if (Hls.isSupported()) {
              currentHls = new Hls();
              currentHls.loadSource(data.url);
              currentHls.attachMedia(video);
              currentHls.on(Hls.Events.MANIFEST_PARSED, () => video.play());
            } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
              video.src = data.url;
              video.play();
            }
          })
          .catch(err => {
            console.error('Chyba archivu:', err);
            info.innerHTML = 'Chyba: ' + catchupChannelName + ' ' + catchupTimeLabel + ' &middot; ' + err.message;
            info.style.color = 'var(--red)';
          });
      }

      // Async EPG loading
      function loadEpg() {
        fetch('/epg_live', {credentials: 'same-origin'})
          .then(r => r.json())
          .then(data => {
            document.querySelectorAll('.channel-card').forEach(card => {
              const chId = card.dataset.channelId;
              const epgEl = card.querySelector('.ch-epg');
              const progressEl = card.querySelector('.ch-progress');
              const emptyEl = card.querySelector('.ch-epg-empty');
              const now = data[chId];
              if (now) {
                card.dataset.epgStartts = now.startts;
                card.dataset.epgEndts = now.endts;
                card.dataset.epgTitle = now.title;
                card.dataset.epgDesc = now.description || '';
                card.dataset.epgCover = now.cover || '';
                epgEl.textContent = now.title;
                epgEl.style.display = '';
                progressEl.dataset.start = now.startts;
                progressEl.dataset.end = now.endts;
                progressEl.style.display = '';
                if (emptyEl) emptyEl.style.display = 'none';
              } else {
                epgEl.style.display = 'none';
                progressEl.style.display = 'none';
                if (emptyEl) { emptyEl.textContent = 'EPG není k dispozici'; emptyEl.style.display = ''; }
              }
            });
            updateProgressBars();
          })
          .catch(() => {
            document.querySelectorAll('.ch-epg-empty').forEach(el => {
              el.textContent = 'EPG není k dispozici';
            });
          });
      }
      loadEpg();
      setInterval(() => { updateProgressBars(); updatePlayerProgress(); }, 60000);

      function toggleFilter() {
        const input = document.getElementById('filter-input');
        const btn = document.getElementById('filter-toggle');
        if (input.style.display === 'none') {
          input.style.display = '';
          input.focus();
          btn.style.color = 'var(--accent)';
        } else {
          input.style.display = 'none';
          input.value = '';
          btn.style.color = '';
          filterChannels();
        }
      }

      function filterChannels() {
        const query = document.getElementById('filter-input').value.toLowerCase();
        document.querySelectorAll('.channel-card').forEach(card => {
          const name = card.querySelector('.ch-name').textContent.toLowerCase();
          card.style.display = name.includes(query) ? '' : 'none';
        });
      }
    </script>
  </body>
</html>