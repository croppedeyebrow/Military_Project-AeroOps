import { describe, expect, it } from "vitest";
import { formatDeploymentLabel, shortenGitSha } from "./format";

describe("shortenGitSha", () => {
  it("40자 SHA를 기본 10자로 줄인다", () => {
    expect(shortenGitSha("abcdef0123456789abcdef0123456789abcdef01")).toBe("abcdef0123");
  });

  it("local-dev placeholder(9자)는 기본 길이(10) 안에 들어가 그대로 둔다", () => {
    expect(shortenGitSha("local-dev")).toBe("local-dev");
  });

  it("길이를 명시하면 그 길이로 줄인다", () => {
    expect(shortenGitSha("abcdef0123456789", 4)).toBe("abcd");
  });
});

describe("formatDeploymentLabel", () => {
  it("git_sha(축약)와 image_tag를 가운뎃점으로 연결한다", () => {
    const label = formatDeploymentLabel({
      git_sha: "abcdef0123456789abcdef0123456789abcdef01",
      image_tag: "v1.2.3",
    });
    expect(label).toBe("abcdef0123 · v1.2.3");
  });
});
