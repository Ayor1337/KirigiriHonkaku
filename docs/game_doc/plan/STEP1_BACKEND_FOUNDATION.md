# Step 1 后端骨架阶段计划

> 本文档只覆盖项目落地的第一阶段：后端骨架阶段。
> 它用于承接 [OVERVIEW.md](C:/Users/ayor/PycharmProjects/KirigiriHonkaku/docs/plan/OVERVIEW.md) 的总体落地顺序，并进一步明确阶段一的目标、范围、产物与完成标准。
> 当前仍然不拆到逐步任务清单。
> 固定指令：Implementation Plan, Task List and Thought in Chinese

## 1. 阶段定位

Step 1 的目标不是做出完整可玩版本，而是把整个项目的后端骨架搭稳。

这一阶段只回答一个问题：

**怎样把现有的玩法规格、架构边界、数据结构和数据库设计，转化为一个稳定、可继续扩展的后端基础盘。**

## 2. 阶段目标

本阶段的核心目标包括：

- 建立单体后端基础结构
- 固定 `API -> Engine -> Repository/FileStorage -> AI Runtime` 主链路
- 固定 `FastAPI + PostgreSQL + SQLAlchemy 2.0 + Alembic + data/` 的基础技术盘
- 固定代码目录、模型目录、仓库层、引擎层和 AI Runtime 的模块边界
- 让后续阶段能够在不推翻骨架的前提下继续推进

一句话：

**先把系统骨架搭起来，而不是先把玩法细节全部做完。**

## 3. 阶段范围

Step 1 只覆盖骨架级落地，当前范围如下：

### 3.1 应落地的部分

- 单体后端应用结构
- `app/` 单包源码布局
- `/api/v1` 路由组织方式
- 数据库连接与迁移基础设施
- SQLAlchemy 模型组织方式
- Repository / UnitOfWork 结构
- FileStorage 结构
- Game Engine 主入口与规则模块目录
- AI Runtime 模块边界和基础调用层
- 运行时 `data/` 目录约定

### 3.2 当前不纳入的部分

- 完整调查主循环逻辑
- AI 提示词质量调优
- 暴露度和结局的完整业务闭环
- 多案件模板与内容扩展
- 侦探板的复杂行为实现
- 完整的前端交互支持

## 4. 阶段依赖的设计基础

Step 1 依赖以下设计文档作为事实基础：

### 4.1 玩法规格基础

- [GAME_SPEC.md](C:/Users/ayor/PycharmProjects/KirigiriHonkaku/docs/specs/GAME_SPEC.md)
- [PLAYER_SPEC.md](C:/Users/ayor/PycharmProjects/KirigiriHonkaku/docs/specs/PLAYER_SPEC.md)
- [MAP_SPEC.md](C:/Users/ayor/PycharmProjects/KirigiriHonkaku/docs/specs/MAP_SPEC.md)
- [CLUE_SPEC.md](C:/Users/ayor/PycharmProjects/KirigiriHonkaku/docs/specs/CLUE_SPEC.md)
- [DIALOGUE_SPEC.md](C:/Users/ayor/PycharmProjects/KirigiriHonkaku/docs/specs/DIALOGUE_SPEC.md)

### 4.2 架构边界基础

- [FRAMEWORK_SPEC.md](C:/Users/ayor/PycharmProjects/KirigiriHonkaku/docs/architecture/FRAMEWORK_SPEC.md)
- [ENGINE_SPEC.md](C:/Users/ayor/PycharmProjects/KirigiriHonkaku/docs/architecture/ENGINE_SPEC.md)
- [AI_RUNTIME_SPEC.md](C:/Users/ayor/PycharmProjects/KirigiriHonkaku/docs/architecture/AI_RUNTIME_SPEC.md)
- [ACTION_SPEC.md](C:/Users/ayor/PycharmProjects/KirigiriHonkaku/docs/architecture/ACTION_SPEC.md)
- [STATE_BOUNDARY_SPEC.md](C:/Users/ayor/PycharmProjects/KirigiriHonkaku/docs/architecture/STATE_BOUNDARY_SPEC.md)
- [TECH_STACK_SPEC.md](C:/Users/ayor/PycharmProjects/KirigiriHonkaku/docs/architecture/TECH_STACK_SPEC.md)

### 4.3 数据设计基础

- [DATA_STRUCTURE_SPEC.md](C:/Users/ayor/PycharmProjects/KirigiriHonkaku/docs/architecture/DATA_STRUCTURE_SPEC.md)
- [DATABASE_SCHEMA_SPEC.md](C:/Users/ayor/PycharmProjects/KirigiriHonkaku/docs/architecture/DATABASE_SCHEMA_SPEC.md)

## 5. 阶段产物

Step 1 完成后，项目应至少形成以下稳定产物：

### 5.1 应用骨架

- 可以启动的 FastAPI 应用入口
- 明确的 `api/v1` 路由聚合方式
- 明确的 `app/` 目录结构

### 5.2 数据基础设施

- PostgreSQL 连接配置
- SQLAlchemy 2.0 基础配置
- Alembic 初始迁移骨架
- `data/` 运行时目录约定

### 5.3 模型与持久化骨架

- 模型文件分组已经固定
- Repository 结构已经固定
- UnitOfWork 事务入口已经固定
- FileStorage 已有基础读写边界

### 5.4 规则与 AI 骨架

- Game Engine 主入口存在
- 规则模块目录存在
- `Action` / `ActionResult` 结构存在
- AI Runtime 入口存在
- AI Runtime 与 Engine 的调用边界已经固定

## 6. 阶段完成标准

Step 1 是否完成，不看“玩法有没有跑通”，而看下面这些骨架标准是否成立：

- 单体后端代码布局已经固定
- 主要模块边界不再反复变动
- 数据模型和数据库 schema 已能进入实现
- Repository / FileStorage / Engine / AI Runtime 调用方向明确
- `Action` 进入引擎、`ActionResult` 输出的主链路在结构上成立
- 后续阶段能够在不推翻骨架的前提下继续往主循环实现推进

## 7. 阶段内的重点取舍

本阶段必须坚持以下取舍：

- 优先搭骨架，不优先补功能细节
- 优先定边界，不优先做内容量
- 优先定主链路，不优先补边缘行为
- 优先保证规则层和 AI 层分工，不让 AI 越权接管世界硬状态

这意味着：

- 允许阶段一结束时“功能少”
- 但不允许阶段一结束时“结构乱”

## 8. 阶段结束后应能承接的下一步

Step 1 完成后，项目应自然进入以下下一层计划：

- 世界状态核心落地
- 最小动作闭环落地
- AI 文本链路接入

也就是：

- Step 1 负责“能搭”
- Step 2 才开始负责“能跑”

## 9. 当前结论

Step 1 可以概括为：

**把这个项目从“设计已经定了”推进到“后端骨架已经稳定成立”的阶段，让后续所有功能都建立在清晰的应用结构、数据结构、引擎边界与 AI Runtime 边界之上。**
