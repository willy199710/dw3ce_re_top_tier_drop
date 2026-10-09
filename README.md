# DW3CE_TopTierDrops

**English** | [繁體中文](README.zh-TW.md)

A drop-quality mod for **Dynasty Warriors 3: Complete Edition Remastered** (`DW3CE_RE`, Steam).
Every weapon and skill item that drops on the battlefield is rolled at the **highest quality the vanilla game can produce**.

> - Built and tested against game version **1.0.2.0**.
> - **The game executable is never modified on disk.** Data changes ship as a standard UE mod pak; code changes are applied in memory by a proxy DLL.

---

## Features

### Dropped weapons

| | Vanilla | With this mod |
|---|---|---|
| Weapon rank | Random by stage difficulty (rank 0–2) | **Always rank 2** (the highest rank the drop table uses) |
| Number of skills | Random 1–5, ~67% of weapons get only 1 | **Always the maximum**: 5 for normal weapons, 3 for bodyguard weapons |
| Element | Only rank 2 has a 20% chance; element is random among Fire / Lightning / Slash / Wind | **Always present**; the element is selectable in the ini (default Slash 斬) |
| Skill values | Tier depends on stage difficulty, then a random roll inside the tier | **Always the vanilla maximum** (weapon tier 3, top of the tier, ×1.5 bonus) |

### Skill items dropped on the field

| | Vanilla | With this mod |
|---|---|---|
| Value | Tier depends on stage difficulty, then a random roll inside the tier | **Always the vanilla maximum** (item tier 4, top of the tier) |

### Items dropped by defeated enemies (meat buns, arrows, Attack Up, Defense Up)

| | Vanilla | With this mod |
|---|---|---|
| Size upgrade | Upgraded one size only if combo count ÷ 8 exceeds the current size (S→M needs 8 hits, M→L 16, L→LL 24) | **Always upgraded one size, regardless of combo** (items already at max size stay) |

Attack Up / Defense Up amounts per size: S +1, M +2, L +4, LL +8 (stat cap 150).

### Example values

| Skill (internal ID) | Field item | Skill on a weapon |
|---|---|---|
| `EQUIP_ITEM_SHINSOKUHU` (神速符) | 20 | 24 |
| `EQUIP_ITEM_BYAKKOGA` (白虎牙) | 25 | 30 |
| `EQUIP_ITEM_SEIRYUTAN` (青龍膽) | 75 | 90 |

In general: field item = `ValueRand × 5`, weapon skill = `ValueRand × 6`,
where `ValueRand` is each skill's value step in `DT_EquipItemBaseData`.

### Not changed

- Unique weapons (4th weapons etc.): unlock conditions and their fixed elements
- Which item an enemy drops (only its size is upgraded) and which skills can drop
- Weapons and items you already own — only new drops are affected

---

## Installation

Copy the **`DW3CE_RE` folder** inside `mods/DW3CE_TopTierDrops/` into the game's root folder (the one that contains `DW3CE_RE.exe`) and merge.

```
mods/DW3CE_TopTierDrops/DW3CE_RE   →   <Steam>/steamapps/common/DW3CE_RE/DW3CE_RE
```

This only **adds** 5 files; no vanilla file is replaced:

| File | Location | Purpose |
|---|---|---|
| `zDW3TopDrops_P.pak` / `.utoc` / `.ucas` | `DW3CE_RE/Content/Paks/~mods/` | Modified drop tables |
| `version.dll` | `DW3CE_RE/Binaries/Win64/` | In-memory patches to the weapon generation code |
| `dw3ce_re_top_tier_drop.ini` | `DW3CE_RE/Binaries/Win64/` | Toggles for each code patch |

> [!IMPORTANT]
> **All 5 files are required.** With the data pak alone, weapon skill values become the *lowest* tier
> (see [Why both parts are needed](#why-both-parts-are-needed)).

### Checking that it works

After launching the game, open `DW3CE_RE/Binaries/Win64/dw3ce_re_top_tier_drop.log`. It should contain an `[Element] = 3 (...)` line, 7 `applied` lines, and finally `done`.

### Updating from an older version
Older releases named the settings file `dw3ce_patch.ini`. If `dw3ce_re_top_tier_drop.ini` is missing, the new `version.dll` still reads the old file
(and notes it in the log), but it is recommended to switch to the new `dw3ce_re_top_tier_drop.ini` and delete the old `dw3ce_patch.ini` / `dw3ce_patch.log`.

## Uninstall

Delete the 5 files above (and `dw3ce_re_top_tier_drop.log` if present).
Steam's *Verify integrity of game files* does **not** remove extra mod files, so delete them manually.

## Configuration (`dw3ce_re_top_tier_drop.ini`)

Restart the game after editing.

**`Element` — element of dropped weapons**

| Value | Element |
|---|---|
| `0` | Random (vanilla: Fire / Lightning / Slash / Wind) |
| `1` | Fire |
| `2` | Lightning |
| `3` | Slash (default) |
| `4` | Wind |

**Toggles** — `1` = on, `0` = off

| Key | Effect |
|---|---|
| `MaxSkillRoll` | Weapon skills and field skill items always roll the top of their tier |
| `MaxGuardSkillRoll` | Bodyguard weapon skills always roll their maximum |
| `SkillTierFix` | **Required — do not disable.** Disabling it drops weapon skill values to the lowest tier |
| `GuardTierFix` | **Required — do not disable.** Disabling it drops bodyguard weapon skill values to the lowest tier |
| `ComboUpgradeAlways` | Items dropped by defeated enemies are always upgraded one size, ignoring the combo count (off = vanilla combo requirement) |

## After a game update

- If `dw3ce_re_top_tier_drop.log` reports `signature NOT found`, the game code has changed. That patch is **skipped automatically** — the DLL never writes to a location it cannot verify — and the mod needs updating.
- If the update changes the data tables, the pak must be rebuilt (see [Building from source](#building-from-source)).

---

## How it works

### Data pak
Three cooked DataTables are re-encoded and packed as an IoStore patch container (`_P` suffix, loaded from `Paks/~mods`):

| Table | Change |
|---|---|
| `DT_DropRandomTable` | `WeaponRandRank` → rank 2; `SkillItemRandRank` → `[0,0,0,0,100]`; `CorrectionRate` → 100; `CorrectionRatio` → 150 |
| `DT_SkillNumRandomTable` | `SkillRandBase` → `[100,100,100,100,100]` (index 0 = most skills) |
| `DT_WeaponRankData` | `AttributeProbability` → 100 for ranks 0–2 |

### Proxy DLL
The game imports `version.dll`, which is not in Windows' KnownDLLs, so a `version.dll` placed next to the executable is loaded first.
All 17 real exports are forwarded to `C:\Windows\System32\version.dll`. On load, the DLL verifies a 20-byte signature at each patch site
(expected RVA first, then a unique scan of `.text`) and applies same-length byte patches:

| Key | What it changes |
|---|---|
| `Element` | The hard-coded element table `{FIRE, THUNDER, ZAN, WIND}` (`ZAN` = Slash) is filled with the chosen element (`0` leaves it untouched) |
| `MaxSkillRoll` / `MaxGuardSkillRoll` | Removes the random roll inside a tier, always taking the maximum |
| `SkillTierFix` / `GuardTierFix` | When no `SkillItemRandRank` entry matches, fall back to tier 3 instead of tier 0 |
| `ComboUpgradeAlways` | In the enemy drop routine, removes the `combo / 8 > size` check so the one-size upgrade always happens |

Patches sharing a key are applied all-or-nothing.

### Why both parts are needed
The skill value function scans `SkillItemRandRank` for the first entry above a 0–99 roll — but **weapons only scan entries 0–3, while field items scan 0–4**.
With pure data edits you can give either weapons or items their maximum tier, never both:

| `SkillItemRandRank` | Weapons (scan 0–3) | Field items (scan 0–4) |
|---|---|---|
| `[0,0,0,100,100]` | tier 3 ✓ | tier 3 ✗ (max is 4) |
| `[0,0,0,0,100]` | no match → tier 0 ✗ | tier 4 ✓ |

The mod uses `[0,0,0,0,100]` and lets `SkillTierFix` change the weapon fallback from tier 0 to tier 3.

All analysis was done statically (reading the executable and disassembling it with capstone). The full development log — every step, the tools used,
and how each finding was verified — is in [`source/DW3CE_TopTierDrops/README.md`](source/DW3CE_TopTierDrops/README.md) (Traditional Chinese).

---

## Repository layout

```
├─ README.md / README.zh-TW.md
├─ mods/
│  └─ DW3CE_TopTierDrops/        Release files, laid out like the game folder
├─ source/
│  └─ DW3CE_TopTierDrops/
│     ├─ datatable/              build_mod.py + edited JSON of the three tables
│     ├─ dll/                    dw3ce_re_top_tier_drop.c + build.bat
│     └─ README.md               Development log (zh-TW)
└─ tools/
   ├─ DataTableTools/            usmap-free DataTable tooling (see below)
   ├─ retoc/                     Third-party IoStore tool (MIT)
   └─ game_data/                 Vanilla exports — NOT in the repo, regenerate locally
```

### DataTableTools
Small Python tools written for this mod. They read UE 5.6 reflection data **statically from the shipping executable**,
so no `.usmap` and no runtime injection is needed.

| Script | Purpose |
|---|---|
| `reflect.py` | Recover struct / enum / class schemas from UHT reflection params; resolve the import table |
| `dt2json.py` / `json2dt.py` | Cooked (unversioned) DataTable ⇄ JSON. 150 of 168 tables round-trip byte-for-byte |
| `list_utoc.py` | List every asset path in a `.utoc` directory index |
| `xref.py` | RIP-relative xrefs, call sites and function bounds (`.pdata`) for disassembly work |

## Building from source

Requirements: Windows, Python 3.10+ (`numpy` and `capstone` only needed for `xref.py`), Visual Studio 2019 Build Tools for the DLL, and a local copy of the game.

1. **Export vanilla data** into `tools/game_data/` (not shipped — it is game content). Steps are in [`tools/game_data/README.md`](tools/game_data/README.md).
2. **Data pak**
   ```bash
   cd source/DW3CE_TopTierDrops/datatable
   python build_mod.py              # build to ./build/out
   python build_mod.py --package    # also refresh mods/DW3CE_TopTierDrops
   python build_mod.py --install    # also copy into the game's Paks/~mods
   ```
   The game path defaults to `G:\SteamLibrary\steamapps\common\DW3CE_RE`; override it with the `DW3CE_GAME_DIR` environment variable.
   Builds are deterministic (`retoc --no-parallel`), and every written table is decoded again and compared before packing.
3. **DLL**: run `source/DW3CE_TopTierDrops/dll/build.bat`, then copy `version.dll` into `mods/DW3CE_TopTierDrops/DW3CE_RE/Binaries/Win64/`.

## Checksums (SHA-256)

| File | SHA-256 |
|---|---|
| `zDW3TopDrops_P.pak` | `75e7144577253917f6da7312ef5e585b12fb728226a22b0938323751a6b555cd` |
| `zDW3TopDrops_P.utoc` | `a78a6f7e50afaf6983a3db5b441ef9afbb19e0060d51d92846b9b6d2388404d2` |
| `zDW3TopDrops_P.ucas` | `b2f2967c3fc01102108ab3ce035bbf41c7f9a817f7f7ec7074e8e6938bfc15f7` |
| `version.dll` | `3a95ca9ee0f473cfddd883a212cd276b929e9af694633215e1724ac15d1c25b1` |
| Target `DW3CE_RE-Win64-Shipping.exe` 1.0.2.0 | `ca1a65a53242a7cf42493bd2006b8c555d87597387468e4b7a07c52d4eefe92e` |

## License

- Code and documentation written for this project (`source/`, `tools/DataTableTools/`, READMEs) are released under the [MIT License](LICENSE).
- `tools/retoc/` is third-party software under its own MIT license (see [`tools/retoc/LICENSE`](tools/retoc/LICENSE)).
- The game, its data, and content derived from it (the tables inside the mod pak and `edited_json`) belong to their respective rights holders and are **not** covered by the MIT license.

## Disclaimer

- This is an unofficial fan mod, not affiliated with or endorsed by the game's publisher or developer.
- Intended for single-player use only. Use at your own risk; back up your saves.
