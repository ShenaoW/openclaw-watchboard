import { PageContainer, ProList } from "@ant-design/pro-components";
import {
  Alert,
  Card,
  Col,
  Descriptions,
  Divider,
  Progress,
  Row,
  Space,
  Tag,
  Timeline,
  Typography,
} from "antd";
import { useMemo, useState } from "react";
import { LinkOutlined } from "@ant-design/icons";
import { history, useLocation } from "@umijs/max";

const { Paragraph, Text, Link } = Typography;

const riskTabList = [
  { tab: "Top 10 风险", key: "/risks/top10" },
  { tab: "已披露漏洞", key: "/risks/vulnerabilities" },
];

type Severity = "Critical" | "High" | "Medium";

interface TopRisk {
  id: string;
  rank: number;
  title: string;
  subtitle: string;
  severity: Severity;
  priority: number;
  category: string;
  summary: string;
  attackChain: string[];
  impact: string[];
  mitigation: string[];
  keyFacts: string[];
}

interface RiskUpdate {
  date: string;
  title: string;
  summary: string;
  riskFocus: string;
  source: string;
  url: string;
}

const severityColorMap: Record<Severity, string> = {
  Critical: "red",
  High: "orange",
  Medium: "gold",
};

const severityLabelMap: Record<Severity, string> = {
  Critical: "严重",
  High: "高危",
  Medium: "中危",
};

const topRisks: TopRisk[] = [
  {
    id: "prompt-injection",
    rank: 1,
    title: "Prompt Injection",
    subtitle: "提示注入攻击",
    severity: "Critical",
    priority: 9.9,
    category: "输入信任边界",
    summary:
      "攻击者把恶意指令混入网页、邮件、文档或聊天内容中，诱导 Agent 偏离原始任务，转而读取本地文件、执行工具调用或泄露敏感凭据。",
    attackChain: [
      "恶意网页/邮件/文档",
      "Agent 自动读取外部内容",
      "提示被覆盖或串改",
      "触发工具调用/敏感数据外泄",
    ],
    impact: [
      "读取本地文件和历史会话",
      "泄露 API Key、Cookie、SSH 配置",
      "诱导执行危险命令或外联请求",
    ],
    mitigation: [
      "对外部内容做上下文隔离",
      "高风险工具强制二次确认",
      "最小化默认工具权限并记录审计日志",
    ],
    keyFacts: [
      "属于 Agent 原生风险，不是单一 CVE 可修复问题",
      "只要模型会解析外部内容，这类攻击就长期存在",
    ],
  },
  {
    id: "malicious-skills",
    rank: 2,
    title: "Malicious Skills",
    subtitle: "恶意 Skills / 插件供应链攻击",
    severity: "Critical",
    priority: 9.7,
    category: "技能生态供应链",
    summary:
      "ClawHub 市场中的第三方 Skill 具备真实执行能力，一旦被伪装成常用工具，用户安装后就可能直接落地窃密、木马或钱包盗取逻辑。",
    attackChain: [
      "伪装成常用 Skill",
      "用户安装并执行前置脚本",
      "本地下载恶意二进制/脚本",
      "窃取浏览器数据、密码或钱包",
    ],
    impact: [
      "窃取浏览器密码与会话",
      "盗取加密货币钱包与私钥",
      "通过 Skill 成为主机侧持久化入口",
    ],
    mitigation: [
      "对 Skill 做代码审计和来源验证",
      "禁用手动执行来源不明前置命令",
      "只允许白名单仓库和签名发行源",
    ],
    keyFacts: [
      "公开研究提到 2,857 个技能中发现 341 个恶意样本",
      "部分恶意 Skill 曾进入推荐位，风险并非边缘案例",
    ],
  },
  {
    id: "skill-dependency-injection",
    rank: 3,
    title: "Skill Dependency Injection",
    subtitle: "Skill 依赖注入",
    severity: "High",
    priority: 9.3,
    category: "运行时依赖链",
    summary:
      "不少 Skill 会在运行时拉取远程脚本、说明文件或第三方依赖，等于把控制权交给外部服务器，形成类 npm / PyPI 的二次供应链风险。",
    attackChain: [
      "Skill 安装或运行时拉取远程资源",
      "资源内容被替换或投毒",
      "本地执行 source/curl/bash 类命令",
      "扩展为 RCE 或持久化",
    ],
    impact: [
      "远程代码执行",
      "执行环境被静默替换",
      "第三方基础设施失陷后批量中招",
    ],
    mitigation: [
      "禁止运行时下载并执行脚本",
      "锁定版本和校验哈希",
      "将第三方依赖转为本地审计制品",
    ],
    keyFacts: [
      "研究指出约 2.9% 的技能会远程执行代码",
      "约 17.7% 的技能会加载不可信第三方内容",
    ],
  },
  {
    id: "tool-privilege-escalation",
    rank: 4,
    title: "Tool Privilege Escalation",
    subtitle: "工具权限滥用",
    severity: "Critical",
    priority: 9.4,
    category: "工具权限控制",
    summary:
      "一旦 Agent 已连接文件系统、Shell、浏览器和网络接口，任何 prompt injection 或恶意 Skill 都可能把这些工具组合成“本地超级后门”。",
    attackChain: [
      "攻击控制模型输出",
      "调用高权限工具",
      "读取本地敏感资产",
      "横向访问浏览器/API/云端账号",
    ],
    impact: [
      "读取 ~/.ssh、浏览器 Cookie、系统配置",
      "借用本地身份继续攻击内网或云资源",
      "把多种工具串成完整攻击链",
    ],
    mitigation: [
      "默认关闭高风险工具",
      "把文件、命令、网络权限分离",
      "按任务粒度实施最小权限授权",
    ],
    keyFacts: [
      "Agent 的危险不在单个工具，而在多工具组合后的自动化能力",
      "高权限执行模式会显著放大任何前置失陷的后果",
    ],
  },
  {
    id: "clawjacked",
    rank: 5,
    title: "ClawJacked",
    subtitle: "WebSocket 控制接口劫持",
    severity: "Critical",
    priority: 9.6,
    category: "本地控制面暴露",
    summary:
      "OpenClaw 本地 WebSocket/Gateway 控制面如果使用弱口令或认证设计不当，恶意网页脚本即可尝试接管本地 Agent 会话与设备权限。",
    attackChain: [
      "用户访问恶意网页",
      "浏览器脚本连接 localhost 网关",
      "弱认证/逻辑缺陷被利用",
      "获取 Agent 控制权与设备数据",
    ],
    impact: [
      "接管 Agent 会话",
      "枚举连接设备和日志",
      "读取配置数据并进一步操控执行流",
    ],
    mitigation: [
      "立即升级到已修复版本",
      "使用强 token 并限制本地控制面暴露",
      "对 localhost 控制接口增加来源校验",
    ],
    keyFacts: [
      "Oasis Security 于 2026-02-26 公开了 ClawJacked",
      "公开报道显示官方在 24 小时内推送修复，建议至少升级到 2026.2.25",
    ],
  },
  {
    id: "command-injection",
    rank: 6,
    title: "Command Injection / RCE",
    subtitle: "命令注入与远程代码执行",
    severity: "Critical",
    priority: 9.5,
    category: "命令执行面",
    summary:
      "多个公开漏洞表明 OpenClaw 控制流、命令拼接和连接参数处理曾出现一键 RCE、命令注入等问题，浏览恶意页面即可触发失陷。",
    attackChain: [
      "恶意链接或路径参数",
      "窃取 token / 注入命令",
      "控制 Agent 执行接口",
      "在宿主机上执行任意命令",
    ],
    impact: [
      "主机级远程代码执行",
      "接管会话与代理能力",
      "后续可下载其他 payload 或横向移动",
    ],
    mitigation: [
      "升级到包含修复的版本",
      "关闭不必要的执行路径和自动批准",
      "对所有外部可控参数做白名单校验",
    ],
    keyFacts: [
      "公开资料提到 CVE-2026-25253 与 CVE-2026-25157",
      "这类问题直接关联“看一个页面就中招”的高危场景",
    ],
  },
  {
    id: "sandbox-hash-collision",
    rank: 7,
    title: "Sandbox Hash Collision",
    subtitle: "容器隔离漏洞",
    severity: "High",
    priority: 8.8,
    category: "隔离与沙箱",
    summary:
      "沙箱实例的哈希计算如果没有正确覆盖顺序敏感参数，可能导致应当重建的容器被复用，从而出现隔离绕过或脏状态继承。",
    attackChain: [
      "构造特殊配置数组",
      "哈希碰撞导致命中旧沙箱",
      "旧状态被保留",
      "借此绕过隔离边界",
    ],
    impact: [
      "容器环境污染与状态复用",
      "隔离边界弱化",
      "为进一步命令执行创造条件",
    ],
    mitigation: [
      "修复哈希逻辑并强制重建隔离环境",
      "高风险操作使用一次性沙箱",
      "对沙箱元数据做完整性校验",
    ],
    keyFacts: [
      "该类问题的危险在于“看起来有沙箱，实际没有重新隔离”",
      "与 RCE 组合后会把影响面从单次任务扩大到持续环境",
    ],
  },
  {
    id: "token-drain",
    rank: 8,
    title: "Token Drain / Resource Abuse",
    subtitle: "Token 滥用与资源消耗",
    severity: "High",
    priority: 8.6,
    category: "成本与可用性",
    summary:
      "恶意 Skill 或提示可以诱导 Agent 反复调用工具和模型，制造高频循环任务，快速放大 token 消耗、API 成本和执行队列压力。",
    attackChain: [
      "恶意提示诱导循环调用",
      "工具/模型反复执行",
      "token 与 API 费用暴涨",
      "资源被耗尽影响正常任务",
    ],
    impact: ["费用异常上涨", "任务队列阻塞", "监控不足时会演变成慢性 DoS"],
    mitigation: [
      "为 token、调用次数、并发设置硬阈值",
      "加入循环检测与预算中断",
      "对异常消耗做告警和自动熔断",
    ],
    keyFacts: [
      "公开研究提到攻击可使 token 消耗放大 6 到 9 倍",
      "这类攻击不一定取数据，但会直接打击稳定性和成本",
    ],
  },
  {
    id: "fake-installer",
    rank: 9,
    title: "Fake Installer / Supply-Chain Malware",
    subtitle: "假安装包与投毒供应链",
    severity: "High",
    priority: 8.9,
    category: "分发链风险",
    summary:
      "随着 OpenClaw 爆火，攻击者开始投放假 GitHub 仓库、搜索广告和恶意安装包，诱导用户安装带有 infostealer 的伪客户端。",
    attackChain: [
      "搜索广告/仿冒仓库",
      "下载伪装安装包",
      "安装窃密木马",
      "盗取凭据并回传攻击者",
    ],
    impact: [
      "凭据与会话被窃取",
      "终端成为肉鸡或代理节点",
      "给后续 OpenClaw 生态攻击提供落脚点",
    ],
    mitigation: [
      "仅从官方仓库和校验后的发行源安装",
      "对下载链接和仓库所有权做核验",
      "对开发机执行 EDR/恶意软件扫描",
    ],
    keyFacts: [
      "2026 年 3 月公开报道提到假 GitHub 仓库与 Bing 广告投毒",
      "部分样本关联 Vidar infostealer 与代理木马",
    ],
  },
  {
    id: "cross-app-leakage",
    rank: 10,
    title: "Cross-Application Data Leakage",
    subtitle: "跨应用数据泄露",
    severity: "High",
    priority: 8.7,
    category: "跨系统数据访问",
    summary:
      "当 Agent 同时接入邮箱、Slack、日历、文件系统和浏览器后，任何一次控制面失陷都可能升级成跨应用数据整合式泄露。",
    attackChain: [
      "Agent 被提示注入或 Skill 接管",
      "读取多系统消息与文件",
      "拼接敏感上下文",
      "统一外传到攻击者端",
    ],
    impact: [
      "邮件、IM、日历、文件的联合泄露",
      "从业务上下文中提取密钥与凭据",
      "形成难以察觉的深度信息外流",
    ],
    mitigation: [
      "按数据域隔离连接器权限",
      "限制跨应用联动默认能力",
      "对高敏感连接器使用单独审批与审计",
    ],
    keyFacts: [
      "Agent 与多业务系统的统一访问，是它区别于普通助手的高风险点",
      "真正危险的是“组合数据”而不是某一个单点系统",
    ],
  },
];

const latestUpdates: RiskUpdate[] = [
  {
    date: "2026-03-06",
    title: "假安装包与搜索投毒进入公开传播阶段",
    summary:
      "公开报道显示，攻击者利用假 GitHub 仓库和 Bing 搜索广告传播伪造的 OpenClaw 安装包，样本与 Vidar infostealer、GhostSocks 等载荷相关。",
    riskFocus: "Fake Installer / Supply-Chain Malware",
    source: "TechRadar",
    url: "https://www.techradar.com/pro/security/hackers-exploit-openclaw-to-spread-malware-via-github-and-a-little-help-from-bing",
  },
  {
    date: "2026-02-26",
    title: "ClawJacked 披露本地 Gateway 可被恶意网页接管",
    summary:
      "Oasis Security 披露 OpenClaw 本地控制面存在高危接管链，恶意网站可通过 localhost WebSocket 交互劫持 Agent，官方建议升级到 2026.2.25 或更高版本。",
    riskFocus: "ClawJacked / WebSocket 控制接口劫持",
    source: "Oasis Security",
    url: "https://www.oasis.security/blog/openclaw-vulnerability",
  },
  {
    date: "2026-02-18",
    title: "Endor Labs 公布 6 个 OpenClaw 新漏洞",
    summary:
      "Endor Labs 公开了 Gateway SSRF、Webhook 认证缺失、上传路径穿越等 6 个漏洞，说明 Agent 工具流的数据路径本身就是新的攻击面。",
    riskFocus: "Command Injection / 工具链漏洞扩展",
    source: "Endor Labs",
    url: "https://www.endorlabs.com/learn/how-ai-sast-traced-data-flows-to-uncover-six-openclaw-vulnerabilities",
  },
  {
    date: "2026-02-06",
    title: "ClawHub 恶意 Skills 大规模曝光",
    summary:
      "公开研究指出 ClawHub 生态中发现数百个恶意技能，部分通过前置命令诱导用户下载和执行恶意程序，供应链风险从理论演变为实际投毒事件。",
    riskFocus: "Malicious Skills / Skill Dependency Injection",
    source: "Intelligibberish",
    url: "https://intelligibberish.com/articles/2026-02-06-openclaw-clawhub-malicious-skills-ai-agent-supply-chain-attack/",
  },
  {
    date: "2026-01-29",
    title: "OpenClaw 版本修复一键 RCE 与命令注入类问题",
    summary:
      "多份公开安全汇总显示，v2026.1.29 修复了与 token 外泄、一键 RCE、SSH 命令注入及沙箱逃逸相关的高危问题，这也是 2026 年初最关键的一轮补丁。",
    riskFocus: "Command Injection / RCE / Sandbox",
    source: "公开安全汇总",
    url: "https://blog.cyberdesserts.com/openclaw-malicious-skills-security/",
  },
];

export default function RisksPage() {
  const location = useLocation();
  const [selectedRiskId, setSelectedRiskId] = useState<string | null>(null);

  const selectedRisk = useMemo(
    () => topRisks.find((item) => item.id === selectedRiskId) || null,
    [selectedRiskId],
  );

  return (
    <PageContainer
      title="OpenClaw Top 10 风险"
      tabList={riskTabList}
      tabActiveKey={location.pathname}
      onTabChange={(key) => history.push(key)}
    >
      <style>
        {`
          @keyframes riskDetailFadeIn {
            from {
              opacity: 0;
              transform: translateY(8px);
            }
            to {
              opacity: 1;
              transform: translateY(0);
            }
          }
        `}
      </style>
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="OpenClaw 安全生态正面临一系列高强度安全挑战。本资源基于公开研究、漏洞披露与真实攻击路径，整理出当前最关键的 Top 10 风险，帮助安全研究员、CISO、学术界、相关开发者与用户使用统一语言理解 OpenClaw 风险。"
      />

      <Row gutter={[16, 16]} align="stretch">
        <Col xs={24}>
          <Card
            bordered={false}
            style={{
              marginBottom: 8,
              borderRadius: 20,
              background:
                "linear-gradient(135deg, #eef6ff 0%, #ffffff 55%, #f5fbff 100%)",
            }}
            bodyStyle={{ padding: 28 }}
          >
            <Space direction="vertical" size={10} style={{ width: "100%" }}>
              <Text
                style={{
                  fontSize: 12,
                  letterSpacing: 1.2,
                  color: "#1677ff",
                  fontWeight: 700,
                }}
              >
                OPENCLAW SECURITY KNOWLEDGEBASE
              </Text>
              <Text
                strong
                style={{ fontSize: 32, lineHeight: 1.2, color: "#0f172a" }}
              >
                OpenClaw Top 10 风险
              </Text>
              <Paragraph
                style={{
                  margin: 0,
                  fontSize: 15,
                  color: "#475569",
                  maxWidth: 980,
                }}
              >
                该风险列表按照真实攻击链梳理 OpenClaw 在提示注入、恶意
                Skills、工具权限、本地控制面与供应链分发上的核心风险。页面左侧用于快速切换风险项，右侧展开攻击链、影响面和处置建议，底部跟踪最近公开披露动态。
              </Paragraph>
            </Space>
          </Card>
        </Col>

        <Col xs={24} xl={8} style={{ display: "flex" }}>
          <Card
            title="风险清单"
            bodyStyle={{ padding: "12px 0" }}
            style={{ height: "100%", width: "100%", borderRadius: 20 }}
          >
            <ProList<TopRisk>
              rowKey="id"
              split
              showActions="hover"
              pagination={false}
              dataSource={topRisks}
              onRow={(record) => ({
                onMouseEnter: () => setSelectedRiskId(record.id),
                onMouseLeave: () => setSelectedRiskId(null),
                style: {
                  cursor: "pointer",
                  background: selectedRiskId === record.id ? "#f0f7ff" : "#fff",
                  borderLeft:
                    selectedRiskId === record.id
                      ? "4px solid #1677ff"
                      : "4px solid transparent",
                  paddingTop: 12,
                  paddingBottom: 12,
                  paddingLeft: 16,
                  paddingRight: 18,
                  transition: "all 0.2s ease",
                },
              })}
              metas={{
                title: {
                  dataIndex: "title",
                  render: (_, row) => (
                    <div style={{ paddingLeft: 12 }}>
                      <Space size={8} wrap>
                        <Text
                          strong
                          style={{ fontSize: 16 }}
                        >{`${row.rank}. ${row.title}`}</Text>
                        <Tag color={severityColorMap[row.severity]}>
                          {severityLabelMap[row.severity]}
                        </Tag>
                      </Space>
                    </div>
                  ),
                },
                description: {
                  render: (_, row) => (
                    <div style={{ paddingLeft: 12, paddingTop: 4 }}>
                      <Text type="secondary" style={{ fontSize: 14 }}>
                        {row.subtitle}
                      </Text>
                    </div>
                  ),
                },
              }}
            />
          </Card>
        </Col>

        <Col xs={24} xl={16} style={{ display: "flex" }}>
          <Card
            style={{ borderRadius: 20, width: "100%", height: "100%" }}
            bodyStyle={{ padding: 28, height: "100%" }}
          >
            {selectedRisk ? (
              <div
                key={selectedRisk.id}
                style={{
                  animation: "riskDetailFadeIn 220ms ease",
                  height: "100%",
                }}
              >
                <div style={{ marginBottom: 18 }}>
                  <Space size={10} wrap style={{ marginBottom: 8 }}>
                    <Text strong style={{ fontSize: 28, color: "#0f172a" }}>
                      {`${selectedRisk.rank}. ${selectedRisk.title}`}
                    </Text>
                    <Tag color={severityColorMap[selectedRisk.severity]}>
                      {severityLabelMap[selectedRisk.severity]}
                    </Tag>
                    <Tag color="blue">{selectedRisk.category}</Tag>
                  </Space>
                  <div>
                    <Text style={{ fontSize: 14, color: "#64748b" }}>
                      {selectedRisk.subtitle}
                    </Text>
                  </div>
                </div>

                <Paragraph
                  style={{ fontSize: 16, marginTop: 12, marginBottom: 20 }}
                >
                  {selectedRisk.summary}
                </Paragraph>

                <Descriptions
                  column={2}
                  bordered
                  size="middle"
                  style={{ marginBottom: 24 }}
                >
                  <Descriptions.Item label="中文名称">
                    {selectedRisk.subtitle}
                  </Descriptions.Item>
                  <Descriptions.Item label="优先级">
                    {selectedRisk.priority.toFixed(1)} / 10
                  </Descriptions.Item>
                  <Descriptions.Item label="风险类别">
                    {selectedRisk.category}
                  </Descriptions.Item>
                  <Descriptions.Item label="建议级别">
                    {severityLabelMap[selectedRisk.severity]}
                  </Descriptions.Item>
                </Descriptions>

                <Row gutter={[20, 20]}>
                  <Col xs={24} md={8}>
                    <Card
                      size="small"
                      title="典型攻击链"
                      style={{ height: "100%", borderRadius: 16 }}
                    >
                      {selectedRisk.attackChain.map((item, index) => (
                        <div key={item} style={{ marginBottom: 14 }}>
                          <Text
                            strong
                            style={{ color: "#1677ff" }}
                          >{`0${index + 1}`}</Text>
                          <div style={{ marginTop: 4 }}>{item}</div>
                        </div>
                      ))}
                    </Card>
                  </Col>
                  <Col xs={24} md={8}>
                    <Card
                      size="small"
                      title="主要影响"
                      style={{ height: "100%", borderRadius: 16 }}
                    >
                      {selectedRisk.impact.map((item) => (
                        <Paragraph key={item} style={{ marginBottom: 12 }}>
                          {item}
                        </Paragraph>
                      ))}
                    </Card>
                  </Col>
                  <Col xs={24} md={8}>
                    <Card
                      size="small"
                      title="处置建议"
                      style={{ height: "100%", borderRadius: 16 }}
                    >
                      {selectedRisk.mitigation.map((item) => (
                        <Paragraph key={item} style={{ marginBottom: 12 }}>
                          {item}
                        </Paragraph>
                      ))}
                    </Card>
                  </Col>
                </Row>

                <Divider style={{ margin: "24px 0 20px" }} />

                <Card
                  size="small"
                  title="关键观察"
                  style={{ borderRadius: 16 }}
                >
                  {selectedRisk.keyFacts.map((item) => (
                    <Paragraph key={item} style={{ marginBottom: 12 }}>
                      {item}
                    </Paragraph>
                  ))}
                </Card>

                <div style={{ marginTop: 20 }}>
                  <Text strong>处理优先度</Text>
                  <Progress
                    percent={Math.round(selectedRisk.priority * 10)}
                    strokeColor={
                      selectedRisk.severity === "Critical"
                        ? "#ff4d4f"
                        : "#fa8c16"
                    }
                    showInfo={false}
                    style={{ marginTop: 8 }}
                  />
                </div>
              </div>
            ) : (
              <div
                style={{
                  minHeight: 640,
                  height: "100%",
                  display: "flex",
                  alignItems: "flex-start",
                  justifyContent: "flex-start",
                  textAlign: "left",
                  padding: "8px 8px 0",
                }}
              >
                <div
                  style={{
                    animation: "riskDetailFadeIn 220ms ease",
                    maxWidth: 720,
                  }}
                >
                  <Text
                    strong
                    style={{
                      display: "block",
                      fontSize: 28,
                      color: "#0f172a",
                      marginBottom: 12,
                    }}
                  >
                    滑动以查看具体风险详情
                  </Text>
                  <Paragraph
                    style={{ fontSize: 16, color: "#64748b", margin: 0 }}
                  >
                    将鼠标移动到左侧任意风险项上，右侧会自动展开对应的攻击链、影响面和处置建议。
                  </Paragraph>
                </div>
              </div>
            )}
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24}>
          <Card
            title="最新风险动态"
            style={{ borderRadius: 20 }}
            bodyStyle={{ padding: 28 }}
          >
            <Timeline
              items={latestUpdates.map((item) => ({
                color: item.date >= "2026-02-20" ? "red" : "blue",
                children: (
                  <div>
                    <Text strong>{item.date}</Text>
                    <div style={{ margin: "4px 0 6px" }}>{item.title}</div>
                    <Paragraph type="secondary" style={{ marginBottom: 6 }}>
                      {item.summary}
                    </Paragraph>
                    <Space size={8} wrap>
                      <Tag color="purple">{item.riskFocus}</Tag>
                      <Text type="secondary">{item.source}</Text>
                      <Link href={item.url} target="_blank">
                        查看来源 <LinkOutlined />
                      </Link>
                    </Space>
                  </div>
                ),
              }))}
            />
          </Card>
        </Col>
      </Row>
    </PageContainer>
  );
}
