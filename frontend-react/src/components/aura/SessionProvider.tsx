import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { logout, sessionUserName, probeFounder } from "@/lib/session";

export type Session = {
  userName: string;
  isFounder: boolean;
  logout: () => void;
};

const SessionContext = createContext<Session>({
  userName: "",
  isFounder: false,
  logout: () => {},
});

export function SessionProvider({ children }: { children: ReactNode }) {
  const [userName] = useState(sessionUserName);
  const [isFounder, setIsFounder] = useState(false);

  useEffect(() => {
    let live = true;
    void probeFounder().then((founder) => {
      if (live) setIsFounder(founder);
    });
    return () => {
      live = false;
    };
  }, []);

  return (
    <SessionContext.Provider value={{ userName, isFounder, logout: () => void logout() }}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSession(): Session {
  return useContext(SessionContext);
}
