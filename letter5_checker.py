#!/usr/bin/env python3
"""
5位纯英文字母 .com 域名挖掘与检测工具 (5-Letter .com Domain Finder)

特点：
1. 精准双阶段检测：
   - 第一阶段：aiodns 异步高并发 DNS 初筛（极速跳过已建站/已配置NS的绝大部分域名）
   - 第二阶段：Verisign 官方权威 RDAP 接口复核（100% 确保未被抢注，杜绝误报）
2. 智能品相策略（告别杂乱无意义字符）：
   - cvcvc / pronounce: 辅音+元音+辅音+元音+辅音 (如 balex.com, rovik.com)，自然发音、适合品牌
   - pinyin: 5字母拼音组合 (2+3 或 3+2，如 banli.com, daqiu.com)，适合国内项目
   - patterns: 结构韵律型 (如 ABABA, AABAA, ABBAB)
   - suffix: 优质词根/后缀 (如 xxly, xxer, xxon, xxio, xxgo 等)
   - random: 完全随机 5 字母
3. 批次化挖掘：支持指定目标找到 N 个可用域名后自动停止。
"""

import argparse
import asyncio
import itertools
import random
import signal
import string
import sys
import time
import urllib.error
import urllib.request
import aiodns

running = True


def signal_handler(sig, frame):
    global running
    print("\n[!] 收到停止指令，正在保存已找到的可用域名...")
    running = False


signal.signal(signal.SIGINT, signal_handler)

# 辅音与元音定义
VOWELS = ["a", "e", "i", "o", "u"]
CONSONANTS = [c for c in string.ascii_lowercase if c not in VOWELS]  # 21个辅音
# 优质高频易读辅音（剔除 q, x, z 等较生僻辅音，发音更自然）
PREMIUM_CONSONANTS = [
    "b", "c", "d", "f", "g", "h", "k", "l", "m", "n", "p", "r", "s", "t", "v", "w", "y"
]

# 2字母常用拼音
PINYIN_2 = [
    "ba", "bi", "bo", "bu", "pa", "pi", "po", "pu", "ma", "mi", "mo", "mu", "fa", "fo", "fu",
    "da", "de", "di", "du", "ta", "te", "ti", "tu", "na", "ne", "ni", "nu", "la", "le", "li", "lu",
    "ga", "ge", "gu", "ka", "ke", "ku", "ha", "he", "hu", "za", "ze", "zi", "zu", "ca", "ce", "ci", "cu",
    "sa", "se", "si", "su", "ya", "ye", "yi", "yo", "yu", "wa", "wo", "wu"
]

# 3字母常用拼音
PINYIN_3 = [
    "bai", "bei", "bao", "ban", "ben", "pai", "pei", "pao", "pou", "pan", "pen",
    "mai", "mei", "mao", "mou", "man", "men", "fai", "fei", "fan", "fen",
    "dai", "dei", "dao", "dou", "dan", "den", "tai", "tao", "tou", "tan",
    "nai", "nei", "nao", "nou", "nan", "nen", "lai", "lei", "lao", "lou", "lan",
    "gai", "gei", "gao", "gou", "gan", "gen", "kai", "kou", "kan", "ken",
    "hai", "hei", "hao", "hou", "han", "hen", "zai", "zei", "zao", "zou", "zan", "zen",
    "cai", "cao", "cou", "can", "cen", "sai", "sao", "sou", "san", "sen"
]

# 常见 2 字母后缀
TECH_SUFFIXES = ["ly", "er", "on", "ex", "go", "io", "is", "up", "me", "in", "do", "to"]
# 科技感硬朗发音后缀 (常用于工具、安全、SaaS、数据库产品)
TECH_ENDINGS = ["ix", "ex", "ox", "ax", "on", "os", "is", "us", "or", "er"]


def gen_cvcvc(premium: bool = True) -> str:
    """生成 CVCVC 发音型单词 (如: badev, rozin, valex)"""
    cs = PREMIUM_CONSONANTS if premium else CONSONANTS
    c1 = random.choice(cs)
    v1 = random.choice(VOWELS)
    c2 = random.choice(cs)
    v2 = random.choice(VOWELS)
    c3 = random.choice(cs)
    return f"{c1}{v1}{c2}{v2}{c3}.com"


def gen_tech_brand() -> str:
    """科技极客感 5 字母域名: 辅音+元音+辅音+科技后缀 (如 kavex, zolix, velon, remox)"""
    cs = PREMIUM_CONSONANTS
    c1 = random.choice(cs)
    v1 = random.choice(VOWELS)
    c2 = random.choice(cs)
    end = random.choice(TECH_ENDINGS)
    # c1(1) + v1(1) + end(2) = 4字母，需要 5 字母:
    # 结构 1: c1 + v1 + c2 + end (如 r + e + m + ox = remox.com -> 5字母)
    # 结构 2: c1 + v1 + end + 辅音 (5字母)
    return f"{c1}{v1}{c2}{end}.com" if len(end) == 2 else f"{c1}{v1}{c2}{end}x.com"


def gen_ai_brand() -> str:
    """AI 品牌域名: xxxai.com 或 aixxx.com (共5字母纯英文字母)"""
    chars = string.ascii_lowercase
    if random.random() < 0.6:
        # xxx + ai.com
        prefix = "".join(random.choices(chars, k=3))
        return f"{prefix}ai.com"
    else:
        # ai + xxx.com
        suffix = "".join(random.choices(chars, k=3))
        return f"ai{suffix}.com"


def gen_vcvcv() -> str:
    """优雅元音开头的双音节品牌词: V+C+V+C+V (如 amiro, eliva, ovira, uzela)"""
    cs = PREMIUM_CONSONANTS
    v1 = random.choice(VOWELS)
    c1 = random.choice(cs)
    v2 = random.choice(VOWELS)
    c2 = random.choice(cs)
    v3 = random.choice(VOWELS)
    return f"{v1}{c1}{v2}{c2}{v3}.com"


def gen_startup() -> str:
    """初创公司高频商业词头: co / go / re / up + 3字母自然发音 (如 gotem, copek, rezon, uplov)"""
    prefix = random.choice(["co", "go", "re", "up", "ex", "in", "my"])
    c1 = random.choice(PREMIUM_CONSONANTS)
    v1 = random.choice(VOWELS)
    c2 = random.choice(PREMIUM_CONSONANTS)
    return f"{prefix}{c1}{v1}{c2}.com"


def gen_blend() -> str:
    """流动辅音高级双音节词: C + V + [l/r/n/s/m] + C + V (如 belsa, mirco, korva, tensa, valdo)"""
    cs = PREMIUM_CONSONANTS
    c1 = random.choice(cs)
    v1 = random.choice(VOWELS)
    bridge = random.choice(["l", "r", "n", "s", "m"])
    c2 = random.choice([c for c in cs if c not in ["w", "y", "h"]])
    v2 = random.choice(VOWELS)
    return f"{c1}{v1}{bridge}{c2}{v2}.com"


def gen_friendly() -> str:
    """高亲和力社交/个人词头: my / we / ok / hi / be + 3字母自然发音 (如 weton, mypek, okvim, hiram)"""
    prefix = random.choice(["my", "we", "ok", "hi", "be", "so", "to"])
    c1 = random.choice(PREMIUM_CONSONANTS)
    v1 = random.choice(VOWELS)
    c2 = random.choice(PREMIUM_CONSONANTS)
    return f"{prefix}{c1}{v1}{c2}.com"


def gen_ify() -> str:
    """硅谷 SaaS 极品行动词根: 2 字母 + ify (如 voify, raify, zeify, tuify)"""
    c1 = random.choice(string.ascii_lowercase)
    c2 = random.choice(string.ascii_lowercase)
    return f"{c1}{c2}ify.com"


def gen_latin() -> str:
    """现代科技/罗曼优雅结尾: C + V + C + [ia/io/ea/eo/ua] (如 selia, tomio, bavio, remio)"""
    c1 = random.choice(PREMIUM_CONSONANTS)
    v1 = random.choice(VOWELS)
    c2 = random.choice(PREMIUM_CONSONANTS)
    end = random.choice(["ia", "io", "ea", "eo", "ua"])
    return f"{c1}{v1}{c2}{end}.com"


def gen_palindrome() -> str:
    """5字母回文艺术米: A-B-C-B-A 正反读完全一致 (如 rotur, senes, tonot, kerek)"""
    # 结构1: 辅音+元音+辅音+元音+辅音 (自然发音回文)
    if random.random() < 0.6:
        c1 = random.choice(PREMIUM_CONSONANTS)
        v = random.choice(VOWELS)
        c2 = random.choice([c for c in PREMIUM_CONSONANTS if c != c1])
        return f"{c1}{v}{c2}{v}{c1}.com"
    else:
        # 纯字母回文
        a = random.choice(string.ascii_lowercase)
        b = random.choice(string.ascii_lowercase)
        c = random.choice(string.ascii_lowercase)
        return f"{a}{b}{c}{b}{a}.com"


def gen_developer() -> str:
    """硬核极客/开发者工具词根: 2 字母 + [dev/ops/api/bot/app] (如 xkdev, vmops, qzapi)"""
    c1 = random.choice(string.ascii_lowercase)
    c2 = random.choice(string.ascii_lowercase)
    root = random.choice(["dev", "ops", "api", "bot", "app"])
    return f"{c1}{c2}{root}.com"


def gen_pinyin() -> str:
    """生成 5 字母拼音 (2+3 或 3+2)"""
    if random.random() < 0.5:
        return f"{random.choice(PINYIN_2)}{random.choice(PINYIN_3)}.com"
    else:
        return f"{random.choice(PINYIN_3)}{random.choice(PINYIN_2)}.com"


def gen_pattern() -> str:
    """生成规律/韵律型 5 字母 (如 ABABA, AABAA, ABBBA, ABBAB)"""
    pat = random.choice(["ABABA", "AABAA", "ABBBA", "ABBAB", "AABBA", "ABBAA"])
    a = random.choice(string.ascii_lowercase)
    b = random.choice([c for c in string.ascii_lowercase if c != a])
    chars = [a if ch == "A" else b for ch in pat]
    return f"{''.join(chars)}.com"


def gen_suffix_domain() -> str:
    """前 3 字母 + 2 字母常用科技词根 (如 xxly.com, xxer.com)"""
    prefix = "".join(random.choices(string.ascii_lowercase, k=3))
    suffix = random.choice(TECH_SUFFIXES)
    return f"{prefix}{suffix}.com"


def gen_random_domain() -> str:
    """完全随机 5 字母 .com"""
    letters = "".join(random.choices(string.ascii_lowercase, k=5))
    return f"{letters}.com"


def generate_batch(strategy: str, count: int) -> set[str]:
    """根据策略生成指定批次的不重复候选域名"""
    domains = set()
    attempts = 0
    max_attempts = count * 10

    while len(domains) < count and attempts < max_attempts:
        attempts += 1
        if strategy == "cvcvc":
            d = gen_cvcvc(premium=True)
        elif strategy == "palindrome":
            d = gen_palindrome()
        elif strategy == "developer":
            d = gen_developer()
        elif strategy == "ify":
            d = gen_ify()
        elif strategy == "latin":
            d = gen_latin()
        elif strategy == "blend":
            d = gen_blend()
        elif strategy == "friendly":
            d = gen_friendly()
        elif strategy == "vcvcv":
            d = gen_vcvcv()
        elif strategy == "startup":
            d = gen_startup()
        elif strategy == "tech":
            d = gen_tech_brand()
        elif strategy == "ai":
            d = gen_ai_brand()
        elif strategy == "pinyin":
            d = gen_pinyin()
        elif strategy == "pattern":
            d = gen_pattern()
        elif strategy == "suffix":
            d = gen_suffix_domain()
        elif strategy == "random":
            d = gen_random_domain()
        else:
            d = gen_cvcvc(premium=False)
        domains.add(d)

    return domains


async def check_dns_single(domain: str, resolver: aiodns.DNSResolver) -> bool:
    """DNS 查询：返回 True 表示可能是未注册 (NXDOMAIN)"""
    try:
        if hasattr(resolver, "query_dns"):
            await resolver.query_dns(domain, "NS")
        else:
            await resolver.query(domain, "NS")
        return False  # 有 NS 记录，说明已注册
    except aiodns.error.DNSError as e:
        if len(e.args) > 0 and e.args[0] == 4:
            return True  # 4 表示 NXDOMAIN
        return False
    except Exception:
        return False


def verify_rdap(domain: str, timeout: float = 3.5) -> bool | None:
    """通过 Verisign 官方注册局权威验证"""
    url = f"https://rdap.verisign.com/com/v1/domain/{domain}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) DomainFinder/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout):
            return False  # 已注册
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return True  # 确定未注册
        return None
    except Exception:
        return None


async def run_discovery_round(
    candidates: list[str],
    resolver: aiodns.DNSResolver,
    concurrency: int = 50,
) -> list[str]:
    """批量异步初筛候选集"""
    sem = asyncio.Semaphore(concurrency)
    dns_available = []

    async def _check(dom):
        async with sem:
            is_nx = await check_dns_single(dom, resolver)
            if is_nx:
                dns_available.append(dom)
            await asyncio.sleep(0.005)

    tasks = [_check(d) for d in candidates]
    await asyncio.gather(*tasks)
    return dns_available


def parse_args():
    parser = argparse.ArgumentParser(
        description="5位纯字母 .com 域名挖掘与权威检测器"
    )
    parser.add_argument(
        "--strategy",
        choices=["cvcvc", "palindrome", "developer", "ify", "latin", "blend", "friendly", "vcvcv", "startup", "tech", "ai", "pinyin", "pattern", "suffix", "random"],
        default="cvcvc",
        help="生成策略: cvcvc(易读品牌发音型), palindrome(回文艺术米rotur/senes), developer(极客工具词根xxdev/xxops), ify(SaaS行动词根xxify), latin(罗曼优雅结尾如selia/tomio), blend(流动辅音高级双音节词如belsa), friendly(社交词头my/we/ok/hi+3字母发音), vcvcv(元音开头优雅品牌词如amiro), startup(商业词头co/go/re+3字母发音), tech(极客硬朗后缀如-ix/-ex/-ox), ai(AI品牌米xxxai/aixxx), pinyin(5位拼音), pattern(韵律型ABABA), suffix(科技后缀xxly/xxer), random(纯随机)",
    )
    parser.add_argument(
        "--target",
        type=int,
        default=10,
        help="想要找到的可用域名目标数量 (默认: 10 个，找到即停)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=200,
        help="每批次生成的候选域名数 (默认: 200)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=50,
        help="DNS 并发协程数 (默认: 50)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="available_5letter.txt",
        help="保存可用域名的文件 (默认: available_5letter.txt)",
    )
    return parser.parse_args()


async def main_async(args):
    print("=" * 65)
    print("  5位纯字母 .com 域名挖掘器 (5-Letter Domain Finder)")
    print(f"  策略: {args.strategy} | 目标发现数量: {args.target} 个")
    print(f"  输出保存: {args.output}")
    print("=" * 65)

    resolver = aiodns.DNSResolver(
        nameservers=["1.1.1.1", "8.8.8.8", "223.5.5.5"],
        timeout=3.0,
        tries=2,
    )

    found_domains = []
    round_idx = 1
    total_checked = 0

    with open(args.output, "a", encoding="utf-8") as f:
        f.write(f"\n# --- 扫描启动: {time.strftime('%Y-%m-%d %H:%M:%S')} (策略: {args.strategy}) ---\n")

    while running and len(found_domains) < args.target:
        print(f"\n[第 {round_idx} 轮] 生成 {args.batch_size} 个候选域名并进行 DNS 初筛...", flush=True)
        candidates = list(generate_batch(args.strategy, args.batch_size))
        total_checked += len(candidates)

        # 1. 高速初筛
        dns_candidates = await run_discovery_round(
            candidates, resolver, concurrency=args.concurrency
        )
        print(f"  初筛完成: {len(candidates)} 个域名中发现 {len(dns_candidates)} 个潜在可用", flush=True)

        # 2. 权威 RDAP 复核
        if dns_candidates:
            print(f"  正在通过 Verisign 官方 RDAP 逐一精准验证...", flush=True)
            for cand in dns_candidates:
                if not running or len(found_domains) >= args.target:
                    break

                res = verify_rdap(cand)
                if res is True:
                    found_domains.append(cand)
                    print(f"  [+] [100%未注册] {cand:<14} (已找到 {len(found_domains)}/{args.target})", flush=True)
                    with open(args.output, "a", encoding="utf-8") as f:
                        f.write(f"{cand}\n")
                        f.flush()
                elif res is False:
                    print(f"  [-] [已被注册]   {cand:<14}", flush=True)
                else:
                    print(f"  [?] [查询超时]   {cand:<14}", flush=True)

                time.sleep(0.3)  # 防止被官方接口限频
        else:
            print("  本轮候选已全部被注册，继续下一轮生成...", flush=True)

        round_idx += 1

    print("\n" + "=" * 65)
    print(f"  挖掘结束！累计扫描候选: {total_checked} 个")
    print(f"  成功找到可用 5 字母 .com 域名: {len(found_domains)} 个")
    print(f"  结果已追加写入: {args.output}")
    print("=" * 65)


def main():
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    args = parse_args()
    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        print("\n已安全退出。")


if __name__ == "__main__":
    main()
