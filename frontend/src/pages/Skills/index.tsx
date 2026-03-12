import { PageContainer, ProList } from '@ant-design/pro-components';
import {
  Alert,
  Avatar,
  Button,
  Card,
  Col,
  Empty,
  Input,
  Row,
  Select,
  Space,
  Spin,
  Table,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import {
  CheckCircleOutlined,
  CodeOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  StopOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { Column } from '@ant-design/charts';
import { useEffect, useState } from 'react';
import { useSkillsData, useSkillsList, type SkillDetail } from '../../services/skillsApi';

const { Search } = Input;
const { Option } = Select;
const { Paragraph, Text, Link } = Typography;

function formatDate(value?: string) {
  if (!value) {
    return '-';
  }
  const match = value.match(/\d{4}-\d{2}-\d{2}/);
  return match ? match[0] : value;
}

function getSourceTag(source: string) {
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
  onSearch: (value: string) => void;
  emptyText: string;
}) {
  return (
    <Card
      title={props.title}
      extra={
        <Space>
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
          <Search
            placeholder="搜索 Skills"
            style={{ width: 220 }}
            onSearch={props.onSearch}
            enterButton
          />
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
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                <CodeOutlined style={{ color: '#1677ff' }} />
                <span style={{ fontWeight: 600 }}>{record.name}</span>
                <Tag color="blue">{record.version || '-'}</Tag>
                {getSourceTag(record.source)}
                {record.classification === 'safe' ? <Tag color="green">安全</Tag> : null}
                {record.classification === 'suspicious' ? <Tag color="orange">可疑</Tag> : null}
                {record.classification === 'malicious' ? <Tag color="red">恶意</Tag> : null}
              </div>
            ),
          },
          description: {
            render: (_, record) => (
              <div>
                <Paragraph style={{ marginBottom: 8 }}>
                  {record.description || '暂无公开描述'}
                </Paragraph>
                <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 12, color: '#64748b' }}>
                  <span>分类：{record.category || '-'}</span>
                  <span>维护者：{record.maintainer || '-'}</span>
                  <span>更新时间：{formatDate(record.lastUpdated)}</span>
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
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSource, setSelectedSource] = useState<string | undefined>(undefined);
  const [selectedCategory, setSelectedCategory] = useState<string | undefined>(undefined);
  const [trustedPage, setTrustedPage] = useState(1);
  const [suspiciousPage, setSuspiciousPage] = useState(1);
  const [maliciousPage, setMaliciousPage] = useState(1);

  const { stats, loading: statsLoading, error: statsError, refetch: refetchStats } = useSkillsData();
  const trusted = useSkillsList({ classification: 'safe', source: selectedSource, category: selectedCategory, search: searchTerm, page: trustedPage, limit: 20 });
  const suspicious = useSkillsList({ classification: 'suspicious', source: selectedSource, category: selectedCategory, search: searchTerm, page: suspiciousPage, limit: 20 });
  const malicious = useSkillsList({ classification: 'malicious', source: selectedSource, category: selectedCategory, search: searchTerm, page: maliciousPage, limit: 20 });

  useEffect(() => {
    const errors = [statsError, trusted.error, suspicious.error, malicious.error].filter(Boolean);
    if (errors.length > 0) {
      // eslint-disable-next-line no-console
      console.error(errors[0]);
    }
  }, [statsError, trusted.error, suspicious.error, malicious.error]);

  const resetPages = () => {
    setTrustedPage(1);
    setSuspiciousPage(1);
    setMaliciousPage(1);
  };

  const handleSearch = (value: string) => {
    setSearchTerm(value);
    resetPages();
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
    await Promise.all([refetchStats(), trusted.refetch(), suspicious.refetch(), malicious.refetch()]);
  };

  const categoryData = stats?.topCategories || [];
  const sourceDistributionData = stats
    ? [
        { source: 'ClawHub', count: stats.sourceDistribution.clawhub },
        { source: 'Skills.rest', count: stats.sourceDistribution.skillsRest },
        { source: 'SkillsMP', count: stats.sourceDistribution.skillsmp },
      ].filter((item) => item.count > 0)
    : [];

  const categoryConfig = {
    data: categoryData,
    xField: 'category',
    yField: 'count',
    height: 300,
    color: '#1890ff',
    label: false,
    axis: {
      y: {
        labelFormatter: (value: string) => Number(value).toLocaleString(),
      },
    },
  };

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
          <span title={text}>{text}</span>
        </Space>
      ),
    },
    {
      title: '总技能数',
      dataIndex: 'skillCount',
      key: 'skillCount',
    },
    {
      title: '安全',
      dataIndex: 'safeCount',
      key: 'safeCount',
      render: (count: number) => <Tag color="green">{count}</Tag>,
    },
    {
      title: '可疑',
      dataIndex: 'suspiciousCount',
      key: 'suspiciousCount',
      render: (count: number) => <Tag color={count > 0 ? 'orange' : 'default'}>{count}</Tag>,
    },
    {
      title: '恶意',
      dataIndex: 'maliciousCount',
      key: 'maliciousCount',
      render: (count: number) => <Tag color={count > 0 ? 'red' : 'default'}>{count}</Tag>,
    },
  ];

  if (statsLoading && !stats) {
    return (
      <PageContainer>
        <div style={{ textAlign: 'center', padding: '50px 0' }}>
          <Spin size="large" />
        </div>
      </PageContainer>
    );
  }

  if (statsError && !stats) {
    return (
      <PageContainer>
        <Alert message="数据加载失败" description={statsError} type="error" showIcon />
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
      subTitle="保留原有布局，仅展示当前可确认的数据字段"
      extra={[
        <Button key="sync" icon={<ReloadOutlined />} onClick={handleRefresh} loading={statsLoading}>
          同步 Skill 库
        </Button>,
      ]}
    >
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="已移除列表中的 mock 性详情、推断性原因、安全分数和详情跳转入口，仅保留可确认的清单、来源、分类、维护者、仓库与更新时间。"
      />

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <Avatar size={48} style={{ backgroundColor: '#1890ff' }} icon={<CodeOutlined />} />
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
              <Avatar size={48} style={{ backgroundColor: '#52c41a' }} icon={<CheckCircleOutlined />} />
              <div style={{ marginLeft: 16 }}>
                <div style={{ fontSize: 24, fontWeight: 'bold', color: '#52c41a' }}>{stats.securityDistribution.safe.toLocaleString()}</div>
                <div style={{ color: '#999' }}>安全 Skills</div>
              </div>
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <Avatar size={48} style={{ backgroundColor: '#fa8c16' }} icon={<ExclamationCircleOutlined />} />
              <div style={{ marginLeft: 16 }}>
                <div style={{ fontSize: 24, fontWeight: 'bold', color: '#fa8c16' }}>{stats.securityDistribution.suspicious.toLocaleString()}</div>
                <div style={{ color: '#999' }}>可疑 Skills</div>
              </div>
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <Avatar size={48} style={{ backgroundColor: '#722ed1' }} icon={<StopOutlined />} />
              <div style={{ marginLeft: 16 }}>
                <div style={{ fontSize: 24, fontWeight: 'bold', color: '#722ed1' }}>{stats.securityDistribution.malicious.toLocaleString()}</div>
                <div style={{ color: '#999' }}>恶意 Skills</div>
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginBottom: 24 }} align="stretch">
        <Col span={7} style={{ display: 'flex' }}>
          <Card title="📊 数据源分布" size="small" style={{ width: '100%', height: '100%' }}>
            <Space direction="vertical" style={{ width: '100%' }} size={10}>
              {sourceDistributionData.map((item) => (
                <div key={item.source} style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>{item.source}</span>
                  <strong>{item.count.toLocaleString()}</strong>
                </div>
              ))}
            </Space>
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
                onSearch={handleSearch}
                emptyText="暂无可信 Skills"
              />
            ),
          },
          {
            key: 'suspicious',
            label: '⚠️ 可疑 Skills 检测',
            children: (
              <SkillListSection
                title="可疑 Skills 列表"
                loading={suspicious.loading}
                skills={suspicious.skills}
                currentPage={suspiciousPage}
                total={suspicious.pagination.total}
                onPageChange={setSuspiciousPage}
                selectedSource={selectedSource}
                selectedCategory={selectedCategory}
                categories={stats.topCategories}
                onSourceChange={handleSourceChange}
                onCategoryChange={handleCategoryChange}
                onSearch={handleSearch}
                emptyText="暂无可疑 Skills"
              />
            ),
          },
          {
            key: 'malicious',
            label: '🚫 恶意 Skills',
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
                onSearch={handleSearch}
                emptyText="暂无恶意 Skills"
              />
            ),
          },
        ]}
      />
    </PageContainer>
  );
}
