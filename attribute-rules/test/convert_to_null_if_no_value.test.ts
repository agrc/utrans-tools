import { expect, test } from "vitest";
import { feature, loadExecutor } from "./_helpers.js";

const executor = await loadExecutor(
  "calculation/Roads_Edit/convert_to_null_if_no_value.arcade",
  [{ name: "$feature", type: "feature" }]
);

test("convert_to_null_if_no_value converts blank text fields to null", () => {
  const result = executor.execute({
    "$feature": feature({
      ADDRSYS_L: "   ", ADDRSYS_R: "GRID", BIKE_L: "", BIKE_R: "Existing",
      BIKE_PLN_L: null, BIKE_PLN_R: "Plan", DOT_HWYNAM: "", DOT_RTNAME: "Route", DOT_RTPART: "  "
    })
  });

  expect(result).toEqual({
    result: { attributes: {
      ADDRSYS_L: null, ADDRSYS_R: "GRID", BIKE_L: null, BIKE_R: "Existing",
      BIKE_PLN_L: null, BIKE_PLN_R: "Plan", DOT_HWYNAM: null, DOT_RTNAME: "Route", DOT_RTPART: null
    } }
  });
});