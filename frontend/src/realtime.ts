import { createClient } from "@supabase/supabase-js";

// Supabase Realtime subscription to new odds snapshots. The backend writes a
// row to `snapshots` after every re-simulation; Supabase pushes the INSERT to
// every open browser, so odds update the instant a goal is processed — no
// polling. Falls back to null when Supabase isn't configured, in which case
// the app keeps polling the API (see App.tsx).
//
// Vite env vars (browser-safe; baked into the build, protected by RLS):
//   VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY
const URL = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

export const isRealtimeConfigured = Boolean(URL && ANON_KEY);

/**
 * Subscribe to snapshot inserts. Calls onSnapshot whenever a new snapshot row
 * lands. Returns an unsubscribe function, or null if Supabase isn't
 * configured (caller should fall back to polling).
 */
export function subscribeToSnapshots(
  onSnapshot: () => void,
): (() => void) | null {
  if (!URL || !ANON_KEY) return null;

  const supabase = createClient(URL, ANON_KEY, {
    auth: { persistSession: false },
  });

  const channel = supabase
    .channel("snapshots-stream")
    .on(
      "postgres_changes",
      { event: "INSERT", schema: "public", table: "snapshots" },
      () => onSnapshot(),
    )
    .subscribe();

  return () => {
    supabase.removeChannel(channel);
  };
}
