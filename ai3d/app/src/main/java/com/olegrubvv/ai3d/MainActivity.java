package com.olegrubvv.ai3d;

import android.app.*;
import android.os.*;
import android.content.*;
import android.net.Uri;
import android.webkit.*;
import android.widget.Toast;

public class MainActivity extends Activity {
    private static final int FILE_REQ = 1204;
    private static final String HOME = "file:///android_asset/index.html";
    private static final String GENERATE = "https://tencent-hunyuan3d-2.hf.space";
    private static final String RIG = "https://jasongzy-make-it-animatable.hf.space";
    private WebView web;
    private ValueCallback<Uri[]> fileCallback;

    @Override public void onCreate(Bundle b) {
        super.onCreate(b);
        web = new WebView(this);
        setContentView(web);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setLoadWithOverviewMode(true);
        s.setUseWideViewPort(true);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE);
        s.setUserAgentString(s.getUserAgentString() + " AIPhoto3D/3.0");

        web.addJavascriptInterface(new Object(){
            @JavascriptInterface public void openGenerate(){ runOnUiThread(() -> web.loadUrl(GENERATE)); }
            @JavascriptInterface public void openRig(){ runOnUiThread(() -> web.loadUrl(RIG)); }
            @JavascriptInterface public void home(){ runOnUiThread(() -> web.loadUrl(HOME)); }
        }, "AndroidNav");

        web.setWebViewClient(new WebViewClient(){
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request){
                Uri u = request.getUrl();
                String scheme = u.getScheme();
                if("http".equals(scheme) || "https".equals(scheme) || "file".equals(scheme)) return false;
                try { startActivity(new Intent(Intent.ACTION_VIEW, u)); } catch(Exception ignored) {}
                return true;
            }
        });

        web.setWebChromeClient(new WebChromeClient(){
            @Override public boolean onShowFileChooser(WebView v, ValueCallback<Uri[]> cb, FileChooserParams p){
                if(fileCallback != null) fileCallback.onReceiveValue(null);
                fileCallback = cb;
                try {
                    Intent intent = p.createIntent();
                    String[] accepts = p.getAcceptTypes();
                    if(accepts != null && accepts.length == 1 && accepts[0] != null && !accepts[0].isEmpty()) intent.setType(accepts[0]);
                    startActivityForResult(intent, FILE_REQ);
                    return true;
                } catch(Exception e){
                    fileCallback = null;
                    Toast.makeText(MainActivity.this, "Не удалось открыть файл", Toast.LENGTH_SHORT).show();
                    return false;
                }
            }
        });

        web.setDownloadListener((url, userAgent, contentDisposition, mimeType, contentLength) -> {
            try {
                DownloadManager.Request r = new DownloadManager.Request(Uri.parse(url));
                r.addRequestHeader("User-Agent", userAgent);
                r.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
                r.setAllowedOverMetered(true);
                r.setAllowedOverRoaming(true);
                String name = URLUtil.guessFileName(url, contentDisposition, mimeType);
                if(name == null || name.trim().isEmpty()) name = "AI_3D_" + System.currentTimeMillis() + ".glb";
                r.setTitle(name);
                r.setDescription("Скачивание 3D-файла");
                r.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, name);
                ((DownloadManager)getSystemService(DOWNLOAD_SERVICE)).enqueue(r);
                Toast.makeText(MainActivity.this, "Файл скачивается в Downloads", Toast.LENGTH_LONG).show();
            } catch(Exception e){
                try { startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url))); }
                catch(Exception ignored){ Toast.makeText(MainActivity.this, "Не удалось скачать файл", Toast.LENGTH_LONG).show(); }
            }
        });
        web.loadUrl(HOME);
    }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data){
        super.onActivityResult(requestCode, resultCode, data);
        if(requestCode != FILE_REQ || fileCallback == null) return;
        Uri[] result = null;
        if(resultCode == RESULT_OK && data != null){
            if(data.getClipData() != null){
                int n = data.getClipData().getItemCount();
                result = new Uri[n];
                for(int i=0;i<n;i++) result[i] = data.getClipData().getItemAt(i).getUri();
            } else if(data.getData() != null) result = new Uri[]{data.getData()};
        }
        fileCallback.onReceiveValue(result);
        fileCallback = null;
    }

    @Override public void onBackPressed(){
        String u = web.getUrl();
        if(u != null && !u.equals(HOME)) web.loadUrl(HOME);
        else super.onBackPressed();
    }
}
