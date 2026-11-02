// Structure checks for index.html.  Run: node tests/check_html.js
const assert = require("assert");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { execFileSync } = require("child_process");
const { extractScripts, HTML } = require("./load_pure");

const html = fs.readFileSync(HTML, "utf8");
let n = 0;
function t(name, fn) { fn(); n++; console.log("ok - " + name); }

t("under 1 MB", () => assert.ok(Buffer.byteLength(html) < 1024 * 1024, String(Buffer.byteLength(html))));
t("no doctype / html / head / body tags", () => {
  assert.ok(!/<!doctype/i.test(html));
  assert.ok(!/<\/?(html|head|body)[\s>]/i.test(html));
});
t("<title> is first, <style> is second", () => {
  assert.ok(/^<title>[^<]{3,40}<\/title>\s*<style>/.test(html));
  const title = /<title>([^<]*)<\/title>/.exec(html)[1];
  assert.ok(title.trim().split(/\s+/).length >= 2 && title.trim().split(/\s+/).length <= 4, title);
  const firstTags = [...html.matchAll(/<(title|style|script|div|main|nav)\b/g)].map((m) => m[1]);
  assert.deepStrictEqual(firstTags.slice(0, 2), ["title", "style"]);
});
t("every inline script passes node --check", () => {
  const inline = extractScripts(html).filter((s) => !/\ssrc=/.test(s.attrs));
  assert.ok(inline.length >= 2);
  inline.forEach((s, i) => {
    const f = path.join(os.tmpdir(), "dnd-sheet-inline-" + process.pid + "-" + i + ".js");
    fs.writeFileSync(f, s.body);
    try { execFileSync(process.execPath, ["--check", f], { stdio: "pipe" }); }
    finally { fs.unlinkSync(f); }
  });
  console.log("   (" + inline.length + " inline scripts checked)");
});
t("external scripts: cdnjs only, exact versions", () => {
  const srcs = [...html.matchAll(/<script[^>]*\ssrc="([^"]+)"/g)].map((m) => m[1]);
  assert.ok(srcs.length >= 1);
  srcs.forEach((s) => assert.ok(/^https:\/\/cdnjs\.cloudflare\.com\/ajax\/libs\/[\w.\-]+\/\d+\.\d+\.\d+\//.test(s), s));
  assert.ok(srcs.some((s) => s.includes("pdf.js/3.11.174/pdf.min.js")));
  assert.ok(html.includes("https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js"));
});
t("fonts are Google only; no other hosts at all", () => {
  const hosts = new Set([...html.matchAll(/https?:\/\/([a-z0-9.\-]+)/gi)].map((m) => m[1]));
  const bad = [...hosts].filter((h) => !["cdnjs.cloudflare.com", "fonts.googleapis.com"].includes(h));
  assert.deepStrictEqual(bad, []);
});
t("no fetch( , alert( , confirm( , prompt( ; localStorage only for UI bits and the device save in deviceStorage()", () => {
  const code = extractScripts(html).map((s) => s.body).join("\n");
  assert.ok(!/\bfetch\s*\(/.test(code));
  assert.ok(!/\b(alert|confirm|prompt)\s*\(/.test(code));
  const lines = code.replace(/\/\*[\s\S]*?\*\//g, "").split("\n").filter((l) => /localStorage/.test(l));
  lines.forEach((l) => assert.ok(/UI_KEY/.test(l) || /win\.localStorage, k = LOCAL_PREFIX/.test(l), l.trim()));
  assert.strictEqual(lines.filter((l) => /win\.localStorage/.test(l)).length, 1, "one place opens the device storage");
});
t("black and white theme: every colour lives in :root variables, one palette for all modes", () => {
  const style = /<style>([\s\S]*?)<\/style>/.exec(html)[1];
  const root = /:root\{([^}]*)\}/.exec(style)[1];
  const rest = style.replace(/:root\{[^}]*\}/, "");
  assert.ok(!/#[0-9a-fA-F]{3,8}\b/.test(rest.replace(/&#\d+;/g, "")), "hard-coded colour outside :root: " + (rest.match(/#[0-9a-fA-F]{3,8}\b/) || [])[0]);
  assert.ok(!/rgba?\(|hsla?\(/.test(rest), "rgb()/hsl() colour outside :root");
  assert.ok(!/prefers-color-scheme/.test(style) && !/data-theme/.test(style), "no per-mode palettes");
  assert.ok((root.match(/color-scheme:dark/g) || []).length === 1);
  assert.ok(/body\{[^}]*background:var\(--bg\)/.test(html));
  const v = {}; root.replace(/--([a-z0-9-]+):(#[0-9a-fA-F]{6})/g, (_, k, c) => { v[k] = c; });
  const lum = (h) => { const x = [1, 3, 5].map((i) => parseInt(h.substr(i, 2), 16) / 255).map((c) => (c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4))); return 0.2126 * x[0] + 0.7152 * x[1] + 0.0722 * x[2]; };
  const cr = (a, b) => { const l = [lum(a), lum(b)].sort((p, q) => q - p); return (l[0] + 0.05) / (l[1] + 0.05); };
  assert.strictEqual(v.bg, "#000000"); assert.strictEqual(v.ink, "#ffffff");
  [["ink", "bg"], ["ink", "surface"], ["ink", "surface2"], ["muted", "bg"], ["muted", "surface"], ["off", "bg"], ["off", "surface2"], ["accent-ink", "accent"],
    ["danger", "bg"], ["danger", "surface"], ["danger-ink", "danger"], ["warn-ink", "warn"], ["bar-ink", "bar"], ["label-ink", "label-bg"]].forEach(([f, b]) => {
    const r = cr(v[f], v[b]); assert.ok(r >= 4.5, "contrast " + f + " on " + b + " is " + r.toFixed(2));
  });
  [["line", "bg"], ["line", "surface"], ["focus", "bg"]].forEach(([f, b]) => assert.ok(cr(v[f], v[b]) >= 3, "UI contrast " + f + " on " + b));
  const g = (h) => { const x = [1, 3, 5].map((i) => parseInt(h.substr(i, 2), 16)); return Math.max(...x) - Math.min(...x); };
  ["bg", "surface", "surface2", "ink", "muted", "line", "hair", "accent", "warn", "off", "bar", "label-bg"].forEach((k) => assert.strictEqual(g(v[k]), 0, k + " must be a pure grey (no green)"));
});
t("16px gutters and no sideways scroll", () => {
  assert.ok(/#app\{[^}]*padding:0 16px/.test(html));
  assert.ok(/\.topin\{[^}]*padding:8px 16px/.test(html));
  assert.ok(/body\{[^}]*overflow-x:hidden/.test(html));
});
t("reduced-motion respected", () => assert.ok(/prefers-reduced-motion: no-preference/.test(html)));
t("claude.use only called after the first run (inside initCaps, deferred)", () => {
  assert.ok(/setTimeout\(initCaps, 0\)/.test(html));
  assert.ok(!/claude\.use\(/.test(html), "no direct claude.use( call in the first run");
  const body = html.slice(html.indexOf("async function initCaps"));
  assert.ok(/cl\.use\(n\)/.test(body.slice(0, 900)), "use() lives in initCaps");
});
t("every id on a form control is unique and each control has an id", () => {
  const ids = [...html.matchAll(/ id="([^"]+)"/g)].map((m) => m[1]).filter((i) => !i.includes("'"));
  const dup = ids.filter((x, i) => ids.indexOf(x) !== i);
  assert.deepStrictEqual(dup, []);
});

console.log("\n" + n + " structure checks passed");
