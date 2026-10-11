# -*- coding: utf-8 -*-
"""本次要重挑图片的药味清单（用户 2026-10-11 反馈「图片有误」）。

用法:
  python tools/review/refetch_list.py            # 打印清单与统计
  python tools/review/refetch_list.py --write    # 写出 review/refetch_names.txt
"""
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 用户原话里的清单（保留原顺序，含重复）
RAW = """穿山甲 蜂蜜 蜂房 紫草 苍术 丁香 羌活 蚕沙 郁金 鸦胆子 使君子 槟榔 雷丸 鹤草芽
薤白 人参 绞股蓝 饴糖 牛黄 天麻 蜈蚣 羚羊角 代赭石 生铁落 麝香 冰片 苏合香 熊胆
黄芩 石膏 知母 淡竹叶 夏枯草 小蓟 款冬花 白及 佩兰 秦艽 橘核 紫苏叶 生姜 防风
羌活 藁本 升麻 葛根 淡豆豉 金银花 大青叶 射干 马勃 白头翁 马齿苋 生地黄 赤芍
水牛角 青蒿 地骨皮 白薇 银柴胡 胡黄连 火麻仁 郁李仁 京大戟 巴豆霜 川乌 豨莶草
络石藤 雷公藤 苍术 草豆蔻 茯苓 玉米须 冬瓜皮 通草 车前子 瞿麦 地肤子 海金沙
虎杖 干姜 吴茱萸 胡椒 陈皮 木香 香附 沉香 檀香 大腹皮 麦芽 莱菔子 南瓜子 大蓟
槐花 侧柏叶 白茅根 苎麻根 浅草 五灵脂 仙鹤草 棕榈炭 钩藤 艾叶 血余炭 炮姜 川芎
姜黄 乳香 桃仁 自然铜 土鳖虫 王不留行 骨碎补 血竭 三棱 穿山甲 天南星 芥子
白附子 川贝母 浙贝母 瓜蒌 前胡 竹沥 昆布 百部 紫菀 桑白皮 葶苈子 朱砂 磁石 龙骨
酸枣仁 柏子仁 远志 珍珠母 地龙 蜈蚣 石菖蒲 太子参 仙茅 续断 肉苁蓉 补骨脂 益智仁
菟丝子 沙苑子 冬虫夏草 当归 熟地黄 白芍 阿胶 龙眼肉 北沙参 南沙参 天冬 黄精
女贞子 肉豆蔻 赤石脂 金樱子 紫苏梗 重楼 山慈菇 金荞麦 商陆 千金子 草乌 蚕沙
海桐皮 老鹤草 两面针 橘核 娑罗子 刀豆 月季花 凌霄花 矮地茶 蛇床子 升药 绞股蓝
鹿角 鹿角霜 核桃仁 韭菜子 胆南星 洋金花 满山红"""

# 用户笔误 / 别名 → 题库标准药名
ALIAS = {
    "老鹤草": "老鹳草",
    "浅草": "茜草",        # 位于苎麻根与五灵脂之间，教材止血药顺序即茜草；疑为输入笔误
}


def names():
    seen, out = set(), []
    for raw in RAW.split():
        n = ALIAS.get(raw, raw)
        if n in seen:
            continue
        seen.add(n)
        out.append(n)
    return out


def main():
    ns = names()
    herbs = json.load(io.open(os.path.join(ROOT, "herbs.json"), encoding="utf-8"))["herbs"]
    have = set(h["name"] for h in herbs)
    miss = [n for n in ns if n not in have]
    print("去重后 %d 味（原清单含重复项已合并）" % len(ns))
    print("题库中不存在: %s" % (miss or "无"))
    if "--write" in sys.argv:
        p = os.path.join(ROOT, "review", "refetch_names.txt")
        io.open(p, "w", encoding="utf-8").write("\n".join(ns) + "\n")
        print("已写出 %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
