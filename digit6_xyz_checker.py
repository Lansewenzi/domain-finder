#!/usr/bin/env python3
"""
6位纯数字 .xyz 域名深度挖掘与权威检测工具 (6-Digit .xyz Domain Finder)
====================================================================
特点：
1. 权威双阶段核验架构：
   - 阶段一：aiodns 异步高并发 DNS 极速初筛（毫秒级跳过已建站/已配解析域名）
   - 阶段二：CentralNic (.xyz 官方根注册局) 权威 RDAP 接口复核（HTTP 404 确保 100% 未注册）
2. 丰富数字米市专属策略（品相规律、回文、顺子、吉利数、无4/无04、区间扫描等）
3. 智能品相评分与标签标注
"""

import argparse
import asyncio
import itertools
import os
import random
import re
import signal
import sys
import time
import urllib.error
import urllib.request
import aiodns

running = True


def signal_handler(sig, frame):
    global running
    print("\n[!] 收到停止指令，正在保存已发现的可用域名并安全退出...")
    running = False


signal.signal(signal.SIGINT, signal_handler)

LUCKY_DIGITS = ["1", "6", "8", "9"]
NO4_DIGITS = ["0", "1", "2", "3", "5", "6", "7", "8", "9"]
NO04_DIGITS = ["1", "2", "3", "5", "6", "7", "8", "9"]
ALL_DIGITS = [str(i) for i in range(10)]


def evaluate_digit_domain(num_str: str) -> tuple[int, list[str]]:
    """评估 6 位数字域名的品相价值与标签"""
    score = 50
    tags = []

    # 1. 顺子检测
    if num_str in ["012345", "123456", "234567", "345678", "456789"]:
        score += 50
        tags.append("正顺子")
    elif num_str in ["543210", "654321", "765432", "876543", "987654"]:
        score += 45
        tags.append("倒顺子")

    # 2. 连续重复 (豹子 / 炸弹)
    for d in ALL_DIGITS:
        if d * 6 == num_str:
            score += 60
            tags.append("6重叠(豹子)")
        elif d * 5 in num_str:
            score += 45
            tags.append("5连号")
        elif d * 4 in num_str:
            score += 30
            tags.append("4连号")

    # 3. 回文数检测
    if num_str == num_str[::-1] and "6重叠(豹子)" not in tags:
        score += 35
        tags.append("回文数(ABCCBA)")

    # 4. 经典规律结构
    a, b, c, d, e, f = list(num_str)
    if a == b and c == d and e == f and len(set(num_str)) >= 2:
        score += 30
        tags.append("AABBCC")
    elif a == b == c and d == e == f and a != d:
        score += 35
        tags.append("AAABBB")
    elif a == c == e and b == d == f and a != b:
        score += 35
        tags.append("ABABAB")
    elif a == d and b == e and c == f and len(set(num_str[:3])) >= 2:
        score += 30
        tags.append("ABCABC")
    elif a == b and c == d and a == f and b == e and a != c:
        score += 25
        tags.append("AABBAA")
    elif a == d == e and b == c == f and a != b:
        score += 25
        tags.append("ABBAAB")

    # 5. 吉利尾数
    if num_str.endswith("888"):
        score += 25
        tags.append("尾888")
    elif num_str.endswith("666"):
        score += 25
        tags.append("尾666")
    elif num_str.endswith("999"):
        score += 20
        tags.append("尾999")
    elif num_str.endswith("168"):
        score += 20
        tags.append("尾168(一路发)")
    elif num_str.endswith("518"):
        score += 15
        tags.append("尾518(我要发)")
    elif num_str.endswith("88") or num_str.endswith("66") or num_str.endswith("99"):
        score += 10
        tags.append("尾双吉")

    # 6. 无 4 / 无 04 溢价
    if "4" not in num_str:
        if "0" not in num_str:
            score += 15
            tags.append("无04(米市极品)")
        else:
            score += 8
            tags.append("无4")
    else:
        score -= 10

    # 7. 全吉利数字 (仅由 1, 6, 8, 9 组成)
    if all(ch in LUCKY_DIGITS for ch in num_str):
        score += 20
        tags.append("纯吉利数(1/6/8/9)")

    return score, tags


def gen_pattern_domain(allow_digits: list[str]) -> str:
    """生成具有规律结构的 6 位数字"""
    pattern_type = random.choice([
        "AABBCC", "AAABBB", "ABABAB", "ABCABC", "AABBAA", "ABBAAB",
        "AAAABB", "AABBBB", "AAABAA", "ABBBBA"
    ])
    d1 = random.choice(allow_digits)
    d2 = random.choice([x for x in allow_digits if x != d1])
    d3 = random.choice([x for x in allow_digits if x not in [d1, d2]]) if len(allow_digits) > 2 else d1

    if pattern_type == "AABBCC":
        return f"{d1}{d1}{d2}{d2}{d3}{d3}.xyz"
    elif pattern_type == "AAABBB":
        return f"{d1}{d1}{d1}{d2}{d2}{d2}.xyz"
    elif pattern_type == "ABABAB":
        return f"{d1}{d2}{d1}{d2}{d1}{d2}.xyz"
    elif pattern_type == "ABCABC":
        return f"{d1}{d2}{d3}{d1}{d2}{d3}.xyz"
    elif pattern_type == "AABBAA":
        return f"{d1}{d1}{d2}{d2}{d1}{d1}.xyz"
    elif pattern_type == "ABBAAB":
        return f"{d1}{d2}{d2}{d1}{d1}{d2}.xyz"
    elif pattern_type == "AAAABB":
        return f"{d1}{d1}{d1}{d1}{d2}{d2}.xyz"
    elif pattern_type == "AABBBB":
        return f"{d1}{d1}{d2}{d2}{d2}{d2}.xyz"
    elif pattern_type == "AAABAA":
        return f"{d1}{d1}{d1}{d2}{d1}{d1}.xyz"
    else:
        return f"{d1}{d2}{d2}{d2}{d2}{d1}.xyz"


def gen_palindrome_domain(allow_digits: list[str]) -> str:
    """生成 6 位回文数 (ABCCBA)"""
    a = random.choice(allow_digits)
    b = random.choice(allow_digits)
    c = random.choice(allow_digits)
    return f"{a}{b}{c}{c}{b}{a}.xyz"


def gen_lucky_domain(allow_digits: list[str]) -> str:
    """生成吉利数字/带吉利尾数的 6 位数"""
    if random.random() < 0.5:
        # 纯吉利数字组合 (1, 6, 8, 9)
        chars = [random.choice(LUCKY_DIGITS) for _ in range(6)]
        return f"{''.join(chars)}.xyz"
    else:
        # 前三位随机 (符合过滤条件) + 尾数 888 / 666 / 999 / 168 / 518
        prefix = "".join(random.choice(allow_digits) for _ in range(3))
        tail = random.choice(["888", "666", "999", "168", "518", "889", "668", "886"])
        return f"{prefix}{tail}.xyz"


def gen_straight_domain() -> str:
    """生成顺子或变体顺子"""
    straights = [
        "012345", "123456", "234567", "345678", "456789",
        "543210", "654321", "765432", "876543", "987654",
        # 局部顺子 + 叠字
        "123321", "678876", "123123", "456456", "789789"
    ]
    return f"{random.choice(straights)}.xyz"


def gen_date_domain() -> str:
    """生成年份/纪元数字 (如 202401 ~ 203012, 198001 ~ 200512)"""
    if random.random() < 0.6:
        # 近未来与当前纪元: 2020~2035 + 月份 01~12
        year = random.randint(2020, 2035)
        month = random.randint(1, 12)
        return f"{year}{month:02d}.xyz"
    else:
        # 生日怀旧年份: 1980~2010 + 月份
        year = random.randint(1980, 2010)
        month = random.randint(1, 12)
        return f"{year}{month:02d}.xyz"


def gen_random_digit_domain(allow_digits: list[str]) -> str:
    """纯随机生成 6 位数字"""
    return f"{''.join(random.choice(allow_digits) for _ in range(6))}.xyz"


def generate_candidate_batch(
    strategy: str,
    count: int,
    allow_digits: list[str],
    prefix: str = "",
    suffix: str = "",
    range_iter=None
) -> list[str]:
    """生成一批候选 6 位数字 .xyz 域名"""
    # 如果指定了具体数字区间
    if range_iter is not None:
        batch = []
        for _ in range(count):
            try:
                num = next(range_iter)
                num_str = f"{num:06d}"
                # 检查是否包含被禁用的数字
                if any(ch not in allow_digits for ch in num_str):
                    continue
                if prefix and not num_str.startswith(prefix):
                    continue
                if suffix and not num_str.endswith(suffix):
                    continue
                batch.append(f"{num_str}.xyz")
            except StopIteration:
                break
        return batch

    domains = set()
    attempts = 0
    max_attempts = count * 15

    while len(domains) < count and attempts < max_attempts:
        attempts += 1

        if strategy == "pattern":
            d = gen_pattern_domain(allow_digits)
        elif strategy == "palindrome":
            d = gen_palindrome_domain(allow_digits)
        elif strategy == "lucky":
            d = gen_lucky_domain(allow_digits)
        elif strategy == "straight":
            d = gen_straight_domain()
        elif strategy == "date":
            d = gen_date_domain()
        elif strategy == "no4":
            d = gen_random_digit_domain(NO4_DIGITS)
        elif strategy == "no04":
            d = gen_random_digit_domain(NO04_DIGITS)
        else:
            d = gen_random_digit_domain(allow_digits)

        num_str = d.replace(".xyz", "")

        # 检查是否满足 6 位纯数字
        if len(num_str) != 6 or not num_str.isdigit():
            continue

        # 检查允许的数字集合
        if any(ch not in allow_digits for ch in num_str):
            continue

        # 前缀与后缀过滤
        if prefix and not num_str.startswith(prefix):
            continue
        if suffix and not num_str.endswith(suffix):
            continue

        domains.add(d)

    return list(domains)


async def check_dns_worker(
    queue: asyncio.Queue,
    resolver: aiodns.DNSResolver,
    dns_candidates: list[str],
    progress: dict,
    total: int
):
    """DNS 异步并发初筛 Worker"""
    while running:
        try:
            domain = queue.get_nowait()
        except asyncio.QueueEmpty:
            break

        progress["checked"] += 1
        curr = progress["checked"]

        try:
            if hasattr(resolver, "query_dns"):
                await resolver.query_dns(domain, "NS")
            else:
                await resolver.query(domain, "NS")
        except aiodns.error.DNSError as e:
            # 错误码 4 = NXDOMAIN (域名无解析记录，大概率未注册)
            if len(e.args) > 0 and e.args[0] == 4:
                dns_candidates.append(domain)
        except Exception:
            pass
        finally:
            queue.task_done()

        if curr % 25 == 0 or curr == total:
            pct = curr * 100 // total if total > 0 else 0
            print(f"\r  [DNS初筛] 进度: {curr}/{total} ({pct}%) | 候选: {len(dns_candidates)}", end="", flush=True)

        await asyncio.sleep(0.002)


async def dns_filter_phase(domains: list[str], concurrency: int = 80) -> list[str]:
    """阶段一：DNS 高速初筛"""
    if not domains:
        return []

    queue = asyncio.Queue()
    for d in domains:
        queue.put_nowait(d)

    resolver = aiodns.DNSResolver(
        nameservers=["1.1.1.1", "8.8.8.8", "223.5.5.5", "119.29.29.29"],
        timeout=2.5,
        tries=2
    )

    dns_candidates = []
    progress = {"checked": 0}
    total = len(domains)

    tasks = [
        asyncio.create_task(check_dns_worker(queue, resolver, dns_candidates, progress, total))
        for _ in range(concurrency)
    ]
    await asyncio.gather(*tasks)
    print()
    return dns_candidates


def verify_with_centralnic_rdap(domain: str, timeout: float = 3.5) -> bool | None:
    """阶段二：通过 CentralNic (.xyz 根注册局) 官方 RDAP API 权威核验真伪"""
    url = f"https://rdap.centralnic.com/xyz/domain/{domain}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) XYZHunter/1.0",
            "Accept": "application/rdap+json, application/json"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout):
            return False  # 状态码 200，已被注册
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return True  # 状态码 404，100% 确认未注册
        return None
    except Exception:
        return None


async def run_checker(args):
    start_time = time.time()
    allow_digits = ALL_DIGITS

    # 过滤规则：无4 / 无04
    if args.no_04:
        allow_digits = NO04_DIGITS
        filter_desc = "无 0, 4 (纯 12356789)"
    elif args.no_4:
        allow_digits = NO4_DIGITS
        filter_desc = "无 4 (纯 012356789)"
    else:
        filter_desc = "全部数字 (0-9)"

    print("=" * 68)
    print("  6位纯数字 .xyz 域名深度挖掘与权威检测工具 (6-Digit .xyz Finder)")
    print("=" * 68)
    print(f"  挖掘策略: {args.strategy}")
    print(f"  数字过滤: {filter_desc}")
    if args.prefix:
        print(f"  固定前缀: {args.prefix}")
    if args.suffix:
        print(f"  固定后缀: {args.suffix}")
    if args.range:
        print(f"  区间扫描: {args.range[0]:06d} ~ {args.range[1]:06d}")
    print(f"  目标数量: 发现 {args.target} 个可用域名后停止")
    print(f"  保存文件: {args.output}")
    print("=" * 68)

    range_iter = None
    if args.range:
        range_iter = iter(range(args.range[0], args.range[1] + 1))

    total_scanned = 0
    verified_available = []
    round_no = 0

    with open(args.output, "a", encoding="utf-8") as f:
        f.write(f"\n# --- 扫描启动: {time.strftime('%Y-%m-%d %H:%M:%S')} (策略: {args.strategy}, 过滤: {filter_desc}) ---\n")

    while running and len(verified_available) < args.target:
        round_no += 1
        candidates = generate_candidate_batch(
            args.strategy,
            args.batch_size,
            allow_digits,
            prefix=args.prefix,
            suffix=args.suffix,
            range_iter=range_iter
        )

        if not candidates:
            print("[*] 候选池已无更多可用组合，扫描结束。")
            break

        total_scanned += len(candidates)
        print(f"\n[轮次 {round_no}] 正在对 {len(candidates)} 个候选域名进行 DNS 高速初筛...")
        dns_passed = await dns_filter_phase(candidates, concurrency=args.concurrency)

        print(f"  -> DNS 初筛发现 {len(dns_passed)} 个潜在可用域名，正在通过 CentralNic 官方 RDAP 复核...")

        for domain in dns_passed:
            if not running or len(verified_available) >= args.target:
                break

            num_str = domain.replace(".xyz", "")
            score, tags = evaluate_digit_domain(num_str)
            tag_str = f"[{' | '.join(tags)}]" if tags else ""

            is_avail = verify_with_centralnic_rdap(domain)

            if is_avail is True:
                verified_available.append(domain)
                print(f"  [+] [100%未注册] {domain:<12} (品相分: {score:2d}) {tag_str} ({len(verified_available)}/{args.target})")
                with open(args.output, "a", encoding="utf-8") as f:
                    f.write(f"{domain} (品相分: {score}) {tag_str}\n")
                    f.flush()
            elif is_avail is False:
                # 已注册但未配解析
                pass
            else:
                pass

            time.sleep(0.2)

    elapsed = time.time() - start_time
    print("\n" + "=" * 68)
    print(f"  扫描完成! 耗时: {elapsed:.2f} 秒 | 累计探测: {total_scanned} 个")
    print(f"  成功发掘 100% 确认未注册的 6D.xyz 域名: {len(verified_available)} 个")
    print(f"  结果已实时追加写入: {args.output}")
    print("=" * 68)


def main():
    parser = argparse.ArgumentParser(description="6位纯数字 .xyz 域名深度挖掘与检测工具")
    parser.add_argument(
        "--strategy",
        choices=["pattern", "palindrome", "lucky", "straight", "date", "no4", "no04", "random", "range"],
        default="pattern",
        help="生成策略: pattern(规律结构AABBCC/ABABAB等), palindrome(回文ABCCBA), lucky(吉利数/尾888/666), straight(顺子), date(年份日期), no4(无4), no04(无04), random(纯随机), range(区间连续扫描)"
    )
    parser.add_argument("--prefix", type=str, default="", help="指定前缀数字 (如 88, 666)")
    parser.add_argument("--suffix", type=str, default="", help="指定后缀数字 (如 888, 66)")
    parser.add_argument("--range", type=int, nargs=2, metavar=("START", "END"), help="指定扫描区间 (如 --range 100000 109999)")
    parser.add_argument("--no-4", action="store_true", help="严格排除数字 4 (米市硬通货)")
    parser.add_argument("--no-04", action="store_true", help="严格排除数字 0 和 4 (最高流通性)")
    parser.add_argument("--target", type=int, default=10, help="目标发现可用域名数量 (默认: 10)")
    parser.add_argument("--batch-size", type=int, default=200, help="每批次候选池大小 (默认: 200)")
    parser.add_argument("--concurrency", type=int, default=80, help="DNS 初筛并发数 (默认: 80)")
    parser.add_argument("--output", type=str, default="available_6d_xyz.txt", help="输出保存文件 (默认: available_6d_xyz.txt)")

    args = parser.parse_args()

    if args.range:
        args.strategy = "range"

    asyncio.run(run_checker(args))


if __name__ == "__main__":
    main()
