# 数据库 Schema 设计

> 本文档在 [DATA_STRUCTURE_SPEC.md](C:/Users/ayor/PycharmProjects/KirigiriHonkaku/docs/architecture/DATA_STRUCTURE_SPEC.md) 的实体骨架之上，直接给出 PostgreSQL 关系型 schema 设计。
> 当前目标是明确表、主外键关系、字段层级与约束方向，不展开到 ORM 写法与 migration 步骤。
> 固定指令：Implementation Plan, Task List and Thought in Chinese

## 1. 设计原则

- 所有核心表统一使用 `UUID` 作为主键
- 所有数据都从属于某个 `session`
- 结构化状态与长文本附件分离
- 玩家与 NPC 的公共关系统一通过 `character` 承接
- 先保证规则一致性，再追求完全范式化
- 对于高变化、弱规则的数据，允许使用 `JSONB`

## 2. PostgreSQL 约定

### 2.1 主键

所有核心表主键统一为：

- `id UUID PRIMARY KEY`

### 2.2 时间列

所有审计时间统一为：

- `created_at TIMESTAMPTZ`
- `updated_at TIMESTAMPTZ`

### 2.3 枚举策略

当前建议：

- 优先使用 `TEXT + CHECK` 或应用层约束
- 不急于为每个字段单独建 PostgreSQL enum

这样做的原因：

- 早期迭代时变更成本更低
- 不会因为枚举膨胀拖累 migration

### 2.4 JSONB 使用范围

以下场景允许优先使用 `JSONB`：

- `status_flags`
- `temporary_effects`
- `rule_flags`
- `resource_flags`
- `tag_flags`

但以下内容不建议塞进 `JSONB`：

- 主关系
- 主外键
- 关键状态主值
- 需要频繁 join 的核心结构

## 3. 表清单总览

当前建议的数据库表如下：

### 会话根表

- `session`

### 角色体系

- `character`
- `player`
- `player_state`
- `player_inventory`
- `player_knowledge`
- `knowledge_entry`
- `knowledge_topic`
- `detective_board`
- `board_item`
- `board_link`
- `board_note`
- `npc`
- `npc_state`
- `npc_schedule`
- `schedule_entry`

### 地图体系

- `map`
- `location`
- `connection`

### 案件对象

- `clue`
- `event`
- `event_participant`

### 对话体系

- `dialogue`
- `dialogue_participant`
- `utterance`

## 4. 会话根表

### 4.1 `session`

一局游戏的根表。

#### 建议字段

- `id UUID PK`
- `uuid TEXT UNIQUE`
- `title TEXT`
- `status TEXT`
- `start_time_minute INTEGER NOT NULL`
- `current_time_minute INTEGER NOT NULL`
- `incident_time_minute INTEGER`
- `exposure_value INTEGER NOT NULL DEFAULT 0`
- `exposure_level TEXT`
- `ending_type TEXT`
- `accusation_state TEXT`
- `case_template_key TEXT`
- `map_template_key TEXT`
- `truth_template_key TEXT`
- `story_file_path TEXT`
- `history_file_path TEXT`
- `truth_file_path TEXT`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`

#### 说明

- `uuid` 可作为外部可读会话标识
- `status` 表示会话整体运行状态
- `ending_type` 和 `accusation_state` 暂不单独拉表

## 5. 角色体系

### 5.1 `character`

玩家和 NPC 的公共壳。

#### 建议字段

- `id UUID PK`
- `session_id UUID NOT NULL FK -> session.id`
- `kind TEXT NOT NULL`
- `display_name TEXT NOT NULL`
- `public_identity TEXT`
- `current_location_id UUID FK -> location.id`
- `is_active BOOLEAN NOT NULL DEFAULT TRUE`
- `can_participate_dialogue BOOLEAN NOT NULL DEFAULT TRUE`
- `can_hold_clue BOOLEAN NOT NULL DEFAULT TRUE`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`

#### 约束建议

- `CHECK (kind IN ('player','npc'))`

### 5.2 `player`

玩家主表。

#### 建议字段

- `id UUID PK`
- `session_id UUID NOT NULL UNIQUE FK -> session.id`
- `character_id UUID NOT NULL UNIQUE FK -> character.id`
- `template_key TEXT`
- `template_name TEXT`
- `trait_text TEXT`
- `background_text TEXT`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`

#### 说明

- 一局只允许一个 `player`
- 一个 `player` 必须唯一对应一个 `character`

### 5.3 `player_state`

玩家动态状态表。

#### 建议字段

- `id UUID PK`
- `player_id UUID NOT NULL UNIQUE FK -> player.id`
- `hp_state TEXT`
- `injury_state TEXT`
- `poison_state TEXT`
- `exposure_value INTEGER NOT NULL DEFAULT 0`
- `exposure_level TEXT`
- `status_flags JSONB NOT NULL DEFAULT '{}'`
- `temporary_effects JSONB NOT NULL DEFAULT '{}'`
- `unlocked_access JSONB NOT NULL DEFAULT '[]'`
- `updated_at TIMESTAMPTZ NOT NULL`

### 5.4 `player_inventory`

玩家持有资源与物品状态。

#### 建议字段

- `id UUID PK`
- `player_id UUID NOT NULL UNIQUE FK -> player.id`
- `money_amount INTEGER NOT NULL DEFAULT 0`
- `resource_flags JSONB NOT NULL DEFAULT '{}'`
- `held_item_refs JSONB NOT NULL DEFAULT '[]'`
- `equipped_item_refs JSONB NOT NULL DEFAULT '[]'`
- `credential_refs JSONB NOT NULL DEFAULT '[]'`
- `weapon_refs JSONB NOT NULL DEFAULT '[]'`
- `document_refs JSONB NOT NULL DEFAULT '[]'`
- `updated_at TIMESTAMPTZ NOT NULL`

#### 说明

- 当前不额外设计通用 `item` 表
- 这一层先保持轻量，后续需要再拆

### 5.5 `player_knowledge`

玩家统一知识池容器。

#### 建议字段

- `id UUID PK`
- `player_id UUID NOT NULL UNIQUE FK -> player.id`
- `summary_text TEXT`
- `last_updated_at TIMESTAMPTZ`

### 5.6 `knowledge_topic`

知识主题表。

#### 建议字段

- `id UUID PK`
- `player_knowledge_id UUID NOT NULL FK -> player_knowledge.id`
- `name TEXT NOT NULL`
- `description TEXT`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`

### 5.7 `knowledge_entry`

知识条目表。

#### 建议字段

- `id UUID PK`
- `player_knowledge_id UUID NOT NULL FK -> player_knowledge.id`
- `topic_id UUID FK -> knowledge_topic.id`
- `source_type TEXT NOT NULL`
- `source_ref_id UUID`
- `title TEXT`
- `content TEXT NOT NULL`
- `importance_level TEXT`
- `learned_at_minute INTEGER`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`

#### 说明

- `source_type + source_ref_id` 表示知识来源
- 来源可来自 `clue`、`dialogue`、`event`、`npc`、`location`

### 5.8 `detective_board`

玩家唯一侦探板。

#### 建议字段

- `id UUID PK`
- `player_id UUID NOT NULL UNIQUE FK -> player.id`
- `board_layout_version INTEGER NOT NULL DEFAULT 1`
- `updated_at TIMESTAMPTZ NOT NULL`

### 5.9 `board_item`

侦探板卡片。

#### 建议字段

- `id UUID PK`
- `board_id UUID NOT NULL FK -> detective_board.id`
- `target_type TEXT NOT NULL`
- `target_ref_id UUID NOT NULL`
- `position_x DOUBLE PRECISION`
- `position_y DOUBLE PRECISION`
- `group_key TEXT`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`

#### 约束建议

- `target_type` 当前只允许：
  - `npc`
  - `location`
  - `clue`
  - `event`

### 5.10 `board_link`

侦探板连线。

#### 建议字段

- `id UUID PK`
- `board_id UUID NOT NULL FK -> detective_board.id`
- `from_item_id UUID NOT NULL FK -> board_item.id`
- `to_item_id UUID NOT NULL FK -> board_item.id`
- `label TEXT`
- `style_key TEXT`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`

### 5.11 `board_note`

侦探板自由备注。

#### 建议字段

- `id UUID PK`
- `board_id UUID NOT NULL FK -> detective_board.id`
- `content TEXT NOT NULL`
- `position_x DOUBLE PRECISION`
- `position_y DOUBLE PRECISION`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`

### 5.12 `npc`

NPC 主表。

#### 建议字段

- `id UUID PK`
- `session_id UUID NOT NULL FK -> session.id`
- `character_id UUID NOT NULL UNIQUE FK -> character.id`
- `template_key TEXT`
- `role_type TEXT`
- `profile_file_path TEXT`
- `memory_file_path TEXT`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`

### 5.13 `npc_state`

NPC 当前状态。

#### 建议字段

- `id UUID PK`
- `npc_id UUID NOT NULL UNIQUE FK -> npc.id`
- `current_location_id UUID FK -> location.id`
- `attitude_to_player TEXT`
- `alertness_level TEXT`
- `emotion_tag TEXT`
- `is_available BOOLEAN NOT NULL DEFAULT TRUE`
- `is_in_event BOOLEAN NOT NULL DEFAULT FALSE`
- `is_under_pressure BOOLEAN NOT NULL DEFAULT FALSE`
- `state_flags JSONB NOT NULL DEFAULT '{}'`
- `updated_at TIMESTAMPTZ NOT NULL`

### 5.14 `npc_schedule`

NPC 日程容器。

#### 建议字段

- `id UUID PK`
- `npc_id UUID NOT NULL UNIQUE FK -> npc.id`
- `schedule_mode TEXT`
- `updated_at TIMESTAMPTZ NOT NULL`

### 5.15 `schedule_entry`

日程条目。

#### 建议字段

- `id UUID PK`
- `schedule_id UUID NOT NULL FK -> npc_schedule.id`
- `start_minute INTEGER NOT NULL`
- `end_minute INTEGER NOT NULL`
- `behavior_type TEXT NOT NULL`
- `behavior_description TEXT`
- `target_location_id UUID FK -> location.id`
- `priority INTEGER NOT NULL DEFAULT 0`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`

## 6. 地图体系

### 6.1 `map`

会话地图根表。

#### 建议字段

- `id UUID PK`
- `session_id UUID NOT NULL UNIQUE FK -> session.id`
- `template_key TEXT`
- `display_name TEXT`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`

### 6.2 `location`

统一空间点。

#### 建议字段

- `id UUID PK`
- `map_id UUID NOT NULL FK -> map.id`
- `parent_location_id UUID FK -> location.id`
- `name TEXT NOT NULL`
- `description TEXT`
- `location_type TEXT NOT NULL`
- `visibility_level TEXT`
- `is_hidden BOOLEAN NOT NULL DEFAULT FALSE`
- `status_flags JSONB NOT NULL DEFAULT '{}'`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`

#### 说明

- `parent_location_id` 用于表达混合分层地图
- 不强制所有地图都严格三层

### 6.3 `connection`

地点间连接关系。

#### 建议字段

- `id UUID PK`
- `map_id UUID NOT NULL FK -> map.id`
- `from_location_id UUID NOT NULL FK -> location.id`
- `to_location_id UUID NOT NULL FK -> location.id`
- `connection_type TEXT`
- `access_rule JSONB NOT NULL DEFAULT '{}'`
- `is_hidden BOOLEAN NOT NULL DEFAULT FALSE`
- `is_locked BOOLEAN NOT NULL DEFAULT FALSE`
- `is_one_way BOOLEAN NOT NULL DEFAULT FALSE`
- `is_dangerous BOOLEAN NOT NULL DEFAULT FALSE`
- `time_window_rule JSONB NOT NULL DEFAULT '{}'`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`

#### 说明

- `connection` 当前保持单一实体
- 限制、隐藏、危险、限时等条件先挂在本表

## 7. 案件对象

### 7.1 `clue`

统一线索表。

#### 建议字段

- `id UUID PK`
- `session_id UUID NOT NULL FK -> session.id`
- `name TEXT NOT NULL`
- `description TEXT`
- `clue_type TEXT NOT NULL`
- `initial_location_id UUID FK -> location.id`
- `initial_holder_character_id UUID FK -> character.id`
- `current_location_id UUID FK -> location.id`
- `current_holder_character_id UUID FK -> character.id`
- `is_key_clue BOOLEAN NOT NULL DEFAULT FALSE`
- `is_movable BOOLEAN NOT NULL DEFAULT TRUE`
- `is_time_sensitive BOOLEAN NOT NULL DEFAULT FALSE`
- `clue_state TEXT`
- `document_file_path TEXT`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`

#### 约束建议

- 初始归属必须二选一：
  - `initial_location_id`
  - `initial_holder_character_id`
- 当前归属必须二选一：
  - `current_location_id`
  - `current_holder_character_id`

### 7.2 `event`

特殊规则状态事件。

#### 建议字段

- `id UUID PK`
- `session_id UUID NOT NULL FK -> session.id`
- `name TEXT NOT NULL`
- `event_type TEXT NOT NULL`
- `description TEXT`
- `location_id UUID NOT NULL FK -> location.id`
- `start_minute INTEGER NOT NULL`
- `end_minute INTEGER NOT NULL`
- `event_state TEXT`
- `is_public_event BOOLEAN NOT NULL DEFAULT FALSE`
- `rule_flags JSONB NOT NULL DEFAULT '{}'`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`

### 7.3 `event_participant`

事件参与者。

#### 建议字段

- `id UUID PK`
- `event_id UUID NOT NULL FK -> event.id`
- `character_id UUID NOT NULL FK -> character.id`
- `participant_role TEXT`
- `attendance_state TEXT`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`

## 8. 对话体系

### 8.1 `dialogue`

一次完整会话。

#### 建议字段

- `id UUID PK`
- `session_id UUID NOT NULL FK -> session.id`
- `dialogue_type TEXT`
- `location_id UUID NOT NULL FK -> location.id`
- `start_minute INTEGER NOT NULL`
- `end_minute INTEGER`
- `summary_file_path TEXT`
- `transcript_file_path TEXT`
- `tag_flags JSONB NOT NULL DEFAULT '{}'`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`

#### 说明

- `dialogue` 是会话，不是单条发言
- 摘要和全文不单独做结构化表

### 8.2 `dialogue_participant`

会话参与者。

#### 建议字段

- `id UUID PK`
- `dialogue_id UUID NOT NULL FK -> dialogue.id`
- `character_id UUID NOT NULL FK -> character.id`
- `participant_role TEXT`
- `created_at TIMESTAMPTZ NOT NULL`

### 8.3 `utterance`

单条发言。

#### 建议字段

- `id UUID PK`
- `dialogue_id UUID NOT NULL FK -> dialogue.id`
- `sequence_no INTEGER NOT NULL`
- `speaker_character_id UUID NOT NULL FK -> character.id`
- `content TEXT NOT NULL`
- `tone_tag TEXT`
- `utterance_flags JSONB NOT NULL DEFAULT '{}'`
- `created_at TIMESTAMPTZ NOT NULL`

#### 约束建议

- `UNIQUE(dialogue_id, sequence_no)`

## 9. 状态概念承载位置

### 9.1 Exposure

当前建议同时体现在两层：

- `session.exposure_value / exposure_level`
- `player_state.exposure_value / exposure_level`

后续如要保持单一事实源，可统一收敛到一层。

### 9.2 Accusation

当前不单独拉表。

建议承载位置：

- `session.accusation_state`
- 动作结果日志

### 9.3 Ending

当前不单独拉表。

建议承载位置：

- `session.ending_type`
- `session.status`

## 10. 文件附件归属

以下内容不作为结构化表，而作为文本附件路径挂在对应表上：

- `session.story_file_path`
- `session.history_file_path`
- `session.truth_file_path`
- `npc.profile_file_path`
- `npc.memory_file_path`
- `dialogue.summary_file_path`
- `dialogue.transcript_file_path`
- `clue.document_file_path`

## 11. 关键关系总结

- 一个 `session` 只有一个 `player`
- 一个 `session` 有多个 `character`
- 一个 `player` 必须唯一对应一个 `character`
- 一个 `npc` 必须唯一对应一个 `character`
- 一个 `session` 只有一个 `map`
- 一个 `map` 有多个 `location`
- 一个 `map` 有多个 `connection`
- 一个 `session` 有多个 `clue`
- 一个 `session` 有多个 `event`
- 一个 `event` 有多个 `event_participant`
- 一个 `session` 有多个 `dialogue`
- 一个 `dialogue` 有多个 `dialogue_participant`
- 一个 `dialogue` 有多条 `utterance`
- `utterance.speaker_character_id` 统一指向 `character`

## 12. 当前结论

当前数据库 schema 可以概括为：

**以 `session` 为根，以 `character` 统一玩家与 NPC 的公共关系，以 `map/location/connection` 承担空间结构，以 `clue/event/dialogue` 承担案件互动对象，再由玩家与 NPC 各自扩展出子系统，并通过文件路径字段接入故事、记忆、摘要与全文等长文本资料。**
