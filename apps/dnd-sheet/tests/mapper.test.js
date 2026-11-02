// Runs the upload mapper from index.html on the field values read from a made-up filled-in 5e sheet
// (tests/fixtures/sample_sheet_fields.json, field names as on the official fillable sheet).
// Run: node tests/mapper.test.js
const assert = require("assert");
const fs = require("fs");
const path = require("path");
const { loadPure } = require("./load_pure");
const P = loadPure();

const fieldsPath = path.join(__dirname, "fixtures", "sample_sheet_fields.json");
const fields = JSON.parse(fs.readFileSync(fieldsPath, "utf8"));

let n = 0;
function t(name, fn) { fn(); n++; console.log("ok - " + name); }

const res = P.mapSheetFields(fields);
const c = res.character;

t("identity fields (incl. 'Race ' with a trailing space)", () => {
  assert.strictEqual(c.name, "Tarn Brightwater");
  assert.strictEqual(c.cls, "Paladin 5");
  assert.strictEqual(c.level, 5);
  assert.strictEqual(c.race, "Half-Elf");
  assert.strictEqual(c.background, "Soldier");
  assert.strictEqual(c.alignment, "Neutral Good");
});

t("ability scores", () => {
  assert.deepStrictEqual(c.abilities, { str: 16, dex: 10, con: 14, int: 8, wis: 12, cha: 17 });
});

t("combat numbers and HP", () => {
  assert.strictEqual(c.ac, 18); assert.strictEqual(c.speed, 30);
  assert.strictEqual(c.initBonus, 0);
  assert.deepStrictEqual(c.hp, { cur: 37, max: 44, temp: 5 });
  assert.deepStrictEqual(c.hitDice, [{ die: 10, total: 5, used: 0 }]);
});

t("save proficiencies from check boxes (WIS, CHA)", () => {
  assert.deepStrictEqual(c.saveProf, { str: false, dex: false, con: false, int: false, wis: true, cha: true });
});

t("skills: check box = proficient, number = mod + 2x prof makes expertise", () => {
  assert.strictEqual(c.skillProf.athletics, 1);
  assert.strictEqual(c.skillProf.intimidation, 1);
  assert.strictEqual(c.skillProf.persuasion, 2, "+9 = CHA 3 + 2 x 3");
  assert.strictEqual(c.skillProf.religion, 1, "box checked even though the number is odd");
  assert.strictEqual(c.skillProf.insight, 1);
  assert.strictEqual(c.skillProf.acrobatics, 0);
  assert.strictEqual(c.skillProf.stealth, 0);
});

t("derived numbers agree with the printed sheet", () => {
  assert.strictEqual(P.profBonus(c.level), 3);
  assert.strictEqual(P.skillTotal(c, "persuasion"), 9);
  assert.strictEqual(P.skillTotal(c, "athletics"), 6);
  assert.strictEqual(P.saveTotal(c, "wis"), 4);
  assert.strictEqual(P.saveTotal(c, "cha"), 6);
  assert.strictEqual(P.passivePerception(c), 11);
});

t("attacks, text blocks, money", () => {
  assert.strictEqual(c.attacks.length, 2);
  assert.deepStrictEqual(c.attacks[0], { name: "Longsword", bonus: "+6", damage: "1d8+3 slashing" });
  assert.strictEqual(c.attacks[1].name, "Javelin");
  assert.ok(/Chain mail/.test(c.equipment));
  assert.ok(/Elvish/.test(c.proficiencies));
  assert.ok(/Divine Smite/.test(c.features));
  assert.deepStrictEqual(c.currency, { cp: 3, sp: 14, ep: 0, gp: 120, pp: 1 });
});

t("spellcasting: ability, slots, spell names", () => {
  assert.strictEqual(c.spellAbility, "cha");
  assert.deepStrictEqual(c.slots[0], { max: 4, used: 1 });
  assert.deepStrictEqual(c.slots[1], { max: 2, used: 0 });
  assert.deepStrictEqual(c.spells.map((s) => s.name), ["Bless", "Cure Wounds"]);
  assert.ok(c.spells.every((s) => s.level === null), "levels are not guessed");
  assert.strictEqual(P.spellSaveDC(c), 8 + 3 + 3);
});

t("report lists what was found and nothing missing", () => {
  assert.ok(res.found.length >= 8, res.found.join("; "));
  assert.deepStrictEqual(res.missing, []);
});

t("result survives sanitizeCharacter unchanged", () => {
  const again = P.sanitizeCharacter(JSON.parse(JSON.stringify(c)));
  assert.deepStrictEqual(again, c);
});

t("tolerates different case, missing fields, junk and null values", () => {
  const lower = {}; for (const k of Object.keys(fields)) lower[k.toLowerCase().replace(/ /g, "_")] = fields[k];
  const r2 = P.mapSheetFields(lower);
  assert.strictEqual(r2.character.name, "Tarn Brightwater");
  assert.strictEqual(r2.character.race, "Half-Elf");
  assert.strictEqual(r2.character.abilities.cha, 17);
  const r3 = P.mapSheetFields({ CHARACTERNAME: "Only Name", str: "18", foo: null, bar: [1], baz: true });
  assert.strictEqual(r3.character.name, "Only Name");
  assert.strictEqual(r3.character.abilities.str, 18);
  assert.ok(r3.missing.includes("Hit points") && r3.missing.includes("Armor Class"));
  const r4 = P.mapSheetFields({}); assert.strictEqual(r4.found.length, 0);
  assert.doesNotThrow(() => P.mapSheetFields(null));
});

t("modifier-only sheets: score worked out and flagged; swapped score/mod boxes fixed", () => {
  const r = P.mapSheetFields({ STRmod: "+3", STR: "", DEX: "+2", DEXmod: "14" });
  assert.strictEqual(r.character.abilities.str, 16);
  assert.ok(r.approx.includes("STR"));
  assert.strictEqual(r.character.abilities.dex, 14, "values in the wrong boxes are swapped back");
});

t("pdf.js style values: booleans and arrays", () => {
  const r = P.mapSheetFields({ "Check Box 21": "Yes", "Check Box 22": "Off", Inspiration: true, STR: ["12"] });
  assert.strictEqual(r.character.saveProf.wis, true);
  assert.strictEqual(r.character.saveProf.cha, false);
  assert.strictEqual(r.character.inspiration, true);
  assert.strictEqual(r.character.abilities.str, 12);
});

console.log("\n" + n + " test groups passed");
