# Step 6 游戏生成运行时规范

> 本文档描述当前版本的内部运行时接口。
> 当前系统已从模板组合装配切换为多轮 AGENT 生成完整游戏。
> 固定指令：Implementation Plan, Task List and Thought in Chinese

## 1. 目标

当前内部运行时需要解决三件事：

- 如何用多轮 AGENT 生成完整可玩的案件
- 如何将 AGENT 输出约束为当前后端可消费的结构
- 如何在失败时不留下半套世界状态

## 2. 运行时分层

当前世界生成由三层组成：

- `GameGenerationRuntime`
  - 对外暴露 `generate(session_uuid)`
  - 负责多轮模型调用
- `WorldBlueprint`
  - 作为 AGENT 最终输出契约
  - 必须能被当前 ORM bootstrap 逻辑消费
- `WorldBootstrapService`
  - 负责状态切换、落库、文件写入与失败回退

## 3. 多轮 AGENT 流程

### 3.1 Plan 阶段

输入：

- `session.uuid`

输出：

- `title`
- `premise`
- `setting`
- `tone`
- 世界规模目标

### 3.2 Generate 阶段

基于 `Plan` 生成完整 `WorldBlueprint`。

顶层必须至少包含：

- `title`
- `map`
- `locations`
- `connections`
- `player`
- `npcs`
- `clues`
- `events`
- `truth`

### 3.3 Validate / Fix 阶段

流程固定为：

1. 用 Pydantic 校验结构是否合法
2. 用本地业务校验器检查引用闭合与主线约束
3. 若失败，将错误列表回喂模型进行修正
4. 超过修正上限则失败

## 4. 本地业务约束

当前本地校验至少覆盖：

- location key 唯一
- npc key 唯一
- clue key 唯一
- 连接引用的地点必须存在
- 玩家与 NPC 初始地点必须存在
- 线索必须满足“地点/持有者”二选一约束
- 事件参与者必须引用已存在角色
- `truth.culprit_npc_key` 必须引用已存在 NPC
- `truth.required_clue_keys` 至少包含一条线索
- `npc.profile_markdown / npc.memory_markdown / clue.document_markdown` 不得为空

## 5. 会话状态机

bootstrap 相关状态流转如下：

- `draft` -> `generating` -> `ready`
- 若生成失败：`generating` -> `draft`

约束：

- `draft` 才允许启动 bootstrap
- `generating` 中不允许再次 bootstrap
- `generating` 中不允许提交 action
- 失败时不得留下半套地图/NPC/线索/Event

## 6. 当前边界

当前明确不做：

- 后台异步任务系统
- 任务轮询接口
- 模板回退
- 自由文本 fallback 世界
- 与动作主循环解耦的新世界结构

## 7. 当前结论

当前版本的内部运行时核心不再是“模板注册 + 组合校验”，而是三条稳定边界：

- 多轮 AGENT 生成边界
- `WorldBlueprint` 结构约束边界
- `draft / generating / ready` 状态机边界
