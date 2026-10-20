package com.wangji.tcmreview;

import android.app.Activity;
import android.content.res.AssetManager;
import android.os.Bundle;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import java.io.BufferedInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.URLDecoder;

/**
 * 中药学复习 —— 把网页版装进一个 WebView 里。
 *
 * 为什么要在应用内起一个本地 HTTP 服务，而不是直接 loadUrl("file:///android_asset/...")：
 *   1. file:// 是不透明来源（opaque origin），localStorage 在部分机型上直接抛异常，
 *      而错题本、成绩记录全靠 localStorage，丢了就白复习了；
 *   2. 页面里的 fetch('data/xxx.json') 在 file:// 下会被 CORS 拦掉。
 *   起一个只监听 127.0.0.1 的小服务，页面就拿到正常的 http 来源，
 *   上面两个问题都不存在，行为跟在线版完全一致。
 */
public class MainActivity extends Activity {

    private WebView web;
    private ServerSocket server;
    private int port;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setLoadWithOverviewMode(true);
        s.setUseWideViewPort(true);
        s.setBuiltInZoomControls(false);
        s.setDisplayZoomControls(false);
        s.setAllowFileAccess(true);
        web.setWebViewClient(new WebViewClient());
        setContentView(web);

        try {
            startServer();
            web.loadUrl("http://127.0.0.1:" + port + "/index.html");
        } catch (IOException e) {
            // 兜底：本地服务起不来就直接读资源（至少内容能看）
            web.loadUrl("file:///android_asset/index.html");
        }
    }

    private void startServer() throws IOException {
        server = new ServerSocket(0, 8, InetAddress.getByName("127.0.0.1"));
        port = server.getLocalPort();
        Thread t = new Thread(new Runnable() {
            @Override
            public void run() {
                while (true) {
                    try {
                        final Socket sock = server.accept();
                        Thread w = new Thread(new Runnable() {
                            @Override
                            public void run() {
                                serve(sock);
                            }
                        });
                        w.setDaemon(true);
                        w.start();
                    } catch (IOException e) {
                        break; // server 关了，线程退出
                    }
                }
            }
        });
        t.setDaemon(true);
        t.start();
    }

    private void serve(Socket sock) {
        try {
            BufferedInputStream in = new BufferedInputStream(sock.getInputStream());
            StringBuilder head = new StringBuilder();
            int c;
            while ((c = in.read()) != -1) {
                head.append((char) c);
                int n = head.length();
                if (n >= 4 && head.charAt(n - 4) == '\r' && head.charAt(n - 3) == '\n'
                        && head.charAt(n - 2) == '\r' && head.charAt(n - 1) == '\n') {
                    break;
                }
                if (n > 8192) {
                    break;
                }
            }

            String requestLine = head.toString().split("\r\n")[0];
            String[] bits = requestLine.split(" ");
            String path = bits.length > 1 ? bits[1] : "/index.html";
            int q = path.indexOf('?');
            if (q >= 0) {
                path = path.substring(0, q);
            }
            if (path.equals("/") || path.isEmpty()) {
                path = "/index.html";
            }
            path = URLDecoder.decode(path, "UTF-8");
            while (path.startsWith("/")) {
                path = path.substring(1);
            }

            String mime = mimeOf(path);
            byte[] body;
            int code;
            try {
                InputStream is = getAssets().open(path);
                body = readAll(is);
                is.close();
                code = 200;
            } catch (IOException e) {
                body = "404".getBytes("UTF-8");
                code = 404;
                mime = "text/plain; charset=utf-8";
            }

            OutputStream os = sock.getOutputStream();
            String hdr = "HTTP/1.1 " + code + (code == 200 ? " OK" : " Not Found") + "\r\n"
                    + "Content-Type: " + mime + "\r\n"
                    + "Content-Length: " + body.length + "\r\n"
                    + "Cache-Control: max-age=86400\r\n"
                    + "Connection: close\r\n\r\n";
            os.write(hdr.getBytes("UTF-8"));
            os.write(body);
            os.flush();
        } catch (Exception e) {
            // 单个请求出错不影响整体
        } finally {
            try {
                sock.close();
            } catch (IOException e) {
                // ignore
            }
        }
    }

    private static byte[] readAll(InputStream is) throws IOException {
        ByteArrayOutputStream bo = new ByteArrayOutputStream();
        byte[] buf = new byte[16384];
        int n;
        while ((n = is.read(buf)) > 0) {
            bo.write(buf, 0, n);
        }
        return bo.toByteArray();
    }

    private static String mimeOf(String p) {
        String l = p.toLowerCase();
        if (l.endsWith(".html") || l.endsWith(".htm")) {
            return "text/html; charset=utf-8";
        }
        if (l.endsWith(".js")) {
            return "application/javascript; charset=utf-8";
        }
        if (l.endsWith(".css")) {
            return "text/css; charset=utf-8";
        }
        if (l.endsWith(".json")) {
            return "application/json; charset=utf-8";
        }
        if (l.endsWith(".jpg") || l.endsWith(".jpeg")) {
            return "image/jpeg";
        }
        if (l.endsWith(".png")) {
            return "image/png";
        }
        if (l.endsWith(".gif")) {
            return "image/gif";
        }
        if (l.endsWith(".webp")) {
            return "image/webp";
        }
        if (l.endsWith(".svg")) {
            return "image/svg+xml";
        }
        if (l.endsWith(".ico")) {
            return "image/x-icon";
        }
        return "application/octet-stream";
    }

    @Override
    public void onBackPressed() {
        if (web != null && web.canGoBack()) {
            web.goBack();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onDestroy() {
        try {
            if (server != null) {
                server.close();
            }
        } catch (IOException e) {
            // ignore
        }
        super.onDestroy();
    }
}