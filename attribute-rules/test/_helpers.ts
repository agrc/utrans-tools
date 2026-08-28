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

export const lineGeometry = {
  type: "polyline",
  paths: [[[-111.9, 40.7], [-111.8, 40.7]]],
  spatialReference: { wkid: 4326 }
};