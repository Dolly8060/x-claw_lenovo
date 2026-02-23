
# 使用转义处理文档中的特殊字符
document_content = r"""
# X-Claw 智能助手系统技术方案
## 基于 MiroThinker 30B 的企业级 AI 助手架构

**文档版本**: v1.0  
**编制团队**: X-Engine  
**适用硬件**: NVIDIA L20 48GB  
**目标平台**: Feishu (飞书) + Microsoft Teams  
**日期**: 2026年

---

## 目录

1. [方案背景与目标](#1-方案背景与目标)
2. [总体架构设计](#2-总体架构设计)
3. [硬件评估与选型](#3-硬件评估与选型)
4. [详细技术实现](#4-详细技术实现)
5. [部署与运维](#5-部署与运维)
6. [实施路线图](#6-实施路线图)
7. [风险与对策](#7-风险与对策)
8. [附录](#8-附录)

---

## 1. 方案背景与目标

### 1.1 项目背景

随着企业数字化转型的深入，团队急需一个具备深度研究能力的智能助手，能够：
- 自动分解复杂任务并进行多步骤推理
- 处理超长文档（256K上下文）
- 自主进行网页搜索与信息提取
- 管理本地文件资源
- 无缝集成飞书和 Teams 办公平台

### 1.2 核心诉求

| 需求项 | 具体要求 | 优先级 |
|--------|---------|--------|
| **模型能力** | 任务分解、多跳推理、长文本理解 | P0 |
| **工具能力** | 网页搜索、内容提取、文件管理 | P0 |
| **客户端** | Feishu + Teams 双平台支持 | P0 |
| **代码调试** | 不需要 | - |
| **部署方式** | 本地服务器（L20）私有化部署 | P0 |
| **扩展性** | 支持未来接入其他平台（Slack/Discord） | P1 |

### 1.3 技术选型决策

**为什么选择 MiroThinker 30B？**
- 开源可商用（MIT许可证）
- 支持 256K 超长上下文
- 单任务支持 400-600 次工具调用（行业领先）
- 针对研究任务优化（BrowseComp 69.8%，GAIA 81.9%）
- 基于 Qwen3-30B，中文能力优秀

**为什么不直接使用 OpenClaw？**
- OpenClaw 原生依赖云 API（OpenAI/Claude）
- 工具系统为自研 Skill，与 MiroThinker 训练时使用的 MCP 工具不兼容
- 需要深度改造才能支持本地模型和 MCP 协议

**X-Claw 的定位**
- 基于 OpenClaw 架构思想，完全重写
- 原生支持 MCP（Model Context Protocol）
- 专为 MiroThinker 优化
- 企业级多平台接入

---

## 2. 总体架构设计

### 2.1 架构原则

**三层解耦策略**：
1. **接入层**：平台无关的消息网关
2. **编排层**：智能任务调度与记忆管理
3. **能力层**：模型推理与工具执行

### 2.2 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    第一层：接入网关 (Gateway)                  │
│  X-Claw Gateway                                              │
│  ├── Feishu Adapter (Webhook + Event订阅)                    │
│  ├── Teams Adapter (Bot Framework)                           │
│  └── 统一消息队列 (Redis/RabbitMQ)                            │
└──────────────────────┬──────────────────────────────────────┘
                       │  标准化消息格式 (JSON Schema)
┌──────────────────────▼──────────────────────────────────────┐
│                   第二层：编排引擎 (Orchestrator)              │
│  X-Claw Core (魔改自 OpenClaw)                               │
│  ├── 会话管理 (Session Manager)                              │
│  ├── 记忆系统 (Hybrid Memory)                                │
│  │   ├── 短期：Redis (最近10轮)                              │
│  │   └── 长期：向量数据库 (ChromaDB)                         │
│  ├── 任务路由 (Task Router)                                  │
│  └── MCP 客户端 (MCP Client)  ← 关键！连接 MiroFlow          │
└──────────────────────┬──────────────────────────────────────┘
                       │  MCP 协议 (stdio/sse)
┌──────────────────────▼──────────────────────────────────────┐
│                   第三层：能力层 (Capabilities)                │
│  MiroFlow 工具链 (MCP Servers)                               │
│  ├── searching_mcp_server (Serper/Google)                    │
│  ├── browser_session (Playwright网页浏览)                     │
│  ├── reading_mcp_server (文件解析)                           │
│  └── python_mcp_server (可选，仅用于数据处理)                 │
│                                                              │
│  推理引擎 (Inference Engine)                                  │
│  ├── SGLang / vLLM (MiroThinker 30B)                         │
│  └── 量化策略：AWQ-4bit 或 FP8 (L20优化)                      │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 数据流设计

**单次请求完整流程**：

1. 用户消息 (Feishu/Teams)
2. X-Claw Gateway (协议转换)
3. X-Claw Core (编排引擎)
   - 加载会话历史 (Redis)
   - 检索长期记忆 (ChromaDB)
   - 构造 Prompt (含可用工具列表)
4. MiroThinker 30B (SGLang)
   - 生成思考过程
   - 决定工具调用
5. MCP Client
   - 调用 searching (搜索)
   - 调用 browser (浏览网页)
   - 调用 reading (读取文件)
6. 工具执行结果
7. MiroThinker 30B (继续推理)
   - 分析工具返回
   - 决定下一步行动
   - 重复直到给出最终答案
8. X-Claw Core
   - 保存会话 (Redis)
   - 更新记忆 (ChromaDB)
9. X-Claw Gateway
10. 用户收到回复 (Feishu/Teams)

### 2.4 关键技术选型对比

| 组件 | 候选方案 | 最终选择 | 理由 |
|------|---------|---------|------|
| **推理引擎** | vLLM / SGLang / TRT-LLM | **SGLang** | L20 上性能最佳，支持 FP8 |
| **模型格式** | FP16 / AWQ / FP8 / GGUF | **FP8** | L20 Tensor Core 优化，显存占用 24GB |
| **工具协议** | Skill / MCP / Function Call | **MCP** | MiroThinker 训练原生支持 |
| **记忆存储** | Redis / PostgreSQL / MongoDB | **Redis + ChromaDB** | 短期会话 + 长期语义检索 |
| **消息队列** | RabbitMQ / Kafka / Redis | **Redis** | 简化架构，性能足够 |

---

## 3. 硬件评估与选型

### 3.1 NVIDIA L20 48GB 规格分析

| 规格项 | 参数 | 对项目影响 |
|--------|------|-----------|
| **显存** | 48GB GDDR6 | 可单卡部署 30B 模型（FP8 量化后 24GB） |
| **架构** | Ada Lovelace | 第四代 Tensor Core，支持 FP8 |
| **NVLink** | 支持 | 可扩展双卡，支持 256K 长上下文 |
| **TDP** | 275W | 需确保服务器散热和电源 |
| **vLLM 兼容性** | 良好但有退化 | 已知 L20 在 vLLM 上存在性能退化，建议使用 SGLang |

### 3.2 部署模式对比

| 模式 | 配置 | 上下文长度 | 并发能力 | 适用场景 |
|------|------|-----------|---------|---------|
| **单卡 FP8** | 1×L20 48GB | 128K | 3-5 用户 | 初期验证，中小团队 |
| **单卡 FP16** | 1×L20 48GB | 64K | 1-2 用户 | 精度优先，低并发 |
| **双卡 FP8** | 2×L20 96GB | 256K | 8-12 用户 | 满血性能，企业级 |
| **双卡 AWQ-4bit** | 2×L20 96GB | 256K | 15-20 用户 | 极致并发，精度可接受 |

**推荐配置**：单卡 FP8（初期）→ 双卡 FP8（扩展期）

### 3.3 配套硬件建议

| 组件 | 最低配置 | 推荐配置 |
|------|---------|---------|
| **CPU** | 16 核 | 32 核（AMD EPYC 或 Intel Xeon） |
| **内存** | 128GB | 256GB DDR5 |
| **存储** | 1TB NVMe SSD | 2TB NVMe SSD（模型+数据） |
| **网络** | 1Gbps | 10Gbps（多用户场景） |
| **系统** | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |

---

## 4. 详细技术实现

### 4.1 第一层：接入网关 (X-Claw Gateway)

#### 4.1.1 Feishu 接入模块

**技术方案**：使用飞书开放平台 Webhook + Event 订阅模式

```python
# x_claw/adapters/feishu_adapter.py
from larksuiteoapi import Config, Context, DOMAIN_FEISHU
from larksuiteoapi.service.im.v1 import ImService
from fastapi import FastAPI, Request
import asyncio
import json

class FeishuAdapter:
    def __init__(self, app_id, app_secret, encrypt_key, core_engine):
        self.config = Config.new_internal_app_config(DOMAIN_FEISHU, app_id, app_secret)
        self.im_service = ImService(self.config)
        self.encrypt_key = encrypt_key
        self.core = core_engine
        
    async def handle_webhook(self, request):
        payload = await request.json()
        
        if self.encrypt_key:
            payload = self._decrypt(payload)
        
        if "challenge" in payload:
            return {"challenge": payload["challenge"]}
        
        if payload.get("header", {}).get("event_type") == "im.message.receive_v1":
            await self._process_message(payload["event"])
        
        return {"status": "ok"}
    
    async def _process_message(self, event):
        message = event["message"]
        sender = event["sender"]
        
        user_id = sender["sender_id"]["open_id"]
        chat_id = message["chat_id"]
        msg_type = message["message_type"]
        content = json.loads(message["content"])
        
        if msg_type != "text":
            return
        
        text = content.get("text", "")
        
        response = await self.core.process_message(
            user_id=user_id,
            chat_id=chat_id,
            content=text,
            platform="feishu",
            metadata={
                "message_id": message["message_id"],
                "chat_type": event["message"]["chat_type"]
            }
        )
        
        self._send_reply(message["message_id"], response)
```

**飞书后台配置步骤**：
1. 登录飞书开放平台 (open.feishu.cn)
2. 创建企业自建应用
3. 开启机器人能力（获取 App ID, App Secret）
4. 配置事件订阅：
   - 请求地址: `https://your-domain.com/webhook/feishu`
   - 加密密钥: 生成 32 位随机字符串
   - 订阅事件: `im.message.receive_v1`
5. 配置权限：`im:chat:readonly`, `im:message:send`, `im:message.group_msg`

#### 4.1.2 Microsoft Teams 接入模块

**技术方案**：使用 Bot Framework SDK

```python
# x_claw/adapters/teams_adapter.py
from botbuilder.core import BotFrameworkAdapter, TurnContext, MessageFactory
from botbuilder.schema import Activity, ActivityTypes

class TeamsAdapter:
    def __init__(self, app_id, app_password, core_engine):
        self.adapter = BotFrameworkAdapter(app_id, app_password)
        self.core = core_engine
        
    async def handle_request(self, request):
        body = await request.json()
        activity = Activity().deserialize(body)
        auth_header = request.headers.get("Authorization", "")
        
        async def on_turn(turn_context):
            if turn_context.activity.type == ActivityTypes.message:
                await self._process_message(turn_context)
        
        await self.adapter.process_activity(activity, auth_header, on_turn)
        return {"status": "ok"}
    
    async def _process_message(self, turn_context):
        user_id = turn_context.activity.from_property.id
        text = turn_context.activity.text
        conversation_id = turn_context.activity.conversation.id
        
        await turn_context.send_activity(Activity(type=ActivityTypes.typing))
        
        response = await self.core.process_message(
            user_id=user_id,
            chat_id=conversation_id,
            content=text,
            platform="teams"
        )
        
        await turn_context.send_activity(MessageFactory.text(response))
```

### 4.2 第二层：编排引擎 (X-Claw Core)

#### 4.2.1 核心架构

```python
# x_claw/core/engine.py
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
import json

@dataclass
class Session:
    user_id: str
    platform: str
    chat_id: str
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    history: list = field(default_factory=list)
    context: dict = field(default_factory=dict)

class XClawCore:
    def __init__(self, mcp_client, llm_client, memory_store, max_iterations=50):
        self.mcp = mcp_client
        self.llm = llm_client
        self.memory = memory_store
        self.max_iterations = max_iterations
        self.active_sessions = {}
        
    async def process_message(self, user_id, chat_id, content, platform, metadata=None):
        session_key = f"{platform}:{user_id}:{chat_id}"
        
        # 1. 加载或创建会话
        session = await self._get_or_create_session(session_key, user_id, platform, chat_id)
        
        # 2. 检索长期记忆
        memories = await self.memory.retrieve_long_term(user_id, content, top_k=5)
        
        # 3. 获取可用工具列表
        tools = await self.mcp.get_available_tools()
        
        # 4. 构造系统提示词
        system_prompt = self._build_system_prompt(tools, memories)
        
        # 5. 构造消息历史
        messages = self._build_messages(session, content, system_prompt)
        
        # 6. 执行 Agent Loop
        result = await self._agent_loop(messages, tools, session_key)
        
        # 7. 保存会话和记忆
        await self._save_session(session, content, result)
        if result["success"]:
            await self.memory.save_long_term(user_id, content, result["answer"])
        
        return self._format_response(result)
    
    async def _agent_loop(self, messages, tools, session_key):
        iteration = 0
        tool_call_count = 0
        
        while iteration < self.max_iterations:
            iteration += 1
            
            response = await self.llm.chat.completions.create(
                model="mirothinker-30b",
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.3,
                max_tokens=4096
            )
            
            message = response.choices[0].message
            
            if message.tool_calls:
                tool_call_count += len(message.tool_calls)
                messages.append({
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [tc.model_dump() for tc in message.tool_calls]
                })
                
                for tool_call in message.tool_calls:
                    result = await self._execute_tool(tool_call)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result
                    })
            else:
                return {
                    "success": True,
                    "answer": message.content,
                    "tool_calls": tool_call_count
                }
        
        return {"success": False, "answer": "处理超时", "tool_calls": tool_call_count}
    
    async def _execute_tool(self, tool_call):
        parts = tool_call.function.name.split("__")
        server_name, tool_name = parts[0], parts[1]
        arguments = json.loads(tool_call.function.arguments)
        
        result = await self.mcp.call_tool(server_name, tool_name, arguments)
        return result.content[0].text if result.content else "无输出"
```

#### 4.2.2 记忆系统

```python
# x_claw/core/memory.py
import redis
import chromadb
from chromadb.config import Settings
import hashlib

class HybridMemoryStore:
    def __init__(self, redis_url="redis://localhost:6379", chroma_path="./data/chroma"):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.chroma_client = chromadb.Client(Settings(persist_directory=chroma_path))
        self.collection = self.chroma_client.get_or_create_collection("x_claw_memories")
        
    async def save_session(self, user_id, history):
        key = f"session:{user_id}"
        self.redis.setex(key, 3600 * 24, json.dumps(history))
    
    async def get_recent_history(self, user_id, limit=10):
        data = self.redis.get(f"session:{user_id}")
        if data:
            history = json.loads(data)
            return history[-limit:]
        return []
    
    async def save_long_term(self, user_id, query, answer):
        content = f"Q: {query}\nA: {answer}"
        doc_id = hashlib.md5(f"{user_id}:{content}".encode()).hexdigest()
        
        self.collection.add(
            documents=[content],
            ids=[doc_id],
            metadatas=[{"user_id": user_id, "query": query}]
        )
        self.chroma_client.persist()
    
    async def retrieve_long_term(self, user_id, query, top_k=5):
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where={"user_id": user_id}
        )
        return results['documents'][0] if results else []
```

### 4.3 第三层：能力层

#### 4.3.1 MCP 客户端

```python
# x_claw/mcp/client.py
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import yaml

class MiroFlowMCPClient:
    def __init__(self, config_path):
        self.config = self._load_config(config_path)
        self.sessions = {}
        self.tools_cache = []
        
    def _load_config(self, path):
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    
    async def initialize(self):
        for server_name, server_config in self.config.get("mcp_servers", {}).items():
            await self._connect_server(server_name, server_config)
        await self._cache_tools()
    
    async def _connect_server(self, name, config):
        params = StdioServerParameters(
            command=config["command"],
            args=config.get("args", []),
            env={**config.get("env", {}), **self.config.get("env", {})}
        )
        
        stdio_transport = await stdio_client(params)
        session = ClientSession(stdio_transport[0], stdio_transport[1])
        await session.initialize()
        self.sessions[name] = session
    
    async def get_available_tools(self):
        return self.tools_cache
    
    async def call_tool(self, server_name, tool_name, arguments):
        if server_name not in self.sessions:
            raise ValueError(f"Server {server_name} not connected")
        session = self.sessions[server_name]
        return await session.call_tool(tool_name, arguments)
```

#### 4.3.2 推理引擎配置

```yaml
# config/mcp_servers.yaml
mcp_servers:
  searching:
    command: "python"
    args: ["-m", "src.tool.mcp_servers.searching_mcp_server"]
    env:
      SERPER_API_KEY: "${SERPER_API_KEY}"
      SEARCHING_TOP_N: "10"
      
  browser:
    command: "python"
    args: ["-m", "src.tool.mcp_servers.browser_session"]
    env:
      BROWSER_HEADLESS: "true"
      
  reading:
    command: "python"
    args: ["-m", "src.tool.mcp_servers.reading_mcp_server"]
```

---

## 5. 部署与运维

### 5.1 环境准备

```bash
# 系统更新
sudo apt update && sudo apt upgrade -y

# 安装 CUDA
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt update
sudo apt install -y cuda-toolkit-12-4

# 安装依赖
sudo apt install -y python3-pip python3-venv redis-server

# 环境变量
echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
```

### 5.2 推理引擎部署

**SGLang 部署（推荐）**：

```bash
# 安装
pip install sglang[all]

# 启动（单卡 L20 FP8）
python -m sglang.launch_server \
  --model miromind-ai/MiroThinker-v1.5-30B \
  --tp 1 \
  --quantization fp8 \
  --mem-fraction-static 0.85 \
  --max-model-len 131072 \
  --port 8000

# 双卡扩展
python -m sglang.launch_server \
  --model miromind-ai/MiroThinker-v1.5-30B \
  --tp 2 \
  --quantization fp8 \
  --max-model-len 262144 \
  --port 8000
```

### 5.3 Docker Compose 配置

```yaml
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"
    volumes:
      - chroma_data:/chroma/chroma

  sglang:
    image: sglang/sglang:latest
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=0
    volumes:
      - ./models:/models
    command: >
      python -m sglang.launch_server
      --model /models/mirothinker-30b
      --tp 1 --quantization fp8
      --port 8000 --host 0.0.0.0
    ports:
      - "8000:8000"

  x-claw:
    build: .
    ports:
      - "8080:8080"
    environment:
      - REDIS_URL=redis://redis:6379
      - LLM_BASE_URL=http://sglang:8000/v1
    env_file:
      - .env

volumes:
  redis_data:
  chroma_data:
```

---

## 6. 实施路线图

### Week 1：基础设施
- [ ] L20 环境配置（CUDA、驱动）
- [ ] SGLang + MiroThinker 30B 部署
- [ ] MiroFlow 工具链测试
- [ ] 压力测试

### Week 2：X-Claw Core
- [ ] MCP 客户端封装
- [ ] 会话管理与记忆系统
- [ ] Agent Loop 实现
- [ ] 单元测试

### Week 3：接入层
- [ ] Feishu 机器人开发
- [ ] Teams 机器人开发
- [ ] 消息队列集成
- [ ] 端到端联调

### Week 4：优化
- [ ] 长上下文压力测试
- [ ] 并发性能优化
- [ ] 监控部署
- [ ] 文档编写

### Week 5：上线
- [ ] 安全加固
- [ ] 容灾备份
- [ ] 灰度发布
- [ ] 正式上线

---

## 7. 风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| L20 显存不足 | 无法部署 | 使用 FP8 量化，或升级双卡 |
| SGLang 兼容性问题 | 输出异常 | 准备 vLLM 备选方案 |
| MCP 工具链不稳定 | 调用失败 | 实现重试机制 + 降级策略 |
| Serper API 额度耗尽 | 搜索失效 | 接入 DuckDuckGo 作为 fallback |

---

## 8. 附录

### 8.1 术语表
- **MCP**: Model Context Protocol，模型上下文协议
- **SGLang**: 高性能 LLM 推理引擎
- **FP8**: 8-bit 浮点量化
- **Agent Loop**: 智能体循环

### 8.2 参考资源
- MiroThinker: https://github.com/MiroMindAI
- SGLang: https://docs.sglang.ai/
- MCP: https://modelcontextprotocol.io/

### 8.3 性能基准
- 简单问答: < 5s
- 研究任务（10 次工具调用）: < 30s
- 长文档分析（128K）: < 60s
- 并发用户: 5-10 人

---

**文档结束**

*X-Engine 团队 | 2026年*
"""

# 保存文档
output_path = '/mnt/kimi/output/X-Claw_Technical_Solution.md'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(document_content)

print("✅ 技术方案文档已生成！")
print(f"文档路径: {output_path}")
print(f"文档大小: {len(document_content)} 字符")
print(f"文档行数: {len(document_content.splitlines())} 行")
