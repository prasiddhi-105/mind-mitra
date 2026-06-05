import React, { createContext, useState, useContext, useEffect } from 'react';

type AppContextType = {
  darkMode: boolean;
  setDarkMode: (v: boolean) => void;
  userName: string;
};

export const AppContext = createContext<AppContextType>({
  darkMode: false,
  setDarkMode: () => {},
  userName: 'Alex',
});

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [darkMode, setDarkMode] = useState<boolean>(() => {
    const saved = localStorage.getItem('darkMode');
    return saved === 'true';
  });
  const [userName] = useState('Alex');

  useEffect(() => {
    localStorage.setItem('darkMode', String(darkMode));
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);

  return (
    <AppContext.Provider value={{ darkMode, setDarkMode, userName }}>
      {children}
    </AppContext.Provider>
  );
};

export const useAppContext = () => useContext(AppContext); 