import { readdirSync } from "node:fs";
import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

// Feature-Sliced Design boundaries. Layers import downwards only
// (app -> widgets -> features -> entities -> shared); slices are used through
// their index.ts barrel; slices of one layer don't import each other.
const slices = (layer) =>
  readdirSync(new URL(`./src/${layer}`, import.meta.url), { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name);

const deepImport = (layer) => ({
  group: [`@/${layer}/*/*`],
  message: `Import from the slice barrel (@/${layer}/<slice>), not its internals.`,
});

const upward = (layers, why) =>
  layers.map((layer) => ({
    group: [`@/${layer}`, `@/${layer}/**`],
    message: `${why} must not import from the "${layer}" layer.`,
  }));

const siblings = (layer) =>
  slices(layer).map((slice) => ({
    files: [`src/${layer}/${slice}/**`],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            deepImport("features"),
            deepImport("widgets"),
            deepImport("entities"),
            ...(layer === "entities" ? upward(["features", "widgets", "app"], "An entity") : []),
            ...(layer === "features" ? upward(["widgets", "app"], "A feature") : []),
            ...(layer === "widgets" ? upward(["app"], "A widget") : []),
            ...slices(layer)
              .filter((other) => other !== slice)
              .map((other) => ({
                group: [`@/${layer}/${other}`],
                message: `Slices of the "${layer}" layer must not import each other; move shared code down a layer.`,
              })),
          ],
        },
      ],
    },
  }));

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    files: ["src/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-imports": ["error", { patterns: [deepImport("features"), deepImport("widgets"), deepImport("entities")] }],
    },
  },
  {
    files: ["src/shared/**"],
    rules: {
      "no-restricted-imports": [
        "error",
        { patterns: [deepImport("features"), deepImport("widgets"), deepImport("entities"), ...upward(["entities", "features", "widgets", "app"], "shared code")] },
      ],
    },
  },
  ...siblings("entities"),
  ...siblings("features"),
  ...siblings("widgets"),
  // Tests may reach into a slice to test its internals.
  {
    files: ["src/**/*.test.{ts,tsx}"],
    rules: { "no-restricted-imports": "off" },
  },
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
]);

export default eslintConfig;
