#!/bin/sh
# Pone en el addon de Telegram de la caja el descifrado nativo (libtgige.so) y reinicia Kodi.
#   sh tools/instalar_cifrado.sh
#
# Por qué: sin él, el addon descifra en Python (una llamada por cada 16 bytes) y abrir un vídeo de Telegram tarda
# 10–24 s; con él, el autor midió ~5 veces más velocidad. El .so se compiló aquí (25/11/2026) con el NDK oficial de
# Google desde tools/native/tgige.c del addon (44 líneas revisadas: solo encadena bloques AES de la propia Kodi), y
# el addon lo comprueba contra su propio cálculo antes de usarlo. Está en ~/.config/kodi-papa/libtgige-armv7.so.
# No hace nada si la caja está reproduciendo algo.
set -e
ADB="$HOME/Library/Android/sdk/platform-tools/adb"
SO="$HOME/.config/kodi-papa/libtgige-armv7.so"
DIR=/storage/emulated/0/Android/data/org.xbmc.kodi/files/.kodi/addons/plugin.video.telegram/resources/lib/_native/ige/arm
"$ADB" connect 192.168.1.167:5555 >/dev/null
if "$ADB" shell "su 0 grep -q . /dev/null" 2>/dev/null; then :; fi
PLAYING=$(printf '{"jsonrpc":"2.0","id":1,"method":"Player.GetActivePlayers"}' | nc -w 3 192.168.1.167 9090 | grep -c playerid || true)
if [ "$PLAYING" != "0" ]; then echo "La caja está reproduciendo algo: no hago nada."; exit 1; fi
"$ADB" push "$SO" /data/local/tmp/libtgige.so >/dev/null
"$ADB" shell "su 0 sh -c 'mkdir -p $DIR && cp /data/local/tmp/libtgige.so $DIR/ && chown -R u0_a84:u0_a84 $DIR/../.. && rm /data/local/tmp/libtgige.so'"
echo "Copiado. Reiniciando Kodi…"
printf '{"jsonrpc":"2.0","id":1,"method":"Application.Quit"}' | nc -w 3 192.168.1.167 9090 >/dev/null || true
i=0; while [ -n "$("$ADB" shell pidof org.xbmc.kodi)" ] && [ $i -lt 20 ]; do sleep 3; i=$((i+1)); done
[ -n "$("$ADB" shell pidof org.xbmc.kodi)" ] && "$ADB" shell am force-stop org.xbmc.kodi
"$ADB" shell am start -n org.xbmc.kodi/.Splash >/dev/null
echo "Kodi arrancando. En un minuto, el addon de Telegram debería decir «OpenSSL native … fast»."
