// =====================================================================
//  中药学复习系统 —— 图片放大查看器 + 错题本面板
//  文件: Widgets.cs
// =====================================================================
using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.Text;
using System.Windows.Forms;

namespace TcmReview
{
    // ==================================================================
    //  图片放大查看器：滚轮缩放、拖动平移、方向键切换、双击复位
    // ==================================================================
    public class ImageViewer : Form
    {
        private List<byte[]> _data = new List<byte[]>();
        private List<string> _names = new List<string>();
        private int _index;
        private Bitmap _bmp;
        private float _zoom = 1f;
        private SizeF _fit = new SizeF(1f, 1f);
        private PointF _pan = new PointF(0f, 0f);
        private bool _dragging;
        private Point _dragStart;
        private PointF _panStart;
        private string _source = "";

        private Canvas _canvas;
        private Label _caption;
        private Label _zoomLbl;
        private Button _prevBtn, _nextBtn;

        private class Canvas : Panel
        {
            public ImageViewer Owner;
            public Canvas()
            {
                SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.UserPaint |
                         ControlStyles.OptimizedDoubleBuffer | ControlStyles.ResizeRedraw, true);
                BackColor = Color.FromArgb(28, 32, 30);
            }
            protected override void OnPaint(PaintEventArgs e) { if (Owner != null) Owner.DrawCanvas(e.Graphics); }
        }

        private string _herb = "";
        private List<string> _keys = new List<string>();

        /// <summary>删除当前图片回调（参数：药名、原始图片序号）</summary>
        public Action<string, int> OnDelete;

        public void SetKeys(List<string> keys) { _keys = keys; }

        public ImageViewer(string herbName, List<byte[]> images, List<string> captions, int startIndex)
        {
            _herb = herbName;
            _data = images;
            _names = captions;
            _index = Math.Max(0, Math.Min(startIndex, images.Count - 1));

            Text = "图片查看 · " + herbName;
            StartPosition = FormStartPosition.CenterParent;
            ClientSize = new Size(1020, 720);
            MinimumSize = new Size(560, 420);
            BackColor = Color.FromArgb(28, 32, 30);
            KeyPreview = true;

            _canvas = new Canvas();
            _canvas.Owner = this;
            _canvas.Dock = DockStyle.Fill;
            _canvas.MouseDown += OnCanvasDown;
            _canvas.MouseMove += OnCanvasMove;
            _canvas.MouseUp += OnCanvasUp;
            _canvas.MouseWheel += OnWheel;
            _canvas.DoubleClick += delegate { _zoom = 1f; _pan = new PointF(0, 0); _canvas.Invalidate(); UpdateZoomLabel(); };
            Controls.Add(_canvas);

            Panel bar = new Panel();
            bar.Dock = DockStyle.Bottom;
            bar.Height = 58;
            bar.BackColor = Color.FromArgb(40, 46, 43);
            Controls.Add(bar);
            bar.BringToFront();

            Button close = MakeBtn("关闭 (Esc)", 96);
            close.Left = 12; close.Top = 12;
            close.Click += delegate { Close(); };
            bar.Controls.Add(close);

            _prevBtn = MakeBtn("◀ 上一张", 96);
            _prevBtn.Left = 118; _prevBtn.Top = 12;
            _prevBtn.Click += delegate { Step(-1); };
            bar.Controls.Add(_prevBtn);

            _nextBtn = MakeBtn("下一张 ▶", 96);
            _nextBtn.Left = 222; _nextBtn.Top = 12;
            _nextBtn.Click += delegate { Step(1); };
            bar.Controls.Add(_nextBtn);

            Button zoomOut = MakeBtn("缩小 −", 86);
            zoomOut.Left = 336; zoomOut.Top = 12;
            zoomOut.Click += delegate { ZoomBy(1f / 1.25f); };
            bar.Controls.Add(zoomOut);

            Button zoomIn = MakeBtn("放大 ＋", 86);
            zoomIn.Left = 428; zoomIn.Top = 12;
            zoomIn.Click += delegate { ZoomBy(1.25f); };
            bar.Controls.Add(zoomIn);

            Button fit = MakeBtn("适应窗口", 96);
            fit.Left = 520; fit.Top = 12;
            fit.Click += delegate { _zoom = 1f; _pan = new PointF(0, 0); _canvas.Invalidate(); UpdateZoomLabel(); };
            bar.Controls.Add(fit);

            Button del = MakeBtn("删掉这张图", 106);
            del.Left = 622; del.Top = 12;
            del.BackColor = Color.FromArgb(120, 54, 48);
            del.Click += delegate
            {
                if (_data.Count <= 1)
                {
                    MessageBox.Show("这是该药最后一张图片。\n删除后该药不再显示图片。", "删除图片",
                        MessageBoxButtons.OK, MessageBoxIcon.Information);
                }
                if (MessageBox.Show("确定删除这张图片吗？\n（只影响本程序显示，原图不删除；可在数据目录的 hidden.txt 里恢复）",
                    "删除图片", MessageBoxButtons.YesNo, MessageBoxIcon.Question) != DialogResult.Yes)
                    return;
                int originalIndex = _index + 1;
                if (_keys != null && _index < _keys.Count)
                {
                    string k = _keys[_index];
                    int u = k.LastIndexOf('_');
                    int dot = k.LastIndexOf('.');
                    if (u > 0 && dot > u + 1)
                    {
                        int v;
                        if (int.TryParse(k.Substring(u + 1, dot - u - 1), out v)) originalIndex = v;
                    }
                }
                if (OnDelete != null) OnDelete(_herb, originalIndex);
                Close();
            };
            bar.Controls.Add(del);

            _zoomLbl = new Label();
            _zoomLbl.Font = Ui.FB(11f);
            _zoomLbl.ForeColor = Color.FromArgb(210, 225, 218);
            _zoomLbl.AutoSize = false;
            _zoomLbl.Width = 90; _zoomLbl.Height = 30;
            _zoomLbl.Left = 740; _zoomLbl.Top = 16;
            _zoomLbl.TextAlign = ContentAlignment.MiddleLeft;
            bar.Controls.Add(_zoomLbl);

            _caption = new Label();
            _caption.Font = Ui.F(10.5f);
            _caption.ForeColor = Color.FromArgb(190, 205, 198);
            _caption.AutoSize = false;
            _caption.Height = 34;
            _caption.Left = 830; _caption.Top = 12;
            _caption.Anchor = AnchorStyles.Top | AnchorStyles.Right | AnchorStyles.Left;
            _caption.TextAlign = ContentAlignment.MiddleLeft;
            bar.Controls.Add(_caption);
            bar.Resize += delegate { _caption.Width = Math.Max(80, bar.ClientSize.Width - _caption.Left - 12); };

            KeyDown += delegate(object s, KeyEventArgs e)
            {
                if (e.KeyCode == Keys.Escape) Close();
                else if (e.KeyCode == Keys.Left || e.KeyCode == Keys.PageUp) Step(-1);
                else if (e.KeyCode == Keys.Right || e.KeyCode == Keys.PageDown) Step(1);
                else if (e.KeyCode == Keys.Add || e.KeyCode == Keys.Oemplus) ZoomBy(1.25f);
                else if (e.KeyCode == Keys.Subtract || e.KeyCode == Keys.OemMinus) ZoomBy(1f / 1.25f);
                else if (e.KeyCode == Keys.D0) { _zoom = 1f; _pan = new PointF(0, 0); _canvas.Invalidate(); }
            };

            Load_Index();
        }

        private Button MakeBtn(string text, int w)
        {
            Button b = new Button();
            b.Text = text;
            b.Width = w; b.Height = 34;
            b.FlatStyle = FlatStyle.Flat;
            b.FlatAppearance.BorderSize = 0;
            b.BackColor = Color.FromArgb(62, 72, 68);
            b.ForeColor = Color.White;
            b.Font = Ui.FB(10.5f);
            b.Cursor = Cursors.Hand;
            b.UseVisualStyleBackColor = false;
            return b;
        }

        private void Load_Index()
        {
            if (_bmp != null) { _bmp.Dispose(); _bmp = null; }
            if (_index < 0 || _index >= _data.Count) return;
            try
            {
                using (MemoryStream ms = new MemoryStream(_data[_index]))
                using (Image src = Image.FromStream(ms))
                    _bmp = new Bitmap(src);
            }
            catch { _bmp = null; }

            _zoom = 1f;
            _pan = new PointF(0, 0);
            _source = _names != null && _index < _names.Count ? _names[_index] : "";
            _caption.Text = (string.IsNullOrEmpty(_source) ? "公开网络资料" : _source) +
                "　（滚轮缩放 · 拖动平移 · 双击复位）";
            bool many = _data.Count > 1;
            _prevBtn.Enabled = many;
            _nextBtn.Enabled = many;
            _canvas.Invalidate();
            UpdateZoomLabel();
        }

        private void Step(int d)
        {
            if (_data.Count <= 1) return;
            _index = (_index + d + _data.Count) % _data.Count;
            Load_Index();
        }

        private void ZoomBy(float k)
        {
            float z = _zoom * k;
            if (z < 0.15f) z = 0.15f;
            if (z > 8f) z = 8f;
            _zoom = z;
            _canvas.Invalidate();
            UpdateZoomLabel();
        }

        private void UpdateZoomLabel()
        {
            if (_zoomLbl != null) _zoomLbl.Text = "缩放 " + Math.Round(_zoom * 100) + "%";
        }

        private void OnWheel(object sender, MouseEventArgs e)
        {
            ZoomBy(e.Delta > 0 ? 1.15f : 1f / 1.15f);
        }

        private void OnCanvasDown(object sender, MouseEventArgs e)
        {
            if (e.Button == MouseButtons.Left)
            {
                _dragging = true;
                _dragStart = e.Location;
                _panStart = _pan;
                _canvas.Cursor = Cursors.SizeAll;
            }
        }

        private void OnCanvasMove(object sender, MouseEventArgs e)
        {
            if (!_dragging) return;
            _pan = new PointF(_panStart.X + (e.X - _dragStart.X), _panStart.Y + (e.Y - _dragStart.Y));
            _canvas.Invalidate();
        }

        private void OnCanvasUp(object sender, MouseEventArgs e)
        {
            _dragging = false;
            _canvas.Cursor = Cursors.Default;
        }

        public void DrawCanvas(Graphics g)
        {
            g.Clear(Color.FromArgb(28, 32, 30));
            if (_bmp == null)
            {
                using (Font f = Ui.F(14f))
                    g.DrawString("（图片加载失败）", f, Brushes.Gray, 24, 24);
                return;
            }
            int cw = _canvas.ClientSize.Width, ch = _canvas.ClientSize.Height;
            if (cw <= 0 || ch <= 0) return;
            _fit = new SizeF((float)cw / _bmp.Width, (float)ch / _bmp.Height);
            float baseScale = Math.Min(_fit.Width, _fit.Height);
            if (baseScale > 1f) baseScale = 1f;      // 小图不放大，保持清晰
            float scale = baseScale * _zoom;
            float dw = _bmp.Width * scale, dh = _bmp.Height * scale;
            float x = (cw - dw) / 2f + _pan.X;
            float y = (ch - dh) / 2f + _pan.Y;

            g.InterpolationMode = _zoom >= 1f ? InterpolationMode.NearestNeighbor
                                              : InterpolationMode.HighQualityBicubic;
            g.PixelOffsetMode = PixelOffsetMode.HighQuality;
            g.DrawImage(_bmp, x, y, dw, dh);
        }
    }

    // ==================================================================
    //  错题本面板：左侧药物列表 + 右侧详情卡 + 工具栏
    // ==================================================================
    public class MistakesPanel : Panel
    {
        private HerbData _data;
        private Dictionary<string, int> _map = new Dictionary<string, int>();
        private ListBox _list;
        private Label _nameLbl, _countLbl, _fxLbl, _usageLbl, _cautionLbl, _emptyLbl;
        private Panel _detailCard;
        private Label _summary;
        private int _current = -1;

        /// <summary>点击「在速查中查看」时回调（参数：药名）</summary>
        public Action<string> OnBrowse;
        /// <summary>点击「开始错题强化」时回调</summary>
        public Action OnStartReview;

        public MistakesPanel(HerbData data)
        {
            _data = data;
            BackColor = Ui.Bg;
            Padding = new Padding(20, 16, 20, 16);
            Build();
            Reload();
        }

        private void Build()
        {
            // ---- 工具栏（底部） ----
            Panel bar = new Panel();
            bar.Dock = DockStyle.Bottom;
            bar.Height = 54;
            bar.BackColor = Ui.Bg;
            Controls.Add(bar);

            Button b1 = Ui.Btn("刷新", 88, 36, Ui.Card, Ui.Brand, 11f);
            b1.Left = 0; b1.Top = 8;
            b1.Click += delegate { Reload(); };
            bar.Controls.Add(b1);

            Button b2 = Ui.Btn("开始错题强化", 150, 36, Ui.Brand, Color.White, 11f);
            b2.Left = 98; b2.Top = 8;
            b2.Click += delegate { if (OnStartReview != null) OnStartReview(); };
            bar.Controls.Add(b2);

            Button b3 = Ui.Btn("清空错题本", 118, 36, Ui.Card, Ui.Bad, 11f);
            b3.Left = 258; b3.Top = 8;
            b3.Click += delegate
            {
                if (MessageBox.Show("确定清空错题本吗？此操作不可撤销。", "确认",
                    MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes)
                {
                    Store.ClearWrong();
                    Reload();
                }
            };
            bar.Controls.Add(b3);

            Button b4 = Ui.Btn("导出为文本", 118, 36, Ui.Card, Ui.Brand, 11f);
            b4.Left = 386; b4.Top = 8;
            b4.Click += delegate { ExportText(); };
            bar.Controls.Add(b4);

            _summary = Ui.Lbl("", 11f, Ui.Sub, false);
            _summary.AutoSize = false;
            _summary.Dock = DockStyle.Right;
            _summary.Width = 300;
            _summary.TextAlign = ContentAlignment.MiddleRight;
            _summary.Padding = new Padding(0, 8, 0, 0);
            bar.Controls.Add(_summary);

            // ---- 左侧列表 ----
            Panel left = new Panel();
            left.Dock = DockStyle.Left;
            left.Width = 320;
            left.Padding = new Padding(0, 0, 14, 0);
            left.BackColor = Ui.Bg;
            Controls.Add(left);

            Panel card = new Panel();
            card.Dock = DockStyle.Fill;
            card.BackColor = Ui.Card;
            card.Padding = new Padding(12);
            left.Controls.Add(card);

            Label lt = Ui.Lbl("错题药物（按错误次数排序）", 11f, Ui.Brand, true);
            lt.Dock = DockStyle.Top;
            lt.Height = 26;
            card.Controls.Add(lt);

            _list = new ListBox();
            _list.Dock = DockStyle.Fill;
            _list.Font = Ui.F(11.5f);
            _list.BorderStyle = BorderStyle.None;
            _list.IntegralHeight = false;
            _list.ItemHeight = 24;
            _list.DrawMode = DrawMode.OwnerDrawFixed;
            _list.DrawItem += DrawItem;
            _list.SelectedIndexChanged += delegate { ShowDetail(); };
            Ui.SetDoubleBuffered(_list);
            card.Controls.Add(_list);
            _list.BringToFront();

            _emptyLbl = Ui.Lbl("错题本还是空的：\n做一次测试，答错或未答对的题目会自动记到这里。", 11.5f, Ui.Sub, false);
            _emptyLbl.AutoSize = false;
            _emptyLbl.Dock = DockStyle.Fill;
            _emptyLbl.TextAlign = ContentAlignment.MiddleCenter;
            card.Controls.Add(_emptyLbl);
            _emptyLbl.BringToFront();

            // ---- 右侧详情 ----
            _detailCard = new Panel();
            _detailCard.Dock = DockStyle.Fill;
            _detailCard.BackColor = Ui.Card;
            _detailCard.Padding = new Padding(22, 18, 22, 18);
            _detailCard.AutoScroll = true;
            Controls.Add(_detailCard);
            _detailCard.BringToFront();

            _nameLbl = new Label();
            _nameLbl.Font = new Font(Ui.FontName, 22f, FontStyle.Bold);
            _nameLbl.ForeColor = Ui.Brand;
            _nameLbl.AutoSize = true;
            _nameLbl.Left = 22; _nameLbl.Top = 18;
            _detailCard.Controls.Add(_nameLbl);

            _countLbl = new Label();
            _countLbl.Font = Ui.FB(12f);
            _countLbl.ForeColor = Color.White;
            _countLbl.BackColor = Ui.Bad;
            _countLbl.AutoSize = false;
            _countLbl.Width = 150; _countLbl.Height = 30;
            _countLbl.Left = 22; _countLbl.Top = 66;
            _countLbl.TextAlign = ContentAlignment.MiddleCenter;
            _detailCard.Controls.Add(_countLbl);

            Button viewBtn = Ui.Btn("在速查中查看", 130, 30, Ui.Card, Ui.Brand, 10.5f);
            viewBtn.Left = 184; viewBtn.Top = 66;
            viewBtn.Click += delegate
            {
                if (_current >= 0 && OnBrowse != null) OnBrowse(CurrentName);
            };
            _detailCard.Controls.Add(viewBtn);

            _fxLbl = MakeDetailLabel(112);
            _usageLbl = MakeDetailLabel(0);
            _cautionLbl = MakeDetailLabel(0);
            _fxLbl.Top = 112;
            _usageLbl.Top = 190;
            _cautionLbl.Top = 250;

            PositionDetail();
            _detailCard.Resize += delegate { PositionDetail(); };
        }

        private Label MakeDetailLabel(int top)
        {
            Label l = new Label();
            l.AutoSize = false;
            l.Font = Ui.F(12f);
            l.ForeColor = Ui.Text;
            l.Left = 22;
            l.Top = top;
            _detailCard.Controls.Add(l);
            return l;
        }

        private void PositionDetail()
        {
            int w = _detailCard.ClientSize.Width - 60;
            if (w < 200) w = 200;
            foreach (Control c in new Control[] { _fxLbl, _usageLbl, _cautionLbl })
            {
                if (c == null) continue;
                c.Width = w;
                Size need = c.GetPreferredSize(new Size(w, 0));
                c.Height = Math.Max(28, need.Height + 8);
            }
            _fxLbl.Top = 108;
            _usageLbl.Top = _fxLbl.Top + _fxLbl.Height + 12;
            _cautionLbl.Top = _usageLbl.Top + _usageLbl.Height + 12;
        }

        private string CurrentName
        {
            get
            {
                MistakeRow r = _list.SelectedItem as MistakeRow;
                return r == null ? "" : r.Herb.Name;
            }
        }

        private void DrawItem(object sender, DrawItemEventArgs e)
        {
            if (e.Index < 0 || e.Index >= _list.Items.Count) return;
            MistakeRow row = _list.Items[e.Index] as MistakeRow;
            if (row == null) return;
            bool sel = (e.State & DrawItemState.Selected) == DrawItemState.Selected;
            Color back = sel ? Ui.BrandLight : Ui.Card;
            using (SolidBrush b = new SolidBrush(back)) e.Graphics.FillRectangle(b, e.Bounds);
            using (Font f = Ui.FB(11.5f))
            using (SolidBrush fb = new SolidBrush(sel ? Ui.Brand : Ui.Text))
                e.Graphics.DrawString(row.Herb.Name, f, fb, e.Bounds.Left + 10, e.Bounds.Top + 4);
            string cat = row.Herb.CatMain;
            using (Font f2 = Ui.F(9.5f))
            using (SolidBrush fb2 = new SolidBrush(Ui.Sub))
                e.Graphics.DrawString(cat, f2, fb2, e.Bounds.Left + 96, e.Bounds.Top + 7);
            string cnt = row.Count + " 次";
            using (Font f3 = Ui.FB(10.5f))
            using (SolidBrush fb3 = new SolidBrush(row.Count >= 3 ? Ui.Bad : Ui.Warn))
            {
                SizeF sz = e.Graphics.MeasureString(cnt, f3);
                e.Graphics.DrawString(cnt, f3, fb3,
                    e.Bounds.Right - sz.Width - 12, e.Bounds.Top + 5);
            }
            using (Pen p = new Pen(Ui.Line))
                e.Graphics.DrawLine(p, e.Bounds.Left + 8, e.Bounds.Bottom - 1,
                    e.Bounds.Right - 8, e.Bounds.Bottom - 1);
        }

        public void Reload()
        {
            _map = Store.LoadWrong();
            _list.BeginUpdate();
            _list.Items.Clear();
            List<MistakeRow> rows = new List<MistakeRow>();
            int total = 0;
            foreach (KeyValuePair<string, int> kv in _map)
            {
                Herb h = _data.Find(kv.Key);
                if (h == null) continue;
                rows.Add(new MistakeRow(h, kv.Value));
                total += kv.Value;
            }
            rows.Sort(delegate(MistakeRow a, MistakeRow b)
            {
                int c = b.Count.CompareTo(a.Count);
                if (c != 0) return c;
                return string.CompareOrdinal(a.Herb.Name, b.Herb.Name);
            });
            foreach (MistakeRow r in rows) _list.Items.Add(r);
            _list.EndUpdate();

            bool has = rows.Count > 0;
            _list.Visible = has;
            _emptyLbl.Visible = !has;
            _detailCard.Visible = has;
            _summary.Text = has
                ? "共 " + rows.Count + " 味药 · 累计错 " + total + " 次"
                : "错题本为空";
            if (has)
            {
                _list.SelectedIndex = 0;
                ShowDetail();
            }
        }

        private void ShowDetail()
        {
            MistakeRow row = _list.SelectedItem as MistakeRow;
            if (row == null)
            {
                _current = -1;
                return;
            }
            _current = _list.SelectedIndex;
            Herb h = row.Herb;
            _nameLbl.Text = h.Name;
            _countLbl.Text = "做错 " + row.Count + " 次";
            _fxLbl.Text = "【分类】" + h.Cat + "\n【性味】" + h.Nature + "\n【归经】" + h.Meridian +
                "\n【功效】" + h.FxText;
            _usageLbl.Text = "【用法用量】" + h.Usage;
            _cautionLbl.Text = "【使用注意】" + h.Caution;
            _fxLbl.ForeColor = Ui.Text;
            PositionDetail();
        }

        private void ExportText()
        {
            try
            {
                StringBuilder sb = new StringBuilder();
                sb.AppendLine("中药学复习系统 · 错题本导出");
                sb.AppendLine("导出时间：" + DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"));
                sb.AppendLine(new string('=', 50));
                int i = 0;
                foreach (object o in _list.Items)
                {
                    MistakeRow r = o as MistakeRow;
                    if (r == null) continue;
                    i++;
                    sb.AppendLine();
                    sb.AppendLine(i + ". " + r.Herb.Name + "（错 " + r.Count + " 次）");
                    sb.AppendLine("   分类：" + r.Herb.Cat);
                    sb.AppendLine("   性味：" + r.Herb.Nature + "　归经：" + r.Herb.Meridian);
                    sb.AppendLine("   功效：" + r.Herb.FxText);
                    sb.AppendLine("   用法：" + r.Herb.Usage);
                    sb.AppendLine("   注意：" + r.Herb.Caution);
                }
                if (i == 0) sb.AppendLine("（错题本为空）");
                string path = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.Desktop),
                    "错题本导出_" + DateTime.Now.ToString("yyyyMMdd_HHmmss") + ".txt");
                File.WriteAllText(path, sb.ToString(), new UTF8Encoding(true));
                if (MessageBox.Show("已导出到桌面：\n" + path + "\n\n现在打开吗？", "导出完成",
                    MessageBoxButtons.YesNo, MessageBoxIcon.Information) == DialogResult.Yes)
                    System.Diagnostics.Process.Start("notepad.exe", path);
            }
            catch (Exception ex)
            {
                MessageBox.Show("导出失败：" + ex.Message, "提示");
            }
        }

        private class MistakeRow
        {
            public Herb Herb;
            public int Count;
            public MistakeRow(Herb h, int c) { Herb = h; Count = c; }
            public override string ToString() { return Herb.Name + "  " + Count + " 次"; }
        }
    }

    // ==================================================================
    //  成绩记录面板：统计卡 + 分数趋势图 + 明细列表
    // ==================================================================
    public class RecordsView : Panel
    {
        private ListView _list;
        private Label _cntLbl, _bestLbl, _avgLbl, _wrongLbl, _lastLbl;
        private TrendChart _chart;
        private Label _empty;

        public RecordsView()
        {
            BackColor = Ui.Bg;
            Padding = new Padding(20, 16, 20, 16);
            Build();
            Reload();
        }

        private void Build()
        {
            Panel bar = new Panel();
            bar.Dock = DockStyle.Bottom;
            bar.Height = 54;
            bar.BackColor = Ui.Bg;
            Controls.Add(bar);

            Button b1 = Ui.Btn("刷新", 88, 36, Ui.Card, Ui.Brand, 11f);
            b1.Left = 0; b1.Top = 8;
            b1.Click += delegate { Reload(); };
            bar.Controls.Add(b1);

            Button b2 = Ui.Btn("清空记录", 110, 36, Ui.Card, Ui.Bad, 11f);
            b2.Left = 98; b2.Top = 8;
            b2.Click += delegate
            {
                if (MessageBox.Show("确定清空全部成绩记录吗？", "确认",
                    MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes)
                {
                    Store.ClearHistory();
                    Reload();
                }
            };
            bar.Controls.Add(b2);

            Label tip = Ui.Lbl("记录保存在 %LocalAppData%\\TcmReview\\history.txt", 10f, Ui.Sub, false);
            tip.Dock = DockStyle.Right;
            tip.AutoSize = false;
            tip.Width = 420;
            tip.TextAlign = ContentAlignment.MiddleRight;
            bar.Controls.Add(tip);

            // ---- 上部：统计卡 + 趋势图 ----
            Panel top = new Panel();
            top.Dock = DockStyle.Top;
            top.Height = 208;
            top.BackColor = Ui.Bg;
            Controls.Add(top);

            Panel stats = new Panel();
            stats.Dock = DockStyle.Left;
            stats.Width = 320;
            stats.BackColor = Ui.Card;
            stats.Padding = new Padding(18, 16, 18, 16);
            stats.Margin = new Padding(0, 0, 14, 0);
            top.Controls.Add(stats);

            Label st = Ui.Lbl("总览", 12.5f, Ui.Brand, true);
            st.Dock = DockStyle.Top;
            st.Height = 28;
            stats.Controls.Add(st);

            _cntLbl = StatRow(stats, "测试次数");
            _bestLbl = StatRow(stats, "历史最高");
            _avgLbl = StatRow(stats, "平均分");
            _lastLbl = StatRow(stats, "最近一次");
            _wrongLbl = StatRow(stats, "错题本药味");

            Panel chartCard = new Panel();
            chartCard.Dock = DockStyle.Fill;
            chartCard.BackColor = Ui.Card;
            chartCard.Padding = new Padding(14, 12, 14, 12);
            top.Controls.Add(chartCard);
            chartCard.BringToFront();

            Label ct = Ui.Lbl("得分趋势（最近 20 次）", 12.5f, Ui.Brand, true);
            ct.Dock = DockStyle.Top;
            ct.Height = 26;
            chartCard.Controls.Add(ct);

            _chart = new TrendChart();
            _chart.Dock = DockStyle.Fill;
            _chart.BackColor = Ui.Card;
            chartCard.Controls.Add(_chart);
            _chart.BringToFront();

            // ---- 下部：明细 ----
            _list = new ListView();
            _list.Dock = DockStyle.Fill;
            _list.View = View.Details;
            _list.FullRowSelect = true;
            _list.Font = Ui.F(11.5f);
            _list.HeaderStyle = ColumnHeaderStyle.Nonclickable;
            _list.BorderStyle = BorderStyle.FixedSingle;
            Ui.SetDoubleBuffered(_list);
            _list.Columns.Add("时间", 170);
            _list.Columns.Add("模式", 110);
            _list.Columns.Add("得分", 100);
            _list.Columns.Add("正确率", 100);
            _list.Columns.Add("正确 / 总题", 120);
            _list.Columns.Add("用时", 110);
            _list.Columns.Add("错题数", 90);
            _list.Columns.Add("评价", 220);
            Controls.Add(_list);
            _list.BringToFront();

            _empty = Ui.Lbl("还没有测试记录：去「开始测试」做一套吧。", 12f, Ui.Sub, false);
            _empty.Dock = DockStyle.Fill;
            _empty.TextAlign = ContentAlignment.MiddleCenter;
            Controls.Add(_empty);
            _empty.BringToFront();
        }

        private Label StatRow(Panel parent, string title)
        {
            Panel row = new Panel();
            row.Dock = DockStyle.Top;
            row.Height = 30;
            row.BackColor = Ui.Card;
            parent.Controls.Add(row);
            row.BringToFront();

            Label t = Ui.Lbl(title, 10.5f, Ui.Sub, false);
            t.Dock = DockStyle.Left;
            t.AutoSize = false;
            t.Width = 110;
            t.TextAlign = ContentAlignment.MiddleLeft;
            row.Controls.Add(t);

            Label v = Ui.Lbl("-", 12f, Ui.Text, true);
            v.Dock = DockStyle.Fill;
            v.AutoSize = false;
            v.TextAlign = ContentAlignment.MiddleRight;
            row.Controls.Add(v);
            v.BringToFront();
            return v;
        }

        public void Reload()
        {
            List<Record> list = Store.LoadHistory();
            list.Reverse();      // 最新在前

            _list.BeginUpdate();
            _list.Items.Clear();
            foreach (Record r in list)
            {
                ListViewItem it = new ListViewItem(r.Time);
                it.SubItems.Add(r.Mode);
                it.SubItems.Add(r.Score + " / " + r.Total);
                it.SubItems.Add(r.Accuracy.ToString("0.0") + " %");
                it.SubItems.Add(r.Correct + " / " + r.Count);
                it.SubItems.Add((r.Seconds / 60) + " 分 " + (r.Seconds % 60) + " 秒");
                it.SubItems.Add(r.Wrong.ToString());
                it.SubItems.Add(HomeForm.Comment(r.Score, r.Total));
                double pct = r.Total > 0 ? (double)r.Score / r.Total : 0;
                if (pct >= 0.9) it.ForeColor = Ui.Ok;
                else if (pct < 0.6) it.ForeColor = Ui.Bad;
                else it.ForeColor = Ui.Text;
                _list.Items.Add(it);
            }
            _list.EndUpdate();

            int best = 0;
            int bestTotal = 100;
            double pctSum = 0;
            int pctCount = 0;
            foreach (Record r in list)
            {
                if (r.Total <= 0) continue;
                double pct = (double)r.Score / r.Total;
                if (r.Score > best)
                {
                    best = r.Score;
                    bestTotal = r.Total;
                }
                pctSum += pct;
                pctCount++;
            }
            _cntLbl.Text = list.Count + " 次";
            _bestLbl.Text = list.Count == 0 ? "-" : best + " / " + bestTotal + " 分";
            _avgLbl.Text = pctCount == 0 ? "-" :
                (pctSum / pctCount * 100).ToString("0.0") + " 分（百分制均值）";
            _lastLbl.Text = list.Count == 0 ? "-" :
                list[0].Score + " / " + list[0].Total + " 分";
            _wrongLbl.Text = Store.LoadWrong().Count + " 味";

            _chart.SetData(list);
            bool has = list.Count > 0;
            _list.Visible = has;
            _empty.Visible = !has;
        }

        /// <summary>分数趋势图（自绘）</summary>
        private class TrendChart : Panel
        {
            private List<Record> _data = new List<Record>();
            public TrendChart()
            {
                SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.UserPaint |
                         ControlStyles.OptimizedDoubleBuffer | ControlStyles.ResizeRedraw, true);
            }
            public void SetData(List<Record> list)
            {
                _data = new List<Record>();
                int start = Math.Max(0, list.Count - 20);
                for (int i = start; i < list.Count; i++) _data.Add(list[i]);
                Invalidate();
            }
            protected override void OnPaint(PaintEventArgs e)
            {
                Graphics g = e.Graphics;
                g.SmoothingMode = System.Drawing.Drawing2D.SmoothingMode.AntiAlias;
                g.Clear(BackColor);
                int n = _data.Count;
                if (n == 0)
                {
                    using (Font f = Ui.F(11f)) g.DrawString("暂无数据", f, Brushes.Gray, 12, 12);
                    return;
                }
                int padL = 34, padR = 10, padT = 14, padB = 26;
                int w = ClientSize.Width - padL - padR;
                int h = ClientSize.Height - padT - padB;
                if (w < 40 || h < 30) return;

                // 网格
                using (Pen gp = new Pen(Color.FromArgb(232, 236, 234)))
                using (Font f = Ui.F(8.5f))
                using (SolidBrush tb = new SolidBrush(Ui.Sub))
                {
                    for (int v = 0; v <= 100; v += 25)
                    {
                        int y = padT + h - (int)(h * v / 100.0);
                        g.DrawLine(gp, padL, y, padL + w, y);
                        g.DrawString(v.ToString(), f, tb, 6, y - 7);
                    }
                }
                // 及格线 / 目标
                using (Pen ok = new Pen(Color.FromArgb(210, 226, 218)) { DashStyle = System.Drawing.Drawing2D.DashStyle.Dash })
                {
                    int y60 = padT + h - (int)(h * 0.6);
                    g.DrawLine(ok, padL, y60, padL + w, y60);
                }

                float slot = (float)w / n;
                float bw = Math.Max(4f, Math.Min(28f, slot * 0.62f));
                using (Font vf = Ui.FB(9f))
                for (int i = 0; i < n; i++)
                {
                    Record r = _data[i];
                    double pct = r.Total > 0 ? (double)r.Score / r.Total : 0;
                    int bh = (int)(h * Math.Min(1.0, pct));
                    float x = padL + slot * i + (slot - bw) / 2f;
                    int y = padT + h - bh;
                    Color c = pct >= 0.9 ? Ui.Ok : (pct >= 0.6 ? Ui.Brand : Ui.Bad);
                    using (SolidBrush b = new SolidBrush(Color.FromArgb(200, c)))
                        g.FillRectangle(b, x, y, bw, bh);
                    using (SolidBrush b2 = new SolidBrush(c))
                        g.FillRectangle(b2, x, y, bw, Math.Min(3, bh));
                    if (n <= 12 || i % 2 == 0)
                    {
                        string s = r.Score.ToString();
                        SizeF sz = g.MeasureString(s, vf);
                        if (sz.Width < slot + 6)
                            g.DrawString(s, vf, new SolidBrush(c), x + (bw - sz.Width) / 2, Math.Max(0, y - 14));
                    }
                    string d = r.Time.Length >= 10 ? r.Time.Substring(5, 5) : "";
                    if (n <= 8 || i % 3 == 0)
                        using (Font df = Ui.F(8f))
                        using (SolidBrush db = new SolidBrush(Ui.Sub))
                            g.DrawString(d, df, db, x - 2, padT + h + 4);
                }
            }
        }
    }
}
