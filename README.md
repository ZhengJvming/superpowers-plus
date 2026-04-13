# Superpowers-Plus

🚀 给 coding agent 装上结构化的大脑 —— 不只是工具，更是**纪律**。

**[English](README.en.md)** | 中文

Superpowers-Plus 是一套为 AI 编程助手设计的结构化工作流技能系统，基于可组合的"技能"（skills）自动触发。你的 agent 不只是写代码 —— 它会设计、分解、规划、测试、审查和记忆。

> **注意**：本项目是 [Superpowers](https://github.com/obra/superpowers) 的增强版本，增加了金字塔分解（Pyramid Decomposition）和记忆管理（Memory Management）系统，专门处理复杂、跨会话的大型工程任务。

## 快速开始

### 安装方式

Superpowers-Plus 支持多种 AI 编程助手平台。选择你的平台并按以下步骤安装：

***

#### Claude Code

**方式 1：Clone 安装（推荐）**

```bash
# 1. Clone 仓库
git clone https://github.com/jimmy/superpowers-plus.git ~/.claude/superpowers-plus

# 2. 在项目中创建插件引用
# 在项目根目录创建 .claude/plugins.json（如果不存在）
echo '{"plugins": ["~/.claude/superpowers-plus"]}' > .claude/plugins.json

# 3. 重启 Claude Code
```

**方式 2：本地开发模式**

```bash
# Clone 到本地
git clone https://github.com/jimmy/superpowers-plus.git ~/coding/superpowers-plus

# 在项目中使用绝对路径
echo '{"plugins": ["~/coding/superpowers-plus"]}' > .claude/plugins.json
```

**验证安装**：

```
告诉 Claude Code："列出你的技能"
```

应该能看到 `using-superpowers`、`brainstorming`、`pyramid-decomposition` 等技能。

***

#### Cursor

**方式 1：Clone 安装**

```bash
# 1. Clone 仓库
git clone https://github.com/jimmy/superpowers-plus.git ~/.cursor/superpowers-plus

# 2. 在项目根目录创建 .cursor/plugins.json
echo '{"plugins": ["~/.cursor/superpowers-plus"]}' > .cursor/plugins.json

# 3. 重启 Cursor
```

**方式 2：项目级安装**

```bash
# 直接 Clone 到项目目录
git clone https://github.com/jimmy/superpowers-plus.git .cursor/plugins/superpowers-plus

# Cursor 会自动发现 .cursor/plugins/ 目录下的插件
```

**验证安装**：

```
在 Cursor 中输入："你有哪些开发技能？"
```

***

#### OpenAI Codex

**安装步骤**：

```bash
# 1. Clone 仓库
git clone https://github.com/jimmy/superpowers-plus.git ~/.codex/superpowers-plus

# 2. 创建技能目录
mkdir -p ~/.agents/skills

# 3. 创建软链接（Unix/macOS）
ln -s ~/.codex/superpowers-plus/skills ~/.agents/skills/superpowers-plus

# Windows PowerShell（无需开发者模式）:
# cmd /c mklink /J "$env:USERPROFILE\.agents\skills\superpowers-plus" "$env:USERPROFILE\.codex\superpowers-plus\skills"

# 4. 重启 Codex
```

**验证安装**：

```bash
ls -la ~/.agents/skills/superpowers-plus
```

***

#### OpenCode

**安装步骤**：

在项目根目录的 `opencode.json` 中添加：

```json
{
  "plugin": ["superpowers-plus@git+https://github.com/jimmy/superpowers-plus.git"]
}
```

重启 OpenCode，插件会自动安装。

**验证安装**：

```
使用 skill 工具列出技能
```

***

#### 其他平台

对于其他支持技能/插件系统的 AI 编程助手，参考以下通用安装方式：

```bash
# 1. Clone 仓库
git clone https://github.com/jimmy/superpowers-plus.git <platform-dir>/superpowers-plus

# 2. 根据平台文档配置技能目录
# 通常需要指向 skills/ 目录
```

***

### 使用金字塔记忆系统（可选）

对于足够大的项目，建议初始化金字塔记忆系统：

```bash
# 在项目根目录执行
python3 <skill-path>/memory-management/scripts/run_memory_cli.py init \
  --project my-project --embedding skip
```

记忆存储在 `<project-root>/.superpowers/pyramid-memory/` —— 单个 SQLite 文件。记得将 `.superpowers/` 添加到 `.gitignore`。

***

## ✨ 核心功能

### 1. 📐 金字塔分解系统（Pyramid Decomposition）

处理大型、模糊、跨边界的复杂需求：

```
用户需求："构建一个电商平台"

AI 自动分解：
Level 0: 电商平台
    │
    ├── Level 1: 用户模块 | 商品模块 | 订单模块 | 支付模块
    │
    └── Level 2: (继续拆分)
        - 用户模块：注册、登录、权限、个人资料
        - 商品模块：列表、详情、搜索、库存
        - 订单模块：创建、查询、修改、取消
        - 支付模块：支付宝、微信、信用卡
```

每个叶子节点都是独立的业务功能单元，由单独的 Agent 负责实现。

### 2. 🧠 记忆管理系统（Memory Management）

基于 CozoDB 图数据库的持久化记忆：

- **节点管理**：存储分解树的每个节点
- **决策存储**：记录每个拆分决策的上下文和理由
- **接口契约**：管理叶子节点的输入/输出定义
- **文件引用**：追踪代码文件与节点的关联
- **语义召回**：基于向量相似度的历史决策检索

### 3. 🎯 自适应路由门控

根据任务特征自动选择最合适的工作流：

| 任务类型      | 路由                                                                | 示例                       |
| --------- | ----------------------------------------------------------------- | ------------------------ |
| **简单/本地** | `systematic-debugging` 或 `test-driven-development`                | "修复空指针"、"添加辅助函数"         |
| **有界多步骤** | `brainstorming` → `writing-plans` → `subagent-driven-development` | "添加 OAuth 登录"、"重构配置解析器"  |
| **大型/模糊** | `pyramid-decomposition` → 叶子节点交付 → `writing-plans`                | "构建支付系统"、" redesign 数据层" |
| **分析/审查** | `codebase-exploration`（独立模式）                                      | "审查架构"、"映射依赖关系"          |

***

## 📚 技能列表

### 路由层

- **using-superpowers** —— 入口路由器。分类任务，分发到正确的工作流。
- **writing-skills** —— 用于编写和测试新技能的元技能。

### 核心工作流层

- **brainstorming** —— 通过苏格拉底式对话将模糊想法转化为已验证的设计。
- **pyramid-decomposition** —— 大型需求的 BFS 分解，生成独立性合格的叶子节点。
- **codebase-exploration** —— 映射现有代码库：模块结构、依赖图、变更热点、架构模式。
- **memory-management** —— 持久化图 + 决策记忆。CozoDB 后端，Python CLI，JSON 协议。
- **writing-plans** —— 创建小尺寸实现计划。每步都有精确文件路径、完整代码、验证命令。
- **subagent-driven-development** —— 执行计划，每个任务分发一个子代理，两阶段审查。
- **executing-plans** —— 用于不支持子代理环境的替代执行方案。

### 纪律层

- **test-driven-development** —— 严格的 RED-GREEN-REFACTOR。没有失败测试就不写生产代码。
- **systematic-debugging** —— 四阶段根因调查。通过依赖图跨模块追踪。
- **verification-before-completion** —— 证据优先，始终如此。
- **requesting-code-review** / **receiving-code-review** —— 结构化审查分发和响应。
- **finishing-a-development-branch** —— 合并、PR、保留或丢弃 —— 带安全验证。
- **using-git-worktrees** —— 隔离的开发分支。
- **dispatching-parallel-agents** —— 并发调查独立问题。

***

## 🎯 设计哲学

### 核心问题

大多数 coding agent 以同样的方式失败：它们直接开始写代码。小任务能工作，但超过单个文件的任务就变成一团糟 —— 幻觉的接口、矛盾的决策、粗糙的分解导致模块边界模糊。

三个根本原因：

1. **上下文爆炸** —— 上下文窗口是有限的。对于任何非平凡的系统，完整的设计 + 代码 + 决策无法全部放入。子代理从头开始重新推导上下文。决策在会话之间蒸发。
2. **用户无法预先阐明完整设计** —— 需求开始时是模糊的（"给我构建一个支付系统"）。临时问答产生不一致的规格。Agent 用假设填补空白，这些假设几周后变成 bug。
3. **分解过早停止** —— 没有强制机制，agent 将工作拆分成仍然太粗的块。职责重叠。隐藏的耦合潜入。并行的子代理在共享状态上冲突，产生无法组合的代码。

### Superpowers 方法

**纪律优于智能。** 遵循严格流程的较弱 agent 胜过即兴发挥的天才 agent。

系统强制执行三个不变量：

- **没有设计就不写代码** —— 每个实现都从已批准的规格开始。Agent 问微问题，提出带权衡的替代方案，以可消化的部分呈现设计。你从不写规格 —— 你确认或拒绝一个。
- **没有独立性就不成为叶子节点** —— 每个工作单元必须通过五个标准（单一职责、接口清晰、独立可测试、Token 预算、封闭依赖）才能开始实现。任何标准失败都会强制进一步分解，直到耦合消失。
- **没有证据就不声称** —— "应该能工作"是不允许的。每个完成声明都需要新鲜的验证命令、完整的输出读取和确认的结果。Agent 不能在运行测试之前表达满意。

***

## 📖 方法论

工作流镜像资深工程师的实际思考方式：

```
模糊想法
  → 结构化设计（头脑风暴）
    → 金字塔分解（大型/跨边界工作）
      → 独立性合格的叶子节点
        → 小尺寸实现计划（每任务 2-5 分钟）
          → TDD 实现（RED → GREEN → REFACTOR）
            → 两阶段代码审查（规格合规 → 代码质量）
              → 已验证的完成
```

每个阶段都有**硬门控** —— 不满足退出标准就无法继续。Agent 无法用合理化绕过这些门控。如果测试失败，它不能声称成功。如果叶子节点太粗，它不能开始实现。如果设计未批准，它不能写代码。

### 五独立性标准

节点只有满足所有五个标准才能成为叶子节点：

| 标准           | 如何检查               | 防止什么              |
| ------------ | ------------------ | ----------------- |
| **单一职责**     | LLM 判断             | 做太多事情的神模块         |
| **接口清晰**     | 至少一个已发布接口          | 在变化下破裂的隐式契约       |
| **独立可测试**    | LLM 判断             | 无法隔离验证的单元         |
| **Token 预算** | 上下文包 < 8000 tokens | 子代理无法在上下文中容纳的叶子节点 |
| **封闭依赖**     | 所有依赖都是显式图边         | 导致集成失败的隐藏耦合       |

***

## 🧠 记忆架构

持久化记忆系统解决上下文爆炸：

```
┌─────────────────────────────────────────────────────┐
│                    Pyramid Memory                    │
│                                                      │
│  Nodes ─── hierarchy edges ─── dependency edges      │
│    │                                                 │
│    ├── Decisions (options, reasoning, trade-offs)     │
│    ├── Interfaces (contracts between leaves)          │
│    ├── File References (code pointers + staleness)    │
│    └── Scratchpad (session findings, hypotheses)      │
│                                                      │
│  Storage: CozoDB (graph + vector, single SQLite file) │
│  Access: Python CLI with JSON output                  │
│  Context: One leaf package at a time, never the       │
│           full pyramid                                │
└─────────────────────────────────────────────────────┘
```

当子代理需要叶子节点的上下文时，它获得 exactly 所需的内容 —— 节点、祖先链、相关决策、接口、依赖和文件引用 —— 在一个有界的包中。不是整个金字塔。不是整个代码库。只是最小充分上下文。

***

## 💡 技术亮点

### PEP 723 独立脚本

所有 CLI 脚本都是自包含的 Python 脚本，使用 PEP 723 依赖声明：

```python
# /// script
# dependencies = ["cozo-embedded", "numpy", "requests"]
# ///
```

**优势**：

- 无需全局安装，通过 `uv` 运行时自动管理依赖
- 工作区级别的 UV\_CACHE\_DIR 隔离
- 内置镜像回退（清华 -> 阿里云 -> PyPI）

### 协议化存储层

```python
# MemoryStore Protocol
class MemoryStore(Protocol):
    def create_node(self, node: Node) -> None: ...
    def add_edge(self, edge: Edge) -> None: ...
    def recall(self, query: str, k: int = 3) -> List[RecallResult]: ...

# 双实现
- InMemoryStore: 测试和轻量级使用
- CozoStore: 生产级持久化存储
```

***

## 更新

```bash
# 进入安装目录
cd ~/.claude/superpowers-plus  # 或其他安装路径

# 拉取最新代码
git pull
```

技能通过软链接即时更新。

***

## 卸载

```bash
# 1. 删除插件引用
rm .claude/plugins.json  # 或编辑移除 superpowers-plus

# 2. 删除安装的仓库
rm -rf ~/.claude/superpowers-plus

# 3. 清理项目记忆（可选）
rm -rf .superpowers/
```

***

## 贡献

参见 `CLAUDE.md` 了解贡献者指南。简短版本：这个仓库有 94% 的 PR 拒绝率。阅读指南。遵循 `writing-skills`。用压力场景测试。展示人类参与的证据。

**重要**：在为此仓库做出贡献之前，请阅读 `.github/PULL_REQUEST_TEMPLATE.md` 并填写每一部分。不要留空或使用占位符文本。

***

## 🙏 致谢

Superpowers-Plus 站在巨人的肩膀上：

- **原版 Superpowers**: <https://github.com/obra/superpowers> by [Jesse Vincent](https://blog.fsck.com)

***

## 社区

由 [Jesse Vincent](https://blog.fsck.com) 和 [Prime Radiant](https://primeradiant.com) 构建。金字塔记忆系统由社区贡献。

- **Discord**: [加入我们](https://discord.gg/35wsABTejz)
- **Issues**: <https://github.com/obra/superpowers/issues>
- **发布通知**: [注册](https://primeradiant.com/superpowers/)

***

## 许可证

MIT 许可证 —— 详见 LICENSE 文件。

***

## 赞助

如果 Superpowers 帮助你构建了赚钱的东西，考虑 [赞助 Jesse 的开源工作](https://github.com/sponsors/obra)。
