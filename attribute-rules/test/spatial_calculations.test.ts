import { expect, test } from "vitest";
import ArcGISMap from "@arcgis/core/Map.js";
import FeatureLayer from "@arcgis/core/layers/FeatureLayer.js";
import { feature, lineGeometry, loadExecutor } from "./_helpers.js";

function emptyPolygonLayer(title: string, fields: any[]) {
  return new FeatureLayer({
    title, geometryType: "polygon", spatialReference: { wkid: 26912 },
    objectIdField: "OBJECTID", fields: [{ name: "OBJECTID", type: "oid" }, ...fields], source: []
  });
}

function emptyDatastore() {
  return new ArcGISMap({ layers: [
    emptyPolygonLayer("AddressSystemQuadrants", [{ name: "QUADRANT", type: "string" }, { name: "GRID_NAME", type: "string" }]),
    emptyPolygonLayer("Counties", [{ name: "FIPS_STR", type: "string" }, { name: "NAME", type: "string" }]),
    emptyPolygonLayer("ZipCodes", [{ name: "ZIP5", type: "string" }, { name: "NAME", type: "string" }]),
    emptyPolygonLayer("Municipalities", [{ name: "NAME", type: "string" }])
  ] });
}

const spatialExecutor = await loadExecutor("calculation/Roads_Edit/spatial_assignments.arcade", [
  { name: "$feature", type: "feature" }, { name: "$datastore", type: "featureSetCollection" }
]);
const uniqueIdExecutor = await loadExecutor("calculation/Roads_Edit/unique_id.arcade", [
  { name: "$feature", type: "feature" }, { name: "$datastore", type: "featureSetCollection" }
]);

test("spatial_assignments compiles with its datastore contract", () => {
  expect(spatialExecutor).toBeDefined();
});

test("spatial_assignments assigns UDOT to both sides for zero-prefixed routes", async () => {
  const result = await spatialExecutor.executeAsync({
    "$feature": feature({ DOT_RTNAME: "0123" }, lineGeometry), "$datastore": emptyDatastore()
  });
  expect(result.result.attributes).toMatchObject({ DOT_OWN_L: "UDOT", DOT_OWN_R: "UDOT" });
});

test("unique_id reports missing geometry", async () => {
  const result = await uniqueIdExecutor.executeAsync({
    "$feature": feature({ NAME: "MAIN", POSTDIR: null, POSTTYPE: null }), "$datastore": emptyDatastore()
  });
  expect(result).toBe("ERR:MISSING_GEOMETRY");
});