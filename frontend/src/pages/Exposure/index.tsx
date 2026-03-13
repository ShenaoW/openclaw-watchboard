import { PageContainer, ProTable } from "@ant-design/pro-components";
import {
  Badge,
  Button,
  Card,
  Col,
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
} from "@ant-design/icons";
import { Column, Line } from "@ant-design/charts";
import { useEffect, useRef, useState } from "react";
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
  useExposureTrends,
} from "../../services/exposureApi";

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

const provinceNameMap: Record<string, string> = {
  Beijing: "北京",
  Shanghai: "上海",
  Tianjin: "天津",
  Chongqing: "重庆",
  Guangdong: "广东",
  Zhejiang: "浙江",
  Jiangsu: "江苏",
  Shandong: "山东",
  Sichuan: "四川",
  Hubei: "湖北",
  Hunan: "湖南",
  Henan: "河南",
  Hebei: "河北",
  Fujian: "福建",
  Anhui: "安徽",
  Jiangxi: "江西",
  Shaanxi: "陕西",
  Liaoning: "辽宁",
  Jilin: "吉林",
  Heilongjiang: "黑龙江",
  "Hong Kong": "香港",
  HongKong: "香港",
  Hainan: "海南",
  Guangxi: "广西",
  "Guangxi Zhuangzu": "广西",
  Yunnan: "云南",
  Guizhou: "贵州",
  Gansu: "甘肃",
  Shanxi: "山西",
  "Nei Mongol": "内蒙古",
  Xinjiang: "新疆",
  "Xinjiang Uygur": "新疆",
  Tibet: "西藏",
  Qinghai: "青海",
  "Ningxia Huizu": "宁夏",
};

const cityNameMap: Record<string, string> = {
  Beijing: "北京",
  Shanghai: "上海",
  Guangzhou: "广州",
  Hangzhou: "杭州",
  "Hong Kong": "香港",
  Shenzhen: "深圳",
  Chengdu: "成都",
  Nanjing: "南京",
  Qingdao: "青岛",
  Guiyang: "贵阳",
  Xiamen: "厦门",
  Chongqing: "重庆",
  Wuhan: "武汉",
  Suzhou: "苏州",
  Yangzhou: "扬州",
  Huizhou: "惠州",
  Ningbo: "宁波",
  Lanzhou: "兰州",
  Fuzhou: "福州",
  Leshan: "乐山",
  Zhengzhou: "郑州",
  Hefei: "合肥",
  Jinan: "济南",
  Tianjin: "天津",
  Changsha: "长沙",
  Shiyan: "十堰",
  Taizhou: "台州",
  Kunming: "昆明",
  Wenzhou: "温州",
  Dongguan: "东莞",
  Xiangyang: "襄阳",
  Guyuan: "固原",
  Nanchang: "南昌",
  Fuqing: "福清",
  Wuxi: "无锡",
  Zhongshan: "中山",
  Zhenjiang: "镇江",
  Hohhot: "呼和浩特",
  Jinhua: "金华",
  "Xi'an": "西安",
  Shenyang: "沈阳",
  Linyi: "临沂",
  Jiaxing: "嘉兴",
  Zhongwei: "中卫",
  Jiangmen: "江门",
  Zhangzhou: "漳州",
  Suqian: "宿迁",
  Harbin: "哈尔滨",
  Huzhou: "湖州",
  Quanzhou: "泉州",
  Xinyang: "信阳",
  Shaoxing: "绍兴",
  Xuzhou: "徐州",
  Nanning: "南宁",
  Weihai: "威海",
  Shijiazhuang: "石家庄",
  Dalian: "大连",
  Foshan: "佛山",
  Xuchang: "许昌",
  Langfang: "廊坊",
  Taiyuan: "太原",
  Haikou: "海口",
  Ningde: "宁德",
  Changzhou: "常州",
  Changchun: "长春",
  Yichang: "宜昌",
  Putian: "莆田",
  Nantong: "南通",
  Fuyang: "阜阳",
  Wuhu: "芜湖",
  Shaoyang: "邵阳",
  Jilin: "吉林",
  Luoyang: "洛阳",
  Yantai: "烟台",
  Weifang: "潍坊",
  Yiwu: "义乌",
  Yancheng: "盐城",
  "Ma'anshan": "马鞍山",
  Chizhou: "池州",
  Shihezi: "石河子",
  "Lu'an": "六安",
  Zhuhai: "珠海",
  Meishan: "眉山",
  Yinchuan: "银川",
  Baoding: "保定",
  Jingdezhen: "景德镇",
  Benxi: "本溪",
  Panjin: "盘锦",
  Jiujiang: "九江",
  Maoming: "茂名",
  Meizhou: "梅州",
  Qingyuan: "清远",
  Shantou: "汕头",
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

function getRuntimeStatusColor(status: string) {
  switch (status) {
    case "Active":
      return "green";
    case "Inactive":
      return "red";
    default:
      return "default";
  }
}

function getWorldDistributionColor(count: number, maxCount: number) {
  const ratio = maxCount > 0 ? Math.min(Math.max(count / maxCount, 0), 1) : 0;
  if (ratio >= 0.75) return "#ff4d4f";
  if (ratio >= 0.5) return "#ff7a45";
  if (ratio >= 0.25) return "#fadb14";
  return "#1677ff";
}

function getChinaDistributionColor(count: number, maxCount: number) {
  const ratio = maxCount > 0 ? Math.min(Math.max(count / maxCount, 0), 1) : 0;
  if (ratio >= 0.6) return "#ff4d4f";
  if (ratio >= 0.35) return "#fa8c16";
  if (ratio >= 0.12) return "#fadb14";
  return "#4f86ff";
}

const exposureSummaryOverrides = {
  chinaExposedServices: 58812,
  coveredCountries: 100,
  provinceCount: 30,
  cityCount: 195,
};

export default function Exposure() {
  const [runtimeStatusFilter, setRuntimeStatusFilter] = useState("all");
  const [chinaScopeFilter, setChinaScopeFilter] = useState("all");
  const [versionStatusFilter, setVersionStatusFilter] = useState("all");
  const [historicalVulnFilter, setHistoricalVulnFilter] = useState("all");
  const [historicalVulnCountFilter, setHistoricalVulnCountFilter] =
    useState("all");
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [mapScale, setMapScale] = useState(0.94);
  const [chinaMapScale, setChinaMapScale] = useState(1);
  const [chinaMapOffset, setChinaMapOffset] = useState({ x: -20, y: -120 });
  const dragStateRef = useRef<{
    dragging: boolean;
    startX: number;
    startY: number;
    originX: number;
    originY: number;
  }>({
    dragging: false,
    startX: 0,
    startY: 0,
    originX: 0,
    originY: 0,
  });
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
    trendData,
    loading: trendLoading,
    error: trendError,
  } = useExposureTrends("30d");

  const {
    services: exposedServices,
    pagination,
    loading: servicesLoading,
    error: servicesError,
  } = useExposedServices({
    runtimeStatus:
      runtimeStatusFilter === "all" ? undefined : runtimeStatusFilter,
    chinaScope: chinaScopeFilter === "all" ? undefined : chinaScopeFilter,
    versionStatus:
      versionStatusFilter === "all" ? undefined : versionStatusFilter,
    historicalVulnStatus:
      historicalVulnFilter === "all" ? undefined : historicalVulnFilter,
    historicalVulnCountRange:
      historicalVulnCountFilter === "all"
        ? undefined
        : historicalVulnCountFilter,
    page: currentPage,
    limit: pageSize,
  });

  useEffect(() => {
    const errors = [
      overviewError,
      geoError,
      portError,
      trendError,
      servicesError,
    ].filter(Boolean);
    if (errors.length > 0) {
      message.error(String(errors[0]));
    }
  }, [overviewError, geoError, portError, trendError, servicesError]);

  const worldMaxCount = Math.max(
    ...(geographicData?.world || []).map((item) => item.count),
    1,
  );
  const chinaMaxCount = Math.max(
    ...(geographicData?.china || []).map((item) => item.count),
    1,
  );

  const mapMarkers = (geographicData?.world || [])
    .filter((item) => item.lat && item.lng)
    .map((item) => ({
      ...item,
      countryZh: countryNameMap[item.country] || item.country,
      radius: Math.max(4, Math.min(16, Math.sqrt(item.count) / 18)),
      color: getWorldDistributionColor(item.count, worldMaxCount),
    }));

  const chinaMarkers = (geographicData?.china || []).map((item) => ({
    ...item,
    radius: Math.max(5, Math.min(18, Math.sqrt(item.count) / 6)),
    color: getChinaDistributionColor(item.count, chinaMaxCount),
    provinceZh: provinceNameMap[item.province] || item.province,
    cityZh: cityNameMap[item.city] || item.city,
  }));

  const geoDisplayData = (geographicData?.world || [])
    .slice(0, 5)
    .map((item) => ({
      country: countryNameMap[item.country] || item.country,
      count: item.count,
    }));

  const portChartData = (portData?.common || []).slice(0, 8).map((item) => ({
    label: `${item.port}`,
    value: item.count,
    service: item.service,
    color: getPortColor(item.port),
  }));

  const provinceChartData = (geographicData?.provinceTop || []).map((item) => ({
    label: provinceNameMap[item.province] || item.province,
    value: item.count,
  }));

  const chinaCityTopData = (geographicData?.cityTop || []).map((item) => ({
    city:
      cityNameMap[item.city] ||
      item.city ||
      provinceNameMap[item.province] ||
      item.province,
    count: item.count,
  }));

  const changeMapScale = (delta: number) => {
    setMapScale((current) =>
      Math.min(1.2, Math.max(0.55, Number((current + delta).toFixed(2)))),
    );
  };

  const resetMapScale = () => {
    setMapScale(0.94);
  };

  const changeChinaMapScale = (delta: number) => {
    setChinaMapScale((current) =>
      Math.min(2.4, Math.max(0.8, Number((current + delta).toFixed(2)))),
    );
  };

  const resetChinaMapView = () => {
    setChinaMapScale(1);
    setChinaMapOffset({ x: -85, y: -10 });
  };

  const startChinaMapDrag = (clientX: number, clientY: number) => {
    dragStateRef.current = {
      dragging: true,
      startX: clientX,
      startY: clientY,
      originX: chinaMapOffset.x,
      originY: chinaMapOffset.y,
    };
  };

  const moveChinaMapDrag = (clientX: number, clientY: number) => {
    if (!dragStateRef.current.dragging) {
      return;
    }

    const deltaX = clientX - dragStateRef.current.startX;
    const deltaY = clientY - dragStateRef.current.startY;
    setChinaMapOffset({
      x: dragStateRef.current.originX + deltaX,
      y: dragStateRef.current.originY + deltaY,
    });
  };

  const stopChinaMapDrag = () => {
    dragStateRef.current.dragging = false;
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

  const provinceColumnConfig = {
    data: provinceChartData,
    xField: "label",
    yField: "value",
    height: 320,
    legend: false,
    color: "#1677ff",
    columnStyle: {
      radius: [6, 6, 0, 0],
    },
    label: false,
    axis: {
      x: {
        title: true,
        titleText: "省份",
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
      items: ["label", "value"],
      customItems: (items: any[]) =>
        items.map((item) => ({
          ...item,
          value: Number(item.data.value).toLocaleString(),
        })),
    },
  };

  const evolutionChartData = trendData.flatMap((item) => [
    { date: item.date, type: "首次发现", value: item.firstSeen },
    { date: item.date, type: "最后发现", value: item.lastSeen },
    { date: item.date, type: "活跃实例", value: item.active },
  ]);

  const evolutionLineConfig = {
    data: evolutionChartData,
    xField: "date",
    yField: "value",
    seriesField: "type",
    height: 320,
    colorField: "type",
    color: ({ type }: { type: string }) => {
      if (type === "首次发现") return "#1677ff";
      if (type === "最后发现") return "#ff7a45";
      return "#52c41a";
    },
    smooth: true,
    point: {
      size: 3,
      shape: "circle",
      style: {
        lineWidth: 1.5,
        fill: "#fff",
      },
    },
    axis: {
      x: {
        title: true,
        titleText: "日期",
        labelAutoRotate: true,
        labelFill: "#1677ff",
      },
      y: {
        title: true,
        titleText: "实例数量",
        labelFormatter: (value: string) => Number(value).toLocaleString(),
        labelFill: "#1677ff",
      },
    },
    legend: {
      color: {
        title: false,
        position: "top",
      },
      position: "top",
    },
    tooltip: {
      items: ["type", "value"],
      customItems: (items: any[]) =>
        items.map((item) => ({
          ...item,
          value: Number(item.value).toLocaleString(),
        })),
    },
  };

  const columns = [
    {
      title: "IP地址",
      dataIndex: "maskedIp",
      key: "maskedIp",
      render: (_: string, record: any) => (
        <code style={{ color: "#1677ff" }}>{record.maskedIp || record.ip}</code>
      ),
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
          <div>{record.country}</div>
          <div style={{ fontSize: 12, color: "#999" }}>{record.asn}</div>
        </div>
      ),
    },
    {
      title: "运行状态",
      dataIndex: "runtimeStatus",
      key: "runtimeStatus",
      render: (status: string) => (
        <Tag color={getRuntimeStatusColor(status)}>{status}</Tag>
      ),
    },
    {
      title: "境内实例",
      dataIndex: "isChinaInstance",
      key: "isChinaInstance",
      render: (_: unknown, record: any) =>
        record.isChinaInstance ? (
          <Space size={4} wrap>
            <Tag color="cyan">中国境内</Tag>
          </Space>
        ) : (
          <Tag>海外</Tag>
        ),
    },
    {
      title: "境内位置",
      key: "chinaLocation",
      render: (_: unknown, record: any) =>
        record.isChinaInstance ? (
          <span>
            {(() => {
              const province =
                provinceNameMap[record.province || ""] ||
                record.province ||
                "-";
              const city = cityNameMap[record.cnCity] || record.cnCity || "";
              return city && city !== province
                ? `${province} / ${city}`
                : province;
            })()}
          </span>
        ) : (
          "-"
        ),
    },
    {
      title: "版本号",
      dataIndex: "serverVersion",
      key: "serverVersion",
      render: (serverVersion?: string | null) =>
        serverVersion ? (
          <Tag color="blue">{serverVersion}</Tag>
        ) : (
          <Badge status="default" text="未探测到" />
        ),
    },
    {
      title: "历史漏洞关联",
      key: "historicalVulnerabilities",
      render: (_: unknown, record: any) => {
        const count = Number(record.historicalVulnCount || 0);
        if (!count) {
          return <Badge status="default" text="未关联到历史漏洞" />;
        }

        const matches = Array.isArray(record.historicalVulnMatches)
          ? record.historicalVulnMatches
          : [];
        const tooltipContent = (
          <div style={{ maxWidth: 420 }}>
            {matches.slice(0, 4).map((item: any) => (
              <div
                key={`${item.vulnerability_id}-${item.title}`}
                style={{ marginBottom: 8 }}
              >
                <div style={{ fontWeight: 700 }}>
                  {item.vulnerability_id || item.cve || "漏洞条目"}
                </div>
                <div>{item.title}</div>
                <div style={{ color: "#bfbfbf", fontSize: 12 }}>
                  {item.severity} · {item.affected_versions}
                </div>
              </div>
            ))}
            {count > 4 ? (
              <div style={{ color: "#bfbfbf" }}>其余 {count - 4} 条未展开</div>
            ) : null}
          </div>
        );

        return (
          <Space size={6} wrap>
            <Tooltip title={tooltipContent}>
              <Tag color="volcano">关联 {count} 条</Tag>
            </Tooltip>
            {record.historicalVulnMaxSeverity ? (
              <Tag
                color={
                  record.historicalVulnMaxSeverity === "Critical"
                    ? "red"
                    : record.historicalVulnMaxSeverity === "High"
                      ? "orange"
                      : "gold"
                }
              >
                {record.historicalVulnMaxSeverity}
              </Tag>
            ) : null}
          </Space>
        );
      },
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
                  justifyContent: "center",
                  gap: 10,
                }}
              >
                <div>
                  <div
                    style={{ fontSize: 13, color: "#8c8c8c", marginBottom: 6 }}
                  >
                    历史暴露服务总数
                  </div>
                  <div
                    style={{ fontSize: 26, fontWeight: 600, color: "#1677ff" }}
                  >
                    {(overview?.totalExposedServices || 0).toLocaleString()}
                  </div>
                </div>
                <div style={{ borderTop: "1px solid #f0f0f0", paddingTop: 10 }}>
                  <div
                    style={{ fontSize: 13, color: "#8c8c8c", marginBottom: 6 }}
                  >
                    当前活跃实例总数
                  </div>
                  <div
                    style={{ fontSize: 26, fontWeight: 600, color: "#52c41a" }}
                  >
                    {(overview?.activeInstances || 0).toLocaleString()}
                  </div>
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
                  justifyContent: "center",
                  gap: 10,
                }}
              >
                <div>
                  <div
                    style={{ fontSize: 13, color: "#8c8c8c", marginBottom: 6 }}
                  >
                    境内暴露总数
                  </div>
                  <div
                    style={{ fontSize: 26, fontWeight: 600, color: "#13a8a8" }}
                  >
                    {exposureSummaryOverrides.chinaExposedServices.toLocaleString()}
                  </div>
                </div>
                <div style={{ borderTop: "1px solid #f0f0f0", paddingTop: 10 }}>
                  <div
                    style={{ fontSize: 13, color: "#8c8c8c", marginBottom: 6 }}
                  >
                    境内活跃实例数量
                  </div>
                  <div
                    style={{ fontSize: 26, fontWeight: 600, color: "#08979c" }}
                  >
                    {(overview?.chinaActiveInstances || 0).toLocaleString()}
                  </div>
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
                  justifyContent: "center",
                  gap: 10,
                }}
              >
                <div>
                  <div
                    style={{ fontSize: 13, color: "#8c8c8c", marginBottom: 6 }}
                  >
                    覆盖国家/地区
                  </div>
                  <div
                    style={{ fontSize: 26, fontWeight: 600, color: "#722ed1" }}
                  >
                    {exposureSummaryOverrides.coveredCountries.toLocaleString()}
                  </div>
                </div>
                <div style={{ borderTop: "1px solid #f0f0f0", paddingTop: 10 }}>
                  <div
                    style={{ fontSize: 13, color: "#8c8c8c", marginBottom: 6 }}
                  >
                    涉及省市
                  </div>
                  <div
                    style={{ fontSize: 26, fontWeight: 600, color: "#531dab" }}
                  >
                    {exposureSummaryOverrides.provinceCount.toLocaleString()} /{" "}
                    {exposureSummaryOverrides.cityCount.toLocaleString()}
                  </div>
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
                  justifyContent: "center",
                  gap: 10,
                }}
              >
                <div>
                  <div
                    style={{ fontSize: 13, color: "#8c8c8c", marginBottom: 6 }}
                  >
                    存在漏洞的暴露实例
                  </div>
                  <div
                    style={{ fontSize: 26, fontWeight: 600, color: "#fa541c" }}
                  >
                    {(
                      overview?.historicalVulnerableInstances || 0
                    ).toLocaleString()}
                  </div>
                </div>
                <div style={{ borderTop: "1px solid #f0f0f0", paddingTop: 10 }}>
                  <div
                    style={{ fontSize: 13, color: "#8c8c8c", marginBottom: 6 }}
                  >
                    合计历史漏洞条目数
                  </div>
                  <div
                    style={{ fontSize: 26, fontWeight: 600, color: "#cf1322" }}
                  >
                    {(
                      overview?.historicalMatchedVulnerabilityCount || 0
                    ).toLocaleString()}
                  </div>
                </div>
              </div>
            </Card>
          </Col>
        </Row>
      </Spin>

      <Card title="📈 暴露实例演化趋势" style={{ marginBottom: 16 }}>
        <Spin spinning={trendLoading}>
          <Line {...evolutionLineConfig} />
        </Spin>
      </Card>

      <Card title="🌍 全球暴露实例分布图" style={{ marginBottom: 16 }}>
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
                        title={`${point.countryZh}: ${point.count.toLocaleString()}`}
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
              </div>
            </Col>
          ))}
        </Row>
      </Card>

      <Card title="🇨🇳 境内暴露实例分布图" style={{ marginBottom: 16 }}>
        <div
          style={{
            height: 420,
            borderRadius: 12,
            overflow: "hidden",
            position: "relative",
            background: "linear-gradient(180deg, #eef6ff 0%, #f8fbff 100%)",
            border: "1px solid #d6e4ff",
          }}
          onMouseMove={(event) =>
            moveChinaMapDrag(event.clientX, event.clientY)
          }
          onMouseUp={stopChinaMapDrag}
          onMouseLeave={stopChinaMapDrag}
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
              onClick={() => changeChinaMapScale(0.12)}
            />
            <Button
              size="small"
              icon={<MinusOutlined />}
              onClick={() => changeChinaMapScale(-0.12)}
            />
            <Button
              size="small"
              icon={<ReloadOutlined />}
              onClick={resetChinaMapView}
            />
          </div>
          <Spin spinning={geoLoading}>
            <ComposableMap
              projection="geoMercator"
              projectionConfig={{ scale: 420, center: [104, 35] }}
              style={{ width: "100%", height: "100%" }}
            >
              <g
                transform={`translate(${chinaMapOffset.x} ${chinaMapOffset.y}) scale(${chinaMapScale})`}
                style={{
                  cursor: dragStateRef.current.dragging ? "grabbing" : "grab",
                }}
                onMouseDown={(event) =>
                  startChinaMapDrag(event.clientX, event.clientY)
                }
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
                {chinaMarkers.map((point) => (
                  <Marker
                    key={`${point.province}-${point.city}`}
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
                      <Tooltip
                        title={`${point.cityZh && point.cityZh !== point.provinceZh ? `${point.provinceZh} / ${point.cityZh}` : point.provinceZh}: ${point.count.toLocaleString()}`}
                      >
                        <circle
                          r={point.radius}
                          fill={point.color}
                          fillOpacity={0.78}
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
          {chinaCityTopData.map((item) => (
            <Col key={item.city} flex="1 1 0">
              <div style={{ textAlign: "center", padding: "8px 0" }}>
                <div
                  style={{ fontSize: 20, fontWeight: "bold", color: "#1677ff" }}
                >
                  {item.count.toLocaleString()}
                </div>
                <div style={{ fontSize: 12, color: "#666" }}>{item.city}</div>
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
          <Card title="🏙️ 省份分布 Top 5">
            <Spin spinning={geoLoading}>
              <Column {...provinceColumnConfig} />
            </Spin>
          </Card>
        </Col>
      </Row>

      <Card title="📋 暴露服务详情">
        <div style={{ marginBottom: 16 }}>
          <Space wrap>
            <Select
              placeholder="筛选运行状态"
              style={{ width: 150 }}
              value={runtimeStatusFilter}
              onChange={(value) => {
                setRuntimeStatusFilter(value);
                setCurrentPage(1);
              }}
            >
              <Option value="all">全部状态</Option>
              <Option value="Active">Active</Option>
              <Option value="Inactive">Inactive</Option>
              <Option value="Unknown">Unknown</Option>
            </Select>
            <Select
              placeholder="境内外分布"
              style={{ width: 150 }}
              value={chinaScopeFilter}
              onChange={(value) => {
                setChinaScopeFilter(value);
                setCurrentPage(1);
              }}
            >
              <Option value="all">全部范围</Option>
              <Option value="china">境内实例</Option>
              <Option value="overseas">境外实例</Option>
            </Select>
            <Select
              placeholder="版本信息"
              style={{ width: 150 }}
              value={versionStatusFilter}
              onChange={(value) => {
                setVersionStatusFilter(value);
                setCurrentPage(1);
              }}
            >
              <Option value="all">全部版本</Option>
              <Option value="detected">已探测版本</Option>
              <Option value="undetected">未探测版本</Option>
            </Select>
            <Select
              placeholder="历史漏洞关联"
              style={{ width: 170 }}
              value={historicalVulnFilter}
              onChange={(value) => {
                setHistoricalVulnFilter(value);
                setCurrentPage(1);
              }}
            >
              <Option value="all">全部实例</Option>
              <Option value="matched">可关联历史漏洞</Option>
              <Option value="unmatched">未关联历史漏洞</Option>
            </Select>
            <Select
              placeholder="关联漏洞数量"
              style={{ width: 170 }}
              value={historicalVulnCountFilter}
              onChange={(value) => {
                setHistoricalVulnCountFilter(value);
                setCurrentPage(1);
              }}
            >
              <Option value="all">关联漏洞数量</Option>
              <Option value="1-2">1-2 条</Option>
              <Option value="3-9">3-9 条</Option>
              <Option value="10+">10 条以上</Option>
            </Select>
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
            scroll={{ x: 1300 }}
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
