// =====================================================================
//  中药学复习系统 —— 首页界面
//  文件: HomeForm.cs
//  页面：中药速查 / 开始测试 / 错题本 / 成绩记录 / 设置
// =====================================================================
using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Text;
using System.Windows.Forms;

namespace TcmReview
{
    public class HomeForm : BaseForm
    {
        private HerbData _data;
        private AppConfig _cfg;
        private TabControl _tabs;

        // 速查页
        private TextBox _search;
        private ListBox _catList;
        private ListBox _herbList;
        private RichTextBox _detail;
        private PictureBox _pic;
        private Label _picCap;
        private CheckBox _onlyWrong;
        private Label _statLbl;
        private Dictionary<string, int> _wrongMap = new Dictionary<string, int>();

        // 测试页
        private ComboBox _modeBox;
        private CheckedListBox _catChecks;
        private NumericUpDown _q1, _q2, _q3, _q4;      // 单选/多选/填空/判断 题量
        private Label _totalLbl;
        private Button _startBtn;
        private NumericUpDown _wrongCount;

        // 设置页
        private NumericUpDown _setWrongCount;

        // 固定分值（100 分制）：单选3分、多选5分、填空3分、判断2分
        private const int P_SINGLE = 3;
        private const int P_MULTI = 5;
        private const int P_FILL = 3;
        private const int P_JUDGE = 2;
        private const int FULL_SCORE = 100;

        public HomeForm()
        {
            _data = HerbData.Current;
            _cfg = AppConfig.Load();
            _wrongMap = Store.LoadWrong();

            Text = _data.Title + " · 中药学智能复习系统";
            ClientSize = new Size(1180, 760);
            MinimumSize = new Size(1020, 680);

            BuildHeader();
            BuildTabs();
            RefreshStats();
        }

        public AppConfig Config { get { return _cfg; } }

        // ---------------- 顶部标题 ----------------
        private Panel _header;
        private Label _subTitle;
        private void BuildHeader()
        {
            _header = new Panel();
            _header.Dock = DockStyle.Top;
            _header.Height = 76;
            _header.BackColor = Ui.Brand;
            Controls.Add(_header);

            PictureBox logo = new PictureBox();
            logo.Width = 54; logo.Height = 54;
            logo.Left = 18; logo.Top = 11;
            logo.BackColor = Color.Transparent;
            logo.Paint += delegate(object s, PaintEventArgs e)
            {
                e.Graphics.SmoothingMode = System.Drawing.Drawing2D.SmoothingMode.AntiAlias;
                e.Graphics.FillEllipse(new SolidBrush(Color.FromArgb(70, 255, 255, 255)),
                    0, 0, logo.Width - 1, logo.Height - 1);
                using (Font f = new Font("SimHei", 26f, FontStyle.Bold))
                using (StringFormat sf = new StringFormat())
                {
                    sf.Alignment = StringAlignment.Center;
                    sf.LineAlignment = StringAlignment.Center;
                    e.Graphics.DrawString("药", f, Brushes.White,
                        new RectangleF(0, 0, logo.Width, logo.Height), sf);
                }
            };
            _header.Controls.Add(logo);

            Label t = Ui.Lbl(_data.Title, 19f, Color.White, true);
            t.Left = 84; t.Top = 12;
            t.Font = new Font(Ui.FontName, 19f, FontStyle.Bold);
            _header.Controls.Add(t);

            _subTitle = Ui.Lbl("", 10f, Color.FromArgb(210, 235, 225), false);
            _subTitle.Left = 86; _subTitle.Top = 46;
            _header.Controls.Add(_subTitle);

            Button upd = new Button();
            upd.Text = "检查更新";
            upd.Font = Ui.FB(10f);
            upd.FlatStyle = FlatStyle.Flat;
            upd.FlatAppearance.BorderColor = Color.FromArgb(120, 200, 175);
            upd.BackColor = Color.FromArgb(45, 130, 100);
            upd.ForeColor = Color.White;
            upd.Width = 92; upd.Height = 28;
            upd.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            upd.Left = _header.ClientSize.Width - 108;
            upd.Top = 24;
            upd.Cursor = Cursors.Hand;
            upd.Click += delegate
            {
                string msg = UpdateChecker.Check();
                if (msg.Length == 0)
                    MessageBox.Show(UpdateChecker.Url.Length == 0
                        ? "尚未配置更新地址。\n可在命令行用 --update-url <地址> 指定，或修改 UpdateChecker.Url。"
                        : "已是最新版本 " + UpdateChecker.CurrentVersion + "（或检查失败）。",
                        "检查更新", MessageBoxButtons.OK, MessageBoxIcon.Information);
                else
                    MessageBox.Show(msg, "发现新版本", MessageBoxButtons.OK, MessageBoxIcon.Information);
            };
            _header.Controls.Add(upd);

            Label tip = Ui.Lbl("100 分制 · 限时 · 单选 / 多选 / 填空 / 判断", 10.5f,
                Color.FromArgb(210, 235, 225), false);
            tip.AutoSize = false;
            tip.Dock = DockStyle.Right;
            tip.Width = 360;
            tip.TextAlign = ContentAlignment.MiddleRight;
            tip.Padding = new Padding(0, 0, 22, 0);
            _header.Controls.Add(tip);
        }

        // ---------------- 选项卡 ----------------
        private void BuildTabs()
        {
            _tabs = new TabControl();
            _tabs.Dock = DockStyle.Fill;
            _tabs.Font = Ui.F(11.5f);
            _tabs.Padding = new Point(18, 6);
            Controls.Add(_tabs);
            _tabs.BringToFront();

            TabPage pBrowse = new TabPage("中药速查");
            TabPage pExam = new TabPage("开始测试");
            TabPage pWrong = new TabPage("错题本");
            TabPage pHist = new TabPage("成绩记录");
            TabPage pSet = new TabPage("设置");
            pBrowse.BackColor = Ui.Bg; pExam.BackColor = Ui.Bg;
            pWrong.BackColor = Ui.Bg; pHist.BackColor = Ui.Bg; pSet.BackColor = Ui.Bg;

            _tabs.TabPages.Add(pBrowse);
            _tabs.TabPages.Add(pExam);
            _tabs.TabPages.Add(pWrong);
            _tabs.TabPages.Add(pHist);
            _tabs.TabPages.Add(pSet);

            BuildBrowse(pBrowse);
            BuildExam(pExam);
            BuildWrong(pWrong);
            BuildHistory(pHist);
            BuildSettings(pSet);
        }

        // ================= 中药速查 =================
        private void BuildBrowse(TabPage page)
        {
            Panel left = new Panel();
            left.Dock = DockStyle.Left;
            left.Width = 372;
            left.Padding = new Padding(14, 14, 8, 14);
            left.BackColor = Ui.Bg;
            page.Controls.Add(left);

            Panel card = new Panel();
            card.Dock = DockStyle.Fill;
            card.BackColor = Ui.Card;
            card.Padding = new Padding(12);
            left.Controls.Add(card);

            Label l1 = Ui.Lbl("搜索药名 / 功效 / 性味 / 归经", 10.5f, Ui.Sub, true);
            l1.Dock = DockStyle.Top;
            card.Controls.Add(l1);

            _search = new TextBox();
            _search.Font = Ui.F(12f);
            _search.Dock = DockStyle.Top;
            _search.BorderStyle = BorderStyle.FixedSingle;
            _search.Height = 30;
            card.Controls.Add(_search);
            _search.BringToFront();
            _search.TextChanged += delegate { RefreshHerbList(); };

            Panel sp = new Panel(); sp.Dock = DockStyle.Top; sp.Height = 8;
            card.Controls.Add(sp); sp.BringToFront();

            _onlyWrong = new CheckBox();
            _onlyWrong.Text = "只看错题本中的药物";
            _onlyWrong.Font = Ui.F(10.5f);
            _onlyWrong.Dock = DockStyle.Top;
            _onlyWrong.Height = 26;
            _onlyWrong.ForeColor = Ui.Sub;
            _onlyWrong.CheckedChanged += delegate { RefreshHerbList(); };
            card.Controls.Add(_onlyWrong);
            _onlyWrong.BringToFront();

            Label l2 = Ui.Lbl("分类", 10.5f, Ui.Sub, true);
            l2.Dock = DockStyle.Top;
            l2.Height = 24;
            card.Controls.Add(l2);
            l2.BringToFront();

            _catList = new ListBox();
            _catList.Font = Ui.F(10.5f);
            _catList.Dock = DockStyle.Top;
            _catList.Height = 236;
            _catList.IntegralHeight = false;
            _catList.BorderStyle = BorderStyle.FixedSingle;
            Ui.SetDoubleBuffered(_catList);
            _catList.SelectedIndexChanged += delegate { RefreshHerbList(); };
            card.Controls.Add(_catList);
            _catList.BringToFront();
            _catList.Items.Add("（全部分类）");
            foreach (string c in _data.Categories) _catList.Items.Add(c);

            Label l3 = Ui.Lbl("药物列表", 10.5f, Ui.Sub, true);
            l3.Dock = DockStyle.Top;
            l3.Height = 24;
            card.Controls.Add(l3);
            l3.BringToFront();

            _statLbl = Ui.Lbl("", 10f, Ui.Sub, false);
            _statLbl.Dock = DockStyle.Bottom;
            _statLbl.Height = 22;
            card.Controls.Add(_statLbl);
            _statLbl.BringToFront();

            _herbList = new ListBox();
            _herbList.Font = Ui.F(11.5f);
            _herbList.Dock = DockStyle.Fill;
            _herbList.BorderStyle = BorderStyle.FixedSingle;
            _herbList.IntegralHeight = false;
            // 关键：让列表显示药名而不是 TcmReview.Herb
            Ui.SetDoubleBuffered(_herbList);
            _herbList.DisplayMember = "Name";
            _herbList.ValueMember = "Name";
            _herbList.SelectedIndexChanged += delegate { ShowHerb(); };
            card.Controls.Add(_herbList);
            _herbList.BringToFront();

            Panel right = new Panel();
            right.Dock = DockStyle.Fill;
            right.Padding = new Padding(8, 14, 14, 14);
            page.Controls.Add(right);
            right.BringToFront();

            _detail = new RichTextBox();
            _detail.Dock = DockStyle.Fill;
            _detail.ReadOnly = true;
            _detail.BackColor = Ui.Card;
            _detail.BorderStyle = BorderStyle.None;
            _detail.Font = Ui.F(12f);
            _detail.DetectUrls = false;
            _detail.Padding = new Padding(0);
            Ui.SetDoubleBuffered(_detail);
            right.Controls.Add(_detail);

            _pic = new PictureBox();
            _pic.Width = 306;
            _pic.Height = 258;
            _pic.Left = 8;
            _pic.Top = 16;
            _pic.BackColor = Color.FromArgb(238, 240, 238);
            _pic.SizeMode = PictureBoxSizeMode.Zoom;
            Ui.SetDoubleBuffered(_pic);
            _pic.BorderStyle = BorderStyle.FixedSingle;
            _pic.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            _pic.Visible = false;
            _pic.Cursor = Cursors.Hand;
            _pic.DoubleClick += delegate { OpenImageViewer(); };
            right.Controls.Add(_pic);
            _pic.BringToFront();

            _picCap = Ui.Lbl("", 9.5f, Ui.Sub, false);
            _picCap.AutoSize = false;
            _picCap.Width = 306;
            _picCap.Height = 34;
            _picCap.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            _picCap.TextAlign = ContentAlignment.TopLeft;
            _picCap.Visible = false;
            right.Controls.Add(_picCap);
            _picCap.BringToFront();

            right.Resize += delegate
            {
                _pic.Left = right.ClientSize.Width - _pic.Width - 6;
                _picCap.Left = _pic.Left;
                _picCap.Top = _pic.Top + _pic.Height + 4;
                _detail.Padding = new Padding(0, 0, _pic.Width + 18, 0);
            };

            // 所有控件就绪后再选中第一项并刷新（避免事件回调访问未初始化控件）
            _catList.SelectedIndex = 0;
            RefreshHerbList();
        }

        private void RefreshHerbList()
        {
            string key = _search.Text.Trim();
            string cat = _catList.SelectedIndex <= 0 ? null : (string)_catList.SelectedItem;
            bool onlyWrong = _onlyWrong.Checked;

            _herbList.BeginUpdate();
            _herbList.Items.Clear();
            int n = 0;
            foreach (Herb h in _data.Herbs)
            {
                if (cat != null && h.Cat != cat) continue;
                if (onlyWrong && !_wrongMap.ContainsKey(h.Name)) continue;
                if (key.Length > 0)
                {
                    string blob = h.Name + h.Nature + h.Meridian + h.FxText + h.Cat;
                    if (blob.IndexOf(key, StringComparison.OrdinalIgnoreCase) < 0) continue;
                }
                _herbList.Items.Add(h);
                n++;
            }
            _herbList.EndUpdate();
            _statLbl.Text = "共 " + n + " 味（题库合计 " + _data.Herbs.Count + " 味）";
            if (_herbList.Items.Count > 0) _herbList.SelectedIndex = 0;
            else
            {
                _detail.Clear();
                _pic.Visible = false;
                _picCap.Visible = false;
            }
        }

        private void ShowHerb()
        {
            Herb h = _herbList.SelectedItem as Herb;
            if (h == null)
            {
                _detail.Clear();
                _pic.Visible = false;
                _picCap.Visible = false;
                return;
            }

            _detail.Clear();
            Append("【药名】", Ui.Brand);
            Append(h.Name + "\n", Ui.Text, true);
            Append("【分类】", Ui.Brand);
            Append(h.Cat + "\n", Ui.Text);
            Append("【性味】", Ui.Brand);
            Append(h.Nature + "\n", Ui.Text);
            Append("【归经】", Ui.Brand);
            Append(h.Meridian + "\n", Ui.Text);
            Append("【功效】", Ui.Brand);
            Append(h.FxText + "\n", Ui.Accent, true);
            Append("【用法用量】", Ui.Brand);
            Append(h.Usage + "\n", Ui.Text);
            Append("【使用注意】", Ui.Brand);
            Append(h.Caution + "\n", Ui.Text);
            if (_wrongMap.ContainsKey(h.Name))
                Append("\n※ 该药在你的错题本中（累计错 " + _wrongMap[h.Name] + " 次）", Ui.Bad, true);

            ShowImages(h);
        }

        /// <summary>显示该药的内嵌图片（已缩放缓存，避免切换时掉帧）</summary>
        private void ShowImages(Herb h)
        {
            try
            {
                List<byte[]> imgs = ImgBundle.GetImages(h.Name);
                if (imgs.Count == 0)
                {
                    _pic.Image = null;
                    _pic.Visible = false;
                    _picCap.Visible = false;
                    return;
                }
                _pic.Image = ImageCache.Get(h.Name, imgs[0], _pic.Width, _pic.Height);
                _pic.Visible = true;
                _picCap.Visible = true;
                string src = ImageSource.Get(h.Name, 1);
                _picCap.Text = "图 1/" + imgs.Count + (src.Length > 0 ? "　" + src : "") +
                    "\n（图片为公开网络资料，仅作学习参考；双击可放大）";
            }
            catch
            {
                _pic.Image = null;
                _pic.Visible = false;
                _picCap.Visible = false;
            }
        }

        /// <summary>双击图片放大查看（支持滚轮缩放、拖动平移、左右切换）</summary>
        private void OpenImageViewer()
        {
            Herb h = _herbList.SelectedItem as Herb;
            if (h == null) return;
            List<byte[]> imgs = ImgBundle.GetImages(h.Name);
            if (imgs.Count == 0) return;
            List<string> caps = new List<string>();
            for (int i = 0; i < imgs.Count; i++) caps.Add(ImageSource.Get(h.Name, i + 1));
            ImageViewer v = new ImageViewer(h.Name, imgs, caps, 0);
            v.SetKeys(ImgBundle.GetKeys(h.Name));
            v.Icon = this.Icon;
            v.OnDelete = delegate(string name, int originalIndex)
            {
                Store.AddHidden(name, originalIndex);
                ShowImages(h);
            };
            v.ShowDialog(this);
        }

        private void Append(string text, Color color) { Append(text, color, false); }

        private void Append(string text, Color color, bool bold)
        {
            _detail.SelectionStart = _detail.TextLength;
            _detail.SelectionLength = 0;
            _detail.SelectionFont = bold ? Ui.FB(12.5f) : Ui.F(12f);
            _detail.SelectionColor = color;
            _detail.AppendText(text);
        }

        // ================= 开始测试 =================
        private void BuildExam(TabPage page)
        {
            Panel wrap = new Panel();
            wrap.Dock = DockStyle.Fill;
            wrap.Padding = new Padding(20, 16, 20, 16);
            wrap.AutoScroll = true;
            page.Controls.Add(wrap);

            // ---- ① 测试范围 ----
            GroupBox g1 = MakeGroup("① 测试范围", 480, 210);
            wrap.Controls.Add(g1);

            _modeBox = new ComboBox();
            _modeBox.DropDownStyle = ComboBoxStyle.DropDownList;
            _modeBox.Font = Ui.F(11f);
            _modeBox.Left = 16; _modeBox.Top = 30; _modeBox.Width = 440;
            _modeBox.Items.Add("随机模拟测试（按下方分类范围）");
            _modeBox.Items.Add("按分类抽取（在下方勾选分类）");
            _modeBox.Items.Add("错题强化（错题本中的药物优先）");
            _modeBox.SelectedIndex = 0;
            g1.Controls.Add(_modeBox);

            Label lc = Ui.Lbl("抽题分类（可多选，不勾选＝全部）", 10.5f, Ui.Sub, true);
            lc.Left = 16; lc.Top = 66;
            g1.Controls.Add(lc);

            _catChecks = new CheckedListBox();
            _catChecks.Font = Ui.F(10f);
            _catChecks.Left = 16; _catChecks.Top = 90;
            _catChecks.Width = 440; _catChecks.Height = 108;
            _catChecks.CheckOnClick = true;
            foreach (string c in _data.Categories) _catChecks.Items.Add(c);
            g1.Controls.Add(_catChecks);

            // ---- ② 题型与分值（固定 100 分制） ----
            GroupBox g2 = MakeGroup("② 题型与分值（固定 100 分制，只需调题量）", 480, 210);
            g2.Left = 500;
            wrap.Controls.Add(g2);

            _q1 = AddQtyRow(g2, "单项选择题", P_SINGLE, 32, 10);
            _q2 = AddQtyRow(g2, "多项选择题", P_MULTI, 62, 4);
            _q3 = AddQtyRow(g2, "填空题", P_FILL, 92, 10);
            _q4 = AddQtyRow(g2, "判断题", P_JUDGE, 122, 10);

            _totalLbl = Ui.Lbl("", 11.5f, Ui.Brand, true);
            _totalLbl.Left = 16; _totalLbl.Top = 154;
            _totalLbl.AutoSize = false;
            _totalLbl.Width = 450; _totalLbl.Height = 46;
            g2.Controls.Add(_totalLbl);

            foreach (NumericUpDown n in new NumericUpDown[] { _q1, _q2, _q3, _q4 })
                n.ValueChanged += delegate { UpdateTotal(); };

            // ---- ③ 限时与模式 ----
            GroupBox g3 = MakeGroup("③ 限时与作答模式", 480, 150);
            g3.Top = 224;
            wrap.Controls.Add(g3);

            Label l4 = Ui.Lbl("考试限时（分钟，0＝不限时）", 10.5f, Ui.Sub, true);
            l4.Left = 16; l4.Top = 28;
            g3.Controls.Add(l4);

            NumericUpDown minuteBox = new NumericUpDown();
            minuteBox.Font = Ui.F(12f);
            minuteBox.Left = 16; minuteBox.Top = 52; minuteBox.Width = 104;
            minuteBox.Minimum = 0; minuteBox.Maximum = 300;
            minuteBox.Value = 30;
            g3.Controls.Add(minuteBox);
            _minuteBox = minuteBox;

            Button b15 = Ui.Btn("15 分钟", 80, 28, Ui.Card, Ui.Brand, 10f);
            b15.Left = 132; b15.Top = 53;
            b15.Click += delegate { _minuteBox.Value = 15; };
            g3.Controls.Add(b15);

            Button b30 = Ui.Btn("30 分钟", 80, 28, Ui.Card, Ui.Brand, 10f);
            b30.Left = 218; b30.Top = 53;
            b30.Click += delegate { _minuteBox.Value = 30; };
            g3.Controls.Add(b30);

            Button b60 = Ui.Btn("60 分钟", 80, 28, Ui.Card, Ui.Brand, 10f);
            b60.Left = 304; b60.Top = 53;
            b60.Click += delegate { _minuteBox.Value = 60; };
            g3.Controls.Add(b60);

            Button b0 = Ui.Btn("不限时", 80, 28, Ui.Card, Ui.Brand, 10f);
            b0.Left = 390; b0.Top = 53;
            b0.Click += delegate { _minuteBox.Value = 0; };
            g3.Controls.Add(b0);

            _immediateBox = new CheckBox();
            _immediateBox.Text = "练习模式：每题作答后立即显示答案与解析";
            _immediateBox.Font = Ui.F(10.5f);
            _immediateBox.ForeColor = Ui.Text;
            _immediateBox.Left = 16; _immediateBox.Top = 96;
            _immediateBox.Width = 450;
            g3.Controls.Add(_immediateBox);

            Label l5 = Ui.Lbl("（不勾选＝模拟测试，交卷后统一评分）", 10f, Ui.Sub, false);
            l5.Left = 32; l5.Top = 120;
            g3.Controls.Add(l5);

            // ---- ④ 开始 ----
            GroupBox g4 = MakeGroup("④ 开始测试", 480, 150);
            g4.Left = 500; g4.Top = 224;
            wrap.Controls.Add(g4);

            _startBtn = Ui.Btn("开 始 测 试", 200, 50, Ui.Brand, Color.White, 14f);
            _startBtn.Left = 16; _startBtn.Top = 30;
            _startBtn.Click += delegate { StartQuiz(); };
            g4.Controls.Add(_startBtn);

            Button randomBtn = Ui.Btn("随机出题（立刻开考）", 200, 50, Ui.Accent, Color.White, 12f);
            randomBtn.Left = 228; randomBtn.Top = 30;
            randomBtn.Click += delegate { StartQuiz(); };
            g4.Controls.Add(randomBtn);

            Button resetBtn = Ui.Btn("恢复默认题量", 140, 32, Ui.Card, Ui.Brand, 10.5f);
            resetBtn.Left = 16; resetBtn.Top = 94;
            resetBtn.Click += delegate
            {
                _q1.Value = 10; _q2.Value = 4; _q3.Value = 10; _q4.Value = 10;
                _minuteBox.Value = 30;
                UpdateTotal();
            };
            g4.Controls.Add(resetBtn);

            _wrongCount = new NumericUpDown();
            _wrongCount.Font = Ui.F(11f);
            _wrongCount.Left = 176; _wrongCount.Top = 98; _wrongCount.Width = 60;
            _wrongCount.Minimum = 1; _wrongCount.Maximum = 200;
            _wrongCount.Value = 20;
            g4.Controls.Add(_wrongCount);

            Label l6 = Ui.Lbl("错题强化题量", 10f, Ui.Sub, false);
            l6.Left = 244; l6.Top = 102;
            g4.Controls.Add(l6);

            _minuteBox.ValueChanged += delegate { UpdateTotal(); };

            ApplyConfigToUi();
            UpdateTotal();
        }

        private NumericUpDown _minuteBox;
        private CheckBox _immediateBox;

        /// <summary>一行题量设置：题型名 + 固定分值 + 题量</summary>
        private NumericUpDown AddQtyRow(GroupBox g, string name, int points, int y, int qty)
        {
            Label l = Ui.Lbl(name, 11f, Ui.Text, true);
            l.Left = 16; l.Top = y + 2;
            l.AutoSize = false;
            l.Width = 120;
            g.Controls.Add(l);

            Label p = Ui.Lbl("每题 " + points + " 分", 10.5f, Ui.Sub, false);
            p.Left = 140; p.Top = y + 3;
            p.AutoSize = false;
            p.Width = 90;
            g.Controls.Add(p);

            NumericUpDown n = new NumericUpDown();
            n.Font = Ui.F(11.5f);
            n.Left = 234; n.Top = y;
            n.Width = 64;
            n.Minimum = 0;
            n.Maximum = 100;
            n.Value = qty;
            g.Controls.Add(n);

            Label u = Ui.Lbl("题＝" + points + " 分/题", 10f, Ui.Sub, false);
            u.Left = 304; u.Top = y + 3;
            u.AutoSize = false;
            u.Width = 120;
            g.Controls.Add(u);
            return n;
        }

        private GroupBox MakeGroup(string title, int w, int h)
        {
            GroupBox g = new GroupBox();
            g.Text = title;
            g.Font = Ui.FB(11f);
            g.ForeColor = Ui.Brand;
            g.Width = w; g.Height = h;
            g.Left = 0; g.Top = 0;
            g.BackColor = Ui.Card;
            g.Padding = new Padding(8);
            return g;
        }

        private void ApplyConfigToUi()
        {
            _q1.Value = Clamp(_cfg.N1, _q1.Minimum, _q1.Maximum);
            _q2.Value = Clamp(_cfg.N2, _q2.Minimum, _q2.Maximum);
            _q3.Value = Clamp(_cfg.N4, _q3.Minimum, _q3.Maximum);
            _q4.Value = Clamp(_cfg.N3, _q4.Minimum, _q4.Maximum);
            _minuteBox.Value = Clamp(_cfg.Minutes, 0, 300);
            _immediateBox.Checked = _cfg.Immediate;
            for (int i = 0; i < _data.Categories.Count; i++)
                if (_cfg.Cats.Contains(_data.Categories[i]))
                    _catChecks.SetItemChecked(i, true);
        }

        private static decimal Clamp(int v, decimal min, decimal max)
        {
            if (v < min) return min;
            if (v > max) return max;
            return v;
        }

        /// <summary>题量是否合法（总分必须正好 100 分）</summary>
        private bool ConfigValid
        {
            get { return CurrentTotal() == FULL_SCORE && CurrentQuestions() > 0; }
        }

        private int CurrentTotal()
        {
            return (int)_q1.Value * P_SINGLE + (int)_q2.Value * P_MULTI +
                   (int)_q3.Value * P_FILL + (int)_q4.Value * P_JUDGE;
        }

        private int CurrentQuestions()
        {
            return (int)(_q1.Value + _q2.Value + _q3.Value + _q4.Value);
        }

        private void UpdateTotal()
        {
            int total = CurrentTotal();
            int qs = CurrentQuestions();
            string txt = "本次试卷：" + qs + " 题　合计 " + total + " 分";
            _totalLbl.ForeColor = total == FULL_SCORE ? Ui.Brand : Ui.Bad;

            if (total == FULL_SCORE)
            {
                txt += "　✔ 正好 100 分，可以开考";
            }
            else if (total > FULL_SCORE)
            {
                txt += "　✘ 超出 " + (total - FULL_SCORE) + " 分，请减少题量";
            }
            else
            {
                txt += "　✘ 还差 " + (FULL_SCORE - total) + " 分，请增加题量";
            }
            _totalLbl.Text = txt;

            if (qs == 0) _totalLbl.Text = "请至少设置一种题型";

            if (_startBtn != null) _startBtn.Enabled = (total == FULL_SCORE && qs > 0);
            _cfg.WrongCount = _wrongCount == null ? _cfg.WrongCount : (int)_wrongCount.Value;
        }

        private void CollectConfig()
        {
            _cfg.N1 = (int)_q1.Value; _cfg.P1 = P_SINGLE;
            _cfg.N2 = (int)_q2.Value; _cfg.P2 = P_MULTI;
            _cfg.N3 = (int)_q4.Value; _cfg.P3 = P_JUDGE;
            _cfg.N4 = (int)_q3.Value; _cfg.P4 = P_FILL;
            _cfg.Minutes = (int)_minuteBox.Value;
            _cfg.Immediate = _immediateBox.Checked;
            _cfg.Cats.Clear();
            for (int i = 0; i < _catChecks.Items.Count; i++)
                if (_catChecks.GetItemChecked(i)) _cfg.Cats.Add((string)_catChecks.Items[i]);
        }

        private void StartQuiz()
        {
            CollectConfig();

            if (CurrentTotal() != FULL_SCORE)
            {
                MessageBox.Show("当前合计 " + CurrentTotal() + " 分，必须是 100 分才能开考。\n\n" +
                    "分值固定为：单选 " + P_SINGLE + " 分/题、多选 " + P_MULTI +
                    " 分/题、填空 " + P_FILL + " 分/题、判断 " + P_JUDGE + " 分/题。",
                    "题量不符合 100 分制", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }
            _cfg.WrongCount = (int)_wrongCount.Value;
            _cfg.Save();

            Cursor = Cursors.WaitCursor;
            QuizEngine eng = new QuizEngine(_data, _cfg);

            // 错题强化：把抽题范围限定到错题本中的药物
            if (_modeBox.SelectedIndex == 2)
            {
                List<Herb> pool = new List<Herb>();
                foreach (string n in _wrongMap.Keys)
                {
                    Herb h = _data.Find(n);
                    if (h != null) pool.Add(h);
                }
                eng.SetPool(pool);
            }

            List<QItem> items = eng.BuildQuiz(_cfg);
            Cursor = Cursors.Default;

            if (items.Count == 0)
            {
                MessageBox.Show("未能生成题目，请扩大抽题范围或更换分类。", "提示",
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }
            if (items.Count < _cfg.QuestionTotal())
            {
                MessageBox.Show("当前范围内可生成的不重复题目有限，本次共生成 " + items.Count + " 题。",
                    "提示", MessageBoxButtons.OK, MessageBoxIcon.Information);
            }

            QuizData qd = new QuizData();
            qd.Items = items;
            qd.LimitSeconds = _cfg.Minutes * 60;
            qd.ModeName = _modeBox.SelectedIndex == 2 ? "错题强化" :
                          (_cfg.Immediate ? "练习模式" : "模拟测试");

            QuizForm f = new QuizForm(_data, _cfg, qd);
            Hide();
            f.ShowDialog(this);
            Show();
            _wrongMap = Store.LoadWrong();
            RefreshHerbList();
            RefreshStats();
            if (_wrongPanel != null) _wrongPanel.Reload();
            if (_records != null) _records.Reload();
        }

        // ================= 错题本 =================
        private MistakesPanel _wrongPanel;

        private void BuildWrong(TabPage page)
        {
            _wrongPanel = new MistakesPanel(_data);
            _wrongPanel.Dock = DockStyle.Fill;
            _wrongPanel.OnBrowse = delegate(string name) { BrowseTo(name); };
            _wrongPanel.OnStartReview = delegate { StartWrongReview(); };
            page.Controls.Add(_wrongPanel);
        }

        /// <summary>跳到「中药速查」并定位到指定药物</summary>
        private void BrowseTo(string name)
        {
            if (string.IsNullOrEmpty(name)) return;
            _tabs.SelectedIndex = 0;
            _onlyWrong.Checked = false;
            _catList.SelectedIndex = 0;
            _search.Text = name;
            RefreshHerbList();
            for (int i = 0; i < _herbList.Items.Count; i++)
            {
                Herb h = _herbList.Items[i] as Herb;
                if (h != null && h.Name == name) { _herbList.SelectedIndex = i; break; }
            }
        }

        /// <summary>按错题本范围直接开考（100 分制默认题量）</summary>
        private void StartWrongReview()
        {
            if (_wrongMap.Count == 0)
            {
                MessageBox.Show("错题本为空，先做一次测试吧。", "提示",
                    MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }
            _cfg.Immediate = false;
            _cfg.Minutes = 20;
            _cfg.Cats.Clear();
            _q1.Value = 10; _q2.Value = 4; _q3.Value = 10; _q4.Value = 10;
            _minuteBox.Value = 20;
            _modeBox.SelectedIndex = 2;
            UpdateTotal();
            _tabs.SelectedIndex = 1;
            StartQuiz();
        }

        // ================= 成绩记录 =================
        private RecordsView _records;

        private void BuildHistory(TabPage page)
        {
            _records = new RecordsView();
            _records.Dock = DockStyle.Fill;
            page.Controls.Add(_records);
        }

        public static string Comment(int score, int total)
        {
            if (total <= 0) return "";
            double p = (double)score / total;
            if (p >= 0.95) return "优秀！基础扎实";
            if (p >= 0.85) return "良好，继续巩固";
            if (p >= 0.75) return "中等，注意易混药";
            if (p >= 0.6) return "及格，建议重做题库";
            return "不及格，建议先看速查表";
        }

        // ================= 设置 =================
        private void BuildSettings(TabPage page)
        {
            Panel wrap = new Panel();
            wrap.Dock = DockStyle.Fill;
            wrap.Padding = new Padding(24, 20, 24, 20);
            wrap.AutoScroll = true;
            page.Controls.Add(wrap);

            Label h1 = Ui.Lbl("默认参数设置", 14f, Ui.Brand, true);
            h1.Left = 0; h1.Top = 0;
            wrap.Controls.Add(h1);

            int imgCount = ImgBundle.Count;
            string info =
                "题库：" + _data.Herbs.Count + " 味中药，覆盖 " + _data.Categories.Count + " 个分类（按《中药学》教材分类编排）。\r\n" +
                "图片：" + (imgCount > 0
                    ? "已内嵌 " + imgCount + " 张中药真实图片（含药材、饮片、炮制品等形态），在「中药速查」右侧显示，来源清单见程序目录下 images_credits.txt"
                    : "未内嵌图片（运行 fetch_images.py 抓取后重新编译）") + "。\r\n" +
                "分值：固定 100 分制 —— 单选 " + P_SINGLE + " 分/题、多选 " + P_MULTI +
                " 分/题、填空 " + P_FILL + " 分/题、判断 " + P_JUDGE + " 分/题；只调整题量，合计必须正好 100 分。\r\n" +
                "出题：同一套试卷内题目不重复；多选题全对满分、漏选一半、错选不得分；填空题支持同义词与错别字容错。\r\n" +
                "数据目录：" + Store.Dir;
            Label infoLbl = Ui.Lbl(info, 11f, Ui.Text, false);
            infoLbl.Left = 0; infoLbl.Top = 34;
            infoLbl.AutoSize = true;
            infoLbl.MaximumSize = new Size(1060, 0);
            wrap.Controls.Add(infoLbl);

            Label h2 = Ui.Lbl("错题强化模式默认题量", 11f, Ui.Text, true);
            h2.Left = 0; h2.Top = 168;
            wrap.Controls.Add(h2);

            _setWrongCount = new NumericUpDown();
            _setWrongCount.Font = Ui.F(11f);
            _setWrongCount.Left = 0; _setWrongCount.Top = 194; _setWrongCount.Width = 70;
            _setWrongCount.Minimum = 5; _setWrongCount.Maximum = 200;
            _setWrongCount.Value = 20;
            wrap.Controls.Add(_setWrongCount);

            Button save = Ui.Btn("保存设置", 120, 36, Ui.Brand, Color.White, 11.5f);
            save.Left = 0; save.Top = 240;
            save.Click += delegate
            {
                _cfg.WrongCount = (int)_setWrongCount.Value;
                _cfg.Save();
                _wrongCount.Value = _cfg.WrongCount < _wrongCount.Minimum
                    ? _wrongCount.Minimum : _cfg.WrongCount;
                MessageBox.Show("设置已保存。", "提示");
            };
            wrap.Controls.Add(save);

            Button openDir = Ui.Btn("打开数据目录", 130, 36, Ui.Card, Ui.Brand, 11.5f);
            openDir.Left = 132; openDir.Top = 240;
            openDir.Click += delegate
            {
                try
                {
                    Store.EnsureDir();
                    System.Diagnostics.Process.Start("explorer.exe", Store.Dir);
                }
                catch (Exception ex)
                {
                    MessageBox.Show("无法打开目录：" + ex.Message, "提示");
                }
            };
            wrap.Controls.Add(openDir);
        }

        private void RefreshStats()
        {
            List<Record> list = Store.LoadHistory();
            int best = 0;
            foreach (Record r in list) if (r.Score > best) best = r.Score;
            if (_subTitle != null)
            {
                _subTitle.Text = "题库 " + _data.Herbs.Count + " 味 · " + _data.Categories.Count +
                    " 个分类 · 图片 " + ImgBundle.Count + " 张 · 已测试 " + list.Count +
                    " 次 · 历史最高 " + best + " 分 · 错题本 " + _wrongMap.Count + " 味";
            }
            if (_setWrongCount != null)
                _setWrongCount.Value = _cfg.WrongCount < _setWrongCount.Minimum
                    ? _setWrongCount.Minimum
                    : (_cfg.WrongCount > _setWrongCount.Maximum ? _setWrongCount.Maximum : _cfg.WrongCount);
        }
    }

    // ------------------------------------------------------------------
    //  图片缓存：把 12MB 位图缩放到显示尺寸并缓存，避免每次切换药味都重绘大图
    // ------------------------------------------------------------------
    public static class ImageCache
    {
        private static readonly Dictionary<string, Bitmap> _map =
            new Dictionary<string, Bitmap>(StringComparer.Ordinal);

        public static Bitmap Get(string name, byte[] data, int w, int h)
        {
            string key = name + "@" + w + "x" + h;
            Bitmap cached;
            if (_map.TryGetValue(key, out cached)) return cached;

            Bitmap result;
            using (MemoryStream ms = new MemoryStream(data))
            using (Image src = Image.FromStream(ms))
            {
                int tw = w, th = h;
                double k = Math.Min((double)w / src.Width, (double)h / src.Height);
                if (k < 1.0)
                {
                    tw = Math.Max(1, (int)(src.Width * k));
                    th = Math.Max(1, (int)(src.Height * k));
                }
                else
                {
                    tw = src.Width; th = src.Height;
                }
                Bitmap bmp = new Bitmap(tw, th, System.Drawing.Imaging.PixelFormat.Format24bppRgb);
                using (Graphics g = Graphics.FromImage(bmp))
                {
                    g.InterpolationMode = System.Drawing.Drawing2D.InterpolationMode.HighQualityBicubic;
                    g.PixelOffsetMode = System.Drawing.Drawing2D.PixelOffsetMode.HighQuality;
                    g.Clear(Color.White);
                    g.DrawImage(src, 0, 0, tw, th);
                }
                result = bmp;
            }
            if (_map.Count > 400)   // 控制内存上限
            {
                foreach (Bitmap b in _map.Values) b.Dispose();
                _map.Clear();
            }
            _map[key] = result;
            return result;
        }
    }

    // ------------------------------------------------------------------
    //  图片来源（读取 images_credits.txt，缺失时静默返回空）
    // ------------------------------------------------------------------
    public static class ImageSource
    {
        private static Dictionary<string, string> _map;

        private static void Load()
        {
            if (_map != null) return;
            _map = new Dictionary<string, string>(StringComparer.Ordinal);
            try
            {
                string[] dirs = new string[] {
                    Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "images_credits.txt"),
                    Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "images_credits.txt")
                };
                foreach (string p in dirs)
                {
                    if (!File.Exists(p)) continue;
                    string cur = "";
                    foreach (string line in File.ReadAllLines(p, Encoding.UTF8))
                    {
                        if (line.EndsWith("：", StringComparison.Ordinal) && line.Length > 1)
                        {
                            cur = line.Substring(0, line.Length - 1).Trim();
                            continue;
                        }
                        if (cur.Length > 0 && line.TrimStart().StartsWith("_")
                            && line.Contains("_1.jpg"))
                        {
                            // 形如：    麻黄_1.jpg  ←  标题  [许可]  来源页
                            int arrow = line.IndexOf("←", StringComparison.Ordinal);
                            string tail = arrow >= 0 ? line.Substring(arrow + 1).Trim() : "";
                            string[] parts = tail.Split(new char[] { '[' }, 2);
                            string title = parts[0].Trim();
                            if (title.Length > 40) title = title.Substring(0, 40);
                            if (!_map.ContainsKey(cur)) _map[cur] = title;
                        }
                    }
                    if (_map.Count > 0) break;
                }
            }
            catch { }
        }

        /// <summary>返回形如“XX百科 / 图片站点”的来源说明</summary>
        public static string Get(string herbName, int index)
        {
            Load();
            string v;
            if (_map != null && _map.TryGetValue(herbName, out v)) return v;
            return "";
        }
    }
}
