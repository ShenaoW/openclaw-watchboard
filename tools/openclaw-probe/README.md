# OpenClaw Probe

`openclaw-probe` 现在只保留一条核心链路：

1. 从 FOFA 代理的 `/api/v1/search/all` 拉取 `app="openclaw"` 数据
   - 每次成功抓取后，会把原始 CSV 缓存到 `data/explosure/fofa_cache/openclaw_latest.csv`
   - 同时按日期写入 `data/explosure/fofa_cache/history/`
   - 默认只使用 `search/all?page=`
   - 首次请求会读取响应里的总量，然后按尽量大的 `size` 计算总页数，减少抓取次数
2. 找出相对当前实例库的新增 `ip:port`
3. 对新增目标只探测 `/health` 和 `__openclaw/control-ui-config.json`
4. 只有 `health=200` 且 config 能成功返回版本配置的目标才会入库
5. 对库里所有历史实例每天重跑活跃探测和版本探测
6. 记录每日快照
7. 运行产物保存到 `run_dir`

核心入口：

- `fofa_incremental_updater.py`
  - 兼容入口，转发到拆分后的主流程
- 同目录下的多个脚本
  - 按功能拆分后的核心实现

## Current Files

- `fofa_incremental_updater.py`
  - 唯一推荐 CLI 入口，外部调用方式保持不变
- `cli.py`
  - 参数解析与入口
- `pipeline.py`
  - 主流程编排
- `fofa.py`
  - FOFA 拉取与加载
- `prober.py`
  - HTTP 探测与 OpenClaw 指纹判断
- `repository.py`
  - SQLite 建表、bootstrap、插入、状态更新、快照落库
- `exporters.py`
  - 运行产物保存，兼容 CSV 导出代码暂时保留但不作为默认流程
- `common.py`
  - 通用 CSV、日期、`ip:port` 工具函数
- `constants.py`
  - 路径与字段常量
- `backup/`
  - 历史脚本备份

## Notes

- 当前版本默认直接使用 FOFA 的 `country_name / region / city`
- 国内位置不再额外依赖 IP 反查
- 当前默认流程不再回写兼容 CSV，也不自动刷新旧版 `exposure` 分析链路
- 每次运行都会在 `run_dir/status.json` 写入阶段状态，并同步更新 `data/explosure/runs/latest_status.json`
- 如果任务异常中断，`latest_status.json` 里会保留失败阶段和错误信息
- 可以用以下两种方式复用本地缓存：
  - `--fofa-cache-first`
    - 先读本地 `openclaw_latest.csv`，不存在时再抓取 FOFA
  - `--fofa-cache-only`
    - 完全只用本地缓存回放一次更新流程
- 可以用 `--fofa-fetch-only`
  - 只抓取 FOFA 数据并刷新本地缓存
  - 会保留本次 `run_dir` 产物和状态
  - 不会继续做探测、落库、快照和数据库更新
- 当前 `--fofa-fetch-mode` 仅保留 `all`
  - 主流程只使用 `search/all?page=`

## Daily Commands

推荐优先使用外层包装脚本：

- [`scripts/run_openclaw_probe_pipeline.sh`](/Users/shawn/Desktop/openclaw-watchboard/scripts/run_openclaw_probe_pipeline.sh)

默认完整更新：

```bash
FOFA_KEY='your-key' /bin/zsh scripts/run_openclaw_probe_pipeline.sh
```

等价目标：

- 抓取 FOFA
- 更新本地缓存
- 探测新增实例
- 回写兼容 CSV/JSON
- 刷新 `data/exposure.db`

常用模式：

```bash
# 只抓取 FOFA 缓存
FOFA_KEY='your-key' OPENCLAW_PROBE_FETCH_ONLY=1 OPENCLAW_PROBE_WRITE_LIVE=0 OPENCLAW_PROBE_REFRESH_DB=0 /bin/zsh scripts/run_openclaw_probe_pipeline.sh

# 只使用本地缓存跑后续更新
OPENCLAW_PROBE_CACHE_ONLY=1 /bin/zsh scripts/run_openclaw_probe_pipeline.sh

# 优先读缓存，没有缓存时再抓 FOFA
FOFA_KEY='your-key' OPENCLAW_PROBE_CACHE_FIRST=1 /bin/zsh scripts/run_openclaw_probe_pipeline.sh

# 大批量活跃探测时提高速度
FOFA_KEY='your-key' OPENCLAW_PROBE_CONCURRENCY=256 OPENCLAW_PROBE_TIMEOUT=3 /bin/zsh scripts/run_openclaw_probe_pipeline.sh
```

如果需要直接调用 Python CLI：

```bash
python3 tools/openclaw-probe/fofa_incremental_updater.py \
  --fofa-key 'your-key' \
  --fofa-no-proxy \
  --write-live \
  --refresh-db
```
