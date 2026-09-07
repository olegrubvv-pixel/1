package com.olegrubvv.ai3d;

import android.app.*;
import android.os.*;
import android.content.*;
import android.net.Uri;
import android.provider.Settings;
import android.webkit.*;
import android.widget.Toast;
import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import org.json.*;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.*;

public class MainActivity extends Activity {
    private WebView web;
    private ValueCallback<Uri[]> fileCallback;
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final String BASE = "https://api.meshy.ai/openapi/v1/image-to-3d";

    private final ActivityResultLauncher<Intent> filePicker = registerForActivityResult(
        new ActivityResultContracts.StartActivityForResult(), result -> {
            if (fileCallback == null) return;
            Uri[] out = null;
            if (result.getResultCode() == RESULT_OK && result.getData() != null) {
                Uri u = result.getData().getData();
                if (u != null) out = new Uri[]{u};
            }
            fileCallback.onReceiveValue(out);
            fileCallback = null;
        }
    );

    @Override public void onCreate(Bundle b) {
        super.onCreate(b);
        web = new WebView(this);
        setContentView(web);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        web.setWebViewClient(new WebViewClient());
        web.setWebChromeClient(new WebChromeClient(){
            @Override public boolean onShowFileChooser(WebView v, ValueCallback<Uri[]> cb, FileChooserParams p){
                if(fileCallback != null) fileCallback.onReceiveValue(null);
                fileCallback = cb;
                try { filePicker.launch(p.createIntent()); }
                catch(Exception e){ fileCallback = null; return false; }
                return true;
            }
        });
        web.addJavascriptInterface(new Bridge(), "Android");
        web.loadUrl("file:///android_asset/index.html");
    }

    @Override public void onBackPressed(){
        if(web.canGoBack()) web.goBack(); else super.onBackPressed();
    }

    private void js(String code){ runOnUiThread(() -> web.evaluateJavascript(code, null)); }

    class Bridge {
        @JavascriptInterface public void create(String imageData, String apiKey, String quality, boolean pbr){
            executor.execute(() -> {
                try {
                    JSONObject body = new JSONObject();
                    body.put("image_url", imageData);
                    body.put("should_texture", true);
                    body.put("enable_pbr", pbr);
                    body.put("target_formats", new JSONArray().put("glb"));
                    body.put("alpha_thumbnail", true);
                    body.put("multi_view_thumbnails", true);
                    body.put("auto_size", true);
                    body.put("origin_at", "bottom");
                    if("smart".equals(quality)){
                        body.put("model_type", "smart-topology");
                        body.put("ai_model", "meshy-t2");
                        body.put("target_polycount", 60000);
                    } else {
                        body.put("model_type", "standard");
                        body.put("ai_model", "latest");
                        body.put("texture_resolution", "ultra".equals(quality) ? "4k" : "2k");
                        if("ultra".equals(quality)) body.put("ultra_mode", true);
                    }
                    String resp = request("POST", BASE, apiKey, body.toString());
                    JSONObject o = new JSONObject(resp);
                    String id = o.optString("result");
                    if(id.isEmpty()) throw new Exception(resp);
                    js("window.onCreated(" + JSONObject.quote(id) + ")");
                } catch(Exception e){ js("window.onError(" + JSONObject.quote(e.getMessage()) + ")"); }
            });
        }

        @JavascriptInterface public void status(String id, String apiKey){
            executor.execute(() -> {
                try {
                    String resp = request("GET", BASE + "/" + URLEncoder.encode(id, "UTF-8"), apiKey, null);
                    js("window.onStatus(" + JSONObject.quote(resp) + ")");
                } catch(Exception e){ js("window.onError(" + JSONObject.quote(e.getMessage()) + ")"); }
            });
        }

        @JavascriptInterface public void download(String url){
            runOnUiThread(() -> {
                try{
                    DownloadManager.Request r = new DownloadManager.Request(Uri.parse(url));
                    r.setTitle("AI 3D модель");
                    r.setDescription("Скачивание GLB");
                    r.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
                    r.setMimeType("model/gltf-binary");
                    r.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, "AI_3D_" + System.currentTimeMillis() + ".glb");
                    ((DownloadManager)getSystemService(DOWNLOAD_SERVICE)).enqueue(r);
                    Toast.makeText(MainActivity.this, "GLB скачивается в папку Downloads", Toast.LENGTH_LONG).show();
                }catch(Exception e){ Toast.makeText(MainActivity.this, e.getMessage(), Toast.LENGTH_LONG).show(); }
            });
        }
    }

    private String request(String method, String url, String key, String body) throws Exception {
        if(key == null || key.trim().isEmpty()) throw new Exception("Вставь Meshy API key");
        HttpURLConnection c = (HttpURLConnection)new URL(url).openConnection();
        c.setRequestMethod(method);
        c.setConnectTimeout(30000); c.setReadTimeout(120000);
        c.setRequestProperty("Authorization", "Bearer " + key.trim());
        c.setRequestProperty("Content-Type", "application/json");
        c.setRequestProperty("Accept", "application/json");
        if(body != null){
            c.setDoOutput(true);
            byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
            try(OutputStream os = c.getOutputStream()){ os.write(bytes); }
        }
        int code = c.getResponseCode();
        InputStream is = code >= 200 && code < 300 ? c.getInputStream() : c.getErrorStream();
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        byte[] buf = new byte[8192]; int n;
        while((n=is.read(buf))>0) out.write(buf,0,n);
        String text = out.toString("UTF-8");
        if(code < 200 || code >= 300){
            try{
                JSONObject e = new JSONObject(text);
                String m = e.optString("message", e.optString("error", text));
                throw new Exception("Meshy: " + m);
            }catch(JSONException je){ throw new Exception("Meshy HTTP " + code + ": " + text); }
        }
        return text;
    }
}
