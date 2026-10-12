# DW3CE_TopTierDrops — 真・三國無雙 3 Complete Edition Remastered 掉落強化 Mod

[English](README.md) | **繁體中文**

讓戰場上掉落的武器與道具，全部達到**原版遊戲能出現的最高品質**。

> 對應遊戲版本：1.0.2.0（Steam）。已實測通過。
> 遊戲執行檔**完全不修改**：資料用 mod 包覆蓋，程式邏輯在記憶體中修改。

---

## 這個 mod 做了什麼

### 掉落武器
| 項目 | 原版 | 套用後 |
|---|---|---|
| 武器等級 | 依關卡難度隨機（等級 0~2） | **固定為最高的等級 2** |
| 技能數量 | 隨機 1~5 個，約 67% 只有 1 個 | **固定為上限**：一般武器 5 個、護衛兵武器 3 個 |
| 屬性 | 只有等級 2 有 20% 機率帶屬性，種類在炎／雷／斬／風中隨機 | **每把都有**，種類可在 ini 指定（預設「斬」） |
| 紅技能 | 只有等級 2 有 10% 機率 | **每把都有**（佔用最後一格技能，所以是 4 藍 + 1 紅） |
| 技能數值 | 依關卡難度落在不同級距，級距內再隨機 | **固定為原版上限**（武器最高級距 3、級距內最大值、再 ×1.5 加成） |

### 戰場上掉落的技能道具
| 項目 | 原版 | 套用後 |
|---|---|---|
| 數值 | 依關卡難度落在不同級距，級距內再隨機 | **固定為原版上限**（道具最高級距 4、級距內最大值） |

一般技能道具和護衛兵技能道具都適用。

### 擊倒敵人掉落的道具（肉包、箭矢、攻擊力＋、防禦力＋）
| 項目 | 原版 | 套用後 |
|---|---|---|
| 尺寸升級 | 連擊數 ÷ 8 大於目前尺寸才升一級（S→M 需 8 連擊、M→L 需 16、L→LL 需 24） | **不看連擊數，一律升一級**（已是最大尺寸則不變） |

攻擊力＋／防禦力＋ 每種尺寸的增加量：S +1、M +2、L +4、LL +8（累計上限 150）。

### 數值範例

| 技能 | 場上掉落的道具 | 武器上的技能 |
|---|---|---|
| 神速符 | 20 | 24 |
| 白虎牙 | 25 | 30 |
| 青龍膽 | 75 | 90 |

其他技能的上限：道具 = `ValueRand × 5`，武器技能 = `ValueRand × 6`（`ValueRand` 是每個技能在遊戲資料裡的數值單位）。

### 沒有改的部分
- 專屬武器（第四武器等）的取得條件與屬性
- 敵人會掉哪一種道具（只升級尺寸，不改種類）、掉落的技能種類
- 已經拿到的武器與道具（只影響之後新掉落的）

---

## 安裝

把 `mods\DW3CE_TopTierDrops\` 裡面的 **`DW3CE_RE` 資料夾**，複製到遊戲根目錄（有 `DW3CE_RE.exe` 的那一層），合併覆蓋。

```
mods\DW3CE_TopTierDrops\DW3CE_RE   →   ...\steamapps\common\DW3CE_RE\DW3CE_RE
```

只會新增以下 5 個檔案，不會取代任何原版檔案：

| 檔案 | 位置 | 作用 |
|---|---|---|
| `zDW3TopDrops_P.pak` / `.utoc` / `.ucas` | `DW3CE_RE\Content\Paks\~mods\` | 修改後的掉落資料表 |
| `version.dll` | `DW3CE_RE\Binaries\Win64\` | 在記憶體中修改武器生成邏輯 |
| `dw3ce_re_top_tier_drop.ini` | `DW3CE_RE\Binaries\Win64\` | 各項程式修改的開關 |

**5 個檔案必須一起使用。** 只放資料表的話，武器技能數值反而會變成最低。

### 確認是否生效
啟動遊戲後，打開 `DW3CE_RE\Binaries\Win64\dw3ce_re_top_tier_drop.log`，正常內容應有一行 `[Element] = 3 (...)`、8 行 `applied`，最後一行 `done`。

### 從舊版更新
舊版的設定檔叫 `dw3ce_patch.ini`。新版的 `version.dll` 找不到 `dw3ce_re_top_tier_drop.ini` 時，仍會讀取舊檔名（log 會提醒改名），
但建議直接改用新版的 `dw3ce_re_top_tier_drop.ini`，並刪除舊的 `dw3ce_patch.ini`、`dw3ce_patch.log`。

### 使用 Ultimate ASI Loader（與其他使用 `version.dll` 的模組共存）
遊戲只會載入一個 `version.dll`，所以本模組的 `version.dll` 無法和其他同樣使用 `version.dll` 的模組同時安裝。
這時請改用 ASI 版，交給 [Ultimate ASI Loader](https://github.com/ThirteenAG/Ultimate-ASI-Loader) 載入：

1. 在 `DW3CE_RE\Binaries\Win64\` 安裝 Ultimate ASI Loader（x64），檔名用 `version.dll`；如果其他模組用的本來就是 Ultimate ASI Loader，沿用即可。
2. 把 **`mods\DW3CE_TopTierDrops_ASI\`** 裡的 `DW3CE_RE` 資料夾複製到遊戲根目錄，合併覆蓋。
   內容是同樣的 mod 包、`dw3ce_re_top_tier_drop.asi`（跟 `version.dll` 是同一個檔案，只是改了副檔名），以及 `dw3ce_re_top_tier_drop.ini`，**不含** `version.dll`。
3. `dw3ce_re_top_tier_drop.ini` 要放在 `.asi` 旁邊。log 也會寫在同一個位置，第一行會是 `loaded as ...\dw3ce_re_top_tier_drop.asi`。

不要把本模組的 `version.dll` 和 `.asi` 同時安裝，擇一即可。

### 變體版：武器掉落等級維持原版（`DW3CE_VanillaWeaponDrops`）
適合想讓武器等級像原版一樣依關卡難度變化，但其他項目仍維持最高品質的玩家。
變體版只有一份替換用的 mod 包，**檔名和一般版相同**，所以是取代一般版的 mod 包，不是額外新增：

| 項目 | 一般版（`DW3CE_TopTierDrops`） | 變體版（`DW3CE_VanillaWeaponDrops`） |
|---|---|---|
| 武器等級 | 固定為等級 2 | 原版：依關卡難度隨機（等級 0~2） |
| 屬性、紅技能、技能數量、技能數值、場上道具、敵人掉落道具 | 最高品質 | 與一般版相同 |

1. 先安裝一般版（`version.dll` 或 `.asi`，以及 `dw3ce_re_top_tier_drop.ini` 仍然必要）。
2. 把 **`mods\DW3CE_VanillaWeaponDrops\`** 裡的 `DW3CE_RE` 資料夾複製到遊戲根目錄，**覆蓋** `DW3CE_RE\Content\Paks\~mods\` 裡的 3 個 `zDW3TopDrops_P.*` 檔案。
3. 要換回一般版，再把 `mods\DW3CE_TopTierDrops\` 裡的 3 個 mod 包檔案複製回去即可。

## 移除

刪除上表的 5 個檔案（以及執行後產生的 `dw3ce_re_top_tier_drop.log`）即可。使用 ASI 版的話，刪的是 `dw3ce_re_top_tier_drop.asi` 而不是 `version.dll`。
（Steam 的「驗證遊戲檔案完整性」不會刪除多出來的 mod 檔案，要手動刪。）

## 設定（dw3ce_re_top_tier_drop.ini）

修改後重新啟動遊戲。

**`Element`：掉落武器的屬性**

| 值 | 屬性 |
|---|---|
| `0` | 隨機（原版：炎／雷／斬／風） |
| `1` | 炎 |
| `2` | 雷 |
| `3` | 斬（預設） |
| `4` | 風 |

**其他開關**：`1` = 開啟，`0` = 關閉

| 開關 | 效果 |
|---|---|
| `MaxSkillRoll` | 武器技能與場上道具的數值固定取最大值 |
| `MaxGuardSkillRoll` | 護衛兵武器的技能數值固定取最大值 |
| `MaxGuardItemRoll` | 場上掉落的護衛兵技能道具，數值固定取級距內最大值 |
| `SkillTierFix` | **必要，請勿關閉**。關閉會讓武器技能數值變成最低級距 |
| `GuardTierFix` | **必要，請勿關閉**。關閉會讓護衛兵武器技能數值變成最低級距 |
| `ComboUpgradeAlways` | 擊倒敵人掉落的道具一律升一級尺寸，不看連擊數（關閉則恢復原版的連擊條件） |

## 遊戲更新後

- `dw3ce_re_top_tier_drop.log` 若出現 `signature NOT found`，表示遊戲程式碼變了，該項修改會**自動跳過**（不會亂改），需要更新 mod。
- 若更新改到資料表，需要重新建置 mod。方法見 `source\DW3CE_TopTierDrops\README.md`。

---

## 資料夾說明

```
dw3ce_re_top_tier_drop\
├─ README.md                 英文版說明（GitHub 首頁）
├─ README.zh-TW.md           本檔：mod 功能與使用說明
├─ mods\
│  ├─ DW3CE_TopTierDrops\        成品（照遊戲目錄結構擺放）
│  ├─ DW3CE_TopTierDrops_ASI\    同上，但 DLL 改為給 Ultimate ASI Loader 載入的 .asi
│  └─ DW3CE_VanillaWeaponDrops\  變體版：只有替換用的 mod 包（武器掉落等級維持原版）
├─ source\
│  ├─ DW3CE_TopTierDrops\        原始碼、建置腳本、修改紀錄、開發歷程與驗證過程
│  └─ DW3CE_VanillaWeaponDrops\  變體版的修改紀錄（edited_json，由 build_mod.py --vanilla-weapons --package 產生）
└─ tools\                    開發用工具（DataTable 解析工具、retoc、原版資料匯出）
```

## 檔案校驗

| 檔案 | SHA-256 |
|---|---|
| `zDW3TopDrops_P.pak` | `75e7144577253917f6da7312ef5e585b12fb728226a22b0938323751a6b555cd` |
| `zDW3TopDrops_P.utoc` | `36c42c3e499f09b74cc479ec265488e308df8a8903f3549226b30296aa502ab1` |
| `zDW3TopDrops_P.ucas` | `bce3a11576852ef75c02ae12d47878e7b0cfc158225e3d345137e5344b23ff82` |
| `zDW3TopDrops_P.pak`（變體版） | `75e7144577253917f6da7312ef5e585b12fb728226a22b0938323751a6b555cd`（與一般版相同） |
| `zDW3TopDrops_P.utoc`（變體版） | `6556fc950d304fa5e9ec9ce562c4b9c0b9e8d8b38167cf0a74ffd059e0d5c8c5` |
| `zDW3TopDrops_P.ucas`（變體版） | `718b2a8685f1babe07422e4ee132a61c039ff04db0989980a7c4fc0511229010` |
| `version.dll` | `f2bc13d72ab2fbf76566d459ea079c3cff116a6f54f24a3e9c968995bd486e94` |
| `dw3ce_re_top_tier_drop.asi`（ASI 版） | `f2bc13d72ab2fbf76566d459ea079c3cff116a6f54f24a3e9c968995bd486e94`（與 version.dll 相同） |
| 對應的遊戲執行檔 `DW3CE_RE-Win64-Shipping.exe` 1.0.2.0 | `ca1a65a53242a7cf42493bd2006b8c555d87597387468e4b7a07c52d4eefe92e` |

## 授權

- 本專案自己撰寫的程式碼與文件（`source\`、`tools\DataTableTools\`、各 README）採用 [MIT License](LICENSE)。
- `tools\retoc\` 是第三方工具，沿用其原作者的 MIT 授權（見 `tools\retoc\LICENSE`）。
- 遊戲本體、遊戲資料及其衍生內容（mod 包內的資料表、`edited_json`）的權利屬於原遊戲權利人，不在 MIT 授權範圍內。

## 注意

- 僅供單機遊玩。
