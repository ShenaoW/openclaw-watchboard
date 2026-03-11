import { PageContainer, ProList } from '@ant-design/pro-components';
import {
  Card, Col, Row, Tabs, Button, Tag, Rate, Progress, Badge,
  Avatar, Input, Select, Space, Modal, Form, message, Descriptions, Statistic,
  Table, Spin, Empty
} from 'antd';
import {
  SafetyOutlined, ReloadOutlined,
  SafetyCertificateOutlined, BugOutlined, StarOutlined, DownloadOutlined,
  ExclamationCircleOutlined, CheckCircleOutlined, EyeOutlined,
  UserOutlined, CodeOutlined, GlobalOutlined, StopOutlined
} from '@ant-design/icons';
import { Column } from '@ant-design/charts';
import { useEffect, useState } from 'react';
import { history } from '@umijs/max';
import { useSkillsData, useSkillsList, skillsAPI, SkillDetail } from '../../services/skillsApi';

const { Search } = Input;
const { Option } = Select;

export default function Skills() {
  const [reportModalVisible, setReportModalVisible] = useState(false);
  const [verifyModalVisible, setVerifyModalVisible] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSource, setSelectedSource] = useState<string | undefined>(undefined);
  const [selectedCategory, setSelectedCategory] = useState<string | undefined>(undefined);

  // 分页状态
  const [trustedPage, setTrustedPage] = useState(1);
  const [suspiciousPage, setSuspiciousPage] = useState(1);
  const [maliciousPage, setMaliciousPage] = useState(1);
  const pageSize = 20; // 每页显示数量

  // 使用自定义hooks获取数据
  const { stats, loading: statsLoading, error: statsError, refetch: refetchStats } = useSkillsData();

  // 安全技能列表
  const {
    skills: trustedSkills,
    pagination: trustedPagination,
    loading: trustedLoading,
    error: trustedError,
    refetch: refetchTrusted
  } = useSkillsList({
    classification: 'safe',
    source: selectedSource,
    category: selectedCategory,
    search: searchTerm,
    page: trustedPage,
    limit: pageSize
  });

  // 可疑技能列表
  const {
    skills: suspiciousSkills,
    pagination: suspiciousPagination,
    loading: suspiciousLoading,
    error: suspiciousError,
    refetch: refetchSuspicious
  } = useSkillsList({
    classification: 'suspicious',
    source: selectedSource,
    category: selectedCategory,
    search: searchTerm,
    page: suspiciousPage,
    limit: pageSize
  });

  const {
    skills: maliciousSkills,
    pagination: maliciousPagination,
    loading: maliciousLoading,
    error: maliciousError,
    refetch: refetchMalicious
  } = useSkillsList({
    classification: 'malicious',
    source: selectedSource,
    category: selectedCategory,
    search: searchTerm,
    page: maliciousPage,
    limit: pageSize
  });

  const handleSearch = (value: string) => {
    setSearchTerm(value);
    setTrustedPage(1); // 重置到第一页
    setSuspiciousPage(1);
    setMaliciousPage(1);
  };

  const handleSourceChange = (value?: string) => {
    setSelectedSource(value);
    setTrustedPage(1); // 重置到第一页
    setSuspiciousPage(1);
    setMaliciousPage(1);
  };

  const handleCategoryChange = (value?: string) => {
    setSelectedCategory(value);
    setTrustedPage(1); // 重置到第一页
    setSuspiciousPage(1);
    setMaliciousPage(1);
  };

  const handleViewSkill = (skill: SkillDetail) => {
    history.push(`/skills/${skill.id}`);
  };

  const handleReport = async (values: any) => {
    try {
      await skillsAPI.reportSkill({
        skillId: values.skillName,
        reason: values.reason,
        description: values.description
      });
      message.success('举报已提交，我们会尽快审核');
      setReportModalVisible(false);
    } catch (error) {
      message.error('举报提交失败，请稍后重试');
    }
  };

  const handleVerify = async (values: any) => {
    try {
      await skillsAPI.verifySkill({
        skillId: '',
        source: values.source,
        verifyType: values.verifyType
      });
      message.success('安全验证已启动，请稍后查看结果');
      setVerifyModalVisible(false);
    } catch (error) {
      message.error('验证启动失败，请稍后重试');
    }
  };

  const handleRefresh = async () => {
    await Promise.all([refetchStats(), refetchTrusted(), refetchSuspicious(), refetchMalicious()]);
    message.success('数据已更新');
  };

  useEffect(() => {
    const errors = [statsError, trustedError, suspiciousError, maliciousError].filter(Boolean);
    if (errors.length > 0) {
      message.error(errors[0] as string);
    }
  }, [statsError, trustedError, suspiciousError, maliciousError]);

  // 图表配置
  const sourceDistributionData = stats
    ? [
        { source: 'ClawHub', count: stats.sourceDistribution.clawhub, color: '#52c41a' },
        { source: 'Skills.rest', count: stats.sourceDistribution.skillsRest, color: '#1890ff' },
        { source: 'SkillsMP.com', count: stats.sourceDistribution.skillsmp, color: '#722ed1' },
      ].filter((item) => item.count > 0)
    : [];

  const categoryData = stats?.topCategories || [];
  const sourceTotal = sourceDistributionData.reduce((sum, item) => sum + item.count, 0);
  const sourceChartBackground = sourceDistributionData.length
    ? `conic-gradient(${sourceDistributionData
        .map((item, index) => {
          const start = sourceDistributionData
            .slice(0, index)
            .reduce((sum, current) => sum + current.count, 0);
          const end = start + item.count;
          const startPercent = (start / sourceTotal) * 100;
          const endPercent = (end / sourceTotal) * 100;
          return `${item.color} ${startPercent}% ${endPercent}%`;
        })
        .join(', ')})`
    : '#f0f0f0';

  const categoryConfig = {
    data: categoryData,
    xField: 'category',
    yField: 'count',
    height: 300,
    color: '#1890ff',
    meta: {
      count: {
        formatter: (value: number) => Number(value).toLocaleString(),
      },
    },
    axis: {
      y: {
        labelFormatter: (value: string) => Number(value).toLocaleString(),
      },
    },
    label: {
      position: 'middle' as const,
      style: {
        fill: '#FFFFFF',
        opacity: 0.6,
      },
    },
  };

  // Top开发者表格列配置
  const developerColumns = [
    {
      title: '开发者',
      dataIndex: 'developer',
      key: 'developer',
      width: 240,
      ellipsis: true,
      render: (text: string) => (
        <Space style={{ maxWidth: 220 }}>
          <Avatar icon={<UserOutlined />} size="small" />
          <span
            style={{
              display: 'inline-block',
              maxWidth: 180,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
            title={text}
          >
            {text}
          </span>
        </Space>
      ),
    },
    {
      title: '总技能数',
      dataIndex: 'skillCount',
      key: 'skillCount',
      sorter: (a: any, b: any) => a.skillCount - b.skillCount,
    },
    {
      title: '安全技能',
      dataIndex: 'safeCount',
      key: 'safeCount',
      render: (count: number) => <Tag color="green">{count}</Tag>,
    },
    {
      title: '可疑技能',
      dataIndex: 'suspiciousCount',
      key: 'suspiciousCount',
      render: (count: number) => count > 0 ? <Tag color="red">{count}</Tag> : <Tag>0</Tag>,
    },
    {
      title: '恶意技能',
      dataIndex: 'maliciousCount',
      key: 'maliciousCount',
      render: (count: number) => count > 0 ? <Tag color="volcano">{count}</Tag> : <Tag>0</Tag>,
    },
  ];

  const getSourceTag = (source: string) => {
    switch (source) {
      case 'clawhub':
        return <Tag color="green">官方</Tag>;
      case 'skills.rest':
        return <Tag color="blue">Skills.rest</Tag>;
      case 'skillsmp':
        return <Tag color="purple">SkillsMP</Tag>;
      default:
        return <Tag>{source}</Tag>;
    }
  };

  if (statsLoading) {
    return (
      <PageContainer>
        <div style={{ textAlign: 'center', padding: '50px 0' }}>
          <Spin size="large" />
        </div>
      </PageContainer>
    );
  }

  if (statsError) {
    return (
      <PageContainer>
        <Alert
          message="数据加载失败"
          description={statsError}
          type="error"
          showIcon
          action={
            <Button size="small" onClick={handleRefresh}>
              重试
            </Button>
          }
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
      title="Skill 投毒检测与可信库管理"
      subTitle="OpenClaw Skills 安全监控与信任管理"
      extra={[
        <Button key="sync" icon={<ReloadOutlined />} onClick={handleRefresh} loading={statsLoading}>
          同步 Skill 库
        </Button>
      ]}
    >
      {/* 统计概览 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <Avatar
                size={48}
                style={{ backgroundColor: '#1890ff' }}
                icon={<CodeOutlined />}
              />
              <div style={{ marginLeft: 16 }}>
                <div style={{ fontSize: 24, fontWeight: 'bold' }}>{stats.totalSkills.toLocaleString()}</div>
                <div style={{ color: '#999' }}>Skills 总数</div>
              </div>
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <Avatar
                size={48}
                style={{ backgroundColor: '#52c41a' }}
                icon={<CheckCircleOutlined />}
              />
              <div style={{ marginLeft: 16 }}>
                <div style={{ fontSize: 24, fontWeight: 'bold', color: '#52c41a' }}>
                  {stats.securityDistribution.safe.toLocaleString()}
                </div>
                <div style={{ color: '#999' }}>安全 Skills</div>
              </div>
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <Avatar
                size={48}
                style={{ backgroundColor: '#ff4d4f' }}
                icon={<ExclamationCircleOutlined />}
              />
              <div style={{ marginLeft: 16 }}>
                <div style={{ fontSize: 24, fontWeight: 'bold', color: '#ff4d4f' }}>
                  {stats.securityDistribution.suspicious.toLocaleString()}
                </div>
                <div style={{ color: '#999' }}>可疑 Skills</div>
              </div>
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <Avatar
                size={48}
                style={{ backgroundColor: '#722ed1' }}
                icon={<StopOutlined />}
              />
              <div style={{ marginLeft: 16 }}>
                <div style={{ fontSize: 24, fontWeight: 'bold', color: '#722ed1' }}>
                  {stats.securityDistribution.malicious.toLocaleString()}
                </div>
                <div style={{ color: '#999' }}>恶意 Skills</div>
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      {/* 数据统计图表 */}
      <Row gutter={16} style={{ marginBottom: 24 }} align="stretch">
        <Col span={7} style={{ display: 'flex' }}>
          <Card title="📊 数据源分布" size="small" style={{ width: '100%', height: '100%' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div
                style={{
                  height: 300,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <div
                  style={{
                    width: 240,
                    height: 240,
                    borderRadius: '50%',
                    background: sourceChartBackground,
                    position: 'relative',
                    boxShadow: 'inset 0 0 0 1px rgba(0,0,0,0.04)',
                  }}
                >
                  <div
                    style={{
                      position: 'absolute',
                      inset: 42,
                      borderRadius: '50%',
                      background: '#fff',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      textAlign: 'center',
                    }}
                  >
                    <div style={{ fontSize: 28, fontWeight: 700, lineHeight: 1 }}>
                      {sourceTotal.toLocaleString()}
                    </div>
                    <div style={{ marginTop: 8, color: '#8c8c8c', fontSize: 12 }}>
                      Total Skills
                    </div>
                  </div>
                </div>
              </div>
              <div>
                {sourceDistributionData.map((item) => (
                  <div
                    key={item.source}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      marginBottom: 8,
                    }}
                    >
                      <Space size={8}>
                        <span
                        style={{
                          width: 10,
                          height: 10,
                          borderRadius: '50%',
                          display: 'inline-block',
                          backgroundColor: item.color,
                        }}
                        />
                      <span>{item.source}</span>
                    </Space>
                    <Space size={12}>
                      <span style={{ color: '#8c8c8c', fontSize: 12 }}>
                        {((item.count / sourceTotal) * 100).toFixed(1)}%
                      </span>
                      <strong>{item.count.toLocaleString()}</strong>
                    </Space>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </Col>
        <Col span={7} style={{ display: 'flex' }}>
          <Card title="📈 技能分类分布" size="small" style={{ width: '100%', height: '100%' }}>
            <Column {...categoryConfig} />
          </Card>
        </Col>
        <Col span={10} style={{ display: 'flex' }}>
          <Card title="👥 Top 10 开发者" size="small" style={{ width: '100%', height: '100%' }}>
            <Table
              dataSource={stats.topDevelopers.slice(0, 10)}
              columns={developerColumns}
              pagination={false}
              size="small"
              rowKey="developer"
              scroll={{ y: 300 }}
            />
          </Card>
        </Col>
      </Row>

      <Tabs
        defaultActiveKey="trusted"
        items={[
          {
            key: 'trusted',
            label: '✅ 可信 Skills 库',
            children: (
              <Row gutter={16}>
                <Col span={24}>
                  <Card
                    title="可信 Skills 列表"
                    extra={
                      <Space>
                        <Select
                          placeholder="选择数据源"
                          style={{ width: 150 }}
                          value={selectedSource}
                          onChange={handleSourceChange}
                          allowClear
                        >
                          <Option value="clawhub">ClawHub官方</Option>
                          <Option value="skills.rest">Skills.rest</Option>
                          <Option value="skillsmp">SkillsMP</Option>
                        </Select>
                        <Select
                          placeholder="选择分类"
                          style={{ width: 150 }}
                          value={selectedCategory}
                          onChange={handleCategoryChange}
                          allowClear
                        >
                          {stats.topCategories.map((cat: any) => (
                            <Option key={cat.category} value={cat.category}>{cat.category}</Option>
                          ))}
                        </Select>
                        <Search
                          placeholder="搜索 Skills"
                          style={{ width: 200 }}
                          onSearch={handleSearch}
                          enterButton
                        />
                        <Button type="primary" onClick={() => setVerifyModalVisible(true)}>
                          验证新 Skill
                        </Button>
                      </Space>
                    }
                    loading={trustedLoading}
                  >
                    <ProList<SkillDetail>
                      dataSource={trustedSkills}
                      showActions="hover"
                      onItem={(record) => ({
                        onClick: () => handleViewSkill(record),
                      })}
                      pagination={{
                        current: trustedPage,
                        pageSize: pageSize,
                        total: trustedPagination.total,
                        showSizeChanger: false,
                        showQuickJumper: true,
                        showTotal: (total, range) => `${range[0]}-${range[1]} 共 ${total} 个技能`,
                        onChange: (page) => setTrustedPage(page),
                      }}
                      metas={{
                        title: {
                          render: (_, record) => (
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                              <SafetyCertificateOutlined style={{ color: '#52c41a' }} />
                              <span style={{ fontWeight: 600 }}>{record.name}</span>
                              <Tag color="green">v{record.version}</Tag>
                              {getSourceTag(record.source)}
                              {record.verified && <Badge status="success" text="已验证" />}
                            </div>
                          ),
                        },
                        description: {
                          render: (_, record) => (
                            <div>
                              <div style={{ marginBottom: 8 }}>{record.description}</div>
                              <div style={{ display: 'flex', gap: 16, fontSize: 12, color: '#999' }}>
                                <span>📁 {record.category}</span>
                                <span>👤 {record.maintainer}</span>
                                <span>📅 {new Date(record.lastUpdated).toLocaleDateString()}</span>
                              </div>
                            </div>
                          ),
                        },
                        extra: {
                          render: (_, record) => (
                            <div style={{ textAlign: 'right' }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <DownloadOutlined />
                                <span>{record.downloads.toLocaleString()}</span>
                              </div>
                              <Rate disabled defaultValue={record.rating} allowHalf style={{ fontSize: 12 }} />
                              <div style={{ marginTop: 4 }}>
                                <Progress
                                  percent={record.securityScore}
                                  size="small"
                                  strokeColor={record.securityScore > 90 ? '#52c41a' : '#ffa940'}
                                  format={() => `${record.securityScore}%`}
                                />
                              </div>
                              <div style={{ marginTop: 8 }}>
                                <Button
                                  size="small"
                                  icon={<EyeOutlined />}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleViewSkill(record);
                                  }}
                                >
                                  查看详情
                                </Button>
                              </div>
                            </div>
                          ),
                        },
                      }}
                    />
                  </Card>
                </Col>
              </Row>
            ),
          },
          {
            key: 'suspicious',
            label: '⚠️ 可疑 Skills 检测',
            children: (
              <Row gutter={16}>
                <Col span={24}>
                  <Card
                    title="可疑 Skills 列表"
                    extra={
                      <Space>
                        <Select
                          placeholder="选择数据源"
                          style={{ width: 150 }}
                          value={selectedSource}
                          onChange={handleSourceChange}
                          allowClear
                        >
                          <Option value="clawhub">ClawHub官方</Option>
                          <Option value="skills.rest">Skills.rest</Option>
                          <Option value="skillsmp">SkillsMP</Option>
                        </Select>
                        <Select
                          placeholder="选择分类"
                          style={{ width: 150 }}
                          value={selectedCategory}
                          onChange={handleCategoryChange}
                          allowClear
                        >
                          {stats.topCategories.map((cat: any) => (
                            <Option key={cat.category} value={cat.category}>{cat.category}</Option>
                          ))}
                        </Select>
                        <Search
                          placeholder="搜索 Skills"
                          style={{ width: 200 }}
                          onSearch={handleSearch}
                          enterButton
                        />
                        <Button
                          type="primary"
                          danger
                          onClick={() => setReportModalVisible(true)}
                        >
                          举报可疑 Skill
                        </Button>
                      </Space>
                    }
                    loading={suspiciousLoading}
                  >
                    <ProList<SkillDetail>
                      dataSource={suspiciousSkills}
                      showActions="hover"
                      onItem={(record) => ({
                        onClick: () => handleViewSkill(record),
                      })}
                      pagination={{
                        current: suspiciousPage,
                        pageSize: pageSize,
                        total: suspiciousPagination.total,
                        showSizeChanger: false,
                        showQuickJumper: true,
                        showTotal: (total, range) => `${range[0]}-${range[1]} 共 ${total} 个可疑技能`,
                        onChange: (page) => setSuspiciousPage(page),
                      }}
                      metas={{
                        title: {
                          render: (_, record) => (
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                              <BugOutlined style={{ color: '#ff4d4f' }} />
                              <span style={{ fontWeight: 600 }}>{record.name}</span>
                              <Tag color="orange">待复核</Tag>
                              {getSourceTag(record.source)}
                            </div>
                          ),
                        },
                        description: {
                          render: (_, record) => (
                            <div>
                              <div style={{ marginBottom: 8 }}>{record.description}</div>
                              <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
                                首次发现: {new Date(record.lastUpdated).toLocaleDateString()} | 分析状态: 待审查
                              </div>
                            </div>
                          ),
                        },
                        extra: {
                          render: (_, record) => (
                            <div style={{ textAlign: 'right' }}>
                              <Progress
                                percent={record.securityScore}
                                size="small"
                                strokeColor="#ff4d4f"
                                format={() => `${record.securityScore}%`}
                              />
                              <div style={{ marginTop: 8 }}>
                                <Button
                                  size="small"
                                  icon={<EyeOutlined />}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleViewSkill(record);
                                  }}
                                >
                                  分析详情
                                </Button>
                              </div>
                            </div>
                          ),
                        },
                      }}
                    />
                  </Card>
                </Col>
              </Row>
            ),
          },
          {
            key: 'malicious',
            label: '🚫 恶意 Skills',
            children: (
              <Row gutter={16}>
                <Col span={24}>
                  <Card
                    title="恶意 Skills 列表"
                    extra={
                      <Space>
                        <Select
                          placeholder="选择数据源"
                          style={{ width: 150 }}
                          value={selectedSource}
                          onChange={handleSourceChange}
                          allowClear
                        >
                          <Option value="clawhub">ClawHub官方</Option>
                          <Option value="skills.rest">Skills.rest</Option>
                          <Option value="skillsmp">SkillsMP</Option>
                        </Select>
                        <Select
                          placeholder="选择分类"
                          style={{ width: 150 }}
                          value={selectedCategory}
                          onChange={handleCategoryChange}
                          allowClear
                        >
                          {stats.topCategories.map((cat: any) => (
                            <Option key={cat.category} value={cat.category}>{cat.category}</Option>
                          ))}
                        </Select>
                        <Search
                          placeholder="搜索 Skills"
                          style={{ width: 200 }}
                          onSearch={handleSearch}
                          enterButton
                        />
                        <Tag color="volcano">
                          已确认恶意: {stats.securityDistribution.malicious}
                        </Tag>
                      </Space>
                    }
                    loading={maliciousLoading}
                  >
                    <ProList<SkillDetail>
                      dataSource={maliciousSkills}
                      showActions="hover"
                      onItem={(record) => ({
                        onClick: () => handleViewSkill(record),
                      })}
                      pagination={{
                        current: maliciousPage,
                        pageSize: pageSize,
                        total: maliciousPagination.total,
                        showSizeChanger: false,
                        showQuickJumper: true,
                        showTotal: (total, range) => `${range[0]}-${range[1]} 共 ${total} 个恶意技能`,
                        onChange: (page) => setMaliciousPage(page),
                      }}
                      metas={{
                        title: {
                          render: (_, record) => (
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                              <StopOutlined style={{ color: '#cf1322' }} />
                              <span style={{ fontWeight: 600 }}>{record.name}</span>
                              {getSourceTag(record.source)}
                              <Tag color="red">已确认恶意</Tag>
                            </div>
                          ),
                        },
                        description: {
                          render: (_, record) => (
                            <div>
                              <div style={{ marginBottom: 8 }}>{record.description}</div>
                              <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
                                最近更新时间: {new Date(record.lastUpdated).toLocaleDateString()}
                              </div>
                            </div>
                          ),
                        },
                        extra: {
                          render: (_, record) => (
                            <div style={{ textAlign: 'right' }}>
                              <Progress
                                percent={record.securityScore}
                                size="small"
                                status="exception"
                                strokeColor="#cf1322"
                                format={() => `${record.securityScore}%`}
                              />
                              <div style={{ marginTop: 8 }}>
                                <Button
                                  size="small"
                                  danger
                                  icon={<EyeOutlined />}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleViewSkill(record);
                                  }}
                                >
                                  分析详情
                                </Button>
                              </div>
                            </div>
                          ),
                        },
                      }}
                    />
                  </Card>
                </Col>
              </Row>
            ),
          },
        ]}
      />

      {/* 举报模态框 */}
      <Modal
        title="举报可疑 Skill"
        open={reportModalVisible}
        onCancel={() => setReportModalVisible(false)}
        footer={null}
      >
        <Form onFinish={handleReport} layout="vertical">
          <Form.Item label="Skill 名称" name="skillName" rules={[{ required: true }]}>
            <Input placeholder="请输入 Skill 名称" />
          </Form.Item>
          <Form.Item label="举报原因" name="reason" rules={[{ required: true }]}>
            <Select placeholder="选择举报原因">
              <Option value="malicious">恶意行为</Option>
              <Option value="privacy">隐私泄露</Option>
              <Option value="security">安全漏洞</Option>
              <Option value="other">其他</Option>
            </Select>
          </Form.Item>
          <Form.Item label="详细描述" name="description">
            <Input.TextArea rows={4} placeholder="请详细描述可疑行为..." />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                提交举报
              </Button>
              <Button onClick={() => setReportModalVisible(false)}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 验证模态框 */}
      <Modal
        title="验证 Skill 安全性"
        open={verifyModalVisible}
        onCancel={() => setVerifyModalVisible(false)}
        footer={null}
      >
        <Form onFinish={handleVerify} layout="vertical">
          <Form.Item label="Skill 来源" name="source" rules={[{ required: true }]}>
            <Input placeholder="请输入 Skill 的 URL 或仓库地址" />
          </Form.Item>
          <Form.Item label="验证类型" name="verifyType" rules={[{ required: true }]}>
            <Select placeholder="选择验证类型">
              <Option value="full">完整安全验证</Option>
              <Option value="quick">快速检查</Option>
              <Option value="static">静态代码分析</Option>
            </Select>
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                开始验证
              </Button>
              <Button onClick={() => setVerifyModalVisible(false)}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
}
