/**
 * Barrel export for all API services.
 */
export { default as api } from './axios.instance';
export { authApi } from './auth.api';
export type { LoginResponse } from './auth.api';
export { rolesApi, usersApi, permissionsApi } from './admin.api';
export { casesApi } from './cases.api';
export { evidenceApi } from './evidence.api';
export {
  suspectsApi,
  interrogationsApi,
  trialsApi,
  bailsApi,
  bountyTipsApi,
} from './suspects.api';
export { boardApi } from './board.api';
export { coreApi } from './core.api';
