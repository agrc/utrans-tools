import { readFile } from "node:fs/promises";
import Graphic from "@arcgis/core/Graphic.js";
import { createArcadeExecutor } from "@arcgis/core/arcade.js";

export async function loadExecutor(relativePath: string, variables: any[]) {
  const expression = await readFile(
    new URL(`../${relativePath}`, import.meta.url),
    "utf8"
  );

  return createArcadeExecutor(expression, { variables });
}

export function feature(attributes: Record<string, any>, geometry?: any) {
  return new Graphic({ attributes, geometry });
}

// NAD83 UTM 12N to match Roads_Edit; Offset() uses linear units and rejects a geographic SR
export const lineGeometry = {
  type: "polyline",
  paths: [[[424100, 4505000], [432500, 4505000]]],
  spatialReference: { wkid: 26912 }
};