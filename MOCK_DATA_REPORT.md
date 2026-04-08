# 项目 Mock / 硬编码数据清查报告

> 生成时间：2026-04-07
> 范围：`src/` 目录下的源代码与已废弃的 mock 文件

---

## 一、已删除的 Mock 文件（历史遗留）

以下文件曾在项目早期存在，现已被删除，仅 `CLAUDE.md` 中有记录：

| 历史文件 | 原用途 |
|---------|--------|
| `src/data/mock.ts` | 旧版 `mockGameState` 兼容数据 |
| `src/data/mapMock.ts` | 地图视图专用的 `mockMapData` |

**现状**：`src/data/` 目录已为空，`Glob` 与 `Grep` 均无法搜到任何 mock 数据引用。

---

## 二、当前仍存在的硬编码 / Mock-like 数据

### 1. 天气——永远下雨（TopBar）
**文件**：`src/components/layout/TopBar.tsx:38`
```tsx
<TimeDisplay date={date} timePeriod={timePeriod} weather="雨" />
```
- `weather="雨"` 是**写死**的，不会随场景或后端数据变化。

### 2. 游戏基期日期固定（TopBar）
**文件**：`src/components/layout/TopBar.tsx:14`
```tsx
const baseDate = new Date("1924-10-15T00:00:00");
```
- 所有游戏时间都以 `1924-10-15` 为基准进行推算，并非来自后端配置。

### 3. 玩家档案完全写死（PlayerProfileView）
**文件**：`src/components/views/PlayerProfileView.tsx`

以下信息均为硬编码的静态文本，未与 `useGameSession` 或后端 API 关联：

- **玩家名字**：`雾切响子`（第 119 行）
- **称号**：`超高校级的侦探`（第 122 行）
- **特性标签**：`["敏锐观察", "逻辑推理", "冷静沉着"]`（第 127 行）
- **背景故事**：
  > "曾在苏格兰场工作的传奇侦探，以敏锐的观察力和超凡的逻辑推理能力闻名。被称为'希望的侦探'，解决过多起悬案。本次受邀调查雾切洋馆的神秘事件。"
- **特殊能力**：
  - `超高校级观察力` — "能够发现常人忽略的细微线索"
  - `逻辑推理` — "快速串联线索，还原事件真相"

### 4. 地图标题固定（MapView）
**文件**：`src/components/views/MapView.tsx:159`
```tsx
<h1 className="font-serif text-2xl text-(--text-primary) mt-1">雾切洋馆</h1>
```
- 地图名称 "雾切洋馆" 是硬编码的，不随 `session` 或 `scene` 变化。

### 5. 空状态 Fallback 文案

| 文件 | 位置 | 硬编码内容 | 触发条件 |
|------|------|-----------|---------|
| `InvestigationView.tsx` | 第 40 行 | `"你环顾四周，感受着这个地方的氛围..."` | `currentLocation.description` 为空 |
| `DialogueView.tsx` | 第 33 行 | `"${npcName}看着你，等待你的提问。"` | `narrativeText` 为空且 `latestDialogue` 无内容 |
| `CaseColumn.tsx` | 第 48 行 | `"此处无人..."` | `visibleNpcs.length === 0` |
| `CaseColumn.tsx` | 第 86 行 | `"尚未发现任何线索..."` | `discoveredClues.length === 0` |

### 6. 暴露度等级写死（PlayerProfileView）
**文件**：`src/components/views/PlayerProfileView.tsx:20-28`
```tsx
const getExposureStyle = (value: number) => {
  if (value <= 20) return { label: "安全", color: "#10b981", desc: "你的行踪未被注意" };
  if (value <= 40) return { label: "警惕", color: "#f59e0b", desc: "有人开始注意你的举动" };
  if (value <= 60) return { label: "危险", color: "#ef4444", desc: "你已引起怀疑" };
  return { label: "暴露", color: "#dc2626", desc: "你的身份面临暴露风险" };
};
```
- 暴露度的区间、文案、颜色全部写死在前端，未使用后端返回的配置。

### 7. SSE 阶段文案映射（HomeView）
**文件**：`src/components/views/HomeView.tsx:12-21`
```tsx
const STAGE_LABELS: Record<SessionBootstrapStageKey, string> = {
  session_creating: "正在建立调查卷宗...",
  session_created: "卷宗已建立，准备生成案件...",
  world_planning: "正在规划案件结构...",
  world_generating: "正在生成世界内容...",
  world_validating: "正在校验案件结构...",
  world_fixing: "正在修正生成结果...",
  world_persisting: "正在写入调查现场...",
  world_ready: "案件已就绪，正在进入现场...",
};
```
- 虽然阶段占位符来自后端，但显示文案完全由前端硬编码映射。

---

## 三、补充说明：非 Mock 但需要关注的显示问题

### FeedbackView 直接显示 location key
**文件**：`src/components/views/FeedbackView.tsx:159-166`
```tsx
{movement?.to_location_key && (
  <div ...>
    <span className="text-(--text-primary)">{movement.to_location_key}</span>
  </div>
)}
```
- 移动反馈直接显示 location key（如 `study`），而非 human-readable 的地点名称。这不是 mock 数据，但会影响体验。

---

## 四、结论

| 类别 | 数量 | 说明 |
|------|------|------|
| 已删除的 mock 文件 | 2 个 | `mock.ts`、`mapMock.ts` |
| 硬编码的静态内容 | 7 处 | 天气、日期、玩家档案、地图标题、暴露度等级、SSE 文案 |
| 空状态 fallback 文案 | 4 处 | 属于合理 UX 设计，但可替换为后端配置 |
| 显示问题 | 1 处 | FeedbackView 的 `to_location_key` 未转名称 |

如果后续需要消除这些硬编码，建议优先从以下接口获取数据：
- **玩家档案**：从 `GET /api/v1/sessions/{session_id}` 的 `root_ids.player_id` 关联的玩家详情接口获取
- **天气 / 地图标题**：扩展 `SceneSnapshot` 或 `SceneLocation` 结构
- **暴露度文案**：扩展 `ExposureInfo` 类型，由后端返回 `label`、`desc`、`color`
