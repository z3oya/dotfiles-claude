# guard-hud

A Claude Code mod that makes your guard layer visible: a band above the prompt
and a `/guard-hud` pane surfacing every tool call of the turn and how it ended —
done, errored (including blocks by your settings hooks and other mods), or
denied by a mod in the same tier.

- **Band** — `this turn: N calls · M denied · K err` with a Hide button
- **Pane** — `/guard-hud` lists recent calls (`outcome tool brief`), done dimmed
- **Status line** — `blocked: <tool> <brief>` while the last call was blocked
- **Toast** — once per turn on the first mod-tier denial

It only observes: guard-hud never denies or rewrites a tool call itself.

## Install

Claude Code **v2.1.287+**, in a terminal or the Desktop app's Code tab.

```
/plugin install guard-hud --marketplace z3oya/guard-hud
```

Answer `y` to add the marketplace, then pick a scope. The hooks run from then
on; the band appears once the turn has tool calls, and `/guard-hud` opens the
pane.

## Notes

- Pane and status text is sanitized to single-width characters (the terminal
  grid requirement); CJK in commands shows as `?` there.
- Blocks by **settings hooks** land in the `err` column (they surface from
  `next(e)` as `isError`); the `deny` column is reserved for same-tier mod
  denials.
- `disableAllHooks`, `--safe-mode` and `--bare` also stop this mod.

## Development

```
git clone https://github.com/z3oya/guard-hud
claude --plugin-dir guard-hud
```

Tests run against the engine itself: `claude plugin test guard-hud`.

## License

MIT
