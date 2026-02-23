# X-Claw V2（MiroThinker 30B 优先）首次部署可执行任务清单

这份清单是按“第一次实际部署”设计的，优先保证能稳定跑通，再逐步补强。

适用前提：

- 目标是企业级深度研究助手（不是高并发客服）
- 首次部署继续使用 `MiroThinker 30B`
- 推理引擎使用 `SGLang`（OpenAI 兼容 API）
- 当前代码骨架基于本目录 `x_claw/` 与配置文件

---

## 0. 部署目标（先统一口径）

本次上线目标不是“功能最全”，而是：

1. 能在本地/测试环境稳定跑通一条完整链路
2. 默认使用 MiroThinker 30B
3. 能接收调试请求（`/debug/message`）
4. 具备基础健康检查与监控指标
5. 为后续接入真实 MCP 工具留好接口

本次不强制完成：

1. 真实飞书/Teams 回发消息 SDK 集成
2. Redis/ChromaDB 的生产级实现
3. 完整 MCP SDK 适配
4. Kubernetes 上线

---

## 1. 阶段拆解（建议顺序）

### 阶段 A：环境准备（半天到 1 天）

任务：

1. 准备 Linux 服务器（推荐 Ubuntu 22.04/24.04）
2. 安装 NVIDIA 驱动、CUDA（与 SGLang 兼容）
3. 安装 Python 3.11+
4. 安装 `uv`（推荐）或 `pip`
5. 准备模型存储目录（例如 `/data/models/mirothinker-30b`）

验收标准：

- `nvidia-smi` 能看到 L20
- `python --version` >= 3.11
- 磁盘空间足够（模型 + 日志 + 缓存）

---

### 阶段 B：启动 MiroThinker 30B 推理服务（SGLang）（半天）

任务：

1. 安装 SGLang
2. 准备 MiroThinker 模型文件
3. 启动 SGLang OpenAI 兼容接口
4. 做推理健康检查

参考命令（单卡 L20 / FP8）：

```bash
python -m sglang.launch_server \
  --model /data/models/mirothinker-30b \
  --tp 1 \
  --quantization fp8 \
  --mem-fraction-static 0.85 \
  --max-model-len 131072 \
  --host 0.0.0.0 \
  --port 8000
```

验收标准：

- `curl http://127.0.0.1:8000/v1/models` 返回模型信息（或 OpenAI 兼容响应）
- 简单 chat completion 能返回结果

---

### 阶段 C：部署 X-Claw 骨架服务（半天）

任务：

1. 复制环境变量
2. 安装依赖
3. 启动 X-Claw 服务
4. 检查 `/health`、`/ready`、`/metrics`

命令：

```bash
cp .env.example .env
```

编辑 `.env`（最少改这几项）：

```env
XCLAW_LLM_PROVIDER=mirothinker
XCLAW_LLM_BASE_URL=http://127.0.0.1:8000/v1
XCLAW_LLM_API_KEY=dummy
XCLAW_LLM_MODEL=mirothinker-30b
```

安装运行（推荐 `uv`）：

```bash
uv venv
source .venv/bin/activate
uv pip install -e .
uvicorn x_claw.main:app --host 0.0.0.0 --port 8080
```

验收标准：

- `GET /health` 返回 `ok`
- `GET /ready` 能显示 `llm_provider=mirothinker`
- `GET /metrics` 有 Prometheus 指标输出

---

### 阶段 D：跑通调试链路（必须完成）（半天）

任务：

1. 使用 `/debug/message` 发送简单问题
2. 验证任务分类（simple_qa / deep_research）
3. 验证配额逻辑和日志输出

命令示例：

```bash
curl -X POST http://127.0.0.1:8080/debug/message \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "u1",
    "chat_id": "c1",
    "platform": "debug",
    "content": "请解释什么是 MCP 协议"
  }'
```

深度研究示例：

```bash
curl -X POST http://127.0.0.1:8080/debug/message \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "u1",
    "chat_id": "c1",
    "platform": "debug",
    "content": "请做一个关于企业 AI Agent 架构趋势的深度调研"
  }'
```

验收标准：

- 能返回回答
- 返回 JSON 中包含 `task_type`、`tool_calls`、`iterations`
- 简单问答默认不启用工具（当前骨架策略）

---

### 阶段 E：接入真实 MCP 工具（第一个迭代重点，1 到 3 天）

当前骨架中 `x_claw/mcp/client_wrapper.py` 已留好接口，但默认未接真实 MCP SDK。

任务：

1. 将 `config/mcp_servers.example.yaml` 复制为 `config/mcp_servers.yaml`
2. 安装并验证实际 MCP 服务器（searching / browser / reading）
3. 在 `x_claw/mcp/client_wrapper.py` 中替换骨架实现：
   - `initialize()`
   - `get_available_tools()`
   - `call_tool()`
4. 保留现有超时、重试、错误包装逻辑

验收标准：

- `/ready` 中可看到 MCP 服务健康状态
- 深度研究问题能产生实际工具调用
- 工具失败能返回 `[TOOL_ERROR] ...` 而不是整个请求崩溃

---

### 阶段 F：接入飞书 / Teams（第一个上线前迭代，1 到 3 天）

任务：

1. 完成飞书签名校验 / 解密 / 去重
2. 接入飞书回发消息 API
3. 接入 Teams Bot Framework 鉴权与回发
4. 验证 webhook 联调

注意：

- 当前骨架适配器只做解析和标准化，不包含生产级安全逻辑

验收标准：

- 飞书与 Teams 各至少完成一条真实消息往返
- 非文本消息可安全忽略
- 重复事件不会重复执行任务

---

## 2. 必做配置文件与代码位置（你以后就按这个找）

核心入口：

- `x_claw/main.py`
- `x_claw/bootstrap.py`

模型与策略：

- `x_claw/core/llm_provider.py`（MiroThinker Provider 在这里）
- `x_claw/core/capability_manager.py`
- `x_claw/core/task_router.py`
- `x_claw/core/engine.py`

工具链：

- `x_claw/mcp/client_wrapper.py`
- `x_claw/mcp/health_checker.py`
- `config/mcp_servers.example.yaml`

接入层：

- `x_claw/adapters/feishu_adapter.py`
- `x_claw/adapters/teams_adapter.py`

观测与治理：

- `x_claw/observability/metrics.py`
- `x_claw/observability/logging_utils.py`
- `x_claw/core/quota_manager.py`

部署与运行：

- `.env.example`
- `docker-compose.yml`
- `Dockerfile`

---

## 3. 第一次部署的“完成定义”（DoD）

满足以下 8 条，就算第一次部署成功：

1. SGLang + MiroThinker 30B 服务稳定启动
2. X-Claw 服务能启动并连接到 SGLang
3. `/health`、`/ready`、`/metrics` 正常
4. `/debug/message` 能处理简单问答
5. `/debug/message` 能处理深度研究类输入（即使暂时无真实工具）
6. 配额限制可生效（至少深度研究并发限制）
7. 日志中可看到请求处理记录和任务类型
8. 出错时返回结构化错误信息，而不是进程崩溃

---

## 4. 第一周建议任务排期（实战版）

### Day 1

1. 跑通 SGLang + MiroThinker 30B
2. 跑通 X-Claw `/health` 与 `/debug/message`

### Day 2

1. 验证任务分类与配额逻辑
2. 补 `/ready` 输出细节和基本日志
3. 固化 `.env` 配置模板

### Day 3-4

1. 接入真实 MCP SDK（先做 `searching`）
2. 验证工具超时、重试、错误包装

### Day 5

1. 接入 `reading` 或 `browser` 二选一
2. 做 10 个 smoke case 回归表

---

## 5. 你现在最应该盯的 5 个指标（第一次部署版）

1. 请求成功率
2. 平均响应时间
3. 深度研究任务失败率
4. 工具调用失败率（接入真实 MCP 后）
5. 单任务平均 token 和工具调用次数

---

## 6. 下一步改造优先级（基于你继续用 MiroThinker）

P0（先做）

1. 真实 MCP SDK 集成
2. Redis 会话存储替换内存版
3. 飞书签名校验 + 幂等去重
4. 工具审计日志

P1（接着做）

1. ChromaDB 长期记忆
2. 用户反馈闭环
3. A/B 测试框架（仍以 MiroThinker 为主，对比 Prompt/版本）

P2（后续）

1. 多模型路由
2. Kubernetes
3. 模型蒸馏

---

## 7. 常见坑（第一次部署高频）

1. SGLang 已启动但 `base_url` 写错（漏了 `/v1`）
2. 模型名不匹配（`XCLAW_LLM_MODEL` 与实际服务不一致）
3. GPU 显存看起来够，但 `max-model-len` 过大导致启动失败
4. 工具调用失败直接抛异常，导致整条请求失败（要用包装器兜底）
5. 没有 trace_id，后续排错非常痛苦

---

## 8. 你可以直接执行的最小启动命令（本地调试）

启动 X-Claw：

```bash
uvicorn x_claw.main:app --host 0.0.0.0 --port 8080
```

调试请求：

```bash
curl -X POST http://127.0.0.1:8080/debug/message \
  -H 'Content-Type: application/json' \
  -d '{"content":"请解释MCP协议"}'
```

---

文档版本：v1.0（配套本目录 V2 骨架代码）

