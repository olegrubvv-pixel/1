package com.gameok.heyenglish;

import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.speech.tts.TextToSpeech;
import android.speech.tts.Voice;
import android.webkit.JavascriptInterface;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.Comparator;
import java.util.Locale;
import java.util.Set;

public class MainActivity extends Activity {
    private WebView webView;
    private OfflineTtsBridge ttsBridge;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        webView = new WebView(this);
        setContentView(webView);

        WebView.setWebContentsDebuggingEnabled(false);

        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(false);
        s.setBlockNetworkLoads(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setBuiltInZoomControls(false);
        s.setDisplayZoomControls(false);
        s.setSupportZoom(false);

        ttsBridge = new OfflineTtsBridge();
        webView.addJavascriptInterface(ttsBridge, "AndroidTTS");

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                String scheme = request.getUrl().getScheme();
                return "http".equalsIgnoreCase(scheme) || "https".equalsIgnoreCase(scheme);
            }

            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                String scheme = request.getUrl().getScheme();
                if ("http".equalsIgnoreCase(scheme) || "https".equalsIgnoreCase(scheme)) {
                    return new WebResourceResponse(
                            "text/plain",
                            "UTF-8",
                            403,
                            "Offline",
                            java.util.Collections.emptyMap(),
                            new java.io.ByteArrayInputStream(new byte[0])
                    );
                }
                return super.shouldInterceptRequest(view, request);
            }
        });

        String html = readAsset("index.html");
        webView.loadDataWithBaseURL(
                "https://offline.heyenglish.local/",
                html,
                "text/html",
                "UTF-8",
                null
        );
    }

    private String readAsset(String name) {
        try (InputStream in = getAssets().open(name);
             ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[8192];
            int n;
            while ((n = in.read(buffer)) >= 0) {
                out.write(buffer, 0, n);
            }
            return out.toString(StandardCharsets.UTF_8.name());
        } catch (Exception e) {
            return "<!doctype html><meta charset='utf-8'><h2>HEY English</h2><p>Не удалось открыть локальные данные приложения.</p>";
        }
    }

    private void flushState() {
        if (webView != null) {
            webView.evaluateJavascript(
                    "try{if(typeof flushPersistentState==='function')flushPersistentState()}catch(e){}",
                    null
            );
        }
    }

    @Override
    protected void onPause() {
        flushState();
        if (webView != null) webView.onPause();
        super.onPause();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (webView != null) webView.onResume();
    }

    @Override
    protected void onDestroy() {
        flushState();
        if (ttsBridge != null) ttsBridge.shutdown();
        if (webView != null) {
            webView.removeJavascriptInterface("AndroidTTS");
            webView.destroy();
        }
        super.onDestroy();
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }

    private final class OfflineTtsBridge implements TextToSpeech.OnInitListener {
        private final Handler main = new Handler(Looper.getMainLooper());
        private TextToSpeech tts;
        private volatile boolean ready = false;
        private Voice localUsVoice;

        OfflineTtsBridge() {
            tts = new TextToSpeech(MainActivity.this, this);
        }

        @Override
        public void onInit(int status) {
            if (status != TextToSpeech.SUCCESS || tts == null) return;
            try {
                tts.setLanguage(Locale.US);
                Set<Voice> voices = tts.getVoices();
                if (voices != null) {
                    localUsVoice = voices.stream()
                            .filter(v -> v.getLocale() != null)
                            .filter(v -> "en".equalsIgnoreCase(v.getLocale().getLanguage()))
                            .filter(v -> "US".equalsIgnoreCase(v.getLocale().getCountry()))
                            .filter(v -> !v.isNetworkConnectionRequired())
                            .min(Comparator.comparingInt(Voice::getLatency))
                            .orElse(null);
                }
                if (localUsVoice != null) {
                    tts.setVoice(localUsVoice);
                    tts.setSpeechRate(0.88f);
                    ready = true;
                }
            } catch (Throwable ignored) {
                ready = false;
            }
        }

        @JavascriptInterface
        public boolean speak(final String text) {
            if (!ready || tts == null || text == null || text.trim().isEmpty()) return false;
            final String safe = text.trim();
            main.post(() -> {
                if (tts != null && ready) {
                    tts.setSpeechRate(safe.indexOf(' ') < 0 ? 0.82f : 0.88f);
                    tts.speak(safe, TextToSpeech.QUEUE_FLUSH, null, "hey-" + System.nanoTime());
                }
            });
            return true;
        }

        @JavascriptInterface
        public boolean isReady() {
            return ready;
        }

        void shutdown() {
            ready = false;
            if (tts != null) {
                try { tts.stop(); } catch (Throwable ignored) {}
                try { tts.shutdown(); } catch (Throwable ignored) {}
                tts = null;
            }
        }
    }
}
