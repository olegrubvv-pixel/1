package com.olegrubvv.ai3d;

import android.app.*;
import android.os.*;
import android.content.*;
import android.net.Uri;
import android.provider.MediaStore;
import android.util.Base64;
import android.webkit.*;
import android.widget.Toast;
import java.io.*;

public class MainActivity extends Activity {
    private static final int FILE_REQ = 1204;
    private static final String HOME = "file:///android_asset/index.html";
    private static final String GENERATE = "https://tencent-hunyuan3d-2.hf.space";
    private WebView web;
    private ValueCallback<Uri[]> fileCallback;
    private OutputStream saveStream;
    private Uri saveUri;

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
        s.setAllowFileAccessFromFileURLs(true);
        s.setAllowUniversalAccessFromFileURLs(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setLoadWithOverviewMode(true);
        s.setUseWideViewPort(true);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE);
        s.setUserAgentString(s.getUserAgentString() + " AIPhoto3D/4.1");
        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(web, true);

        web.addJavascriptInterface(new Object(){
            @JavascriptInterface public void openGenerate(){ runOnUiThread(() -> web.loadUrl(GENERATE)); }
            @JavascriptInterface public void home(){ runOnUiThread(() -> web.loadUrl(HOME)); }
        }, "AndroidNav");

        web.addJavascriptInterface(new Object(){
            @JavascriptInterface public synchronized void begin(String filename){
                try{
                    closeSave(false);
                    String safe = filename == null || filename.trim().isEmpty() ? "Rigged_Player.glb" : filename.replaceAll("[^a-zA-Z0-9._-]", "_");
                    if(!safe.toLowerCase().endsWith(".glb")) safe += ".glb";
                    if(Build.VERSION.SDK_INT >= 29){
                        ContentValues v = new ContentValues();
                        v.put(MediaStore.Downloads.DISPLAY_NAME, safe);
                        v.put(MediaStore.Downloads.MIME_TYPE, "model/gltf-binary");
                        v.put(MediaStore.Downloads.IS_PENDING, 1);
                        saveUri = getContentResolver().insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, v);
                        if(saveUri == null) throw new IOException("Не удалось создать файл");
                        saveStream = getContentResolver().openOutputStream(saveUri, "w");
                    }else{
                        File dir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS);
                        if(!dir.exists()) dir.mkdirs();
                        saveStream = new FileOutputStream(new File(dir, safe));
                    }
                    if(saveStream == null) throw new IOException("Не удалось открыть файл");
                }catch(Exception e){ notifyJs("window.onNativeSaveError", String.valueOf(e.getMessage())); }
            }
            @JavascriptInterface public synchronized void chunk(String b64){
                try{
                    if(saveStream == null) throw new IOException("Файл не открыт");
                    saveStream.write(Base64.decode(b64, Base64.DEFAULT));
                }catch(Exception e){ notifyJs("window.onNativeSaveError", String.valueOf(e.getMessage())); }
            }
            @JavascriptInterface public synchronized void finish(){
                try{
                    closeSave(true);
                    runOnUiThread(() -> Toast.makeText(MainActivity.this, "Rigged GLB сохранён в Downloads", Toast.LENGTH_LONG).show());
                    notifyJs("window.onNativeSaved", "ok");
                }catch(Exception e){ notifyJs("window.onNativeSaveError", String.valueOf(e.getMessage())); }
            }
        }, "AndroidFiles");

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
            @Override public boolean onConsoleMessage(ConsoleMessage cm){
                if(cm.messageLevel() == ConsoleMessage.MessageLevel.ERROR){
                    String msg = cm.message();
                    if(msg != null && msg.length() > 140) msg = msg.substring(0,140);
                    final String out = msg;
                    runOnUiThread(() -> Toast.makeText(MainActivity.this, "JS: " + out, Toast.LENGTH_LONG).show());
                }
                return true;
            }

            @Override public boolean onShowFileChooser(WebView v, ValueCallback<Uri[]> cb, FileChooserParams p){
                if(fileCallback != null) fileCallback.onReceiveValue(null);
                fileCallback = cb;
                try {
                    Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
                    intent.addCategory(Intent.CATEGORY_OPENABLE);
                    String[] accepts = p.getAcceptTypes();
                    boolean image = false;
                    if(accepts != null){
                        for(String a: accepts){
                            if(a != null && a.toLowerCase().contains("image")){ image = true; break; }
                        }
                    }
                    if(image){
                        intent.setType("image/*");
                    }else{
                        intent.setType("*/*");
                        intent.putExtra(Intent.EXTRA_MIME_TYPES, new String[]{"model/gltf-binary","model/gltf+json","application/octet-stream","application/json"});
                    }
                    intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, p.getMode() == FileChooserParams.MODE_OPEN_MULTIPLE);
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
                Toast.makeText(MainActivity.this, "Не удалось скачать файл", Toast.LENGTH_LONG).show();
            }
        });
        web.loadUrl(HOME);
    }

    private synchronized void closeSave(boolean commit) throws IOException {
        if(saveStream != null){ saveStream.flush(); saveStream.close(); saveStream = null; }
        if(Build.VERSION.SDK_INT >= 29 && saveUri != null){
            if(commit){ ContentValues v = new ContentValues(); v.put(MediaStore.Downloads.IS_PENDING, 0); getContentResolver().update(saveUri, v, null, null); }
            else getContentResolver().delete(saveUri, null, null);
            saveUri = null;
        }
    }

    private void notifyJs(String fn, String msg){
        runOnUiThread(() -> web.evaluateJavascript(fn + "(" + org.json.JSONObject.quote(msg) + ")", null));
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
