# openclaw-scan

`openclaw-scan` 是面向 OpenClaw 部署节点的本地安全检测工具，用于从主机侧快速审计版本漏洞、网络暴露、运行权限、Prompt 风险、Skill 来源可信性以及明文凭据泄露。

## 研发信息

- 联合研发单位：华中科技大学网络空间安全学院 × 武汉金银湖实验室
- 研究团队：SecurityPRIDE 研究团队
- 作者：王浩宇（haoyuwang@hust.edu.cn）、侯心怡（xinyihou@hust.edu.cn）、王申奥（shenaowang@hust.edu.cn）
- 平台主页：OpenClaw Watchboard

## 功能范围

- OpenClaw 版本识别与漏洞库匹配
- 容器隔离、端口监听与本地服务暴露检查
- OpenClaw 进程权限与文件系统写权限审计
- Prompt Injection 风险模式扫描
- Skill/MCP 来源与危险函数检查
- 明文密钥、Token、私钥与助记词泄露扫描
- Markdown 报告与 JSON 摘要输出

## 安装方式

### 直接运行

```bash
python3 scan.py
```

### 作为命令行工具安装

```bash
pip install .
openclaw-scan --help
```

## 命令示例

```bash
openclaw-scan
openclaw-scan --quiet
openclaw-scan --report-path ./reports/openclaw_security_report.md --summary-path ./reports/openclaw_security_report.json
```

## 输出文件

- `openclaw_security_report.md`
- `openclaw_security_report.json`

## 依赖

- Python 3.9+
- 可选依赖：`websocket-client`

如果目标主机未安装 `ss`，工具会尝试提示安装 `iproute2`。
