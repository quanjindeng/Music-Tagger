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
# For release signing, the workflow will inject the keystore file and set these values via sed before running buildozer.
# android.release_keystore = release.keystore
# android.release_keyalias = myalias
# android.release_keypass = mykeypass
# android.release_keystore_password = mykeystorepass

# Add any extra permissions your app needs
android.permissions = INTERNET
