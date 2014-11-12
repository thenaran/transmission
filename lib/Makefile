install:
	@sed -i s/debian-transmission/root/g /etc/init.d/transmission-daemon 
	@cp settings.json /etc/transmission-daemon;rm settings.json
	@chmod 777 /etc/transmission-daemon/settings.json
	@mv /usr/share/transmission/web /usr/share/transmission/web_old
	@mv /lib/web /usr/share/transmission/web
	@find /usr/share/transmission/web -exec touch -c -h -m -t 201401010000 {} \;
