"use client";

import { useEffect, useMemo, useState } from "react";

import {
  TRACE_CLIENT,
  TRACE_PRODUCER,
  TRACE_SERVER,
} from "@/lib/design-tokens";
import {
  presenceSocketUrl,
  type PresenceStatus,
  type PresenceUser,
} from "@/lib/collaboration";

type PresenceSocketEvent = {
  type?: string | undefined;
  user?: string | undefined;
  display?: string | undefined;
  status?: PresenceStatus | undefined;
  focus?: string | undefined;
  color?: string | undefined;
};

export interface PresenceSocketOptions {
  workspaceId: string | undefined;
  callerSub: string;
  display: string;
  focus?: string | undefined;
  baseUrl?: string | undefined;
  enabled?: boolean | undefined;
  initialUsers?: readonly PresenceUser[] | undefined;
}

export interface PresenceSocketState {
  users: readonly PresenceUser[];
  connected: boolean;
  error: string | null;
  socketUrl: string | null;
}

const PRESENCE_COLORS = [TRACE_SERVER, TRACE_CLIENT, TRACE_PRODUCER] as const;
const EMPTY_PRESENCE_USERS: readonly PresenceUser[] = [];

function colorForUser(id: string): string {
  let total = 0;
  for (const char of id) total += char.charCodeAt(0);
  return PRESENCE_COLORS[total % PRESENCE_COLORS.length] ?? TRACE_SERVER;
}

function normalizePresenceUser(
  event: PresenceSocketEvent,
  fallback: { callerSub: string; display: string; focus?: string | undefined },
): PresenceUser | null {
  const id = event.user ?? fallback.callerSub;
  if (!id) return null;
  const nextFocus = event.focus ?? fallback.focus;
  return {
    id,
    display:
      event.display ?? (id === fallback.callerSub ? fallback.display : id),
    color: event.color ?? colorForUser(id),
    status: event.status ?? "active",
    ...(nextFocus !== undefined ? { focus: nextFocus } : {}),
  };
}

function upsertUser(
  users: readonly PresenceUser[],
  nextUser: PresenceUser,
): PresenceUser[] {
  const index = users.findIndex((user) => user.id === nextUser.id);
  if (index === -1) return [...users, nextUser];
  return users.map((user, currentIndex) =>
    currentIndex === index ? { ...user, ...nextUser } : user,
  );
}

function removeUser(
  users: readonly PresenceUser[],
  userId: string | undefined,
): PresenceUser[] {
  if (!userId) return [...users];
  return users.filter((user) => user.id !== userId);
}

export function usePresenceSocket({
  workspaceId,
  callerSub,
  display,
  focus,
  baseUrl,
  enabled = true,
  initialUsers = EMPTY_PRESENCE_USERS,
}: PresenceSocketOptions): PresenceSocketState {
  const socketUrl = useMemo(
    () =>
      workspaceId
        ? presenceSocketUrl(
            workspaceId,
            baseUrl === undefined ? { callerSub } : { callerSub, baseUrl },
          )
        : null,
    [baseUrl, callerSub, workspaceId],
  );
  const [users, setUsers] = useState<readonly PresenceUser[]>(initialUsers);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setUsers(initialUsers);
  }, [initialUsers]);

  useEffect(() => {
    if (!enabled || !workspaceId || !socketUrl) {
      setConnected(false);
      return;
    }
    if (typeof WebSocket === "undefined") {
      setError("WebSocket is not available in this browser.");
      setConnected(false);
      return;
    }

    let closed = false;
    const socket = new WebSocket(socketUrl);
    const currentUser = normalizePresenceUser(
      { user: callerSub, display, focus },
      { callerSub, display, focus },
    );
    if (currentUser) {
      setUsers((current) => upsertUser(current, currentUser));
    }

    socket.onopen = () => {
      if (closed) return;
      setConnected(true);
      setError(null);
      socket.send(
        JSON.stringify({
          type: "presence.update",
          display,
          status: "active",
          focus,
          color: currentUser?.color,
        }),
      );
    };
    socket.onmessage = (message) => {
      if (closed) return;
      try {
        const event = JSON.parse(String(message.data)) as PresenceSocketEvent;
        if (event.type === "presence.left") {
          setUsers((current) => removeUser(current, event.user));
          return;
        }
        if (
          event.type === "presence.joined" ||
          event.type === "presence.update"
        ) {
          const nextUser = normalizePresenceUser(event, {
            callerSub,
            display,
            focus,
          });
          if (nextUser) {
            setUsers((current) => upsertUser(current, nextUser));
          }
        }
      } catch {
        setError("Presence update could not be parsed.");
      }
    };
    socket.onerror = () => {
      if (closed) return;
      setError("Presence socket failed.");
      setConnected(false);
    };
    socket.onclose = () => {
      if (closed) return;
      setConnected(false);
    };

    return () => {
      closed = true;
      socket.close();
    };
  }, [callerSub, display, enabled, focus, socketUrl, workspaceId]);

  return { users, connected, error, socketUrl };
}
