/**
 * Auth API service — login, register, refresh, me.
 */
import api from './axios.instance';
import type {
  LoginRequest,
  RegisterRequest,
  TokenRefreshResponse,
  AuthTokens,
} from '@/types/api.types';
import type { User, MeUpdateRequest } from '@/types/user.types';

export interface LoginResponse extends AuthTokens {
  user: User;
}

export const authApi = {
  login: (data: LoginRequest) =>
    api.post<LoginResponse>('/accounts/auth/login/', data).then((r) => r.data),

  register: (data: RegisterRequest) =>
    api.post<User>('/accounts/auth/register/', data).then((r) => r.data),

  refreshToken: (refresh: string) =>
    api
      .post<TokenRefreshResponse>('/accounts/auth/token/refresh/', { refresh })
      .then((r) => r.data),

  getMe: () => api.get<User>('/accounts/me/').then((r) => r.data),

  updateMe: (data: MeUpdateRequest) =>
    api.patch<User>('/accounts/me/', data).then((r) => r.data),
};
