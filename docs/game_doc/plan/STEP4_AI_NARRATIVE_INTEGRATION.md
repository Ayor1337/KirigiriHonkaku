# Step 4 AI 叙事接入阶段计划

> 本文档只覆盖项目落地的第四阶段：AI 叙事接入阶段。
> 它用于承接 [OVERVIEW.md](./OVERVIEW.md) 与 [STEP3_MAIN_LOOP.md](./STEP3_MAIN_LOOP.md)，进一步明确阶段四的目标、范围、产物与完成标准。
> 当前仍然不拆到逐步任务清单。
> 固定指令：Implementation Plan, Task List and Thought in Chinese

## 1. 阶段定位

Step 4 的目标不是让 AI 接管游戏规则，而是把 AI 稳定接到已经成立的主循环之后。

这一阶段只回答一个问题：

**怎样在不破坏硬规则边界的前提下，把已经能运转的调查主循环推进成一个“NPC 会说话、对话会沉淀、文本能留存、软状态可受限变化”的可运行叙事系统。**

## 2. 阶段目标

本阶段的核心目标包括：

- 把 AI Runtime 稳定接入 `Action -> Rule Resolution -> State Mutation` 之后的执行链
- 让 `talk` 等动作在硬规则结算完成后，能够生成 NPC 表达与文本结果
- 落地对话摘要生成与完整记录保存的双轨文本链路
- 落地 `MEMORY.md` 的受控更新机制
- 让 AI 在受限边界内调整少量软状态，而不越权修改硬状态

一句话：

**先让世界会说话，但仍然由规则决定世界怎么动。**

## 3. 阶段范围

Step 4 只覆盖 AI 叙事接入，当前范围如下：

### 3.1 应落地的部分

- AI Runtime 的调用入口与执行时机
- NPC 对话文本生成
- NPC 语气、回避、态度等表达层控制
- 对话摘要生成
- 完整对话记录保存
- `MEMORY.md` 更新链路
- 受限软状态写入机制
- AI 结果与 `ActionResult` / 文本存储结果的组装方式

### 3.2 当前不纳入的部分

- AI 决定时间推进
- AI 决定地图可达性、位置变化或线索存在
- 暴露度主值推进
- 真凶反制逻辑
- 正式指认与结局判定
- 复杂的多角色公开场合博弈
- 模型效果调优到内容生产级质量

## 4. 阶段依赖的设计基础

Step 4 依赖以下设计文档作为事实基础：

### 4.1 架构边界基础

- [AI_RUNTIME_SPEC.md](../architecture/AI_RUNTIME_SPEC.md)
- [ENGINE_SPEC.md](../architecture/ENGINE_SPEC.md)
- [ACTION_SPEC.md](../architecture/ACTION_SPEC.md)
- [STATE_BOUNDARY_SPEC.md](../architecture/STATE_BOUNDARY_SPEC.md)

### 4.2 数据与存储基础

- [DATA_STRUCTURE_SPEC.md](../architecture/DATA_STRUCTURE_SPEC.md)
- [DATABASE_SCHEMA_SPEC.md](../architecture/DATABASE_SCHEMA_SPEC.md)
- [STEP2_WORLD_STATE_CORE.md](./STEP2_WORLD_STATE_CORE.md)
- [STEP3_MAIN_LOOP.md](./STEP3_MAIN_LOOP.md)

### 4.3 玩法与文本基础

- [GAME_SPEC.md](../specs/GAME_SPEC.md)
- [DIALOGUE_SPEC.md](../specs/DIALOGUE_SPEC.md)
- [NPC_SPEC.md](../specs/NPC_SPEC.md)
- [STORAGE_SPEC.md](../specs/STORAGE_SPEC.md)

## 5. 阶段产物

Step 4 完成后，项目应至少形成以下稳定产物：

### 5.1 AI 后置执行链

- 引擎完成硬状态结算后，能够稳定调用 AI Runtime
- AI Runtime 能接收受控上下文，而不是直接接触全部原始状态
- AI 生成结果能够回传给主流程并进入统一保存链路

### 5.2 对话与文本落盘骨架

- NPC 对话文本可以稳定生成
- 对话摘要可以稳定生成并保存
- 完整对话记录可以稳定保存
- `MEMORY.md` 可以围绕既定角色或会话稳定更新

### 5.3 软状态受限更新骨架

- NPC 态度、警觉、情绪等软状态有明确可写边界
- AI 的写入结果可以被校验、审计和落盘
- AI 输出不会直接破坏世界硬状态一致性

## 6. 阶段完成标准

Step 4 是否完成，不看“文风是否已经极强”，而看下面这些叙事接入标准是否成立：

- AI Runtime 已经进入主循环后置链路，而不是孤立试验模块
- `talk` 至少具备一条“规则结算后生成文本并落盘”的完整路径
- 对话摘要与完整记录已经形成双轨保存，而不是只保留单份文本
- `MEMORY.md` 更新已经进入系统流程，而不是依赖人工补写
- AI 可调整的软状态边界已经固定，不再和硬状态混杂
- 即使 AI 输出不够精彩，系统仍能稳定完成动作结果返回和文本保存
- 后续阶段可以在不推翻 AI 边界的前提下接入暴露度、公开场合与结局系统

## 7. 阶段内的重点取舍

本阶段必须坚持以下取舍：

- 优先固定 AI 接入边界，不优先追求单次生成质量上限
- 优先保证文本链路稳定，不优先扩展大量提示词花样
- 优先保证 AI 结果可审计，不优先开放大范围状态写权限
- 优先让规则层继续主导世界，不让 AI 越权接管结算

这意味着：

- 允许阶段四结束时“文本表现还不够华丽”
- 但不允许阶段四结束时“AI 已经能随意改世界硬状态”

## 8. 阶段结束后应能承接的下一步

Step 4 完成后，项目应自然进入以下下一层计划：

- 暴露度推进
- 真凶反制触发
- 正式指认与结局判定

也就是：

- Step 4 负责“世界会说话”
- Step 5 才开始负责“世界能结案”

## 9. 当前结论

Step 4 可以概括为：

**把这个项目从“玩家已经可以推动世界前进”推进到“系统已经可以在既定规则边界内生成 NPC 表达、沉淀对话摘要与记忆文本”的阶段，让 AI Runtime 成为主循环之后的稳定叙事层，而不是越权接管世界规则的核心。**
