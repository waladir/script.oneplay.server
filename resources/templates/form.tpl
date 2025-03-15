<html>
  <head>
      <title>Oneplay Server</title>
  </head>
  <script>
    function myFunction(text) {
      navigator.clipboard.writeText(text);
    }   
  </script
  <body>
    <h2>Oneplay Server</h2>
      Diskuze a podpora k Oneplay Serveru: <a href="https://www.xbmc-kodi.cz/prispevek-oneplay-server">https://www.xbmc-kodi.cz/prispevek-oneplay-server</a>
    <h3><font color="red">{{ message }}</font></h3>
    <form method="post" action="/">
      <input type="hidden" name="action" value="reset_channels">
      <input type="submit" value="Resetovat kanály">
    </form>
    <form method="post" action="/">
      <input type="hidden" name="action" value="reset_session">
      <input type="submit" value="Resetovat session">
    </form>
    <hr>
    <p>
    <table>
    <tr><td><b>Playlist</b></td><td><a href="{{ playlist_url }}">{{ playlist_url }}</a></td><td><button onclick="myFunction('{{ playlist_url }}')"/><img src="/img/clipboard.png" width="15" height="15"></button></td></tr>
    <tr><td><b>Playlist pro TVheadend</b></td><td><a href="{{ playlist_tvheadend_url }}">{{ playlist_tvheadend_url }}</a></td><td><button onclick="myFunction('{{ playlist_tvheadend_url }}')"/><img src="/img/clipboard.png" width="15" height="15"></button></td></tr>
    <tr><td><b>EPG</b></td><td><a href="{{ epg_url }}">{{ epg_url }}</a></td><td><button onclick="myFunction('{{ epg_url }}')"/><img src="/img/clipboard.png" width="15" height="15"></button></td></tr>
    <table>
    <hr>
    <h3>Kanály</h3>
    <table>
% for item in playlist:
      <tr><td><img height="30px" width="45px" src="{{ item['logo'] }}"></td><td><a href="{{ item['url'] }}">{{ item['name'] }}</a></td><td><button onclick="myFunction('{{ item['url'] }}')"/><img src="/img/clipboard.png" width="15" height="15"></button></td></tr>
% end
    </table>
  </body>
</html>