import { expect, test } from "vitest";
import FeatureLayer from "@arcgis/core/layers/FeatureLayer.js";
import { feature, loadExecutor } from "./_helpers.js";

const executor = await loadExecutor(
  "constraint/Roads_Edit/constrain_to_attribute_domain.arcade",
  [{ name: "$feature", type: "feature" }]
);

function roadFeature(attributes: Record<string, any>) {
  const layer = new FeatureLayer({
    title: "Roads",
    fields: [
      { name: "OBJECTID", type: "oid" },
      { name: "SPEED_LMT", type: "integer", domain: {
        type: "coded-value", name: "Speed limits",
        codedValues: [{ code: 25, name: "25 mph" }, { code: 35, name: "35 mph" }]
      } }
    ],
    objectIdField: "OBJECTID",
    source: []
  });
  const road = feature({
    OBJECTID: 1, PREDIR: null, POSTTYPE: null, POSTDIR: null, AN_POSTDIR: null,
    A1_PREDIR: null, A1_POSTTYPE: null, A1_POSTDIR: null, A2_PREDIR: null,
    A2_POSTTYPE: null, A2_POSTDIR: null, VERT_LEVEL: null, ONEWAY: null,
    SPEED_LMT: null, ...attributes
  });
  (road as any).layer = layer;
  return road;
}

test("constrain_to_attribute_domain accepts a coded domain value", () => {
  expect(executor.execute({ "$feature": roadFeature({ SPEED_LMT: 35 }) })).toBe(true);
});

test("constrain_to_attribute_domain accepts an empty string", () => {
  expect(executor.execute({ "$feature": roadFeature({ SPEED_LMT: "" }) })).toBe(true);
});

test("constrain_to_attribute_domain rejects an invalid coded domain value", () => {
  expect(executor.execute({ "$feature": roadFeature({ SPEED_LMT: 30 }) })).toEqual({
    errorMessage: "Invalid value [30] entered for field: SPEED_LMT"
  });
});