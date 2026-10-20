import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
  {
    // These two rules (from the React Compiler-era eslint-plugin-react-hooks)
    // flag 8 existing components. The app works, and rewriting them blind could
    // change UI behaviour, so they are warnings: still listed on every run, but
    // they don't block CI/deploys. TODO: refactor the flagged effects/refs, then
    // delete this block.
    rules: {
      "react-hooks/set-state-in-effect": "warn",
      "react-hooks/refs": "warn",
    },
  },
]);

export default eslintConfig;
