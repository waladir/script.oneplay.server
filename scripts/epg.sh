#!/bin/bash
XMLTV_SOCK=/home/hts/.hts/tvheadend/epggrab/xmltv.sock
EPG_URL=http://localhost:8082/epg
EPG_FILE=/tmp/epg.xml

wget ${EPG_URL} -O ${EPG_FILE}
cat ${EPG_FILE} | /usr/bin/socat - UNIX-CONNECT:${XMLTV_SOCK}

