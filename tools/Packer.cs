// =====================================================================
//  图片打包工具（构建期使用，不随主程序发布）
//  文件: tools/Packer.cs
//
//  把 images/ 目录打包成 .NET 资源文件 images.res：
//    - 每条图片作为一个 byte[] 资源（资源名 = 文件名）
//    - 同时写入 TCMIMG 汇总包（主程序优先读取它）
//  资源文件用 csc /resource: 编进 exe，运行时用 GetManifestResourceStream 读取，
//  这样图片数据不进入 .NET 字符串元数据（避免 CS0013 元数据溢出）。
//
//  用法: Packer.exe <images目录> <输出.res> [最长边] [质量]
// =====================================================================
using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Resources;
using System.Text;

internal static class Packer
{
    private static int Main(string[] args)
    {
        if (args.Length < 2)
        {
            Console.WriteLine("usage: Packer.exe <imgDir> <outRes> [maxSide] [quality]");
            return 2;
        }
        string dir = args[0];
        string outRes = args[1];
        int maxSide = args.Length > 2 ? int.Parse(args[2]) : 420;
        int quality = args.Length > 3 ? int.Parse(args[3]) : 70;

        if (!Directory.Exists(dir))
        {
            Console.WriteLine("no dir: " + dir);
            Console.WriteLine("written=0");
            return 0;
        }

        string[] files = Directory.GetFiles(dir);
        Array.Sort(files, StringComparer.Ordinal);

        List<string> names = new List<string>();
        List<byte[]> datas = new List<byte[]>();
        long total = 0;
        int skipped = 0;

        foreach (string f in files)
        {
            string ext = Path.GetExtension(f).ToLowerInvariant();
            if (ext != ".jpg" && ext != ".jpeg" && ext != ".png") continue;
            try
            {
                byte[] packed = Repack(f, maxSide, quality);
                if (packed == null || packed.Length < 500) { skipped++; continue; }
                names.Add(Path.GetFileName(f));
                datas.Add(packed);
                total += packed.Length;
            }
            catch (Exception ex)
            {
                skipped++;
                Console.WriteLine("skip " + Path.GetFileName(f) + ": " + ex.Message);
            }
        }

        // ---- 汇总包（主程序优先读它） ----
        MemoryStream ms = new MemoryStream();
        BinaryWriter bw = new BinaryWriter(ms, Encoding.UTF8);
        bw.Write(Encoding.ASCII.GetBytes("TCMIMGV1"));
        bw.Write(1);
        bw.Write(names.Count);
        // 头部长度 = 16 + Σ(4 + 名称字节 + 8)
        int headLen = 16;
        for (int i = 0; i < names.Count; i++)
            headLen += 4 + Encoding.UTF8.GetByteCount(names[i]) + 8;
        int off = 0;
        for (int i = 0; i < names.Count; i++)
        {
            byte[] nb = Encoding.UTF8.GetBytes(names[i]);
            bw.Write(nb.Length);
            bw.Write(nb);
            bw.Write(off);
            bw.Write(datas[i].Length);
            off += datas[i].Length;
        }
        for (int i = 0; i < datas.Count; i++) bw.Write(datas[i]);
        bw.Flush();
        byte[] bundle = ms.ToArray();
        bw.Close();

        // ---- 写资源文件（只存汇总包，避免两份数据） ----
        using (ResourceWriter rw = new ResourceWriter(outRes))
        {
            rw.AddResource("TCMIMG", bundle);
            rw.Generate();
        }

        Console.WriteLine("written=" + names.Count + " skipped=" + skipped +
            " packed=" + (total / 1048576.0).ToString("0.0") + "MB" +
            " res=" + (new FileInfo(outRes).Length / 1048576.0).ToString("0.0") + "MB");
        return 0;
    }

    /// <summary>缩放并重新编码为 JPEG</summary>
    private static byte[] Repack(string path, int maxSide, int quality)
    {
        using (Image src = Image.FromFile(path))
        {
            int w = src.Width, h = src.Height;
            int nw = w, nh = h;
            if (Math.Max(w, h) > maxSide)
            {
                double k = (double)maxSide / Math.Max(w, h);
                nw = Math.Max(1, (int)(w * k));
                nh = Math.Max(1, (int)(h * k));
            }
            using (Bitmap bmp = new Bitmap(nw, nh, PixelFormat.Format24bppRgb))
            {
                using (Graphics g = Graphics.FromImage(bmp))
                {
                    g.InterpolationMode = System.Drawing.Drawing2D.InterpolationMode.HighQualityBicubic;
                    g.PixelOffsetMode = System.Drawing.Drawing2D.PixelOffsetMode.HighQuality;
                    g.Clear(Color.White);
                    g.DrawImage(src, 0, 0, nw, nh);
                }
                ImageCodecInfo jpg = null;
                foreach (ImageCodecInfo c in ImageCodecInfo.GetImageEncoders())
                    if (c.FormatID == ImageFormat.Jpeg.Guid) { jpg = c; break; }
                using (EncoderParameters ep = new EncoderParameters(1))
                {
                    ep.Param[0] = new EncoderParameter(System.Drawing.Imaging.Encoder.Quality, (long)quality);
                    using (MemoryStream outMs = new MemoryStream())
                    {
                        bmp.Save(outMs, jpg, ep);
                        return outMs.ToArray();
                    }
                }
            }
        }
    }
}
