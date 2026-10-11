import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import type { GuardCall, Outcome, TurnStats } from '../types'

const PANE = 'guard-hud'
const calls = atom({ plugin: 'guard-hud', key: 'calls' } as const, [] as GuardCall[])
const last = atom({ plugin: 'guard-hud', key: 'last' } as const, null as TurnStats | null)
const isHidden = atom({ plugin: 'guard-hud', key: 'isHidden' } as const, false)

// Pane/status text lands on the terminal grid: one cell per character.
const ascii = (s: string) => s.replace(/[^\x20-\x7E]/g, '?')
const clip = (s: string, n: number) => ascii(s).slice(0, n)

export const register: Register = on => {
  let seq = 0
  let tools = 0
  let denied = 0
  let errors = 0
  let deniedThisTurn = false
  let statusShown = false

  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'guard-hud',
      description: 'Open the guard activity pane (also un-hides the band)',
    })
    return next(e)
  })

  on('command.run', { command: 'guard-hud' }, async $ => {
    await update($, isHidden, () => false)
    await $.ui.open({ id: PANE, title: 'Guard HUD' })

    return { text: 'Guard HUD pane opened.' }
  })

  on('prompt.submit', async ($, e, next) => {
    tools = 0
    denied = 0
    errors = 0
    deniedThisTurn = false
    statusShown = false
    await update($, last, () => ({ tools, denied, errors }))

    return next(e)
  })

  on('tool.call', async ($, e, next) => {
    const id = e.tool_use_id ?? `${e.tool}#${seq++}`
    const raw = 'command' in e ? String(e.command) : 'file_path' in e ? String(e.file_path) : ''
    const brief = clip(raw, 48)
    tools += 1

    await update($, calls, list =>
      [...list, { id, tool: e.tool, brief, outcome: 'runs' as Outcome }].slice(-200),
    )

    const ran = await next(e)

    const outcome: Outcome = ran.deny !== undefined ? 'deny' : ran.isError === true ? 'err' : 'done'
    if (outcome === 'deny') denied += 1
    if (outcome === 'err') errors += 1
    await update($, last, () => ({ tools, denied, errors }))
    await update($, calls, list =>
      list.map(one => (one.id === id ? { ...one, outcome } : one)),
    )

    if (outcome === 'done') {
      if (statusShown) {
        statusShown = false
        $.ui.status(undefined)
      }
    } else {
      statusShown = true
      $.ui.status(`blocked: ${e.tool} ${brief}`.slice(0, 64))
      if (outcome === 'deny' && !deniedThisTurn) {
        deniedThisTurn = true
        $.ui.toast('guard denied: ' + e.tool)
      }
    }

    return ran
  }).catch(($, e, next) => next(e))

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const turn = await read($, last)
    const isQuiet = (await read($, isHidden)) || turn === null || turn.tools === 0

    if (isQuiet) {
      return next(e)
    }

    const { Box, Button, Text } = $.ui.resolve(e)

    return (
      <Box>
        <Text dimColor>
          this turn: {turn.tools} calls · {turn.denied} denied · {turn.errors} err{' '}
        </Text>
        <Button
          key="hide"
          label="Hide"
          onPress={() => update($, isHidden, () => true)}
        />
      </Box>
    )
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    const list = await read($, calls)
    const room = Math.max(1, (e.viewport?.rows ?? 24) - 4)

    return (
      <Box flexDirection="column">
        {list.length === 0 && <Text dimColor>No tool calls yet.</Text>}
        {list.slice(-room).map(call => (
          <Text dimColor={call.outcome === 'done'}>
            {call.outcome.padEnd(5)} {call.tool} {call.brief}
          </Text>
        ))}
      </Box>
    )
  })
}
