import {
  PageContainer,
  ProTable,
  type ProColumns,
} from "@ant-design/pro-components";
import { history, useLocation } from "@umijs/max";
import { Alert, Card, Space, Tag, Typography } from "antd";
import { useEffect, useMemo, useState } from "react";
import { riskAPI, type VulnerabilityItem } from "../../services/riskApi";
import { normalizeRiskStage } from "../../utils/riskStage";

const { Paragraph, Text, Link } = Typography;

const riskTabList = [
  { tab: "Top 10 风险", key: "/risks/top10" },
  { tab: "已披露漏洞", key: "/risks/vulnerabilities" },
];

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
    "all" | "llm" | "general"
  >("all");
  const [stageFilter, setStageFilter] = useState<string>("all");
  const [summary, setSummary] = useState({
    llmSpecific: 0,
    generalSoftware: 0,
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

          const severityDiff =
            (severityWeight[b.severity] || 0) -
            (severityWeight[a.severity] || 0);
          if (severityDiff !== 0) return severityDiff;

          return a.index - b.index;
        });

        setRows(sortedRows);
        setSummary(
          data.summary || {
            llmSpecific: 0,
            generalSoftware: 0,
          },
        );
      } catch (err) {
        setError(err instanceof Error ? err.message : "加载漏洞数据失败");
      } finally {
        setLoading(false);
      }
    };

    load();
  }, []);

  const stageOptions = useMemo(() => {
    const counter = new Map<string, number>();
    rows.forEach((item) => {
      const key = normalizeRiskStage(item.stage) || "未标注阶段";
      counter.set(key, (counter.get(key) || 0) + 1);
    });

    return Array.from(counter.entries())
      .map(([stage, count]) => ({ stage, count }))
      .sort((a, b) => {
        if (b.count !== a.count) return b.count - a.count;
        return a.stage.localeCompare(b.stage);
      });
  }, [rows]);

  const filteredRows = useMemo(() => {
    let nextRows = rows;

    if (activeFilter === "llm") {
      nextRows = nextRows.filter(
        (item) => item.vulnerabilityNatureId === "llm_system_specific",
      );
    }
    if (activeFilter === "general") {
      nextRows = nextRows.filter(
        (item) =>
          item.vulnerabilityNatureId === "general_software_vulnerability",
      );
    }

    if (stageFilter !== "all") {
      nextRows = nextRows.filter(
        (item) => (normalizeRiskStage(item.stage) || "未标注阶段") === stageFilter,
      );
    }

    return nextRows;
  }, [activeFilter, rows, stageFilter]);

  const toggleFilter = (filter: "all" | "llm" | "general") => {
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
      title: "OpenClaw 生命周期阶段",
      dataIndex: "stage",
      width: 240,
      render: (_, record) => (
        <Tag color="blue">{normalizeRiskStage(record.stage) || "未标注阶段"}</Tag>
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
      title: "严重等级",
      dataIndex: "severity",
      width: 100,
      render: (_, record) => (
        <Tag color={severityColor(record.severity)}>{record.severity}</Tag>
      ),
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
            大模型系统特有漏洞，指漏洞与 Agent、LLM
            提示、工具调用、沙箱或本地控制面等能力直接相关；软件系统通用漏洞，指常规软件系统中也会出现的鉴权、输入校验、路径处理或资源访问缺陷；生命周期阶段用于表示漏洞主要出现于 OpenClaw
            的哪个处理阶段。
          </span>
        }
      />

      <Card
        style={{ marginBottom: 16, borderRadius: 20 }}
        bodyStyle={{ padding: 24 }}
      >
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
          {stageOptions.map((item) => (
            <Tag
              key={item.stage}
              color={stageFilter === item.stage ? "processing" : "default"}
              style={{ cursor: "pointer", paddingInline: 10 }}
              onClick={() =>
                setStageFilter((current) =>
                  current === item.stage ? "all" : item.stage,
                )
              }
            >
              {item.stage} {item.count}
            </Tag>
          ))}
        </Space>
        {error ? (
          <Paragraph
            style={{ color: "#ff4d4f", marginTop: 12, marginBottom: 0 }}
          >
            {error}
          </Paragraph>
        ) : null}
      </Card>

      <ProTable<VulnerabilityItem>
        rowKey={(record) =>
          `${record.index}-${record.vulnerabilityId || record.title}`
        }
        loading={loading}
        search={false}
        options={false}
        columns={columns}
        dataSource={filteredRows}
        pagination={{ pageSize: 20, showSizeChanger: false }}
        scroll={{ x: 1450 }}
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
                <Text strong>生命周期阶段：</Text>
                {normalizeRiskStage(record.stage) || "未标注阶段"}
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
