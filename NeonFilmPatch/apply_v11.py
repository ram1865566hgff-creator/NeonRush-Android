#!/usr/bin/env python3
"""NeonFilm v1.1 overlay controls, cumulative 10-second double-tap, reliable SAF media."""
from pathlib import Path

src = Path("MoviePlayer/app/src/main/java/ru/neonfilm/player/MainActivity.java")
s = src.read_text(encoding="utf-8")

def replace(old, new):
    global s
    count = s.count(old)
    if count != 1:
        raise SystemExit("Patch input mismatch: expected one match, found " + str(count) + " for " + repr(old[:75]))
    s = s.replace(old, new, 1)

replace("import android.app.Activity;", "import android.app.Activity;\nimport android.app.AlertDialog;")
replace("import android.os.Looper;", "import android.os.Looper;\nimport android.os.ParcelFileDescriptor;\nimport android.os.SystemClock;")

replace("    private MediaPlayer player;\n", """    private MediaPlayer player;
    // Android document-provider content:// URIs are NOT filesystem paths.
    // Keep the granted descriptor open for as long as VLC reads the video.
    private ParcelFileDescriptor videoDescriptor;
    private boolean triedSoftwareDecoder;
    private long lastDoubleTapTime;
    private int lastDoubleTapDirection;
    private int accumulatedSeekSeconds;
    private final Runnable autoHide = () -> {
        if (currentUri != null && player != null && player.isPlaying()) setControlsVisible(false);
    };
""")

replace("                    playButton.setText(\"Ⅱ\");\n", """                    playButton.setText("Ⅱ");
                    scheduleAutoHide();
""")

replace("""            } else if (event.type == MediaPlayer.Event.EncounteredError) {
                runOnUiThread(() -> notifyUser("Не удалось открыть видео. Попробуйте другой файл."));
""", """            } else if (event.type == MediaPlayer.Event.EncounteredError) {
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
""")

replace("""            @Override public boolean onSingleTapConfirmed(MotionEvent e) {
                setControlsVisible(!controlsVisible);
                return true;
            }
            @Override public boolean onDoubleTap(MotionEvent e) {
                int direction = e.getX() >= videoFrame.getWidth() / 2f ? 1 : -1;
                seekBy(direction * gestureSeconds);
                return true;
            }
""", """            @Override public boolean onSingleTapConfirmed(MotionEvent e) {
                setControlsVisible(!controlsVisible);
                if (controlsVisible) scheduleAutoHide();
                return true;
            }
            @Override public boolean onDoubleTap(MotionEvent e) {
                int direction = e.getX() >= videoFrame.getWidth() / 2f ? 1 : -1;
                long now = SystemClock.uptimeMillis();
                // Rapid double taps on one side add ten seconds each:
                // first = 10 s, second = 20 s total, third = 30 s total.
                if (direction == lastDoubleTapDirection && now - lastDoubleTapTime <= 1400) {
                    accumulatedSeekSeconds += 10;
                } else {
                    accumulatedSeekSeconds = 10;
                }
                lastDoubleTapDirection = direction;
                lastDoubleTapTime = now;
                seekBy(direction * 10);
                showHint((direction > 0 ? "+" : "−") + accumulatedSeekSeconds + " сек");
                return true;
            }
""")

start = s.index("        LinearLayout seekButtons = horizontalRow();")
end = s.index("        libraryArea = new LinearLayout(this);", start)
s = s[:start] + """        // Only playback and menu controls. Seeking is by double-tap on video.
        LinearLayout primaryActions = horizontalRow();
        bottomBar.addView(primaryActions, rowLayout());
        playButton = button("▶ Пауза / Играть", BLUE, this::togglePlay);
        addWeighted(primaryActions, playButton);
        addWeighted(primaryActions, button("☰ Меню", SOFT, this::openPlayerMenu));

""" + s[end:]

replace("""    private void setControlsVisible(boolean visible) {
        controlsVisible = visible;
        topBar.setVisibility(visible ? View.VISIBLE : View.GONE);
        bottomBar.setVisibility(visible ? View.VISIBLE : View.GONE);
        // In portrait, the recent list remains visible only with controls.
        libraryArea.setVisibility(visible && getResources().getConfiguration().orientation != Configuration.ORIENTATION_LANDSCAPE
                ? View.VISIBLE : View.GONE);
    }
""", """    private void scheduleAutoHide() {
        handler.removeCallbacks(autoHide);
        if (currentUri != null) handler.postDelayed(autoHide, 3200);
    }
    private void setControlsVisible(boolean visible) {
        controlsVisible = visible;
        topBar.setVisibility(visible ? View.VISIBLE : View.GONE);
        bottomBar.setVisibility(visible && currentUri != null ? View.VISIBLE : View.GONE);
        libraryArea.setVisibility(visible && currentUri == null
                && getResources().getConfiguration().orientation != Configuration.ORIENTATION_LANDSCAPE
                ? View.VISIBLE : View.GONE);
        if (!visible) handler.removeCallbacks(autoHide);
    }
""")
replace("""        libraryArea.setVisibility(!landscape && controlsVisible ? View.VISIBLE : View.GONE);
        topBar.setVisibility(controlsVisible ? View.VISIBLE : View.GONE);
        bottomBar.setVisibility(controlsVisible ? View.VISIBLE : View.GONE);
""", """        libraryArea.setVisibility(!landscape && controlsVisible && currentUri == null ? View.VISIBLE : View.GONE);
        topBar.setVisibility(controlsVisible ? View.VISIBLE : View.GONE);
        bottomBar.setVisibility(controlsVisible && currentUri != null ? View.VISIBLE : View.GONE);
""")

start = s.index("    private void loadVideo(Uri uri, String name, boolean resume) {")
end = s.index("    private void togglePlay() {", start)
s = s[:start] + """    private void loadVideo(Uri uri, String name, boolean resume) {
        if (player == null) return;
        try {
            if (currentUri != null) savePlaybackPosition(player.getTime());
            currentUri = uri;
            currentName = name;
            triedSoftwareDecoder = false;
            accumulatedSeekSeconds = 0;
            resumeAtMs = resume ? prefs.getLong("resume_" + uri.toString().hashCode(), 0L) : 0L;
            if (!resume) prefs.edit().putLong("resume_" + uri.toString().hashCode(), 0L).apply();
            subtitleTrackToRestore = -1;
            startPlayback(uri, false);
            emptyLabel.setVisibility(View.GONE);
            subheading.setText(name);
            setControlsVisible(true);
            scheduleAutoHide();
            saveRecent(uri, name);
            prefs.edit().putString("last_video_uri", uri.toString())
                    .putString("last_video_name", name).apply();
        } catch (Exception error) {
            reportPlaybackError(error);
        }
    }

    private void startPlayback(Uri uri, boolean softwareDecoder) throws Exception {
        // Release previous VLC media BEFORE closing its file descriptor.
        player.stop();
        closeVideoDescriptor();
        videoDescriptor = getContentResolver().openFileDescriptor(uri, "r");
        if (videoDescriptor == null) throw new java.io.IOException("Нет доступа к видео");
        Media media = new Media(libVLC, videoDescriptor.getFileDescriptor());
        try {
            media.setHWDecoderEnabled(!softwareDecoder, false);
            media.addOption(":file-caching=350");
            player.setMedia(media);
        } finally {
            media.release();
        }
        player.play();
        player.setRate(savedRate);
    }

    private void closeVideoDescriptor() {
        if (videoDescriptor != null) {
            try { videoDescriptor.close(); } catch (java.io.IOException ignored) {}
            videoDescriptor = null;
        }
    }
    private void reportPlaybackError(Exception error) {
        String detail = error == null ? "" : ": " + error.getMessage();
        notifyUser("Не удалось открыть файл" + detail);
        emptyLabel.setText("Видео не открылось\\nНажмите «Открыть» и выберите файл ещё раз");
        emptyLabel.setVisibility(View.VISIBLE);
        setControlsVisible(true);
    }
    @Override protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        if (intent != null && intent.getData() != null) {
            loadVideo(intent.getData(), getName(intent.getData()), false);
        }
    }

    private void openPlayerMenu() {
        String[] choices = {
            "Открыть видео",
            subtitleDisabled ? "Включить субтитры" : "Выключить субтитры",
            "Выбрать файл субтитров",
            "Скорость: " + savedRate + "×",
            rotationLocked ? "Включить автоповорот" : "Зафиксировать ориентацию",
            "Недавно открытые"
        };
        new AlertDialog.Builder(this)
                .setTitle("NeonFilm • Меню")
                .setItems(choices, (dialog, which) -> {
                    switch (which) {
                        case 0: pickFile(PICK_VIDEO); break;
                        case 1: toggleSubtitles(); break;
                        case 2: pickFile(PICK_SUBTITLE); break;
                        case 3: changeSpeed(); break;
                        case 4: toggleRotation(); break;
                        case 5: showRecentMenu(); break;
                        default: break;
                    }
                    scheduleAutoHide();
                }).show();
    }
    private void showRecentMenu() {
        try {
            JSONArray items = new JSONArray(prefs.getString("recents", "[]"));
            if (items.length() == 0) { notifyUser("Недавних видео ещё нет"); return; }
            String[] names = new String[items.length()];
            for (int i = 0; i < items.length(); i++) {
                names[i] = items.getJSONObject(i).optString("name", "Видео");
            }
            new AlertDialog.Builder(this).setTitle("Недавние видео")
                    .setItems(names, (dialog, which) -> {
                        JSONObject item = items.optJSONObject(which);
                        if (item != null) {
                            Uri uri = Uri.parse(item.optString("uri"));
                            loadVideo(uri, item.optString("name", "Видео"), true);
                        }
                    }).show();
        } catch (Exception e) { notifyUser("Не удалось прочитать историю"); }
    }

""" + s[end:]

# Prevent old unused button references from crashing when invoked from the new menu.
replace("""        gestureButton.setText("Жест: " + gestureSeconds + "с");
""", """        if (gestureButton != null) gestureButton.setText("Жест: " + gestureSeconds + "с");
""")
replace("""        subtitleButton.setText(subtitleDisabled ? "CC: выкл" : "CC: вкл");
""", """        if (subtitleButton != null) subtitleButton.setText(subtitleDisabled ? "CC: выкл" : "CC: вкл");
""")
replace("""            subtitleButton.setText("CC: вкл");
""", """            if (subtitleButton != null) subtitleButton.setText("CC: вкл");
""")
replace("""        rotateButton.setText(rotationLocked ? "🔒 Экран" : "↻ Авто");
""", """        if (rotateButton != null) rotateButton.setText(rotationLocked ? "🔒 Экран" : "↻ Авто");
""")
replace("""        speedButton.setText(String.format(Locale.US, "Скорость: %.2g×", savedRate));
""", """        if (speedButton != null) speedButton.setText(String.format(Locale.US, "Скорость: %.2g×", savedRate));
        showHint(String.format(Locale.US, "Скорость %.2g×", savedRate));
""")
replace("""            player.detachViews();
            player.release();
""", """            player.detachViews();
            closeVideoDescriptor();
            player.release();
""")
# Explicitly keep the Android build's version consistent.
gradle = Path("MoviePlayer/app/build.gradle")
b = gradle.read_text(encoding="utf-8").replace("compileSdk 35", "compileSdk 36").replace("versionCode 1", "versionCode 2").replace("versionName '1.0'", "versionName '1.1'")
gradle.write_text(b, encoding="utf-8")
src.write_text(s, encoding="utf-8")
print("Applied NeonFilm 1.1 patch with persistent file descriptor and cumulative gestures.")
