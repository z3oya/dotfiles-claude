import type { On } from 'claude-code'
import { expect, test } from 'claude-code/testing'

import type { GuardCall } from '../types'

// The test body's own `$` has no $.state noun to read atoms with; the kit's
// bottom answers only beneath the plugins. Observe the plugin's writes the
// event way instead: test hooks sit beneath every plugin, so the plugin's
// `update($, calls, ...)` surfaces here as `state.set` events.
function collectCalls(on: On) {
  const writes: GuardCall[][] = []
  on('state.set', { plugin: 'guard-hud', key: 'calls' }, ($, e, next) => {
    writes.push(e.value)
    return next(e)
  })
  return writes
}

test('a denied answer classifies as deny', async ($, on) => {
  const writes = collectCalls(on)
  on('tool.call', () => ({ deny: 'test deny' }))
  await $.tool.call({ tool: 'Bash', command: 'echo x' })

  expect(writes.at(-1)?.at(-1)?.outcome).toBe('deny')
})

test('an errored answer classifies as err', async ($, on) => {
  const writes = collectCalls(on)
  on('tool.call', () => ({ isError: true, result: null, text: 'boom' }))
  await $.tool.call({ tool: 'Bash', command: 'echo y' })

  expect(writes.at(-1)?.at(-1)?.outcome).toBe('err')
})

test('an answered call classifies as done', async ($, on) => {
  const writes = collectCalls(on)
  on('tool.call', () => ({ result: { stdout: 'ok', stderr: '', interrupted: false } }))
  await $.tool.call({ tool: 'Bash', command: 'echo z' })

  expect(writes.at(-1)?.at(-1)?.outcome).toBe('done')
})
