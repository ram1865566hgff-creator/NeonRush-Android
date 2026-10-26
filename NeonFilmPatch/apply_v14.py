#!/usr/bin/env python3
"""NeonFilm 1.4: render phone MP4 using Media3/ExoPlayer TextureView, no SurfaceView stacking."""
from pathlib import Path
p = Path("MoviePlayer/app/src/main/java/ru/neonfilm/player/MainActivity.java")
s = p.read_text(encoding="utf-8")
def change(a,b):
    global s
    n=s.count(a)
    if n!=1: raise RuntimeError(f"Expected 1 match, got {n}: {a[:100]!r}")
    s=s.replace(a,b,1)

change("import android.widget.VideoView;",
"""import android.view.TextureView;
import androidx.media3.exoplayer.ExoPlayer;
import androidx.media3.common.Player;
import androidx.media3.common.MediaItem;
import androidx.media3.common.PlaybackException;
import androidx.media3.common.VideoSize;""")
change("""    private VideoView nativeVideo;
    private boolean nativeMode = false;""",
"""    private ExoPlayer nativeVideo;
    private TextureView nativeSurface;
    private FrameLayout nativeFrame;
    private boolean nativeFirstFrame;
    private long nativeStartedAt;
    private float nativeVideoAspect = 16f / 9f;
    private boolean nativeMode = false;""")
start=s.index("        nativeVideo = new VideoView(this);")
end=s.index("\n        emptyLabel = text(", start)
s=s[:start]+"""        // A TextureView is composited in the same window as the gestures/menu.
        // SurfaceView (used by VideoView) can end up behind an opaque VLC layer.
        nativeSurface = new TextureView(this);
        nativeSurface.setOpaque(true);
        nativeSurface.setVisibility(View.GONE);
        videoFrame.addView(nativeSurface, new FrameLayout.LayoutParams(-1, -1, Gravity.CENTER));
        nativeFrame = videoFrame;
        videoFrame.addOnLayoutChangeListener((v, l, t, r, b, ol, ot, oright, ob) ->
                layoutNativeSurface());
        nativeVideo = new ExoPlayer.Builder(this).build();
        nativeVideo.setVideoTextureView(nativeSurface);
        nativeVideo.addListener(new Player.Listener() {
            @Override public void onPlaybackStateChanged(int state) {
                if (!nativeMode) return;
                if (state == Player.STATE_READY) {
                    if (resumeAtMs > 0L) {
                        nativeVideo.seekTo(resumeAtMs);
                        resumeAtMs = 0L;
                    }
                    emptyLabel.setVisibility(View.GONE);
                    playButton.setText("Ⅱ");
                    scheduleAutoHide();
                } else if (state == Player.STATE_ENDED) {
                    playButton.setText("▶");
                    setControlsVisible(true);
                }
            }
            @Override public void onRenderedFirstFrame() {
                if (!nativeMode) return;
                nativeFirstFrame = true;
                emptyLabel.setVisibility(View.GONE);
            }
            @Override public void onVideoSizeChanged(VideoSize size) {
                if (!nativeMode || size.width <= 0 || size.height <= 0) return;
                nativeVideoAspect = (float)size.width * size.pixelWidthHeightRatio / size.height;
                layoutNativeSurface();
            }
            @Override public void onPlayerError(PlaybackException err) {
                if (nativeMode) fallbackFromNative("Media3: " + err.getErrorCodeName());
            }
        });""" + s[end:]
start=s.index("    // Android VideoView delegates document-provider")
end=s.index("    private void fallbackFromNative(", start)
s=s[:start]+"""    // Media3 reads Android document-provider content:// URIs directly, without
    // copying large movies or misusing a temporary file descriptor.
    private void layoutNativeSurface() {
        if (nativeFrame == null || nativeSurface == null) return;
        int w = nativeFrame.getWidth(), h = nativeFrame.getHeight();
        if (w <= 0 || h <= 0 || nativeVideoAspect <= 0) return;
        int fittedW = w, fittedH = Math.round(w / nativeVideoAspect);
        if (fittedH > h) {
            fittedH = h;
            fittedW = Math.round(h * nativeVideoAspect);
        }
        FrameLayout.LayoutParams lp = new FrameLayout.LayoutParams(
                Math.max(1, fittedW), Math.max(1, fittedH), Gravity.CENTER);
        nativeSurface.setLayoutParams(lp);
    }
    private void startNativeVideo(Uri uri) {
        player.stop();
        closeVideoDescriptor();
        nativeVideo.stop();
        nativeVideo.clearMediaItems();
        nativeMode = true;
        nativeFirstFrame = false;
        nativeStartedAt = SystemClock.elapsedRealtime();
        nativeLastPosition = -1;
        nativeLastProgressAt = nativeStartedAt;
        nativeVideoAspect = 16f / 9f;
        videoView.setVisibility(View.GONE);
        nativeSurface.setVisibility(View.VISIBLE);
        layoutNativeSurface();
        nativeVideo.setMediaItem(MediaItem.fromUri(uri));
        nativeVideo.setPlaybackSpeed(savedRate);
        nativeVideo.prepare();
        nativeVideo.play();
    }
    private void stopNativeVideo() {
        nativeMode = false;
        nativeVideo.stop();
        nativeVideo.clearMediaItems();
        nativeSurface.setVisibility(View.GONE);
        videoView.setVisibility(View.VISIBLE);
    }
""" + s[end:]
change("""        if (!nativeVideo.isPlaying()) {
            // Don't classify intentional pause as a playback hang.""",
"""        if (nativeVideo.isPlaying() && !nativeFirstFrame
                && now - nativeStartedAt > 12000L) {
            fallbackFromNative("Звук идёт без видеокадров");
            return;
        }
        if (!nativeVideo.isPlaying()) {
            // Don't classify intentional pause as a playback hang.""")
change("nativeVideo != null && nativeVideo.canSeekForward()", "nativeVideo != null && nativeVideo.isCurrentMediaItemSeekable()")
change("nativeVideo.seekTo((int)Math.min(Integer.MAX_VALUE, Math.max(0, ms)))","nativeVideo.seekTo(Math.max(0, ms))")
change("else nativeVideo.start();", "else nativeVideo.play();")
change("""        if (nativeMode) {
            if (android.os.Build.VERSION.SDK_INT >= 23) {
                try { nativeVideo.getClass(); /* rate set via MediaPlayer below when prepared */ }
                catch (Exception ignored) { }
            }
            notifyUser("Скорость для MP4 сейчас 1×; VLC поддерживает изменение");
        } else player.setRate(savedRate);""",
"""        if (nativeMode) nativeVideo.setPlaybackSpeed(savedRate);
        else player.setRate(savedRate);""")
change("if (nativeVideo != null) nativeVideo.stopPlayback();",
"""if (nativeVideo != null) {
            nativeVideo.stop();
            nativeVideo.release();
            nativeVideo = null;
        }""")

p.write_text(s, encoding="utf-8")

gradle=Path("MoviePlayer/app/build.gradle")
b=gradle.read_text(encoding="utf-8")
b=b.replace("versionCode 4","versionCode 5").replace("versionName '1.3'","versionName '1.4'")
b=b.replace("dependencies {\n", """dependencies {
    implementation 'androidx.media3:media3-exoplayer:1.11.1'
""")
gradle.write_text(b, encoding="utf-8")
manifest=Path("MoviePlayer/app/src/main/AndroidManifest.xml")
m=manifest.read_text(encoding="utf-8")
m=m.replace('android:allowBackup="false"', 'android:allowBackup="false"\n        android:hardwareAccelerated="true"')
manifest.write_text(m, encoding="utf-8")
print("NeonFilm 1.4 — Media3 ExoPlayer TextureView and visible-video watchdog enabled")
