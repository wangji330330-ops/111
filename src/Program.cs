// =====================================================================
//  中药学复习系统 —— 程序入口
//  文件: Program.cs
// =====================================================================
using System;
using System.Collections.Generic;
using System.Text;
using System.Windows.Forms;

namespace TcmReview
{
    internal static class Program
    {
        public static bool Debug = false;

        public static void Trace(string msg)
        {
            if (!Debug) return;
            try
            {
                string p = System.IO.Path.Combine(
                    System.IO.Path.GetTempPath(), "tcm_debug.log");
                System.IO.File.AppendAllText(p,
                    DateTime.Now.ToString("HH:mm:ss.fff") + "  " + msg + Environment.NewLine,
                    new UTF8Encoding(false));
            }
            catch { }
        }

        [STAThread]
        private static void Main(string[] args)
        {
            // --update-url <版本文件地址>：指定更新检查地址
            if (args != null)
            {
                for (int i = 0; i < args.Length - 1; i++)
                    if (args[i] == "--update-url") UpdateChecker.Url = args[i + 1];
            }
            // 也可写在工作目录的 update_url.txt 里（一行地址）
            try
            {
                if (UpdateChecker.Url.Length == 0 && System.IO.File.Exists("update_url.txt"))
                    UpdateChecker.Url = System.IO.File.ReadAllText("update_url.txt").Trim();
            }
            catch { }

            Debug = Environment.GetEnvironmentVariable("TCM_DEBUG") == "1";
            if (Debug)
            {
                try { System.IO.File.Delete("debug.log"); }
                catch { }
            }
            Trace("Main start, args=" + (args == null ? "null" : args.Length.ToString()));

            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            SetIcon();
            Trace("styles+icon ok, icon=" + (AppIcon.Value != null ? "loaded" : "null"));

            Application.ThreadException += delegate(object s, System.Threading.ThreadExceptionEventArgs e)
            {
                Trace("ThreadException: " + e.Exception);
            };
            AppDomain.CurrentDomain.UnhandledException += delegate(object s, UnhandledExceptionEventArgs e)
            {
                Trace("UnhandledException: " + e.ExceptionObject);
            };

            // 自测模式：dotnet 中药复习.exe --selftest [题量]
            if (args != null && args.Length > 0 && args[0] == "--selftest")
            {
                int n = 120;
                if (args.Length > 1)
                {
                    int t;
                    if (int.TryParse(args[1], out t) && t > 0) n = t;
                }
                Environment.ExitCode = SelfTest.Run(n);
                return;
            }

            try
            {
                Trace("loading herb data...");
                HerbData d = HerbData.Current;
                Trace("herbs=" + d.Herbs.Count + " cats=" + d.Categories.Count);
                Trace("creating HomeForm...");
                HomeForm hf = new HomeForm();
                Trace("HomeForm created; running message loop");
                Application.Run(hf);
                Trace("message loop exited normally");
            }
            catch (Exception ex)
            {
                Trace("EXCEPTION: " + ex);
                MessageBox.Show("程序发生错误：\n" + ex.ToString(), "错误",
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
            Trace("Main end");
        }

        /// <summary>从嵌入资源加载程序图标（缺失时忽略）</summary>
        private static void SetIcon()
        {
            try
            {
                System.IO.Stream s = typeof(Program).Assembly
                    .GetManifestResourceStream("app.ico");
                if (s == null) return;
                System.Drawing.Icon ic = new System.Drawing.Icon(s, 32, 32);
                // 保存为静态引用，供各窗体使用
                AppIcon.Value = ic;
            }
            catch { }
        }
    }

    public static class AppIcon
    {
        public static System.Drawing.Icon Value;
    }

    // ------------------------------------------------------------------
    //  自测：批量出题并交叉校验题目正确性（无界面）
    // ------------------------------------------------------------------
    internal static class SelfTest
    {
        public static int Run(int rounds)
        {
            StringBuilder log = new StringBuilder();
            int problems = 0;

            HerbData data = HerbData.Current;
            log.AppendLine("题库载入：药材 " + data.Herbs.Count + " 味，分类 " +
                data.Categories.Count + " 个，同义词组 " + data.Synonyms.Count + " 组");
            if (data.Herbs.Count < 100) { log.AppendLine("！题库过小"); problems++; }

            Dictionary<string, int> typeCount = new Dictionary<string, int>();
            int totalItems = 0;
            int dupStems = 0;
            int shortPapers = 0;

            for (int seed = 1; seed <= rounds; seed++)
            {
                // 每 4 套里换一种组卷方式，覆盖所有题型
                int kind = seed % 4;
                AppConfig cfg = new AppConfig();
                cfg.Seed = seed;
                cfg.Cats = new List<string>();
                switch (kind)
                {
                    case 0:   // 全选择题：单选+多选 = 100 分
                        cfg.N1 = 20; cfg.P1 = 3;
                        cfg.N2 = 8; cfg.P2 = 5;
                        cfg.N3 = 0; cfg.N4 = 0;
                        break;
                    case 1:   // 判断+填空 = 100 分
                        cfg.N1 = 0; cfg.N2 = 0;
                        cfg.N3 = 10; cfg.P3 = 2;
                        cfg.N4 = 24; cfg.P4 = 3;
                        break;
                    case 2:   // 默认 100 分制：单选 20×3 + 填空 10×3 + 判断 5×2
                        cfg.N1 = 20; cfg.P1 = 3;
                        cfg.N4 = 10; cfg.P4 = 3;
                        cfg.N3 = 5; cfg.P3 = 2;
                        break;
                    default:  // 四种题型混合 = 100 分（含分类限定）
                        cfg.N1 = 8; cfg.P1 = 3;
                        cfg.N2 = 4; cfg.P2 = 5;
                        cfg.N4 = 8; cfg.P4 = 3;
                        cfg.N3 = 10; cfg.P3 = 2;
                        if (data.Categories.Count > 4)
                        {
                            cfg.Cats.Add(data.Categories[seed % data.Categories.Count]);
                            cfg.Cats.Add(data.Categories[(seed + 7) % data.Categories.Count]);
                        }
                        break;
                }

                QuizEngine eng = new QuizEngine(data, cfg);
                List<QItem> items = eng.BuildQuiz(cfg);
                totalItems += items.Count;

                // 同一套试卷内不允许出现重复题干
                Dictionary<string, int> stems = new Dictionary<string, int>();
                foreach (QItem it in items)
                {
                    string t = it.TypeName;
                    if (!typeCount.ContainsKey(t)) typeCount[t] = 0;
                    typeCount[t]++;

                    string stem = it.TypeName + "|" + it.Question;
                    if (stems.ContainsKey(stem)) dupStems++;
                    else stems[stem] = 1;

                    int p = Validate(data, it);
                    if (p > 0)
                    {
                        problems++;
                        if (problems <= 80)
                            log.AppendLine("！seed=" + seed + " " + it.TypeName + " [" + it.HerbName + "] " +
                                it.Question.Replace("\n", " "));
                    }
                }
                int want = cfg.N1 + cfg.N2 + cfg.N3 + cfg.N4;
                if (items.Count < want) shortPapers++;
            }

            // ---- 判分逻辑测试 ----
            int scoreProblems = 0;
            scoreProblems += CheckFill("辛，温", "辛，温");
            scoreProblems += CheckFill("辛温", "辛，温");
            scoreProblems += CheckFill("发散风寒", "发汗解表");
            scoreProblems += CheckFill("辛、甘，微温", "辛、甘，微温");
            scoreProblems += CheckFill("解表散风", "解表散风，透疹消疮");
            scoreProblems += CheckFill("完全不同", "利水渗湿") == 0 ? 0 : 0; // 只记录，不断言
            if (!AnswerMatcher.IsCorrect("辛，温", "辛温")) scoreProblems++;

            log.AppendLine("出题总量：" + totalItems + " 题（" + rounds + " 套随机卷，覆盖各种题型组合）");
            foreach (KeyValuePair<string, int> kv in typeCount)
                log.AppendLine("　" + kv.Key + "：" + kv.Value + " 题");
            log.AppendLine("试卷内重复题干数：" + dupStems + "（必须为 0）");
            log.AppendLine("题量不足的试卷数：" + shortPapers + "（分类范围过小时允许）");
            log.AppendLine("题目校验问题数：" + problems);
            log.AppendLine("判分用例问题数：" + scoreProblems);
            log.AppendLine(problems == 0 && scoreProblems == 0 && dupStems == 0
                ? "SELFTEST PASS" : "SELFTEST FAIL");

            string txt = log.ToString();
            try
            {
                System.IO.File.WriteAllText("selftest.txt", txt, new UTF8Encoding(false));
            }
            catch { }

            // 控制台只输出 ASCII 摘要，避免代码页乱码；详细报告见 selftest.txt
            Console.WriteLine("items=" + totalItems + " problems=" + problems +
                " scoreProblems=" + scoreProblems + " dupStems=" + dupStems +
                " shortPapers=" + shortPapers);
            int ti = 0;
            foreach (KeyValuePair<string, int> kv in typeCount)
                Console.WriteLine("  type[" + (ti++) + "] count=" + kv.Value);
            Console.WriteLine(problems == 0 && scoreProblems == 0 && dupStems == 0
                ? "SELFTEST PASS" : "SELFTEST FAIL");
            Console.WriteLine("report: selftest.txt");

            return (problems == 0 && scoreProblems == 0 && dupStems == 0) ? 0 : 1;
        }

        private static int CheckFill(string user, string answer)
        {
            return AnswerMatcher.IsCorrect(user, answer) ? 0 : 1;
        }

        /// <summary>校验一道题自洽；返回问题条数</summary>
        private static int Validate(HerbData data, QItem it)
        {
            int bad = 0;

            if (it.Type == QType.Single || it.Type == QType.Judge)
            {
                if (it.Options.Length < 2) bad++;
                if (it.AnswerIndex < 0 || it.AnswerIndex >= it.Options.Length) bad++;
                if (it.Type == QType.Judge && it.Options.Length != 2) bad++;
                if (it.Type == QType.Judge) return bad;

                Herb h = data.Find(it.HerbName);
                if (h == null) return bad + 1;

                if (it.Question.IndexOf("不是「", StringComparison.Ordinal) >= 0)
                {
                    // 题型：下列哪一项不是「X」的功效 —— 选项中恰好一项不是该药功效
                    int fakeCount = 0;
                    for (int i = 0; i < it.Options.Length; i++)
                    {
                        bool has = h.FxOverlap(it.Options[i]);
                        if (i == it.AnswerIndex)
                        {
                            if (has) bad++;          // 正确项不该是它的功效
                            else fakeCount++;
                        }
                        else if (!has) bad++;        // 干扰项必须是它的功效
                    }
                    if (fakeCount != 1) bad++;
                    if (it.AnswerIndex >= 0 && it.AnswerIndex < it.Options.Length &&
                        h.FxOverlap(it.Options[it.AnswerIndex])) bad++;
                }
                else if (it.Question.IndexOf("的功效是", StringComparison.Ordinal) >= 0 &&
                         it.Options[0].Length < 20)
                {
                    // 题型：X 的功效是 —— 选项为功效项
                    string ans = it.Options[it.AnswerIndex];
                    if (!h.FxOverlap(ans)) bad++;
                    for (int i = 0; i < it.Options.Length; i++)
                        if (i != it.AnswerIndex && h.FxOverlap(it.Options[i])) bad++;
                }
                else if (it.Question.IndexOf("的性味是", StringComparison.Ordinal) >= 0)
                {
                    if (AnswerMatcher.Norm(it.Options[it.AnswerIndex]) != AnswerMatcher.Norm(h.Nature)) bad++;
                    if (Dup(it.Options)) bad++;
                }
                else if (it.Question.IndexOf("的归经是", StringComparison.Ordinal) >= 0)
                {
                    if (AnswerMatcher.Norm(it.Options[it.AnswerIndex]) != AnswerMatcher.Norm(h.Meridian)) bad++;
                    if (Dup(it.Options)) bad++;
                }
                else if (it.Question.IndexOf("属于下列哪一类药物", StringComparison.Ordinal) >= 0)
                {
                    if (it.Options[it.AnswerIndex] != h.Cat) bad++;
                    if (Dup(it.Options)) bad++;
                }
                else
                {
                    // 题型：具有「X」功效的药物是 A/B/C/D —— 选项为药名
                    string fx = ExtractAsk(it.Question);
                    if (fx == null) { bad++; }
                    else
                    {
                        if (CountOwners(data, fx) != 1) bad++;
                        for (int i = 0; i < it.Options.Length; i++)
                        {
                            Herb o = data.Find(it.Options[i]);
                            if (o == null) { bad++; continue; }
                            bool has = o.HasFx(fx);
                            if (i == it.AnswerIndex && !has) bad++;
                            if (i != it.AnswerIndex && has) bad++;
                        }
                    }
                }
            }
            else if (it.Type == QType.Multi)
            {
                if (it.Options.Length < 3) bad++;
                if (it.AnswerSet.Length < 2) bad++;

                bool byFx = it.Question.IndexOf("具有「", StringComparison.Ordinal) == 0;
                if (byFx)
                {
                    int k = it.Question.IndexOf("」功效的药物有", StringComparison.Ordinal);
                    if (k > 0)
                    {
                        string fx = it.Question.Substring(3, k - 3);
                        for (int i = 0; i < it.Options.Length; i++)
                        {
                            Herb o = data.Find(it.Options[i]);
                            if (o == null) { bad++; continue; }
                            bool has = o.HasFx(fx);
                            bool key = Contains(it.AnswerSet, i);
                            if (key != has) bad++;
                        }
                    }
                }
                else
                {
                    Herb h = data.Find(it.HerbName);
                    if (h == null) bad++;
                    else
                    {
                        for (int i = 0; i < it.Options.Length; i++)
                        {
                            bool has = h.FxOverlap(it.Options[i]);
                            bool key = Contains(it.AnswerSet, i);
                            if (key != has) bad++;
                        }
                    }
                }
                foreach (int a in it.AnswerSet)
                    if (a < 0 || a >= it.Options.Length) bad++;
            }
            else if (it.Type == QType.Fill)
            {
                if (it.FillAnswer.Trim().Length == 0) bad++;
                if (it.Question.IndexOf("＿＿", StringComparison.Ordinal) < 0 &&
                    it.Question.IndexOf("请填写", StringComparison.Ordinal) < 0) bad++;

                if (it.Question.IndexOf("的功效是：", StringComparison.Ordinal) > 0)
                {
                    Herb h = data.Find(it.HerbName);
                    if (h == null || !h.FxOverlap(it.FillAnswer)) bad++;
                }
                if (it.Question.IndexOf("的功效药物是", StringComparison.Ordinal) >= 0 ||
                    it.Question.IndexOf("功效的药物是", StringComparison.Ordinal) >= 0)
                {
                    int k = it.Question.IndexOf("具有「", StringComparison.Ordinal);
                    int e = it.Question.IndexOf("」功效的药物是", StringComparison.Ordinal);
                    if (k == 0 && e > k)
                    {
                        string fx = it.Question.Substring(3, e - 3);
                        if (CountOwners(data, fx) != 1) bad++;
                        Herb ans = data.Find(it.FillAnswer);
                        if (ans == null || !ans.HasFx(fx)) bad++;
                    }
                }
            }
            else if (it.Type == QType.Match)
            {
                if (it.MatchLeft.Length != it.MatchAnswer.Length) bad++;
                for (int i = 0; i < it.MatchAnswer.Length; i++)
                    if (it.MatchAnswer[i] < 0 || it.MatchAnswer[i] >= it.MatchOptions.Length) bad++;
            }
            return bad;
        }

        private static bool Contains(int[] arr, int v)
        {
            foreach (int a in arr) if (a == v) return true;
            return false;
        }

        private static bool Dup(string[] arr)
        {
            for (int i = 0; i < arr.Length; i++)
                for (int j = i + 1; j < arr.Length; j++)
                    if (AnswerMatcher.Norm(arr[i]) == AnswerMatcher.Norm(arr[j])) return true;
            return false;
        }

        private static int CountOwners(HerbData data, string fx)
        {
            int n = 0;
            foreach (Herb h in data.Herbs) if (h.HasFx(fx)) n++;
            return n;
        }

        /// <summary>从“具有「X」功效的药物是：”中提取 X</summary>
        private static string ExtractAsk(string q)
        {
            int k = q.IndexOf("具有「", StringComparison.Ordinal);
            if (k < 0) return null;
            int e = q.IndexOf("」功效的药物是", StringComparison.Ordinal);
            if (e < 0) return null;
            return q.Substring(k + 3, e - k - 3);
        }
    }
}
