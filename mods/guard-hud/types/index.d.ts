export type Outcome = 'runs' | 'done' | 'deny' | 'err'
export type GuardCall = { id: string; tool: string; brief: string; outcome: Outcome }
export type TurnStats = { tools: number; denied: number; errors: number }

declare module 'claude-code' {
  interface PluginState {
    'guard-hud': { calls: GuardCall[]; last: TurnStats | null; isHidden: boolean }
  }
}
