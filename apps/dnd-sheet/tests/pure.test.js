// Unit tests for the pure functions inside index.html.  Run: node tests/pure.test.js
const assert = require("assert");
const { loadPure } = require("./load_pure");
const P = loadPure();

let n = 0;
function t(name, fn) { fn(); n++; console.log("ok - " + name); }

function sheet(over) {
  const c = P.blankCharacter();
  Object.assign(c, over || {});
  return c;
}

t("ability modifiers for 1, 10, 11, 20", () => {
  assert.strictEqual(P.abilityMod(1), -5);
  assert.strictEqual(P.abilityMod(10), 0);
  assert.strictEqual(P.abilityMod(11), 0);
  assert.strictEqual(P.abilityMod(20), 5);
});

t("proficiency bonus at levels 1, 5, 9, 13, 17", () => {
  assert.deepStrictEqual([1, 5, 9, 13, 17].map(P.profBonus), [2, 3, 4, 5, 6]);
  assert.strictEqual(P.profBonus(4), 2);
  assert.strictEqual(P.profBonus(20), 6);
});

t("save and skill totals, proficiency and expertise doubling", () => {
  const c = sheet({ level: 5 }); // prof +3
  c.abilities.wis = 16; // +3
  c.abilities.dex = 14; // +2
  c.saveProf.wis = true;
  assert.strictEqual(P.saveTotal(c, "wis"), 6);
  assert.strictEqual(P.saveTotal(c, "dex"), 2);
  c.skillProf.insight = 0;
  assert.strictEqual(P.skillTotal(c, "insight"), 3);
  c.skillProf.insight = 1;
  assert.strictEqual(P.skillTotal(c, "insight"), 6);
  c.skillProf.insight = 2; // expertise: mod + 2 * prof
  assert.strictEqual(P.skillTotal(c, "insight"), 9);
  c.skillProf.stealth = 2;
  assert.strictEqual(P.skillTotal(c, "stealth"), 2 + 6);
});

t("passive Perception and initiative", () => {
  const c = sheet({ level: 1 });
  c.abilities.wis = 14; c.abilities.dex = 15;
  assert.strictEqual(P.passivePerception(c), 12);
  c.skillProf.perception = 1;
  assert.strictEqual(P.passivePerception(c), 14);
  assert.strictEqual(P.initiative(c), 2);
  c.initBonus = 5;
  assert.strictEqual(P.initiative(c), 7);
});

t("temp HP absorbs damage first", () => {
  const c = sheet(); c.hp = { cur: 20, max: 30, temp: 8 };
  const a = P.applyDamage(c, 5);
  assert.deepStrictEqual(a.hp, { cur: 20, max: 30, temp: 3 });
  const b = P.applyDamage(c, 12);
  assert.deepStrictEqual(b.hp, { cur: 16, max: 30, temp: 0 });
  assert.strictEqual(c.hp.temp, 8, "input not mutated");
  const info = P.damageInfo(c, 12);
  assert.strictEqual(info.absorbed, 8); assert.strictEqual(info.lost, 4);
});

t("HP clamps at 0 on damage and at max on healing", () => {
  const c = sheet(); c.hp = { cur: 5, max: 30, temp: 0 };
  assert.strictEqual(P.applyDamage(c, 999).hp.cur, 0);
  assert.strictEqual(P.applyHeal(c, 999).hp.cur, 30);
  assert.strictEqual(P.applyDamage(c, -4).hp.cur, 5, "negative damage ignored");
  assert.strictEqual(P.applyTempHp(P.applyTempHp(c, 6), 4).hp.temp, 6, "temp HP keeps the higher");
});

t("damage at 0 HP adds one failed death save (capped at 3)", () => {
  const c = sheet(); c.hp = { cur: 0, max: 30, temp: 0 };
  const a = P.applyDamage(c, 4);
  assert.deepStrictEqual(a.deathSaves, { s: 0, f: 1 });
  assert.strictEqual(a.hp.cur, 0);
  const b = P.applyDamage(P.applyDamage(P.applyDamage(P.applyDamage(c, 1), 1), 1), 1);
  assert.strictEqual(b.deathSaves.f, 3);
  assert.deepStrictEqual(P.applyDamage(c, 0).deathSaves, { s: 0, f: 0 }, "zero damage adds none");
  const up = sheet(); up.hp = { cur: 5, max: 30, temp: 0 };
  assert.deepStrictEqual(P.applyDamage(up, 9).deathSaves, { s: 0, f: 0 }, "dropping to 0 is not a failure");
});

t("death saves reset when healed above 0", () => {
  const c = sheet(); c.hp = { cur: 0, max: 30, temp: 0 };
  let d = P.setDeathSave(P.setDeathSave(c, "s", 2), "f", 1);
  assert.deepStrictEqual(d.deathSaves, { s: 2, f: 1 });
  assert.deepStrictEqual(P.applyHeal(d, 0).deathSaves, { s: 2, f: 1 }, "0 healing leaves them");
  assert.deepStrictEqual(P.applyHeal(d, 1).deathSaves, { s: 0, f: 0 });
  const e = P.normalizeHp(Object.assign(P.blankCharacter(), { hp: { cur: 7, max: 9, temp: 0 }, deathSaves: { s: 1, f: 2 } }), false);
  assert.deepStrictEqual(e.deathSaves, { s: 0, f: 0 });
});

t("spell slot spend and restore, and pact slots", () => {
  const c = sheet(); c.slots[0] = { max: 2, used: 0 };
  let a = P.spendSlot(P.spendSlot(c, 1), 1);
  assert.strictEqual(a.slots[0].used, 2);
  assert.strictEqual(P.spendSlot(a, 1).slots[0].used, 2, "cannot overspend");
  assert.strictEqual(P.restoreSlot(a, 1).slots[0].used, 1);
  assert.strictEqual(P.restoreSlot(c, 1).slots[0].used, 0, "cannot go below 0");
  c.pact = { max: 2, used: 0, level: 3 };
  const p = P.spendPact(P.spendPact(c));
  assert.strictEqual(p.pact.used, 2);
  assert.strictEqual(P.spendPact(p).pact.used, 2);
  assert.strictEqual(P.restorePact(p).pact.used, 1);
});

function rested() {
  const c = sheet({ level: 6 });
  c.hp = { cur: 4, max: 40, temp: 5 };
  c.deathSaves = { s: 1, f: 1 };
  c.hitDice = [{ die: 8, total: 6, used: 6 }];
  c.slots[0] = { max: 4, used: 3 }; c.slots[2] = { max: 2, used: 2 };
  c.pact = { max: 2, used: 2, level: 3 };
  c.resources = [
    { name: "Channel Divinity", max: 2, used: 2, reset: "short" },
    { name: "Rage", max: 3, used: 3, reset: "long" }
  ];
  c.exhaustion = 2; c.concentration = { on: true, spell: "Bless" };
  return c;
}

t("short rest restores only short-rest resources and pact slots", () => {
  const s = P.shortRest(rested());
  assert.strictEqual(s.resources[0].used, 0);
  assert.strictEqual(s.resources[1].used, 3);
  assert.strictEqual(s.pact.used, 0);
  assert.strictEqual(s.slots[0].used, 3);
  assert.strictEqual(s.slots[2].used, 2);
  assert.strictEqual(s.hp.cur, 4);
  assert.strictEqual(s.hitDice[0].used, 6);
});

t("long rest restores HP, all slots, all resources; an explicit 2014 sheet gets half the hit dice (min 1), the default 2024 gets all", () => {
  const old14 = () => Object.assign(rested(), { edition: "2014" });
  const def = rested(); assert.strictEqual(def.edition, "2024", "blank characters default to the 2024 rules"); assert.strictEqual(P.longRest(def).hitDice[0].used, 0);
  const l = P.longRest(old14());
  assert.strictEqual(l.hp.cur, 40); assert.strictEqual(l.hp.temp, 0);
  assert.deepStrictEqual(l.deathSaves, { s: 0, f: 0 });
  assert.ok(l.slots.every((s) => s.used === 0));
  assert.strictEqual(l.pact.used, 0);
  assert.ok(l.resources.every((r) => r.used === 0));
  assert.strictEqual(l.hitDice[0].used, 3, "6 dice: back 3");
  assert.strictEqual(l.exhaustion, 1);
  assert.strictEqual(l.concentration.on, false);
  const one = old14(); one.hitDice = [{ die: 10, total: 1, used: 1 }];
  assert.strictEqual(P.longRest(one).hitDice[0].used, 0, "1 die: min 1 back");
  const three = old14(); three.hitDice = [{ die: 8, total: 3, used: 3 }];
  assert.strictEqual(P.longRest(three).hitDice[0].used, 2, "3 dice: floor(3/2)=1 back");
  const multi = old14(); multi.hitDice = [{ die: 8, total: 2, used: 2 }, { die: 10, total: 2, used: 2 }];
  const m = P.longRest(multi); // budget 2, largest die first
  assert.strictEqual(m.hitDice[1].used, 0); assert.strictEqual(m.hitDice[0].used, 2);
});

t("sanitizeCharacter fills defaults and clamps junk", () => {
  const c = P.sanitizeCharacter({ name: "X", level: 99, abilities: { str: "abc", dex: 40 }, hp: { cur: 50, max: 10 }, slots: "nope", spells: [{ name: "" }, { name: "Shield", level: 12 }] });
  assert.strictEqual(c.level, 20);
  assert.strictEqual(c.abilities.str, 10); assert.strictEqual(c.abilities.dex, 30);
  assert.strictEqual(c.hp.cur, 10);
  assert.strictEqual(c.slots.length, 9);
  assert.strictEqual(c.spells.length, 1); assert.strictEqual(c.spells[0].level, 9);
  assert.doesNotThrow(() => P.sanitizeCharacter(null));
});

t("exampleCharacter is flagged as an example and is coherent", () => {
  const e = P.exampleCharacter();
  assert.strictEqual(e.example, true);
  assert.ok(/^Example/.test(e.name));
  assert.ok(e.hp.cur < e.hp.max);
  assert.strictEqual(P.spellSaveDC(e), 8 + 3 + 3);
});

t("characterFromExtracted validates Claude's reply", () => {
  const good = P.characterFromExtracted({
    name: "Tor", classLevel: "Fighter 3", race: "Human", abilities: { str: 16, dex: 12, con: 14, int: 8, wis: 10, cha: 10 },
    saveProficiencies: ["str", "Constitution"], skills: { athletics: 1, "Sleight of Hand": 2, bogus: 1 }, ac: 17, initiative: 1, speed: 30,
    hpMax: 28, hpCurrent: null, hitDice: "3d10", attacks: [{ name: "Longsword", bonus: "+5", damage: "1d8+3" }], slots: { "1": 2 }, spells: [{ name: "Shield", level: 1 }]
  });
  const c = good.character;
  assert.strictEqual(c.level, 3); assert.strictEqual(c.hp.cur, 28);
  assert.ok(c.saveProf.str && c.saveProf.con && !c.saveProf.dex);
  assert.strictEqual(c.skillProf.athletics, 1); assert.strictEqual(c.skillProf.sleightOfHand, 2);
  assert.strictEqual(c.initBonus, 0); // dex 12 gives +1, printed +1, so no extra bonus
  assert.strictEqual(c.hitDice[0].die, 10); assert.strictEqual(c.slots[0].max, 2);
  assert.throws(() => P.characterFromExtracted("nope"));
  assert.throws(() => P.characterFromExtracted({ foo: 1 }));
  assert.ok(P.buildReadPrompt("text", "abc").includes("SHEET TEXT START"));
});

console.log("\n" + n + " test groups passed");
