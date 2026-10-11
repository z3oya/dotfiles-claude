# zai-quota

A Claude Code mod that pins GLM Coding Plan quota into the status line: the
plan name plus the 5-hour, weekly and MCP windows, refreshed every 3 minutes.

- **Status line** — `GLM coding-plan Pro | 5h 17% | wk 42% | MCP 30/1000`
- **3-minute refresh** — one request per tick, timed out at 15 s, guarded
  against overlap
- **Sticky display** — the last good reading stays up while the API is
  unreachable; errors show only until the first good reading lands

## Install

Claude Code **v2.1.287+**, in a terminal or the Desktop app's Code tab.

```
/plugin install zai-quota --marketplace z3oya/zai-quota
```

Answer `y` to add the marketplace, then pick a scope. The status entry appears
once the first good reading lands.

## Notes

- Needs a **personal** API key in the environment (`ANTHROPIC_AUTH_TOKEN`,
  `ZAI_API_KEY`, `BIGMODEL_API_KEY` or `ZHIPU_API_KEY`); team keys without
  org headers get empty data.
- Host follows `ANTHROPIC_BASE_URL`: a URL containing `z.ai` queries
  `api.z.ai`, anything else `open.bigmodel.cn`. Raw-key auth first, retried
  with `Bearer` on 401.
- Status text is sanitized to single-width characters; CJK plan names show
  as `?` there.
- `disableAllHooks`, `--safe-mode` and `--bare` also stop this mod.

## Development

```
git clone https://github.com/z3oya/zai-quota
claude --plugin-dir zai-quota
```

Tests run against the engine itself: `claude plugin test zai-quota`.
