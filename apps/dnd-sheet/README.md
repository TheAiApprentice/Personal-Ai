# Table Sheet: a D&D 5e character sheet for your phone

One HTML file that keeps your character during a game, so nobody at the table does sheet math. You roll your own dice; the app never rolls.
It is built for the 2024 rules (a character file that says `"edition": "2014"` keeps the older rest and exhaustion rules).

This copy has no characters built in. On first open you see a made-up example character and the hint
**"Create your character or import a sheet."** Keep the example as a starting point, clear it to a blank sheet, or upload your own.

## What it tracks

- **One-tap play.** Your actions sit as buttons at the top of the Play tab. Tap one and it is done: its cost is spent, the numbers
  to roll are shown on the button with your bonuses already added, actions you can no longer take this turn go grey, and tapping
  it again undoes it.
- **Resource bar.** HP, temp HP when you have some, class resources (Focus Points, Rage and the like), spell slots and hit dice, always on top.
- **End turn, rests and items.** End turn writes one short line to a turn log and starts a clean turn. Short and long rests bring
  back what the rules say, with hit dice spending on a short rest. Type items in plain words (`2 potions of healing`): a count goes up
  or down, and a healing potion becomes a one-tap button.
- **Level up.** One tap takes a character to the next level from the class table: hit points (average or the number you rolled),
  features, resources, spell slots, subclass at level 3, Ability Score Improvements and the Epic Boon. One step of undo.
  Classes it knows: all 12 of the 2024 Player's Handbook, **Barbarian, Bard, Cleric, Druid, Fighter, Monk, Paladin, Ranger, Rogue,
  Sorcerer, Warlock, Wizard**, plus the **Artificer** (2024-compatible). Each comes with one subclass the app fills in for you; pick
  "Other" to type a different one (its features are then not added automatically). Spell slots follow the full- and half-caster
  tables, the Warlock gets Pact Magic, and class resources (Rage, Focus Points, Sneak Attack dice, Second Wind and Action Surge,
  Channel Divinity, Bardic Inspiration, Wild Shape, Sorcery Points, Lay on Hands and the rest) land on the resource bar and as
  one-tap buttons. A homebrew or third-party class still works; change its level by hand on the Sheet tab.
- **Everything else on a sheet.** Abilities, saves, skills (with expertise), AC, initiative, speed, conditions, exhaustion, death saves,
  spells and slots, inventory, money, notes.
- **Sheet import** (Roster tab, "Upload a sheet"): a character `.json` file in this app's format, or a PDF with form fields such as the
  official fillable 5e sheet, is read on the phone itself. You see what was read and confirm before anything changes.

## Open it on a phone

The app is the single file `index.html`. Pick one:

1. **From a link (any phone).** Put `index.html` on any static web host and open the link in Safari or Chrome.
   Then use **Share > Add to Home Screen** (iPhone) or **menu > Add to Home screen** (Android) so it opens like an app.
2. **As a Claude artifact.** Give `index.html` to Claude, ask it to publish the page as an artifact, and open that link on the phone.
   This is the one place where reading photos of a sheet works (see below).
3. **As a local file (Android).** Copy `index.html` to the phone and open it in Chrome.

Once the page has loaded it runs without an internet connection, with two exceptions that it loads from the web:

- **Fonts** from Google Fonts (`fonts.googleapis.com`). Offline it falls back to the phone's own fonts; nothing breaks.
- **PDF import** uses pdf.js 3.11.174 from `cdnjs.cloudflare.com`. Without a connection, PDF import says so; `.json` import still works.

## Saving and backups

Your characters and their play state (HP, spent resources and slots, hit dice, items, money, notes, the turn log) save
by themselves a moment after each change, and when the page is closed.

- **On a phone (options 1 and 3):** saved in the browser's own storage on that device. No account and no internet needed;
  it survives closing the page and restarting the phone. The Roster tab says "Saved on this device, in this browser."
- **iPhone:** add the page to the Home Screen and open it from there. Safari can clear the storage of a website you
  haven't opened for about a week; a Home Screen app is not cleared that way.
- **As a Claude artifact (option 2):** saved in the artifact's private storage instead.
- **Clearing the browser's data (or "website data") for the page deletes your characters.** So does private browsing,
  which keeps nothing; the Roster tab then says "Saving is off".
- **Back up with Export.** Roster tab > Export next to a character downloads it as a `.json` file. Upload a sheet reads
  it back, on the same phone or a new one. Use it to keep a backup or to move a character.

Reading a photo, a scan or a flat PDF (no form fields) needs the Claude artifact; elsewhere use a fillable PDF or a `.json` file.

## Rules content and licence

- The app's code is under the MIT licence of this repository (see [`LICENSE`](../../LICENSE)).
- **SRD 5.2.** This work includes material from the System Reference Document 5.2 ("SRD 5.2") by Wizards of the Coast LLC,
  available at https://www.dndbeyond.com/srd. The SRD 5.2 is licensed under the Creative Commons Attribution 4.0 International
  License, available at https://creativecommons.org/licenses/by/4.0/legalcode. The core features and numbers of the twelve
  Player's Handbook classes follow the SRD 5.2, and so do the subclasses College of Lore, Life Domain, Circle of the Land,
  Champion, Warrior of the Open Hand, Oath of Devotion, Hunter, Thief, Draconic Sorcery, Fiend Patron and Evoker; the
  descriptions are short paraphrases.
- **Not in the SRD.** Path of the Wild Heart (Player's Handbook 2024) and the Artificer are not SRD content. For those, the app keeps
  only feature names, levels and the numbers it needs, with one-line descriptions in our own words. You need your own book for the
  full text.
- **[check book].** Any number that could not be confirmed is marked `[check book]` on the sheet. Check it against your book.
- This is an unofficial fan tool, not affiliated with or endorsed by Wizards of the Coast. Dungeons & Dragons and D&D are trademarks
  of Wizards of the Coast LLC.

## Tests

Node.js 18 or newer, no packages:

    node tests/run_all.js

Expected: `all 4 test files passed` (page structure, the rules maths, the fillable-PDF field reader, and this clean copy:
no built-in characters, the first-run hint, the licence note, level up, one-tap play, end turn, rests, items and `.json`
import on brand-new characters, saving on the device and reopening, a full storage, and the Export/Upload round trip).
