import { describe, it, expect, vi, beforeEach } from "vitest";

beforeEach(() => vi.stubEnv("ML_SERVICE_URL", "http://ml.test"));

describe("callMl", () => {
  it("posts JSON with a bearer token and returns the parsed body", async () => {
    const fetchMock = vi.fn(async () =>
      new Response(JSON.stringify({ risk_score: 82 }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const { callMl } = await import("./ml");
    const out = await callMl("/api/v1/predict", "tok", { age: 24 });
    expect(out.risk_score).toBe(82);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("http://ml.test/api/v1/predict");
    expect((init as RequestInit).headers).toMatchObject({ Authorization: "Bearer tok" });
  });
});
