# Build the zDW3TopDrops_P data mod from the vanilla JSON exports.
# usage: python build_mod.py [--package] [--install]
#   (no flag)  build to ./build/out only
#   --package  also refresh the release copy in E:\DE3MOD\mods\DW3CE_TopTierDrops\DW3CE_RE\Content\Paks\~mods
#   --install  also copy into the game's Content\Paks\~mods
import json, os, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
DE3MOD = os.path.join(HERE, '..', '..', '..')
TOOLS = os.path.join(DE3MOD, 'tools')
PACKAGE_MODS = os.path.join(DE3MOD, 'mods', 'DW3CE_TopTierDrops', 'DW3CE_RE', 'Content', 'Paks', '~mods')
sys.path.insert(0, os.path.join(TOOLS, 'DataTableTools'))
import json2dt, dt2json, reflect

GAME_PAKS = os.path.join(reflect.GAME_DIR, 'DW3CE_RE', 'Content', 'Paks')
RETOC = os.path.join(TOOLS, 'retoc', 'retoc.exe')
VANILLA_JSON = os.path.join(TOOLS, 'game_data', 'vanilla_json')
LEGACY = os.path.join(TOOLS, 'game_data', 'legacy')
SCRIPTOBJ = os.path.join(LEGACY, 'scriptobjects.bin')
NAME = 'zDW3TopDrops_P'

CORRECTION_RATIO = 150   # vanilla value used by StageRank_10..13

def edit_drop(rows):
    for r in rows.values():
        if any(r['WeaponRandRank']):             # StageRank_14/15 never drop weapons -> keep
            r['WeaponRandRank'] = [0, 0, 100, 0, 0]
        # items scan entries 0..4 -> tier 4 (item max). Weapons/guard weapons scan only 0..3, find no match
        # and fall back to tier 3 (weapon max) -- REQUIRES SkillTierFix/GuardTierFix in version.dll.
        r['SkillItemRandRank'] = [0, 0, 0, 0, 100]
        r['CorrectionRate'] = 100                # always apply the correction multiplier
        r['CorrectionRatio'] = CORRECTION_RATIO

def edit_skillnum(rows):
    for r in rows.values():
        r['SkillRandBase'] = [100, 100, 100, 100, 100]   # index 0 = most skills

def edit_weaponrank(rows):
    for k in ('WeaponRank_0', 'WeaponRank_1', 'WeaponRank_2'):
        rows[k]['AttributeProbability'] = 100

EDITS = {
    'DT_DropRandomTable': edit_drop,
    'DT_SkillNumRandomTable': edit_skillnum,
    'DT_WeaponRankData': edit_weaponrank,
}

def main():
    src = os.path.join(HERE, 'build', 'src')
    out = os.path.join(HERE, 'build', 'out')
    shutil.rmtree(src, ignore_errors=True); shutil.rmtree(out, ignore_errors=True)
    da = os.path.join(src, 'DW3CE_RE', 'Content', 'DataAsset')
    os.makedirs(da); os.makedirs(out)
    shutil.copyfile(SCRIPTOBJ, os.path.join(src, 'scriptobjects.bin'))
    for t, fn in EDITS.items():
        js = json.load(open(os.path.join(VANILLA_JSON, t + '.json'), encoding='utf-8'))
        fn(js['Rows'])
        json.dump(js, open(os.path.join(out, t + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        orig = os.path.join(LEGACY, t)
        new = json2dt.encode(orig, js)
        old = open(orig + '.uexp', 'rb').read()
        ua = bytearray(open(orig + '.uasset', 'rb').read())
        if len(new) != len(old):
            ua = json2dt.patch_sizes(ua, len(old), len(new))
        open(os.path.join(da, t + '.uasset'), 'wb').write(ua)
        open(os.path.join(da, t + '.uexp'), 'wb').write(new)
        # decode what we wrote and compare with the intended JSON
        _, _, rows = dt2json.decode(os.path.join(da, t))
        assert rows == js['Rows'], t
        print(f'{t}: {len(old)} -> {len(new)} bytes, verified')
    subprocess.run([RETOC, 'to-zen', '--no-parallel', '--version', 'UE5_6', src, os.path.join(out, NAME + '.utoc')], check=True)
    targets = []
    if '--package' in sys.argv: targets.append(PACKAGE_MODS)
    if '--install' in sys.argv: targets.append(os.path.join(GAME_PAKS, '~mods'))
    for mods in targets:
        os.makedirs(mods, exist_ok=True)
        for ext in ('pak', 'utoc', 'ucas'):
            shutil.copyfile(os.path.join(out, f'{NAME}.{ext}'), os.path.join(mods, f'{NAME}.{ext}'))
        print('copied to', os.path.abspath(mods))

if __name__ == '__main__':
    main()
