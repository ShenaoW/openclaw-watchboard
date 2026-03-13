import { PageContainer } from "@ant-design/pro-components";
import {
  Card,
  Col,
  Empty,
  Progress,
  Row,
  Space,
  Spin,
  Tag,
  Typography,
  message,
} from "antd";
import { Column } from "@ant-design/charts";
import { GlobalOutlined, SafetyCertificateOutlined } from "@ant-design/icons";
import { useEffect, useMemo, useState } from "react";
import { useExposureOverview } from "../../services/exposureApi";
import { riskAPI, type VulnerabilityItem } from "../../services/riskApi";
import { useSkillsData } from "../../services/skillsApi";
import { normalizeRiskStage } from "../../utils/riskStage";

const { Text } = Typography;

const countryNameMap: Record<string, string> = {
  "China mainland": "中国大陆",
  "United States": "美国",
  Singapore: "新加坡",
  Germany: "德国",
  "Hong Kong": "中国香港",
};

function severityColor(level: string) {
  if (level === "Critical") return "#ff4d4f";
  if (level === "High") return "#fa8c16";
  if (level === "Moderate") return "#fadb14";
  return "#91caff";
}

export default function Dashboard() {
  const {
    overview,
    loading: exposureLoading,
    error: exposureError,
  } = useExposureOverview();
  const {
    stats: skillsStats,
    loading: skillsLoading,
    error: skillsError,
  } = useSkillsData();
  const [vulnerabilities, setVulnerabilities] = useState<VulnerabilityItem[]>(
    [],
  );
  const [riskLoading, setRiskLoading] = useState(false);
  const [riskError, setRiskError] = useState<string | null>(null);

  useEffect(() => {
    const loadVulnerabilities = async () => {
      setRiskLoading(true);
      setRiskError(null);
      try {
        const data = await riskAPI.getVulnerabilities();
        setVulnerabilities(data.vulnerabilities || []);
      } catch (err) {
        setRiskError(err instanceof Error ? err.message : "加载漏洞数据失败");
      } finally {
        setRiskLoading(false);
      }
    };

    loadVulnerabilities();
  }, []);

  useEffect(() => {
    const errors = [exposureError, skillsError, riskError].filter(Boolean);
    if (errors.length > 0) {
      message.error(String(errors[0]));
    }
  }, [exposureError, skillsError, riskError]);

  const loading = exposureLoading || skillsLoading || riskLoading;

  const criticalAndHighVuls = vulnerabilities.filter(
    (item) => item.severity === "Critical" || item.severity === "High",
  ).length;

  const stageDistribution = useMemo(() => {
    const stageCounter = new Map<string, number>();
    vulnerabilities.forEach((item) => {
      const key = normalizeRiskStage(item.stage);
      stageCounter.set(key, (stageCounter.get(key) || 0) + 1);
    });

    return Array.from(stageCounter.entries())
      .map(([stage, count]) => ({ stage, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);
  }, [vulnerabilities]);

  const vulnerabilitySeverityDistribution = useMemo(() => {
    const severityOrder = ["Critical", "High", "Moderate", "Low"];
    const counter = new Map<string, number>();

    vulnerabilities.forEach((item) => {
      counter.set(item.severity, (counter.get(item.severity) || 0) + 1);
    });

    return severityOrder
      .filter((level) => counter.has(level))
      .map((level) => ({
        severity: level,
        count: counter.get(level) || 0,
      }));
  }, [vulnerabilities]);

  const topCountries = overview?.topCountries || [];
  const securityDistribution = skillsStats?.securityDistribution;

  return (
    <PageContainer
      title="ClawSec 总览"
      subTitle="汇总 OpenClaw 暴露面、Skills 风险与已披露漏洞态势"
    >
      <Spin spinning={loading}>
        <Row gutter={[16, 16]} align="stretch" style={{ marginBottom: 8 }}>
          <Col xs={24} sm={12} xl={6} style={{ display: "flex" }}>
            <Card
              style={{ width: "100%", height: "100%", borderRadius: 20 }}
              bodyStyle={{ height: "100%" }}
            >
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  height: "100%",
                  justifyContent: "space-between",
                }}
              >
                <div>
                  <Text type="secondary">已披露漏洞总数</Text>
                  <div
                    style={{
                      fontSize: 34,
                      fontWeight: 700,
                      color: "#0f172a",
                      marginTop: 8,
                    }}
                  >
                    {vulnerabilities.length.toLocaleString()}
                  </div>
                </div>
                <Text type="secondary">已同步到本地漏洞数据库</Text>
              </div>
            </Card>
          </Col>
          <Col xs={24} sm={12} xl={6} style={{ display: "flex" }}>
            <Card
              style={{ width: "100%", height: "100%", borderRadius: 20 }}
              bodyStyle={{ height: "100%" }}
            >
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  height: "100%",
                  justifyContent: "space-between",
                }}
              >
                <div>
                  <Text type="secondary">高危与严重漏洞</Text>
                  <div
                    style={{
                      fontSize: 34,
                      fontWeight: 700,
                      color: "#ff4d4f",
                      marginTop: 8,
                    }}
                  >
                    {criticalAndHighVuls.toLocaleString()}
                  </div>
                </div>
                <Tag color="red">优先处理 RCE、鉴权与资源访问缺陷</Tag>
              </div>
            </Card>
          </Col>
          <Col xs={24} sm={12} xl={6} style={{ display: "flex" }}>
            <Card
              style={{ width: "100%", height: "100%", borderRadius: 20 }}
              bodyStyle={{ height: "100%" }}
            >
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  height: "100%",
                  justifyContent: "space-between",
                }}
              >
                <div>
                  <Text type="secondary">历史公网暴露服务</Text>
                  <div
                    style={{
                      fontSize: 34,
                      fontWeight: 700,
                      color: "#1677ff",
                      marginTop: 8,
                    }}
                  >
                    {(overview?.totalExposedServices || 0).toLocaleString()}
                  </div>
                </div>
                <Space size={8} wrap>
                  <GlobalOutlined style={{ color: "#1677ff" }} />
                  <Text>
                    当前活跃实例{" "}
                    {(overview?.activeInstances || 0).toLocaleString()}
                  </Text>
                </Space>
              </div>
            </Card>
          </Col>
          <Col xs={24} sm={12} xl={6} style={{ display: "flex" }}>
            <Card
              style={{ width: "100%", height: "100%", borderRadius: 20 }}
              bodyStyle={{ height: "100%" }}
            >
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  height: "100%",
                  justifyContent: "space-between",
                }}
              >
                <div>
                  <Text type="secondary">恶意 Skills</Text>
                  <div
                    style={{
                      fontSize: 34,
                      fontWeight: 700,
                      color: "#fa541c",
                      marginTop: 8,
                    }}
                  >
                    {(securityDistribution?.malicious || 0).toLocaleString()}
                  </div>
                </div>
                <Space size={8} wrap>
                  <SafetyCertificateOutlined style={{ color: "#fa541c" }} />
                  <Text>
                    总计{" "}
                    {(
                      (securityDistribution?.safe || 0) +
                      (securityDistribution?.suspicious || 0) +
                      (securityDistribution?.malicious || 0) +
                      (securityDistribution?.unknown || 0)
                    ).toLocaleString()}
                  </Text>
                </Space>
              </div>
            </Card>
          </Col>
        </Row>

        <Row gutter={[16, 22]} align="stretch">
          <Col xs={24} xl={15} style={{ display: "flex" }}>
            <Card
              title="漏洞阶段分布"
              style={{ width: "100%", height: "100%", borderRadius: 20 }}
              bodyStyle={{ height: "100%" }}
            >
              {stageDistribution.length > 0 ? (
                <Column
                  data={stageDistribution}
                  xField="stage"
                  yField="count"
                  height={320}
                  color="#1677ff"
                  label={false}
                  axis={{
                    x: {
                      labelAutoRotate: true,
                      labelFontWeight: 700,
                      labelFill: "#1677ff",
                    },
                    y: { labelFontWeight: 700, labelFill: "#1677ff" },
                  }}
                />
              ) : (
                <Empty description="暂无漏洞阶段数据" />
              )}
            </Card>
          </Col>
          <Col xs={24} xl={9} style={{ display: "flex" }}>
            <Card
              title="漏洞严重等级"
              style={{ width: "100%", height: "100%", borderRadius: 20 }}
              bodyStyle={{ height: "100%" }}
            >
              {vulnerabilitySeverityDistribution.length > 0 ? (
                <div style={{ paddingTop: 8 }}>
                  {vulnerabilitySeverityDistribution.map((item) => {
                    const maxValue =
                      vulnerabilitySeverityDistribution[0]?.count || 1;
                    const percent = Math.round((item.count / maxValue) * 100);
                    return (
                      <div key={item.severity} style={{ marginBottom: 18 }}>
                        <div
                          style={{
                            display: "flex",
                            justifyContent: "space-between",
                            marginBottom: 8,
                          }}
                        >
                          <Text
                            strong
                            style={{ color: severityColor(item.severity) }}
                          >
                            {item.severity}
                          </Text>
                          <Text>{item.count.toLocaleString()}</Text>
                        </div>
                        <Progress
                          percent={percent}
                          strokeColor={severityColor(item.severity)}
                          showInfo={false}
                        />
                      </div>
                    );
                  })}
                </div>
              ) : (
                <Empty description="暂无漏洞严重等级数据" />
              )}
            </Card>
          </Col>
        </Row>

        <Row gutter={[16, 22]} align="stretch" style={{ marginTop: 8 }}>
          <Col xs={24} xl={12} style={{ display: "flex" }}>
            <Card
              title="全球暴露重点地区"
              style={{ width: "100%", height: "100%", borderRadius: 20 }}
              bodyStyle={{ height: "100%" }}
            >
              {topCountries.length > 0 ? (
                <div style={{ paddingTop: 4 }}>
                  {topCountries.slice(0, 5).map((country) => {
                    const percent = topCountries[0]
                      ? Math.round(
                          (country.count / topCountries[0].count) * 100,
                        )
                      : 0;

                    return (
                      <div key={country.country} style={{ marginBottom: 18 }}>
                        <div
                          style={{
                            display: "flex",
                            justifyContent: "space-between",
                            marginBottom: 8,
                          }}
                        >
                          <Text strong>
                            {countryNameMap[country.country] || country.country}
                          </Text>
                          <Text style={{ color: "#1677ff" }}>
                            {country.count.toLocaleString()}
                          </Text>
                        </div>
                        <Progress
                          percent={percent}
                          strokeColor="#1677ff"
                          showInfo={false}
                        />
                      </div>
                    );
                  })}
                </div>
              ) : (
                <Empty description="暂无暴露地区数据" />
              )}
            </Card>
          </Col>
          <Col xs={24} xl={12} style={{ display: "flex" }}>
            <Card
              title="Skills 风险分布"
              style={{ width: "100%", height: "100%", borderRadius: 20 }}
              bodyStyle={{ height: "100%" }}
            >
              {securityDistribution ? (
                <div style={{ paddingTop: 4 }}>
                  {[
                    {
                      label: "可信 Skills",
                      value: securityDistribution.safe,
                      color: "#52c41a",
                    },
                    {
                      label: "待检测 Skills",
                      value: securityDistribution.unknown || 0,
                      color: "#1677ff",
                    },
                    {
                      label: "恶意 Skills",
                      value: securityDistribution.malicious,
                      color: "#ff4d4f",
                    },
                  ].map((item) => {
                    const total =
                      securityDistribution.safe +
                      securityDistribution.malicious +
                      (securityDistribution.unknown || 0);
                    const percent =
                      total > 0 ? Math.round((item.value / total) * 100) : 0;

                    return (
                      <div key={item.label} style={{ marginBottom: 18 }}>
                        <div
                          style={{
                            display: "flex",
                            justifyContent: "space-between",
                            marginBottom: 8,
                          }}
                        >
                          <Text strong style={{ color: item.color }}>
                            {item.label}
                          </Text>
                          <Text>{item.value.toLocaleString()}</Text>
                        </div>
                        <Progress
                          percent={percent}
                          strokeColor={item.color}
                          showInfo={false}
                        />
                      </div>
                    );
                  })}
                </div>
              ) : (
                <Empty description="暂无 Skills 分布数据" />
              )}
            </Card>
          </Col>
        </Row>

      </Spin>
    </PageContainer>
  );
}
