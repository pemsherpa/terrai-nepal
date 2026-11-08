import { describe, expect, it } from "vitest";
import { unwrapList } from "@/lib/api";

describe("unwrapList", () => {
  it("returns array directly when already an array", () => {
    const items = [{ id: "1" }, { id: "2" }];
    expect(unwrapList(items)).toEqual(items);
  });

  it("extracts results from paginated response", () => {
    const paginated = {
      count: 1,
      next: null,
      previous: null,
      results: [{ id: "abc" }],
    };
    expect(unwrapList(paginated)).toEqual([{ id: "abc" }]);
  });
});

describe("api client", () => {
  it("stores and clears tokens in localStorage", async () => {
    const { setTokens, getAccessToken, clearTokens } = await import("@/lib/api");
    setTokens({ access: "test-access", refresh: "test-refresh" });
    expect(getAccessToken()).toBe("test-access");
    clearTokens();
    expect(getAccessToken()).toBeNull();
  });
});
