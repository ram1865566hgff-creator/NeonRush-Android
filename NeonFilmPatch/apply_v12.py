#!/usr/bin/env python3
"""NeonFilm 1.2: resilient camera-video playback, orientation-safe texture, decoder switch."""
from pathlib import Path
src=Path("MoviePlayer/app/src/main/java/ru/neonfilm/player/MainActivity.java")
s=src.read_text(encoding="utf-8")
def swap(a,b):
    global s
    n=s.count(a)
    if n!=1:
        raise ValueError("Expected exactly one occurrence ("+str(n)+"): "+repr(a[:130]))
    s=s.replace(a,b,1)

# MediaCodec on several OEM firmware versions can freeze the first frame without a VLC error.
# Start in software compatibility mode; allow hardware acceleration via menu.
swap("    private boolean triedSoftwareDecoder;",
"""    private boolean triedSoftwareDecoder;
    private boolean preferSoftwareDecoder = true;
    private long lastProgressAtMs;
    private long lastProgressPositionMs = -1;
    private boolean playbackFailureShown;""")
swap('        subtitleDisabled = prefs.getBoolean("subtitle_disabled", false);',
"""        subtitleDisabled = prefs.getBoolean("subtitle_disabled", false);
        preferSoftwareDecoder = prefs.getBoolean("software_decoder", true);
        getWindow().getDecorView().setBackgroundColor(Color.BLACK);
        getWindow().setBackgroundDrawableResource(android.R.color.black);""")
swap("        player.attachViews(videoView, null, true, false);",
"""        // TextureView stays in the same composited window during device rotation.
        player.attachViews(videoView, null, true, true);
        player.setVideoScale(MediaPlayer.ScaleType.SURFACE_BEST_FIT);
        videoView.addOnLayoutChangeListener((v, l, t, r, b, oldL, oldT, oldR, oldB) -> {
            if (r - l > 0 && b - t > 0 && (r - l != oldR - oldL || b - t != oldB - oldT)) {
                videoView.post(() -> {
                    if (player != null) player.updateVideoSurfaces();
                });
            }
        });""")
swap("        videoView = new VLCVideoLayout(this);",
"""        videoView = new VLCVideoLayout(this);
        videoView.setBackgroundColor(Color.BLACK);""")
swap("""            } else if (event.type == MediaPlayer.Event.EncounteredError) {
                runOnUiThread(() -> {
                    // Camera clips occasionally fail with a device's hardware decoder.
                    if (currentUri != null && !triedSoftwareDecoder) {
                        triedSoftwareDecoder = true;
                        try {
                            startPlayback(currentUri, true);
                            showHint("Пробуем программное декодирование");
                        } catch (Exception error) {
                            reportPlaybackError(error);
                        }
                    } else {
                        reportPlaybackError(null);
                    }
                });
""",
"""            } else if (event.type == MediaPlayer.Event.EncounteredError) {
                runOnUiThread(() -> recoverDecoder("Ошибка видеодекодера"));
""")
swap("            triedSoftwareDecoder = false;\n            accumulatedSeekSeconds = 0;",
"""            triedSoftwareDecoder = false;
            playbackFailureShown = false;
            accumulatedSeekSeconds = 0;""")
swap("            startPlayback(uri, false);",
"            startPlayback(uri, preferSoftwareDecoder);")
swap("""            media.setHWDecoderEnabled(!softwareDecoder, false);
            media.addOption(":file-caching=350");""",
"""            media.setHWDecoderEnabled(!softwareDecoder, false);
            media.addOption(":file-caching=900");
            media.addOption(":network-caching=900");""")
swap("""        player.stop();
        closeVideoDescriptor();
        videoDescriptor = getContentResolver().openFileDescriptor(uri, "r");""",
"""        player.stop();
        closeVideoDescriptor();
        lastProgressAtMs = SystemClock.elapsedRealtime();
        lastProgressPositionMs = -1;
        videoDescriptor = getContentResolver().openFileDescriptor(uri, "r");""")
swap("""                    if (player.isPlaying() && position > 0) {
                        int second = (int)(position / 1000);""",
"""                    checkPlaybackProgress(position);
                    if (player.isPlaying() && position > 0) {
                        int second = (int)(position / 1000);""")
swap("""    private void closeVideoDescriptor() {""",
"""    private void checkPlaybackProgress(long position) {
        if (player == null || currentUri == null) return;
        long now = SystemClock.elapsedRealtime();
        if (!player.isPlaying()) {
            lastProgressAtMs = now;
            lastProgressPositionMs = position;
            return;
        }
        if (position > lastProgressPositionMs + 200) {
            lastProgressPositionMs = position;
            lastProgressAtMs = now;
        } else if (!triedSoftwareDecoder && now - lastProgressAtMs >= 8000) {
            recoverDecoder("Видео зависло. Переключаем декодер");
        } else if (triedSoftwareDecoder && !playbackFailureShown
                && now - lastProgressAtMs >= 20000) {
            playbackFailureShown = true;
            notifyUser("Видео не воспроизводится. Попробуйте другой режим в меню");
            setControlsVisible(true);
        }
    }
    private void recoverDecoder(String reason) {
        if (player == null || currentUri == null) return;
        if (triedSoftwareDecoder) {
            reportPlaybackError(null);
            return;
        }
        triedSoftwareDecoder = true;
        long position = Math.max(0, player.getTime());
        if (position > 0) resumeAtMs = position;
        preferSoftwareDecoder = !preferSoftwareDecoder;
        try {
            startPlayback(currentUri, preferSoftwareDecoder);
            showHint(reason);
        } catch (Exception e) {
            reportPlaybackError(e);
        }
    }
    private void toggleDecoderMode() {
        if (currentUri == null) {
            notifyUser("Сначала выберите видео");
            return;
        }
        long position = player == null ? 0 : Math.max(0, player.getTime());
        if (position > 0) resumeAtMs = position;
        preferSoftwareDecoder = !preferSoftwareDecoder;
        prefs.edit().putBoolean("software_decoder", preferSoftwareDecoder).apply();
        triedSoftwareDecoder = false;
        playbackFailureShown = false;
        try {
            startPlayback(currentUri, preferSoftwareDecoder);
            showHint(preferSoftwareDecoder ? "Совместимый режим" : "Аппаратное ускорение");
        } catch (Exception e) { reportPlaybackError(e); }
    }
    private void closeVideoDescriptor() {""")
swap("""            "Недавно открытые"
        };""",
"""            "Недавно открытые",
            preferSoftwareDecoder ? "Декодирование: совместимое (сменить)" :
                    "Декодирование: аппаратное (сменить)"
        };""")
swap("                        case 5: showRecentMenu(); break;",
"""                        case 5: showRecentMenu(); break;
                        case 6: toggleDecoderMode(); break;""")
swap("""        updateOrientationLayout();
    }
    @Override protected void onStop() {""",
"""        updateOrientationLayout();
        if (videoView != null) {
            videoView.requestLayout();
            videoView.postDelayed(() -> {
                if (player != null) player.updateVideoSurfaces();
            }, 240);
        }
    }
    @Override protected void onStop() {""")
src.write_text(s,encoding="utf-8")

manifest=Path("MoviePlayer/app/src/main/AndroidManifest.xml")
m=manifest.read_text(encoding="utf-8")
m=m.replace('android:allowBackup="false"','android:allowBackup="false"\n        android:resizeableActivity="true"\n        android:maxAspectRatio="3.0"')
manifest.write_text(m,encoding="utf-8")
gradle=Path("MoviePlayer/app/build.gradle")
b=gradle.read_text(encoding="utf-8")
b=b.replace("versionCode 2","versionCode 3").replace("versionName '1.1'","versionName '1.2'")
gradle.write_text(b,encoding="utf-8")
print("Applied NeonFilm v1.2 stability and layout fixes")
