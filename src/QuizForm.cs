// =====================================================================
//  中药学复习系统 —— 答题界面 / 成绩单
//  文件: QuizForm.cs
// =====================================================================
using System;
using System.Collections.Generic;
using System.Drawing;
using System.Text;
using System.Windows.Forms;

namespace TcmReview
{
    public class QuizForm : BaseForm
    {
        private HerbData _data;
        private AppConfig _cfg;
        private QuizData _quiz;

        private int _index;
        private int _elapsed;
        private Timer _timer;
        private bool _finished;
        private List<Button> _navButtons = new List<Button>();

        // 控件
        private Label _titleLbl, _typeLbl, _timerLbl, _progressLbl;
        private ProgressBar _bar;
        private RichTextBox _questionBox;
        private Panel _answerPanel;
        private Button _prev, _next, _submit, _confirm;
        private Panel _navPanel;
        private FlowLayoutPanel _navFlow;
        private Panel _root;

        // 当前题控件状态
        private List<RadioButton> _radios = new List<RadioButton>();
        private List<CheckBox> _checks = new List<CheckBox>();
        private TextBox _fillBox;
        private bool _suppress;

        public QuizForm(HerbData data, AppConfig cfg, QuizData quiz)
        {
            _data = data;
            _cfg = cfg;
            _quiz = quiz;

            Text = quiz.ModeName + " · 中药学复习系统";
            ClientSize = new Size(1180, 760);
            MinimumSize = new Size(1000, 660);
            WindowState = FormWindowState.Maximized;
            KeyPreview = true;

            BuildLayout();
            _timer = new Timer();
            _timer.Interval = 1000;
            _timer.Tick += OnTick;
            _timer.Start();

            KeyDown += OnKeyDown;
            FormClosing += OnClosing;
            Resize += delegate { LayoutTopArea(); };
            Shown += delegate { LayoutTopArea(); };

            ShowQuestion();
            UpdateNav();
            UpdateProgress();
        }

        // ================= 布局 =================
        private void BuildLayout()
        {
            _root = new Panel();
            _root.Dock = DockStyle.Fill;
            _root.Padding = new Padding(14);
            Controls.Add(_root);

            // ---- 右侧答题卡 ----
            _navPanel = new Panel();
            _navPanel.Dock = DockStyle.Right;
            _navPanel.Width = 236;
            _navPanel.BackColor = Ui.Card;
            _navPanel.Padding = new Padding(10);
            _root.Controls.Add(_navPanel);

            Label navTitle = Ui.Lbl("答题卡", 12f, Ui.Brand, true);
            navTitle.Dock = DockStyle.Top;
            navTitle.Height = 28;
            _navPanel.Controls.Add(navTitle);

            Label navHint = Ui.Lbl("○ 未答　● 已答", 10f, Ui.Sub, false);
            navHint.Dock = DockStyle.Bottom;
            navHint.Height = 44;
            navHint.TextAlign = ContentAlignment.BottomLeft;
            _navPanel.Controls.Add(navHint);

            _navFlow = new FlowLayoutPanel();
            _navFlow.Dock = DockStyle.Fill;
            _navFlow.AutoScroll = true;
            _navFlow.BackColor = Ui.Card;
            _navPanel.Controls.Add(_navFlow);
            _navFlow.BringToFront();

            // ---- 顶部状态栏（用 TableLayoutPanel 保证计时器永不被遮挡） ----
            Panel top = new Panel();
            top.Dock = DockStyle.Top;
            top.Height = 88;
            top.BackColor = Ui.Card;
            top.Padding = new Padding(14, 8, 14, 4);
            _root.Controls.Add(top);
            top.BringToFront();

            _bar = new ProgressBar();
            _bar.Dock = DockStyle.Bottom;
            _bar.Height = 8;
            _bar.Style = ProgressBarStyle.Continuous;
            top.Controls.Add(_bar);

            TableLayoutPanel tgrid = new TableLayoutPanel();
            tgrid.Dock = DockStyle.Fill;
            tgrid.ColumnCount = 3;
            tgrid.RowCount = 1;
            tgrid.BackColor = Ui.Card;
            tgrid.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100f));
            tgrid.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 300f));
            tgrid.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 320f));
            top.Controls.Add(tgrid);
            tgrid.BringToFront();

            // 左：题号 + 题型
            Panel left = new Panel();
            left.Dock = DockStyle.Fill;
            left.BackColor = Ui.Card;
            tgrid.Controls.Add(left, 0, 0);

            _titleLbl = Ui.Lbl("", 13.5f, Ui.Brand, true);
            _titleLbl.Left = 2; _titleLbl.Top = 6;
            left.Controls.Add(_titleLbl);

            _typeLbl = Ui.Lbl("", 10.5f, Ui.Sub, false);
            _typeLbl.Left = 2; _typeLbl.Top = 34;
            _typeLbl.AutoSize = false;
            _typeLbl.Width = 120;
            left.Controls.Add(_typeLbl);

            // 中：进度
            Panel midTop = new Panel();
            midTop.Dock = DockStyle.Fill;
            midTop.BackColor = Ui.Card;
            tgrid.Controls.Add(midTop, 1, 0);

            _progressLbl = Ui.Lbl("", 11f, Ui.Sub, false);
            _progressLbl.Dock = DockStyle.Fill;
            _progressLbl.TextAlign = ContentAlignment.MiddleRight;
            _progressLbl.AutoSize = false;
            _progressLbl.Padding = new Padding(0, 0, 8, 0);
            midTop.Controls.Add(_progressLbl);

            // 右：计时器 + 交卷
            Panel rightTop = new Panel();
            rightTop.Dock = DockStyle.Fill;
            rightTop.BackColor = Ui.Card;
            tgrid.Controls.Add(rightTop, 2, 0);

            _timerLbl = new Label();
            _timerLbl.Text = "00:00";
            _timerLbl.Font = Ui.FB(17f);
            _timerLbl.ForeColor = Ui.Accent;
            _timerLbl.BackColor = Color.FromArgb(252, 244, 236);
            _timerLbl.Dock = DockStyle.Fill;
            _timerLbl.TextAlign = ContentAlignment.MiddleCenter;
            _timerLbl.Margin = new Padding(0);
            rightTop.Controls.Add(_timerLbl);

            _submit = Ui.Btn("交卷评分", 112, 42, Ui.Accent, Color.White, 12.5f);
            _submit.Dock = DockStyle.Right;
            _submit.Click += delegate { TryFinish(); };
            rightTop.Controls.Add(_submit);
            _submit.BringToFront();

            // ---- 底部按钮栏 ----
            Panel bottom = new Panel();
            bottom.Dock = DockStyle.Bottom;
            bottom.Height = 62;
            bottom.BackColor = Ui.Bg;
            _root.Controls.Add(bottom);
            bottom.BringToFront();

            _confirm = Ui.Btn("确认作答（显示答案）", 190, 42, Ui.Brand, Color.White, 12f);
            _confirm.Left = 16; _confirm.Top = 10;
            _confirm.Visible = _cfg.Immediate;
            _confirm.Click += delegate { ConfirmCurrent(); };
            bottom.Controls.Add(_confirm);

            _prev = Ui.Btn("上一题", 100, 42, Ui.Card, Ui.Brand, 12f);
            _prev.Left = 220; _prev.Top = 10;
            _prev.Click += delegate { GoTo(_index - 1); };
            bottom.Controls.Add(_prev);

            _next = Ui.Btn("下一题", 100, 42, Ui.Card, Ui.Brand, 12f);
            _next.Left = 330; _next.Top = 10;
            _next.Click += delegate { GoTo(_index + 1); };
            bottom.Controls.Add(_next);

            Button home = Ui.Btn("退出测试", 110, 42, Ui.Card, Ui.Bad, 12f);
            home.Left = 440; home.Top = 10;
            home.Click += delegate { QuitAsk(); };
            bottom.Controls.Add(home);

            // ---- 中间答题区 ----
            Panel mid = new Panel();
            mid.Dock = DockStyle.Fill;
            mid.Padding = new Padding(0, 10, 12, 10);
            _root.Controls.Add(mid);
            mid.BringToFront();

            _questionBox = new RichTextBox();
            _questionBox.Dock = DockStyle.Top;
            _questionBox.Height = 130;
            _questionBox.ReadOnly = true;
            _questionBox.BorderStyle = BorderStyle.None;
            _questionBox.BackColor = Ui.Card;
            _questionBox.Font = Ui.F(14f);
            _questionBox.ForeColor = Ui.Text;
            _questionBox.DetectUrls = false;
            mid.Controls.Add(_questionBox);

            _answerPanel = new Panel();
            _answerPanel.Dock = DockStyle.Fill;
            _answerPanel.AutoScroll = true;
            _answerPanel.BackColor = Ui.Card;
            _answerPanel.Padding = new Padding(18, 8, 18, 8);
            mid.Controls.Add(_answerPanel);
            _answerPanel.BringToFront();

            _answerPanel.Resize += delegate { LayoutAnswerChildren(); };
        }

        /// <summary>兼容保留：顶部改用停靠布局后无需手动摆放</summary>
        private void LayoutTopArea()
        {
            if (_submit != null) _submit.BringToFront();
            if (_timerLbl != null) _timerLbl.BringToFront();
        }

        // ================= 计时 =================
        private void OnTick(object sender, EventArgs e)
        {
            if (_finished) return;
            _elapsed++;
            UpdateTimerLabel();
            if (_quiz.LimitSeconds > 0 && _elapsed >= _quiz.LimitSeconds)
            {
                _timer.Stop();
                _quiz.UsedSeconds = _elapsed;
                MessageBox.Show("考试时间到，系统将自动交卷。", "时间到",
                    MessageBoxButtons.OK, MessageBoxIcon.Information);
                Finish();
            }
            else if (_elapsed % 1 == 0)
            {
                // 累计当前题用时
                if (_index >= 0 && _index < _quiz.Items.Count && !_finished)
                    _quiz.Items[_index].Seconds++;
            }
        }

        private void UpdateTimerLabel()
        {
            if (_quiz.LimitSeconds > 0)
            {
                int left = _quiz.LimitSeconds - _elapsed;
                if (left < 0) left = 0;
                _timerLbl.Text = "剩余 " + (left / 60).ToString("00") + ":" + (left % 60).ToString("00");
                if (left <= 60)
                {
                    _timerLbl.ForeColor = Ui.Bad;
                    _timerLbl.BackColor = Color.FromArgb(253, 236, 234);
                }
                else if (left <= 300)
                {
                    _timerLbl.ForeColor = Ui.Warn;
                    _timerLbl.BackColor = Color.FromArgb(253, 246, 232);
                }
                else
                {
                    _timerLbl.ForeColor = Ui.Brand;
                    _timerLbl.BackColor = Color.FromArgb(236, 246, 241);
                }
            }
            else
            {
                _timerLbl.Text = "已用 " + (_elapsed / 60).ToString("00") + ":" + (_elapsed % 60).ToString("00");
                _timerLbl.ForeColor = Ui.Brand;
                _timerLbl.BackColor = Color.FromArgb(236, 246, 241);
            }
        }

        private void UpdateProgress()
        {
            int answered = _quiz.CountAnswered();
            int total = _quiz.Items.Count;
            _bar.Maximum = Math.Max(1, total);
            _bar.Value = Math.Min(answered, _bar.Maximum);
            _progressLbl.Text = "已答 " + answered + " / " + total + " 题";
        }

        // ================= 显示题目 =================
        private void ShowQuestion()
        {
            if (_index < 0 || _index >= _quiz.Items.Count) return;
            QItem it = _quiz.Items[_index];

            _titleLbl.Text = "第 " + (_index + 1) + " 题 / 共 " + _quiz.Items.Count + " 题";
            _typeLbl.Text = it.TypeName + "　本题 " + it.Points + " 分　" +
                (_cfg.Immediate ? "练习模式：点“确认作答”后显示答案" : "测试模式：可直接跳题，交卷后统一评分");

            _questionBox.Clear();
            AppendQ(it.Question, Ui.Text, true);

            BuildAnswerControls(it);
            _prev.Enabled = _index > 0;
            _next.Enabled = _index < _quiz.Items.Count - 1;
            _confirm.Enabled = !it.Graded;
            UpdateNav();
            UpdateProgress();

            // 标出当前题
            for (int i = 0; i < _navButtons.Count; i++)
            {
                Button b = _navButtons[i];
                int idx = (int)b.Tag;
                b.FlatAppearance.BorderColor = idx == _index ? Ui.Brand : Ui.Line;
                b.FlatAppearance.BorderSize = idx == _index ? 2 : 1;
            }
        }

        private void AppendQ(string text, Color color, bool bold)
        {
            _questionBox.SelectionStart = _questionBox.TextLength;
            _questionBox.SelectionLength = 0;
            _questionBox.SelectionFont = bold ? Ui.FB(14.5f) : Ui.F(12f);
            _questionBox.SelectionColor = color;
            _questionBox.AppendText(text);
        }

        // ---------------- 生成作答控件 ----------------
        private List<Control> _answerControls = new List<Control>();

        private void BuildAnswerControls(QItem it)
        {
            _answerPanel.SuspendLayout();
            _answerPanel.Controls.Clear();
            _answerControls.Clear();
            _radios.Clear();
            _checks.Clear();
            _matchLeftSet.Clear();
            _fillBox = null;
            _suppress = true;

            bool graded = it.Graded;

            if (it.Type == QType.Single || it.Type == QType.Judge)
            {
                for (int i = 0; i < it.Options.Length; i++)
                {
                    RadioButton r = new RadioButton();
                    string letter = ((char)('A' + i)).ToString() + "．";
                    r.Text = letter + it.Options[i];
                    r.Font = Ui.F(13f);
                    r.AutoSize = false;
                    r.Height = 34;
                    r.Tag = i;
                    r.Checked = it.Pick.Contains(i);
                    if (graded) r.Enabled = false;
                    r.CheckedChanged += OnRadioChanged;
                    _answerPanel.Controls.Add(r);
                    _radios.Add(r);
                    _answerControls.Add(r);
                }
            }
            else if (it.Type == QType.Multi)
            {
                for (int i = 0; i < it.Options.Length; i++)
                {
                    CheckBox c = new CheckBox();
                    string letter = ((char)('A' + i)).ToString() + "．";
                    c.Text = letter + it.Options[i];
                    c.Font = Ui.F(13f);
                    c.AutoSize = false;
                    c.Height = 34;
                    c.Tag = i;
                    c.Checked = it.Pick.Contains(i);
                    if (graded) c.Enabled = false;
                    c.CheckedChanged += OnCheckChanged;
                    _answerPanel.Controls.Add(c);
                    _checks.Add(c);
                    _answerControls.Add(c);
                }
                Label hint = Ui.Lbl("（多选：全对满分，漏选得一半分，错选不得分）", 10.5f, Ui.Sub, false);
                _answerPanel.Controls.Add(hint);
                _answerControls.Add(hint);
            }
            else if (it.Type == QType.Fill)
            {
                _fillBox = new TextBox();
                _fillBox.Font = Ui.F(15f);
                _fillBox.Width = 460;
                _fillBox.Height = 36;
                _fillBox.Text = it.FillInput;
                if (graded) _fillBox.ReadOnly = true;
                _fillBox.TextChanged += delegate
                {
                    if (_suppress) return;
                    it.FillInput = _fillBox.Text;
                    it.Answered = _fillBox.Text.Trim().Length > 0;
                    UpdateNav();
                    UpdateProgress();
                };
                _answerPanel.Controls.Add(_fillBox);
                _answerControls.Add(_fillBox);

                Label l2 = Ui.Lbl("提示：填写功效、性味、归经或药名；系统自动容错判定（同义词、错别字）。", 10.5f, Ui.Sub, false);
                _answerPanel.Controls.Add(l2);
                _answerControls.Add(l2);
            }
            else if (it.Type == QType.Match)
            {
                for (int i = 0; i < it.MatchLeft.Length; i++)
                {
                    Label l = Ui.Lbl(it.MatchLeft[i], 12.5f, Ui.Text, true);
                    l.AutoSize = false;
                    l.Height = 30;
                    l.Width = 120;
                    l.TextAlign = ContentAlignment.MiddleLeft;
                    _answerPanel.Controls.Add(l);
                    _answerControls.Add(l);
                    _matchLeftSet.Add(l);

                    ComboBox cb = new ComboBox();
                    cb.DropDownStyle = ComboBoxStyle.DropDownList;
                    cb.Font = Ui.F(12f);
                    cb.Width = 420;
                    cb.Items.Add("（请选择）");
                    foreach (string o in it.MatchOptions) cb.Items.Add(o);
                    cb.Tag = i;
                    cb.SelectedIndex = it.MatchPick != null && it.MatchPick[i] >= 0 ? it.MatchPick[i] + 1 : 0;
                    if (graded) cb.Enabled = false;
                    cb.SelectedIndexChanged += delegate(object s, EventArgs e)
                    {
                        if (_suppress) return;
                        ComboBox c2 = (ComboBox)s;
                        int k = (int)c2.Tag;
                        it.MatchPick[k] = c2.SelectedIndex - 1;
                        bool all = true;
                        foreach (int p in it.MatchPick) if (p < 0) { all = false; break; }
                        it.Answered = all;
                        UpdateNav();
                        UpdateProgress();
                    };
                    _answerPanel.Controls.Add(cb);
                    _answerControls.Add(cb);
                }
            }

            // 已批改的题目显示结果
            if (graded) AddFeedback(it);

            _answerPanel.ResumeLayout();
            LayoutAnswerChildren();
            _suppress = false;
        }

        private void LayoutAnswerChildren()
        {
            int w = _answerPanel.ClientSize.Width - _answerPanel.Padding.Horizontal;
            if (w < 200) w = 200;
            int y = _answerPanel.Padding.Top;
            foreach (Control c in _answerControls)
            {
                c.Left = _answerPanel.Padding.Left;
                c.Width = _matchLeftSet.Contains(c) ? 130 : (w - 10);
                if (c is Label)
                {
                    Size need = c.GetPreferredSize(new Size(c.Width, 0));
                    c.Height = Math.Max(24, need.Height + 4);
                }
                c.Top = y;
                y += c.Height + 6;
            }
        }

        private readonly List<Control> _matchLeftSet = new List<Control>();

        private void AddFeedback(QItem it)
        {
            bool ok = it.Score >= it.Points - 0.001;
            bool part = !ok && it.Score > 0;
            Color col = ok ? Ui.Ok : (part ? Ui.Warn : Ui.Bad);
            string mark = ok ? "✔ 回答正确" : (part ? "◐ 部分正确" : "✘ 回答错误");

            Label l1 = Ui.Lbl(mark + "　得分 " + Trim(it.Score) + " / " + it.Points, 13f, col, true);
            l1.AutoSize = false;
            l1.Height = 30;
            _answerPanel.Controls.Add(l1);
            _answerControls.Add(l1);

            string correct = "";
            if (it.Type == QType.Single || it.Type == QType.Judge)
                correct = ((char)('A' + it.AnswerIndex)).ToString() + "．" + it.Options[it.AnswerIndex];
            else if (it.Type == QType.Multi)
            {
                List<string> s = new List<string>();
                foreach (int a in it.AnswerSet)
                    s.Add(((char)('A' + a)).ToString() + "．" + it.Options[a]);
                correct = string.Join("　", s.ToArray());
            }
            else if (it.Type == QType.Fill) correct = it.FillAnswer;

            Label l2 = Ui.Lbl("【正确答案】" + correct, 12.5f, Ui.Brand, true);
            l2.AutoSize = false;
            _answerPanel.Controls.Add(l2);
            _answerControls.Add(l2);

            Label l3 = Ui.Lbl("【解析】" + it.Reference + "（分类：" + it.Tip + "）", 11.5f, Ui.Sub, false);
            l3.AutoSize = false;
            _answerPanel.Controls.Add(l3);
            _answerControls.Add(l3);
        }

        private static string Trim(double v)
        {
            if (Math.Abs(v - Math.Round(v)) < 0.001) return ((int)Math.Round(v)).ToString();
            return v.ToString("0.#");
        }

        // ---------------- 作答事件 ----------------
        private void OnRadioChanged(object sender, EventArgs e)
        {
            if (_suppress) return;
            RadioButton r = (RadioButton)sender;
            if (!r.Checked) return;
            QItem it = _quiz.Items[_index];
            it.Pick.Clear();
            it.Pick.Add((int)r.Tag);
            it.Answered = true;
            UpdateNav();
            UpdateProgress();
        }

        private void OnCheckChanged(object sender, EventArgs e)
        {
            if (_suppress) return;
            QItem it = _quiz.Items[_index];
            it.Pick.Clear();
            foreach (CheckBox c in _checks)
                if (c.Checked) it.Pick.Add((int)c.Tag);
            it.Answered = it.Pick.Count > 0;
            UpdateNav();
            UpdateProgress();
        }

        private void ConfirmCurrent()
        {
            if (_index < 0 || _index >= _quiz.Items.Count) return;
            QItem it = _quiz.Items[_index];
            if (!it.Answered)
            {
                MessageBox.Show("请先作答。", "提示", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }
            it.Score = QuizData.ScoreOf(it);
            it.Graded = true;
            BuildAnswerControls(it);
            _confirm.Enabled = false;
            UpdateNav();

            if (it.Score >= it.Points - 0.001)
            {
                // 答对，稍作停顿自动下一题
                if (_index < _quiz.Items.Count - 1) GoTo(_index + 1);
            }
            else
            {
                Store.AddWrong(new string[] { it.HerbName });
            }
        }

        // ---------------- 导航 ----------------
        private void GoTo(int ni)
        {
            if (ni < 0 || ni >= _quiz.Items.Count) return;
            _index = ni;
            ShowQuestion();
        }

        private void OnKeyDown(object sender, KeyEventArgs e)
        {
            if (_finished) return;
            if (e.KeyCode == Keys.Left) { GoTo(_index - 1); e.Handled = true; }
            else if (e.KeyCode == Keys.Right || e.KeyCode == Keys.PageDown) { GoTo(_index + 1); e.Handled = true; }
            else if (e.KeyCode == Keys.PageUp) { GoTo(_index - 1); e.Handled = true; }
            else if (e.KeyCode == Keys.D1 || e.KeyCode == Keys.NumPad1) { ClickRadio(0); }
            else if (e.KeyCode == Keys.D2 || e.KeyCode == Keys.NumPad2) { ClickRadio(1); }
            else if (e.KeyCode == Keys.D3 || e.KeyCode == Keys.NumPad3) { ClickRadio(2); }
            else if (e.KeyCode == Keys.D4 || e.KeyCode == Keys.NumPad4) { ClickRadio(3); }
            else if (e.KeyCode == Keys.Enter && _cfg.Immediate) { ConfirmCurrent(); }
        }

        private void ClickRadio(int i)
        {
            if (_index < 0 || _index >= _quiz.Items.Count) return;
            QItem it = _quiz.Items[_index];
            if (it.Graded) return;
            if (it.Type == QType.Single || it.Type == QType.Judge)
            {
                if (i < _radios.Count) _radios[i].Checked = true;
            }
        }

        private void UpdateNav()
        {
            if (_navButtons.Count != _quiz.Items.Count)
            {
                _navFlow.Controls.Clear();
                _navButtons.Clear();
                _navFlow.SuspendLayout();
                for (int i = 0; i < _quiz.Items.Count; i++)
                {
                    Button b = new Button();
                    b.Width = 44; b.Height = 40;
                    b.Text = (i + 1).ToString();
                    b.Font = Ui.F(10.5f);
                    b.FlatStyle = FlatStyle.Flat;
                    b.FlatAppearance.BorderSize = 1;
                    b.FlatAppearance.BorderColor = Ui.Line;
                    b.BackColor = Ui.Card;
                    b.ForeColor = Ui.Text;
                    b.Tag = i;
                    b.Cursor = Cursors.Hand;
                    b.Margin = new Padding(3);
                    b.Click += delegate(object s, EventArgs e)
                    {
                        if (_finished) return;
                        _index = (int)((Button)s).Tag;
                        ShowQuestion();
                    };
                    _navFlow.Controls.Add(b);
                    _navButtons.Add(b);
                }
                _navFlow.ResumeLayout();
            }

            for (int i = 0; i < _navButtons.Count; i++)
            {
                Button b = _navButtons[i];
                QItem it = _quiz.Items[i];
                if (it.Graded)
                {
                    bool ok = it.Score >= it.Points - 0.001;
                    bool part = !ok && it.Score > 0;
                    b.BackColor = ok ? Ui.Ok : (part ? Ui.Warn : Ui.Bad);
                    b.ForeColor = Color.White;
                }
                else if (i == _index)
                {
                    b.BackColor = Ui.Brand;
                    b.ForeColor = Color.White;
                }
                else if (it.Answered)
                {
                    b.BackColor = Ui.BrandLight;
                    b.ForeColor = Ui.Brand;
                }
                else
                {
                    b.BackColor = Ui.Card;
                    b.ForeColor = Ui.Text;
                }
            }
        }

        // ================= 交卷 =================
        private void TryFinish()
        {
            int unanswered = _quiz.Items.Count - _quiz.CountAnswered();
            int graded = 0;
            foreach (QItem it in _quiz.Items) if (it.Graded) graded++;

            string msg = "确定交卷评分吗？\n\n共 " + _quiz.Items.Count + " 题";
            if (unanswered > 0) msg += "，其中 " + unanswered + " 题未作答（按 0 分计）";
            if (_cfg.Immediate && graded < _quiz.Items.Count)
                msg += "\n注意：练习模式下尚未确认作答的 " + (_quiz.Items.Count - graded) + " 题将按你当前选择自动评分";
            msg += "。";

            if (MessageBox.Show(msg, "交卷确认", MessageBoxButtons.YesNo,
                MessageBoxIcon.Question) == DialogResult.Yes)
            {
                Finish();
            }
        }

        private void Finish()
        {
            if (_finished) return;
            _finished = true;
            _timer.Stop();
            _quiz.UsedSeconds = _elapsed;
            _quiz.Grade();

            List<string> wrongs = new List<string>();
            foreach (QItem it in _quiz.Items)
                if (it.Score < it.Points - 0.001) wrongs.Add(it.HerbName);
            if (wrongs.Count > 0) Store.AddWrong(wrongs);

            Record r = new Record();
            r.Time = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss");
            r.Mode = _quiz.ModeName;
            r.Score = _quiz.Score();
            r.Total = _quiz.TotalScore();
            r.Correct = _quiz.CountCorrect();
            r.Count = _quiz.Items.Count;
            r.Seconds = _elapsed;
            r.Wrong = wrongs.Count;
            Store.AppendHistory(r);

            ShowResult(r);
        }

        // ================= 成绩单 =================
        private void ShowResult(Record r)
        {
            Controls.Clear();

            Panel root = new Panel();
            root.Dock = DockStyle.Fill;
            root.Padding = new Padding(18);
            root.AutoScroll = true;
            Controls.Add(root);

            // ---- 分数卡片 ----
            Panel card = new Panel();
            card.Dock = DockStyle.Top;
            card.Height = 190;
            card.BackColor = Ui.Brand;
            root.Controls.Add(card);

            int total = r.Total <= 0 ? 100 : r.Total;
            double pct = (double)r.Score / total;
            string comment = HomeForm.Comment(r.Score, total);

            Label score = new Label();
            score.Text = r.Score + " 分";
            score.Font = new Font(Ui.FontName, 52f, FontStyle.Bold);
            score.ForeColor = Color.White;
            score.AutoSize = true;
            score.BackColor = Color.Transparent;
            score.Left = 40; score.Top = 32;
            card.Controls.Add(score);

            Label of = new Label();
            of.Text = "满分 " + total + " 分　" + comment;
            of.Font = Ui.FB(15f);
            of.ForeColor = Color.FromArgb(220, 242, 233);
            of.AutoSize = true;
            of.MaximumSize = new Size(390, 0);
            of.BackColor = Color.Transparent;
            of.Left = 46; of.Top = 118;
            card.Controls.Add(of);

            string[] stats = new string[] {
                "正确 " + r.Correct + " / " + r.Count + " 题",
                "正确率 " + r.Accuracy.ToString("0.0") + " %",
                "用时 " + (r.Seconds / 60) + " 分 " + (r.Seconds % 60) + " 秒",
                "错题 " + r.Wrong + " 题",
                "模式 " + r.Mode,
                "时间 " + r.Time
            };
            for (int i = 0; i < stats.Length; i++)
            {
                Label l = new Label();
                l.Text = stats[i];
                l.Font = Ui.FB(13f);
                l.ForeColor = Color.White;
                l.AutoSize = true;
                l.BackColor = Color.Transparent;
                l.Left = 470;
                l.Top = 30 + i * 26;
                card.Controls.Add(l);
            }

            // ---- 按钮栏 ----
            Panel bar = new Panel();
            bar.Dock = DockStyle.Top;
            bar.Height = 62;
            bar.BackColor = Ui.Bg;
            root.Controls.Add(bar);

            Button again = Ui.Btn("再做一套", 130, 42, Ui.Brand, Color.White, 12.5f);
            again.Left = 0; again.Top = 10;
            again.Click += delegate { DialogResult = DialogResult.OK; Close(); };
            bar.Controls.Add(again);

            Button review = Ui.Btn("只重做错题", 130, 42, Ui.Card, Ui.Brand, 12.5f);
            review.Left = 142; review.Top = 10;
            review.Enabled = r.Wrong > 0;
            review.Click += delegate { ReviewWrong(); };
            bar.Controls.Add(review);

            Button home = Ui.Btn("返回首页", 130, 42, Ui.Card, Ui.Sub, 12.5f);
            home.Left = 284; home.Top = 10;
            home.Click += delegate { DialogResult = DialogResult.Cancel; Close(); };
            bar.Controls.Add(home);

            // ---- 逐题分析 ----
            RichTextBox ana = new RichTextBox();
            ana.Dock = DockStyle.Fill;
            ana.ReadOnly = true;
            ana.BackColor = Ui.Card;
            ana.BorderStyle = BorderStyle.None;
            ana.Font = Ui.F(12.5f);
            ana.DetectUrls = false;
            root.Controls.Add(ana);
            ana.BringToFront();
            bar.BringToFront();
            card.BringToFront();

            WriteAnalysis(ana);
        }

        private void WriteAnalysis(RichTextBox box)
        {
            box.Clear();
            W(box, "逐 题 解 析\n", Ui.Brand, 17f, true);
            W(box, "说明：绿色为本程序判定正确，红色为错误，黄色为部分正确（多选题漏选）。\n\n", Ui.Sub, 11f, false);

            for (int i = 0; i < _quiz.Items.Count; i++)
            {
                QItem it = _quiz.Items[i];
                bool ok = it.Score >= it.Points - 0.001;
                bool part = !ok && it.Score > 0;
                Color col = ok ? Ui.Ok : (part ? Ui.Warn : Ui.Bad);
                string head = (ok ? "✔" : (part ? "◐" : "✘")) + " 第 " + (i + 1) + " 题　" +
                    it.TypeName + "　得分 " + Trim(it.Score) + "/" + it.Points +
                    "　（" + it.HerbName + "）";
                W(box, head + "\n", col, 13f, true);
                W(box, it.Question.Replace("\n\n", " ").Replace("\n", " ") + "\n", Ui.Text, 12f, false);

                if (it.Type == QType.Single || it.Type == QType.Judge || it.Type == QType.Multi)
                {
                    for (int k = 0; k < it.Options.Length; k++)
                    {
                        bool isAns = false;
                        if (it.Type == QType.Multi)
                        {
                            foreach (int a in it.AnswerSet) if (a == k) { isAns = true; break; }
                        }
                        else isAns = (k == it.AnswerIndex);
                        bool chosen = it.Pick.Contains(k);
                        string mark = (chosen ? "［你选］" : "　　　") + (isAns ? "［正确］" : "　　　");
                        string line = "   " + ((char)('A' + k)) + "．" + it.Options[k] + "　" + mark + "\n";
                        Color c = isAns ? Ui.Ok : (chosen ? Ui.Bad : Ui.Sub);
                        W(box, line, c, 12f, isAns);
                    }
                }
                else if (it.Type == QType.Fill)
                {
                    W(box, "   你的作答：" + (it.FillInput.Length == 0 ? "（未作答）" : it.FillInput) + "\n", Ui.Bad, 12f, false);
                    W(box, "   正确答案：" + it.FillAnswer + "\n", Ui.Ok, 12f, true);
                }
                else if (it.Type == QType.Match)
                {
                    for (int k = 0; k < it.MatchLeft.Length; k++)
                    {
                        int mine = it.MatchPick != null && k < it.MatchPick.Length ? it.MatchPick[k] : -1;
                        string my = mine >= 0 && mine < it.MatchOptions.Length ? it.MatchOptions[mine] : "（未选）";
                        string std = it.MatchAnswer[k] < it.MatchOptions.Length ? it.MatchOptions[it.MatchAnswer[k]] : "";
                        W(box, "   " + it.MatchLeft[k] + " → 你选：" + my + "　正确：" + std + "\n",
                            my == std ? Ui.Ok : Ui.Bad, 12f, false);
                    }
                }

                if (!ok)
                    W(box, "   解析：" + it.Reference + "\n", Ui.Brand, 11.5f, false);
                W(box, "   用时约 " + it.Seconds + " 秒　（" + it.Tip + "）\n\n", Ui.Sub, 10.5f, false);
            }
        }

        private void W(RichTextBox box, string text, Color color, float size, bool bold)
        {
            box.SelectionStart = box.TextLength;
            box.SelectionLength = 0;
            box.SelectionFont = bold
                ? new Font(Ui.FontName, size, FontStyle.Bold)
                : new Font(Ui.FontName, size);
            box.SelectionColor = color;
            box.AppendText(text);
        }

        // ---------------- 只重做错题 ----------------
        private void ReviewWrong()
        {
            List<QItem> wrongs = _quiz.WrongItems();
            if (wrongs.Count == 0) return;

            List<QItem> items = new List<QItem>();
            foreach (QItem w in wrongs)
            {
                QItem n = new QItem();
                n.Type = w.Type;
                n.HerbName = w.HerbName;
                n.Question = w.Question;
                n.Options = w.Options;
                n.AnswerIndex = w.AnswerIndex;
                n.AnswerSet = w.AnswerSet;
                n.FillAnswer = w.FillAnswer;
                n.MatchAnswer = w.MatchAnswer;
                n.MatchLeft = w.MatchLeft;
                n.MatchOptions = w.MatchOptions;
                n.MatchPick = new int[w.MatchPick != null ? w.MatchPick.Length : 0];
                for (int i = 0; i < n.MatchPick.Length; i++) n.MatchPick[i] = -1;
                n.Reference = w.Reference;
                n.Tip = w.Tip;
                n.Points = w.Points;
                items.Add(n);
            }

            QuizData qd = new QuizData();
            qd.Items = items;
            qd.LimitSeconds = 0;
            qd.ModeName = "错题重做";
            for (int i = 0; i < qd.Items.Count; i++) qd.Items[i].Order = i + 1;

            AppConfig c = _cfg.Clone();
            c.Immediate = true;

            QuizForm f = new QuizForm(_data, c, qd);
            DialogResult = DialogResult.OK;
            Hide();
            f.ShowDialog(this);
            Close();
        }

        private void QuitAsk()
        {
            if (_finished) { Close(); return; }
            if (MessageBox.Show("确定退出测试吗？本次成绩不会保存。", "退出确认",
                MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes)
            {
                _timer.Stop();
                DialogResult = DialogResult.Cancel;
                Close();
            }
        }

        private void OnClosing(object sender, FormClosingEventArgs e)
        {
            if (_timer != null) _timer.Stop();
        }
    }
}
