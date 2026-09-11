[app]
title = Seismic Guard Jabar
package.name = seismicguard
package.domain = org.seismic
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,mp3
version = 1.0
requirements = python3,kivy,requests,urllib3,chardet,idna
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,VIBRATE,WAKE_LOCK

[buildozer]
log_level = 2
warn_on_root = 1
