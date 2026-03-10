# OpenClaw Watchboard

OpenClaw 安全风险监控面板是一个全面的安全态势感知平台，专门为监控和分析 OpenClaw 相关安全风险而设计。

## 功能特性

### 🚨 OpenClaw Top 10 风险监控
- 实时展示最新的 OpenClaw 安全风险
- 详细的风险分析和影响评估
- 风险趋势分析和历史跟踪
- CVE 关联和补丁建议

### 🌐 公网暴露情况分析
- 全球公网暴露服务发现
- 地理分布可视化大屏
- 端口和服务风险评估
- 实时威胁监控和告警

### 🛡️ Skill 投毒检测与可信库管理
- 恶意 Skill 检测和分析
- 可信 Skill 库维护
- Skill 安全评分系统
- 社区举报和审核机制

## 技术架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   External      │
│                 │    │                 │    │   Services      │
│ ├─ React 19     │◄──►│ ├─ Node.js      │◄──►│ ├─ OpenClaw API │
│ ├─ Ant Design  │    │ ├─ Express      │    │ ├─ CVE Feeds    │
│ ├─ TypeScript   │    │ ├─ TypeScript   │    │ ├─ Threat Intel │
│ └─ Charts       │    │ └─ SQLite       │    │ └─ Skill Repos  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 前端技术栈
- **React 19** + **TypeScript**
- **Ant Design Pro** - 企业级 UI 解决方案
- **Ant Design Charts** - 数据可视化
- **UmiJS** - 应用框架
- **Zustand** - 状态管理

### 后端技术栈
- **Node.js** + **Express** + **TypeScript**
- **SQLite** - 数据存储
- **TypeORM** - ORM 框架
- **Node-cron** - 定时任务

## 快速开始

### 环境要求
- Node.js >= 16.0.0
- npm >= 8.0.0

### 安装依赖
```bash
# 安装所有依赖
npm run install:all

# 或分别安装
npm install                    # 根目录依赖
npm run install:frontend       # 前端依赖
npm run install:backend        # 后端依赖
npm run install:shared         # 共享模块依赖
```

### 配置环境变量
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置文件
vim .env
```

### 启动开发环境
```bash
# 启动前后端服务（推荐）
npm run dev

# 或分别启动
npm run dev:frontend          # 前端开发服务器 (http://localhost:3000)
npm run dev:backend           # 后端 API 服务器 (http://localhost:3001)
```

### 生产部署
```bash
# 构建所有模块
npm run build

# 启动生产服务
npm start
```

## API 接口

### 风险管理 API
- `GET /api/risks/top10` - 获取 Top 10 风险
- `GET /api/risks/:id` - 获取风险详情
- `GET /api/risks/stats/summary` - 风险统计
- `POST /api/risks/refresh` - 刷新风险数据

### 暴露分析 API
- `GET /api/exposure/overview` - 暴露概况
- `GET /api/exposure/services` - 暴露服务列表
- `GET /api/exposure/geography` - 地理分布
- `POST /api/exposure/scan` - 触发扫描

### Skill 管理 API
- `GET /api/skills/trusted` - 可信 Skill 列表
- `GET /api/skills/suspicious` - 可疑 Skill 列表
- `POST /api/skills/report` - 举报可疑 Skill
- `POST /api/skills/verify` - 验证 Skill 安全性

## 开发指南

### 项目结构
```
openclaw-watchboard/
├── frontend/          # React 前端应用
├── backend/           # Express 后端 API
├── shared/           # 共享类型和工具
├── docs/             # 项目文档
├── .env.example      # 环境变量模板
└── package.json      # 项目配置
```

### 代码规范
```bash
# 代码格式检查
npm run lint

# 自动修复格式问题
npm run lint:fix

# 运行测试
npm test
```

## 部署说明

### Docker 部署
```bash
# 构建镜像
docker build -t openclaw-watchboard .

# 运行容器
docker run -d -p 3000:3000 -p 3001:3001 openclaw-watchboard
```

### 系统要求
- 操作系统: Linux/macOS/Windows
- 内存: >= 2GB RAM
- 存储: >= 10GB 可用空间
- 网络: 能够访问互联网（用于获取威胁情报）

## 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 许可证

本项目基于 MIT 许可证开源 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 支持与反馈

- 🐛 [报告 Bug](https://github.com/openclaw/watchboard/issues)
- 💡 [功能建议](https://github.com/openclaw/watchboard/discussions)
- 📧 联系我们: security@openclaw.com

## 致谢

感谢所有为 OpenClaw 生态系统安全做出贡献的安全研究员和开发者。