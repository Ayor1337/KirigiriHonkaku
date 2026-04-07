# Step 6 内容扩展 API 规范

> 本文档描述当前对外 HTTP 接口约定。
> 当前版本已将会话 bootstrap 从模板装配改为多轮 AGENT 生成，并为首页新建流程补充了实时阶段流。
> 固定指令：Implementation Plan, Task List and Thought in Chinese

## 1. 范围

当前对外使用以下接口：

- `POST /api/v1/sessions`
- `POST /api/v1/sessions/bootstrap-stream`
- `GET /api/v1/sessions`
- `POST /api/v1/sessions/{session_id}/bootstrap`
- `GET /api/v1/sessions/{session_id}`
- `GET /api/v1/sessions/{session_id}/state`
- `GET /api/v1/sessions/{session_id}/player`
- `GET /api/v1/sessions/{session_id}/map`
- `GET /api/v1/sessions/{session_id}/npcs`
- `POST /api/v1/actions`

当前版本不新增：

- 后台异步任务系统
- 独立任务轮询接口
- 模板列表查询接口
- 侦探板接口
- 知识池接口
- 隐藏区域专用动作接口

## 2. 会话创建

### 2.1 `POST /api/v1/sessions`

请求体：

- 空请求体
- 不再接收 `title`
- 不再接收 `case_template_key / map_template_key / truth_template_key`

示例：

```http
POST /api/v1/sessions
```

成功响应语义：

- 创建最小会话根记录
- 生成 `uuid`
- 初始化运行时目录
- 返回当前状态 `draft`
- `title` 初始允许为 `null`
- `root_ids` 初始为空对象 `{}`

成功响应示例：

```json
{
  "id": "...",
  "uuid": "...",
  "title": null,
  "status": "draft",
  "start_time_minute": 0,
  "current_time_minute": 0,
  "data_directories": {
    "session_root": "...",
    "story": "...",
    "history": "...",
    "truth": "...",
    "npc": "...",
    "dialogue": "...",
    "clue": "..."
  },
  "root_ids": {}
}
```

## 3. 实时创建与世界生成

### 3.1 `POST /api/v1/sessions/bootstrap-stream`

作用：

- 创建一个新的 `draft` 会话
- 立即进入 `generating`
- 通过 SSE 按阶段返回创建与世界生成进度
- 成功后发出最终 `complete` 事件
- 失败时发出 `error` 事件，并保证会话回退到 `draft`

响应类型：

- `Content-Type: text/event-stream`

事件类型：

- `stage`
- `complete`
- `error`

`stage` 事件字段：

- `placeholder`：阶段占位符，供前端自行翻译
- `session_id`：从 `session_created` 开始返回
- `attempt`：仅 `world_validating / world_fixing` 相关阶段按需返回
- `max_attempts`：仅校验修正链路按需返回

当前阶段占位符枚举：

- `session_creating`
- `session_created`
- `world_planning`
- `world_generating`
- `world_validating`
- `world_fixing`
- `world_persisting`
- `world_ready`

阶段流示例：

```text
event: stage
data: {"placeholder":"session_creating"}

event: stage
data: {"placeholder":"session_created","session_id":"..."}

event: stage
data: {"placeholder":"world_planning","session_id":"..."}

event: stage
data: {"placeholder":"world_generating","session_id":"..."}

event: stage
data: {"placeholder":"world_validating","session_id":"...","attempt":1,"max_attempts":3}

event: stage
data: {"placeholder":"world_persisting","session_id":"..."}

event: stage
data: {"placeholder":"world_ready","session_id":"..."}

event: complete
data: {"session_id":"...","status":"ready","created_counts":{"characters":3},"root_ids":{"player_id":"...","map_id":"..."}}
```

`complete` 事件语义：

- 与 `POST /api/v1/sessions/{session_id}/bootstrap` 的成功响应等价
- 前端可直接从 `root_ids.player_id` 和 `session_id` 进入游戏

`error` 事件字段：

- `code`
- `message`
- `session_id`：若空会话已创建则返回
- `failed_placeholder`：失败发生时最近一个阶段占位符

`error` 示例：

```text
event: error
data: {"code":"generation_failed","message":"Generated world blueprint failed validation.","session_id":"...","failed_placeholder":"world_validating"}
```

失败语义：

- `generation_failed`：AGENT 输出通过 JSON 解析，但未通过本地业务校验
- `generation_output_invalid`：AGENT 输出无法解析为结构化结果
- `generation_provider_error`：模型 provider 不可用、超时或调用失败
- `internal_error`：其他未分类错误

## 4. 会话列表查询

### 4.1 `GET /api/v1/sessions`

说明：

- 返回全部会话的基础状态列表
- 响应体为数组，不额外包裹 `items/total`
- 默认按 `created_at` 倒序（最新创建的会话在前）
- 列表项不包含 `data_directories`
- 列表项不包含 `root_ids`

示例：

```http
GET /api/v1/sessions
```

成功响应示例：

```json
[
  {
    "id": "...",
    "uuid": "...",
    "title": null,
    "status": "draft",
    "start_time_minute": 0,
    "current_time_minute": 0
  },
  {
    "id": "...",
    "uuid": "...",
    "title": "Generated Case 4f26c2ad",
    "status": "ready",
    "start_time_minute": 0,
    "current_time_minute": 15
  }
]
```

## 5. 世界初始化（兼容接口）

### 5.1 `POST /api/v1/sessions/{session_id}/bootstrap`

作用：

- 将指定 `draft` 会话切换到 `generating`
- 通过多轮 AGENT 生成完整可玩的游戏世界
- 生成正式 `title`
- 生成地图、NPC、线索、事件与 truth payload
- 校验结构合法性后一次性落库
- 成功后将会话状态切为 `ready`

说明：

- 该接口继续保留，供兼容调用使用
- 首页新建流程优先使用 `POST /api/v1/sessions/bootstrap-stream`

成功响应示例：

```json
{
  "session_id": "...",
  "status": "ready",
  "created_counts": {
    "characters": 3,
    "players": 1,
    "npcs": 2,
    "locations": 3,
    "connections": 2,
    "clues": 2,
    "events": 1,
    "dialogues": 0
  },
  "root_ids": {
    "player_id": "...",
    "map_id": "..."
  }
}
```

失败语义：

- `404`：会话不存在
- `409`：会话已 `ready`
- `409`：会话当前处于 `generating`
- `422`：AGENT 返回结构可解析，但未通过本地业务校验
- `502`：AGENT 返回内容无法解析为结构化结果
- `503`：模型 provider 不可用、超时或调用失败

`422` 示例：

```json
{
  "detail": {
    "message": "Generated world blueprint failed validation.",
    "errors": [
      "truth.required_clue_keys must contain at least one clue key."
    ]
  }
}
```

## 6. 会话读取

### 6.1 `GET /api/v1/sessions/{session_id}`

说明：

- 只返回会话基础状态、目录信息与根 ID 信息
- `title` 在 `draft / generating` 阶段允许为 `null`
- `root_ids` 在会话未完成 bootstrap 时允许为空对象 `{}`
- 不再返回 `player`
- 不再返回 `map`
- 不再返回顶层 `exposure_value / exposure_level`
- 可用于确认 bootstrap 失败后状态是否已回退为 `draft`

成功响应示例（`draft`）：

```json
{
  "id": "...",
  "uuid": "...",
  "title": null,
  "status": "draft",
  "start_time_minute": 0,
  "current_time_minute": 0,
  "data_directories": {
    "session_root": "...",
    "story": "...",
    "history": "...",
    "truth": "...",
    "npc": "...",
    "dialogue": "...",
    "clue": "..."
  },
  "root_ids": {}
}
```

成功响应示例（`ready`）：

```json
{
  "id": "...",
  "uuid": "...",
  "title": "Generated Case 4f26c2ad",
  "status": "ready",
  "start_time_minute": 0,
  "current_time_minute": 15,
  "data_directories": {
    "session_root": "...",
    "story": "...",
    "history": "...",
    "truth": "...",
    "npc": "...",
    "dialogue": "...",
    "clue": "..."
  },
  "root_ids": {
    "player_id": "...",
    "map_id": "..."
  }
}
```

### 6.2 `GET /api/v1/sessions/{session_id}/state`

说明：

- 返回会话级状态详情
- 当前只包含暴露度字段
- 只要会话存在，无论 `draft / generating / ready / ended` 都可读取

成功响应示例：

```json
{
  "exposure_value": 0,
  "exposure_level": "low"
}
```

### 6.3 `GET /api/v1/sessions/{session_id}/player`

说明：

- 返回当前会话玩家详情
- 仅在会话完成 bootstrap 后可读
- 若会话存在但玩家尚未生成，返回 `404`

成功响应示例：

```json
{
  "id": "...",
  "character_id": "...",
  "display_name": "Detective Kirigiri",
  "public_identity": "Independent Detective",
  "template_key": "case-manor",
  "template_name": "Detective",
  "trait_text": "冷静、谨慎、擅长交叉验证证词。",
  "background_text": "受邀前来调查庄园中的异常事件。",
  "current_location_id": "...",
  "current_location_name": "Entrance Hall",
  "exposure_value": 0,
  "exposure_level": "low"
}
```

失败语义：

- `404`：会话不存在
- `404`：会话存在但玩家尚未生成，detail 为 `Player not found for session.`

### 6.4 `GET /api/v1/sessions/{session_id}/map`

说明：

- 返回当前会话地图详情
- 仅在会话完成 bootstrap 后可读
- 若会话存在但地图尚未生成，返回 `404`

成功响应示例：

```json
{
  "id": "...",
  "template_key": "map-manor",
  "display_name": "Moonview Manor",
  "locations": [
    {
      "id": "...",
      "key": "archive-room",
      "parent_location_id": "...",
      "name": "Archive Room",
      "description": "存放旧档案和纸质材料的房间。",
      "location_type": "interior",
      "visibility_level": "restricted",
      "is_hidden": false,
      "status_flags": {}
    }
  ],
  "connections": [
    {
      "id": "...",
      "from_location_id": "...",
      "to_location_id": "...",
      "connection_type": "door",
      "access_rule": {},
      "is_hidden": false,
      "is_locked": false,
      "is_one_way": false,
      "is_dangerous": false,
      "time_window_rule": {}
    }
  ]
}
```

失败语义：

- `404`：会话不存在
- `404`：会话存在但地图尚未生成，detail 为 `Map not found for session.`

### 6.5 `GET /api/v1/sessions/{session_id}/npcs`

说明：

- 返回当前会话中所有 `has_met_player = true` 的 NPC
- 按 NPC 创建顺序返回
- 会话存在但尚未见过任何 NPC 时返回空数组 `[]`
- draft 会话也可调用，结果通常为空数组

成功响应示例：

```json
[
  {
    "id": "...",
    "character_id": "...",
    "template_key": "journalist",
    "display_name": "Journalist Ren",
    "public_identity": "Freelance Reporter",
    "current_location_id": "...",
    "current_location_name": "Archive Room",
    "has_met_player": true
  }
]
```

空列表示例：

```json
[]
```

失败语义：

- `404`：会话不存在

当前会话状态包括：

- `draft`
- `generating`
- `ready`
- `ended`

## 7. 动作提交

### 7.1 `POST /api/v1/actions`

当前仍支持：

- `move`
- `talk`
- `investigate`
- `gather`
- `accuse`

### 7.2 状态前置约束

动作提交前会校验会话状态：

- `draft`：返回 `409`，detail 为 `Session world state has not been bootstrapped.`
- `generating`：返回 `409`，detail 为 `Session world state is currently being generated.`
- `ended`：返回 `409`，detail 为 `Session has already ended.`

### 7.3 AI 生成记录

每次动作请求在经过叙事 runtime 后，都会把本次生成结果追加写入会话历史目录下的 `ai_generation_log.jsonl`。

当前 `storage_refs` 中会返回：

- `ai_generation_log`：本次会话级 AI 生成日志文件路径
- `latest_action_log`：最近一次动作摘要 JSON 文件路径
- `history_markdown`：动作历史 Markdown 文件路径

`ai_generation_log.jsonl` 中每一行都是一条独立 JSON，包含：

- `action_type`
- `status`
- `runtime_metadata`
- `raw_output_text`
- `result`

### 7.4 其他动作语义

当前 `move / talk / investigate / gather / accuse` 的引擎语义保持不变。

## 8. 当前结论

当前版本对外 API 的关键变化是：

- `POST /sessions` 继续保留为空请求体创建空会话
- 新增 `POST /sessions/bootstrap-stream`，用于首页实时创建与阶段显示
- `GET /sessions` 继续返回全部会话列表
- `GET /sessions/{id}` 继续返回 `root_ids`，用于前端继续游戏
- 玩家详情、地图详情、暴露度与已见过 NPC 列表已拆到独立读取接口
- `bootstrap` 兼容接口继续保留，但不再是首页新建流程的首选入口
- 前端阶段名称不由后端返回，而是由前端基于占位符自行翻译

