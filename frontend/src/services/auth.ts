import { apiClient } from "@/services/api-client";
import type { User } from "@/types/user";

export interface SignupPayload {
  name: string;
  email: string;
  password: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export const authService = {
  signup: (payload: SignupPayload) => apiClient.post<User>("/api/auth/signup", payload),
  login: (payload: LoginPayload) => apiClient.post<User>("/api/auth/login", payload),
  logout: () => apiClient.post<void>("/api/auth/logout"),
  me: () => apiClient.get<User>("/api/auth/me"),
};
