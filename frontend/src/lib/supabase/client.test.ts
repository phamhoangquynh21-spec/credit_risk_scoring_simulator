import { describe, it, expect, vi, beforeEach } from "vitest";

beforeEach(() => {
  vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://x.supabase.co");
  vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "anon-key");
});

describe("createBrowserSupabase", () => {
  it("returns a client with auth + from()", async () => {
    const { createBrowserSupabase } = await import("./client");
    const sb = createBrowserSupabase();
    expect(sb.auth).toBeDefined();
    expect(typeof sb.from).toBe("function");
  });
});
