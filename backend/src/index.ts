import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import compression from 'compression';
import rateLimit from 'express-rate-limit';
import dotenv from 'dotenv';

import { errorHandler } from './middleware/errorHandler';
import { notFound } from './middleware/notFound';
import riskRoutes from './routes/risks';
import exposureRoutes from './routes/exposure';
import skillRoutes from './routes/skills';

// 加载环境变量
dotenv.config();

const app = express();
const PORT = Number(process.env.PORT || 3005);
const allowedOrigins = (process.env.FRONTEND_URLS || process.env.FRONTEND_URL || '')
  .split(',')
  .map((item) => item.trim())
  .filter(Boolean);

// 安全中间件
app.use(helmet());
app.use(cors({
  origin: [
    /^http:\/\/localhost:\d+$/, // 允许localhost的任何端口
    /^http:\/\/127\.0\.0\.1:\d+$/, // 允许127.0.0.1的任何端口
    /^https?:\/\/localhost:\d+$/,
    /^https?:\/\/127\.0\.0\.1:\d+$/,
    'http://localhost:3000',
    'http://localhost:3002',
    'http://localhost:3004',
    ...allowedOrigins
  ],
  credentials: true
}));

// 压缩响应
app.use(compression());

// 日志
app.use(morgan('combined'));

// 限流
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 1000 // 限制每个IP每15分钟最多1000个请求
});
app.use(limiter);

// 解析请求体
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Add debugging middleware to log all requests
app.use((req, res, next) => {
  console.log(`${new Date().toISOString()} - ${req.method} ${req.url}`);
  next();
});

// API 路由
app.use('/api/risks', riskRoutes);
app.use('/api/exposure', exposureRoutes);
app.use('/api/skills', skillRoutes);

// 健康检查
app.get('/health', (req, res) => {
  res.json({
    status: 'OK',
    timestamp: new Date().toISOString(),
    service: 'OpenClaw Watchboard API'
  });
});

// 错误处理中间件
app.use(notFound);
app.use(errorHandler);

app.listen(PORT, '0.0.0.0', () => {
  console.log(`🚀 OpenClaw Watchboard API Server running on port ${PORT}`);
  console.log(`📊 Environment: ${process.env.NODE_ENV || 'development'}`);
  console.log(`🌐 Server accessible at http://localhost:${PORT}`);
});

export default app;
