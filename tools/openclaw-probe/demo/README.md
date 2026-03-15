# Probe Demo

这个 demo 会：

1. 启动一个本地假的 OpenClaw HTTP 实例
2. 生成一份只有 1 条资产的本地 FOFA 样本
3. 调用 `fofa_incremental_updater.py`
4. 打印 `probe_instances`、`probe_daily_snapshots` 和兼容 CSV 导出结果

运行：

```bash
/bin/zsh tools/openclaw-probe/demo/run_demo.sh
```

可选环境变量：

- `OPENCLAW_PROBE_DEMO_HOST`
- `OPENCLAW_PROBE_DEMO_PORT`
- `OPENCLAW_PROBE_DEMO_DIR`
- `PYTHON_BIN`

## Real FOFA 50 Demo

这个 demo 会：

1. 从真实 FOFA 拉取 50 条 `app="openclaw"` 数据
2. 把当前旧参考库裁剪为前 50 条
3. 在临时目录里执行完整增量流程
4. 打印拉取数量、参考库数量、入库数量、快照数量和导出结果

运行：

```bash
FOFA_KEY="..." /bin/zsh tools/openclaw-probe/demo/run_real_fofa_50_demo.sh
```

可选环境变量：

- `FOFA_KEY`
- `OPENCLAW_PROBE_DEMO_DIR`
- `OPENCLAW_PROBE_QUERY`
- `PYTHON_BIN`

说明：

- 这个 demo 默认会绕过 shell 里的 `http_proxy` / `https_proxy` / `all_proxy`
- 因为当前 `107.173.248.139:18999` 经过本地代理会返回 `502 Bad Gateway`
