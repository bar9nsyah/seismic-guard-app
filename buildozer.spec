[app]
title = Seismic Guard Jabar
package.name = seismicguard
package.domain = org.seismicguard
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,xml

version = 1.0
requirements = python3,kivy==2.3.0,requests,urllib3,certifi,chardet,idna

orientation = portrait
fullscreen = 0
android.permissions = INTERNET,VIBRATE,WAKE_LOCK

android.api = 33
android.minapi = 21
android.ndk = 25b
android.build_tools_version = 33.0.2
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
