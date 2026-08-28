import { expect, test } from "vitest";
import { feature, loadExecutor } from "./_helpers.js";

const whitespaceExecutor = await loadExecutor(
  "calculation/Roads_Edit/remove_extra_whitespace.arcade",
  [{ name: "$feature", type: "feature" }]
);
const fullnameExecutor = await loadExecutor(
  "calculation/Roads_Edit/fullname_calculation.arcade",
  [{ name: "$feature", type: "feature" }]
);

test("remove_extra_whitespace trims and collapses spaces", () => {
  expect(whitespaceExecutor.execute({ "$feature": feature({ NAME: "  NORTH   MAIN  " }) })).toBe("NORTH MAIN");
});

test("remove_extra_whitespace returns an empty string for a missing NAME", () => {
  expect(whitespaceExecutor.execute({ "$feature": feature({ NAME: null }) })).toBe("");
});

test("fullname_calculation combines normalized name parts", () => {
  expect(fullnameExecutor.execute({
    "$feature": feature({ NAME: "  O'MAIN  ", POSTDIR: null, POSTTYPE: "  RD  " })
  })).toBe("OMAIN RD");
});

test("fullname_calculation omits missing name parts", () => {
  expect(fullnameExecutor.execute({
    "$feature": feature({ NAME: null, POSTDIR: " N ", POSTTYPE: null })
  })).toBe("N");
});