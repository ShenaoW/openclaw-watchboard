import { PageContainer } from "@ant-design/pro-components";
import { history } from "@umijs/max";
import { Button, Card, Col, Divider, Row, Space, Tag, Typography } from "antd";
import {
  GlobalOutlined,
  MailOutlined,
  SafetyCertificateOutlined,
  TeamOutlined,
} from "@ant-design/icons";

const { Paragraph, Text, Title } = Typography;

const contacts = [
  {
    name: "王浩宇",
    email: "haoyuwang@hust.edu.cn",
  },
  {
    name: "侯心怡",
    email: "xinyihou@hust.edu.cn",
  },
  {
    name: "王申奥",
    email: "shenaowang@hust.edu.cn",
  },
];

export default function HomePage() {
  return (
    <PageContainer title={false}>
      <div
        style={{
          background:
            "radial-gradient(circle at top right, rgba(147,197,253,0.3) 0%, rgba(147,197,253,0) 30%), linear-gradient(135deg, #0b3c82 0%, #0e5bb5 48%, #1d7ae6 100%)",
          borderRadius: 32,
          padding: "44px 36px",
          color: "#f8fafc",
          overflow: "hidden",
          position: "relative",
          boxShadow: "0 24px 60px rgba(15, 52, 115, 0.22)",
        }}
      >
        <div
          style={{
            position: "absolute",
            top: -70,
            right: -90,
            width: 300,
            height: 300,
            borderRadius: "50%",
            background: "rgba(255,255,255,0.14)",
            filter: "blur(8px)",
          }}
        />
        <div
          style={{
            position: "absolute",
            left: -80,
            bottom: -120,
            width: 280,
            height: 280,
            borderRadius: "50%",
            background: "rgba(191,219,254,0.18)",
            filter: "blur(10px)",
          }}
        />
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 16,
            marginBottom: 22,
            flexWrap: "wrap",
          }}
        >
          <Space
            size={18}
            wrap
            align="center"
            style={{
              background: "rgba(255,255,255,0.12)",
              padding: "14px 18px",
              borderRadius: 20,
              border: "1px solid rgba(255,255,255,0.18)",
            }}
          >
            <img
              alt="华中科技大学网络空间安全学院"
              src="/branding/hust-cse.jpg"
              style={{
                width: 72,
                height: 72,
                objectFit: "cover",
                background: "#fff",
                borderRadius: "50%",
                padding: 4,
              }}
            />
            <img
              alt="武汉金银湖实验室"
              src="/branding/jinyinhu-lab.jpg"
              style={{
                width: 72,
                height: 72,
                objectFit: "cover",
                background: "#fff",
                borderRadius: "50%",
                padding: 4,
              }}
            />
            <Text style={{ color: "#ffffff", fontSize: 18, fontWeight: 700 }}>
              华中科技大学网络空间安全学院 × 武汉金银湖实验室
            </Text>
          </Space>
          <Tag
            color="blue"
            style={{
              marginInlineEnd: 0,
              padding: "6px 15px",
              borderRadius: 999,
              fontSize: 13,
              fontWeight: 450,
              lineHeight: "24px",
            }}
          >
            SecurityPRIDE 研究团队
          </Tag>
        </div>
        <Title level={1} style={{ color: "#ffffff", margin: 0, maxWidth: 920 }}>
          面向 OpenClaw 生态安全治理的监测与分析平台
        </Title>
        <Paragraph
          style={{
            color: "rgba(239,246,255,0.92)",
            fontSize: 17,
            lineHeight: 1.95,
            marginTop: 18,
            marginBottom: 28,
            maxWidth: 920,
          }}
        >
          本系统由华中科技大学网络空间安全学院与武汉金银湖实验室共同研发，围绕
          OpenClaw 生态的风险漏洞、Skill
          投毒后门、公网暴露面与部署安全检测，提供统一展示、分析研判与工具支持能力。
        </Paragraph>
        <Space size={16} wrap>
          <Button
            type="primary"
            size="large"
            icon={<SafetyCertificateOutlined />}
            style={{
              background: "#ffffff",
              color: "#0b3c82",
              borderColor: "#ffffff",
              fontWeight: 700,
              boxShadow: "0 10px 24px rgba(8, 47, 104, 0.18)",
            }}
            onClick={() => history.push("/dashboard")}
          >
            进入治理总览
          </Button>
          <Button
            size="large"
            ghost
            icon={<GlobalOutlined />}
            style={{
              borderColor: "rgba(255,255,255,0.6)",
              color: "#ffffff",
              fontWeight: 600,
            }}
            onClick={() => history.push("/tools")}
          >
            部署安全检测工具
          </Button>
        </Space>
      </div>

      <Row gutter={[20, 20]} style={{ marginTop: 20 }}>
        <Col xs={24} xl={14}>
          <Card
            style={{
              borderRadius: 28,
              border: "1px solid #dbeafe",
              boxShadow: "0 14px 36px rgba(37, 99, 235, 0.08)",
              background: "linear-gradient(180deg, #f8fbff 0%, #ffffff 100%)",
            }}
            bodyStyle={{ padding: 28 }}
            title={
              <Space size={10}>
                <TeamOutlined style={{ color: "#1d4ed8" }} />
                <span>团队与研发单位</span>
              </Space>
            }
          >
            <Paragraph
              style={{
                fontSize: 15,
                lineHeight: 1.9,
                marginBottom: 16,
                color: "#334155",
              }}
            >
              华中科技大学 SecurityPEIDE
              研究团队关注于新兴软件系统中的安全、隐私和可靠性问题，长期围绕大模型软件系统安全、智能体组件风险发现与监测开展研究与工程落地，团队在相关方向积累深厚，在软件工程和程序语言、系统安全、网络和系统度量领域的顶会论文成果在国内外名列前茅。
            </Paragraph>
            <Divider style={{ margin: "18px 0", borderColor: "#dbeafe" }} />
            <Space direction="vertical" size={14} style={{ width: "100%" }}>
              <div>
                <Text strong style={{ color: "#0f172a" }}>
                  联合研发单位
                </Text>
                <Row gutter={[16, 16]} style={{ marginTop: 10 }}>
                  <Col span={12}>
                    <div
                      style={{
                        textAlign: "center",
                        padding: 16,
                        borderRadius: 22,
                        background:
                          "linear-gradient(180deg, #eff6ff 0%, #ffffff 100%)",
                        border: "1px solid #dbeafe",
                      }}
                    >
                      <img
                        alt="华中科技大学网络空间安全学院"
                        src="/branding/hust-cse.jpg"
                        style={{
                          width: 110,
                          height: 110,
                          objectFit: "cover",
                          borderRadius: "50%",
                        }}
                      />
                      <Paragraph
                        style={{
                          margin: "10px 0 0",
                          color: "#334155",
                          fontWeight: 600,
                        }}
                      >
                        华中科技大学网络空间安全学院
                      </Paragraph>
                    </div>
                  </Col>
                  <Col span={12}>
                    <div
                      style={{
                        textAlign: "center",
                        padding: 16,
                        borderRadius: 22,
                        background:
                          "linear-gradient(180deg, #eff6ff 0%, #ffffff 100%)",
                        border: "1px solid #dbeafe",
                      }}
                    >
                      <img
                        alt="武汉金银湖实验室"
                        src="/branding/jinyinhu-lab.jpg"
                        style={{
                          width: 110,
                          height: 110,
                          objectFit: "cover",
                          borderRadius: "50%",
                        }}
                      />
                      <Paragraph
                        style={{
                          margin: "10px 0 0",
                          color: "#334155",
                          fontWeight: 600,
                        }}
                      >
                        武汉金银湖实验室
                      </Paragraph>
                    </div>
                  </Col>
                </Row>
              </div>
            </Space>
          </Card>
        </Col>

        <Col xs={24} xl={10}>
          <Card
            style={{
              borderRadius: 28,
              height: "100%",
              border: "1px solid #dbeafe",
              boxShadow: "0 14px 36px rgba(37, 99, 235, 0.08)",
              background: "linear-gradient(180deg, #f8fbff 0%, #ffffff 100%)",
            }}
            bodyStyle={{ padding: 28 }}
            title={
              <Space size={10}>
                <MailOutlined style={{ color: "#1d4ed8" }} />
                <span>联系方式</span>
              </Space>
            }
          >
            <Space direction="vertical" size={18} style={{ width: "100%" }}>
              {contacts.map((contact) => (
                <div
                  key={contact.email}
                  style={{
                    padding: 18,
                    borderRadius: 20,
                    background:
                      "linear-gradient(180deg, #eff6ff 0%, #ffffff 100%)",
                    border: "1px solid #dbeafe",
                    boxShadow: "0 10px 26px rgba(59, 130, 246, 0.08)",
                  }}
                >
                  <Text strong style={{ fontSize: 16, color: "#0f172a" }}>
                    {contact.name}
                  </Text>
                  <div style={{ marginTop: 8 }}>
                    <a
                      href={`mailto:${contact.email}`}
                      style={{ color: "#2563eb", fontWeight: 600 }}
                    >
                      {contact.email}
                    </a>
                  </div>
                </div>
              ))}
            </Space>
          </Card>
        </Col>
      </Row>
    </PageContainer>
  );
}
