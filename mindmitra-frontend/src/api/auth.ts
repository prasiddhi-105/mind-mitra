import axios from 'axios';

export interface LoginResponse {
  access_token: string;
  token_type: string;
  refresh_token: string;
  expires_in: number;
}

export interface MessageResponse {
  message: string;
}

export interface TokenValidationResponse {
  valid: boolean;
}

/**
 * Authenticate against the existing FastAPI backend.
 * Uses OAuth2PasswordRequestForm (application/x-www-form-urlencoded).
 * The backend field is named `username` per the OAuth2 spec — we pass the email there.
 */
export const loginUser = (email: string, password: string) =>
  axios.post<LoginResponse>(
    '/api/v1/auth/login',
    new URLSearchParams({ username: email, password }),
    { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
  );

export const requestPasswordReset = (email: string) =>
  axios.post<MessageResponse>('/api/v1/auth/forgot-password', { email });

export const validateResetToken = (token: string) =>
  axios.get<TokenValidationResponse>('/api/v1/auth/reset-password/validate', {
    params: { token },
  });

export const resetPassword = (token: string, new_password: string) =>
  axios.post<MessageResponse>('/api/v1/auth/reset-password', {
    token,
    new_password,
  });
