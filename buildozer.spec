[app]
title = Seismic Guard Jabar
package.name = seismicguard
package.domain = org.seismicguard
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,xml

version = 1.0
requirements = python3,kivy,requests,urllib3,certifi,chardet,idna

orientation = portrait
fullscreen = 0
android.permissions = INTERNET,VIBRATE,WAKE_LOCK

# Kunci python-for-android agar tidak mengambil versi master Python 3.14 yang rusak
p4a.branch = release-2024.01.21

android.api = 33
android.minapi = 21
android.ndk = 25b
android.build_tools_version = 33.0.2
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
