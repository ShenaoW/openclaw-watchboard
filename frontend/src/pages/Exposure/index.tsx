import { PageContainer, ProTable } from "@ant-design/pro-components";
import {
  Badge,
  Button,
  Card,
  Col,
  Input,
  Row,
  Select,
  Space,
  Spin,
  Statistic,
  Tag,
  Tooltip,
  message,
} from "antd";
import {
  GlobalOutlined,
  MinusOutlined,
  PlusOutlined,
  ReloadOutlined,
  ScanOutlined,
  SearchOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import { Column } from "@ant-design/charts";
import { useEffect, useState } from "react";
import {
  ComposableMap,
  Geographies,
  Geography,
  Marker,
} from "react-simple-maps";
import { feature } from "topojson-client";
import worldAtlas from "world-atlas/countries-110m.json";
import {
  useExposedServices,
  useExposureOverview,
  useGeographicData,
  usePortDistribution,
} from "../../services/exposureApi";

const { Search } = Input;
const { Option } = Select;

const countryNameMap: Record<string, string> = {
  "China mainland": "中国大陆",
  "United States": "美国",
  Singapore: "新加坡",
  Germany: "德国",
  "Hong Kong": "中国香港",
  Japan: "日本",
  Russia: "俄罗斯",
  Canada: "加拿大",
  France: "法国",
  Netherlands: "荷兰",
  Australia: "澳大利亚",
  Brazil: "巴西",
  India: "印度",
  "South Korea": "韩国",
  "United Kingdom": "英国",
};

const geoData = feature(
  worldAtlas as any,
  (worldAtlas as any).objects.countries,
) as any;

function formatWan(value: number) {
  return `${(value / 10000).toFixed(2)}万`;
}

function formatAxisWan(value: string | number) {
  return `${Number(value).toFixed(1)}万`;
}

function getPortColor(port: number): string {
  if ([21, 23, 1433, 3389, 5432, 6379, 9200, 27017].includes(port))
    return "#ff4d4f";
  if ([22, 25, 8080, 8443].includes(port)) return "#fa8c16";
  return "#1677ff";
}

function getRiskColor(level: string) {
  switch (level) {
    case "Critical":
      return "red";
    case "High":
      return "orange";
    case "Medium":
      return "gold";
    case "Low":
      return "green";
    default:
      return "default";
  }
}

export default function Exposure() {
  const [searchTarget, setSearchTarget] = useState("");
  const [riskFilter, setRiskFilter] = useState("all");
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [mapScale, setMapScale] = useState(0.7);
  const mapCenterX = 400;
  const mapCenterY = 300;
  const mapOffsetY = -65;

  const {
    overview,
    loading: overviewLoading,
    error: overviewError,
  } = useExposureOverview();
  const {
    geoData: geographicData,
    loading: geoLoading,
    error: geoError,
  } = useGeographicData();
  const {
    portData,
    loading: portLoading,
    error: portError,
  } = usePortDistribution();

  const {
    services: exposedServices,
    pagination,
    loading: servicesLoading,
    error: servicesError,
  } = useExposedServices({
    search: searchTarget,
    riskLevel: riskFilter === "all" ? undefined : riskFilter,
    page: currentPage,
    limit: pageSize,
  });

  useEffect(() => {
    const errors = [overviewError, geoError, portError, servicesError].filter(
      Boolean,
    );
    if (errors.length > 0) {
      message.error(String(errors[0]));
    }
  }, [overviewError, geoError, portError, servicesError]);

  const mapMarkers = (geographicData?.world || [])
    .filter((item) => item.lat && item.lng)
    .map((item) => ({
      ...item,
      countryZh: countryNameMap[item.country] || item.country,
      radius: Math.max(4, Math.min(16, Math.sqrt(item.count) / 18)),
      color:
        item.risk >= 3 ? "#ff4d4f" : item.risk >= 2.8 ? "#fa8c16" : "#1677ff",
    }));

  const geoDisplayData = (geographicData?.world || [])
    .slice(0, 5)
    .map((item) => ({
      country: countryNameMap[item.country] || item.country,
      count: item.count,
      risk: item.risk,
    }));

  const portChartData = (portData?.common || []).slice(0, 8).map((item) => ({
    label: `${item.port}`,
    value: item.count,
    service: item.service,
    color: getPortColor(item.port),
  }));

  const riskChartData = [
    {
      label: "Critical",
      value: overview?.criticalExposures || 0,
      valueWan: (overview?.criticalExposures || 0) / 10000,
      color: "#ff4d4f",
    },
    {
      label: "High",
      value: overview?.highRiskExposures || 0,
      valueWan: (overview?.highRiskExposures || 0) / 10000,
      color: "#ff7a45",
    },
    {
      label: "Medium",
      value: overview?.mediumRiskExposures || 0,
      valueWan: (overview?.mediumRiskExposures || 0) / 10000,
      color: "#faad14",
    },
    {
      label: "Low",
      value: overview?.lowRiskExposures || 0,
      valueWan: (overview?.lowRiskExposures || 0) / 10000,
      color: "#52c41a",
    },
  ];

  const changeMapScale = (delta: number) => {
    setMapScale((current) =>
      Math.min(1.2, Math.max(0.55, Number((current + delta).toFixed(2)))),
    );
  };

  const resetMapScale = () => {
    setMapScale(0.7);
  };

  const portColumnConfig = {
    data: portChartData,
    xField: "label",
    yField: "value",
    height: 320,
    legend: false,
    colorField: "label",
    color: ({ label }: { label: string }) =>
      portChartData.find((item) => item.label === label)?.color || "#1677ff",
    columnStyle: {
      radius: [6, 6, 0, 0],
    },
    label: false,
    meta: {
      value: {
        formatter: (value: number) => value.toLocaleString(),
      },
    },
    axis: {
      x: {
        title: true,
        titleText: "端口",
        labelFontWeight: 700,
        labelFill: "#1677ff",
        titleFill: "#1677ff",
        titleFontWeight: 700,
      },
      y: {
        title: true,
        titleText: "暴露数量",
        labelFormatter: (value: string) => Number(value).toLocaleString(),
        labelFontWeight: 700,
        labelFill: "#1677ff",
        titleFill: "#1677ff",
        titleFontWeight: 700,
      },
    },
    tooltip: {
      items: ["label", "service", "value"],
      customItems: (items: any[]) =>
        items.map((item) => ({
          ...item,
          name:
            item.name === "label"
              ? "端口"
              : item.name === "service"
                ? "服务"
                : "暴露数量",
          value:
            item.name === "value"
              ? Number(item.data.value).toLocaleString()
              : item.value,
        })),
    },
  };

  const riskColumnConfig = {
    data: riskChartData,
    xField: "label",
    yField: "valueWan",
    height: 320,
    legend: false,
    colorField: "label",
    color: ({ label }: { label: string }) =>
      riskChartData.find((item) => item.label === label)?.color || "#1677ff",
    columnStyle: {
      radius: [6, 6, 0, 0],
    },
    label: false,
    meta: {
      valueWan: {
        formatter: (value: number) => formatAxisWan(value),
      },
    },
    axis: {
      x: {
        title: true,
        titleText: "风险等级",
        labelFontWeight: 700,
        labelFill: "#1677ff",
        titleFill: "#1677ff",
        titleFontWeight: 700,
      },
      y: {
        title: true,
        titleText: "数量（万）",
        labelFormatter: (value: string) => formatAxisWan(value),
        labelFontWeight: 700,
        labelFill: "#1677ff",
        titleFill: "#1677ff",
        titleFontWeight: 700,
      },
    },
    tooltip: {
      items: ["label", "value"],
      customItems: (items: any[]) =>
        items.map((item) => ({
          ...item,
          value: `${Number(item.data.value).toLocaleString()} / ${formatWan(Number(item.data.value))}`,
        })),
    },
  };

  const columns = [
    {
      title: "IP地址",
      dataIndex: "ip",
      key: "ip",
      render: (ip: string) => <code style={{ color: "#1677ff" }}>{ip}</code>,
    },
    {
      title: "主机名",
      dataIndex: "hostname",
      key: "hostname",
      render: (hostname: string) => hostname || "-",
    },
    {
      title: "端口/服务",
      key: "service",
      render: (record: any) => (
        <div>
          <div>
            <strong>{record.port}</strong> / {record.service}
          </div>
          <div style={{ fontSize: 12, color: "#999" }}>{record.banner}</div>
        </div>
      ),
    },
    {
      title: "地理位置",
      key: "location",
      render: (record: any) => (
        <div>
          <div>
            {record.country}, {record.city}
          </div>
          <div style={{ fontSize: 12, color: "#999" }}>{record.asn}</div>
        </div>
      ),
    },
    {
      title: "风险等级",
      dataIndex: "riskLevel",
      key: "riskLevel",
      render: (level: string) => (
        <Tag color={getRiskColor(level)} icon={<WarningOutlined />}>
          {level}
        </Tag>
      ),
    },
    {
      title: "漏洞",
      dataIndex: "vulnerabilities",
      key: "vulnerabilities",
      render: (vulns: string[]) =>
        vulns.length > 0 ? (
          <div>
            {vulns.map((vuln) => (
              <Tag key={vuln} color="red">
                {vuln}
              </Tag>
            ))}
          </div>
        ) : (
          <Badge status="success" text="无已知漏洞" />
        ),
    },
    {
      title: "最后发现",
      dataIndex: "lastSeen",
      key: "lastSeen",
      render: (time: string) => <span style={{ fontSize: 12 }}>{time}</span>,
    },
  ];

  return (
    <PageContainer
      title="公网暴露情况分析"
      subTitle="OpenClaw 服务暴露监控与地理分布"
      extra={[
        <Button key="scan" type="primary" icon={<ScanOutlined />}>
          触发扫描
        </Button>,
      ]}
    >
      <Spin spinning={overviewLoading}>
        <Row gutter={16} style={{ marginBottom: 24 }} align="stretch">
          <Col span={6} style={{ display: "flex" }}>
            <Card
              style={{ width: "100%", height: "100%" }}
              bodyStyle={{ height: "100%" }}
            >
              <div
                style={{
                  minHeight: 96,
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                }}
              >
                <Statistic
                  title="暴露服务总数"
                  value={overview?.totalExposedServices || 0}
                  formatter={(value) => Number(value).toLocaleString()}
                  prefix={<GlobalOutlined />}
                  valueStyle={{ color: "#1677ff" }}
                />
              </div>
            </Card>
          </Col>
          <Col span={6} style={{ display: "flex" }}>
            <Card
              style={{ width: "100%", height: "100%" }}
              bodyStyle={{ height: "100%" }}
            >
              <div
                style={{
                  minHeight: 96,
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                }}
              >
                <Statistic
                  title="高危暴露"
                  value={overview?.criticalExposures || 0}
                  formatter={(value) => Number(value).toLocaleString()}
                  valueStyle={{ color: "#ff4d4f" }}
                />
                <div style={{ marginTop: 8 }}>
                  <Badge status="error" text="需要立即处理" />
                </div>
              </div>
            </Card>
          </Col>
          <Col span={6} style={{ display: "flex" }}>
            <Card
              style={{ width: "100%", height: "100%" }}
              bodyStyle={{ height: "100%" }}
            >
              <div
                style={{
                  minHeight: 96,
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                }}
              >
                <Statistic
                  title="覆盖国家/地区"
                  value={geographicData?.world?.length || 0}
                  valueStyle={{ color: "#52c41a" }}
                />
              </div>
            </Card>
          </Col>
          <Col span={6} style={{ display: "flex" }}>
            <Card
              style={{ width: "100%", height: "100%" }}
              bodyStyle={{ height: "100%" }}
            >
              <div
                style={{
                  minHeight: 96,
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                }}
              >
                <Statistic
                  title="最新扫描"
                  value={
                    overview?.lastScanTime
                      ? new Date(overview.lastScanTime).toLocaleString()
                      : "-"
                  }
                  valueStyle={{ color: "#722ed1" }}
                />
              </div>
            </Card>
          </Col>
        </Row>
      </Spin>

      <Card title="🌍 全球暴露分布热力图" style={{ marginBottom: 16 }}>
        <div
          style={{
            height: 430,
            borderRadius: 12,
            overflow: "hidden",
            position: "relative",
            background: "linear-gradient(180deg, #eef6ff 0%, #f8fbff 100%)",
            border: "1px solid #d6e4ff",
          }}
        >
          <div
            style={{
              position: "absolute",
              right: 16,
              top: 16,
              zIndex: 2,
              display: "flex",
              flexDirection: "column",
              gap: 8,
            }}
          >
            <Button
              size="small"
              icon={<PlusOutlined />}
              onClick={() => changeMapScale(0.08)}
            />
            <Button
              size="small"
              icon={<MinusOutlined />}
              onClick={() => changeMapScale(-0.08)}
            />
            <Button
              size="small"
              icon={<ReloadOutlined />}
              onClick={resetMapScale}
            />
          </div>
          <Spin spinning={geoLoading}>
            <ComposableMap
              projection="geoMercator"
              projectionConfig={{ scale: 118 }}
              style={{ width: "100%", height: "100%" }}
            >
              <g
                transform={`translate(${mapCenterX} ${mapCenterY}) scale(${mapScale}) translate(${-mapCenterX} ${-mapCenterY + mapOffsetY})`}
              >
                <Geographies geography={geoData}>
                  {({ geographies }) =>
                    geographies.map((geography) => (
                      <Geography
                        key={geography.rsmKey}
                        geography={geography}
                        style={{
                          default: {
                            fill: "#dbeafe",
                            outline: "none",
                            stroke: "#93c5fd",
                            strokeWidth: 0.5,
                          },
                          hover: {
                            fill: "#bfdbfe",
                            outline: "none",
                            stroke: "#60a5fa",
                            strokeWidth: 0.8,
                          },
                          pressed: { fill: "#93c5fd", outline: "none" },
                        }}
                      />
                    ))
                  }
                </Geographies>
                {mapMarkers.map((point) => (
                  <Marker
                    key={`${point.country}-${point.code}`}
                    coordinates={[point.lng, point.lat]}
                  >
                    <g>
                      <circle
                        r={point.radius + 2}
                        fill={point.color}
                        opacity={0.22}
                      >
                        <animate
                          attributeName="r"
                          values={`${point.radius};${point.radius + 12}`}
                          dur="2.6s"
                          repeatCount="indefinite"
                        />
                        <animate
                          attributeName="opacity"
                          values="0.26;0"
                          dur="2.6s"
                          repeatCount="indefinite"
                        />
                      </circle>
                      <circle
                        r={point.radius + 2}
                        fill={point.color}
                        opacity={0.18}
                      >
                        <animate
                          attributeName="r"
                          values={`${point.radius};${point.radius + 16}`}
                          dur="2.6s"
                          begin="1.1s"
                          repeatCount="indefinite"
                        />
                        <animate
                          attributeName="opacity"
                          values="0.22;0"
                          dur="2.6s"
                          begin="1.1s"
                          repeatCount="indefinite"
                        />
                      </circle>
                      <Tooltip
                        title={`${point.countryZh}: ${point.count.toLocaleString()}，风险 ${point.risk}`}
                      >
                        <circle
                          r={point.radius}
                          fill={point.color}
                          fillOpacity={0.72}
                          stroke="#fff"
                          strokeWidth={1.5}
                          style={{ cursor: "pointer" }}
                        />
                      </Tooltip>
                    </g>
                  </Marker>
                ))}
              </g>
            </ComposableMap>
          </Spin>
        </div>
        <Row gutter={16} style={{ marginTop: 16 }}>
          {geoDisplayData.map((item) => (
            <Col key={item.country} flex="1 1 0">
              <div style={{ textAlign: "center", padding: "8px 0" }}>
                <div
                  style={{ fontSize: 20, fontWeight: "bold", color: "#1677ff" }}
                >
                  {item.count.toLocaleString()}
                </div>
                <div style={{ fontSize: 12, color: "#666" }}>
                  {item.country}
                </div>
                <div style={{ fontSize: 12, color: "#ff4d4f" }}>
                  风险系数: {item.risk}
                </div>
              </div>
            </Col>
          ))}
        </Row>
      </Card>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Card title="📊 端口分布统计">
            <Spin spinning={portLoading}>
              <Column {...portColumnConfig} />
            </Spin>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="⚠️ 风险等级分布">
            <Spin spinning={overviewLoading}>
              <Column {...riskColumnConfig} />
            </Spin>
          </Card>
        </Col>
      </Row>

      <Card title="📋 暴露服务详情">
        <div style={{ marginBottom: 16 }}>
          <Space>
            <Search
              placeholder="搜索IP地址或主机名"
              allowClear
              style={{ width: 300 }}
              onSearch={(value) => {
                setSearchTarget(value);
                setCurrentPage(1);
              }}
              defaultValue={searchTarget}
            />
            <Select
              placeholder="筛选风险等级"
              style={{ width: 150 }}
              value={riskFilter}
              onChange={(value) => {
                setRiskFilter(value);
                setCurrentPage(1);
              }}
            >
              <Option value="all">全部风险</Option>
              <Option value="Critical">Critical</Option>
              <Option value="High">High</Option>
              <Option value="Medium">Medium</Option>
              <Option value="Low">Low</Option>
            </Select>
            <Button icon={<SearchOutlined />}>高级搜索</Button>
          </Space>
        </div>

        <Spin spinning={servicesLoading}>
          <ProTable
            dataSource={exposedServices}
            columns={columns}
            rowKey="id"
            search={false}
            loading={servicesLoading}
            pagination={{
              current: pagination.page,
              pageSize: pagination.limit,
              total: pagination.total,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total) => `共 ${total} 条记录`,
              onChange: (page, size) => {
                setCurrentPage(page);
                setPageSize(size || 20);
              },
              onShowSizeChange: (_, size) => {
                setCurrentPage(1);
                setPageSize(size);
              },
            }}
            scroll={{ x: 1200 }}
            options={{
              density: false,
              fullScreen: true,
              setting: true,
            }}
          />
        </Spin>
      </Card>
    </PageContainer>
  );
}
