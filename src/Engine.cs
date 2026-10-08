// =====================================================================
//  中药学复习系统 —— 出题引擎 / 判分
//  文件: Engine.cs
// =====================================================================
using System;
using System.Collections.Generic;
using System.Text;

namespace TcmReview
{
    public enum QType { Single = 1, Multi = 2, Judge = 3, Fill = 4, Match = 5 }

    public static class QTypeName
    {
        public static string Of(QType t)
        {
            switch (t)
            {
                case QType.Single: return "单项选择题";
                case QType.Multi: return "多项选择题";
                case QType.Judge: return "判断题";
                case QType.Fill: return "填空题";
                case QType.Match: return "配对题";
            }
            return "题目";
        }
    }

    // ------------------------------------------------------------------
    //  一道题
    // ------------------------------------------------------------------
    public class QItem
    {
        public QType Type;
        public string HerbName = "";
        public string Question = "";
        public string[] Options = new string[0];
        public int AnswerIndex = -1;
        public int[] AnswerSet = new int[0];
        public List<int> Pick = new List<int>();
        public string FillAnswer = "";
        public string FillInput = "";
        public int[] MatchAnswer = new int[0];      // 每题正确答案（对应 Left 的顺序）
        public string[] MatchLeft = new string[0];
        public string[] MatchOptions = new string[0];
        public int[] MatchPick = new int[0];
        public string Reference = "";
        public string Tip = "";

        public int Points = 1;
        public int Order = 0;
        public int Seconds = 0;          // 本题用时
        public bool Answered = false;
        public bool Graded = false;
        public double Score = 0;

        public string TypeName { get { return QTypeName.Of(Type); } }

        public void ClearAnswer()
        {
            Answered = false; Graded = false; Score = 0;
            Pick.Clear();
            FillInput = "";
            if (MatchPick != null && MatchPick.Length > 0)
                for (int i = 0; i < MatchPick.Length; i++) MatchPick[i] = -1;
        }
    }

    // ------------------------------------------------------------------
    //  出题引擎
    // ------------------------------------------------------------------
    public class QuizEngine
    {
        private HerbData _data;
        private Random _rnd;
        private AppConfig _cfg;
        private List<Herb> _pool;
        private Dictionary<string, List<Herb>> _fxIndex = new Dictionary<string, List<Herb>>();
        private HashSet<string> _usedStems = new HashSet<string>(StringComparer.Ordinal);

        /// <summary>重新限定抽题范围（错题强化模式用）</summary>
        public void SetPool(List<Herb> herbs)
        {
            if (herbs != null && herbs.Count > 0) _pool = herbs;
        }

        public QuizEngine(HerbData data, AppConfig cfg)
        {
            _data = data;
            _cfg = cfg;
            _rnd = new Random(cfg.Seed != 0 ? cfg.Seed : Environment.TickCount);
            _pool = BuildPool();
            foreach (Herb h in _data.Herbs)
            {
                foreach (string f in h.Fx)
                {
                    string k = AnswerMatcher.Norm(f);
                    if (k.Length == 0) continue;
                    List<Herb> l;
                    if (!_fxIndex.TryGetValue(k, out l))
                    {
                        l = new List<Herb>();
                        _fxIndex[k] = l;
                    }
                    if (!l.Contains(h)) l.Add(h);
                }
            }
        }

        private List<Herb> BuildPool()
        {
            List<Herb> pool = new List<Herb>();
            if (_cfg.Cats != null && _cfg.Cats.Count > 0)
            {
                foreach (Herb h in _data.Herbs)
                    if (_cfg.Cats.Contains(h.Cat)) pool.Add(h);
            }
            if (pool.Count == 0) pool = new List<Herb>(_data.Herbs);
            return pool;
        }

        public int PoolCount { get { return _pool.Count; } }

        // ---------------- 工具 ----------------
        /// <summary>归经表述：数据里已含“经”字，避免出现“归脾、胃经经”</summary>
        public static string Merid(Herb h)
        {
            string m = h.Meridian;
            if (m.Length == 0) return m;
            if (m.EndsWith("经", StringComparison.Ordinal)) return m;
            return m + "经";
        }

        private T PickOne<T>(List<T> list)
        {
            return list[_rnd.Next(list.Count)];
        }

        public static void Shuffle<T>(List<T> list, Random rnd)
        {
            for (int i = list.Count - 1; i > 0; i--)
            {
                int j = rnd.Next(i + 1);
                T t = list[i]; list[i] = list[j]; list[j] = t;
            }
        }

        private bool HasFx(Herb h, string item)
        {
            return h.HasFx(item);
        }

        /// <summary>某功效在全库中由多少味药（严格字面）拥有</summary>
        private int FxHerbCount(string item)
        {
            List<Herb> l;
            if (_fxIndex.TryGetValue(AnswerMatcher.Norm(item), out l)) return l.Count;
            return 0;
        }

        /// <summary>该功效是否会被其他药“部分包含”从而产生歧义</summary>
        private bool FxAmbiguous(string item)
        {
            string n = AnswerMatcher.Norm(item);
            if (n.Length < 2) return true;
            foreach (Herb h in _pool)
            {
                if (h.FxOverlap(item)) continue;
                foreach (string f in h.Fx)
                {
                    string m = AnswerMatcher.Norm(f);
                    if (m.Length == 0) continue;
                    // 只有一边包含另一边时才可能产生歧义
                    if (m.IndexOf(n, StringComparison.Ordinal) >= 0) return true;
                    if (n.IndexOf(m, StringComparison.Ordinal) >= 0) return true;
                }
            }
            return false;
        }

        private bool SameFxSet(Herb a, Herb b)
        {
            if (a.Fx.Count != b.Fx.Count) return false;
            foreach (string f in a.Fx) if (!b.HasFx(f)) return false;
            return true;
        }

        /// <summary>与 h 功效完全相同的药（出干扰项时必须排除）</summary>
        private List<Herb> Twins(Herb h)
        {
            List<Herb> r = new List<Herb>();
            foreach (Herb o in _pool)
                if (o != h && SameFxSet(h, o)) r.Add(o);
            return r;
        }

        // ---------------- 总入口 ----------------
        public List<QItem> BuildQuiz(AppConfig cfg)
        {
            List<QItem> items = new List<QItem>();
            AddType(items, QType.Single, cfg.N1, cfg.P1);
            AddType(items, QType.Multi, cfg.N2, cfg.P2);
            AddType(items, QType.Judge, cfg.N3, cfg.P3);
            AddType(items, QType.Fill, cfg.N4, cfg.P4);
            Shuffle(items, _rnd);
            for (int i = 0; i < items.Count; i++) items[i].Order = i + 1;
            return items;
        }

        private void AddType(List<QItem> items, QType type, int count, int points)
        {
            if (count <= 0) return;
            List<QItem> made = new List<QItem>();
            int guard = 0;
            int failStreak = 0;
            while (made.Count < count && guard < count * 80 + 900 && failStreak < 500)
            {
                guard++;
                QItem it = null;
                switch (type)
                {
                    case QType.Single: it = MakeSingle(); break;
                    case QType.Multi: it = MakeMulti(); break;
                    case QType.Judge: it = MakeJudge(); break;
                    case QType.Fill: it = MakeFill(); break;
                    case QType.Match: it = MakeMatch(); break;
                }
                if (it == null) { failStreak++; continue; }

                // 同一套试卷内不出重复题干
                string stem = QTypeName.Of(type) + "|" + it.Question;
                if (_usedStems.Contains(stem)) { failStreak++; continue; }
                _usedStems.Add(stem);
                failStreak = 0;

                it.Type = type;
                it.Points = points;
                made.Add(it);
            }
            items.AddRange(made);
        }

        // ---------------- 单项选择题 ----------------
        private QItem MakeSingle()
        {
            int style = _rnd.Next(4);
            if (style == 0) return MakeSingleByFunction();
            if (style == 1) return MakeSingleByHerb();
            if (style == 2) return MakeSingleNotFx();
            return MakeSingleByNature();
        }

        /// <summary>题干给出功效，选择对应药物</summary>
        private QItem MakeSingleByFunction()
        {
            for (int attempt = 0; attempt < 40; attempt++)
            {
                Herb h = PickOne(_pool);
                if (h.Fx.Count == 0) continue;
                string fx = PickOne(h.Fx);
                int owners = FxHerbCount(fx);
                if (owners != 1 || FxAmbiguous(fx)) continue;

                List<Herb> decoys = DecoyHerbs(h, fx, 3);
                if (decoys.Count < 3) continue;

                List<string> names = new List<string>();
                names.Add(h.Name);
                foreach (Herb d in decoys) names.Add(d.Name);
                Shuffle(names, _rnd);

                QItem it = new QItem();
                it.HerbName = h.Name;
                it.Question = "具有「" + fx + "」功效的药物是：";
                it.Options = names.ToArray();
                it.AnswerIndex = names.IndexOf(h.Name);
                it.Reference = h.Name + "：" + h.FxText + "。性味" + h.Nature + "，归" + h.Meridian + "。";
                it.Tip = h.Cat;
                return it;
            }
            return null;
        }

        /// <summary>题干给出药物，选择其功效</summary>
        private QItem MakeSingleByHerb()
        {
            for (int attempt = 0; attempt < 40; attempt++)
            {
                Herb h = PickOne(_pool);
                if (h.Fx.Count == 0) continue;
                string fx = PickOne(h.Fx);
                if (FxAmbiguous(fx)) continue;

                List<string> opts = new List<string>();
                opts.Add(fx);
                List<Herb> twins = Twins(h);

                // 干扰项：其他药拥有的、且本药不具备的功效
                int guard = 0;
                while (opts.Count < 4 && guard < 200)
                {
                    guard++;
                    Herb o = PickOne(_pool);
                    if (o == h) continue;
                    if (twins.Contains(o)) continue;
                    string f2 = PickOne(o.Fx);
                    if (h.FxOverlap(f2)) continue;
                    if (AnswerMatcher.Norm(f2) == AnswerMatcher.Norm(fx)) continue;
                    if (opts.Contains(f2)) continue;
                    opts.Add(f2);
                }
                if (opts.Count < 4) continue;
                Shuffle(opts, _rnd);

                QItem it = new QItem();
                it.HerbName = h.Name;
                it.Question = "「" + h.Name + "」的功效是：";
                it.Options = opts.ToArray();
                it.AnswerIndex = opts.IndexOf(fx);
                it.Reference = h.Name + "：" + h.FxText;
                it.Tip = h.Cat + "　性味：" + h.Nature;
                return it;
            }
            return null;
        }

        /// <summary>下列哪项不是某药的功效</summary>
        private QItem MakeSingleNotFx()
        {
            for (int attempt = 0; attempt < 40; attempt++)
            {
                Herb h = PickOne(_pool);
                if (h.Fx.Count < 3) continue;
                List<Herb> twins = Twins(h);

                // 真实功效做正确项（3 个）
                List<string> reals = new List<string>(h.Fx);
                Shuffle(reals, _rnd);
                if (reals.Count < 3) continue;

                // 假功效：来自其他药、本药完全不具备、且不会歧义
                string fake = null;
                int guard = 0;
                while (fake == null && guard < 200)
                {
                    guard++;
                    Herb o = PickOne(_pool);
                    if (o == h || twins.Contains(o)) continue;
                    string f = PickOne(o.Fx);
                    if (h.FxOverlap(f)) continue;
                    if (FxHerbCount(f) < 1) continue;
                    bool bad = false;
                    foreach (string r in reals)
                        if (AnswerMatcher.Norm(r) == AnswerMatcher.Norm(f)) { bad = true; break; }
                    if (bad) continue;
                    fake = f;
                }
                if (fake == null) continue;

                List<string> opts = new List<string>();
                opts.Add(fake);
                opts.Add(reals[0]); opts.Add(reals[1]); opts.Add(reals[2]);
                Shuffle(opts, _rnd);

                QItem it = new QItem();
                it.HerbName = h.Name;
                it.Question = "下列哪一项不是「" + h.Name + "」的功效？";
                it.Options = opts.ToArray();
                it.AnswerIndex = opts.IndexOf(fake);
                it.Reference = h.Name + "：" + h.FxText + "（“" + fake + "”为其他药物的功效）";
                it.Tip = h.Cat;
                return it;
            }
            return null;
        }

        /// <summary>性味 / 归经辨析</summary>
        private QItem MakeSingleByNature()
        {
            int mode = _rnd.Next(3);
            for (int attempt = 0; attempt < 40; attempt++)
            {
                Herb h = PickOne(_pool);
                string correct;
                string ask;
                if (mode == 0) { correct = h.Nature; ask = "「" + h.Name + "」的性味是："; }
                else if (mode == 1) { correct = h.Meridian; ask = "「" + h.Name + "」的归经是："; }
                else
                {
                    correct = h.Cat;
                    ask = "「" + h.Name + "」属于下列哪一类药物？";
                }
                if (string.IsNullOrEmpty(correct)) continue;

                List<string> opts = new List<string>();
                opts.Add(correct);
                int guard = 0;
                bool byCat = (mode == 2);
                List<string> cands = byCat ? _data.Categories : NaturePool();
                while (opts.Count < 4 && guard < 200)
                {
                    guard++;
                    string cand = cands[_rnd.Next(cands.Count)];
                    if (string.IsNullOrEmpty(cand)) continue;
                    if (cand == correct) continue;
                    if (opts.Contains(cand)) continue;
                    // 避免与正确答案语义重复
                    if (!byCat)
                    {
                        if (CsvShare(cand, correct)) continue;
                    }
                    opts.Add(cand);
                }
                if (opts.Count < 4) continue;
                Shuffle(opts, _rnd);

                QItem it = new QItem();
                it.HerbName = h.Name;
                it.Question = ask;
                it.Options = opts.ToArray();
                it.AnswerIndex = opts.IndexOf(correct);
                it.Reference = h.Name + "：性味" + h.Nature + "，归" + h.Meridian + "经。功效：" + h.FxText;
                it.Tip = h.Cat;
                return it;
            }
            return null;
        }

        private List<string> _naturePool;
        private List<string> NaturePool()
        {
            if (_naturePool == null)
            {
                _naturePool = new List<string>();
                foreach (Herb h in _data.Herbs)
                {
                    if (!string.IsNullOrEmpty(h.Nature) && !_naturePool.Contains(h.Nature))
                        _naturePool.Add(h.Nature);
                    if (!string.IsNullOrEmpty(h.Meridian) && !_naturePool.Contains(h.Meridian))
                        _naturePool.Add(h.Meridian);
                }
            }
            return _naturePool;
        }

        private static bool CsvShare(string a, string b)
        {
            string[] pa = a.Split(new char[] { '、', '，', ',' }, StringSplitOptions.RemoveEmptyEntries);
            string[] pb = b.Split(new char[] { '、', '，', ',' }, StringSplitOptions.RemoveEmptyEntries);
            foreach (string x in pa)
                foreach (string y in pb)
                    if (x.Trim().Length > 0 && x.Trim() == y.Trim()) return true;
            return false;
        }

        /// <summary>挑选干扰药物：不具备目标功效、与本药功效集不同</summary>
        private List<Herb> DecoyHerbs(Herb target, string fx, int count)
        {
            List<Herb> sameCat = new List<Herb>();
            List<Herb> other = new List<Herb>();
            foreach (Herb o in _pool)
            {
                if (o == target) continue;
                if (o.FxOverlap(fx)) continue;
                if (SameFxSet(o, target)) continue;
                if (o.Cat == target.Cat) sameCat.Add(o);
                else other.Add(o);
            }
            Shuffle(sameCat, _rnd);
            Shuffle(other, _rnd);
            List<Herb> res = new List<Herb>();
            foreach (Herb h in sameCat)
            {
                if (res.Count >= count) break;
                res.Add(h);
            }
            foreach (Herb h in other)
            {
                if (res.Count >= count) break;
                res.Add(h);
            }
            return res;
        }

        // ---------------- 多项选择题 ----------------
        private QItem MakeMulti()
        {
            int style = _rnd.Next(2);
            if (style == 0) return MakeMultiByFunction();
            return MakeMultiByHerb();
        }

        /// <summary>下列哪些药物具有某功效</summary>
        private QItem MakeMultiByFunction()
        {
            for (int attempt = 0; attempt < 40; attempt++)
            {
                Herb seed = PickOne(_pool);
                if (seed.Fx.Count == 0) continue;
                string fx = PickOne(seed.Fx);
                if (FxAmbiguous(fx)) continue;

                List<Herb> owners = new List<Herb>();
                List<Herb> l;
                if (_fxIndex.TryGetValue(AnswerMatcher.Norm(fx), out l))
                {
                    foreach (Herb h in l) if (_pool.Contains(h) && !owners.Contains(h)) owners.Add(h);
                }
                if (owners.Count < 4) continue;

                // 正确项 2~3 个；确保彼此功效不完全相同
                Shuffle(owners, _rnd);
                List<Herb> correct = new List<Herb>();
                foreach (Herb o in owners)
                {
                    if (correct.Count >= 3) break;
                    bool clash = false;
                    foreach (Herb c in correct) if (SameFxSet(c, o)) { clash = true; break; }
                    if (!clash) correct.Add(o);
                }
                if (correct.Count < 2) continue;

                int need = 4 - correct.Count;
                List<Herb> decoys = new List<Herb>();
                int guard = 0;
                while (decoys.Count < need && guard < 300)
                {
                    guard++;
                    Herb o = PickOne(_pool);
                    if (o.FxOverlap(fx)) continue;
                    bool clash = false;
                    foreach (Herb c in correct) if (SameFxSet(c, o)) { clash = true; break; }
                    foreach (Herb c in decoys) if (SameFxSet(c, o)) { clash = true; break; }
                    if (clash || decoys.Contains(o)) continue;
                    decoys.Add(o);
                }
                if (decoys.Count < need) continue;

                List<Herb> all = new List<Herb>(correct);
                all.AddRange(decoys);
                Shuffle(all, _rnd);

                string[] opts = new string[all.Count];
                List<int> ans = new List<int>();
                for (int i = 0; i < all.Count; i++)
                {
                    opts[i] = all[i].Name;
                    if (correct.Contains(all[i])) ans.Add(i);
                }

                QItem it = new QItem();
                it.HerbName = correct[0].Name;
                it.Question = "具有「" + fx + "」功效的药物有（多选）：";
                it.Options = opts;
                it.AnswerSet = ans.ToArray();
                StringBuilder sb = new StringBuilder();
                sb.Append("具有「" + fx + "」的药物：");
                foreach (Herb c in owners) sb.Append(c.Name + "、");
                it.Reference = sb.ToString().TrimEnd('、') + "。";
                it.Tip = "多选，全对得满分，漏选得一半分，错选不得分";
                return it;
            }
            return null;
        }

        /// <summary>某药的功效包括哪些</summary>
        private QItem MakeMultiByHerb()
        {
            for (int attempt = 0; attempt < 40; attempt++)
            {
                Herb h = PickOne(_pool);
                if (h.Fx.Count < 2) continue;
                List<Herb> twins = Twins(h);

                List<string> correct = new List<string>(h.Fx);
                int needFake = Math.Max(2, 4 - correct.Count);
                List<string> fake = new List<string>();
                int guard = 0;
                while (fake.Count < needFake && guard < 300)
                {
                    guard++;
                    Herb o = PickOne(_pool);
                    if (o == h || twins.Contains(o)) continue;
                    string f = PickOne(o.Fx);
                    string nf = AnswerMatcher.Norm(f);
                    bool clash = false;
                    foreach (string c in correct) if (AnswerMatcher.Norm(c) == nf) { clash = true; break; }
                    foreach (string c in fake) if (AnswerMatcher.Norm(c) == nf) { clash = true; break; }
                    if (clash) continue;
                    if (h.FxOverlap(f)) continue;
                    fake.Add(f);
                }
                if (fake.Count < needFake) continue;

                List<string> opts = new List<string>(correct);
                opts.AddRange(fake);
                Shuffle(opts, _rnd);
                string[] arr = opts.ToArray();
                List<int> ans = new List<int>();
                for (int i = 0; i < arr.Length; i++)
                    foreach (string c in correct)
                        if (AnswerMatcher.Norm(arr[i]) == AnswerMatcher.Norm(c)) { ans.Add(i); break; }
                if (ans.Count < 2) continue;

                QItem it = new QItem();
                it.HerbName = h.Name;
                it.Question = "「" + h.Name + "」的功效包括（多选）：";
                it.Options = arr;
                it.AnswerSet = ans.ToArray();
                it.Reference = h.Name + "：" + h.FxText;
                it.Tip = "多选，全对得满分，漏选得一半分，错选不得分";
                return it;
            }
            return null;
        }

        // ---------------- 判断题 ----------------
        private QItem MakeJudge()
        {
            for (int attempt = 0; attempt < 40; attempt++)
            {
                Herb h = PickOne(_pool);
                if (h.Fx.Count == 0) continue;
                bool makeTrue = _rnd.Next(100) < 50;

                if (makeTrue)
                {
                    string fx = PickOne(h.Fx);
                    if (FxAmbiguous(fx)) continue;
                    // 若能找到性味不同的同名类别药，则考性味（教材常见考点）
                    string stat = "「" + h.Name + "」的功效是" + h.FxText + "。";
                    if (_rnd.Next(100) < 30 && !string.IsNullOrEmpty(h.Nature))
                        stat = "「" + h.Name + "」性" + h.Nature + "，归" + Merid(h) + "。";
                    QItem it = new QItem();
                    it.HerbName = h.Name;
                    it.Question = "判断下列说法是否正确：\n\n" + stat;
                    it.Options = new string[] { "正确", "错误" };
                    it.AnswerIndex = 0;
                    it.Reference = h.Name + "：性味" + h.Nature + "，归" + h.Meridian + "经；功效：" + h.FxText;
                    it.Tip = "判断题";
                    return it;
                }
                else
                {
                    string stat = MakeFalseStatement(h);
                    if (stat == null) continue;
                    QItem it = new QItem();
                    it.HerbName = h.Name;
                    it.Question = "判断下列说法是否正确：\n\n" + stat;
                    it.Options = new string[] { "正确", "错误" };
                    it.AnswerIndex = 1;
                    it.Reference = h.Name + "：性味" + h.Nature + "，归" + h.Meridian +
                                  "经；功效：" + h.FxText;
                    it.Tip = "判断题";
                    return it;
                }
            }
            return null;
        }

        /// <summary>构造一条关于 h 的错误说法（用于判断题）</summary>
        private string MakeFalseStatement(Herb h)
        {
            List<Herb> twins = Twins(h);
            if (_rnd.Next(100) < 70)
            {
                // 张冠李戴：把其他药的功效安在本药头上
                int guard = 0;
                while (guard < 200)
                {
                    guard++;
                    Herb o = PickOne(_pool);
                    if (o == h || twins.Contains(o)) continue;
                    string f = PickOne(o.Fx);
                    if (h.FxOverlap(f)) continue;
                    if (AnswerMatcher.Norm(f).Length < 2) continue;
                    return "「" + h.Name + "」的功效是" + f + "。";
                }
                return null;
            }
            // 性味张冠李戴
            int g = 0;
            while (g < 200)
            {
                g++;
                Herb o = PickOne(_pool);
                if (o == h) continue;
                if (AnswerMatcher.Norm(o.Nature) == AnswerMatcher.Norm(h.Nature)) continue;
                if (string.IsNullOrEmpty(o.Nature)) continue;
                return "「" + h.Name + "」的性味是" + o.Nature + "。";
            }
            return null;
        }

        // ---------------- 填空题 ----------------
        private QItem MakeFill()
        {
            for (int attempt = 0; attempt < 60; attempt++)
            {
                int style = _rnd.Next(4);
                Herb h = PickOne(_pool);
                if (h.Fx.Count == 0) continue;

                if (style == 0 && h.Fx.Count >= 2)
                {
                    // 功效填空
                    string fx = PickOne(h.Fx);
                    if (AnswerMatcher.Norm(fx).Length < 2) continue;
                    string body = h.FxText.Replace(fx, "＿＿＿＿");
                    QItem it = new QItem();
                    it.HerbName = h.Name;
                    it.Question = "「" + h.Name + "」的功效是：" + body + "\n\n请填写空缺的功效：";
                    it.FillAnswer = fx;
                    it.Reference = h.Name + "：" + h.FxText;
                    it.Tip = "填空题（系统自动模糊判分）";
                    return it;
                }
                if (style == 1)
                {
                    // 性味 / 归经 / 分类填空
                    if (string.IsNullOrEmpty(h.Nature) || string.IsNullOrEmpty(h.Meridian)) continue;
                    QItem it = new QItem();
                    it.HerbName = h.Name;
                    if (_rnd.Next(2) == 0)
                    {
                        it.Question = "「" + h.Name + "」的性味是：＿＿＿＿\n\n请填写其性味（如：辛，温）：";
                        it.FillAnswer = h.Nature;
                    }
                    else
                    {
                        it.Question = "「" + h.Name + "」归＿＿＿＿经。\n\n请填写归经（如：肺、胃经）：";
                        it.FillAnswer = h.Meridian;
                    }
                    it.Reference = h.Name + "：性味" + h.Nature + "，归" + h.Meridian + "经。功效：" + h.FxText;
                    it.Tip = "填空题（系统自动模糊判分）";
                    return it;
                }
                if (style == 2)
                {
                    // 药物填空：具备某独有功效的药
                    string fx = PickOne(h.Fx);
                    if (FxHerbCount(fx) != 1 || FxAmbiguous(fx)) continue;
                    QItem it = new QItem();
                    it.HerbName = h.Name;
                    it.Question = "具有「" + fx + "」功效的药物是：＿＿＿＿\n\n请填写药名：";
                    it.FillAnswer = h.Name;
                    it.Reference = h.Name + "：" + h.FxText + "（性味" + h.Nature + "）";
                    it.Tip = "填空题（系统自动模糊判分）";
                    return it;
                }
                if (style == 3)
                {
                    // 分类填空
                    string main = h.CatMain;
                    string sub = h.CatSub;
                    QItem it = new QItem();
                    it.HerbName = h.Name;
                    if (sub.Length > 0 && _rnd.Next(2) == 0)
                    {
                        it.Question = "「" + h.Name + "」属于" + main + "中的哪一类？\n\n请填写（如：发散风寒药）：";
                        it.FillAnswer = sub;
                    }
                    else
                    {
                        it.Question = "「" + h.Name + "」属于哪一类药物？\n\n请填写（如：解表药）：";
                        it.FillAnswer = main;
                    }
                    it.Reference = h.Name + "　分类：" + h.Cat;
                    it.Tip = "填空题（系统自动模糊判分）";
                    return it;
                }
            }
            return null;
        }

        // ---------------- 配对题（预留） ----------------
        private QItem MakeMatch()
        {
            for (int attempt = 0; attempt < 60; attempt++)
            {
                Herb h = PickOne(_pool);
                if (h.Fx.Count == 0) continue;
                string fx = PickOne(h.Fx);
                int owners = FxHerbCount(fx);
                if (owners != 1 || FxAmbiguous(fx)) continue;

                List<string> left = new List<string>();
                List<string> right = new List<string>();
                left.Add(h.Name);
                right.Add(fx);

                int guard = 0;
                while (left.Count < 4 && guard < 400)
                {
                    guard++;
                    Herb o = PickOne(_pool);
                    if (o == h) continue;
                    if (left.Contains(o.Name)) continue;
                    string f = null;
                    // 选一个该药独有的功效做配对答案
                    foreach (string cand in o.Fx)
                        if (FxHerbCount(cand) == 1 && !FxAmbiguous(cand)) { f = cand; break; }
                    if (f == null) continue;
                    left.Add(o.Name);
                    right.Add(f);
                }
                if (left.Count < 4) continue;

                // 加入干扰项
                int need = 0;
                while (right.Count < 6 && need < 400)
                {
                    need++;
                    Herb o = PickOne(_pool);
                    string f = PickOne(o.Fx);
                    if (right.Contains(f)) continue;
                    if (AnswerMatcher.Norm(f).Length < 2) continue;
                    right.Add(f);
                }

                Shuffle(left, _rnd);
                List<string> answers = new List<string>();
                foreach (string name in left)
                {
                    Herb hh = _data.Find(name);
                    string sel = "";
                    if (hh != null)
                    {
                        foreach (string f in hh.Fx)
                            if (right.Contains(f)) { sel = f; break; }
                    }
                    answers.Add(sel);
                }

                List<string> opt = new List<string>(right);
                Shuffle(opt, _rnd);

                QItem it = new QItem();
                it.HerbName = h.Name;
                it.Question = "配伍选择：为下列药物选择其具有的功效（下拉选择）。";
                it.MatchLeft = left.ToArray();
                it.MatchOptions = opt.ToArray();
                it.MatchAnswer = new int[left.Count];
                bool bad = false;
                for (int i = 0; i < left.Count; i++)
                {
                    int idx = opt.IndexOf(answers[i]);
                    if (idx < 0) { bad = true; break; }
                    it.MatchAnswer[i] = idx;
                }
                if (bad) continue;
                it.MatchPick = new int[left.Count];
                for (int i = 0; i < it.MatchPick.Length; i++) it.MatchPick[i] = -1;
                it.Reference = "正确答案见上方提示";
                it.Tip = "配对题";
                return it;
            }
            return null;
        }
    }

    // ------------------------------------------------------------------
    //  判分 / 成绩单
    // ------------------------------------------------------------------
    public class QuizData
    {
        public List<QItem> Items = new List<QItem>();
        public int LimitSeconds = 0;
        public int UsedSeconds = 0;
        public string ModeName = "模拟测试";

        public int TotalScore()
        {
            int s = 0;
            foreach (QItem it in Items) s += it.Points;
            return s;
        }

        public void Grade()
        {
            foreach (QItem it in Items)
            {
                if (it.Graded) continue;
                it.Score = ScoreOf(it);
                it.Graded = true;
            }
        }

        public static double ScoreOf(QItem it)
        {
            switch (it.Type)
            {
                case QType.Single:
                    if (!it.Answered) return 0;
                    return (it.Pick.Count > 0 && it.Pick[0] == it.AnswerIndex) ? it.Points : 0;

                case QType.Judge:
                    if (!it.Answered) return 0;
                    return (it.Pick.Count > 0 && it.Pick[0] == it.AnswerIndex) ? it.Points : 0;

                case QType.Fill:
                    if (!it.Answered) return 0;
                    return AnswerMatcher.IsCorrect(it.FillInput, it.FillAnswer) ? it.Points : 0;

                case QType.Multi:
                    {
                        if (!it.Answered || it.Pick.Count == 0) return 0;
                        bool wrong = false;
                        int hit = 0;
                        foreach (int p in it.Pick)
                        {
                            bool isAns = false;
                            foreach (int a in it.AnswerSet) if (a == p) { isAns = true; break; }
                            if (isAns) hit++; else wrong = true;
                        }
                        if (wrong) return 0;
                        int total = Math.Max(1, it.AnswerSet.Length);
                        if (hit == total) return it.Points;
                        return it.Points * 0.5;
                    }

                case QType.Match:
                    {
                        if (!it.Answered || it.MatchPick == null) return 0;
                        int hit = 0;
                        for (int i = 0; i < it.MatchAnswer.Length; i++)
                            if (it.MatchPick[i] == it.MatchAnswer[i]) hit++;
                        if (hit == it.MatchAnswer.Length) return it.Points;
                        return it.Points * (double)hit / Math.Max(1, it.MatchAnswer.Length) * 0.9;
                    }
            }
            return 0;
        }

        public int Score()
        {
            double s = 0;
            foreach (QItem it in Items) s += it.Score;
            return (int)Math.Round(s);
        }

        public int CountCorrect()
        {
            int c = 0;
            foreach (QItem it in Items)
                if (it.Graded && it.Score >= it.Points - 0.001) c++;
            return c;
        }

        public double HalfCorrect()
        {
            double c = 0;
            foreach (QItem it in Items)
                if (it.Graded && it.Score > 0 && it.Score < it.Points - 0.001) c++;
            return c;
        }

        public int CountAnswered()
        {
            int c = 0;
            foreach (QItem it in Items) if (it.Answered) c++;
            return c;
        }

        public List<QItem> WrongItems()
        {
            List<QItem> r = new List<QItem>();
            foreach (QItem it in Items)
                if (!it.Graded || it.Score < it.Points - 0.001) r.Add(it);
            return r;
        }

        public string TimeText(int sec)
        {
            int m = sec / 60;
            int s = sec % 60;
            return m.ToString("00") + ":" + s.ToString("00");
        }
    }
}
