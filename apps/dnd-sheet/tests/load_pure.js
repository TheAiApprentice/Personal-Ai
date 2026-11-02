// Pulls the pure-logic script out of index.html and returns its exports.
const fs = require("fs");
const path = require("path");

const HTML = path.join(__dirname, "..", "index.html");

function extractScripts(html) {
  const out = [];
  const re = /<script([^>]*)>([\s\S]*?)<\/script>/gi;
  let m;
  while ((m = re.exec(html))) out.push({ attrs: m[1], body: m[2] });
  return out;
}

function loadPure() {
  const html = fs.readFileSync(HTML, "utf8");
  const s = extractScripts(html).find((x) => /id="pure-logic"/.test(x.attrs));
  if (!s) throw new Error('script id="pure-logic" not found');
  const mod = { exports: {} };
  new Function("module", s.body)(mod);
  return mod.exports;
}

module.exports = { loadPure, extractScripts, HTML };
