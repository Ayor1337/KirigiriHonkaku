# Step 2 世界状态核心阶段计划

> 本文档只覆盖项目落地的第二阶段：世界状态核心阶段。
> 它用于承接 [OVERVIEW.md](C:/Users/ayor/PycharmProjects/KirigiriHonkaku/docs/plan/OVERVIEW.md) 与 [STEP1_BACKEND_FOUNDATION.md](C:/Users/ayor/PycharmProjects/KirigiriHonkaku/docs/plan/STEP1_BACKEND_FOUNDATION.md)，进一步明确阶段二的目标、范围、产物与完成标准。
> 当前仍然不拆到逐步任务清单。
> 固定指令：Implementation Plan, Task List and Thought in Chinese

## 1. 阶段定位

Step 2 的目标不是跑通完整玩法，而是把项目的世界状态主模型稳定下来。

这一阶段只回答一个问题：

**怎样把已经明确的数据结构、数据库 schema 和模型边界，真正落成一套可被系统读取、更新、保存和关联的单局世界状态核心。**

## 2. 阶段目标

本阶段的核心目标包括：

- 落地单局游戏的结构化状态主模型
- 固定 `Session / Character / Player / Npc / Map / Location / Clue / Event / Dialogue` 的真实数据落点
- 让世界对象之间的主从关系和关键关联真正成立
- 让 Repository 可以围绕这些对象提供稳定的聚合读取与写入能力
- 让后续主循环实现时，不需要再反复回改顶级实体和数据库根骨架

一句话：

**先让世界状态能被稳定装进去，而不是先让所有动作都跑起来。**

## 3. 阶段范围

Step 2 只覆盖世界状态核心，当前范围如下：

### 3.1 应落地的部分

- `Session` 根状态
- `Character` 公共层
- `Player` 子系统
- `Npc` 子系统
- `Map / Location / Connection` 空间骨架
- `Clue` 归属状态
- `Event / EventParticipant`
- `Dialogue / DialogueParticipant / Utterance`
- 文本附件路径与结构化对象的连接方式
- Repository 的聚合读取边界

### 3.2 当前不纳入的部分

- 动作规则是否完整生效
- 主循环是否完整跑通
- AI 是否已经生成真实文本
- 暴露度和结局是否已经闭环
- 前端是否已经能完整消费所有对象
- 数据库索引和性能调优

## 4. 阶段依赖的设计基础

Step 2 依赖以下设计文档作为事实基础：

### 4.1 架构边界基础

- [ENGINE_SPEC.md](C:/Users/ayor/PycharmProjects/KirigiriHonkaku/docs/architecture/ENGINE_SPEC.md)
- [ACTION_SPEC.md](C:/Users/ayor/PycharmProjects/KirigiriHonkaku/docs/architecture/ACTION_SPEC.md)
- [STATE_BOUNDARY_SPEC.md](C:/Users/ayor/PycharmProjects/KirigiriHonkaku/docs/architecture/STATE_BOUNDARY_SPEC.md)

### 4.2 数据设计基础

- [DATA_STRUCTURE_SPEC.md](C:/Users/ayor/PycharmProjects/KirigiriHonkaku/docs/architecture/DATA_STRUCTURE_SPEC.md)
- [DATABASE_SCHEMA_SPEC.md](C:/Users/ayor/PycharmProjects/KirigiriHonkaku/docs/architecture/DATABASE_SCHEMA_SPEC.md)

## 5. 阶段产物

Step 2 完成后，项目应至少形成以下稳定产物：

### 5.1 结构化世界对象

- `Session` 能承载一局游戏的主状态
- `Character` 能统一玩家和 NPC 的公共关系
- `Player` 与 `Npc` 子系统有明确落点
- `Map`、`Location`、`Connection` 构成完整空间骨架
- `Clue`、`Event`、`Dialogue` 等案件对象有稳定主表与关系

### 5.2 数据库主模型

- SQLAlchemy 模型骨架可以与 schema 一一对应
- Alembic 初始迁移可以围绕既定表顺序稳定推进
- 关键外键和一对一 / 一对多关系已经定住

### 5.3 数据访问骨架

- Repository 可以围绕玩家、NPC、地图、线索、事件、对话做聚合读取
- UnitOfWork 可以在世界状态层提供统一事务边界

## 6. 阶段完成标准

Step 2 是否完成，不看“动作能不能跑”，而看下面这些世界状态标准是否成立：

- 主要结构化对象已经有稳定表与关系
- 顶级实体和主从关系不再反复变动
- `Character` 能真正统一玩家与 NPC 的公共关系
- `Location` 能真正承接角色、线索、事件、对话的空间定位
- `Clue` 能真正表达初始归属与当前归属
- `Dialogue` 能真正表达会话、参与方和发言序列
- `DetectiveBoard`、`Knowledge`、`NpcSchedule` 等重要子系统已不再停留在概念层
- 后续阶段可以在不推翻数据库根骨架的前提下进入动作闭环实现

## 7. 阶段内的重点取舍

本阶段必须坚持以下取舍：

- 优先固定对象关系，不优先跑动作逻辑
- 优先固定数据库主模型，不优先做行为调度
- 优先固定聚合读取边界，不优先做 AI 文本消费
- 优先保证状态一致性，不优先做表现层细节

这意味着：

- 允许阶段二结束时“玩法还没跑起来”
- 但不允许阶段二结束时“世界状态模型还在摇摆”

## 8. 阶段结束后应能承接的下一步

Step 2 完成后，项目应自然进入以下下一层计划：

- 最小动作闭环落地
- 场景快照落地
- `Action / ActionResult` 主执行链落地

也就是：

- Step 2 负责“世界能装”
- Step 3 才开始负责“世界能动”

## 9. 当前结论

Step 2 可以概括为：

**把这个项目从“后端骨架已经存在”推进到“单局世界状态已经有稳定结构化主模型”的阶段，让后续动作系统、AI Runtime 和结局系统都建立在不会反复推翻的数据根骨架之上。**
