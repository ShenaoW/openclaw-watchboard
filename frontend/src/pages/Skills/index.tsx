import { PageContainer, ProList } from "@ant-design/pro-components";
import {
  Alert,
  Avatar,
  Button,
  Card,
  Col,
  Empty,
  Row,
  Select,
  Space,
  Spin,
  Tabs,
  Tag,
  Typography,
} from "antd";
import {
  CheckCircleOutlined,
  CodeOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  StopOutlined,
} from "@ant-design/icons";
import { Column } from "@ant-design/charts";
import { useEffect, useState } from "react";
import {
  useSkillsData,
  useSkillsList,
  type SkillDetail,
} from "../../services/skillsApi";

const { Option } = Select;
const { Paragraph, Text, Link } = Typography;

function formatDate(value?: string) {
  if (!value) {
    return "unknown";
  }
  const match = value.match(/\d{4}-\d{2}-\d{2}/);
  return match ? match[0] : "unknown";
}

function sanitizeDescription(description?: string) {
  if (!description) {
    return "";
  }
  if (
    description.startsWith("可疑技能：") ||
    description.startsWith("恶意技能：")
  ) {
    return "";
  }
  return description;
}

function getSourceTag(source: string) {
  switch (source) {
    case "clawhub":
      return <Tag color="green">官方</Tag>;
    case "skills.rest":
      return <Tag color="blue">Skills.rest</Tag>;
    case "skillsmp":
      return <Tag color="purple">SkillsMP</Tag>;
    case "skills.sh":
      return <Tag color="cyan">skills.sh</Tag>;
    case "gendigital":
      return <Tag color="geekblue">GenDigital</Tag>;
    case "koi":
      return <Tag color="volcano">KOI</Tag>;
    default:
      return <Tag>{source}</Tag>;
  }
}

function getSourceLabel(source: string) {
  switch (source) {
    case "clawhub":
      return "ClawHub";
    case "skills.rest":
      return "Skills.rest";
    case "skillsmp":
      return "SkillsMP";
    case "skills.sh":
      return "skills.sh";
    case "gendigital":
      return "GenDigital";
    case "koi":
      return "KOI";
    default:
      return source;
  }
}

function SkillListSection(props: {
  title: string;
  loading: boolean;
  skills: SkillDetail[];
  currentPage: number;
  total: number;
  onPageChange: (page: number) => void;
  selectedSource?: string;
  selectedCategory?: string;
  categories: Array<{ category: string }>;
  onSourceChange: (value?: string) => void;
  onCategoryChange: (value?: string) => void;
  emptyText: string;
}) {
  return (
    <Card
      title={props.title}
      extra={
        <Space wrap>
          <Select
            placeholder="选择数据源"
            style={{ width: 150 }}
            value={props.selectedSource}
            onChange={props.onSourceChange}
            allowClear
          >
            <Option value="clawhub">ClawHub官方</Option>
            <Option value="skills.rest">Skills.rest</Option>
            <Option value="skillsmp">SkillsMP</Option>
            <Option value="skills.sh">skills.sh</Option>
            <Option value="gendigital">GenDigital</Option>
            <Option value="koi">KOI</Option>
          </Select>
          <Select
            placeholder="选择分类"
            style={{ width: 150 }}
            value={props.selectedCategory}
            onChange={props.onCategoryChange}
            allowClear
          >
            {props.categories.map((cat) => (
              <Option key={cat.category} value={cat.category}>
                {cat.category}
              </Option>
            ))}
          </Select>
        </Space>
      }
      loading={props.loading}
    >
      <ProList<SkillDetail>
        dataSource={props.skills}
        search={false}
        options={false}
        showActions="hover"
        locale={{ emptyText: props.emptyText }}
        pagination={{
          current: props.currentPage,
          pageSize: 20,
          total: props.total,
          showSizeChanger: false,
          showQuickJumper: true,
          showTotal: (total, range) => `${range[0]}-${range[1]} 共 ${total} 项`,
          onChange: props.onPageChange,
        }}
        metas={{
          title: {
            render: (_, record) => (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  flexWrap: "wrap",
                }}
              >
                <CodeOutlined style={{ color: "#1677ff" }} />
                <span style={{ fontWeight: 600 }}>{record.name}</span>
                <Tag color="blue">{record.version || "-"}</Tag>
                {getSourceTag(record.source)}
                {record.classification === "safe" ? (
                  <Tag color="green">安全</Tag>
                ) : null}
                {record.classification === "suspicious" ? (
                  <Tag color="orange">可疑</Tag>
                ) : null}
                {record.classification === "malicious" ? (
                  <Tag color="red">恶意</Tag>
                ) : null}
                {record.classification === "unknown" ? (
                  <Tag color="default">待检测</Tag>
                ) : null}
              </div>
            ),
          },
          description: {
            render: (_, record) => (
              <div>
                <Paragraph style={{ marginBottom: 8 }}>
                  {sanitizeDescription(record.description) || "暂无公开描述"}
                </Paragraph>
                <div
                  style={{
                    display: "flex",
                    gap: 16,
                    flexWrap: "wrap",
                    fontSize: 12,
                    color: "#64748b",
                  }}
                >
                  <span>分类：{record.category || "-"}</span>
                  <span>维护者：{record.maintainer || "-"}</span>
                  <span>技能更新时间：{formatDate(record.lastUpdated)}</span>
                  {record.repository ? (
                    <Link href={record.repository} target="_blank">
                      仓库链接
                    </Link>
                  ) : null}
                </div>
              </div>
            ),
          },
        }}
      />
    </Card>
  );
}

export default function Skills() {
  const [selectedSource, setSelectedSource] = useState<string | undefined>(
    undefined,
  );
  const [selectedCategory, setSelectedCategory] = useState<string | undefined>(
    undefined,
  );
  const [trustedPage, setTrustedPage] = useState(1);
  const [pendingPage, setPendingPage] = useState(1);
  const [maliciousPage, setMaliciousPage] = useState(1);

  const {
    stats,
    loading: statsLoading,
    error: statsError,
    refetch: refetchStats,
  } = useSkillsData();
  const trusted = useSkillsList({
    classification: "safe",
    source: selectedSource,
    category: selectedCategory,
    page: trustedPage,
    limit: 20,
  });
  const pending = useSkillsList({
    classification: "unknown",
    source: selectedSource,
    category: selectedCategory,
    page: pendingPage,
    limit: 20,
  });
  const malicious = useSkillsList({
    classification: "malicious",
    source: selectedSource,
    category: selectedCategory,
    page: maliciousPage,
    limit: 20,
  });

  useEffect(() => {
    const errors = [statsError, trusted.error, pending.error, malicious.error].filter(Boolean);
    if (errors.length > 0) {
      // eslint-disable-next-line no-console
      console.error(errors[0]);
    }
  }, [statsError, trusted.error, pending.error, malicious.error]);

  const resetPages = () => {
    setTrustedPage(1);
    setPendingPage(1);
    setMaliciousPage(1);
  };

  const handleSourceChange = (value?: string) => {
    setSelectedSource(value);
    resetPages();
  };

  const handleCategoryChange = (value?: string) => {
    setSelectedCategory(value);
    resetPages();
  };

  const handleRefresh = async () => {
    await Promise.all([refetchStats(), trusted.refetch(), pending.refetch(), malicious.refetch()]);
  };

  const categoryData = stats?.topCategories || [];
  const sourceColorMap: Record<string, string> = {
    clawhub: "#52c41a",
    "skills.rest": "#1890ff",
    skillsmp: "#722ed1",
    "skills.sh": "#13c2c2",
    gendigital: "#2f54eb",
    koi: "#fa541c",
    other: "#8c8c8c",
  };
  const sourceDistributionData = stats
    ? stats.sourceDistribution
        .map((item) => ({
          source: getSourceLabel(item.source),
          count: item.count,
          color: sourceColorMap[item.source] || "#8c8c8c",
        }))
        .filter((item) => item.count > 0)
    : [];
  const sourceTotal = sourceDistributionData.reduce(
    (sum, item) => sum + item.count,
    0,
  );
  const sourceChartBackground = sourceDistributionData.length
    ? `conic-gradient(${sourceDistributionData
        .map((item, index) => {
          const start = sourceDistributionData
            .slice(0, index)
            .reduce((sum, current) => sum + current.count, 0);
          const end = start + item.count;
          const startPercent =
            sourceTotal > 0 ? (start / sourceTotal) * 100 : 0;
          const endPercent = sourceTotal > 0 ? (end / sourceTotal) * 100 : 0;
          return `${item.color} ${startPercent}% ${endPercent}%`;
        })
        .join(", ")})`
    : "#f0f0f0";

  const categoryConfig = {
    data: categoryData,
    xField: "category",
    yField: "count",
    height: 300,
    color: "#1890ff",
    label: false,
    axis: {
      y: {
        labelFormatter: (value: string) => Number(value).toLocaleString(),
      },
    },
  };

  if (statsLoading && !stats) {
    return (
      <PageContainer>
        <div style={{ textAlign: "center", padding: "50px 0" }}>
          <Spin size="large" />
        </div>
      </PageContainer>
    );
  }

  if (statsError && !stats) {
    return (
      <PageContainer>
        <Alert
          message="数据加载失败"
          description={statsError}
          type="error"
          showIcon
        />
      </PageContainer>
    );
  }

  if (!stats) {
    return (
      <PageContainer>
        <Empty description="暂无数据" />
      </PageContainer>
    );
  }

  return (
    <PageContainer
      title="Skill 投毒情报与可信治理"
      subTitle="收集公开来源的 Skill 投毒情报，并基于自研能力进行持续安全检测"
      extra={[
        <Button
          key="sync"
          icon={<ReloadOutlined />}
          onClick={handleRefresh}
          loading={statsLoading}
        >
          同步 Skill 库
        </Button>,
      ]}
    >
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <div style={{ display: "flex", alignItems: "center" }}>
              <Avatar
                size={48}
                style={{ backgroundColor: "#1890ff" }}
                icon={<CodeOutlined />}
              />
              <div style={{ marginLeft: 16 }}>
                <div style={{ fontSize: 24, fontWeight: "bold" }}>
                  {stats.totalSkills.toLocaleString()}
                </div>
                <div style={{ color: "#999" }}>Skills 总数</div>
              </div>
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <div style={{ display: "flex", alignItems: "center" }}>
              <Avatar
                size={48}
                style={{ backgroundColor: "#52c41a" }}
                icon={<CheckCircleOutlined />}
              />
              <div style={{ marginLeft: 16 }}>
                <div
                  style={{ fontSize: 24, fontWeight: "bold", color: "#52c41a" }}
                >
                  {stats.securityDistribution.safe.toLocaleString()}
                </div>
                <div style={{ color: "#999" }}>安全 Skills</div>
              </div>
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <div style={{ display: "flex", alignItems: "center" }}>
              <Avatar
                size={48}
                style={{ backgroundColor: "#faad14" }}
                icon={<SafetyCertificateOutlined />}
              />
              <div style={{ marginLeft: 16 }}>
                <div
                  style={{ fontSize: 24, fontWeight: "bold", color: "#faad14" }}
                >
                  {stats.securityDistribution.unknown.toLocaleString()}
                </div>
                <div style={{ color: "#999" }}>待检测 Skills</div>
              </div>
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <div style={{ display: "flex", alignItems: "center" }}>
              <Avatar
                size={48}
                style={{ backgroundColor: "#722ed1" }}
                icon={<StopOutlined />}
              />
              <div style={{ marginLeft: 16 }}>
                <div
                  style={{ fontSize: 24, fontWeight: "bold", color: "#722ed1" }}
                >
                  {stats.securityDistribution.malicious.toLocaleString()}
                </div>
                <div style={{ color: "#999" }}>恶意 Skills</div>
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginBottom: 24 }} align="stretch">
        <Col xs={24} xl={12} style={{ display: "flex" }}>
          <Card
            title="📊 数据源分布"
            size="small"
            style={{ width: "100%", height: "100%" }}
          >
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "260px minmax(0, 1fr)",
                gap: 20,
                alignItems: "center",
                height: "100%",
                minHeight: 320,
              }}
            >
              <div
                style={{
                  height: 300,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <div
                  style={{
                    width: 240,
                    height: 240,
                    borderRadius: "50%",
                    background: sourceChartBackground,
                    position: "relative",
                    boxShadow: "inset 0 0 0 1px rgba(0,0,0,0.04)",
                  }}
                >
                  <div
                    style={{
                      position: "absolute",
                      inset: 42,
                      borderRadius: "50%",
                      background: "#fff",
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      justifyContent: "center",
                      textAlign: "center",
                    }}
                  >
                    <div
                      style={{ fontSize: 28, fontWeight: 700, lineHeight: 1 }}
                    >
                      {sourceTotal.toLocaleString()}
                    </div>
                    <div
                      style={{ marginTop: 8, color: "#8c8c8c", fontSize: 12 }}
                    >
                      Total Skills
                    </div>
                  </div>
                </div>
              </div>
              <div style={{ minWidth: 0 }}>
                {sourceDistributionData.map((item) => (
                  <div
                    key={item.source}
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      justifyContent: "space-between",
                      gap: 16,
                      padding: "10px 0",
                      borderBottom: "1px solid #f0f0f0",
                    }}
                  >
                    <Space size={8} style={{ minWidth: 0 }}>
                      <span
                        style={{
                          width: 10,
                          height: 10,
                          borderRadius: "50%",
                          display: "inline-block",
                          backgroundColor: item.color,
                        }}
                      />
                      <span style={{ fontWeight: 500 }}>{item.source}</span>
                    </Space>
                    <div
                      style={{
                        textAlign: "right",
                        flexShrink: 0,
                        lineHeight: 1.35,
                      }}
                    >
                      <div style={{ color: "#8c8c8c", fontSize: 12 }}>
                        {sourceTotal > 0
                          ? ((item.count / sourceTotal) * 100).toFixed(1)
                          : "0.0"}
                        %
                      </div>
                      <strong>{item.count.toLocaleString()}</strong>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </Col>
        <Col xs={24} xl={12} style={{ display: "flex" }}>
          <Card
            title="📈 技能分类分布"
            size="small"
            style={{ width: "100%", height: "100%" }}
          >
            <Column {...categoryConfig} />
          </Card>
        </Col>
      </Row>

      <Tabs
        defaultActiveKey="trusted"
        items={[
          {
            key: "trusted",
            label: "✅ 可信 Skills 库",
            children: (
              <SkillListSection
                title="可信 Skills 列表"
                loading={trusted.loading}
                skills={trusted.skills}
                currentPage={trustedPage}
                total={trusted.pagination.total}
                onPageChange={setTrustedPage}
                selectedSource={selectedSource}
                selectedCategory={selectedCategory}
                categories={stats.topCategories}
                onSourceChange={handleSourceChange}
                onCategoryChange={handleCategoryChange}
                emptyText="暂无可信 Skills"
              />
            ),
          },
          {
            key: "pending",
            label: "🕓 待检测 Skills",
            children: (
              <SkillListSection
                title="待检测 Skills 列表"
                loading={pending.loading}
                skills={pending.skills}
                currentPage={pendingPage}
                total={pending.pagination.total}
                onPageChange={setPendingPage}
                selectedSource={selectedSource}
                selectedCategory={selectedCategory}
                categories={stats.topCategories}
                onSourceChange={handleSourceChange}
                onCategoryChange={handleCategoryChange}
                emptyText="暂无待检测 Skills"
              />
            ),
          },
          {
            key: "malicious",
            label: "🚫 恶意 Skills",
            children: (
              <SkillListSection
                title="恶意 Skills 列表"
                loading={malicious.loading}
                skills={malicious.skills}
                currentPage={maliciousPage}
                total={malicious.pagination.total}
                onPageChange={setMaliciousPage}
                selectedSource={selectedSource}
                selectedCategory={selectedCategory}
                categories={stats.topCategories}
                onSourceChange={handleSourceChange}
                onCategoryChange={handleCategoryChange}
                emptyText="暂无恶意 Skills"
              />
            ),
          },
        ]}
      />
    </PageContainer>
  );
}
