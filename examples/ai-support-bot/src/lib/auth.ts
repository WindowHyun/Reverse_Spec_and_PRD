import { createContext, useContext } from "react";

type User = { id: string; role: "user" | "admin" } | null;

export const AuthContext = createContext<{ user: User }>({ user: null });

export function useAuth() {
  return useContext(AuthContext);
}
