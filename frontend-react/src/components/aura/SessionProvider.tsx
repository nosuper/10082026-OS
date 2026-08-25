import { createContext, useContext, type ReactNode } from "react";

import { useMethod } from "@/lib/queries";
import {
  FOUNDER_PROBE,
  logout,
  sessionUserId,
  sessionUserName,
  initials as toInitials,
} from "@/lib/session";

export type Session = {
  /** The account, e.g. "bao@studio.vn". */
  userId: string;
  /** The display name Frappe set at login. */
  userName: string;
  /** Two letters for an avatar. */
  initials: string;
  /**
   * Decided by the server, not by the browser. False while the probe is still
   * in flight, so founder-only chrome appears rather than disappears.
   */
  isFounder: boolean;
  /** True until the founder check has answered. */
  isLoading: boolean;
  logout: () => void;
};

const SessionContext = createContext<Session>({
  userId: "",
  userName: "",
  initials: "?",
  isFounder: false,
  isLoading: false,
  logout: () => {},
});

export function SessionProvider({ children }: { children: ReactNode }) {
  // The probe's failure is its answer, so it must not be retried and must not
  // go stale: a producer would otherwise re-ask a question already refused.
  const probe = useMethod<number>(FOUNDER_PROBE, undefined, {
    retry: false,
    staleTime: Number.POSITIVE_INFINITY,
  });

  const userName = sessionUserName();

  const session: Session = {
    userId: sessionUserId(),
    userName,
    initials: toInitials(userName),
    isFounder: probe.isSuccess,
    isLoading: probe.isPending,
    logout: () => void logout(),
  };

  return <SessionContext.Provider value={session}>{children}</SessionContext.Provider>;
}

/** The signed-in user, from anywhere under the root route. */
export function useSession(): Session {
  return useContext(SessionContext);
}
