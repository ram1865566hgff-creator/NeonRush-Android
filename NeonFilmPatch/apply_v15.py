#!/usr/bin/env python3
"""NeonFilm 1.5: compact in-video overlay, intuitive single/double-tap controls.
Run after apply_v11.py -> apply_v12.py -> apply_v13.py -> apply_v14.py.
Preserves Media3 TextureView for MP4 and VLC for other containers.
"""
from pathlib import Path

p = Path("MoviePlayer/app/src/main/java/ru/neonfilm/player/MainActivity.java")
s = p.read_text(encoding="utf-8")

def change(a, b):
    global s
    n = s.count(a)
    if n != 1:
        raise RuntimeError("UI patch expected 1 match, found " + str(n) + ": " + repr(a[:100]))
    s = s.replace(a, b, 1)

# Use full-screen video as layout surface: panels are inside, not above/below it.
change("""        refreshHistory();
        updateOrientationLayout();
    }
""", """        refreshHistory();

        // Let video occupy the entire viewport. Controls float ABOVE video
        // and above the touch detector; they are invisible when not needed.
        root.removeView(topBar);
        root.removeView(bottomBar);
        FrameLayout.LayoutParams floatingHeader =
                new FrameLayout.LayoutParams(-1, dp(62), Gravity.TOP);
        videoFrame.addView(topBar, floatingHeader);
        FrameLayout.LayoutParams floatingFooter =
                new FrameLayout.LayoutParams(-1, ViewGroup.LayoutParams.WRAP_CONTENT, Gravity.BOTTOM);
        videoFrame.addView(bottomBar, floatingFooter);

        updateOrientationLayout();
    }
""")

change("""        topBar.setPadding(dp(16), dp(12), dp(12), dp(12));
""", """        topBar.setPadding(dp(14), dp(9), dp(12), dp(9));
        topBar.setBackgroundColor(Color.argb(208, 9, 14, 26));
""")
change("""        bottomBar.setBackgroundColor(PANEL);
""", """        bottomBar.setBackgroundColor(Color.argb(208, 9, 14, 26));
""")

change("""        LinearLayout primaryActions = horizontalRow();
        bottomBar.addView(primaryActions, rowLayout());
        playButton = button("▶ Пауза / Играть", BLUE, this::togglePlay);
        addWeighted(primaryActions, playButton);
        addWeighted(primaryActions, button("☰ Меню", SOFT, this::openPlayerMenu));
""", """        // No redundant ±10/±20 buttons. Seek with double taps on the picture.
        // Make Pause and Menu large enough to tap without covering the film.
        LinearLayout primaryActions = horizontalRow();
        primaryActions.setPadding(dp(10), 0, dp(10), dp(2));
        bottomBar.addView(primaryActions, rowLayout());
        playButton = button("▶", BLUE, this::togglePlay);
        primaryActions.addView(playButton, new LinearLayout.LayoutParams(dp(58), dp(44)));
        View actionSpacer = new View(this);
        primaryActions.addView(actionSpacer, new LinearLayout.LayoutParams(0, dp(2), 1f));
        TextView menuButton = button("☰  Меню", SOFT, this::openPlayerMenu);
        primaryActions.addView(menuButton, new LinearLayout.LayoutParams(dp(94), dp(44)));
""")

# A pause should not make the controls disappear; and a finger scrubbing the
# timeline should never lose the seekbar.
change("""    private final Runnable autoHide = () -> {
        setControlsVisible(false);
    };
""", """    private final Runnable autoHide = this::maybeHideControls;
""")
change("""    private void scheduleAutoHide() {
""", """    private void maybeHideControls() {
        if (seekingWithFinger) {
            scheduleAutoHide();
        } else if (currentUri != null && isVideoPlaying()) {
            setControlsVisible(false);
        }
    }
    private void scheduleAutoHide() {
""")

change("""                seekingWithFinger = false;
                if (isVideoSeekable()) {
""", """                seekingWithFinger = false;
                scheduleAutoHide();
                if (isVideoSeekable()) {
""")

# Hide the blank intro/history when watching video and keep the file picker
# visible when nothing has been opened.
change("""        bottomBar.setVisibility(visible && currentUri != null ? View.VISIBLE : View.GONE);
""", """        bottomBar.setVisibility(visible && currentUri != null ? View.VISIBLE : View.GONE);
        if (visible && currentUri != null) {
            topBar.bringToFront();
            bottomBar.bringToFront();
        }
""")

p.write_text(s, encoding="utf-8")

g = Path("MoviePlayer/app/build.gradle")
b = g.read_text(encoding="utf-8")
assert "versionCode 5" in b and "versionName '1.4'" in b, "Unexpected version before v1.5"
b = b.replace("versionCode 5", "versionCode 6").replace("versionName '1.4'", "versionName '1.5'")
g.write_text(b, encoding="utf-8")
print("NeonFilm 1.5: controls overlay video, auto-hide respects pause/seek, double-tap unchanged")
