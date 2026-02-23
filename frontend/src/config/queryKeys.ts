/**
 * Centralised React Query key factory.
 *
 * Every query key is built from here so invalidation, prefetching and
 * deduplication work reliably across the app.
 *
 * Pattern:  [scope, ...rest]
 * Example:  queryKeys.cases.detail(42)  → ['cases', 'detail', 42]
 */

export const queryKeys = {
  /* ── Auth / Me ─────────────────────────────────────────────────── */
  me: ['me'] as const,

  /* ── Users ─────────────────────────────────────────────────────── */
  users: {
    all: ['users'] as const,
    list: (params?: unknown) => ['users', 'list', params] as const,
    detail: (id: number) => ['users', 'detail', id] as const,
  },

  /* ── Roles ─────────────────────────────────────────────────────── */
  roles: {
    all: ['roles'] as const,
    list: () => ['roles', 'list'] as const,
    detail: (id: number) => ['roles', 'detail', id] as const,
  },

  /* ── Permissions ───────────────────────────────────────────────── */
  permissions: ['permissions'] as const,

  /* ── Cases ─────────────────────────────────────────────────────── */
  cases: {
    all: ['cases'] as const,
    list: (params?: unknown) => ['cases', 'list', params] as const,
    detail: (id: number) => ['cases', 'detail', id] as const,
    statusLog: (id: number) => ['cases', 'statusLog', id] as const,
    report: (id: number) => ['cases', 'report', id] as const,
    calculations: (id: number) => ['cases', 'calculations', id] as const,
    complainants: (id: number) => ['cases', 'complainants', id] as const,
    witnesses: (id: number) => ['cases', 'witnesses', id] as const,
  },

  /* ── Evidence ──────────────────────────────────────────────────── */
  evidence: {
    all: ['evidence'] as const,
    list: (params?: unknown) => ['evidence', 'list', params] as const,
    detail: (id: number) => ['evidence', 'detail', id] as const,
    files: (id: number) => ['evidence', 'files', id] as const,
    custody: (id: number) => ['evidence', 'custody', id] as const,
  },

  /* ── Suspects ──────────────────────────────────────────────────── */
  suspects: {
    all: ['suspects'] as const,
    list: (params?: unknown) => ['suspects', 'list', params] as const,
    detail: (id: number) => ['suspects', 'detail', id] as const,
    mostWanted: ['suspects', 'most-wanted'] as const,
  },

  /* ── Interrogations ────────────────────────────────────────────── */
  interrogations: {
    list: (suspectId: number) =>
      ['interrogations', 'list', suspectId] as const,
    detail: (suspectId: number, id: number) =>
      ['interrogations', 'detail', suspectId, id] as const,
  },

  /* ── Trials ────────────────────────────────────────────────────── */
  trials: {
    list: (suspectId: number) => ['trials', 'list', suspectId] as const,
    detail: (suspectId: number, id: number) =>
      ['trials', 'detail', suspectId, id] as const,
  },

  /* ── Bails ─────────────────────────────────────────────────────── */
  bails: {
    list: (suspectId: number) => ['bails', 'list', suspectId] as const,
    detail: (suspectId: number, id: number) =>
      ['bails', 'detail', suspectId, id] as const,
  },

  /* ── Bounty Tips ───────────────────────────────────────────────── */
  bountyTips: {
    all: ['bountyTips'] as const,
    list: (params?: unknown) => ['bountyTips', 'list', params] as const,
    detail: (id: number) => ['bountyTips', 'detail', id] as const,
  },

  /* ── Detective Board ───────────────────────────────────────────── */
  boards: {
    all: ['boards'] as const,
    list: (params?: unknown) => ['boards', 'list', params] as const,
    detail: (id: number) => ['boards', 'detail', id] as const,
    full: (id: number) => ['boards', 'full', id] as const,
  },

  /* ── Core ──────────────────────────────────────────────────────── */
  dashboard: ['dashboard'] as const,
  notifications: (params?: unknown) => ['notifications', params] as const,
  search: (q: string) => ['search', q] as const,
  constants: ['constants'] as const,
} as const;
