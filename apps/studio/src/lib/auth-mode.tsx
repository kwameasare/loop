"use client";

import {
  createContext,
  useContext,
  type ReactNode,
} from "react";

const AuthModeContext = createContext<boolean | null>(null);

export function AuthModeProvider({
  auth0Configured,
  children,
}: {
  auth0Configured: boolean;
  children: ReactNode;
}) {
  return (
    <AuthModeContext.Provider value={auth0Configured}>
      {children}
    </AuthModeContext.Provider>
  );
}

export function useAuth0Configured(): boolean {
  const configured = useContext(AuthModeContext);
  if (configured !== null) return configured;
  return (
    typeof process !== "undefined" &&
    Boolean(process.env.NEXT_PUBLIC_AUTH0_DOMAIN)
  );
}
