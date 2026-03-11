import { PageContainer, ProTable, type ProColumns } from "@ant-design/pro-components";
import { history, useLocation } from "@umijs/max";
import { Alert, Card, Space, Tag, Typography } from "antd";
import { useEffect, useMemo, useState } from "react";
import { riskAPI, type VulnerabilityItem } from "../../services/riskApi";

const { Paragraph, Text, Link } = Typography;

const riskTabList = [
  { tab: "Top 10 风险", key: "/risks/top10" },
  { tab: "已披露漏洞", key: "/risks/vulnerabilities" },
];

const top10ColorMap: Record<string, string> = {
  "prompt-injection": "magenta",
  "malicious-skills": "volcano",
  "skill-dependency-injection": "purple",
  "tool-privilege-escalation": "red",
  clawjacked: "red",
  "command-injection": "red",
  "sandbox-hash-collision": "orange",
  "token-drain": "gold",
  "fake-installer": "gold",
  "cross-app-leakage": "blue",
};

const severityWeight: Record<string, number> = {
  Critical: 4,
  High: 3,
  Moderate: 2,
  Low: 1,
};

function severityColor(severity: string) {
  if (severity === "Critical") return "red";
  if (severity === "High") return "orange";
  if (severity === "Moderate") return "gold";
  if (severity === "Low") return "default";
  return "blue";
}

export default function VulnerabilitiesPage() {
  const location = useLocation();
  const [loading, setLoading] = useState(false);
  const [rows, setRows] = useState<VulnerabilityItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<
    "all" | "llm" | "general" | "mapped" | "unmapped"
  >("all");
  const [summary, setSummary] = useState({
    llmSpecific: 0,
    generalSoftware: 0,
    mappedTop10: 0,
  });

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await riskAPI.getVulnerabilities();
        const sortedRows = [...(data.vulnerabilities || [])].sort((a, b) => {
          const natureDiff =
            (a.vulnerabilityNatureId === "llm_system_specific" ? 0 : 1) -
            (b.vulnerabilityNatureId === "llm_system_specific" ? 0 : 1);
          if (natureDiff !== 0) return natureDiff;

          const rankA = a.top10Rank ?? 999;
          const rankB = b.top10Rank ?? 999;
          if (rankA !== rankB) return rankA - rankB;

          const severityDiff = (severityWeight[b.severity] || 0) - (severityWeight[a.severity] || 0);
          if (severityDiff !== 0) return severityDiff;

          return a.index - b.index;
        });

        setRows(sortedRows);
        setSummary(data.summary || { llmSpecific: 0, generalSoftware: 0, mappedTop10: 0 });
      } catch (err) {
        setError(err instanceof Error ? err.message : "加载漏洞数据失败");
      } finally {
        setLoading(false);
      }
    };

    load();
  }, []);

  const mappedCount = useMemo(() => rows.filter((item) => item.top10PrimaryId).length, [rows]);
  const unmappedCount = rows.length - mappedCount;
  const filteredRows = useMemo(() => {
    if (activeFilter === "llm") {
      return rows.filter((item) => item.vulnerabilityNatureId === "llm_system_specific");
    }
    if (activeFilter === "general") {
      return rows.filter((item) => item.vulnerabilityNatureId === "general_software_vulnerability");
    }
    if (activeFilter === "mapped") {
      return rows.filter((item) => Boolean(item.top10PrimaryId));
    }
    if (activeFilter === "unmapped") {
      return rows.filter((item) => !item.top10PrimaryId);
    }
    return rows;
  }, [activeFilter, rows]);

  const toggleFilter = (filter: "all" | "llm" | "general" | "mapped" | "unmapped") => {
    setActiveFilter((current) => (current === filter ? "all" : filter));
  };

  const columns: ProColumns<VulnerabilityItem>[] = [
    {
      title: "漏洞属性",
      dataIndex: "vulnerabilityNatureLabel",
      width: 180,
      render: (_, record) =>
        record.vulnerabilityNatureId === "llm_system_specific" ? (
          <Tag color="red">大模型系统特有漏洞</Tag>
        ) : (
          <Tag>软件系统通用漏洞</Tag>
        ),
    },
    {
      title: "映射 Top 10",
      dataIndex: "top10PrimaryLabel",
      width: 220,
      render: (_, record) =>
        record.top10PrimaryId ? (
          <Tag color={top10ColorMap[record.top10PrimaryId] || "blue"}>
            {record.top10PrimaryLabel}
          </Tag>
        ) : (
          <Tag>未映射</Tag>
        ),
    },
    {
      title: "漏洞编号",
      dataIndex: "vulnerabilityId",
      width: 180,
      render: (_, record) => record.vulnerabilityId || `No.${record.index}`,
    },
    {
      title: "漏洞标题",
      dataIndex: "title",
      ellipsis: true,
      width: 360,
    },
    {
      title: "阶段",
      dataIndex: "stage",
      width: 220,
      ellipsis: true,
    },
    {
      title: "严重等级",
      dataIndex: "severity",
      width: 100,
      render: (_, record) => <Tag color={severityColor(record.severity)}>{record.severity}</Tag>,
    },
    {
      title: "CWE",
      dataIndex: "cwe",
      width: 160,
      ellipsis: true,
      render: (_, record) => record.cwe || "-",
    },
    {
      title: "影响版本",
      dataIndex: "affectedVersions",
      width: 180,
      ellipsis: true,
      render: (_, record) => record.affectedVersions || "-",
    },
    {
      title: "链接",
      dataIndex: "link",
      width: 100,
      render: (_, record) =>
        record.link ? (
          <Link href={record.link} target="_blank">
            查看
          </Link>
        ) : (
          "-"
        ),
    },
  ];

  return (
    <PageContainer
      title="OpenClaw Top 10 风险"
      tabList={riskTabList}
      tabActiveKey={location.pathname}
      onTabChange={(key) => history.push(key)}
    >
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message={
          <span>
            <strong>标签说明：</strong>
            大模型系统特有漏洞，指漏洞与 Agent、LLM 提示、工具调用、沙箱或本地控制面等能力直接相关；软件系统通用漏洞，指常规软件系统中也会出现的鉴权、输入校验、路径处理或资源访问缺陷；已映射 Top 10，指该漏洞可对应到 OpenClaw Top 10 某一类核心风险；未映射，指当前未找到足够依据将其归入某个 Top 10 类别。
          </span>
        }
      />

      <Card style={{ marginBottom: 16, borderRadius: 20 }} bodyStyle={{ padding: 24 }}>
        <Space size={12} wrap>
          <Tag
            color={activeFilter === "all" ? "blue" : "default"}
            style={{ cursor: "pointer", paddingInline: 10 }}
            onClick={() => setActiveFilter("all")}
          >
            总漏洞 {rows.length}
          </Tag>
          <Tag
            color={activeFilter === "llm" ? "red" : "default"}
            style={{ cursor: "pointer", paddingInline: 10 }}
            onClick={() => toggleFilter("llm")}
          >
            大模型系统特有漏洞 {summary.llmSpecific}
          </Tag>
          <Tag
            color={activeFilter === "general" ? "gold" : "default"}
            style={{ cursor: "pointer", paddingInline: 10 }}
            onClick={() => toggleFilter("general")}
          >
            软件系统通用漏洞 {summary.generalSoftware}
          </Tag>
          <Tag
            color={activeFilter === "mapped" ? "purple" : "default"}
            style={{ cursor: "pointer", paddingInline: 10 }}
            onClick={() => toggleFilter("mapped")}
          >
            已映射 Top 10 {summary.mappedTop10}
          </Tag>
          <Tag
            color={activeFilter === "unmapped" ? "cyan" : "default"}
            style={{ cursor: "pointer", paddingInline: 10 }}
            onClick={() => toggleFilter("unmapped")}
          >
            未映射 {unmappedCount}
          </Tag>
        </Space>
        {error ? (
          <Paragraph style={{ color: "#ff4d4f", marginTop: 12, marginBottom: 0 }}>{error}</Paragraph>
        ) : null}
      </Card>

      <ProTable<VulnerabilityItem>
        rowKey={(record) => `${record.index}-${record.vulnerabilityId || record.title}`}
        loading={loading}
        search={false}
        options={false}
        columns={columns}
        dataSource={filteredRows}
        pagination={{ pageSize: 20, showSizeChanger: false }}
        scroll={{ x: 1650 }}
        cardBordered
        expandable={{
          expandedRowRender: (record) => (
            <div style={{ padding: "4px 8px" }}>
              <Paragraph style={{ marginBottom: 8 }}>
                <Text strong>判定说明：</Text>
                {record.analysisReason || "暂无"}
              </Paragraph>
              <Paragraph style={{ marginBottom: 8 }}>
                <Text strong>原因说明：</Text>
                {record.reason || "暂无"}
              </Paragraph>
              <Paragraph style={{ marginBottom: 8 }}>
                <Text strong>关联 Top 10：</Text>
                {record.top10MatchLabels?.length > 0 ? record.top10MatchLabels.join("，") : "无"}
              </Paragraph>
              <Paragraph style={{ marginBottom: 8 }}>
                <Text strong>映射置信度：</Text>
                {record.mappingConfidence ? record.mappingConfidence.toFixed(2) : "0.00"}
              </Paragraph>
              <Paragraph style={{ marginBottom: 0 }}>
                <Text strong>CVE：</Text>
                {record.cve || "暂无"}
              </Paragraph>
            </div>
          ),
        }}
      />
    </PageContainer>
  );
}
