# CHANGELOG_RULES.zh.md — Keep a Changelog 1.1.0 规范 中文版

目标：为人写 changelog，不为机器；让每个版本的显著变更可追溯、可链接。

原文：https://keepachangelog.com/en/1.1.0/

## 1. 文件与结构

```
# Changelog

本项目所有显著变更记录于此。

## [Unreleased]

## [1.0.0] - 2017-06-20

## [0.3.0] - 2015-12-03

[0.3.0]: https://github.com/user/repo/compare/v0.2.0...v0.3.0
```

- 文件固定为仓库根目录 `CHANGELOG.md`
- 顶部常驻 `## [Unreleased]` 段，累积未发布变更
- 发布节 `## [版本号] - YYYY-MM-DD`，日期用 ISO 8601；最新版本在最前
- 可选尾注链接节：`[版本]: <compare URL>`，让每个版本可链接到 diff

## 2. 六类分组

| 类型 | 语义 |
|---|---|
| Added | 新功能 |
| Changed | 对现有功能的变更 |
| Deprecated | 即将移除的功能 |
| Removed | 已移除的功能 |
| Fixed | 缺陷修复 |
| Security | 安全漏洞修补 |

- 同类变更归入同一子节（`### Added` 等），条目用 `-` 列表
- 废弃先公告：先入 Deprecated 预告，实际移除时再入 Removed

## 3. 版本与 SemVer

- 文件头部声明是否遵循 SemVer
- 遵循时：破坏性变更 → MAJOR；新功能 → MINOR；缺陷修复 → PATCH（与 `COMMIT_RULES` 的类型-版本对应一致）

## 4. yanked 版本

- 误发的版本不删除条目，标题后加 `[YANKED]` 并说明原因：

```
## [0.0.5] - 2014-12-13 [YANKED]
```

## 5. 原则与反模式

- changelog 为人而写；记显著变更，不做 git log 转储（需要完整历史时给 `git log` 或发布页链接）
- 每个已发布版本都应有条目
- 同类变更归组，使版本与章节结构稳定可解析
- 发布（打 tag）时把 Unreleased 内容转入新版本节并补当天日期

## 6. 示例

```
## [1.1.0] - 2026-10-11

### Added

- 支持嵌套 glob 模式

### Fixed

- 修复请求竞态导致的乱序响应
```

反例：把 `git log --oneline` 原样粘贴为版本条目 / 版本节无日期 / Unreleased 内容未随发版转移。

## 7. 打 tag 前自检

1. 本版本显著变更已从 Unreleased 转入 `## [X.Y.Z] - <当天 ISO 日期>`？
2. 条目已按六类归组？
3. 破坏性变更已标注（且版本号为 MAJOR）？
4. 版本号与文件头部的 SemVer 声明一致？
5. 没有把 git log 当 changelog？
