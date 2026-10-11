# CHANGELOG_RULES.en.md — Keep a Changelog 1.1.0 Spec (English)

Goal: write changelogs for humans, not machines; make each version's
notable changes traceable and linkable.

Source: https://keepachangelog.com/en/1.1.0/

## 1. File & Structure

```
# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [1.0.0] - 2017-06-20

## [0.3.0] - 2015-12-03

[0.3.0]: https://github.com/user/repo/compare/v0.2.0...v0.3.0
```

- The file is `CHANGELOG.md` at the repository root
- Keep a standing `## [Unreleased]` section on top to accumulate changes
- Cut each release as `## [Version] - YYYY-MM-DD` (ISO 8601 date); newest first
- Optional footer link section: `[Version]: <compare URL>` so versions link to diffs

## 2. Change Categories

| Type | Meaning |
|---|---|
| Added | New features |
| Changed | Changes to existing functionality |
| Deprecated | Soon-to-be removed features |
| Removed | Removed features |
| Fixed | Bug fixes |
| Security | Vulnerability fixes |

- Group entries under `### Added` etc.; use `-` lists
- Announce deprecations first (Deprecated), then record actual removals (Removed)

## 3. Versions & SemVer

- State in the file header whether SemVer is followed
- If so: breaking → MAJOR, features → MINOR, fixes → PATCH (matches the
  type-to-version mapping in `COMMIT_RULES`)

## 4. Yanked Releases

- Never delete a bad release's entry; mark it and explain:

```
## [0.0.5] - 2014-12-13 [YANKED]
```

## 5. Principles & Anti-patterns

- Changelogs are for humans; record notable changes, never dump git log
  (link `git log` or the release page for full history)
- Every released version gets an entry
- Group same-type changes so versions and sections stay parseable
- At release (tagging) time, convert Unreleased into the new version
  section with today's date

## 6. Example

```
## [1.1.0] - 2026-10-11

### Added

- Support nested glob patterns

### Fixed

- Prevent racing of requests causing out-of-order responses
```

Anti-patterns: pasting `git log --oneline` as version entries / version
sections without dates / Unreleased content left behind at release time.

## 7. Pre-tag Checklist

1. Moved this release's notable changes from Unreleased into
   `## [X.Y.Z] - <today's ISO date>`?
2. Entries grouped under the six categories?
3. Breaking changes flagged (and version bumped to MAJOR)?
4. Version consistent with the declared SemVer policy?
5. No raw git log dumped into the changelog?
