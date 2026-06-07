import * as React from 'react';
import { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { getProfile } from '../api/auth';
import type { UserProfile } from '../api/auth';

const TOKEN_KEY = 'token';
const REFRESH_TOKEN_KEY = 'refresh_token';

type AppContextType = {
  darkMode: boolean;
  setDarkMode: (v: boolean) => void;
  user: UserProfile | null;
  userName: string;
  token: string;
  setToken: (token: string, refreshToken?: string) => void;
  setUser: (user: UserProfile | null) => void;
  refreshUser: () => Promise<void>;
  logout: () => void;
  loadingUser: boolean;
};

// eslint-disable-next-line react-refresh/only-export-components
export const AppContext = createContext<AppContextType>({
  darkMode: false,
  setDarkMode: () => {},
  user: null,
  userName: 'Guest',
  token: '',
  setToken: () => {},
  setUser: () => {},
  refreshUser: async () => {},
  logout: () => {},
  loadingUser: false,
});

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [darkMode, setDarkMode] = useState<boolean>(() => {
    const saved = localStorage.getItem('darkMode');
    return saved === 'true';
  });
  const [token, setTokenState] = useState<string>(() => localStorage.getItem(TOKEN_KEY) || '');
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loadingUser, setLoadingUser] = useState(false);

  const setToken = useCallback((newToken: string, refreshToken?: string) => {
    setTokenState(newToken);
    if (newToken) {
      localStorage.setItem(TOKEN_KEY, newToken);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
    if (refreshToken !== undefined) {
      if (refreshToken) {
        localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
      } else {
        localStorage.removeItem(REFRESH_TOKEN_KEY);
      }
    }
  }, []);

  const logout = useCallback(() => {
    setToken('', '');
    setUser(null);
  }, [setToken]);

  const refreshUser = useCallback(async () => {
    if (!token) {
      setUser(null);
      return;
    }
    setLoadingUser(true);
    try {
      const res = await getProfile(token);
      setUser(res.data);
    } catch {
      setUser(null);
    } finally {
      setLoadingUser(false);
    }
  }, [token]);

  useEffect(() => {
    localStorage.setItem('darkMode', String(darkMode));
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);

  useEffect(() => {
    if (token) {
      refreshUser();
    }
  }, [token, refreshUser]);

  const userName = user?.name || 'Guest';

  return (
    <AppContext.Provider
      value={{
        darkMode,
        setDarkMode,
        user,
        userName,
        token,
        setToken,
        setUser,
        refreshUser,
        logout,
        loadingUser,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

// eslint-disable-next-line react-refresh/only-export-components
export const useAppContext = () => useContext(AppContext);
