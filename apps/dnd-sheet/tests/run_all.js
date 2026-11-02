// Runs every test file for the app and prints one line each. Exit 0 only if all pass.
// Run: node tests/run_all.js
const { spawnSync } = require("child_process");
const path = require("path");

const files = ["check_html.js", "pure.test.js", "mapper.test.js", "clean.test.js"];
let bad = 0;
files.forEach((f) => {
  const r = spawnSync(process.execPath, [path.join(__dirname, f)], { encoding: "utf8" });
  const last = (r.stdout || "").trim().split("\n").pop();
  console.log((r.status === 0 ? "PASS " : "FAIL ") + f.padEnd(16) + " " + (r.status === 0 ? last : (r.stderr || "").trim().split("\n").slice(-3).join(" | ")));
  if (r.status !== 0) bad++;
});
console.log(bad ? bad + " file(s) failed" : "all " + files.length + " test files passed");
process.exit(bad ? 1 : 0);
