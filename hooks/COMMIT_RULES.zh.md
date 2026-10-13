# COMMIT_RULES.zh.md — Git 提交信息规范 中文版

目标：可读的历史、机器可解析的类型、稳定的语义化版本信号。

## 1. 结构

```
<type>[(<scope>)][!]: <subject>

<body>

<footer(s)>
```

- subject 必需；
- scope、body、footer 可选；
- 段间必须空行（`git log` / `shortlog` / `rebase` 的解析边界）

## 2. Subject

- ≤50 显示列，72 为硬上限；长度含 `type(scope): ` 前缀；ASCII 记 1 列、汉字记 2 列（≈25 个汉字）
- 祈使语气：英文须通过 "If applied, this commit will ___"，中文须通过 "本次提交将 ___"
- 中英皆可，同一仓库保持一致
- 行尾不加句号等标点；`!` 仅作破坏性变更标记（置于 `:` 之前）
- 描述首词小写
- 禁止零信息描述（`fix bug`、`update files`、`more fixes`）

## 3. Body

- 72 列手动换行（git 不自动换行）
- 写 what 与 why，不写 how（how 在 diff 里）
- 顺序建议：问题背景 → 变更内容 → 选择理由 / 副作用
- body 使用 `-` 列项书写；一句话能说清则省略 body

## 4. Footer

- git trailer 格式 `token: value`；token 内空格写连字符（`Acked-by:`），`BREAKING CHANGE` 为唯一例外（`BREAKING-CHANGE` 与之同义）
- issue 引用：`Refs: #123`、`Resolves: #45`
- 破坏性变更：`BREAKING CHANGE: <破坏点与迁移方式>`；若已用 `!` 标记则 footer 可省略，但描述必须说明破坏点

## 5. 类型

| type | 语义 | semver |
|---|---|---|
| feat | 新功能 | MINOR |
| fix | 缺陷修复 | PATCH |
| docs | 文档 | 无 |
| style | 格式（不影响语义） | 无 |
| refactor | 重构 | 无 |
| perf | 性能优化 | 无 |
| test | 测试 | 无 |
| build | 构建 / 依赖 | 无 |
| ci | CI 配置 | 无 |
| chore | 杂务 | 无 |
| revert | 回退提交 | 随内容 |

- 破坏性变更（任意类型）：`:` 前加 `!`（scope 之后，如 `feat(parser)!:`），或 `BREAKING CHANGE` footer，或两者并用；结果 → MAJOR
- scope：括号内小写名词，指模块 / 分区；类型与 scope 一律小写

## 6. 特殊情形

- revert：subject 为 `revert: <原 subject>`，footer 用 `Refs: <原 SHA>`。git 自动生成的默认消息（`Revert "…"` + body 行 `This reverts commit <sha>.`）与此不同，需手工重写
- merge 消息由 git 自动生成

## 7. 示例

```
feat(parser): support nested glob patterns
```

```
fix: prevent racing of requests

- Introduce a request id and an index table to track outstanding
  requests
- Old behavior: responses could arrive out of order and overwrite
  newer data

BREAKING CHANGE: environment variable `REQUEST_MODE` removed.
Use `concurrency.mode` in config instead.
Refs: #345
```

反例：`fixed parser bug`（过去式）/ `update files`（零信息）/ `feat: add feature!`（`!` 仅作破坏性标记，非行尾标点）

## 8. 提交前自检

1. subject ≤50 显示列（≈25 汉字，72 硬上限）、祈使语气、无句号？
2. 段间空行齐全？
3. body 只讲 what 与 why，且使用 `-` 列项？
4. 类型、scope、`!` 破坏性标记正确？
5. issue / SHA 引用放在 footer？
