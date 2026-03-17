# OpenClaw Skill Audit Scanners Technical Overview

这份文档用于梳理 `tools/openclaw-skill-audit` 目录中几个主要恶意 skill 扫描工具的技术路线。

目标不是做功能列表，而是回答三个问题：

1. 每个工具到底在扫什么
2. 它的核心检测原理是什么
3. 它和其他工具相比强弱点在哪里

## Scanner Categories

这个目录里的项目并不全是同一种工具，大体可以分成四类：

- 本地静态扫描器
- 多层联合审计器
- 主机资产发现/云校验工具
- 基准数据集与研究流水线

## High-Level Comparison

| Tool | Type | Main Technique | Dynamic Execution | External API Dependence | Best Use Case |
|---|---|---|---|---|---|
| `clawscan` | Local static scanner | Multi-analyzer static pattern scan + combination scoring | No | No | 安装前快速审查 OpenClaw/Claude skill |
| `skill-security-audit` | Portable static scanner | IOC matching + multi-detector heuristics + confidence scoring | No | No | 零依赖快速筛恶意 skill |
| `skill-security-scan` | Configurable rule engine | YAML rules + regex/rule classes + report generation | No | No | 需要可配置规则、HTML/JSON 报告 |
| `skills_security_audit` | Multi-layer auditor | Regex + AST + prompt analysis + runtime hooks + LLM | Yes | Optional | 深度审计单个 skill/repo |
| `skill-scanner` | Enterprise / extensible framework | Static + YARA + taint + behavioral + LLM + VT + meta analysis | Optional | Optional | 平台级、可扩展、多引擎扫描 |
| `agent-scan` | Endpoint inventory + verification | Local discovery + local checks + remote verification API | Partial | Yes | 企业终端 agent / MCP / skills 盘点 |
| `caterpillar` | Pre-install scanner | Offline patterns + OpenAI/Alice LLM modes | No | Optional | 安装前打分、轻量审查 |
| `MaliciousAgentSkillsBench` | Research pipeline | Static scan + AI audit + Docker sandbox execution | Yes | Yes | 学术评测、研究复现 |
| `skill-sentinel` | Skill-form security workflow | Threat-category-driven audit guidance | Unclear | Unclear | 把扫描能力包装成 skill 交付 |

## Tool-by-Tool Technical Breakdown

### 1. `clawscan`

Relevant files:

- [`clawscan/src/scanner.js`](/Users/shawn/Desktop/openclaw-watchboard/tools/openclaw-skill-audit/clawscan/src/scanner.js)
- [`clawscan/README.md`](/Users/shawn/Desktop/openclaw-watchboard/tools/openclaw-skill-audit/clawscan/README.md)

Core idea:

- 通过多个专用 analyzer 对 skill 目录做静态扫描
- 每个 analyzer 针对一类风险
- 最后不是简单叠加条目数，而是做“危险组合加权”

Main analyzers:

- `SKILL.md` analysis
- script analysis
- network analysis
- credentials analysis
- obfuscation detection
- typosquat detection
- prompt injection detection

Core techniques:

- 正则/模式匹配识别高危行为
- blocklist 检测恶意域名、IP、webhook、数据外传基础设施
- 组合风险评分

What makes it different:

- 它最有特色的地方不是单条规则，而是组合判断
- 例如“凭证访问 + webhook”“prompt injection + exfiltration”“download + execute”
- 这种思路比传统按条数计分更接近真实攻击链

Strengths:

- 本地运行
- 快
- 对 OpenClaw / Claude skill 场景贴近
- 可解释性强

Weaknesses:

- 纯静态
- 遇到强混淆、条件触发、运行时行为隐藏时容易漏报

### 2. `skill-security-audit`

Relevant files:

- [`skill-security-audit/scripts/skill_audit.py`](/Users/shawn/Desktop/openclaw-watchboard/tools/openclaw-skill-audit/skill-security-audit/scripts/skill_audit.py)
- [`skill-security-audit/README.md`](/Users/shawn/Desktop/openclaw-watchboard/tools/openclaw-skill-audit/skill-security-audit/README.md)
- [`skill-security-audit/scripts/ioc_database.json`](/Users/shawn/Desktop/openclaw-watchboard/tools/openclaw-skill-audit/skill-security-audit/scripts/ioc_database.json)

Core idea:

- 用一组明确的 detector 扫描技能文件
- 同时结合 IOC 数据库提高对已知恶意基础设施的命中率
- 每条 finding 带 severity 和 confidence

Core techniques:

- Download-and-execute pattern detection
- IOC matching
- Credential theft pattern detection
- Persistence pattern detection
- Privilege escalation pattern detection
- Base64 / entropy / hidden char detection
- Social engineering naming heuristics

What makes it different:

- 零依赖、纯 Python stdlib
- IOC 能力很实用
- 对“已知恶意样本家族”和“已知恶意基础设施”命中更准

Strengths:

- 易落地
- 可移植
- 运行门槛低
- 适合做日常快速筛查

Weaknesses:

- 本质仍然是规则/IOC 驱动
- 对未知攻击链、复杂语义意图判断能力有限

### 3. `skill-security-scan`

Relevant files:

- [`skill-security-scan/src/cli.py`](/Users/shawn/Desktop/openclaw-watchboard/tools/openclaw-skill-audit/skill-security-scan/src/cli.py)
- [`skill-security-scan/src/rules_factory.py`](/Users/shawn/Desktop/openclaw-watchboard/tools/openclaw-skill-audit/skill-security-scan/src/rules_factory.py)
- [`skill-security-scan/src/scanner/analyzer.py`](/Users/shawn/Desktop/openclaw-watchboard/tools/openclaw-skill-audit/skill-security-scan/src/scanner/analyzer.py)
- [`skill-security-scan/config/rules.yaml`](/Users/shawn/Desktop/openclaw-watchboard/tools/openclaw-skill-audit/skill-security-scan/config/rules.yaml)

Core idea:

- 把扫描器设计成一个可配置规则引擎
- 规则由 YAML 配置驱动
- 运行时通过规则工厂映射到具体 Rule 类

Core techniques:

- Regex-based content matching
- Rule factory pattern
- Whitelist filtering
- Severity-based filtering
- Console / JSON / HTML reporting

Main detection families:

- network
- file operations
- command execution
- code injection / backdoor
- dependency abuse
- obfuscation

What makes it different:

- 不是把威胁逻辑都硬编码在一个脚本里
- 更像一个传统安全产品里的“规则配置 + 执行引擎”
- 适合后续自己持续扩充规则

Strengths:

- 规则易维护
- 中文输出友好
- 报告形式完整
- 适合作为企业内部规则扫描器雏形

Weaknesses:

- 深度主要取决于规则覆盖
- 缺少 AST / 动态 / LLM 层补充时，上限有限

### 4. `skills_security_audit`

Relevant files:

- [`skills_security_audit/scanners/static.py`](/Users/shawn/Desktop/openclaw-watchboard/tools/openclaw-skill-audit/skills_security_audit/scanners/static.py)
- [`skills_security_audit/scanners/ast_analysis.py`](/Users/shawn/Desktop/openclaw-watchboard/tools/openclaw-skill-audit/skills_security_audit/scanners/ast_analysis.py)
- [`skills_security_audit/scanners/prompt_analysis.py`](/Users/shawn/Desktop/openclaw-watchboard/tools/openclaw-skill-audit/skills_security_audit/scanners/prompt_analysis.py)
- [`skills_security_audit/scanners/runtime_scanner.py`](/Users/shawn/Desktop/openclaw-watchboard/tools/openclaw-skill-audit/skills_security_audit/scanners/runtime_scanner.py)
- [`skills_security_audit/scanners/skills_md.py`](/Users/shawn/Desktop/openclaw-watchboard/tools/openclaw-skill-audit/skills_security_audit/scanners/skills_md.py)
- [`skills_security_audit/README.md`](/Users/shawn/Desktop/openclaw-watchboard/tools/openclaw-skill-audit/skills_security_audit/README.md)

Core idea:

- 把 skill 审计拆成多个层次
- 每一层解决不同维度的问题
- 最终把静态、运行时和 LLM 结果结合起来判断

Core techniques:

- Regex static scan
- AST dangerous import / call scan
- Prompt logic analysis
- Prompt fuzzing
- Runtime sandbox hooks
- LLM intent classification

Runtime monitoring details:

- hook `open`
- hook `os.system`
- hook `socket`
- hook `subprocess`
- hook `Path.*`
- hook `sys.exit`
- hook `import`

What makes it different:

- 在这里面它是少数真正做“运行时 hook 监控”的
- 这意味着它不只是看文本长什么样，还看执行时会碰什么能力

Strengths:

- 分层清晰
- 静态与动态互补
- 对隐藏行为识别能力更强

Weaknesses:

- 动态执行复杂度高
- 慢
- 容易引入运行环境差异

### 5. `skill-scanner`

Relevant files:

- [`skill-scanner/README.md`](/Users/shawn/Desktop/openclaw-watchboard/tools/openclaw-skill-audit/skill-scanner/README.md)
- [`skill-scanner/skill_scanner/cli/cli.py`](/Users/shawn/Desktop/openclaw-watchboard/tools/openclaw-skill-audit/skill-scanner/skill_scanner/cli/cli.py)
- [`skill-scanner/skill_scanner/api/router.py`](/Users/shawn/Desktop/openclaw-watchboard/tools/openclaw-skill-audit/skill-scanner/skill_scanner/api/router.py)
- [`skill-scanner/skill_scanner/threats/threats.py`](/Users/shawn/Desktop/openclaw-watchboard/tools/openclaw-skill-audit/skill-scanner/skill_scanner/threats/threats.py)

Core idea:

- 提供一个企业级、可扩展、 analyzer-driven 的 scanning framework
- 多个 analyzer 可以按策略组合启用
- 最终结果还能映射到统一 taxonomy

Documented analyzer families:

- Static
- Bytecode
- Pipeline taint
- Behavioral
- LLM
- Meta
- VirusTotal
- Trigger / AI Defense

Core techniques:

- YARA / static signatures
- Python bytecode integrity verification
- Shell pipeline taint analysis
- Behavioral/dataflow analysis
- LLM semantic analysis
- Meta-analysis for false positive filtering
- VirusTotal hash / upload-based malware checks
- Threat taxonomy mapping

What makes it different:

- 技术栈最全
- 工程化最强
- 不只是“扫出问题”，还试图把问题映射到统一威胁模型

Strengths:

- 扩展性强
- 适合平台级集成
- 既能本地跑，也能做 API 服务
- 输出适合自动化集成

Weaknesses:

- 依赖复杂
- 上手成本高
- 不适合最轻量的安装前快速扫描

### 6. `agent-scan`

Relevant files:

- [`agent-scan/README.md`](/Users/shawn/Desktop/openclaw-watchboard/tools/openclaw-skill-audit/agent-scan/README.md)

Core idea:

- 不只扫一个 skill，而是先发现整台机器上的 agent 组件
- 然后对 skills / MCP servers / agent configs 做安全验证
- 部分能力依赖远端 Snyk Agent Scan API

Core techniques:

- 本机 agent config auto-discovery
- skills / MCP inventory
- local validation
- remote verification API

What makes it different:

- 重点是“发现”和“终端盘点”
- 更像企业安全产品的一部分，而不是单机代码审计器

Strengths:

- 很适合企业终端规模化盘点
- 能统一覆盖 skills + MCP + agents

Weaknesses:

- 对云 API 有依赖
- 不是最透明的纯本地扫描路径

### 7. `caterpillar`

Relevant files:

- [`caterpillar/README.md`](/Users/shawn/Desktop/openclaw-watchboard/tools/openclaw-skill-audit/caterpillar/README.md)

Core idea:

- 提供多种分析模式
- 让用户在速度、隐私、准确度之间取平衡

Modes:

- `offline`: 本地规则扫描
- `openai`: 使用用户自己的 OpenAI key 做 LLM 审计
- `alice`: 使用自家后端 API 做完整分析

Core techniques:

- Offline pattern matching
- LLM-based semantic analysis
- Risk grading / scoring

What makes it different:

- 它不是单一检测引擎，而是“多模式切换”
- 安装前给 A-F 评分这点更贴近用户决策

Strengths:

- 使用门槛低
- 模式切换实用

Weaknesses:

- 离线模式深度有限
- 云模式透明度和成本受限于外部服务

### 8. `MaliciousAgentSkillsBench`

Relevant files:

- [`MaliciousAgentSkillsBench/README.md`](/Users/shawn/Desktop/openclaw-watchboard/tools/openclaw-skill-audit/MaliciousAgentSkillsBench/README.md)

Core idea:

- 不是单点扫描器
- 而是一套针对恶意 skill 的 benchmark dataset + analysis pipeline

Pipeline:

- crawl
- mapping
- download
- static scan
- AI audit
- dynamic execution in Docker sandbox

Core techniques:

- Large-scale skill crawling
- Static rule-based scanning
- AI-powered deep audit
- Docker sandbox execution
- Runtime monitoring / tracing

What makes it different:

- 学术研究属性最强
- 目标是“评测与理解恶意 skill”，不是单纯安装前阻断

Strengths:

- 适合论文、基准测试、复现实验

Weaknesses:

- 成本高
- 不适合轻量日常使用

### 9. `skill-sentinel`

Relevant files:

- [`skill-sentinel/README.md`](/Users/shawn/Desktop/openclaw-watchboard/tools/openclaw-skill-audit/skill-sentinel/README.md)

Core idea:

- 把安全扫描能力本身包装成一个 skill
- 以 threat categories 方式组织审计输出

Threat model:

- Data exfiltration
- Prompt injection
- Remote code execution
- Credential harvesting
- Obfuscated payloads
- Privilege escalation
- Supply chain compromise
- Social engineering

What makes it different:

- 更像“技能化的安全审计工作流”
- 适合作为 agent 自身 skill 使用
- 不像传统 CLI 那样是成熟代码扫描框架

## Technical Axes Comparison

| Technique | Representative Tools | Principle | Strength | Weakness |
|---|---|---|---|---|
| Regex / heuristic matching | `clawscan`, `skill-security-audit`, `skill-security-scan` | 匹配已知危险模式 | 快、可解释 | 易被语义绕过 |
| AST analysis | `skills_security_audit`, `skill-scanner` | 解析语法树，识别危险调用/import/逻辑 | 比 regex 稳定 | 只对可解析代码有效 |
| Prompt / SKILL.md analysis | `clawscan`, `skills_security_audit`, `agent-scan` | 检测提示词注入、社工和越权指令 | 非常贴合 skill 攻击面 | 复杂语境下容易模糊 |
| Combination scoring | `clawscan` | 多信号联合推断攻击链 | 更贴近真实恶意链路 | 规则设计复杂 |
| IOC matching | `skill-security-audit` | 命中恶意 IP/domain/hash/url | 对已知家族命中准 | 对新样本无能为力 |
| Runtime monitoring | `skills_security_audit`, `MaliciousAgentSkillsBench` | 实际执行并 hook 文件/命令/网络 | 能发现静态看不到的行为 | 慢、复杂、有环境噪音 |
| LLM semantic analysis | `caterpillar`, `skill-scanner`, `skills_security_audit` | 从语义上推断意图和潜在恶意性 | 擅长复杂语义/社工 | 成本高、稳定性较差 |
| External verification / VT / SaaS | `agent-scan`, `skill-scanner` | 接外部安全服务补充检测 | 情报更新快 | 对外部依赖强 |

## Practical Recommendation

如果目标是“本地快速初筛”：

- 优先看 `clawscan`
- 或 `skill-security-audit`
- 或 `skill-security-scan`

如果目标是“深度分析单个 skill/repo”：

- 优先看 `skills_security_audit`
- 或 `skill-scanner`

如果目标是“研究数据集/复现实验”：

- 优先看 `MaliciousAgentSkillsBench`

如果目标是“企业终端统一盘点”：

- 优先看 `agent-scan`

## Bottom Line

这几个工具最大的区别不是“发现了哪些恶意行为”，而是“靠什么技术相信它发现的是真的”：

- `clawscan` 相信规则组合
- `skill-security-audit` 相信 detector + IOC
- `skill-security-scan` 相信规则引擎
- `skills_security_audit` 相信静态 + 动态 + LLM 联合
- `skill-scanner` 相信多 analyzer 框架化组合
- `agent-scan` 相信本机发现 + 云校验
- `MaliciousAgentSkillsBench` 相信完整研究流水线

所以后续如果要做你自己的 `openclaw-skill-audit`，最现实的方向不是“选一个完全替代其他所有工具”，而是明确：

- 哪些场景用轻量静态扫描
- 哪些场景用深度审计
- 哪些场景只需要批量盘点
