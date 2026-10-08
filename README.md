# 中药学复习系统（桌面版 + 网页版）

中药药性 / 功效 / 归经 / 用法 / 注意的**限时 100 分制测试**与**图文速查**。开源、免费、可离线。

- **网页版**（推荐，手机也能用）：[`web/index.html`](web/index.html)
- **桌面版**：`发布\中药学复习系统.exe`（Windows 单文件，双击即用，无需安装）
- **题库**：294 味中药 · 43 个分类 · 821 条功效 · 573 张实物图片
- **许可**：[MIT](LICENSE)（可自由使用、修改、再发布）

---

## 一、网页版（免费部署）

网页版是**纯静态**单页应用：把 `web/` 目录整个上传到任意免费静态托管即可，**不需要服务器、不需要数据库、不需要花钱**。

> 详细的图文步骤见 **[网页版部署指南.md](网页版部署指南.md)**（含 GitHub Pages / Cloudflare Pages / Netlify 三种免费方案与更新方法）。

### 方式 A：GitHub Pages（推荐，永久免费）

```bash
# 1) 在 GitHub 网页上新建仓库，例如 tcm-review
# 2) 本地初始化并推送（把 web/ 作为站点根目录）
git init
git add .
git commit -m "中药学复习系统：题库、桌面版与网页版"
git branch -M main
git remote add origin https://github.com/<你的用户名>/tcm-review.git
git push -u origin main
```

然后：仓库 **Settings → Pages → Build and deployment**
- Source 选 **Deploy from a branch**
- Branch 选 **main**，目录选 **/web**，保存

一两分钟后访问：`https://<你的用户名>.github.io/tcm-review/`

### 方式 B：Cloudflare Pages（也免费，国内访问通常更快）

1. 登录 Cloudflare → **Workers & Pages → Create → Pages → Connect to Git**
2. 选你的仓库；**Build output directory** 填 `web`，Build command 留空
3. 部署完成后得到 `https://<项目名>.pages.dev`

### 方式 C：本地先看看（不联网也能用）

在项目根目录执行（任选其一）：

```bash
python -m http.server 8080 --directory web      # Python
npx serve web                                   # Node
```

浏览器打开 `http://localhost:8080/`。
> 不要用 `file://` 直接双击 `index.html`——浏览器会拦截本地 fetch，导致题库加载失败。

### 更新地址（免费自动更新）

网页版启动时会读取同目录下的 [`web/version.json`](web/version.json)：

```json
{
  "version": "1.1.0",
  "updateUrl": "version.json",
  "notes": "本次更新内容……"
}
```

- 只要把仓库里的 `version.json` 的 `version` 改成新版本号并推送，**所有用户打开网页时就会看到"发现新版本，点击刷新更新"** 的提示条
- 也可以直接点页面右上角「**检查更新**」手动检查
- 桌面版可以后续加同样的检测（读取你部署的 `version.json`）

---

## 二、桌面版（Windows）

`发布\中药学复习系统.exe`：单文件、免安装、离线可用（图片已打包进 exe）。

重新编译：

```powershell
powershell -ExecutionPolicy Bypass -File build.ps1
```

自测（校验每道题正确性与试卷内是否重复）：

```
发布\中药学复习系统.exe --selftest 60
```

---

## 三、功能

| 功能 | 说明 |
| --- | --- |
| 中药速查 | 搜索药名/功效/性味/归经，分类筛选；右侧显示性味、归经、功效、用法、注意 + 实物图片，**点击图片放大**（可删除不合适的图） |
| 开始测试 | **固定 100 分制**：单选 3 分、多选 5 分、填空 3 分、判断 2 分；只调题量，合计必须正好 100 分才能开考；限时 0~300 分钟；支持随机出题、错题强化、练习模式 |
| 错题本 | 按错误次数排序，右侧看该药资料；支持导出文本、一键错题强化 |
| 成绩记录 | 总览统计 + 得分趋势图 + 明细表 |
| 判分 | 多选全对满分/漏选一半/错选不得分；填空支持同义词与错别字容错；同一套试卷题目不重复 |

网页版数据保存在浏览器 `localStorage`（不联网上传）；桌面版保存在 `%LocalAppData%\TcmReview\`。

---

## 四、目录结构

```
├─ web/                    网页版（部署这个目录）
│   ├─ index.html          单页应用
│   ├─ app.js              出题引擎 + 界面逻辑
│   ├─ style.css
│   ├─ version.json        版本与更新信息（改这里即可推送更新）
│   ├─ data/               题库、同义词、图片索引
│   └─ images/             573 张中药图片
├─ src/                    桌面版 C# 源码
├─ tools/                  图片打包/抓取/审查脚本
├─ images/                 原始图片库（桌面版打包用）
├─ build_herbs.py          题库数据源（每味药一行，改这里可增改药物）
├─ build.ps1               桌面版一键编译
├─ make_web.py             生成网页版数据
├─ webtest.js              网页版功能自测
├─ 使用说明.md             桌面版使用说明
└─ LICENSE                 MIT
```

## 五、自测

```bash
python make_web.py     # 生成网页版数据
node webtest.js        # 网页版：出题与判分自测（应输出 WEB SELFTEST PASS）
powershell -File build.ps1   # 桌面版编译 + 自测
```

## 六、免责声明

题库与图片仅用于学习记忆，**不构成医疗建议**；用药请遵医嘱并参考教材与药典。
图片来自公开网络资料，来源见 `images_credits.txt`，再分发请遵守各来源许可。
