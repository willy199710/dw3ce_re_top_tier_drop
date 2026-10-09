# game_data — 原版遊戲資料匯出

從 **DW3CE_RE 1.0.2.0** 匯出的原版資料，作為建置 mod 與查資料的基準。

> 這是遊戲本身的內容，只供個人使用。分享 mod 時請不要一併散布這個資料夾。

## 內容

| 路徑 | 說明 |
|---|---|
| `vanilla_json\` | 150 張 `DataAsset/DT_*` 的 JSON（由 `dt2json.py` 產生），**未修改** |
| `legacy\` | 168 張表的 legacy 格式 `.uasset`／`.uexp`（由 `retoc to-legacy` 產生），以及 `scriptobjects.bin` |
| `utoc_filelist.txt` | `DW3CE_RE-Windows.utoc` 內全部 142,487 個資源路徑（由 `list_utoc.py` 產生） |

`source\DW3CE_TopTierDrops\datatable\build_mod.py` 以 `vanilla_json` 為修改基礎，以 `legacy` 提供 name map、檔頭，以及打包所需的 `scriptobjects.bin`。

## 值得一看的表

| 表 | 內容 |
|---|---|
| `DT_EquipItemBaseData` | 道具／技能：`Type`（Blue/Red）、`RandHit`（掉落累積權重）、`ValueRand`（數值級距寬度）、`WeaponAddProbability` 等 |
| `DT_GuardEquipItemBaseData` | 護衛兵道具：`RandomSeed[4]` 為各級距的亂數上限 |
| `DT_DropRandomTable` | 依關卡等級的武器等級、技能級距分布與加成倍率 |
| `DT_SkillNumRandomTable` | 武器技能數量 |
| `DT_WeaponRankData` | 各武器等級的屬性機率、紅技能機率 |
| `DT_WeaponBaseData` | 255 把武器的攻擊範圍、`Power`、`Attribute`（`EWeaponAttrFlag` bit flags；專屬武器的屬性寫死在這裡） |
| `DT_ItemTypeData` | 場上回復道具（肉包、箭矢等）的模型與 GameplayEffect |
| `DT_ItemData` | 只有 `IsAutoGet`，**不是**道具數值表 |

## 遊戲更新後重新匯出

```bash
cd E:\DE3MOD\tools
retoc\retoc.exe to-legacy --no-shaders -f DataAsset/DT_ "<遊戲>\DW3CE_RE\Content\Paks" tmp
# 把 tmp\DW3CE_RE\Content\DataAsset\* 與 tmp\scriptobjects.bin 放到 game_data\legacy\
# 對每張表執行： python DataTableTools\dt2json.py game_data\legacy\DT_xxx
# 產生的 .json 移到 game_data\vanilla_json\
python DataTableTools\list_utoc.py "<遊戲>\DW3CE_RE\Content\Paks\DW3CE_RE-Windows.utoc" > game_data\utoc_filelist.txt
```

更新後也要先用 `DataTableTools` 確認 round-trip 仍然逐位元組一致，再重建 mod。
