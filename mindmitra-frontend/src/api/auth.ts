import axios from 'axios';

export interface LoginResponse {
  access_token: string;
  token_type: string;
  refresh_token: string;
  expires_in: number;
}

export interface EmergencyContact {
  name: string;
  phone: string;
  email?: string;
  relationship: string;
}

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  role: string;
  is_active: boolean;
  emergency_contacts: EmergencyContact[];
  profile_picture_url?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProfileUpdatePayload {
  name?: string;
  emergency_contacts?: EmergencyContact[];
}

const authHeader = (token: string) => ({ Authorization: `Bearer ${token}` });

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

export const registerUser = (data: {
  email: string;
  name: string;
  password: string;
  role?: string;
}) => axios.post<UserProfile>('/api/v1/auth/register', { ...data, role: data.role ?? 'user' });

export const getProfile = (token: string) =>
  axios.get<UserProfile>('/api/v1/auth/profile', { headers: authHeader(token) });

export const updateProfile = (payload: ProfileUpdatePayload, token: string) =>
  axios.put<UserProfile>('/api/v1/auth/profile', payload, { headers: authHeader(token) });

export const uploadProfilePicture = (file: File, token: string) => {
  const formData = new FormData();
  formData.append('file', file);
  return axios.post<UserProfile>('/api/v1/auth/profile/picture', formData, {
    headers: {
      ...authHeader(token),
      'Content-Type': 'multipart/form-data',
    },
  });
};

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
