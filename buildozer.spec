[app]
title = ReviewPay
package.name = reviewpay
package.domain = com.reviewpay.app
source.dir = .
source.include_exts = py,png,jpg,json
version = 1.0.0
requirements = python3,kivy==2.3.0,requests,pytz,pillow,certifi
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,VIBRATE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.arch = arm64-v8a
[buildozer]
log_level = 2
