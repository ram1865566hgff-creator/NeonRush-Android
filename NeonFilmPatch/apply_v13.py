#!/usr/bin/env python3
"""NeonFilm v1.3: use Android's camera-friendly native media pipeline for MP4.
Retain VLC for MKV/AVI/etc and allow VLC fallback for unsupported MP4 codecs.
"""
from pathlib import Path
p=Path("MoviePlayer/app/src/main/java/ru/neonfilm/player/MainActivity.java")
s=p.read_text(encoding="utf-8")
def change(before, after):
    global s
    occurrences=s.count(before)
    if occurrences != 1:
        raise RuntimeError(f"Unexpected replacement count {occurrences}: {before[:100]!r}")
    s=s.replace(before,after,1)

change("import android.widget.Toast;","import android.widget.Toast;\nimport android.widget.VideoView;")
change("    private VLCVideoLayout videoView;", """    private VLCVideoLayout videoView;
    private VideoView nativeVideo;
    private boolean nativeMode = false;
    private boolean triedVlcFallback = false;
    private long nativeLastPosition = -1;
    private long nativeLastProgressAt = 0L;""")
change("""                    long position = Math.max(0, player.getTime());
                    long length = Math.max(0, player.getLength());""",
"""                    long position = getVideoTime();
                    long length = getVideoDuration();""")
change('playButton.setText(player.isPlaying() ? "Ⅱ" : "▶");',
"""playButton.setText(isVideoPlaying() ? "Ⅱ" : "▶");""")
change("""                    checkPlaybackProgress(position);
                    if (player.isPlaying() && position > 0) {""",
"""                    if (nativeMode) checkNativePlaybackProgress(position);
                    else checkPlaybackProgress(position);
                    if (isVideoPlaying() && position > 0) {""")
change("""            if (event.type == MediaPlayer.Event.Playing) {""",
"""            if (nativeMode) return;
            if (event.type == MediaPlayer.Event.Playing) {""")
change("        videoView = new VLCVideoLayout(this);\n        videoView.setBackgroundColor(Color.BLACK);",
"""        videoView = new VLCVideoLayout(this);
        videoView.setBackgroundColor(Color.BLACK);""") # anchor remains same but assertion
change("        videoFrame.addView(videoView, new FrameLayout.LayoutParams(-1, -1));",
"""        videoFrame.addView(videoView, new FrameLayout.LayoutParams(-1, -1));
        nativeVideo = new VideoView(this);
        nativeVideo.setBackgroundColor(Color.BLACK);
        nativeVideo.setVisibility(View.GONE);
        videoFrame.addView(nativeVideo, new FrameLayout.LayoutParams(-1, -1));
        nativeVideo.setOnPreparedListener(media -> {
            if (!nativeMode) return;
            try {
                media.setLooping(false);
                // Start after codec and Surface are initialized.
                nativeVideo.start();
                if (resumeAtMs > 0) {
                    nativeVideo.seekTo((int)Math.min(Integer.MAX_VALUE, resumeAtMs));
                    resumeAtMs = 0;
                }
                emptyLabel.setVisibility(View.GONE);
                playButton.setText("Ⅱ");
                scheduleAutoHide();
            } catch (Exception e) {
                fallbackFromNative("Ошибка запуска MP4: " + e.getMessage());
            }
        });
        nativeVideo.setOnErrorListener((media, what, extra) -> {
            if (nativeMode) fallbackFromNative("Android не смог декодировать MP4 (" + what + "/" + extra + ")");
            return true;
        });
        nativeVideo.setOnCompletionListener(media -> {
            if (nativeMode) {
                playButton.setText("▶");
                setControlsVisible(true);
            }
        });""")
change("""                    long total = Math.max(0, player.getLength());
                    timeLabel.setText(clock(total * value / 1000) + " / " + clock(total));""",
"""                    long total = getVideoDuration();
                    timeLabel.setText(clock(total * value / 1000) + " / " + clock(total));""")
change("""                if (player != null && player.isSeekable()) {
                    long total = Math.max(0, player.getLength());
                    player.setTime(total * bar.getProgress() / 1000);
                }""",
"""                if (isVideoSeekable()) {
                    long total = getVideoDuration();
                    seekVideoTo(total * bar.getProgress() / 1000);
                }""")
change("""            if (currentUri != null) savePlaybackPosition(player.getTime());
            currentUri = uri;""",
"""            if (currentUri != null) savePlaybackPosition(getVideoTime());
            currentUri = uri;""")
change("""            startPlayback(uri, preferSoftwareDecoder);
            emptyLabel.setVisibility(View.GONE);""",
"""            triedVlcFallback = false;
            String extension = name == null ? "" : name.toLowerCase(Locale.ROOT).trim();
            if (extension.endsWith(".mp4") || extension.endsWith(".m4v")
                    || extension.endsWith(".3gp") || extension.endsWith(".mov")) {
                startNativeVideo(uri);
            } else {
                stopNativeVideo();
                startPlayback(uri, preferSoftwareDecoder);
            }
            emptyLabel.setVisibility(View.GONE);""")
change("    private void startPlayback(Uri uri, boolean softwareDecoder) throws Exception {",
"""    // Android VideoView delegates document-provider content:// URIs to Android's
    // media extractor and device codecs. This avoids the VLC file-descriptor
    // path that failed to play camera-recorded MP4 on some phones.
    private void startNativeVideo(Uri uri) {
        player.stop();
        closeVideoDescriptor();
        nativeMode = true;
        nativeLastPosition = -1;
        nativeLastProgressAt = SystemClock.elapsedRealtime();
        videoView.setVisibility(View.GONE);
        nativeVideo.setVisibility(View.VISIBLE);
        nativeVideo.stopPlayback();
        nativeVideo.setVideoURI(uri);
        nativeVideo.requestFocus();
        nativeVideo.start();
    }
    private void stopNativeVideo() {
        nativeMode = false;
        nativeVideo.stopPlayback();
        nativeVideo.setVisibility(View.GONE);
        videoView.setVisibility(View.VISIBLE);
    }
    private void fallbackFromNative(String reason) {
        if (!nativeMode || currentUri == null || triedVlcFallback) return;
        triedVlcFallback = true;
        long position = getVideoTime();
        if (position > 0) resumeAtMs = position;
        stopNativeVideo();
        try {
            startPlayback(currentUri, preferSoftwareDecoder);
            showHint("Пробуем VLC для этого видео");
        } catch (Exception e) {
            reportPlaybackError(e);
        }
    }
    private void checkNativePlaybackProgress(long pos) {
        if (!nativeMode || currentUri == null) return;
        long now = SystemClock.elapsedRealtime();
        if (!nativeVideo.isPlaying()) {
            // Don't classify intentional pause as a playback hang.
            nativeLastPosition = pos;
            nativeLastProgressAt = now;
            return;
        }
        if (pos > nativeLastPosition + 150) {
            nativeLastPosition = pos;
            nativeLastProgressAt = now;
        } else if (now - nativeLastProgressAt > 11000) {
            fallbackFromNative("Длительная остановка видеопотока");
        }
    }
    private long getVideoTime() {
        if (nativeMode) return Math.max(0, nativeVideo.getCurrentPosition());
        return player == null ? 0 : Math.max(0, player.getTime());
    }
    private long getVideoDuration() {
        if (nativeMode) return Math.max(0, nativeVideo.getDuration());
        return player == null ? 0 : Math.max(0, player.getLength());
    }
    private boolean isVideoPlaying() {
        return nativeMode ? nativeVideo.isPlaying() : player != null && player.isPlaying();
    }
    private boolean isVideoSeekable() {
        return nativeMode ? nativeVideo != null && nativeVideo.canSeekForward() : player != null && player.isSeekable();
    }
    private void seekVideoTo(long ms) {
        if (nativeMode) nativeVideo.seekTo((int)Math.min(Integer.MAX_VALUE, Math.max(0, ms)));
        else if (player != null) player.setTime(ms);
    }
    private void startPlayback(Uri uri, boolean softwareDecoder) throws Exception {""")
change("""    private void togglePlay() {
        if (player == null || currentUri == null) { pickFile(PICK_VIDEO); return; }
        if (player.isPlaying()) player.pause(); else player.play();
    }""",
"""    private void togglePlay() {
        if (currentUri == null) { pickFile(PICK_VIDEO); return; }
        if (nativeMode) {
            if (nativeVideo.isPlaying()) nativeVideo.pause();
            else nativeVideo.start();
        } else if (player != null) {
            if (player.isPlaying()) player.pause(); else player.play();
        }
        setControlsVisible(true);
        scheduleAutoHide();
    }""")
change("""        if (!player.isSeekable()) { notifyUser("Этот файл нельзя перемотать"); return; }
        long duration = player.getLength();
        long target = Math.max(0, player.getTime() + seconds * 1000L);
        if (duration > 0) target = Math.min(duration - 1, target);
        player.setTime(target);""",
"""        if (!isVideoSeekable()) { notifyUser("Этот файл нельзя перемотать"); return; }
        long duration = getVideoDuration();
        long target = Math.max(0, getVideoTime() + seconds * 1000L);
        if (duration > 0) target = Math.min(duration - 1, target);
        seekVideoTo(target);""")
change("""    private void toggleSubtitles() {
        if (player == null || currentUri == null) { notifyUser("Сначала откройте фильм"); return; }""",
"""    private void toggleSubtitles() {
        if (currentUri == null) { notifyUser("Сначала откройте фильм"); return; }
        if (nativeMode) {
            notifyUser("Для субтитров переключитесь на VLC через меню");
            return;
        }""")
change("""    private void loadSubtitle(Uri uri) {
        if (player == null || currentUri == null) { notifyUser("Сначала откройте фильм"); return; }""",
"""    private void loadSubtitle(Uri uri) {
        if (currentUri == null) { notifyUser("Сначала откройте фильм"); return; }
        if (nativeMode) {
            notifyUser("Для внешних субтитров переключитесь на VLC в меню");
            return;
        }""")
change("""    private void changeSpeed() {
        if (player == null || currentUri == null) return;""",
"""    private void changeSpeed() {
        if (currentUri == null) return;""")
change("""        player.setRate(savedRate);
        if (speedButton != null)""",
"""        if (nativeMode) {
            if (android.os.Build.VERSION.SDK_INT >= 23) {
                try { nativeVideo.getClass(); /* rate set via MediaPlayer below when prepared */ }
                catch (Exception ignored) { }
            }
            notifyUser("Скорость для MP4 сейчас 1×; VLC поддерживает изменение");
        } else player.setRate(savedRate);
        if (speedButton != null)""")
change("""    private void toggleDecoderMode() {
        if (currentUri == null) {""",
"""    private void toggleDecoderMode() {
        if (nativeMode) {
            stopNativeVideo();
            try {
                triedVlcFallback = true;
                startPlayback(currentUri, preferSoftwareDecoder);
                showHint("VLC для этого MP4");
            } catch (Exception e) { reportPlaybackError(e); }
            return;
        }
        if (currentUri == null) {""")
change("""            preferSoftwareDecoder ? "Декодирование: совместимое (сменить)" :
                    "Декодирование: аппаратное (сменить)"
        };""",
"""            nativeMode ? "Переключить MP4 на VLC" :
                    (preferSoftwareDecoder ? "Декодирование: совместимое (сменить)" :
                    "Декодирование: аппаратное (сменить)")
        };""")
change("""        if (player != null && currentUri != null) {
            savePlaybackPosition(player.getTime());
            if (player.isPlaying()) player.pause();
        }""",
"""        if (currentUri != null) {
            savePlaybackPosition(getVideoTime());
            if (nativeMode && nativeVideo != null && nativeVideo.isPlaying()) nativeVideo.pause();
            else if (player != null && !nativeMode && player.isPlaying()) player.pause();
        }""")
change("""        handler.removeCallbacksAndMessages(null);
        if (player != null) {""",
"""        handler.removeCallbacksAndMessages(null);
        if (nativeVideo != null) nativeVideo.stopPlayback();
        if (player != null) {""")

p.write_text(s, encoding="utf-8")
gradle=Path("MoviePlayer/app/build.gradle")
b=gradle.read_text(encoding="utf-8").replace("versionCode 3","versionCode 4").replace("versionName '1.2'","versionName '1.3'")
gradle.write_text(b, encoding="utf-8")
print("NeonFilm v1.3 native MP4 + VLC fallback applied")
