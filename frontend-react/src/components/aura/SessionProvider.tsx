import { createContext, useContext, type ReactNode } from "react";

import { useMethod } from "@/lib/queries";
import {
  FOUNDER_PROBE,
  logout,
  sessionUserId,
  sessionUserName,
  initials as toInitials,
} from "@/lib/session";

/**
 * What this session is *for*, decided by the server (T7.1).
 *
 * A crew session has no deals board and no jobs list to offer, and a nav bar
 * full of links that answer with a permission error is worse than no nav bar
 * at all. Asked rather than derived from a role name, because the mapping from
 * roles to screens is the server's and a browser copy of it goes stale
 * silently.
 */
export type SessionScope = {
  user: string;
  crew_only: boolean;
  can_read_jobs: boolean;
  can_read_deals: boolean;
  can_read_settings: boolean;
  /** Which managed lists this session may edit, if any. */
  manages_vocabularies: string[];
};

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
  /**
   * What this session may reach. Optimistic while in flight - jobs and deals
   * default to true so an operating role never watches its own nav appear,
   * and `crewOnly` defaults to false for the same reason in reverse.
   */
  scope: SessionScope;
  /** How the sidebar names this person. */
  roleLabel: string;
  logout: () => void;
};

/**
 * Before the scope answers. Optimistic on the two boards because the common
 * case by far is an operating role, and a nav that appears a beat late reads
 * as breakage; a crew session sees two links vanish instead, once.
 */
const OPEN_SCOPE: SessionScope = {
  user: "",
  crew_only: false,
  can_read_jobs: true,
  can_read_deals: true,
  can_read_settings: true,
  manages_vocabularies: [],
};

const SessionContext = createContext<Session>({
  userId: "",
  userName: "",
  initials: "?",
  isFounder: false,
  isLoading: false,
  scope: OPEN_SCOPE,
  roleLabel: "",
  logout: () => {},
});

export function SessionProvider({ children }: { children: ReactNode }) {
  // The probe's failure is its answer, so it must not be retried and must not
  // go stale: a producer would otherwise re-ask a question already refused.
  const probe = useMethod<number>(FOUNDER_PROBE, undefined, {
    retry: false,
    staleTime: Number.POSITIVE_INFINITY,
  });

  // Not founder-only and not retried into the ground: every signed-in session
  // gets an answer, and the answer decides what the nav offers.
  const scope = useMethod<SessionScope>("auraos.api.session_scope", undefined, {
    staleTime: Number.POSITIVE_INFINITY,
  });

  const userName = sessionUserName();
  const reach = scope.data ?? OPEN_SCOPE;

  const session: Session = {
    userId: sessionUserId(),
    userName,
    initials: toInitials(userName),
    isFounder: probe.isSuccess,
    isLoading: probe.isPending,
    scope: reach,
    // Named from what the session can reach rather than from a role string:
    // "Producer" printed under a crew member's name was the old app's answer
    // and it was wrong about the one person it mattered to.
    roleLabel: probe.isSuccess ? "Founder" : reach.crew_only ? "Crew" : "Producer",
    logout: () => void logout(),
  };

  return <SessionContext.Provider value={session}>{children}</SessionContext.Provider>;
}

/** The signed-in user, from anywhere under the root route. */
export function useSession(): Session {
  return useContext(SessionContext);
}
