# OpenClaw 部署安全检测报告
检测时间: 2026-03-10 12:53:55

## 1. OpenClaw 版本与漏洞
当前版本: OpenClaw 2026.3.8 (3caab92)
最新版本: 2026.3.8
当前版本已经是最新版本。
检测到当前版本可能受影响的漏洞:
- 危害性: Moderate, 漏洞编号: GHSA-QJ22-XQJR-V83V, Telegram message_reaction authorization bypass allows unauthorized system-event injection (Affected: >= 2026.2.17)
- 危害性: High, 漏洞编号: GHSA-V6C6-VQQG-W888, Potential code execution via unsafe hook module path handling in Gateway (Affected: >= 2026.1.5)

## 2. 检查运行环境隔离性及容器逃逸风险：
检测到容器环境 (Docker/Kubernetes)
未检测到虚拟机环境
未检测到宿主机敏感目录挂载
[警告] 检测到容器逃逸风险设备：/proc/sysrq-trigger

## 3. 运行权限与 root 检查
openclaw 进程 PID=457 以 root 运行，存在风险。
openclaw 进程 PID=464 以 root 运行，存在风险。
openclaw 进程 PID=472 以 root 运行，存在风险。
openclaw 进程 PID=479 以 root 运行，存在风险。

## 4. 文件系统写权限范围
PID=457 可写目录: /etc, /var, /tmp, /root, /home, /usr/local, /opt
PID=457 对根目录有写权限，风险较高。
PID=464 可写目录: /etc, /var, /tmp, /root, /home, /usr/local, /opt
PID=464 对根目录有写权限，风险较高。
PID=472 可写目录: /etc, /var, /tmp, /root, /home, /usr/local, /opt
PID=472 对根目录有写权限，风险较高。
PID=479 可写目录: /etc, /var, /tmp, /root, /home, /usr/local, /opt
PID=479 对根目录有写权限，风险较高。

## 5. Gateway 端口 18789 暴露情况
监听记录: LISTEN 0      511        127.0.0.1:18789      0.0.0.0:*    users:(("openclaw-gatewa",pid=479,fd=22))
监听记录: LISTEN 0      511            [::1]:18789         [::]:*    users:(("openclaw-gatewa",pid=479,fd=23))
18789 仅监听本地地址。

## 6. WebSocket/HTTP API/RPC/Debug/Metrics 接口
HTTP 端口 18789 监听所有地址: LISTEN 0      511        127.0.0.1:18789      0.0.0.0:*    users:(("openclaw-gatewa",pid=479,fd=22))
WS 端口 18789 监听所有地址: LISTEN 0      511        127.0.0.1:18789      0.0.0.0:*    users:(("openclaw-gatewa",pid=479,fd=22))
HTTP 端口 18789 监听所有地址: LISTEN 0      511            [::1]:18789         [::]:*    users:(("openclaw-gatewa",pid=479,fd=23))
WS 端口 18789 监听所有地址: LISTEN 0      511            [::1]:18789         [::]:*    users:(("openclaw-gatewa",pid=479,fd=23))
配置文件中检测到疑似监听配置:
- /root/.openclaw/openclaw.json

## 7. AI Agent 行为权限审计
检测到 openclaw 主进程:
命令行: 457 openclaw                      
命令行: 464 openclaw                                                                     
命令行: 472 openclaw                      
命令行: 479 openclaw-gateway                                                             
未检测到 openclaw 子孙进程。

## 8. Prompt Injection 风险检测
检测到可能的 prompt 注入风险模式:
- /root/.openclaw/workspace/AGENTS.md 命中 (;|&&|\|\|)
- /root/.openclaw/workspace/AGENTS.md 命中 (;|&&|\|\|)

## 9. 技能来源可信性与哈希扫描
技能总数: 0, Git 来源: 0, 本地来源: 0
未检测到 Skill/MCP 目录文件。

## 10. 资源异常检测
高CPU进程快照(前10):
    479  6.8  0.0 openclaw-gatewa
    612  5.0  0.0 python3
    464  3.1  0.0 openclaw
    524  0.3  0.0 bash
    457  0.2  0.0 openclaw
    472  0.1  0.0 openclaw
      1  0.0  0.0 bash
     14  0.0  0.0 bash
    319  0.0  0.0 bash
    655  0.0  0.0 ps
未检测到明显对公网IP的连接。
未检测到近24小时大文件写入(仅扫描/var与/tmp)。

## 11. 日志与认证检测
最近登录记录:
wtmp begins Wed Nov 19 11:16:58 2025
SSH 失败尝试(近24h): 0

## 12. 配置明文凭据与环境变量泄露
配置文件中检测到疑似明文凭据:
- /root/.openclaw/openclaw.json 命中 generic_api_key
- /root/.openclaw/agents/main/agent/auth-profiles.json 命中 generic_api_key

## 13. 明文私钥/助记词泄露扫描(DLP)
检测到疑似明文敏感信息:
- /root/.openclaw/openclaw.json 命中 generic_api_key
- /root/.openclaw/openclaw.json.bak 命中 generic_api_key
- /root/.openclaw/completions/openclaw.bash 命中 generic_api_key
- /root/.openclaw/completions/openclaw.bash 命中 mnemonic_phrase
- /root/.openclaw/workspace/SOUL.md 命中 mnemonic_phrase
- /root/.openclaw/workspace/AGENTS.md 命中 mnemonic_phrase
- /root/.openclaw/workspace/HEARTBEAT.md 命中 mnemonic_phrase
- /root/.openclaw/workspace/TOOLS.md 命中 mnemonic_phrase
- /root/.openclaw/agents/main/agent/auth-profiles.json 命中 generic_api_key
- /root/openclaw_security/scannn.py 命中 mnemonic_phrase
- /root/openclaw_security/openclaw_scan/openclaw_vulnerabilities_1.csv 命中 mnemonic_phrase
- /root/openclaw_security/openclaw_scan/scan.py 命中 mnemonic_phrase
- /root/openclaw_security/openclaw-security/OpenClaw-Security-Practices-Guide.md 命中 mnemonic_phrase
- /root/openclaw_security/openclaw-security/README.md 命中 mnemonic_phrase
- /root/openclaw_security/openclaw-security/LICENSE 命中 mnemonic_phrase
- /root/openclaw_security/openclaw-security/docs/OpenClaw_Security_Analysis_2026.md 命中 mnemonic_phrase
- /root/openclaw_security/openclaw-security/tools/openclaw_security_audit.py 命中 mnemonic_phrase

=== 检测完成 ===