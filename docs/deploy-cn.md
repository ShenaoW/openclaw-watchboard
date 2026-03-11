# ClawSec 国内部署说明

## 推荐方案

优先选两种之一：

1. 中国大陆 ECS / 轻量服务器 + 已备案域名
2. 中国香港 ECS / Lighthouse + 域名

如果你要“国内长期稳定访问”，大陆服务器体验最好，但域名需要备案。
如果你要“尽快上线”，中国香港服务器更快，不需要 ICP 备案，但大陆用户延迟通常会更高。

## 服务器建议

- Ubuntu 22.04
- 2 vCPU / 4 GB 内存起
- Node.js 20
- Nginx
- PM2

## 目录结构

```text
/srv/clawsec/openclaw-watchboard/
```

## 部署步骤

### 1. 上传代码

```bash
mkdir -p /srv/clawsec
cd /srv/clawsec
git clone <your-repo> openclaw-watchboard
```

如果你本地直接上传整个仓库，也可以保持原目录结构，只要下面配置路径对应即可。

### 2. 安装依赖

```bash
cd /srv/clawsec/openclaw-watchboard/frontend
npm install

cd /srv/clawsec/openclaw-watchboard/backend
npm install
```

### 3. 构建前后端

```bash
cd /srv/clawsec/openclaw-watchboard/frontend
npm run build

cd /srv/clawsec/openclaw-watchboard/backend
npm run build
```

### 4. 启动后端

安装 PM2：

```bash
npm install -g pm2
```

修改 `deploy/ecosystem.config.cjs` 中的：

- `cwd`
- `FRONTEND_URLS`

然后启动：

```bash
pm2 start /srv/clawsec/openclaw-watchboard/deploy/ecosystem.config.cjs
pm2 save
pm2 startup
```

### 5. 配置 Nginx

把 `deploy/nginx.clawsec.conf` 复制到：

```bash
/etc/nginx/conf.d/clawsec.conf
```

修改：

- `server_name`
- `root`

然后重载：

```bash
nginx -t
systemctl reload nginx
```

### 6. 配 HTTPS

如果是大陆域名，建议：

```bash
apt-get update
apt-get install -y certbot python3-certbot-nginx
certbot --nginx -d your-domain.com
```

## 当前项目已做的生产适配

- 前端 API 走同域 `/api`
- Nginx 可直接反代到后端 `3005`
- 前端路由支持 `try_files ... /index.html`
- 关闭了 PWA，避免 service worker 影响直达子路由

## 发布后检查

访问：

- `https://your-domain.com/`
- `https://your-domain.com/risks/top10`
- `https://your-domain.com/exposure`
- `https://your-domain.com/skills`
- `https://your-domain.com/health`

## 说明

如果你的域名使用中国大陆服务器并面向公网服务，通常需要完成 ICP 备案。
如果你不想等备案，建议先上中国香港服务器。
