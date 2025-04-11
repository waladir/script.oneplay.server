<h1>Oneplay Server</h1>

Oneplay Server slouží jako alternativa k IPTV Web Serveru pro Oneplay. Lze ho používat buď jako doplněk v Kodi i samostatně.

<a href="https://www.xbmc-kodi.cz/prispevek-oneplay-server">Vlákno na fóru XBMC-Kodi.cz</a><br><br>

<b><u>Kodi</u></b>

Nainstalujte doplněk a v jeho nastavení vyplňte přihlašovací údaje, deviceid (libovolný alfanumerický řetězec) a IP adresu nebo jméno serveru. Po uložení nastavení restartujte Kodi nebo zakažte a povolte doplněk.

<b><u>Samostatný skript</u></b>

Oneplay Server pro své fungování vyžaduje python moduly bottle a websocket. Nainstaluje buď jako balíček OS nebo pomocí pip3 (pip3 install &lt;module&gt;)

Rozbalte zip, zkopírujte config.txt.sample na config.txt a v něm vyplňte jméno, heslo, deviceid a IP adresu nebo jméno serveru. Server spusťte z adresáře service.oneplay.server spuštěním python3 server.py.<br>
Pokud chcete Oneplay Server spustit na linuxu se systemd jako službu, jako root/přes sudo:
- zkopírujte z adresáře scripts soubor oneplay_server.service do /etc/systemd/system/
- systemctl daemon-reload
- systemctl enable oneplay_server
- systemctl start oneplay_server


<b><u>TVheadend</u></b>

Pro použití Oneplay Serveru v TVheadendu je potřeba mít na nainstalovaný ffmpeg (na stroji s TVH). Pro načtení EPG přes External XMLTV grabber pak ještě socat.

V config.txt zkontrolujte nastavení cesta_ffmpeg (viz config.txt.sample), v případě Kodi pak analogické položky v nastavení. Při vytváření sítě v TVheadendu použijte adresu http://<adresa nebo jméno serveru>:<port (defaultně 8082)>/playlist/tvheadend/streamlink, např. http://127.0.0.1:8082/playlist/tvheadend.

U EPG je jednou z variant využití External XMLTV grabberu. Nejprve ho je potřeba v TVheadnedu povolit (Program/Channels - EPG Grabber modules). V adresáři scripts je připravený skript k epg.sh, který stáhne EPG z Oneplay Server a obsah pošle External XMLTV grabberu. Zkontrolujte v něm cestu xmltv.sock (vytvoří se po povolení grabberu) a URL Oneplay Serveru.

<b><u>URL</u></b>

Playlist je dustupný na http://<adresa nebo jméno serveru>:<port (defaultně 8082)>/playlist, např. http://127.0.0.1:8082/playlist

EPG lze pak stáhnout z http://<adresa nebo jméno serveru>:<port (defaultně 8082)>/epg, např. http://127.0.0.1:8082/epg

Na http://<adresa nebo jméno serveru>:<port (defaultně 8082)>, např. http://127.0.0.1:8082 je možné stiskem tlačítka vynutit načtení kanálů nebo vytvotvoření nové sessiony.

<b><u>Změny</u></b>
v1.1.6 (11.4.2025)
- ošetření chyb v EPG

v1.1.5 (29.3.2025)
- ošetření jiného typu EPG pro MD

v1.1.4 (27.3.2025)
- změna typu streamu
- úprava tagu v playlistu a volání catchupu

v1.1.3 (22.3.2025)
- oprava načítání konfigurace dockeru
- ošetření chyb při stahování EPG
- oprava chyby u MD v živém vysílání
- zobrazení verze

v1.1.2 (21.3.2025)
- přidání podpory pro běh v dockeru
- doplnění tagu do playlistu
