# Step 6 最小 Demo 流程

> 本文档给出当前版本的最小演示路径。
> 目标是证明系统已经具备“空会话 + 多轮 AGENT 生成完整游戏 + 现有动作闭环仍可运行”的能力。
> 固定指令：Implementation Plan, Task List and Thought in Chinese

## 1. Demo 目标

通过一条最小流程证明以下能力已经成立：

- 系统可以创建空会话，而不是先提交模板参数
- bootstrap 会通过多轮 AGENT 生成完整游戏
- 标题会在 bootstrap 成功后由 AGENT 回写
- 现有 `move / investigate / talk / gather / accuse` 闭环仍能跑通
- 生成失败时会话状态会回退到 `draft`

## 2. 演示步骤

### 2.1 创建会话

```http
POST /api/v1/sessions
```

观察点：

- 返回 `draft`
- `title = null`
- 会话创建成功

### 2.2 bootstrap 世界

```http
POST /api/v1/sessions/{session_id}/bootstrap
```

观察点：

- `status = ready`
- `title` 已在后续 `GET /sessions/{id}` 中出现
- `created_counts` 含地图、角色、线索、事件统计

### 2.3 读取会话，确认标题已回写

```http
GET /api/v1/sessions/{session_id}
```

观察点：

- `status = ready`
- `title` 不再为 `null`

### 2.4 执行动作闭环

使用当前已有动作流继续演示：

- `move`
- `investigate`
- `talk`
- `gather`
- `accuse`

观察点：

- 当前动作接口仍可正常消费 AGENT 生成的世界状态
- `truth_payload`、NPC 文档、线索文档均已生成并落盘

## 3. 失败演示

### 3.1 模型不可用

将生成 runtime 配置为不可用后执行：

```http
POST /api/v1/sessions/{session_id}/bootstrap
```

预期：

- 返回 `503`
- detail 为 `Game generation runtime is not configured.`
- `GET /sessions/{id}` 仍显示 `status = draft`
- `title` 仍为 `null`

### 3.2 结构校验失败

若 AGENT 输出缺少关键 truth 约束，预期：

- 返回 `422`
- detail 中包含 `Generated world blueprint failed validation.`
- 会话状态回退为 `draft`

## 4. 自动化对应

当前这条流程已由以下自动化覆盖：

- `tests/api/test_sessions.py`
- `tests/api/test_world_bootstrap.py`
- `tests/api/test_actions.py`
- `tests/api/test_content_expansion.py`

## 5. 当前结论

如果以上流程成立，就说明当前版本已经具备：

- 空会话创建能力
- 多轮 AGENT 完整建局能力
- 生成失败可回退能力
- 保持动作主循环不破坏的扩展能力
