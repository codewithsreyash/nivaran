import React, { createContext, useContext, useState, useEffect } from 'react';
import { type ReactNode } from 'react';
import { authAPI } from '../lib/api';

export interface User {
  id: number;
  username: string;
  email: string;
  full_name: string;
  role: 'admin' | 'bureau_officer' | 'supervisory_reviewer' | 'read_only';
  bureau_id: number | null;
  is_active: boolean;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  isAdmin: boolean;
  isOfficer: boolean;
  isReviewer: boolean;
  canWrite: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem('user');
    if (stored && token) {
      setUser(JSON.parse(stored));
    }
    setLoading(false);
  }, [token]);

  const login = async (username: string, password: string) => {
    const res = await authAPI.login(username, password);
    const { access_token, user: userData } = res.data;
    localStorage.setItem('token', access_token);
    localStorage.setItem('user', JSON.stringify(userData));
    setToken(access_token);
    setUser(userData);
  };

  const logout = () => {
    authAPI.logout().catch(() => {});
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setToken(null);
    setUser(null);
  };

  const isAdmin = user?.role === 'admin';
  const isOfficer = user?.role === 'bureau_officer';
  const isReviewer = user?.role === 'supervisory_reviewer';
  const canWrite = user?.role !== 'read_only';

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout, isAdmin, isOfficer, isReviewer, canWrite }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
