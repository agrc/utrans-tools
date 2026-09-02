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

const uniqueIdLineGeometry = {
  type: "polyline",
  paths: [[[424100, 4505000], [432500, 4505000]]],
  spatialReference: { wkid: 102100 }
};

function nationalGridDatastore() {
  return new ArcGISMap({ layers: [
    new FeatureLayer({
      title: "NationalGrid", geometryType: "polygon", spatialReference: { wkid: 102100 },
      objectIdField: "OBJECTID",
      fields: [
        { name: "OBJECTID", type: "oid" },
        { name: "GRID1MIL", type: "string" },
        { name: "GRID100K", type: "string" }
      ],
      source: [feature({ OBJECTID: 1, GRID1MIL: "12T", GRID100K: "VK" }, {
        type: "polygon",
        rings: [[[420000, 4500000], [435000, 4500000], [435000, 4510000], [420000, 4510000], [420000, 4500000]]],
        spatialReference: { wkid: 102100 }
      })]
    })
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

test("unique_id appends post direction before post type for non-letter names", async () => {
  const result = await uniqueIdExecutor.executeAsync({
    "$feature": feature({ NAME: "4500", POSTDIR: "W", POSTTYPE: "TER" }, uniqueIdLineGeometry),
    "$datastore": nationalGridDatastore()
  });
  expect(result).toBe("12TVK28300500_4500_W_TER");
});

test("unique_id appends post type before post direction for letters-only names", async () => {
  const result = await uniqueIdExecutor.executeAsync({
    "$feature": feature({ NAME: "Main", POSTDIR: "W", POSTTYPE: "TER" }, uniqueIdLineGeometry),
    "$datastore": nationalGridDatastore()
  });
  expect(result).toBe("12TVK28300500_MAIN_TER_W");
});