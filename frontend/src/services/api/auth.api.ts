/**
 * Auth API service — login, register, refresh, me.
 *
 * Raw backend responses are normalised so the rest of the app always
 * receives `role` as a `RoleListItem | null` object (not a bare integer FK).
 */
import api from './axios.instance';
import type {
  LoginRequest,
  RegisterRequest,
  TokenRefreshResponse,
  AuthTokens,
} from '@/types/api.types';
import type { User, MeUpdateRequest, RawUserDetail } from '@/types/user.types';
import { normalizeUser } from '@/types/user.types';

export interface LoginResponse extends AuthTokens {
  user: User;
}

/** Raw shape from the backend before normalisation. */
interface RawLoginResponse extends AuthTokens {
  user: RawUserDetail;
}

export const authApi = {
  login: (data: LoginRequest) =>
    api
      .post<RawLoginResponse>('/accounts/auth/login/', data)
      .then((r) => ({
        ...r.data,
        user: normalizeUser(r.data.user),
      })),

  register: (data: RegisterRequest) =>
    api.post('/accounts/auth/register/', data).then((r) => r.data),

  refreshToken: (refresh: string) =>
    api
      .post<TokenRefreshResponse>('/accounts/auth/token/refresh/', { refresh })
      .then((r) => r.data),

  getMe: () =>
    api
      .get<RawUserDetail>('/accounts/me/')
      .then((r) => normalizeUser(r.data)),

  updateMe: (data: MeUpdateRequest) =>
    api
      .patch<RawUserDetail>('/accounts/me/', data)
      .then((r) => normalizeUser(r.data)),
};
