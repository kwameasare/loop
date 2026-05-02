import { describe, expect, it } from "vitest";

import { DEFAULT_REGION, REGIONS, inferRegionFromTimezone } from "./regions";

describe("regions catalog (S594)", () => {
  it("matches RegionName literal in openapi-types", () => {
    // If openapi regen ever drops na-east or eu-west, this assertion
    // pins us against silent breakage.
    expect(REGIONS.map((r) => r.value).sort()).toEqual(["eu-west", "na-east"]);
  });

  it("every region has a non-empty description and at least one TZ prefix", () => {
    for (const r of REGIONS) {
      expect(r.label.length).toBeGreaterThan(0);
      expect(r.description.length).toBeGreaterThan(0);
      expect(r.timezonePrefixes.length).toBeGreaterThan(0);
    }
  });
});

describe("inferRegionFromTimezone (S594)", () => {
  it("infers eu-west for European timezones", () => {
    expect(inferRegionFromTimezone("Europe/Berlin")).toBe("eu-west");
    expect(inferRegionFromTimezone("Europe/Paris")).toBe("eu-west");
    expect(inferRegionFromTimezone("Europe/London")).toBe("eu-west");
  });

  it("infers na-east for North American timezones", () => {
    expect(inferRegionFromTimezone("America/New_York")).toBe("na-east");
    expect(inferRegionFromTimezone("America/Los_Angeles")).toBe("na-east");
    expect(inferRegionFromTimezone("America/Toronto")).toBe("na-east");
  });

  it("falls back to DEFAULT_REGION on unknown / undefined timezone", () => {
    expect(inferRegionFromTimezone(undefined)).toBe(DEFAULT_REGION);
    expect(inferRegionFromTimezone("Mars/Olympus_Mons")).toBe(DEFAULT_REGION);
    expect(inferRegionFromTimezone("Asia/Tokyo")).toBe(DEFAULT_REGION);
  });
});
