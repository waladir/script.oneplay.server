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
      #player-section video { width: 100%; background: #000; display: block; aspect-ratio: 16/9; }
      .player-bar {
        display: flex;
        align-items: center;
        padding: 12px 16px;
        gap: 10px;
        background: var(--surface2);
      }
      .player-bar .name { font-weight: 600; font-size: 15px; color: var(--accent); }
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

      /* Channels Grid */
      .channels-header { font-size: 12px; color: var(--text2); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; }
      .channel-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 10px; }
      .channel-card {
        display: flex;
        align-items: center;
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
      .ch-name { font-size: 14px; font-weight: 500; flex: 1; }
      .ch-copy { background: none; border: none; color: var(--text2); cursor: pointer; padding: 5px; font-size: 16px; opacity: 0.6; transition: 0.2s; }
      .ch-copy:hover { color: var(--accent); opacity: 1; }

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
        <h1>Oneplay <span>Server</span> {{ version }}</h1>
        <div style="display:flex;align-items:center;gap:12px">
          <a href="https://www.xbmc-kodi.cz/prispevek-oneplay-server" target="_blank">Podpora &amp; diskuze &rarr;</a>
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
              <button class="dd-item" onclick="toggleModal('links-modal', true)">&#128279; Odkazy</button>
            </div>
          </div>
        </div>
      </header>

      % if message:
      <div class="message">{{ message }}</div>
      % end

      <div id="player-section">
        <video id="player-video" controls autoplay></video>
        <div class="player-bar">
          <span id="player-info" class="name"></span>
          <button class="close-btn" onclick="closePlayer()">&#10005; Zavřít přehrávač</button>
        </div>
      </div>

      <h3 class="channels-header">Seznam kanálů</h3>
      <div class="channel-grid">
        % for item in playlist:
        <div class="channel-card" onclick="playChannel('{{ item['slug'] }}', '{{ item['name'] }}', this)">
          <img src="{{ item['logo'] }}" alt="" loading="lazy">
          <span class="ch-name">{{ item['name'] }}</span>
          <button class="ch-copy" onclick="event.stopPropagation(); copyText('{{ item['url'] }}', this)" title="Kopírovat URL">&#128203;</button>
        </div>
        % end
      </div>

      <div class="modal-overlay" id="links-modal" onclick="closeAllModals(event)">
        <div class="modal">
          <div class="modal-header">
            <h3>&#128279; Externí odkazy</h3>
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
    </div>

    <script>
      let currentHls = null;
      let currentCard = null;

      // Settings dropdown
      function toggleSettings(e) {
        e.stopPropagation();
        document.getElementById('settings-dropdown').classList.toggle('active');
      }
      document.addEventListener('click', function() {
        document.getElementById('settings-dropdown').classList.remove('active');
      });

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

      function playChannel(slug, name, card) {
        const section = document.getElementById('player-section');
        const video = document.getElementById('player-video');
        const info = document.getElementById('player-info');

        info.textContent = `Načítám: ${name}...`;
        section.classList.add('active');
        section.scrollIntoView({ behavior: 'smooth', block: 'start' });

        if (currentCard) currentCard.classList.remove('playing');
        currentCard = card;
        card.classList.add('playing');

        if (currentHls) {
          currentHls.destroy();
          currentHls = null;
        }

        fetch(`/stream_url/${slug}`)
          .then(r => r.json())
          .then(data => {
            if (!data.url) throw new Error('URL nenalezena');
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
            info.textContent = `Chyba: ${err.message}`;
            info.style.color = 'var(--red)';
          });
      }

      function closePlayer() {
        const section = document.getElementById('player-section');
        const video = document.getElementById('player-video');
        if (currentHls) { currentHls.destroy(); currentHls = null; }
        if (currentCard) { currentCard.classList.remove('playing'); currentCard = null; }
        video.pause();
        video.src = '';
        section.classList.remove('active');
      }

      function toggleModal(id, show, fetchUrl = null) {
        const modal = document.getElementById(id);
        if (show) {
          modal.classList.add('active');
          if (fetchUrl) {
            const body = document.getElementById('config-body');
            body.innerHTML = 'Načítám...';
            fetch(fetchUrl)
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
    </script>
  </body>
</html>