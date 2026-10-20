# 安卓版（APK）打包说明

网页版是同一套东西，APK 只是把它装进一个 WebView 里，
所以**功能、题库、图片跟网页版完全一致**，且全部离线。

产物：`发布\中药学复习.apk`（约 31 MB），Android 5.0 以上可装。
网页版右上角有「安卓版 APK」按钮，手机浏览器打开网站就能直接下载安装。

---

## 为什么 APK 里要起一个本地 http 服务

`MainActivity.java` 没有直接 `loadUrl("file:///android_asset/index.html")`，
而是在应用内起了一个只监听 `127.0.0.1` 的迷你 HTTP 服务，页面从
`http://127.0.0.1:端口/index.html` 加载。原因有两个：

1. `file://` 是不透明来源（opaque origin），**localStorage 在部分机型上直接抛异常**。
   错题本和成绩记录全靠 localStorage，丢了等于白复习。
2. 页面里的 `fetch('data/xxx.json')` 在 `file://` 下会被 CORS 拦掉。

走本地 http 就拿到正常来源，两个问题都不存在，行为跟在线版一模一样。

---

## 重新打包的步骤

### 1. 准备工具链（一次性，约 400 MB）

需要 **JDK 17** 和 **Android SDK 的 build-tools + platform**：

| 组件 | 下载地址 |
| --- | --- |
| JDK 17 | `https://mirrors.huaweicloud.com/openjdk/17.0.2/openjdk-17.0.2_windows-x64_bin.zip`（国内快） |
| cmdline-tools | `https://dl.google.com/android/repository/commandlinetools-win-11076708_latest.zip` |
| build-tools;34.0.0 | 用 sdkmanager 装 |
| platforms;android-34 | 用 sdkmanager 装 |

装完后目录长这样（`_android/` 已在 `.gitignore` 里，不会入库）：

```
_android/
  jdk17/                    JDK 17
  sdk/build-tools/34.0.0/   aapt2 / d8 / zipalign / apksigner
  sdk/platforms/android-34/ android.jar
  app/                      工程（源码在 tools/android/ 里有一份归档）
  out/                      产物
```

> **重要**：`aapt2.exe` 打不开非 ASCII 路径，也打不开中文文件名。
> 所以整个构建必须在**纯英文路径**下进行，图片也必须改成英文名。
> 本机用目录联接解决：
> ```powershell
> New-Item -ItemType Junction -Path C:\tcmapk -Target "<项目>\ _android"
> ```
> 然后在 `C:\tcmapk` 下构建。

### 2. 构建

```powershell
python C:\tcmapk\prepassets.py    # 图片改名 img_0001.jpg 并同步替换页面里的引用
python C:\tcmapk\buildapk.py      # 编译资源 → 链接 → javac → d8 → 打包 → 对齐 → 签名
```

`buildapk.py` 会依次跑：

1. `aapt2 compile` 编译 `res/`
2. `aapt2 link` 把资源和 `assets/` 一起打进 `base.apk`
   （编译产物要用**位置参数**传，不能用 `-R`，那是 overlay 语义会报错）
3. `javac` 编译 `MainActivity.java`（`-bootclasspath android.jar`）
4. `d8` 生成 `classes.dex`
5. Python `zipfile` 把 `classes.dex` 写进 apk
6. `zipalign -f -p 4`
7. `keytool` 生成自签名证书（首次）
8. `apksigner sign` 签名并校验

### 3. 发布

把 `out/中药学复习.apk` 复制到：

- `发布\中药学复习.apk`（给 Windows 上的自己）
- `docs\tcm-review.apk`（网站上的下载按钮指向它；用英文名避免 URL 编码问题）

---

## 换图标

改 `genicon.py`（现在是圆角深绿底 + 白色「药」字），跑一次即可：

```powershell
python C:\tcmapk\genicon.py
```

## 改包名 / 版本号

- 包名：`AndroidManifest.xml` 的 `package` 和 `MainActivity.java` 的 `package`
- 版本：`AndroidManifest.xml` 的 `versionCode`/`versionName`，
  以及 `buildapk.py` 里的 `--version-code` / `--version-name`