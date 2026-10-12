# DW3CE_TopTierDrops — 開發歷程

這份文件記錄這個 mod 是怎麼做出來的：用了哪些工具、每一步做了什麼驗證，以及根據什麼證據決定要改哪裡。
mod 的功能與安裝方式見 `E:\DE3MOD\README.zh-TW.md`。

- 開發日期：2026-10-09（一天內完成，中間經過三次實機測試）
- 目標遊戲：真・三國無雙 3 Complete Edition Remastered（`DW3CE_RE`）1.0.2.0，Steam 版
- 整個過程只做**靜態分析**（讀檔案、反組譯），不需要在遊戲執行時掛除錯器或注入工具

---

## 目錄

1. [使用的工具](#使用的工具)
2. [開發歷程](#開發歷程)
   - [階段 1：確認遊戲能不能拆](#階段-1確認遊戲能不能拆)
   - [階段 2：確認引擎版本](#階段-2確認引擎版本)
   - [階段 3：在沒有 usmap 的情況下讀懂 DataTable](#階段-3在沒有-usmap-的情況下讀懂-datatable)
   - [階段 4：找出真正控制掉落的表](#階段-4找出真正控制掉落的表)
   - [階段 5：v1 資料表 mod](#階段-5v1-資料表-mod)
   - [階段 6：查證「必定斬屬性、數值最高」是否可行](#階段-6查證必定斬屬性數值最高是否可行)
   - [階段 7：不改執行檔的修改方式](#階段-7不改執行檔的修改方式)
   - [階段 8：v2](#階段-8v2)
   - [階段 9：v3，道具與武器同時拿到上限](#階段-9v3道具與武器同時拿到上限)
   - [階段 10：整理與可重現建置](#階段-10整理與可重現建置)
   - [階段 11：可選屬性、連擊升級一律生效](#階段-11可選屬性連擊升級一律生效)
   - [階段 12：統一命名](#階段-12統一命名)
   - [階段 13：護衛兵道具的數值](#階段-13護衛兵道具的數值)
   - [階段 14：支援 Ultimate ASI Loader](#階段-14支援-ultimate-asi-loader)
3. [走過的彎路](#走過的彎路)
4. [附錄 A：最終修改清單](#附錄-a最終修改清單)
5. [附錄 B：逆向分析筆記](#附錄-b逆向分析筆記)
6. [附錄 C：建置方式](#附錄-c建置方式)

---

## 使用的工具

| 工具 | 版本 | 用途 |
|---|---|---|
| [retoc](https://github.com/trumank/retoc) | v0.1.5 | IoStore 容器（`.utoc`/`.ucas`）與 legacy 資源（`.uasset`/`.uexp`）互轉、列出容器內容、查 chunk hash |
| Python | 3.10.6 | 所有分析與建置腳本 |
| capstone（Python） | 5.0.7 | x86-64 反組譯 |
| numpy | 2.2.6 | 在 130 MB 的程式碼區段中，快速搜尋 RIP 相對位址參照與 call 目標 |
| Visual Studio 2019 Build Tools | MSVC 14.29.30133、Windows SDK 10.0.19041 | 編譯 `version.dll`（本機原本就有，不需另外安裝） |
| 自製 `DataTableTools` | — | 見 `E:\DE3MOD\tools\DataTableTools\README.md` |

自製工具一覽：

| 檔案 | 做什麼 |
|---|---|
| `list_utoc.py` | 直接解析 `.utoc` 的目錄索引，列出全部資源路徑 |
| `reflect.py` | 從執行檔中的 UHT 反射參數，靜態讀出 struct／enum／class 的欄位名稱、型別、順序；解析 IAT 匯入表 |
| `dt2json.py` / `json2dt.py` | cooked（unversioned）DataTable ⇄ JSON |
| `xref.py` | 找「誰參照這個位址」「誰 call 這個函式」、用 `.pdata` 找函式邊界 |
| `build_mod.py` | 從原版資料套用修改並打包成 mod |

---

## 開發歷程

### 階段 1：確認遊戲能不能拆

**問題**：資源是什麼格式？有沒有加密或防護？

| 做了什麼 | 看到什麼 | 結論 |
|---|---|---|
| 統計遊戲資料夾的副檔名 | 2 組 `.utoc`/`.ucas`（53 GB）、1 個 `.pak`（4 GB）、33 個 `.uasset` | Unreal Engine 5 的 IoStore 格式 |
| 依 `FIoStoreTocHeader` 格式解析 `.utoc` 檔頭 | TOC 版本 8；`ContainerFlags` 只有 `Indexed`，沒有 `Encrypted`；`EncryptionKeyGuid` 全 0 | **資源容器沒有加密**，不需要 AES 金鑰 |
| 解析 `.pak` 檔尾 | `bEncryptedIndex = 1`，版本 11 | `.pak` 的索引有加密，但掉落資料不在這裡，不影響 |
| 列出執行檔的 PE section | 有 `.bind` | Steam DRM（SteamStub），沒有 Denuvo |
| 寫 `list_utoc.py` 解析 utoc 目錄索引 | 共 142,487 個資源；`DW3CE_RE/Content/DataAsset/` 底下有 168 張 `DT_*` 表 | 知道要從哪裡找資料 |

### 階段 2：確認引擎版本

**問題**：打包 mod 時要告訴 retoc 引擎版本，選錯會打包出遊戲讀不了的檔案。

- 執行檔裡找不到 `++UE5+Release-5.x` 版本字串；轉出的 `.uasset` 是 unversioned（版本欄位全 0）；`LegacyFileVersion = -9`。都無法直接判斷版本。
- **驗證方式**：把一個沒有修改過的資源（`DT_SkillNumRandomTable`）分別用 UE5_3 到 UE5_7 打包，再比對產出的 chunk hash 與原版是否相同。

| 版本 | 結果 |
|---|---|
| UE5_3 / 5_4 / 5_5 | `failed to fill whole buffer`（無法打包） |
| UE5_6 | 打包成功，chunk hash `38cf14dd…` **與原版完全相同** |
| UE5_7 | 打包成功 |

**結論**：UE 5.6。之後所有打包都使用 `--version UE5_6`。

### 階段 3：在沒有 usmap 的情況下讀懂 DataTable

**問題**：UE5 打包後的 DataTable 是 *unversioned* 格式，檔案裡沒有欄位名稱和型別。一般作法是把 UE4SS 裝進遊戲、執行時匯出 `.usmap`，但這需要改動遊戲資料夾並啟動遊戲。

**觀察**：先手動解 `DT_ItemData` 的二進位內容。從 name map 看到 row struct 是 `/Script/Refine.ItemData_TableRow`（C++ 原生 struct）。
依 unversioned header 的格式（uint16 片段：skip 7 bits／has-zero 1 bit／is-last 1 bit／count 7 bits）手動拆解後，得知共 255 列，每列只有 1 個 1-byte 欄位。

**突破點**：在執行檔裡搜尋 `ItemData_TableRow` 字串，旁邊是 `FieldID_X`、`FieldID_Y`、`SpawnPoint`、`IsAutoGet` 等欄位名稱。
UHT 產生的反射參數（`FPropertyParams`）會用指標指向這些名稱字串，所以只要搜尋「指向名稱字串的 8-byte 指標」，就能找到參數結構，讀出型別與 offset。

**校正結構 layout**：預設的 layout 推測不一定對，所以每種結構都先 dump 原始 bytes 對照實際內容再定下來：

| 結構 | 實測欄位位置 |
|---|---|
| `FPropertyParams` | 名稱 `+0`、GenFlags `+24`（例如 `0x4C` = Bool、`0x03` = Int、`0x00` = Byte）、Offset `+50`、型別專屬指標 `+56` |
| `FStructParams` | 名稱 `+24`、屬性陣列 `+32`、屬性數 `+40` |
| `FEnumParams` | 名稱 `+16`、列舉值陣列 `+32`、數量（int16）`+44`。第一次猜成 `+40`/`+56` 時讀出亂碼，dump bytes 後校正 |
| `FClassParams` | StaticClass `+0`、屬性陣列 `+40`、屬性數 `+58` |

**驗證**（重點：不能只看「解出來的東西像不像樣」）：
1. **剛好讀到檔尾**：解碼器嘗試每個可能的起點，必須剛好讀到檔案結尾（只剩 4 bytes 的 package tag）才算成功。欄位型別或順序只要錯一個，位置就會對不上。
2. **逐位元組還原**：寫好 `json2dt.py` 後，把 JSON 編碼回去，必須和原檔**每個 byte 都一樣**。最後 168 張表中有 150 張通過，剩下 18 張用了尚未支援的型別，與本 mod 無關。
3. 過程中靠這兩項檢查抓到的 bug：
   - name map 起點誤抓 summary 裡的 PackageName → 改成從檔頭讀 NameCount/NameOffset
   - enum 參數 layout 猜錯 → dump bytes 校正
   - 把「offset 為 0」當成 inner 屬性的判斷條件，誤吃掉真正位於 offset 0 的欄位（`EquipItemSaveData.EquipItemID`）→ 改用名稱比對
   - `FName None` 沒有視為零值，導致 55 張表編碼失敗

**附帶結論**：`DT_ItemData` 只有 `IsAutoGet`（地圖上的道具是否自動拾取），**不是**道具數值表。

### 階段 4：找出真正控制掉落的表

**做法**：用 `reflect.py` 列出執行檔裡含 `Item`、`Equip`、`Weapon`、`Drop`、`Skill` 的 row struct，再把對應的表全部解出來看內容。

| 表 | 判讀依據 |
|---|---|
| `DT_EquipItemBaseData` | 有 `EQUIP_ITEM_SEKITOABUMI`（赤兔鐙）等道具 ID，欄位 `ValueRand`、`RandHit`、`Type`（Blue/Red） |
| `DT_DropRandomTable` | 16 列 `StageRank_00~15`，數值隨等級往右移（`[100,0,0,0,0]` → `[0,0,100,0,0]`），符合「難度越高掉越好」 |
| `DT_SkillNumRandomTable` | `SkillRandBase` 兩列：一般武器、護衛兵武器 |
| `DT_WeaponRankData` | 5 個武器等級，`AttributeProbability` 只有等級 2 是 20 |

另外也確認了 `DA_GameParameterDataAsset`：它不是 DataTable，所以從 class 名稱的寬字元字串找到 StaticClass 函式，再找到 `FClassParams`，讀出 `BattleSettings`／`ActionSettings`／`ItemParamSettings` 的全部欄位。
裡面沒有屬性或技能數值的設定 → 推斷這部分是寫在程式碼裡（階段 6 證實）。

### 階段 5：v1 資料表 mod

**修改**：`WeaponRandRank` → `[0,0,100,0,0]`、`SkillItemRandRank` → `[0,0,0,0,100]`（照抄原版最高難度列）、`SkillRandBase` → `[100]*5`。

**判斷依據**：
- `WeaponRandRank` 是累積機率表：擲 0~99，找第一個「亂數 < 格子值」的位置。原版從來沒用到第 3、4 格，而 `DT_WeaponRankData` 的等級 3/4 對應專屬武器，所以最高只開到等級 2。
- `SkillRandBase` 的方向**當時無法從程式碼確認**，是從資料推論：
  原版 `[1,3,13,33,100]` 換算成機率是 1%/2%/10%/20%/67%，第 0 格最稀有，推論「第 0 格 = 技能最多」。為了保險，另外做了反方向 `[0,0,0,0,100]` 的版本備用。

**驗證**：
- 修改前後檔案大小相同，可以直接替換。
- 打包後把 mod 容器連同原版的 `global.utoc` 一起再用 `retoc to-legacy` 解出來、重新解碼，確認內容是修改後的值。
- **實機測試**：技能數量全滿 → 推論的方向正確。

### 階段 6：查證「必定斬屬性、數值最高」是否可行

**新需求**：每把掉落武器必定帶「斬」屬性、技能數值最高。

**找資料結構**：
- 從反射資料讀出 `WeaponSaveData`（存檔中的武器）：`attr` 是 int64 bit flags，位於 +0x18；技能是 `EquipItemSaveData[]`（`EquipItemID` + `Value`）。
- 讀出 enum `EWeaponAttrFlag`：FIRE = 4、THUNDER = 8、**ZAN = 16**、WIND = 32、4TH = 128 …
- `DT_WeaponBaseData` 的 `Attribute` 欄位：專屬武器的屬性是寫死的（例如 147 = 4TH|ZAN|…），一般武器只有 0/1/3（沒有元素位元）→ 證明掉落武器的屬性是**執行時**才決定的。

**找到武器生成函式**（追蹤路徑）：
1. 字串 `DT_SkillNumRandomTable` → 用 `xref.py` 找參照它的程式碼 → 載入函式。
2. 同一區域找到取表的 getter `0x1414b8100` → 找呼叫它的地方 → 3 處。
3. 用 `reflect.imports()` 解析 IAT，把 `call [rip+x]` 換成函式名稱：其中一個函式呼叫了 **10 次 `ucrt!rand`** → 鎖定為武器生成函式 `0x1415162a0`。

**讀懂邏輯**（詳細見附錄 B）：
- 浮點常數 `0.0030518…` = 100/32767（把 `rand()` 換算成 0~99）、`3.05e-5` = 1/32767、`0.01`、`-0.5`（四捨五入技巧）。
- 屬性：`rand() < AttributeProbability` 時，從立即值 **`0x20100804`**（bytes = 4, 8, 16, 32 = 炎、雷、斬、風）中隨機挑一個 → **屬性種類寫死在程式碼裡，只改資料表做不到「固定斬」**。
- 技能數值函式 `0x141537560`：級距內有 `rand % ValueRand` → **只改資料表也做不到「固定最大值」**。

**同時發現 v1 的問題**：技能數值函式查 `SkillItemRandRank` 時，迴圈上限是 `movzx r9d, r14b; add r9, 4`，其中 `r14b = !isWeapon`，所以武器是 4、道具是 5。
→ **武器只讀前 4 格**，找不到符合的格子就用級距 0。v1 的 `[0,0,0,0,100]` 前 4 格都是 0，反而讓武器技能數值**掉到最低級距**。
（原版 StageRank_13 本身也是 `[0,0,0,0,100]`，所以原版在那個難度也有同樣的現象，看起來是原版的 bug。）

另外用 `xref.py` 列出技能數值函式的所有呼叫者：只有武器生成函式傳入 `isWeapon = 1`，其他 4 處（場上道具等）都是 0，確認武器與道具確實走不同的分支。

### 階段 7：不改執行檔的修改方式

最初提議直接改執行檔的幾個 bytes；使用者希望**不要動執行檔**，改用類似 ASI 的方式。

**選擇 `version.dll` 代理的依據**：
- 解析執行檔的 IAT：有匯入 `VERSION.dll`（`GetFileVersionInfoW` 等 3 個函式）。
- 查 registry 的 `KnownDLLs`：`version.dll` **不在**清單中 → 遊戲會優先載入自己資料夾裡的同名 DLL。
- 本機有 VS2019 Build Tools，可以直接編譯，不必下載其他東西。

**安全設計**：
- 每個修改點寫入前都比對 20 bytes 的原始特徵碼；先查預期位址，不符再掃整個 `.text`。先用 Python 確認每組特徵碼在 `.text` 裡**只出現一次**。
- 找不到就跳過並寫 log，絕不在不確定的位置寫入。
- 只在 `DW3CE_RE-Win64-Shipping.exe` 程序內動作。

**不開遊戲的驗證**：
1. 解析編譯出的 DLL 的 export table：17 個函式都正確轉發到 `C:\Windows\System32\version.dll`。
2. 用 Python 的 `ctypes` 載入這個 DLL，呼叫轉發的 `GetFileVersionInfoSizeW` → 正常回傳；log 寫出 `not the game exe, doing nothing` → 確認在其他程序裡不會動作。
3. 用正規表示式從 C 原始碼取出每組特徵碼，與執行檔實際的 bytes 自動比對 → 全部一致。

### 階段 8：v2

**資料表**：`SkillItemRandRank` → `[0,0,0,100,100]`（武器拿到級距 3）、`CorrectionRate` → 100、`CorrectionRatio` → 150、`AttributeProbability` → 100。
**DLL**：`ZanOnly`、`MaxSkillRoll`、`MaxGuardSkillRoll`。

**過程中的檢查**：
- 等級 0~9 的 `CorrectionRatio` 原本是 0。只改 Rate 的話，數值會被乘以 0 → 一起填 150。
  這讓欄位從「零值旗標」變成實際寫入 4 bytes，檔案變長，因此在 `json2dt.py` 加上 uasset 的 `SerialSize` 與 `BulkDataStartOffset` 修正。
  先在 uasset 中搜尋這兩個數值，確認各自只出現一次才修改；最後再從打包好的容器反解，確認三張表的內容都正確。
- **`CorrectionRatio` 是 125 還是 150？** 曾討論過這點。在原始 `.uexp` 中直接搜尋 int32 的 150 與 125：150 出現 4 次（StageRank_10~13），125 沒有出現。
  再對照程式公式 `數值 × Ratio / 100`，原版效果是 ×1.5 → 決定沿用 150。

**實機測試**：屬性固定斬 ✓、技能數量 ✓，但場上掉落的白虎牙是 **20**。

### 階段 9：v3，道具與武器同時拿到上限

**分析 20 這個數字**：白虎牙的 `ValueRand` = 5，級距 3 的最大值 = (3+1) × 5 = **20**，剛好吻合。這同時證明 `MaxSkillRoll` 有生效。
原版道具的上限是級距 4 = 25。

**為什麼只改資料做不到**：同一列資料武器與道具共用，差別只在讀幾格。

| 設定 | 武器（讀 0~3） | 道具（讀 0~4） |
|---|---|---|
| `[0,0,0,100,100]` | 第 3 格 → 級距 3 ✓ | 第 3 格先符合 → 級距 3 ✗ |
| `[0,0,0,0,100]` | 找不到 → 級距 0 ✗ | 第 4 格 → 級距 4 ✓ |

**解法**：資料改回 `[0,0,0,0,100]`，再用 DLL 把「找不到時的預設級距」從 0 改成 3。

**在不增加長度的前提下改指令**（等長替換，不需要跳板）：
- 預設值原本來自 `xor esi, esi`（2 bytes），空間不夠放 `mov esi, 3`（5 bytes）。
  注意到迴圈裡 `r8d` 與 `rdx` 是**同步遞增**的兩個計數器 → 把 `xor r8d, r8d`（3 bytes）改成 `push 3; pop rsi`（3 bytes），找到時改從 `rdx` 取值（`mov esi, edx; nop`）。兩處必須同時套用。
- 護衛兵武器那段沒有多餘空間，但 `rand()` 之後的 `and eax, 0x7FFF` 是多餘的：UCRT 的 `rand()` 本來就只回傳 0~0x7FFF。
  拿這 5 bytes 加上 `mov r14, rdi`（3 bytes），換成 `push 3; pop r14; nop4`。

**驗證**：
- 在 Python 裡把修改套到執行檔影像的副本上，再用 capstone 反組譯，確認指令邊界正確、後續指令沒有被切斷。
- DLL 改為「同一個 ini key 的修改點全部找到才一起寫入」，避免只改一半。
- 重新比對 6 組特徵碼，再從打包好的容器反解資料表。
- **實機測試通過**：道具與武器同時達到各自的原版上限。

### 階段 10：整理與可重現建置

- 原本分成「資料表 mod」與「DLL mod」兩個資料夾；因為兩者無法單獨運作，合併成 `DW3CE_TopTierDrops`，成品照遊戲目錄結構擺放。
- **建置可重現性**：在新位置重建時，utoc/ucas 跟原本的不一樣。用 `retoc list --hash` 比對，每個 chunk 的內容 hash 都相同，只有排列順序不同。
  原因是 retoc 預設平行處理 → 加上 `--no-parallel` 後連續建置 4 次，結果完全相同。
  `mods\` 裡放的仍是實機測試過的那一份（chunk 內容與重建版相同，只差順序）。
- 從新位置重新編譯 DLL、照著每份 README 的指令實際跑過一遍，確認文件與實際行為一致。

### 階段 11：可選屬性、連擊升級一律生效

**需求一：屬性可以自己選**
- 把 `ZanOnly`（開／關）改成 `Element`（0 = 原版隨機、1 炎、2 雷、3 斬、4 風）。寫入的 4 bytes 改由 ini 的值在執行時決定，數值對應 `EWeaponAttrFlag`（4/8/16/32）。
- 舊版 ini 只有 `ZanOnly` 時照舊相容（1 → 3、0 → 0）；超出 0~4 的值會記錄到 log 並維持原版。
- **驗證**：另外編譯一支測試程式，取名為 `DW3CE_RE-Win64-Shipping.exe` 並載入 DLL。它的映像裡沒有遊戲程式碼，所以只會讀 ini、寫 log，不會真的修改。
  用 9 種 ini 設定（0~4、7、`ZanOnly=1/0`、沒有 ini）逐一確認 log 輸出正確。
- **測試中抓到的潛在 bug**：DLL 會直接讀「基底位址 + 預期 RVA」去比對特徵碼，測試程式的映像很小，那個位址不存在，導致程式當掉。
  實際遊戲映像夠大所以沒出過問題，但遊戲改版後映像可能變小 → 修正為先確認位址落在 `.text` 範圍內才讀取。

**需求二：擊倒敵人掉落的攻擊／防禦道具**
- 一開始的需求描述是「依連擊數決定掉落的攻擊／防禦數值，改成系統上限」，先查證機制在哪裡：
  1. `DT_ItemTypeData` 有 `ITEMTYPE_ATK_UP_S/M/L/LL`、`DEF_UP_S/M/L/LL`，效果都是同一個 `GE_GROWTH_ITEMS`。
     `DT_ComboFactorData`、`GrowthSettings` 等表都跟掉落尺寸無關。
  2. 字串找到 `UGEExecCalc_GrowthItem`（GameplayEffect 的計算類別）。從類別名稱 → StaticClass → 建構子 → vtable，
     與父類別 vtable 比對，找出覆寫的計算函式 `0x141535040`。
     每種尺寸的增加量寫在建構子的 Map 裡：**S +1、M +2、L +4、LL +8**，累計用 `minss 150.0` 封頂。
  3. 從反射資料找到 `GroupLineup_TableRow.DropItem`（`EItemID`），解出 228 張 `DT_GroupLineup_*` 關卡表統計：
     `EItemID` 的編號就是道具種類，**每個敵人掉哪個尺寸是關卡表固定的**。
  4. `ComboCount` 是 GAS 屬性（AttributeSet `+0x180`）。從 UTF-16 字串 `"ComboCount"` 找到建立屬性描述的初始化程式，
     再找到 `AddComboCount`（`0x1417494c0`）與 `GetComboCount`（`0x141749490`）。
     掃描全部「讀取 AttributeSet + 0x180」的位置，只有 4 處；其中呼叫 `GetComboCount` 的 `0x141377df0` 就是**擊倒敵人時的掉落函式**。
- 讀懂的掉落規則（附錄 B）：道具種類 0~15 時，若 `連擊數 ÷ 8 > 目前尺寸` 就升一級（最多一級）。
- 統計各等級敵人掉的攻防道具時發現，一般部隊也有 643 處掉防禦 S。若直接全部改成 LL 會大幅影響平衡，所以先向使用者確認範圍。
  使用者的決定是：**保留原本「升一級」的機制，只是不再看連擊數，一律升級**。
- **修改**：把 `jle`（連擊不足就跳過升級）換成 2 bytes 的 `nop`。特徵碼從 `cdq` 開始取，避開 `call` 的相對位址，遊戲小改版時掃描比較不會失效。
  修改後的機器碼先模擬寫入並反組譯，確認指令邊界正確。

### 階段 12：統一命名

- 設定檔、log、DLL 原始碼原本叫 `dw3ce_patch.*`，統一改成 `dw3ce_re_top_tier_drop.*`（`version.dll` 必須維持原名，遊戲才會載入）。
- 檔名寫死在 DLL 裡，只改檔案名稱會讓設定失效，所以同時修改程式碼。
- **相容處理**：找不到 `dw3ce_re_top_tier_drop.ini` 時，若有舊的 `dw3ce_patch.ini` 就改讀舊檔，並在 log 提醒改名；兩者都沒有就用預設值。
- **驗證**：用測試程式跑 4 種情況（只有新檔、只有舊檔、兩者都有、都沒有），確認讀到的設定與 log 都正確，而且不再產生舊名稱的 log。

### 階段 13：護衛兵道具的數值

- **問題**：使用者詢問護衛兵的裝備和道具是否也會拿到最高。護衛兵武器已確認沒問題（技能數量 3、`GuardTierFix` + `MaxGuardSkillRoll`）。
  道具的部分則需要確認，有沒有其他程式也在決定護衛兵道具的數值。
- **查證**：用 `xref.py` 列出所有呼叫護衛兵道具資料 getter（`0x141465900`）的地方，共 21 處，大多在介面相關的程式區段。
  其中位在武器生成函式旁邊的 `0x141518630` 有自己的 `rand()`，而且跟一般道具掉落在同一個函式（`0x141376c..`）裡被呼叫 → **場上掉落的護衛兵道具有獨立的數值函式**。
- 讀懂邏輯（附錄 B）：它讀 `SkillItemRandRank` 全部 5 格（不限等級上限），所以資料表 `[0,0,0,0,100]` 已讓它落在級距 4；
  但級距內的 `rand % ValueRand` 是它自己算的，`MaxSkillRoll` 管不到 → 數值仍隨機（例如朱雀翼 33～40）。
- **修改**：新增 `MaxGuardItemRoll`，把 `cmovl ebx, eax` 換成 3 bytes 的 `nop`，讓 `ebx` 保持進入前設好的 `ValueRand − 1`。
  特徵碼從 `mulss xmm2, xmm0` 開始取，避開前一行的 RIP 相對位址；確認在 `.text` 中唯一，並模擬寫入後反組譯確認指令邊界。
- **驗證**：8 組特徵碼與執行檔逐一比對一致且唯一；測試程式載入正常。
- **安裝時保留使用者設定**：遊戲裡的 ini 被使用者改過（例如 `Element=0`），所以只替換 DLL，並在 ini 最後補上新開關，不覆蓋原有內容。
  缺少的開關在 DLL 裡預設為開啟，所以舊的 ini 也能直接使用。

### 階段 14：支援 Ultimate ASI Loader

- **問題**：有使用者回報其他模組也使用 `version.dll`。遊戲只會載入一個 `version.dll`，兩個模組無法同時安裝。
- **評估過的做法**：
  1. 在我們的 DLL 加「串接載入」：載入改名後的另一個 `version.dll`。
  2. 改成 `.asi`，交給 Ultimate ASI Loader 載入。
  3. 另外編譯其他檔名的代理 DLL（例如 `winmm.dll`）。
  
  最後採用第 2 種：UAL 本身就是 `version.dll`，會載入資料夾裡所有 `.asi`，很多模組都用它，所以能和其他模組共存。
- **不需要另寫程式**：`.asi` 就是改了副檔名的 DLL。我們的 DLL 在 `DllMain` 啟動修改執行緒；ini 和 log 依 DLL 自己所在的資料夾決定；
  檢查的也是遊戲執行檔的名稱，跟自己叫什麼無關。所以同一個檔案改名成 `dw3ce_re_top_tier_drop.asi` 就能直接使用。
  `version.dll` 原本的 17 個 export 轉發，在 `.asi` 形式下用不到，但留著也不影響。
- **只加了一行 log**：`loaded as <路徑>`，記錄 DLL 是以 `version.dll` 還是 `.asi` 被載入，方便日後排查。
- **曾考慮但沒有採用**：加一個「同一程序只執行一份」的保護，避免使用者同時放 `version.dll` 和 `.asi`。使用者決定不加。
  驗證後確認兩份同時存在也不會出問題：兩份寫入的 bytes 相同，第二份只是拿不到 log 檔。
- **驗證**：寫兩支測試程式，用 `LoadLibrary` 模擬 UAL 載入：
  - 只有 `.asi`：正確讀到旁邊的 ini，log 寫在 `.asi` 旁邊。
  - `version.dll` 與 `.asi` 同時存在：正常結束，沒有當掉。
- **成品**：新增 `mods\DW3CE_TopTierDrops_ASI\`，內容是同一份 mod 包、`.asi` 和 ini，不含 `version.dll`。
  `build.bat` 編譯後會同時產出 `version.dll` 和內容相同的 `.asi`。UAL 本身不隨附，由使用者另外安裝。

---

## 走過的彎路

- **v1 的回歸問題**：照抄原版最高難度的 `[0,0,0,0,100]`，以為就是「最好」，沒想到武器與道具讀的格數不同。這是在階段 6 讀程式碼時才發現的。
- **追錯函式**：階段 5 時曾想從程式碼確認 `SkillRandBase` 的方向，從表名字串一路追到一個 getter 的呼叫者，讀了才發現那是角色生成相關的程式，追錯了。
  後來先用資料推論 + 實機確認，等到階段 6 用「呼叫 `rand` 的次數」才找到正確的函式。
- **小問題**：自訂的 `logf` 與 MSVC 內建數學函式同名（改名 `plog`）；`wvsprintfA` 需要連結 `user32.lib`；retoc 打包需要 `scriptobjects.bin`，否則同樣會出現 `failed to fill whole buffer`。

---

## 附錄 A：最終修改清單

### 資料表（`datatable\build_mod.py`）

| 表 | 欄位 | 原版 | 修改後 |
|---|---|---|---|
| `DT_DropRandomTable`（16 列） | `WeaponRandRank` | 例 `[0,30,100,0,0]` | `[0,0,100,0,0]`（StageRank_14/15 原本就不掉武器，保留） |
| 〃 | `SkillItemRandRank` | 例 `[20,50,85,100,0]` | `[0,0,0,0,100]` |
| 〃 | `CorrectionRate` | 0~15 | 100 |
| 〃 | `CorrectionRatio` | 0 或 150 | 150 |
| `DT_SkillNumRandomTable` | `SkillRandBase`（一般） | `[1,3,13,33,100]` | `[100,100,100,100,100]` |
| 〃 | `SkillRandBase`（護衛兵） | `[2,12,32,38,0]` | `[100,100,100,100,100]` |
| `DT_WeaponRankData` | `AttributeProbability`（等級 0~2） | 0 / 0 / 20 | 100 |
| 〃 | `RedSkillProbability`（等級 0~2） | 0 / 0 / 10 | 100 |

修改後的完整內容在 `datatable\edited_json\`。

### 程式修改（`dll\dw3ce_re_top_tier_drop.c`，VA，ImageBase `0x140000000`）

| ini key | 位置 | 原始指令 | 修改後 | 效果 |
|---|---|---|---|---|
| `Element` | `0x141516921` | `mov dword [rbp+67h], 20100804h` | 立即值四個 bytes 都填入選定屬性（斬 = `10101010h`） | 屬性候選四格都是同一屬性；`0` 不修改 |
| `MaxSkillRoll` | `0x141537673` | `cmovl ecx, eax` | `nop`（3 bytes） | 級距內固定取 `ValueRand−1`。武器與場上道具共用 |
| `MaxGuardSkillRoll` | `0x141516c5b` | `cmovl ecx, eax` | `nop` | 護衛兵武器固定取 `RandomSeed[級距]−1` |
| `SkillTierFix` | `0x1415375ff` | `xor r8d, r8d` | `push 3; pop rsi` | 找不到級距時預設 3 |
| 〃（同組） | `0x141537625` | `mov esi, r8d` | `mov esi, edx; nop` | 改用同步遞增的 rdx |
| `GuardTierFix` | `0x141516bb3` | `and eax, 7FFFh; mov r14, rdi` | `push 3; pop r14; nop4` | 護衛兵武器預設級距 3 |
| `ComboUpgradeAlways` | `0x141377ef1` | `jle 0x141377f01` | `nop`（2 bytes） | 擊倒敵人掉落的道具一律升一級，不看連擊數 |
| `MaxGuardItemRoll` | `0x14151871b` | `cmovl ebx, eax` | `nop`（3 bytes） | 場上掉落的護衛兵道具，級距內固定取最大值 |

---

## 附錄 B：逆向分析筆記

### 武器生成函式 `0x1415162a0`
1. `rand()` → 0~99，查 `DT_DropRandomTable[關卡等級].WeaponRandRank` 決定武器等級。
2. 一般武器：
   - `rand()` 查 `DT_SkillNumRandomTable`（讀 5 格），技能數 = `5 − index`（武器種類 3/4 另 +2/+1，上限 5）。
   - 把 `DT_EquipItemBaseData` 裡 Type = Blue 的項目洗牌（Fisher–Yates），取前 N 個；數值由 `0x141537560` 計算。
   - `rand() < RedSkillProbability` → 最後一格換成紅技能（數值 0）。
   - `rand() < AttributeProbability` → 從 `{4,8,16,32}` 隨機挑一個 OR 進 `attr`。
3. 護衛兵武器（`0x1415169f1` 起）：`DT_SkillNumRandomTable` 只讀 4 格，技能數 = `3 − index`（上限 3）；
   技能取自 `DT_GuardEquipItemBaseData`，數值 `(rand % RandomSeed[級距] + 加成) × 5`，最小 1。

### 技能數值函式 `0x141537560(itemId, stageRank, isWeapon)`
- 關卡等級上限：武器 13、道具 15。
- 級距 = `SkillItemRandRank` 中第一個「`rand(0~99) < 格子值`」的位置；**武器只看 0~3、道具看 0~4**；找不到 = 0。
- 數值 = `rand % ValueRand + 1 + 級距 × ValueRand`。
- 僅武器：`rand(0~99) ≤ CorrectionRate` 時，數值 × `CorrectionRatio / 100`（四捨五入）。

### 擊倒敵人的掉落函式 `0x141377df0(this, itemType, …, player)`
- `itemType` 來自關卡表 `DT_GroupLineup_*` 的 `DropItem`（`0xFF` = 不掉）。部分遊戲模式（全域狀態 9、10）跳過以下升級邏輯。
- 道具種類 0~15（肉包、箭矢、攻擊＋、防禦＋，各 S/M/L/LL）：`尺寸 = 種類 % 4`；若尺寸 < 3 且 `GetComboCount() / 8 > 尺寸` → 種類 +1。
- 本來不掉道具的敵人：連擊數 ≥ 16 時，隨機掉肉包（小）或箭矢（小）。（本 mod 未修改）

### 場上護衛兵道具的數值函式 `0x141518630(this, stageRank)`
- 先由 `0x141537130` 決定護衛兵道具種類（`0xA` = 不掉）。
- 級距 = `DT_DropRandomTable[關卡等級].SkillItemRandRank` 中第一個「`rand(0~99) < 格子值`」的位置，**讀全部 5 格**，關卡等級沒有上限；找不到 = 0。
- 數值 = `rand % ValueRand + 1 + 級距 × ValueRand`（`ValueRand` 取自 `DT_GuardEquipItemBaseData`），沒有加成倍率。

### 成長道具效果 `UGEExecCalc_GrowthItem`（計算函式 `0x141535040`）
- 增加量（建構子 `0x14134f240` 的 Map）：ATK_UP / DEF_UP 的 S/M/L/LL 分別 +1/+2/+4/+8；MAXHP_UP、MAXSP_UP +10。
- 加到角色存檔的能力值上，用 `minss 150.0` 封頂。

### 相關結構
- `WeaponSaveData`：`WeaponID`、`id`、`Skill[]`、`attr`（int64，+0x18）、`dataId`、`GetTime`
- `EquipItemSaveData`：`EquipItemID`、`GuardEquipItemID`、`Value`
- `EWeaponAttrFlag`：NONE 0、ATTR_5 1、ATTR_6 2、FIRE 4、THUNDER 8、ZAN 16、WIND 32、NEW_UNIQUE 64、4TH 128

---

## 附錄 C：建置方式

```
source\DW3CE_TopTierDrops\
├─ README.md            本檔
├─ datatable\
│  ├─ build_mod.py      從原版資料套用修改並打包
│  └─ edited_json\      修改後的三張表
└─ dll\
   ├─ dw3ce_re_top_tier_drop.c   version.dll 原始碼
   └─ build.bat         編譯腳本
```

### 資料表
需要 Python 3.10+，以及 `E:\DE3MOD\tools` 下的工具和原版資料。

```bash
cd datatable
python build_mod.py              # 輸出到 .\build\out\
python build_mod.py --package    # 同上，並更新 E:\DE3MOD\mods\DW3CE_TopTierDrops 的成品
python build_mod.py --install    # 同上，並複製到遊戲的 Paks\~mods\
```
- 遊戲路徑預設是 `G:\SteamLibrary\steamapps\common\DW3CE_RE`，可以用環境變數 `DW3CE_GAME_DIR` 覆蓋。
- 寫出的資料會再解碼一次並與預期比對，不一致就中止。

### DLL
需要 Visual Studio 2019 Build Tools。執行 `dll\build.bat`，會產出 `dll\version.dll` 和內容相同的 `dll\dw3ce_re_top_tier_drop.asi`。
確認無誤後，再分別手動複製到 `mods\DW3CE_TopTierDrops\DW3CE_RE\Binaries\Win64\` 和 `mods\DW3CE_TopTierDrops_ASI\DW3CE_RE\Binaries\Win64\`。
（`vswhere.exe is not recognized` 的訊息可以忽略。）

### 遊戲更新後
1. `dw3ce_re_top_tier_drop.log` 出現 `signature NOT found` → 重新分析該位置，更新 `dw3ce_re_top_tier_drop.c` 的特徵碼。
2. 資料表有變 → 依 `E:\DE3MOD\tools\game_data\README.md` 重新匯出原版資料，確認 round-trip 仍然逐位元組一致，再執行 `build_mod.py --package`。
