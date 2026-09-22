# 🌐 5-Letter .com Domain Finder (5位 .com 域名深度挖掘与权威检测器)

一个专为挖掘高商业价值、品牌品相优质的 **5 位纯英文字母 `.com` 域名** 设计的高性能自动化探测与真伪核验工具。

---

## 💡 为什么需要这个工具？

1. **资源极其紧缺**：5 位纯英文字母 `.com` 域名共有 $26^5 = 11,881,376$（近 1200 万）个可能，其中绝大多数有意义的英文单词、双音节发音、商业缩写和顺口组合已被抢注一空。
2. **人工盲猜命中率趋近于 0**：常见词根和自然发音词的注册率超过 99.5%，靠人工在注册商网站逐个搜索耗时且徒劳。
3. **传统 WHOIS 极易被风控与误报**：
   - 传统 Port 43 WHOIS 请求频繁会被注册局封禁 IP；
   - 仅依赖 DNS 查询会出现大量“虚假可用”（因为很多域名被注册后并没有配置 NS 解析记录，DNS 虽返回 NXDOMAIN，但实际上已被抢注）。
4. **权威双阶段精准复核**：本项目先通过异步 DNS 极速初筛，再直连 **Verisign（.com 官方管理机构）权威 RDAP API** 进行 100% 确认核验（以 HTTP 404 为准），彻底杜绝虚报误报。

---

## ⚡ 核心架构与原理

```
[ 策略候选池生成 ]
   │  (支持自然拼读 / SaaS / AI / 开发者 / 拼音等 15 种商业策略)
   ▼
[ 阶段一：aiodns 异步高并发 DNS 初筛 ] (50~120 并发)
   │  -> 毫秒级探测 NS / A 解析记录
   │  -> 极速跳过 90%+ 已建站或已配置解析的已注册域名
   ▼
[ 阶段二：Verisign 官方权威 RDAP 复核 ]
   │  -> 直连 https://rdap.verisign.com/com/v1/domain/{domain}
   │  -> 权威识别 HTTP 200 (已注册未配NS) 与 HTTP 404 (100% 未注册)
   ▼
[ 100% 可用域名输出 ]
   -> 终端高亮展示 & 实时持久化追加至 available_5letter.txt
```

---

## 🚀 快速上手

### 1. 环境准备
确保已安装 Python 3.9+，并安装异步 DNS 解析依赖：

```bash
pip install aiodns pycares
```

### 2. 基础运行
直接运行将默认使用 `cvcvc`（辅-元-辅-元-辅 自然拼读）策略挖掘 10 个未注册域名：

```bash
python letter5_checker.py
```

---

## 🎯 15 种内置商业品相挖掘策略 (`--strategy`)

根据不同业务定位与品牌风格，工具内置了 15 种精准生成策略：

| 策略参数 (`--strategy`) | 构词逻辑与模式 | 典型代表 / 品牌风格 | 商业应用场景 |
| :--- | :--- | :--- | :--- |
| **`vcvcv`** | 优雅元音开头双音节 (`V+C+V+C+V`) | `amiro`, `eliva`, `upewa`, `iyira` | 硅谷新一代初创、AI、健康科技、消费金融 |
| **`ify`** | 极品 SaaS 行动词根 (`2字母 + ify`) | `eoify`, `cpify`, `dkify`, `wnify` | 类 Spotify/Shopify 的企服软件、工具平台 |
| **`blend`** | 流动辅音高级双音节 (`C+V+[l/r/n/s/m]+C+V`) | `belsa`, `korva`, `dusfe`, `wirsu` | 类 Canva/Figma/Tesla 的现代国际化品牌 |
| **`developer`** | 极客/开发者基建 (`2字母 + dev/ops/app/bot`) | `uddev`, `vjdev`, `kqops`, `gyops` | 开发者工具、开源组件、SRE 监控、CloudOps |
| **`ai`** | 科技与 AI 品牌 (`xxxai` / `aixxx`) | `aijef`, `ainaw`, `aifub`, `ohjai` | AI 基础设施、Agent 平台、垂直模型应用 |
| **`startup`** | 高频初创词头 (`co/go/re/up/ex/in + 3字母`) | `exgir`, `refuy`, `gowuh`, `upboh` | 出海工具、企业级应用、性能套件 |
| **`tech`** | 硬核科技尾缀 (`-ix / -ex / -ox / -us / -or`) | `fihox`, `yecax`, `kuyix`, `yiwox` | 硬件、芯片、底层系统、安全网关 |
| **`latin`** | 现代科技/罗曼优雅结尾 (`-ia / -io / -ea / -ua`) | `copua`, `firua`, `dobua`, `ropua` | 罗曼语系美感、医疗生物、前沿科技 |
| **`cvcvc`** | 经典辅音+元音+辅音+元音+辅音 | `balex`, `rovik`, `gudib`, `pimif` | 通用易读品牌词、域名投资标配品相 |
| **`friendly`** | 高亲和力社交词头 (`my/we/ok/hi/be + 3字母`) | `mywuc`, `okfiv`, `wehob`, `higep` | 社交平台、创作者经济、社区网络 |
| **`palindrome`** | 5 字母回文艺术词 (`A-B-C-B-A`) | `rotur`, `senes`, `frerf`, `exvxe` | 极高艺术审美、设计工作室、奢品时尚 |
| **`pinyin`** | 5 字母中文拼音组合 (`2+3` 或 `3+2`) | `banli`, `daqiu`, `faiwu` | 国内项目、出海华人消费品牌 |
| **`pattern`** | 结构韵律词 (`ABABA`, `AABAA`, `ABBAB`) | `fjjjf`, `ppyyp`, `mrrmr` | 强视觉记忆度、密码极客、短链接 |
| **`suffix`** | 3 字母 + 常用科技词缀 (`-ly / -er / -on`) | `nkbly`, `qvoon`, `cteio` | 现代科技类企业 |
| **`random`** | 5 纯随机英文字母 | `a-z` 任意 5 位 | 探索全盘剩余长尾空间 |

---

## 🛠️ 常用挖掘命令范例

#### 1. 挖掘硅谷 SaaS `**ify.com` 风格域名（找到 5 个停止）
```bash
python letter5_checker.py --strategy ify --target 5
```

#### 2. 挖掘 Canva/Figma 风格的现代流动双音节品牌词
```bash
python letter5_checker.py --strategy blend --target 8
```

#### 3. 挖掘元音开头极优美的品牌词（提高并发到 80）
```bash
python letter5_checker.py --strategy vcvcv --target 10 --concurrency 80
```

#### 4. 挖掘开发者工具类域名 (`**dev.com`, `**ops.com`)
```bash
python letter5_checker.py --strategy developer --target 6
```

#### 5. 自定义保存文件
```bash
python letter5_checker.py --strategy tech --target 10 --output my_tech_domains.txt
```

---

## 📋 命令行参数详解

```bash
usage: letter5_checker.py [-h] [--strategy STRATEGY] [--target TARGET]
                          [--batch-size BATCH_SIZE] [--concurrency CONCURRENCY]
                          [--output OUTPUT]

参数说明:
  -h, --help            显示帮助信息并退出
  --strategy STRATEGY   生成策略选择 (默认: cvcvc)
                        可选: cvcvc, ify, blend, vcvcv, startup, developer,
                              ai, tech, latin, friendly, palindrome, pinyin,
                              pattern, suffix, random
  --target TARGET       目标发现数量，达到该数量后自动停止退出 (默认: 10)
  --batch-size BATCH_SIZE
                        每批次生成的候选域名池大小 (默认: 200)
  --concurrency CONCURRENCY
                        DNS 异步并发数 (默认: 50，网络良好可设为 80~120)
  --output OUTPUT       可用域名持久化保存文件 (默认: available_5letter.txt)
```

---

## 📂 结果归档格式说明

所有经由 Verisign 权威核验可用的域名，会自动以追加方式保存在 `available_5letter.txt` 中，并带有每次扫描的启动时间与策略标签：

```text
# --- 扫描启动: 2026-09-22 09:35:25 (策略: blend) ---
dusfe.com
nosru.com
wirsu.com
rarku.com
wusdi.com

# --- 扫描启动: 2026-09-22 09:41:45 (策略: vcvcv) ---
iyira.com
upewa.com
efove.com
uvafi.com
```

---

## ⚠️ 常见问题与注意事项

1. **为什么查出来的域名建议尽快注册？**
   5 位 `.com` 属于全球高流通资产，尤其是带 `ai`、`dev`、`ify` 等优质词根的域名，米农与创业团队每天都在持续扫盘，遇到心仪的域名建议尽早在 Namecheap、Cloudflare、阿里云等主流平台锁定。
2. **RDAP 查询速率限制**：
   Verisign 官方 RDAP 接口非常稳定，但为保护网络环境与防止单 IP 被暂时限速，脚本在每个候选复核之间设置了微小的休眠时间（0.2s~0.3s），建议保持默认设置。
3. **安全中断**：
   随时可以通过 `Ctrl + C` 中断扫描，程序会安全捕获中断信号并确保已找到的域名完整落盘。
