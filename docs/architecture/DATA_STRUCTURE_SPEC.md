# 数据结构设计

> 本文档在现有玩法规格与架构边界之上，直接定义项目的数据结构设计。
> 当前目标是明确实体、关系、字段层级与文本附件归属，供后续数据库设计与实现设计使用。
> 固定指令：Implementation Plan, Task List and Thought in Chinese

## 1. 设计目标

这份设计要解决四件事：

- 定义一局游戏的核心结构化对象
- 明确对象之间的主从关系和引用方向
- 明确哪些内容进数据库，哪些内容只作为文本附件
- 为后续 PostgreSQL / SQLAlchemy 设计提供稳定骨架

当前不处理：

- 表名和字段类型
- 索引和外键细节
- Alembic 迁移顺序
- API 返回格式

## 2. 总体结构

整套数据结构以 `Session` 为根。

```text
Session
├─ Character
│  ├─ Player
│  │  ├─ PlayerState
│  │  ├─ PlayerInventory
│  │  ├─ PlayerKnowledge
│  │  │  ├─ KnowledgeEntry
│  │  │  └─ KnowledgeTopic
│  │  └─ DetectiveBoard
│  │     ├─ BoardItem
│  │     ├─ BoardLink
│  │     └─ BoardNote
│  └─ Npc
│     ├─ NpcState
│     └─ NpcSchedule
│        └─ ScheduleEntry
├─ Map
│  ├─ Location
│  └─ Connection
├─ Clue
├─ Event
│  └─ EventParticipant
└─ Dialogue
   ├─ DialogueParticipant
   └─ Utterance
```

另有三类不单独抬成顶级实体的状态概念：

- `Exposure`
- `Accusation`
- `Ending`

## 3. 根实体

### 3.1 Session

`Session` 表示一局游戏，是一切数据的根归属。

#### 建议字段层级

- 标识信息
  - `id`
  - `uuid`
  - `title`
- 时间信息
  - `start_time_minute`
  - `current_time_minute`
  - `incident_time_minute`
- 游戏状态
  - `status`
  - `ending_type`
  - `accusation_state`
  - `exposure_value`
  - `exposure_level`
- 模板来源
  - `case_template_key`
  - `map_template_key`
  - `truth_template_key`
- 文本附件引用
  - `story_file_path`
  - `history_file_path`
  - `truth_file_path`
- 审计信息
  - `created_at`
  - `updated_at`

#### 说明

- `Session` 是结构化状态根，不承载长文本正文
- `STORY.md`、`HISTORY.md`、`TRUTH.md` 通过文件路径或文件键关联

## 4. 角色公共层

### 4.1 Character

`Character` 是玩家和 NPC 的公共壳，用来统一所有“谁在说话、谁在场、谁持有某物”的关系。

#### 建议字段层级

- 标识信息
  - `id`
  - `session_id`
  - `kind` (`player` / `npc`)
- 基础信息
  - `display_name`
  - `public_identity`
- 空间信息
  - `current_location_id`
- 互动能力
  - `is_active`
  - `can_participate_dialogue`
  - `can_hold_clue`
- 审计信息
  - `created_at`
  - `updated_at`

#### 说明

- `Character` 只放玩家与 NPC 共享的那一层
- 不放玩家属性、NPC 日程、玩家知识池这类专属内容

## 5. 玩家子系统

### 5.1 Player

`Player` 是玩家角色主实体，用于连接玩家专属子系统。

#### 建议字段层级

- 标识信息
  - `id`
  - `session_id`
  - `character_id`
- 模板信息
  - `template_key`
  - `template_name`
- 角色构筑
  - `trait_text`
  - `background_text`
- 审计信息
  - `created_at`
  - `updated_at`

### 5.2 PlayerState

`PlayerState` 放玩家当前动态状态。

#### 建议字段层级

- 生命与风险
  - `hp_state`
  - `injury_state`
  - `poison_state`
- 暴露与局势
  - `exposure_value`
  - `exposure_level`
- 临时状态
  - `status_flags`
  - `temporary_effects`
- 可达权限
  - `unlocked_access`
- 审计信息
  - `updated_at`

#### 说明

- `PlayerState` 不再继续拆硬状态/软状态子实体
- 硬软边界作为规则约束保留

### 5.3 PlayerInventory

`PlayerInventory` 放玩家当前持有资源与物品状态。

#### 建议字段层级

- 资源概览
  - `money_amount`
  - `resource_flags`
- 物品容器
  - `held_item_refs`
  - `equipped_item_refs`
- 特殊持有
  - `credential_refs`
  - `weapon_refs`
  - `document_refs`
- 审计信息
  - `updated_at`

#### 说明

- 当前只定义层级，不要求现在拆 Item 实体
- 第一阶段可将物品引用和资源状态做成相对轻量的结构

### 5.4 PlayerKnowledge

`PlayerKnowledge` 是玩家统一知识池。

#### 建议字段层级

- 标识信息
  - `id`
  - `player_id`
- 汇总状态
  - `summary_text`
  - `last_updated_at`

#### 子结构

##### KnowledgeEntry

表示一条玩家已纳入知识池的信息。

建议字段层级：

- 标识信息
  - `id`
  - `player_knowledge_id`
- 来源信息
  - `source_type`
  - `source_ref_id`
- 内容信息
  - `title`
  - `content`
  - `importance_level`
- 归类信息
  - `topic_id`
- 时间信息
  - `learned_at_minute`

##### KnowledgeTopic

表示玩家知识池中的主题归类。

建议字段层级：

- 标识信息
  - `id`
  - `player_knowledge_id`
- 分类信息
  - `name`
  - `description`

#### 说明

- `PlayerKnowledge` 采用“底层按来源、上层按主题”的结构
- 不再硬拆“已知事实”和“已获线索”

### 5.5 DetectiveBoard

`DetectiveBoard` 是玩家唯一的侦探板实体。

#### 建议字段层级

- 标识信息
  - `id`
  - `player_id`
- 视图状态
  - `board_layout_version`
  - `updated_at`

#### 子结构

##### BoardItem

表示板上的一张卡片。

建议字段层级：

- 标识信息
  - `id`
  - `board_id`
- 引用信息
  - `target_type`
  - `target_ref_id`
- 展示信息
  - `position_x`
  - `position_y`
  - `group_key`

当前只允许引用：

- `Npc`
- `Location`
- `Clue`
- `Event`

##### BoardLink

表示两张卡片之间的连接。

建议字段层级：

- 标识信息
  - `id`
  - `board_id`
- 连接信息
  - `from_item_id`
  - `to_item_id`
- 展示信息
  - `label`
  - `style_key`

##### BoardNote

表示自由备注。

建议字段层级：

- 标识信息
  - `id`
  - `board_id`
- 内容信息
  - `content`
- 展示信息
  - `position_x`
  - `position_y`

## 6. NPC 子系统

### 6.1 Npc

`Npc` 是 NPC 主实体。

#### 建议字段层级

- 标识信息
  - `id`
  - `session_id`
  - `character_id`
- 基础设定引用
  - `profile_file_path`
  - `memory_file_path`
- 模板信息
  - `template_key`
  - `role_type`
- 审计信息
  - `created_at`
  - `updated_at`

### 6.2 NpcState

`NpcState` 放 NPC 当前结构化状态。

#### 建议字段层级

- 空间状态
  - `current_location_id`
- 互动状态
  - `attitude_to_player`
  - `alertness_level`
  - `emotion_tag`
- 规则状态
  - `is_available`
  - `is_in_event`
  - `is_under_pressure`
  - `state_flags`
- 审计信息
  - `updated_at`

#### 说明

- `NpcState` 承接软状态，但不单独再拆实体
- `MEMORY.md` 是记忆正文唯一文本载体，不再单独建 `NpcMemory`

### 6.3 NpcSchedule

`NpcSchedule` 是 NPC 的日程容器。

#### 建议字段层级

- 标识信息
  - `id`
  - `npc_id`
- 汇总状态
  - `schedule_mode`
  - `updated_at`

#### 子结构

##### ScheduleEntry

表示一条日程安排。

建议字段层级：

- 标识信息
  - `id`
  - `schedule_id`
- 时间范围
  - `start_minute`
  - `end_minute`
- 行为信息
  - `behavior_type`
  - `behavior_description`
- 位置目标
  - `target_location_id`
- 优先级
  - `priority`

## 7. 地图子系统

### 7.1 Map

`Map` 是会话中的空间骨架。

#### 建议字段层级

- 标识信息
  - `id`
  - `session_id`
- 模板信息
  - `template_key`
  - `display_name`
- 审计信息
  - `created_at`
  - `updated_at`

### 7.2 Location

`Location` 表示地图中的统一空间点。

#### 建议字段层级

- 标识信息
  - `id`
  - `map_id`
- 基础信息
  - `name`
  - `description`
  - `location_type`
- 层级信息
  - `parent_location_id`
- 展示与状态
  - `visibility_level`
  - `is_hidden`
  - `status_flags`

#### 说明

- `Location` 支持父级层次
- 但不强制所有地图严格三层

### 7.3 Connection

`Connection` 表示两个 `Location` 之间的连接关系。

#### 建议字段层级

- 标识信息
  - `id`
  - `map_id`
- 连接信息
  - `from_location_id`
  - `to_location_id`
- 类型信息
  - `connection_type`
- 条件信息
  - `access_rule`
  - `is_hidden`
  - `is_locked`
  - `is_one_way`
  - `is_dangerous`
- 时间信息
  - `time_window_rule`

#### 说明

- `Connection` 当前保持单一实体
- 不继续拆更多子结构
- 不单独做 `LocationContent`

## 8. 案件对象

### 8.1 Clue

`Clue` 是统一线索实体。

#### 建议字段层级

- 标识信息
  - `id`
  - `session_id`
- 基础信息
  - `name`
  - `description`
  - `clue_type`
- 初始归属
  - `initial_holder_type`
  - `initial_holder_ref_id`
- 当前归属
  - `current_holder_type`
  - `current_holder_ref_id`
- 状态信息
  - `is_key_clue`
  - `is_movable`
  - `is_time_sensitive`
  - `clue_state`
- 文本附件
  - `document_file_path`

#### 说明

- `Clue` 区分初始归属 / 当前归属
- 当前归属在任一时刻只能有一个：
  - `Location`
  - `Npc`
  - `Player`
- 不额外拆 `ClueDocument` 实体

### 8.2 Event

`Event` 表示地点在某段时间里的特殊规则状态。

#### 建议字段层级

- 标识信息
  - `id`
  - `session_id`
- 基础信息
  - `name`
  - `event_type`
  - `description`
- 位置与时间
  - `location_id`
  - `start_minute`
  - `end_minute`
- 规则状态
  - `event_state`
  - `is_public_event`
  - `rule_flags`

#### 子结构

##### EventParticipant

表示参与某个事件的角色。

建议字段层级：

- 标识信息
  - `id`
  - `event_id`
- 角色信息
  - `character_id`
- 参与状态
  - `participant_role`
  - `attendance_state`

## 9. 对话子系统

### 9.1 Dialogue

`Dialogue` 表示一次完整会话。

#### 建议字段层级

- 标识信息
  - `id`
  - `session_id`
- 基础信息
  - `dialogue_type`
  - `location_id`
- 时间信息
  - `start_minute`
  - `end_minute`
- 结果信息
  - `summary_file_path`
  - `transcript_file_path`
  - `tag_flags`
- 审计信息
  - `created_at`
  - `updated_at`

#### 说明

- `Dialogue` 是会话，不是单条发言
- 摘要和全文不单独做结构化实体，只作为文本附件

### 9.2 DialogueParticipant

表示一次会话中的参与方。

#### 建议字段层级

- 标识信息
  - `id`
  - `dialogue_id`
- 角色信息
  - `character_id`
- 参与状态
  - `participant_role`

### 9.3 Utterance

表示会话中的单条发言。

#### 建议字段层级

- 标识信息
  - `id`
  - `dialogue_id`
- 顺序信息
  - `sequence_no`
- 说话方
  - `speaker_character_id`
- 文本附件
  - `content`
- 标签信息
  - `tone_tag`
  - `utterance_flags`

#### 说明

- 每条 `Utterance` 只对应一个说话方
- 说话方统一指向 `Character`

## 10. 非顶级独立实体的状态概念

### 10.1 Exposure

当前不单独做顶级实体。

建议承载位置：

- `Session`
- 或 `PlayerState`

### 10.2 Accusation

当前不单独做顶级实体。

建议承载位置：

- 动作结果
- 事件结果
- 或 `Session` 当前结案状态

### 10.3 Ending

当前不单独做顶级实体。

建议承载位置：

- `Session` 终局状态

## 11. 文本附件归属

以下内容不作为独立结构化实体，而是作为附件挂在对应对象上：

- `STORY.md` -> `Session`
- `HISTORY.md` -> `Session`
- `TRUTH.md` -> `Session`
- `PROFILE.md` -> `Npc`
- `MEMORY.md` -> `Npc`
- 对话摘要 -> `Dialogue`
- 对话全文 -> `Dialogue`
- 线索正文材料 -> `Clue`

## 12. 当前结论

当前数据结构可以概括为：

**以 Session 为根，以 Character 统一玩家和 NPC，以 Map/Location/Connection 承担空间系统，以 Clue/Event/Dialogue 承担案件互动对象，再由 Player 和 Npc 各自扩展出自己的子系统，最终通过结构化状态与文本附件共同构成一局完整案件的数据骨架。**
