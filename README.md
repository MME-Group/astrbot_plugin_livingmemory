# LivingMemory - 动态生命周期记忆插件

**版本**: v2.1.9 | **作者**: lxfight | **许可证**: AGPLv3

---

## 核心特性

- **混合检索**: 结合 BM25 稀疏检索和 Faiss 向量检索，使用 RRF 融合算法
- **双路四模式检索**: 同时维护文档路与图路，两边都支持关键词检索与向量检索，再统一融合排序
- **智能总结**: 使用 LLM 自动总结对话历史，生成结构化记忆
- **双通道总结**: `canonical_summary`（事实导向，用于检索）与 `persona_summary`（人格风格，用于注入）解耦存储
- **会话隔离**: 支持按人格和会话隔离记忆
- **Agent 主动记忆工具**: 暴露 `recall_long_term_memory`（主动回忆）和 `save_long_term_memory`（主动保存）两个工具，Agent 可自行选择回忆时机或将关键信息写入长期记忆
- **自动遗忘**: 基于时间和重要性的智能清理机制
- **数据安全**: 迁移前自动备份、索引重建带备份回滚、删除操作带事务保护
- **WebUI 管理**: 可视化记忆管理界面

---

## 快速开始

### 安装

将插件文件夹放置于 AstrBot 的 `data/plugins` 目录下，AstrBot 将自动安装依赖。

### 配置

通过 AstrBot 控制台的插件配置页面进行配置：

**必需配置**:
- `embedding_provider_id`: 向量嵌入模型 ID（留空使用默认）
- `llm_provider_id`: 大语言模型 ID（留空使用默认）

**WebUI 配置**:
```json
{
  "webui_settings": {
    "enabled": true,
    "host": "127.0.0.1",
    "port": 8080,
    "access_password": "your_password"
  }
}
```

---

## 命令

| 命令 | 说明 |
| :--- | :--- |
| `/lmem status` | 查看记忆库状态 |
| `/lmem search <query> [k]` | 搜索记忆（默认 5 条） |
| `/lmem forget <id>` | 删除指定记忆 |
| `/lmem rebuild-index` | 重建索引（修复索引不一致） |
| `/lmem rebuild-graph` | 重建图记忆索引（为旧记忆回填图数据） |
| `/lmem webui` | 查看 WebUI 信息 |
| `/lmem reset` | 重置当前会话记忆上下文 |
| `/lmem cleanup [preview\|exec]` | 清理历史消息中的记忆注入片段（默认 preview 预演） |
| `/lmem help` | 显示帮助 |

---

## 架构说明

### 模块结构

```
astrbot_plugin_livingmemory/
├── main.py                          # 插件注册和生命周期管理
├── core/
│   ├── base/                        # 基础组件（配置、常量、异常）
│   ├── managers/                    # 核心管理器（MemoryEngine、ConversationManager）
│   ├── retrieval/                   # 检索层（HybridRetriever、BM25、向量）
│   ├── validators/                  # 验证器（IndexValidator）
│   ├── plugin_initializer.py        # 插件初始化器
│   ├── event_handler.py             # 事件处理器
│   └── command_handler.py           # 命令处理器
├── storage/                         # 存储层（DBMigration、ConversationStore）
├── webui/                           # Web 管理界面
├── tests/                           # 测试套件
└── docs/                            # 文档
```

### 核心组件

1. **PluginInitializer**: 负责插件初始化
   - 非阻塞初始化机制
   - Provider等待和重试
   - 自动数据库迁移

2. **EventHandler**: 处理事件钩子
   - 群聊消息捕获
   - 记忆召回
   - 记忆反思

3. **Agent 记忆工具**: 为 tool loop / agent 模式提供主动记忆能力
   - `recall_long_term_memory`: 主动回忆长期记忆；复用现有会话隔离和人格隔离配置；返回原始记忆列表，不额外注入 prompt
   - `save_long_term_memory`: 主动保存到长期记忆；默认重要性 0.7，支持 [0.0, 1.0]；**默认关闭**，需在配置中将 `active_memory_tools.enable_save_tool` 设为 `true` 才会注册
   - 两者与被动反思总结独立运行，互为补充

4. **CommandHandler**: 处理命令
   - 统一命令响应格式
   - 完善的错误处理

5. **ConfigManager**: 配置管理
   - 集中配置加载
   - 配置验证
   - 嵌套键访问

---

## Agent 主动记忆工具

除了每轮自动记忆召回外，插件在运行时还会向 AstrBot 注册两个 LLM 工具。

### `recall_long_term_memory`（主动回忆）

让 Agent 自行决定何时回忆长期记忆，以及用什么关键词回忆。

特点：

- Agent 可以自己决定是否回忆长期记忆，而不是只能依赖当前轮消息作为查询词
- 工具回忆范围自动继承当前配置中的会话隔离与人格隔离设置
- 检索结果作为工具返回进入 agent 上下文，不会再次走记忆 prompt 注入链路
- 更适合用户要求“回忆”“想起”“之前提过什么”或当前指代不清、需要补查历史上下文的情况

建议的调用策略：

- 优先使用简短关键词，而不是直接复制整句用户输入
- 优先回忆主题、实体名、偏好、约定、历史事件等高信息量词语
- 如果第一次回忆结果不理想，可以换一个更具体或更抽象的关键词再次回忆

返回结果为原始记忆列表，包含记忆内容、相关分数、重要性及会话/人格元数据，便于 agent 自行判断哪些结果真正相关。

### `save_long_term_memory`（主动保存）

让 Agent 在对话中主动把“值得长期记住”的信息写入长期记忆，弥补被动反思总结在轮次到达前的延迟。

适合调用的场景：

- 用户明确说“记住……”
- 用户表达出稳定偏好（喜欢什么、不能吃什么）
- 模型自行判断某条事实值得长期保留

输入参数：

- `content: str` — 简洁、自包含的第三人称总结（建议 <200 字）
- `importance: float = 0.7` — 重要性，范围 [0.0, 1.0]；约 0.3 表示一般偏好、0.7 表示重要事实（默认）、≥0.9 表示关键承诺

工具行为：

- 写入使用当前会话的 `unified_msg_origin` 和当前人格
- 元数据中自动带上 `source="llm_tool_save"` 与 `triggered_by="save_long_term_memory"`，方便后续区分主动写入和被动反思
- 该工具与被动反思总结**独立运行**，同一事实可能被双路径重复记录，故通过 `active_memory_tools.enable_save_tool` 开关控制；**默认关闭**，需手动设为 `true` 才会把 `save_long_term_memory` 注册到 Agent 工具列表

---

## 开发者指南

### 测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_config_manager.py

# 查看覆盖率
pytest --cov=core tests/
```


### 文档

- [API文档](docs/API.md): 详细的API参考
- [架构文档](docs/ARCHITECTURE.md): 系统架构说明
- [开发者指南](docs/DEVELOPMENT.md): 开发和贡献指南

---

## 数据迁移（v1.4.0-1.4.2）

如果您从 v1.4.0-1.4.2 版本升级，旧数据可能无法自动迁移。手动恢复步骤：

1. 找到备份文件：`data/plugin_data/astrbot_plugin_livingmemory/backups/livingmemory_backup_<时间戳>.db`
2. 将该文件移动到：`data/plugin_data/astrbot_plugin_livingmemory/`
3. 重命名为：`livingmemory.db`
4. 重载插件，系统会自动加载和处理数据

---

## 更新记录

详见 [CHANGELOG.md](CHANGELOG.md)

---

## 支持

- **GitHub**: [astrbot_plugin_livingmemory](https://github.com/lxfight-s-Astrbot-Plugins/astrbot_plugin_livingmemory)
- **问题反馈**: [GitHub Issues](https://github.com/lxfight-s-Astrbot-Plugins/astrbot_plugin_livingmemory/issues)
- **QQ 群**: [![加入QQ群](https://img.shields.io/badge/QQ群-953245617-blue?style=flat-square&logo=tencent-qq)](https://qm.qq.com/cgi-bin/qm/qr?k=WdyqoP-AOEXqGAN08lOFfVSguF2EmBeO&jump_from=webapi&authKey=tPyfv90TVYSGVhbAhsAZCcSBotJuTTLf03wnn7/lQZPUkWfoQ/J8e9nkAipkOzwh)
  （口令：lxfight）

---

## 许可证

本项目遵循 AGPLv3 许可证。
