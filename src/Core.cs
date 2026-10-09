// =====================================================================
//  中药学复习系统 —— 核心库：数据模型 / JSON 解析 / 设置存储
//  文件: Core.cs
//  说明: 兼容 C# 5 / .NET Framework 4.x（系统自带，无需安装运行时）
// =====================================================================
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using System.Windows.Forms;
using System.Drawing;

namespace TcmReview
{
    // ------------------------------------------------------------------
    //  一味中药
    // ------------------------------------------------------------------
    public class Herb
    {
        public string Name = "";
        public string Cat = "";
        public string Nature = "";     // 性味
        public string Meridian = "";   // 归经
        public List<string> Fx = new List<string>();   // 功效
        public string Usage = "";
        public string Caution = "";

        public string CatMain
        {
            get
            {
                int i = Cat.IndexOf('·');
                return i < 0 ? Cat : Cat.Substring(0, i);
            }
        }

        public string CatSub
        {
            get
            {
                int i = Cat.IndexOf('·');
                return i < 0 ? "" : Cat.Substring(i + 1);
            }
        }

        public string FxText
        {
            get { return string.Join("；", Fx.ToArray()); }
        }

        /// <summary>列表控件默认用 ToString() 显示，必须返回药名</summary>
        public override string ToString()
        {
            return Name;
        }

        public bool HasFx(string item)
        {
            foreach (string s in Fx)
                if (AnswerMatcher.Norm(s) == AnswerMatcher.Norm(item)) return true;
            return false;
        }

        // 功效项是否在“整体语义”上被本药或少数字面包含（用于避免歧义）
        public bool FxOverlap(string item)
        {
            string n = AnswerMatcher.Norm(item);
            if (n.Length == 0) return false;
            foreach (string s in Fx)
            {
                string m = AnswerMatcher.Norm(s);
                if (m.Length == 0) continue;
                if (m == n) return true;
                if (m.IndexOf(n, StringComparison.Ordinal) >= 0) return true;
                if (n.IndexOf(m, StringComparison.Ordinal) >= 0) return true;
            }
            return false;
        }

        public string FullText()
        {
            StringBuilder sb = new StringBuilder();
            sb.AppendLine("【药名】" + Name);
            sb.AppendLine("【分类】" + Cat);
            sb.AppendLine("【性味】" + Nature);
            sb.AppendLine("【归经】" + Meridian);
            sb.AppendLine("【功效】" + FxText);
            sb.AppendLine("【用法用量】" + Usage);
            sb.AppendLine("【使用注意】" + Caution);
            return sb.ToString();
        }
    }

    // ------------------------------------------------------------------
    //  题库
    // ------------------------------------------------------------------
    public class HerbData
    {
        public string Title = "中药学复习题库";
        public List<Herb> Herbs = new List<Herb>();
        public List<string> Categories = new List<string>();
        public List<string[]> Synonyms = new List<string[]>();

        private static HerbData _cur;

        public static HerbData Current
        {
            get
            {
                if (_cur == null)
                {
                    try { _cur = LoadFromString(EmbeddedData.HerbsJson()); }
                    catch (Exception ex)
                    {
                        MessageBox.Show("题库数据解析失败：" + ex.Message, "错误",
                            MessageBoxButtons.OK, MessageBoxIcon.Error);
                        _cur = new HerbData();
                    }
                }
                return _cur;
            }
        }

        public List<Herb> ByCat(string cat)
        {
            List<Herb> r = new List<Herb>();
            foreach (Herb h in Herbs)
                if (h.Cat == cat) r.Add(h);
            return r;
        }

        public List<Herb> ByCatMain(string main)
        {
            List<Herb> r = new List<Herb>();
            foreach (Herb h in Herbs)
                if (h.CatMain == main) r.Add(h);
            return r;
        }

        public Herb Find(string name)
        {
            foreach (Herb h in Herbs)
                if (h.Name == name) return h;
            return null;
        }

        // ---------- 轻量 JSON 解析（只支持本程序使用的结构） ----------
        public static HerbData LoadFromString(string json)
        {
            int pos = 0;
            object root = ParseValue(json, ref pos);
            Dictionary<string, object> top = root as Dictionary<string, object>;
            if (top == null) throw new Exception("根节点不是对象");

            HerbData data = new HerbData();
            object metaObj;
            if (top.TryGetValue("meta", out metaObj))
            {
                Dictionary<string, object> meta = metaObj as Dictionary<string, object>;
                if (meta != null)
                {
                    object t;
                    if (meta.TryGetValue("title", out t) && t != null) data.Title = t.ToString();
                    object cs;
                    if (meta.TryGetValue("categories", out cs))
                    {
                        List<object> list = cs as List<object>;
                        if (list != null)
                            foreach (object o in list) data.Categories.Add(o == null ? "" : o.ToString());
                    }
                    object sy;
                    if (meta.TryGetValue("synonyms", out sy))
                    {
                        List<object> list = sy as List<object>;
                        if (list != null)
                        {
                            foreach (object g in list)
                            {
                                List<object> grp = g as List<object>;
                                if (grp == null) continue;
                                List<string> one = new List<string>();
                                foreach (object w in grp) one.Add(w == null ? "" : w.ToString());
                                if (one.Count > 0) data.Synonyms.Add(one.ToArray());
                            }
                        }
                    }
                }
            }

            object hs;
            if (top.TryGetValue("herbs", out hs))
            {
                List<object> arr = hs as List<object>;
                if (arr != null)
                {
                    foreach (object o in arr)
                    {
                        Dictionary<string, object> d = o as Dictionary<string, object>;
                        if (d == null) continue;
                        Herb h = new Herb();
                        h.Name = Str(d, "name");
                        h.Cat = Str(d, "cat");
                        h.Nature = Str(d, "nature");
                        h.Meridian = Str(d, "meridian");
                        h.Usage = Str(d, "usage");
                        h.Caution = Str(d, "caution");
                        object fx;
                        if (d.TryGetValue("fx", out fx))
                        {
                            List<object> fl = fx as List<object>;
                            if (fl != null)
                                foreach (object f in fl) h.Fx.Add(f == null ? "" : f.ToString());
                        }
                        if (h.Name.Length > 0) data.Herbs.Add(h);
                    }
                }
            }
            AnswerMatcher.LoadSynonyms(data.Synonyms);
            return data;
        }

        private static string Str(Dictionary<string, object> d, string key)
        {
            object v;
            if (d.TryGetValue(key, out v) && v != null) return v.ToString();
            return "";
        }

        private static object ParseValue(string s, ref int i)
        {
            SkipWs(s, ref i);
            if (i >= s.Length) throw new Exception("JSON 意外结束");
            char c = s[i];
            if (c == '{') return ParseObject(s, ref i);
            if (c == '[') return ParseArray(s, ref i);
            if (c == '"') return ParseString(s, ref i);
            return ParseLiteral(s, ref i);
        }

        private static Dictionary<string, object> ParseObject(string s, ref int i)
        {
            Dictionary<string, object> d = new Dictionary<string, object>();
            i++; // {
            SkipWs(s, ref i);
            if (i < s.Length && s[i] == '}') { i++; return d; }
            while (true)
            {
                SkipWs(s, ref i);
                string key = ParseString(s, ref i);
                SkipWs(s, ref i);
                if (i >= s.Length || s[i] != ':') throw new Exception("JSON 缺少冒号");
                i++;
                object v = ParseValue(s, ref i);
                d[key] = v;
                SkipWs(s, ref i);
                if (i >= s.Length) throw new Exception("JSON 对象未闭合");
                if (s[i] == ',') { i++; continue; }
                if (s[i] == '}') { i++; return d; }
                throw new Exception("JSON 对象语法错误");
            }
        }

        private static List<object> ParseArray(string s, ref int i)
        {
            List<object> list = new List<object>();
            i++; // [
            SkipWs(s, ref i);
            if (i < s.Length && s[i] == ']') { i++; return list; }
            while (true)
            {
                list.Add(ParseValue(s, ref i));
                SkipWs(s, ref i);
                if (i >= s.Length) throw new Exception("JSON 数组未闭合");
                if (s[i] == ',') { i++; continue; }
                if (s[i] == ']') { i++; return list; }
                throw new Exception("JSON 数组语法错误");
            }
        }

        private static string ParseString(string s, ref int i)
        {
            SkipWs(s, ref i);
            if (i >= s.Length || s[i] != '"') throw new Exception("JSON 期望字符串");
            i++;
            StringBuilder sb = new StringBuilder();
            while (i < s.Length)
            {
                char c = s[i++];
                if (c == '"') return sb.ToString();
                if (c != '\\') { sb.Append(c); continue; }
                if (i >= s.Length) break;
                char e = s[i++];
                switch (e)
                {
                    case '"': sb.Append('"'); break;
                    case '\\': sb.Append('\\'); break;
                    case '/': sb.Append('/'); break;
                    case 'b': sb.Append('\b'); break;
                    case 'f': sb.Append('\f'); break;
                    case 'n': sb.Append('\n'); break;
                    case 'r': sb.Append('\r'); break;
                    case 't': sb.Append('\t'); break;
                    case 'u':
                        if (i + 4 <= s.Length)
                        {
                            string hex = s.Substring(i, 4);
                            i += 4;
                            int code = int.Parse(hex, NumberStyles.HexNumber, CultureInfo.InvariantCulture);
                            sb.Append((char)code);
                        }
                        break;
                    default: sb.Append(e); break;
                }
            }
            throw new Exception("JSON 字符串未闭合");
        }

        private static object ParseLiteral(string s, ref int i)
        {
            if (string.Compare(s, i, "null", 0, 4, StringComparison.Ordinal) == 0) { i += 4; return null; }
            if (string.Compare(s, i, "true", 0, 4, StringComparison.Ordinal) == 0) { i += 4; return true; }
            if (string.Compare(s, i, "false", 0, 5, StringComparison.Ordinal) == 0) { i += 5; return false; }
            int start = i;
            while (i < s.Length && "-+.eE0123456789".IndexOf(s[i]) >= 0) i++;
            if (i == start) throw new Exception("JSON 无法识别的记号");
            return s.Substring(start, i - start);
        }

        private static void SkipWs(string s, ref int i)
        {
            while (i < s.Length)
            {
                char c = s[i];
                if (c == ' ' || c == '\t' || c == '\r' || c == '\n') { i++; continue; }
                break;
            }
        }
    }

    // ------------------------------------------------------------------
    //  答案模糊匹配（填空题判分）
    // ------------------------------------------------------------------
    public static class AnswerMatcher
    {
        private static List<string[]> _groups = new List<string[]>();
        private static readonly char[] Noise = new char[] {
            '能','可','有','善','主','且','以','之','其','为','者','也','的','和','与','及','或',
            '、','，',',','。','；',';','：',':',' ','　','（','）','(',')','“','”','"','\'','！','!','？','?',
            '·','-','—','～','~','/','\\','＋','+'
        };

        public static void LoadSynonyms(List<string[]> groups)
        {
            if (groups != null && groups.Count > 0) _groups = groups;
        }

        public static string Norm(string s)
        {
            if (string.IsNullOrEmpty(s)) return "";
            StringBuilder sb = new StringBuilder();
            foreach (char c in s)
            {
                bool skip = false;
                for (int i = 0; i < Noise.Length; i++)
                    if (Noise[i] == c) { skip = true; break; }
                if (!skip) sb.Append(c);
            }
            return sb.ToString().Trim();
        }

        /// <summary>返回 0~1 的相似度，1 表示完全正确</summary>
        public static double Similarity(string user, string answer)
        {
            string a = Norm(user);
            string b = Norm(answer);
            if (a.Length == 0 || b.Length == 0) return 0.0;

            if (a == b) return 1.0;

            // 同义词组
            foreach (string[] g in _groups)
            {
                bool ia = false, ib = false;
                foreach (string w in g)
                {
                    string nw = Norm(w);
                    if (nw.Length == 0) continue;
                    if (nw == a) ia = true;
                    if (nw == b) ib = true;
                }
                if (ia && ib) return 1.0;
            }

            // 互为包含
            if (a.IndexOf(b, StringComparison.Ordinal) >= 0)
                return b.Length >= 2 ? 0.95 : 0.7;
            if (b.IndexOf(a, StringComparison.Ordinal) >= 0)
                return a.Length >= 2 ? 0.9 : 0.65;

            // 编辑距离
            int d = Distance(a, b);
            int max = Math.Max(a.Length, b.Length);
            double sim = 1.0 - (double)d / max;
            // 允许 4 字以上答案错 1 个字
            if (max >= 4 && d <= 1) sim = Math.Max(sim, 0.85);
            return sim < 0 ? 0 : sim;
        }

        public static bool IsCorrect(string user, string answer)
        {
            return Similarity(user, answer) >= 0.75;
        }

        public static int Distance(string a, string b)
        {
            int n = a.Length, m = b.Length;
            if (n == 0) return m;
            if (m == 0) return n;
            int[] prev = new int[m + 1];
            int[] cur = new int[m + 1];
            for (int j = 0; j <= m; j++) prev[j] = j;
            for (int i = 1; i <= n; i++)
            {
                cur[0] = i;
                for (int j = 1; j <= m; j++)
                {
                    int cost = (a[i - 1] == b[j - 1]) ? 0 : 1;
                    int v = prev[j - 1] + cost;
                    if (prev[j] + 1 < v) v = prev[j] + 1;
                    if (cur[j - 1] + 1 < v) v = cur[j - 1] + 1;
                    cur[j] = v;
                }
                int[] t = prev; prev = cur; cur = t;
            }
            return prev[m];
        }
    }

    // ------------------------------------------------------------------
    //  设置 / 记录 存储（文本格式，UTF-8 无 BOM）
    // ------------------------------------------------------------------
    public class AppConfig
    {
        // 固定 100 分制：单选 3 分、多选 5 分、填空 3 分、判断 2 分
        // 默认题量：10×3 + 4×5 + 10×3 + 10×2 = 30+20+30+20 = 100 分
        public int N1 = 10;            // 单选题数
        public int N2 = 4;             // 多选题数
        public int N3 = 10;            // 判断题数
        public int N4 = 10;            // 填空题数
        public int P1 = 3;
        public int P2 = 5;
        public int P3 = 2;
        public int P4 = 3;
        public int Minutes = 30;       // 限时（分钟），0 表示不限时
        public bool Immediate = false; // 即时反馈
        public bool Shuffle = true;    // 选项乱序
        public int Seed = 0;           // 0 表示随机
        public List<string> Cats = new List<string>();
        public int WrongCount = 0;

        public int Total()
        {
            return N1 * P1 + N2 * P2 + N3 * P3 + N4 * P4;
        }

        public int QuestionTotal()
        {
            return N1 + N2 + N3 + N4;
        }

        public static AppConfig Load()
        {
            AppConfig c = new AppConfig();
            string f = Store.ConfigPath;
            if (!File.Exists(f)) return c;
            bool loaded = false;
            try
            {
                foreach (string line in File.ReadAllLines(f, Encoding.UTF8))
                {
                    int k = line.IndexOf('=');
                    if (k <= 0) continue;
                    string key = line.Substring(0, k).Trim();
                    string val = line.Substring(k + 1).Trim();
                    loaded = true;
                    switch (key)
                    {
                        case "N1": c.N1 = Int(val, c.N1); break;
                        case "N2": c.N2 = Int(val, c.N2); break;
                        case "N3": c.N3 = Int(val, c.N3); break;
                        case "N4": c.N4 = Int(val, c.N4); break;
                        case "P1": c.P1 = Int(val, c.P1); break;
                        case "P2": c.P2 = Int(val, c.P2); break;
                        case "P3": c.P3 = Int(val, c.P3); break;
                        case "P4": c.P4 = Int(val, c.P4); break;
                        case "Minutes": c.Minutes = Int(val, c.Minutes); break;
                        case "Immediate": c.Immediate = val == "1"; break;
                        case "Shuffle": c.Shuffle = val != "0"; break;
                        case "Seed": c.Seed = Int(val, c.Seed); break;
                        case "WrongCount": c.WrongCount = Int(val, c.WrongCount); break;
                        case "Cats":
                            c.Cats.Clear();
                            if (val.Length > 0)
                                foreach (string s in val.Split('|'))
                                    if (s.Trim().Length > 0) c.Cats.Add(s.Trim());
                            break;
                    }
                }
            }
            catch { }

            // 分值已锁定为 100 分制；旧版本配置若分值不符，直接回到默认题量
            if (loaded)
            {
                c.P1 = 3; c.P2 = 5; c.P3 = 2; c.P4 = 3;
                if (c.N1 * 3 + c.N2 * 5 + c.N3 * 2 + c.N4 * 3 != 100)
                {
                    c.N1 = 10; c.N2 = 4; c.N3 = 10; c.N4 = 10;
                }
            }
            if (c.Minutes < 0 || c.Minutes > 300) c.Minutes = 30;
            return c;
        }

        public void Save()
        {
            try
            {
                Store.EnsureDir();
                StringBuilder sb = new StringBuilder();
                sb.AppendLine("N1=" + N1);
                sb.AppendLine("N2=" + N2);
                sb.AppendLine("N3=" + N3);
                sb.AppendLine("N4=" + N4);
                sb.AppendLine("P1=" + P1);
                sb.AppendLine("P2=" + P2);
                sb.AppendLine("P3=" + P3);
                sb.AppendLine("P4=" + P4);
                sb.AppendLine("Minutes=" + Minutes);
                sb.AppendLine("Immediate=" + (Immediate ? "1" : "0"));
                sb.AppendLine("Shuffle=" + (Shuffle ? "1" : "0"));
                sb.AppendLine("Seed=" + Seed);
                sb.AppendLine("WrongCount=" + WrongCount);
                sb.AppendLine("Cats=" + string.Join("|", Cats.ToArray()));
                Store.WriteText(Store.ConfigPath, sb.ToString());
            }
            catch { }
        }

        private static int Int(string s, int def)
        {
            int v;
            if (int.TryParse(s, out v)) return v;
            return def;
        }

        public AppConfig Clone()
        {
            AppConfig c = new AppConfig();
            c.N1 = N1; c.N2 = N2; c.N3 = N3; c.N4 = N4;
            c.P1 = P1; c.P2 = P2; c.P3 = P3; c.P4 = P4;
            c.Minutes = Minutes; c.Immediate = Immediate;
            c.Shuffle = Shuffle; c.Seed = Seed;
            c.Cats = new List<string>(Cats);
            c.WrongCount = WrongCount;
            return c;
        }
    }

    public class Record
    {
        public string Time = "";
        public string Mode = "";
        public int Score = 0;
        public int Total = 100;
        public int Correct = 0;
        public int Count = 0;
        public int Seconds = 0;
        public int Wrong = 0;

        public string Line()
        {
            return string.Join("|", new string[] {
                Time, Mode.Replace("|", "/"), Score.ToString(), Total.ToString(),
                Correct.ToString(), Count.ToString(), Seconds.ToString(), Wrong.ToString() });
        }

        public static Record Parse(string line)
        {
            string[] p = line.Split('|');
            if (p.Length < 8) return null;
            Record r = new Record();
            r.Time = p[0]; r.Mode = p[1];
            r.Score = I(p[2]); r.Total = I(p[3]);
            r.Correct = I(p[4]); r.Count = I(p[5]);
            r.Seconds = I(p[6]); r.Wrong = I(p[7]);
            return r;
        }

        private static int I(string s)
        {
            int v; int.TryParse(s, out v); return v;
        }

        public double Accuracy
        {
            get { return Count == 0 ? 0 : (double)Correct * 100.0 / Count; }
        }
    }

    public static class Store
    {
        public static string Dir
        {
            get
            {
                string d = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                    "TcmReview");
                return d;
            }
        }

        public static string ConfigPath { get { return Path.Combine(Dir, "config.txt"); } }
        public static string HistoryPath { get { return Path.Combine(Dir, "history.txt"); } }
        public static string WrongPath { get { return Path.Combine(Dir, "wrong.txt"); } }
        public static string HiddenPath { get { return Path.Combine(Dir, "hidden.txt"); } }

        /// <summary>被用户删除（不再显示）的图片名单，格式 药名|序号</summary>
        public static List<string> LoadHidden()
        {
            List<string> list = new List<string>();
            try
            {
                if (!File.Exists(HiddenPath)) return list;
                foreach (string line in File.ReadAllLines(HiddenPath, Encoding.UTF8))
                {
                    string t = line.Trim();
                    if (t.Length > 0 && !t.StartsWith("#")) list.Add(t);
                }
            }
            catch { }
            return list;
        }

        public static void AddHidden(string herbName, int index)
        {
            try
            {
                List<string> list = LoadHidden();
                string key = herbName + "|" + index;
                if (!list.Contains(key)) list.Add(key);
                StringBuilder sb = new StringBuilder();
                sb.AppendLine("# 用户删除的图片（药名|图片序号），程序不再显示这些图片");
                foreach (string k in list) sb.AppendLine(k);
                WriteText(HiddenPath, sb.ToString());
            }
            catch { }
        }

        public static void ClearHidden()
        {
            try { if (File.Exists(HiddenPath)) File.Delete(HiddenPath); }
            catch { }
        }

        public static void EnsureDir()
        {
            if (!Directory.Exists(Dir)) Directory.CreateDirectory(Dir);
        }

        public static void WriteText(string path, string text)
        {
            EnsureDir();
            File.WriteAllText(path, text, new UTF8Encoding(false));
        }

        public static List<Record> LoadHistory()
        {
            List<Record> list = new List<Record>();
            try
            {
                if (!File.Exists(HistoryPath)) return list;
                foreach (string line in File.ReadAllLines(HistoryPath, Encoding.UTF8))
                {
                    if (line.Trim().Length == 0) continue;
                    if (line.StartsWith("#")) continue;
                    Record r = Record.Parse(line);
                    if (r != null) list.Add(r);
                }
            }
            catch { }
            return list;
        }

        public static void AppendHistory(Record r)
        {
            try
            {
                EnsureDir();
                File.AppendAllText(HistoryPath, r.Line() + Environment.NewLine, new UTF8Encoding(false));
            }
            catch { }
        }

        public static void ClearHistory()
        {
            try { if (File.Exists(HistoryPath)) File.Delete(HistoryPath); }
            catch { }
        }

        // ---------- 错题本 ----------
        public static Dictionary<string, int> LoadWrong()
        {
            Dictionary<string, int> d = new Dictionary<string, int>();
            try
            {
                if (!File.Exists(WrongPath)) return d;
                foreach (string line in File.ReadAllLines(WrongPath, Encoding.UTF8))
                {
                    int i = line.LastIndexOf('|');
                    if (i <= 0) continue;
                    string name = line.Substring(0, i);
                    int c;
                    if (int.TryParse(line.Substring(i + 1), out c) && name.Length > 0) d[name] = c;
                }
            }
            catch { }
            return d;
        }

        public static void AddWrong(IEnumerable<string> names)
        {
            try
            {
                Dictionary<string, int> d = LoadWrong();
                foreach (string n in names)
                {
                    if (string.IsNullOrEmpty(n)) continue;
                    if (d.ContainsKey(n)) d[n] = d[n] + 1;
                    else d[n] = 1;
                }
                SaveWrong(d);
            }
            catch { }
        }

        public static void RemoveWrong(IEnumerable<string> names)
        {
            try
            {
                Dictionary<string, int> d = LoadWrong();
                foreach (string n in names) if (d.ContainsKey(n)) d.Remove(n);
                SaveWrong(d);
            }
            catch { }
        }

        public static void ClearWrong()
        {
            try { if (File.Exists(WrongPath)) File.Delete(WrongPath); }
            catch { }
        }

        private static void SaveWrong(Dictionary<string, int> d)
        {
            List<string> keys = new List<string>(d.Keys);
            keys.Sort(StringComparer.Ordinal);
            StringBuilder sb = new StringBuilder();
            foreach (string k in keys) sb.AppendLine(k + "|" + d[k]);
            WriteText(WrongPath, sb.ToString());
        }
    }

    // ------------------------------------------------------------------
    //  界面配色 / 控件工厂
    // ------------------------------------------------------------------
    public static class Ui
    {
        public static string FontName = "Microsoft YaHei UI";
        public static readonly Color Bg = Color.FromArgb(246, 247, 249);
        public static readonly Color Card = Color.White;
        public static readonly Color Brand = Color.FromArgb(31, 111, 84);      // 药绿
        public static readonly Color BrandLight = Color.FromArgb(232, 244, 238);
        public static readonly Color Accent = Color.FromArgb(193, 105, 62);    // 赭石
        public static readonly Color Text = Color.FromArgb(38, 44, 42);
        public static readonly Color Sub = Color.FromArgb(110, 120, 116);
        public static readonly Color Line = Color.FromArgb(216, 221, 218);
        public static readonly Color Ok = Color.FromArgb(35, 130, 78);
        public static readonly Color Bad = Color.FromArgb(196, 62, 54);
        public static readonly Color Warn = Color.FromArgb(206, 138, 34);

        public static Font F(float size)
        {
            return new Font(FontName, size, FontStyle.Regular, GraphicsUnit.Point);
        }

        public static Font FB(float size)
        {
            return new Font(FontName, size, FontStyle.Bold, GraphicsUnit.Point);
        }

        public static Label Lbl(string text, float size, Color color, bool bold)
        {
            Label l = new Label();
            l.Text = text;
            l.Font = bold ? FB(size) : F(size);
            l.ForeColor = color;
            l.AutoSize = true;
            l.BackColor = Color.Transparent;
            l.Margin = new Padding(0, 0, 0, 6);
            return l;
        }

        public static Button Btn(string text, int w, int h, Color back, Color fore, float size)
        {
            Button b = new Button();
            b.Text = text;
            b.Width = w;
            b.Height = h;
            b.FlatStyle = FlatStyle.Flat;
            b.FlatAppearance.BorderSize = 1;
            b.FlatAppearance.BorderColor = back;
            b.BackColor = back;
            b.ForeColor = fore;
            b.Font = FB(size);
            b.Cursor = Cursors.Hand;
            b.UseVisualStyleBackColor = false;
            return b;
        }

        public static Panel Card2(int pad)
        {
            Panel p = new Panel();
            p.BackColor = Card;
            p.Padding = new Padding(pad);
            p.Margin = new Padding(0, 0, 0, 14);
            return p;
        }

        public static void Round(Control c, int radius)
        {
            // 简易圆角（保留系统绘制，只处理背景）
            c.Paint += delegate(object s, PaintEventArgs e)
            {
                using (Pen pen = new Pen(Line, 1))
                {
                    e.Graphics.DrawRectangle(pen, 0, 0, c.Width - 1, c.Height - 1);
                }
            };
        }

        /// <summary>给控件开启双缓冲（ListBox / RichTextBox 等默认不开启，滚动时会闪）</summary>
        public static void SetDoubleBuffered(Control c)
        {
            if (c == null) return;
            try
            {
                System.Reflection.PropertyInfo pi = typeof(Control).GetProperty(
                    "DoubleBuffered",
                    System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic);
                if (pi != null) pi.SetValue(c, true, null);
            }
            catch { }
        }

        /// <summary>生成计时器样式的小标签</summary>
        public static Label Chip(string text, float size, Color fore, Color back)
        {
            Label l = new Label();
            l.Text = text;
            l.Font = FB(size);
            l.ForeColor = fore;
            l.BackColor = back;
            l.AutoSize = false;
            l.TextAlign = ContentAlignment.MiddleCenter;
            l.Margin = new Padding(0);
            return l;
        }
    }

    // ------------------------------------------------------------------
    //  内嵌中药图片包（由 gen_images.py 生成的数据包）
    //  包格式：magic(8) + version(4) + count(4) + [路径长(4)+路径+偏移(4)+长度(4)]*count + 数据
    // ------------------------------------------------------------------
    public static class ImgBundle
    {
        private static Dictionary<string, byte[]> _map;
        private static bool _loaded;

        private static void Ensure()
        {
            if (_loaded) return;
            _loaded = true;
            _map = new Dictionary<string, byte[]>(StringComparer.Ordinal);
            try
            {
                // 优先读取编译进 exe 的资源 images.res 中的 TCMIMG 汇总包
                byte[] all = null;
                try
                {
                    System.Reflection.Assembly asm = typeof(ImgBundle).Assembly;
                    foreach (string rn in asm.GetManifestResourceNames())
                    {
                        if (!rn.EndsWith("images.res", StringComparison.OrdinalIgnoreCase)) continue;
                        using (Stream s = asm.GetManifestResourceStream(rn))
                        {
                            if (s == null) continue;
                            using (System.Resources.ResourceReader rr =
                                new System.Resources.ResourceReader(s))
                            {
                                System.Collections.IDictionaryEnumerator e = rr.GetEnumerator();
                                while (e.MoveNext())
                                {
                                    string key = e.Key as string;
                                    if (key == "TCMIMG") { all = e.Value as byte[]; break; }
                                }
                            }
                        }
                        if (all != null) break;
                    }
                }
                catch { }

                // 兼容：没有资源文件时回退到源码内嵌的 base64 包（图片很少时才可用）
                if (all == null)
                {
                    string b64 = EmbeddedImages.Data();
                    if (!string.IsNullOrEmpty(b64)) all = Convert.FromBase64String(b64);
                }
                if (all == null || all.Length < 16) return;

                int pos = 0;
                string magic = Encoding.ASCII.GetString(all, 0, 8);
                pos += 8;
                if (magic != "TCMIMGV1") return;
                int version = BitConverter.ToInt32(all, pos); pos += 4;
                int count = BitConverter.ToInt32(all, pos); pos += 4;
                int dataStart = 16;      // 先算出头部长度，数据区在头部之后
                for (int i = 0; i < count; i++)
                {
                    int nlen0 = BitConverter.ToInt32(all, dataStart); dataStart += 4;
                    dataStart += nlen0 + 8;
                }
                for (int i = 0; i < count; i++)
                {
                    int nlen = BitConverter.ToInt32(all, pos); pos += 4;
                    string p = Encoding.UTF8.GetString(all, pos, nlen); pos += nlen;
                    int off = BitConverter.ToInt32(all, pos); pos += 4;
                    int len = BitConverter.ToInt32(all, pos); pos += 4;
                    int start = dataStart + off;   // 偏移量相对数据区起点
                    if (off < 0 || len <= 0 || start + len > all.Length) continue;
                    byte[] buf = new byte[len];
                    Buffer.BlockCopy(all, start, buf, 0, len);
                    _map[p] = buf;
                }
            }
            catch { }
        }

        public static bool HasAny
        {
            get { Ensure(); return _map != null && _map.Count > 0; }
        }

        public static int Count
        {
            get { Ensure(); return _map == null ? 0 : _map.Count; }
        }

        /// <summary>取某味药可见图片的文件键（按序号排序，跳过用户删除的）</summary>
        public static List<string> GetKeys(string herbName)
        {
            Ensure();
            List<string> res = new List<string>();
            if (_map == null || _map.Count == 0) return res;
            List<string> hidden = Store.LoadHidden();
            List<string> keys = new List<string>();
            foreach (string k in _map.Keys)
                if (k.StartsWith(herbName + "_", StringComparison.Ordinal)) keys.Add(k);
            keys.Sort(StringComparer.Ordinal);
            int shown = 0;
            foreach (string k in keys)
            {
                shown++;
                string key = herbName + "|" + shown;
                bool del = false;
                foreach (string h in hidden) if (h == key) { del = true; break; }
                if (del) continue;
                res.Add(k);
            }
            return res;
        }

        /// <summary>取某味药的图片字节（按文件名序号排序，跳过用户删除的）</summary>
        public static List<byte[]> GetImages(string herbName)
        {
            Ensure();
            List<byte[]> res = new List<byte[]>();
            List<string> keys = GetKeys(herbName);
            foreach (string k in keys)
            {
                byte[] b;
                if (_map != null && _map.TryGetValue(k, out b)) res.Add(b);
            }
            return res;
        }
    }

    // ------------------------------------------------------------------
    //  主窗体基类：统一字体与配色
    // ------------------------------------------------------------------
    public class BaseForm : Form
    {
        public BaseForm()
        {
            this.Font = Ui.F(11f);
            this.BackColor = Ui.Bg;
            this.ForeColor = Ui.Text;
            this.StartPosition = FormStartPosition.CenterScreen;
            this.DoubleBuffered = true;
        }

        protected override void OnShown(EventArgs e)
        {
            base.OnShown(e);
            CenterToScreen();
        }
    }

    // ------------------------------------------------------------------
    //  版本检查（桌面版）：读取你部署的 version.json，提示是否有新版本
    // ------------------------------------------------------------------
    public static class UpdateChecker
    {
        public const string CurrentVersion = "1.1.0";

        /// <summary>可在此写死你的更新地址（版本文件），留空则用命令行 --update-url 指定</summary>
        public static string Url = "";

        public static string LastMessage = "";

        /// <summary>后台检查更新，返回提示文本（无更新返回空串）</summary>
        public static string Check()
        {
            string url = Url;
            if (string.IsNullOrEmpty(url)) return "";
            try
            {
                System.Net.WebClient wc = new System.Net.WebClient();
                wc.Encoding = Encoding.UTF8;
                wc.Headers.Add("User-Agent", "TcmReview/" + CurrentVersion);
                string json = wc.DownloadString(url);
                string remote = Pick(json, "version");
                string notes = Pick(json, "notes");
                if (string.IsNullOrEmpty(remote)) return "";
                if (remote != CurrentVersion)
                    return "发现新版本 " + remote + "（当前 " + CurrentVersion + "）\n" +
                           (notes.Length > 0 ? notes : "") + "\n下载：" +
                           Pick(json, "homepage");
                return "";
            }
            catch
            {
                return "";
            }
        }

        /// <summary>从简单 JSON 中取字符串字段</summary>
        private static string Pick(string json, string key)
        {
            try
            {
                int i = json.IndexOf("\"" + key + "\"", StringComparison.Ordinal);
                if (i < 0) return "";
                i = json.IndexOf(':', i);
                if (i < 0) return "";
                i++;
                while (i < json.Length && (json[i] == ' ' || json[i] == '\t')) i++;
                if (i >= json.Length || json[i] != '"') return "";
                i++;
                StringBuilder sb = new StringBuilder();
                while (i < json.Length)
                {
                    char c = json[i];
                    if (c == '\\' && i + 1 < json.Length) { sb.Append(json[i + 1]); i += 2; continue; }
                    if (c == '"') break;
                    sb.Append(c);
                    i++;
                }
                return sb.ToString();
            }
            catch { return ""; }
        }
    }
}
