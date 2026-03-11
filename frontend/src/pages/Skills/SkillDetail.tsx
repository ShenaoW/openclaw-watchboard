import { PageContainer } from '@ant-design/pro-components';
import {
  Card, Descriptions, Tag, Progress, Button, Space, Alert, Tabs,
  Row, Col, Statistic, Badge, Typography, Divider, List, Timeline
} from 'antd';
import {
  ArrowLeftOutlined, SafetyOutlined, ExclamationCircleOutlined,
  DownloadOutlined, StarOutlined, BugOutlined, LinkOutlined,
  CodeOutlined, SecurityScanOutlined, ClockCircleOutlined
} from '@ant-design/icons';
import { useParams, history } from '@umijs/max';
import { useState, useEffect } from 'react';
import { skillsAPI } from '../../services/skillsApi';

const { Title, Text, Paragraph } = Typography;

interface SkillAnalysis {
  skillId: string;
  basicInfo: {
    name: string;
    version: string;
    size: string;
    language: string;
    architecture: string;
    source: string;
    maintainer: string;
    repository: string;
  };
  securityAnalysis: {
    overallScore: number;
    codeQuality: number;
    permissionUsage: number;
    networkBehavior: number;
    fileSystemAccess: number;
  };
  staticAnalysis: {
    malwareSignatures: number;
    suspiciousPatterns: number;
    vulnerabilities: Array<{
      type: string;
      severity: string;
      location: string;
      description: string;
    }>;
  };
  dependencies: Array<{
    name: string;
    version: string;
    vulnerabilities?: number;
    license?: string;
  }>;
  skillMarkdown?: string; // 添加SKILL.md内容
}

export default function SkillDetailPage() {
  const { skillId } = useParams<{ skillId: string }>();
  const [analysis, setAnalysis] = useState<SkillAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (skillId) {
      loadSkillAnalysis();
    }
  }, [skillId]);

  const loadSkillAnalysis = async () => {
    if (!skillId) return;

    setLoading(true);
    setError(null);
    try {
      const data = await skillsAPI.getSkillAnalysis(skillId);
      setAnalysis(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load skill analysis');
    } finally {
      setLoading(false);
    }
  };

  const getSourceTag = (source: string) => {
    switch (source) {
      case 'clawhub':
        return <Tag color="green">官方 ClawHub</Tag>;
      case 'skills.rest':
        return <Tag color="blue">Skills.rest</Tag>;
      case 'skillsmp':
        return <Tag color="purple">SkillsMP</Tag>;
      default:
        return <Tag color="default">{source}</Tag>;
    }
  };

  const getSecurityScoreColor = (score: number) => {
    if (score >= 90) return '#52c41a';
    if (score >= 70) return '#faad14';
    if (score >= 50) return '#fa8c16';
    return '#f5222d';
  };

  if (loading) {
    return (
      <PageContainer>
        <Card loading />
      </PageContainer>
    );
  }

  if (error || !analysis) {
    return (
      <PageContainer>
        <Alert
          message="加载失败"
          description={error || '无法加载技能详情'}
          type="error"
          showIcon
        />
      </PageContainer>
    );
  }

  return (
    <PageContainer
      title={
        <Space>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => history.back()}
            type="text"
          />
          <CodeOutlined />
          {analysis.basicInfo.name}
          <Tag>{analysis.basicInfo.version}</Tag>
          {getSourceTag(analysis.basicInfo.source)}
        </Space>
      }
      extra={[
        <Button key="download" icon={<DownloadOutlined />} type="primary">
          下载技能
        </Button>,
        <Button key="report" icon={<ExclamationCircleOutlined />} danger>
          举报
        </Button>
      ]}
    >
      {/* 基本信息概览 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={18}>
          <Card title="📋 基本信息">
            <Descriptions column={2} bordered>
              <Descriptions.Item label="技能名称">{analysis.basicInfo.name}</Descriptions.Item>
              <Descriptions.Item label="版本">{analysis.basicInfo.version}</Descriptions.Item>
              <Descriptions.Item label="维护者">
                <Space>
                  <Text>{analysis.basicInfo.maintainer}</Text>
                  <Badge status="success" text="已验证" />
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="编程语言">{analysis.basicInfo.language}</Descriptions.Item>
              <Descriptions.Item label="数据源">{getSourceTag(analysis.basicInfo.source)}</Descriptions.Item>
              <Descriptions.Item label="包大小">{analysis.basicInfo.size}</Descriptions.Item>
              <Descriptions.Item label="代码仓库" span={2}>
                <Space>
                  <LinkOutlined />
                  <a href={analysis.basicInfo.repository} target="_blank" rel="noopener noreferrer">
                    {analysis.basicInfo.repository}
                  </a>
                </Space>
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>

        <Col span={6}>
          <Card title="🛡️ 安全评分">
            <div style={{ textAlign: 'center' }}>
              <Progress
                type="circle"
                percent={analysis.securityAnalysis.overallScore}
                strokeColor={getSecurityScoreColor(analysis.securityAnalysis.overallScore)}
                format={percent => (
                  <div>
                    <div style={{ fontSize: 24, fontWeight: 'bold' }}>{percent}</div>
                    <div style={{ fontSize: 12, color: '#999' }}>安全评分</div>
                  </div>
                )}
              />

              <Divider />

              <Space direction="vertical" style={{ width: '100%' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Text>代码质量</Text>
                  <Text strong>{analysis.securityAnalysis.codeQuality}%</Text>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Text>权限使用</Text>
                  <Text strong>{analysis.securityAnalysis.permissionUsage}%</Text>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Text>网络行为</Text>
                  <Text strong>{analysis.securityAnalysis.networkBehavior}%</Text>
                </div>
              </Space>
            </div>
          </Card>
        </Col>
      </Row>

      {/* 详细分析 */}
      <Tabs
        defaultActiveKey="security"
        items={[
          {
            key: 'security',
            label: (
              <Space>
                <SecurityScanOutlined />
                安全分析
              </Space>
            ),
            children: (
              <Row gutter={16}>
                <Col span={12}>
                  <Card title="🔍 静态代码分析" style={{ marginBottom: 16 }}>
                    <Row gutter={16}>
                      <Col span={8}>
                        <Statistic
                          title="恶意签名"
                          value={analysis.staticAnalysis.malwareSignatures}
                          valueStyle={{
                            color: analysis.staticAnalysis.malwareSignatures > 0 ? '#f5222d' : '#52c41a'
                          }}
                        />
                      </Col>
                      <Col span={8}>
                        <Statistic
                          title="可疑模式"
                          value={analysis.staticAnalysis.suspiciousPatterns}
                          valueStyle={{
                            color: analysis.staticAnalysis.suspiciousPatterns > 0 ? '#fa8c16' : '#52c41a'
                          }}
                        />
                      </Col>
                      <Col span={8}>
                        <Statistic
                          title="漏洞数量"
                          value={analysis.staticAnalysis.vulnerabilities.length}
                          valueStyle={{
                            color: analysis.staticAnalysis.vulnerabilities.length > 0 ? '#f5222d' : '#52c41a'
                          }}
                        />
                      </Col>
                    </Row>

                    {analysis.staticAnalysis.vulnerabilities.length > 0 && (
                      <div style={{ marginTop: 16 }}>
                        <Title level={5}>发现的漏洞:</Title>
                        <List
                          dataSource={analysis.staticAnalysis.vulnerabilities}
                          renderItem={(vuln) => (
                            <List.Item>
                              <Space direction="vertical" style={{ width: '100%' }}>
                                <Space>
                                  <Tag color="red">{vuln.severity}</Tag>
                                  <Text strong>{vuln.type}</Text>
                                </Space>
                                <Text type="secondary">{vuln.location}</Text>
                                <Paragraph>{vuln.description}</Paragraph>
                              </Space>
                            </List.Item>
                          )}
                        />
                      </div>
                    )}
                  </Card>
                </Col>

                <Col span={12}>
                  <Card title="📊 安全指标详情">
                    <Space direction="vertical" style={{ width: '100%' }} size="large">
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                          <Text>代码质量</Text>
                          <Text>{analysis.securityAnalysis.codeQuality}%</Text>
                        </div>
                        <Progress
                          percent={analysis.securityAnalysis.codeQuality}
                          strokeColor={getSecurityScoreColor(analysis.securityAnalysis.codeQuality)}
                        />
                      </div>

                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                          <Text>权限使用合理性</Text>
                          <Text>{analysis.securityAnalysis.permissionUsage}%</Text>
                        </div>
                        <Progress
                          percent={analysis.securityAnalysis.permissionUsage}
                          strokeColor={getSecurityScoreColor(analysis.securityAnalysis.permissionUsage)}
                        />
                      </div>

                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                          <Text>网络行为安全性</Text>
                          <Text>{analysis.securityAnalysis.networkBehavior}%</Text>
                        </div>
                        <Progress
                          percent={analysis.securityAnalysis.networkBehavior}
                          strokeColor={getSecurityScoreColor(analysis.securityAnalysis.networkBehavior)}
                        />
                      </div>

                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                          <Text>文件系统访问</Text>
                          <Text>{analysis.securityAnalysis.fileSystemAccess}%</Text>
                        </div>
                        <Progress
                          percent={analysis.securityAnalysis.fileSystemAccess}
                          strokeColor={getSecurityScoreColor(analysis.securityAnalysis.fileSystemAccess)}
                        />
                      </div>
                    </Space>
                  </Card>
                </Col>
              </Row>
            ),
          },
          {
            key: 'dependencies',
            label: (
              <Space>
                <BugOutlined />
                依赖分析
              </Space>
            ),
            children: (
              <Card title="📦 依赖包分析">
                {analysis.dependencies.length > 0 ? (
                  <List
                    dataSource={analysis.dependencies}
                    renderItem={(dep) => (
                      <List.Item>
                        <List.Item.Meta
                          title={
                            <Space>
                              <Text strong>{dep.name}</Text>
                              <Tag>{dep.version}</Tag>
                              {dep.license && <Tag color="blue">{dep.license}</Tag>}
                            </Space>
                          }
                          description={
                            <Space>
                              {dep.vulnerabilities !== undefined && (
                                <>
                                  <Text>已知漏洞: </Text>
                                  <Badge
                                    count={dep.vulnerabilities}
                                    style={{
                                      backgroundColor: dep.vulnerabilities > 0 ? '#f5222d' : '#52c41a'
                                    }}
                                  />
                                </>
                              )}
                            </Space>
                          }
                        />
                      </List.Item>
                    )}
                  />
                ) : (
                  <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
                    暂无依赖信息
                  </div>
                )}
              </Card>
            ),
          },
          {
            key: 'documentation',
            label: (
              <Space>
                <CodeOutlined />
                技能文档
              </Space>
            ),
            children: (
              <Card title="📖 SKILL.md">
                {analysis.skillMarkdown ? (
                  <div style={{
                    backgroundColor: '#f6f8fa',
                    padding: '16px',
                    borderRadius: '8px',
                    fontFamily: 'Monaco, Menlo, "Ubuntu Mono", monospace',
                    fontSize: '13px',
                    lineHeight: '1.5',
                    whiteSpace: 'pre-wrap',
                    overflow: 'auto',
                    maxHeight: '600px'
                  }}>
                    {analysis.skillMarkdown}
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
                    暂无技能文档
                  </div>
                )}
              </Card>
            ),
          },
          {
            key: 'history',
            label: (
              <Space>
                <ClockCircleOutlined />
                版本历史
              </Space>
            ),
            children: (
              <Card title="📈 版本发布历史">
                <Timeline>
                  <Timeline.Item color="green">
                    <Space direction="vertical">
                      <Text strong>v{analysis.basicInfo.version} (当前版本)</Text>
                      <Text type="secondary">最新发布版本</Text>
                    </Space>
                  </Timeline.Item>
                  <Timeline.Item>
                    <Space direction="vertical">
                      <Text>v1.0.1</Text>
                      <Text type="secondary">2024-03-01 - 修复安全漏洞</Text>
                    </Space>
                  </Timeline.Item>
                  <Timeline.Item>
                    <Space direction="vertical">
                      <Text>v1.0.0</Text>
                      <Text type="secondary">2024-02-15 - 初始发布</Text>
                    </Space>
                  </Timeline.Item>
                </Timeline>
              </Card>
            ),
          },
        ]}
      />
    </PageContainer>
  );
}