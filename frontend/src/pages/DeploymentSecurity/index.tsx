import { PageContainer } from '@ant-design/pro-components';
import { Alert, Button, Card, Col, Divider, List, Row, Space, Statistic, Steps, Tag, Typography } from 'antd';
import {
  CheckCircleOutlined,
  DownloadOutlined,
  DeploymentUnitOutlined,
  FileSearchOutlined,
  RadarChartOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import sampleReport from './sampleReport.json';

const capabilityCards = [
  {
    title: '版本与漏洞匹配',
    description: '识别本地 OpenClaw 版本，结合漏洞库匹配受影响版本区间。',
    icon: <RadarChartOutlined style={{ color: '#1677ff', fontSize: 20 }} />,
  },
  {
    title: '部署面暴露检测',
    description: '检查网关监听、容器隔离、端口绑定、进程权限和写权限范围。',
    icon: <DeploymentUnitOutlined style={{ color: '#fa8c16', fontSize: 20 }} />,
  },
  {
    title: 'Agent 与 Skill 审计',
    description: '扫描高权限配置、Prompt Injection 风险、Skill 来源和危险函数调用。',
    icon: <SafetyCertificateOutlined style={{ color: '#52c41a', fontSize: 20 }} />,
  },
  {
    title: '凭据与 DLP 扫描',
    description: '识别明文密钥、Token、私钥、助记词和配置泄露痕迹。',
    icon: <FileSearchOutlined style={{ color: '#722ed1', fontSize: 20 }} />,
  },
];

const workflowSteps = [
  {
    title: '基线探测',
    description: '版本、进程、容器环境、网络监听与部署目录扫描。',
  },
  {
    title: '策略审计',
    description: '配置、Prompt、Skill、MCP、权限和危险函数检查。',
  },
  {
    title: '泄露发现',
    description: '明文密钥、敏感配置、异常连接和高风险日志聚合。',
  },
  {
    title: '报告输出',
    description: '生成 Markdown 报告和 JSON 摘要，便于归档与看板展示。',
  },
];

const outputFiles = [
  'openclaw_security_report.md',
  'openclaw_security_report.json',
];

const commandExample = `npm run scan:deployment-security
python3 tools/openclaw-scan/scan.py --report-path ./reports/openclaw.md --summary-path ./reports/openclaw.json
python3 tools/openclaw-scan/scan.py --quiet`;

const repositoryUrl = 'https://gitcode.com/shenaowang/openclaw-scan.git';

export default function DeploymentSecurity() {
  const sectionRows = sampleReport.sections.map((section) => ({
    title: section.title,
    count: section.items.length,
    preview: section.items.filter((item) => item.startsWith('- ') || item.includes('[警告]')).slice(0, 2),
  }));

  return (
    <PageContainer
      title="OpenClaw 部署安全检测工具"
      subTitle="面向真实部署场景的主机侧安全检测工具"
    >
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={24}>
          <Card style={{ borderRadius: 20 }}>
            <Space direction="vertical" size={12} style={{ width: '100%' }}>
              <Typography.Paragraph style={{ marginBottom: 0, fontSize: 15 }}>
                openclaw-scan 用于在部署主机上直接执行安全检测，覆盖版本漏洞、运行权限、端口暴露、
                Prompt 风险、Skill 来源可信性以及明文凭据泄露。工具同时输出 Markdown 检测报告与 JSON 摘要，
                适合用于上线前验收、变更后复检和日常安全巡检。
              </Typography.Paragraph>
              <Alert
                type="info"
                showIcon
                message="建议直接在 OpenClaw 实际部署节点执行，以获得真实的进程、端口、配置和文件系统审计结果。"
              />
              <Space wrap>
                <Button type="primary" icon={<DownloadOutlined />} href={repositoryUrl} target="_blank" rel="noreferrer">
                  前往 GitCode 仓库
                </Button>
              </Space>
              <Card
                size="small"
                style={{ background: '#0f172a', borderRadius: 12 }}
                bodyStyle={{ padding: 16 }}
              >
                <Typography.Text style={{ color: '#e2e8f0', whiteSpace: 'pre-wrap', fontFamily: 'SFMono-Regular, Consolas, monospace' }}>
                  {commandExample}
                </Typography.Text>
              </Card>
            </Space>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card style={{ borderRadius: 20 }}>
            <Statistic title="检测维度" value={sampleReport.totalSections} suffix="项" />
          </Card>
        </Col>
        <Col span={6}>
          <Card style={{ borderRadius: 20 }}>
            <Statistic title="命中漏洞" value={sampleReport.vulnerabilityMatches} suffix="条" />
          </Card>
        </Col>
        <Col span={6}>
          <Card style={{ borderRadius: 20 }}>
            <Statistic title="高风险告警" value={sampleReport.warningCount} suffix="项" />
          </Card>
        </Col>
        <Col span={6}>
          <Card style={{ borderRadius: 20 }}>
            <Statistic title="敏感信息命中" value={sampleReport.secretFindings} suffix="条" />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {capabilityCards.map((item) => (
          <Col span={6} key={item.title}>
            <Card style={{ height: '100%', borderRadius: 20 }}>
              <Space direction="vertical" size={10}>
                {item.icon}
                <Typography.Title level={5} style={{ margin: 0 }}>
                  {item.title}
                </Typography.Title>
                <Typography.Text type="secondary">{item.description}</Typography.Text>
              </Space>
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={24}>
          <Card title="检测流程" style={{ borderRadius: 20 }}>
            <Steps items={workflowSteps} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} align="stretch" style={{ marginBottom: 24 }}>
        <Col span={15} style={{ display: 'flex' }}>
          <Card
            title="样例检测结果"
            style={{ borderRadius: 20, width: '100%', height: '100%' }}
            bodyStyle={{ height: '100%', display: 'flex', flexDirection: 'column' }}
          >
            <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
              <Col span={8}>
                <Statistic title="报告生成时间" value={sampleReport.generatedAt} valueStyle={{ fontSize: 18 }} />
              </Col>
              <Col span={8}>
                <Statistic title="Root 运行进程" value={sampleReport.rootProcessRisks} suffix="个" />
              </Col>
              <Col span={8}>
                <Statistic title="输出格式" value={outputFiles.length} suffix="种" />
              </Col>
            </Row>
            <div style={{ flex: 1 }}>
              <List
                itemLayout="vertical"
                dataSource={sectionRows}
                renderItem={(item) => (
                  <List.Item>
                    <Space align="center" size={8} wrap>
                      <Typography.Text strong>{item.title}</Typography.Text>
                      <Tag color="blue">{item.count} 条结果</Tag>
                    </Space>
                    {item.preview.length > 0 ? (
                      <Space direction="vertical" size={6} style={{ marginTop: 10 }}>
                        {item.preview.map((preview) => (
                          <Typography.Text key={preview} type="secondary">
                            {preview}
                          </Typography.Text>
                        ))}
                      </Space>
                    ) : (
                      <Typography.Text type="secondary" style={{ display: 'block', marginTop: 10 }}>
                        该模块本次未发现需要重点展开的样例项。
                      </Typography.Text>
                    )}
                  </List.Item>
                )}
              />
            </div>
          </Card>
        </Col>
        <Col span={9} style={{ display: 'flex' }}>
          <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', gap: 16 }}>
            <Card title="工具产出物" style={{ borderRadius: 20 }}>
              <Space direction="vertical" size={12} style={{ width: '100%' }}>
                {outputFiles.map((file) => (
                  <Card key={file} size="small">
                    <Space align="center">
                      <CheckCircleOutlined style={{ color: '#1677ff' }} />
                      <Typography.Text code>{file}</Typography.Text>
                    </Space>
                  </Card>
                ))}
                <Card size="small">
                  <Space align="center">
                    <DownloadOutlined style={{ color: '#1677ff' }} />
                    <Typography.Link href={repositoryUrl} target="_blank" rel="noreferrer">
                      查看 GitCode 仓库
                    </Typography.Link>
                  </Space>
                </Card>
              </Space>
            </Card>
            <Card
              title="适用场景"
              style={{ borderRadius: 20, flex: 1 }}
              bodyStyle={{ height: '100%', display: 'flex', flexDirection: 'column' }}
            >
              <Space direction="vertical" size={10}>
                <Tag color="processing">部署验收</Tag>
                <Tag color="warning">变更后复检</Tag>
                <Tag color="error">应急排查</Tag>
                <Tag color="success">安全基线巡检</Tag>
                <Divider style={{ margin: '8px 0' }} />
                <Typography.Text type="secondary">
                  工具默认从宿主机视角收集进程、监听端口、配置和文件痕迹，适合上线前后快速做一次安全体检。
                </Typography.Text>
              </Space>
            </Card>
          </div>
        </Col>
      </Row>
    </PageContainer>
  );
}
