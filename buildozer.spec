[app]
title = MusicTagger
package.name = musictagger
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,mp3
version = 0.1
requirements = python3,kivy,mutagen,requests
orientation = portrait

[buildozer]
log_level = 2
warn_on_root = 1

[android]
android.api = 33
android.ndk = 25b
# 关键修复：使用预编译的 libffi，避免重新编译
android.skip_update = True
android.accept_sdk_license = True
# 添加必要的编译标志
android.ndk_path = /home/runner/.buildozer/android/platform/android-ndk-r28c
android.sdk_path = /home/runner/.buildozer/android/platform/android-sdk

# Add any extra permissions your app needs
android.permissions = INTERNET
