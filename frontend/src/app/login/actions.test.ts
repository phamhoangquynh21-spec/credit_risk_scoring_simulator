import { describe, it, expect, vi } from "vitest";

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: async () => ({
    auth: { signInWithPassword: vi.fn(async () => ({ error: null })) },
  }),
}));

describe("demo-login route", () => {
  it("rejects an unknown role with 400", async () => {
    const { POST } = await import("./../api/demo-login/route");
    const res = await POST(new Request("http://x/api/demo-login", {
      method: "POST", body: JSON.stringify({ role: "hacker" }),
    }));
    expect(res.status).toBe(400);
  });
});
