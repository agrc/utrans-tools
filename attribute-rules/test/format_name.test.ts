import { expect, test } from "vitest";
import { feature, loadExecutor } from "./_helpers.js";

const executor = await loadExecutor(
  "calculation/Roads_Edit/format_name.arcade",
  [{ name: "$feature", type: "feature" }]
);

test("removes apostrophes from NAME", () => {
  expect(executor.execute({ "$feature": feature({ NAME: "O'CONNELL" }) })).toBe("OCONNELL");
});

test("leaves names without apostrophes unchanged", () => {
  expect(executor.execute({ "$feature": feature({ NAME: "WASHINGTON" }) })).toBe("WASHINGTON");
});

test("uppercases mixed-case names", () => {
  expect(executor.execute({ "$feature": feature({ NAME: "O'Connell" }) })).toBe("OCONNELL");
});