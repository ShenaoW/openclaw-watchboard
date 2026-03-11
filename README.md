# OpenClaw Watchboard

OpenClaw Watchboard 是一个面向 OpenClaw 安全态势分析的监控面板，包含三块核心内容：

- OpenClaw Top 10 风险
- 已披露漏洞数据
- 公网暴露实例与 Skill 投毒分析

## 项目结构

```text
openclaw-watchboard/
├── frontend/      # React 19 + UmiJS + Ant Design Pro
├── backend/       # Node.js + Express + TypeScript
├── shared/        # 共享类型
├── data/          # 本地 SQLite 数据库与原始 CSV/JSON 数据
├── scripts/       # 数据初始化、分析、导入、同步脚本
└── package.json   # Monorepo 入口
```

## 本地启动

### 1. 安装依赖

```bash
npm run install:all
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

### 3. 启动开发环境

```bash
npm run dev
```

默认端口：

- 前端：`http://localhost:3000`
- 后端：`http://localhost:3005`

## 数据库与数据刷新

本项目的数据主要保存在 `data/` 下的三个 SQLite 文件中：

- `data/exposure.db`
- `data/risks.db`
- `data/skills.db`

### 一次性初始化数据库结构

```bash
python3 scripts/setup_database.py
```

### 刷新全部数据库

会按顺序刷新 Skills、暴露数据、漏洞数据：

```bash
npm run refresh:databases
```

等价于：

```bash
python3 scripts/run_analysis.py
```

### 只刷新暴露数据库

```bash
npm run refresh:exposure-db
```

### 只刷新 Skills 数据库

```bash
npm run refresh:skills-db
```

会执行：

- Skills 库结构检查
- ClawHub 数据导入
- CSV Skills 数据导入
- Skills 统计生成

### 只刷新漏洞数据库

```bash
npm run refresh:risks-db
```

会执行：

- Risks 库结构检查
- 漏洞标注 CSV 生成
- 漏洞导入 `risks.db`

当前暴露数据刷新会自动整合这些数据源：

- `data/explosure/openclaw_instances_deduped.csv`
- `data/explosure/endpoint_alive.csv`
- `data/explosure/endpoint_alive_configs.json`
- `data/explosure/openclaw_instances_cn.csv`

其中会补充：

- 实例运行状态
- `serverVersion`
- 境内实例、省份、城市信息

## 同步到远程服务器

### 同步数据库

会把本地 `data/` 下所有 `.db` 文件上传到远端，并自动重启后端进程：

```bash
npm run sync:databases
```

如果当前机器没有配置默认 SSH 别名，可以临时指定远端：

```bash
REMOTE_HOST=your-ssh-host npm run sync:databases
```

### 同步代码

推荐流程：

1. 本地完成代码修改
2. 本地执行前端/后端构建确认
3. 将变更同步到远端代码目录
4. 在远端执行：

```bash
npm run build:backend
npm run build:frontend
pm2 restart openclaw-backend
```

如果这次改动涉及数据结构或数据内容，再额外执行：

```bash
npm run sync:databases
```

## 常用命令

```bash
# 本地开发
npm run dev

# 构建全部
npm run build

# 刷新全部数据库
npm run refresh:databases

# 单独刷新各个数据库
npm run refresh:skills-db
npm run refresh:risks-db
npm run refresh:exposure-db

# 同步所有数据库到远端
npm run sync:databases
```
