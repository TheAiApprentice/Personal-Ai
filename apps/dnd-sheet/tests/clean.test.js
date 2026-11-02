// The shareable copy: nothing built in, a first-run hint, and every feature working on a brand-new character.
// Run: node tests/clean.test.js
const assert = require("assert");
const fs = require("fs");
const { loadPure, HTML } = require("./load_pure");
const P = loadPure();
const html = fs.readFileSync(HTML, "utf8");

let n = 0;
function t(name, fn) { fn(); n++; console.log("ok - " + name); }
const act = (ch, id) => { const a = P.actionList(ch).find((x) => x.id === id); assert.ok(a, "no action " + id); return a; };
const bar = (ch) => { const o = {}; P.resourceBar(ch).forEach((p) => { o[p.id] = p.label + " " + p.cur + "/" + p.max; }); return o; };
function fresh(cls, abilities, die) {
  return P.sanitizeCharacter({ name: "New " + cls, edition: "2024", cls: cls + " 1", level: 1, abilities, hp: { cur: 10, max: 10 }, hitDice: [{ die, total: 1, used: 0 }] });
}
function picksFor(c) {
  const plan = P.levelUpPlan(c), p = {};
  if (plan.needs.sub) p.sub = plan.needs.sub[0].key;
  if (plan.needs.asi) p.asi = { mode: "feat", name: "Alert" };
  if (plan.needs.boon) p.boon = { name: "Boon of Fate", ab: "" };
  if (plan.needs.cantrips) p.cantrips = [];
  return p;
}
function up(c) { const r = P.levelUp(c, picksFor(c)); assert.ok(r.ok, "level up failed at " + c.level + ": " + r.msg); return r; }
const MONK = ["Monk", { str: 10, dex: 16, con: 14, int: 10, wis: 15, cha: 8 }, 8];
const BARB = ["Barbarian", { str: 16, dex: 14, con: 15, int: 8, wis: 10, cha: 10 }, 12];
const ARTI = ["Artificer", { str: 8, dex: 14, con: 14, int: 16, wis: 12, cha: 10 }, 8];

t("no ready-made characters are built in, and the Roster hides the empty Ready-made section", () => {
  assert.deepStrictEqual(P.PRESETS, []);
  assert.ok(/if \(PRESETS\.length\) h \+= sec\("Ready-made characters"/.test(html));
  assert.ok(!/None built in/.test(html));
});

t("first run shows the made-up example with the hint to create or import a character", () => {
  assert.ok(/S\.chars\.example = exampleCharacter\(\);/.test(html));
  assert.ok(html.includes('<b id="first-run">Create your character or import a sheet.</b>'));
  const ex = P.exampleCharacter(); assert.strictEqual(ex.example, true); assert.ok(/^Example: /.test(ex.name));
});

t("licence note and [check book] flags are kept", () => {
  assert.ok(html.includes("Monk and Barbarian follow the SRD 5.2 (CC-BY-4.0, Wizards of the Coast)"));
  assert.ok(html.includes("not in the SRD (own-words summaries only)"));
  assert.ok((html.match(/\[check book\]/g) || []).length >= 4);
});

t("2024 rules are the default for a blank character and for an imported file without an edition", () => {
  assert.strictEqual(P.blankCharacter().edition, "2024");
  const r = P.characterFromJsonText(JSON.stringify({ name: "Imported", cls: "Monk 3", level: 3, abilities: { str: 10, dex: 10, con: 10, int: 10, wis: 10, cha: 10 } }));
  assert.strictEqual(r.character.edition, "2024");
});

t("level up: a brand-new Monk, Barbarian and Artificer each go 1 -> 20 with the class table, subclass asked at 3", () => {
  [MONK, BARB, ARTI].forEach(([cls, ab, die]) => {
    let c = fresh(cls, ab, die);
    while (c.level < 20) {
      const plan = P.levelUpPlan(c);
      if (c.level === 2) assert.ok(plan.needs.sub && plan.needs.sub.length >= 1, cls + ": subclass asked for at 3");
      const before = c; c = up(c).ch;
      assert.strictEqual(c.level, before.level + 1); assert.ok(c.hp.max > before.hp.max, cls + " HP grows");
      assert.strictEqual(c.hitDice.reduce((a, h) => a + h.total, 0), c.level, cls + " hit dice follow level");
      assert.deepStrictEqual(P.sanitizeCharacter(JSON.parse(JSON.stringify(c))), c, cls + " survives a save at " + c.level);
    }
    assert.ok(!P.levelUp(c, {}).ok, "nothing past 20");
  });
  const f = P.levelUp(P.sanitizeCharacter({ name: "F", cls: "Fighter 5", level: 5 }), {});
  assert.ok(!f.ok && /Monk, Barbarian and Artificer/.test(f.msg), "other classes are not guessed");
});

t("level up fills the resource bar and the one-tap buttons; undo puts the sheet back exactly", () => {
  const m1 = fresh(...MONK), r = up(m1), m2 = r.ch;
  assert.strictEqual(bar(m2)["res-fp"], "FP 2/2"); assert.ok(bar(m2).hp);
  ["flurry", "patient-fp", "step-fp", "unarmed"].forEach((id) => act(m2, id));
  assert.deepStrictEqual(P.levelUndo(m2).ch, m1);
  let b = fresh(...BARB); b = up(b).ch; assert.strictEqual(bar(b)["res-rage"], "Rage 2/2"); act(b, "rage"); act(b, "reckless");
});

t("one tap spends, tap again undoes, End turn logs one line, rests bring resources back", () => {
  const m2 = up(fresh(...MONK)).ch;
  const s1 = P.tapAction(m2, P.blankTurn(), act(m2, "flurry"), {}); assert.ok(s1.ok, s1.msg);
  assert.strictEqual(P.findRes(s1.ch, "fp").used, 1); assert.strictEqual(s1.turn.bonus, true);
  assert.strictEqual(P.availability(s1.ch, s1.turn, act(s1.ch, "patient-fp")).ok, false, "bonus action greyed");
  const undo = P.tapAction(s1.ch, s1.turn, act(s1.ch, "flurry"), {}); assert.ok(undo.undone);
  assert.strictEqual(JSON.stringify(undo.ch), JSON.stringify(m2), "back exactly as before");
  const e = P.endTurn(s1.ch, s1.turn);
  assert.ok(/^Turn 1: Flurry of Blows \(1 FP\)\./.test(e.line), e.line); assert.deepStrictEqual(e.ch.turnLog, [e.line]);
  assert.strictEqual(P.findRes(P.shortRest(e.ch), "fp").used, 0, "Focus Points come back on a short rest");
  const hurt = Object.assign(P.sanitizeCharacter(JSON.parse(JSON.stringify(e.ch))), { hp: { cur: 3, max: e.ch.hp.max, temp: 0 } });
  assert.strictEqual(P.longRest(hurt).hp.cur, e.ch.hp.max, "long rest: full HP");
});

t("items: typed in with a count, a potion of healing becomes a one-tap button that counts down", () => {
  const m2 = up(fresh(...MONK)).ch;
  const c = P.addItemText(m2, "2 potions of healing").ch;
  const a = act(c, "item-potions-of-healing"); assert.deepStrictEqual(P.rollLines(c, a, null), ["Heal 2d4+2"]);
  const s = P.tapAction(c, P.blankTurn(), a, {}); assert.ok(s.ok);
  assert.strictEqual(s.ch.items.find((i) => /potion/i.test(i.name)).qty, 1);
});

t("sheet import: a character saved as .json comes back the same", () => {
  const c = up(up(fresh(...BARB)).ch).ch;
  const back = P.characterFromJsonText(JSON.stringify(c));
  assert.strictEqual(back.character.name, c.name); assert.strictEqual(back.character.level, 3); assert.deepStrictEqual(back.character.abilities, c.abilities);
  assert.throws(() => P.characterFromJsonText("not json"));
});

/* A stand-in for the browser's localStorage: same methods, kept in memory, optional size limit like a full phone. */
function fakeStorage(limit) {
  const m = new Map();
  return {
    get length() { return m.size; }, key: (i) => [...m.keys()][i] ?? null, getItem: (k) => (m.has(k) ? m.get(k) : null),
    setItem: (k, v) => { if (limit && String(v).length > limit) { const e = new Error("full"); e.name = "QuotaExceededError"; throw e; } m.set(k, String(v)); },
    removeItem: (k) => { m.delete(k); }, _m: m
  };
}

t("device saving: when there is no account storage the page opens the browser's storage, and a blocked storage is caught", () => {
  assert.ok(/else \{\s*var ls = deviceStorage\(window\);[\s\S]{0,300}STORE\.col = localCollection\(ls, LOCAL_PREFIX\); S\.save\.where = "device";/.test(html));
  assert.ok(/if \(db && user && uid\) \{ STORE\.col = db\.collection\(/.test(html), "account storage still wins when it is there");
  const ok = fakeStorage(); assert.strictEqual(P.deviceStorage({ localStorage: ok }), ok); assert.strictEqual(ok.length, 0, "the probe key is removed");
  assert.strictEqual(P.deviceStorage({ get localStorage() { throw new Error("SecurityError"); } }), null);
  assert.ok(/Saved on this device, in this browser\. Clearing the browser's data deletes your characters, so use Export/.test(html));
  assert.ok(/window\.addEventListener\("pagehide", flushAll\)/.test(html), "pending saves are written when the page closes");
});

const asyncTests = [];
function ta(name, fn) { asyncTests.push([name, fn]); }

ta("save, close, reopen: the character and its play state are still there; delete removes it; junk is skipped", async () => {
  const store = fakeStorage();
  let c = up(up(fresh(...MONK)).ch).ch;                       // a level 3 Monk
  const s = P.tapAction(c, P.blankTurn(), act(c, "flurry"), {}); c = P.endTurn(s.ch, s.turn).ch;   // FP spent, turn logged
  c.hp.cur = 9; c = P.addItemText(c, "2 potions of healing").ch;
  const doc = Object.assign(JSON.parse(JSON.stringify(c)), { kind: "character", id: "c_1" });
  await P.localCollection(store).doc("c_1").set(doc);
  await P.localCollection(store).doc("_prefs").set({ kind: "prefs", defaultId: "c_1" });
  store.setItem(P.LOCAL_PREFIX + "bad", "{not json"); store.setItem("someone-else", "{}");
  const snap = await P.localCollection(store).get();          // a new collection on the same storage = the page opened again
  assert.deepStrictEqual(snap.docs.map((d) => d.id).sort(), ["_prefs", "c_1"]);
  const back = P.sanitizeCharacter(snap.docs.find((d) => d.id === "c_1").data());
  assert.strictEqual(back.level, 3); assert.strictEqual(back.hp.cur, 9); assert.strictEqual(P.findRes(back, "fp").used, 1);
  assert.deepStrictEqual(back.turnLog, c.turnLog); assert.strictEqual(back.items.find((i) => /potion/i.test(i.name)).qty, 2);
  assert.deepStrictEqual(Object.assign(back, { id: undefined }), Object.assign(P.sanitizeCharacter(c), { id: undefined }));
  await P.localCollection(store).doc("c_1").delete();
  assert.deepStrictEqual((await P.localCollection(store).get()).docs.map((d) => d.id), ["_prefs"]);
});

ta("a full phone gives the quota_exceeded code the page already reports, not a crash", async () => {
  const err = await P.localCollection(fakeStorage(10)).doc("x").set({ big: "x".repeat(50) }).then(() => null, (e) => e);
  assert.strictEqual(err && err.code, "quota_exceeded");
});

ta("Export then Upload: the .json backup comes back as the same character (round trip)", async () => {
  let c = up(up(up(fresh(...BARB)).ch).ch).ch; c.hp.cur = 20; c.notes = "Owes the innkeeper 3 gp."; c.id = "c_9";
  const f = P.exportCharacter(c);
  assert.strictEqual(f.filename, "new-barbarian-level-4.json");
  const o = JSON.parse(f.text); assert.strictEqual(o.kind, "character"); assert.ok(!("id" in o) && !("example" in o));
  const r = P.characterFromJsonText(f.text);
  assert.deepStrictEqual(r.missing, []);
  const want = P.sanitizeCharacter(c); delete want.id;
  assert.deepStrictEqual(r.character, want);
  assert.ok(/btn\("export", "Export", id, "sm"\)/.test(html) && /el\.download = f\.filename/.test(html), "Roster has an Export button that downloads the file");
});

(async () => {
  for (const [name, fn] of asyncTests) { await fn(); n++; console.log("ok - " + name); }
  console.log(n + " clean-copy tests passed");
})().catch((e) => { console.error(e); process.exit(1); });
