# -*- coding: utf-8 -*-
"""把网页版打包成 APK —— 一条龙：编译资源 → 链接 → 编译 Java → dex → 打包 → 对齐 → 签名。

为什么用 Python 串起来：这台机器上 PowerShell 的分步产物经常丢，
放在一个进程里做完最稳。任何一步失败都会立刻打印并停下。

用法: python _android/build_apk.py
产物: _android/out/中药学复习.apk
"""
import os
import shutil
import subprocess
import sys
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))
SDK = os.path.join(BASE, "sdk")
BT = os.path.join(SDK, "build-tools", "34.0.0")
JDK = os.path.join(BASE, "jdk17")
APP = os.path.join(BASE, "app")
OUT = os.path.join(BASE, "out")
ANDROID_JAR = os.path.join(SDK, "platforms", "android-34", "android.jar")

AAPT2 = os.path.join(BT, "aapt2.exe")
ZIPALIGN = os.path.join(BT, "zipalign.exe")
APKSIGNER = os.path.join(BT, "apksigner.bat")
D8 = os.path.join(BT, "d8.bat")
JAVAC = os.path.join(JDK, "bin", "javac.exe")
KEYTOOL = os.path.join(JDK, "bin", "keytool.exe")

KS = os.path.join(BASE, "tcmreview.keystore")
KS_PASS = "tcmreview"
KS_ALIAS = "tcmreview"

APK_NAME = "中药学复习.apk"


def run(cmd, what):
    print(">> %s" % what, flush=True)
    env = dict(os.environ)
    env["JAVA_HOME"] = JDK
    env["PATH"] = os.path.join(JDK, "bin") + os.pathsep + env.get("PATH", "")
    p = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    txt = p.stdout.decode("utf-8", "replace")
    tail = "\n".join([l for l in txt.splitlines() if l.strip()][-6:])
    if tail:
        print(tail, flush=True)
    if p.returncode != 0:
        print("!! 失败 (%d): %s" % (p.returncode, what), flush=True)
        sys.exit(1)
    return txt


def main():
    for p in (AAPT2, JAVAC, D8, ZIPALIGN, ANDROID_JAR):
        if not os.path.exists(p):
            print("缺文件: %s" % p)
            return 2

    if os.path.isdir(OUT):
        shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT)
    gen = os.path.join(OUT, "gen")
    classes = os.path.join(OUT, "classes")
    dex = os.path.join(OUT, "dex")
    for d in (gen, classes, dex):
        os.makedirs(d)

    res_zip = os.path.join(OUT, "res.zip")
    base_apk = os.path.join(OUT, "base.apk")
    aligned = os.path.join(OUT, "aligned.apk")
    final = os.path.join(OUT, APK_NAME)

    run([AAPT2, "compile", "--dir", os.path.join(APP, "res"), "-o", res_zip], "aapt2 compile")

    # 注意：编译产物要用位置参数传，不能用 -R（-R 是 overlay 语义，
    # 会报 "resource string/app_name does not override an existing resource"）
    run([AAPT2, "link", "-o", base_apk, "-I", ANDROID_JAR,
         "--manifest", os.path.join(APP, "AndroidManifest.xml"),
         "--java", gen,
         "-A", os.path.join(APP, "assets"),
         "--min-sdk-version", "21", "--target-sdk-version", "34",
         "--version-code", "1701", "--version-name", "1.7.1",
         res_zip],
        "aapt2 link")
    print("   base.apk = %.1f MB" % (os.path.getsize(base_apk) / 1048576.0), flush=True)

    src = os.path.join(APP, "src", "com", "wangji", "tcmreview", "MainActivity.java")
    rjava = os.path.join(gen, "com", "wangji", "tcmreview", "R.java")
    run([JAVAC, "-encoding", "UTF-8", "-source", "8", "-target", "8",
         "-bootclasspath", ANDROID_JAR, "-d", classes, src, rjava], "javac")

    run([D8, "--lib", ANDROID_JAR, "--min-api", "21", "--output", dex,
         os.path.join(classes, "com", "wangji", "tcmreview", "MainActivity.class"),
         os.path.join(classes, "com", "wangji", "tcmreview", "R.class")], "d8")

    dexfile = os.path.join(dex, "classes.dex")
    if not os.path.exists(dexfile):
        print("!! 没生成 classes.dex")
        return 3

    print(">> 写入 classes.dex", flush=True)
    tmp_apk = base_apk + ".tmp"
    with zipfile.ZipFile(base_apk, "r") as zin:
        names = zin.namelist()
        with zipfile.ZipFile(tmp_apk, "w", zipfile.ZIP_DEFLATED) as zout:
            for n in names:
                zout.writestr(zin.getinfo(n), zin.read(n))
            zout.write(dexfile, "classes.dex")
    os.replace(tmp_apk, base_apk)

    run([ZIPALIGN, "-f", "-p", "4", base_apk, aligned], "zipalign")

    if not os.path.exists(KS):
        run([KEYTOOL, "-genkeypair", "-keystore", KS, "-alias", KS_ALIAS,
             "-keyalg", "RSA", "-keysize", "2048", "-validity", "10950",
             "-storepass", KS_PASS, "-keypass", KS_PASS,
             "-dname", "CN=TCM Review, OU=Study, O=Personal, L=CN, C=CN"],
            "keytool 生成签名证书")

    run([APKSIGNER, "sign", "--ks", KS, "--ks-key-alias", KS_ALIAS,
         "--ks-pass", "pass:" + KS_PASS, "--key-pass", "pass:" + KS_PASS,
         "--out", final, aligned], "apksigner 签名")

    run([APKSIGNER, "verify", "--print-certs", final], "apksigner 校验")

    print("", flush=True)
    print("=" * 52, flush=True)
    print("APK 完成: %s" % final, flush=True)
    print("大小: %.1f MB" % (os.path.getsize(final) / 1048576.0), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())