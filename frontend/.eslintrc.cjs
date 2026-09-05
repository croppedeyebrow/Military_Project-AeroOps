module.exports = {
  root: true,
  env: { browser: true, es2022: true },
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
  ],
  parser: "@typescript-eslint/parser",
  plugins: ["react-hooks", "@typescript-eslint"],
  ignorePatterns: ["dist", "node_modules"],
  rules: {
    "react-hooks/rules-of-hooks": "error",
  },
};
