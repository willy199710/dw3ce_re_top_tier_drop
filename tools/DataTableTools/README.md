# DataTableTools — DataTable 解析／編輯工具（自製）

針對 DW3CE_RE（UE 5.6、cooked unversioned 資料）寫的小工具，**不需要 `.usmap`**，也不需要開遊戲：
資料結構直接從遊戲執行檔中 UHT 產生的反射參數靜態讀出來。

需求：Python 3.10+；`xref.py` 另需 `numpy`、`capstone`（本機已安裝：numpy 2.2.6、capstone 5.0.7）。

遊戲路徑預設為 `G:\SteamLibrary\steamapps\common\DW3CE_RE`，可用環境變數 `DW3CE_GAME_DIR` 覆蓋。

## 檔案

| 檔案 | 用途 |
|---|---|
| `reflect.py` | 從執行檔讀出 struct／enum／class 的反射資訊（欄位名稱、型別、順序、enum 值），以及 IAT 匯入表 |
| `dt2json.py` | cooked DataTable（`.uasset` + `.uexp`）→ JSON |
| `json2dt.py` | JSON → cooked DataTable（大小改變時會自動修正 uasset 的 size 欄位） |
| `list_utoc.py` | 列出 `.utoc` 目錄索引中的所有檔案路徑 |
| `xref.py` | 反組譯輔助：找 RIP 相對位址的參照、找 call、用 `.pdata` 找函式邊界、capstone 反組譯 |

## 用法

### 查結構
```bash
python reflect.py EquipItemBaseData_TableRow WeaponSaveData
```
```python
import reflect
reflect.schema('DropRandomTable_TableRow')   # 欄位清單（含父類別），順序即 unversioned 序列化順序
reflect.imports()                           # {IAT 位址: 'dll!函式名'}
```

### 解出／改回一張表（完整流程）
```bash
# 1. 從遊戲容器取出 legacy 格式
..\retoc\retoc.exe to-legacy --no-shaders -f DT_WeaponRankData "<遊戲>\DW3CE_RE\Content\Paks" out
# 2. 轉 JSON（輸出到 <檔名>.json）
python dt2json.py out\DW3CE_RE\Content\DataAsset\DT_WeaponRankData
# 3. 編輯 JSON 後寫回（第一個參數是原檔，提供 name map 與檔頭）
python json2dt.py out\...\DT_WeaponRankData edited.json mod\DW3CE_RE\Content\DataAsset\DT_WeaponRankData
# 4. 打包（輸入資料夾需含 scriptobjects.bin）
..\retoc\retoc.exe to-zen --version UE5_6 mod zMyMod_P.utoc
```
寫回的 JSON 可以用列名或 enum 名稱（例如 `"SkillTypeID_Blue"`），也可以用數字。

### 反組譯輔助
```python
from xref import *          # 匯入時會掃描整個 .text，約需 10 秒
xrefs(0x149c55a18)          # 哪些指令以 RIP 相對方式參照這個位址
calls(0x141537560)          # 誰 call 了這個函式
func_start(0x141516712)     # 由 .pdata 取得所在函式（或 chunk）的起訖
dis(0x1415162a0, 50)        # 反組譯
```

## 驗證狀態

- 168 張 `DataAsset/DT_*` 中，**150 張**可以解碼，且「解碼 → 編碼」與原檔**逐位元組相同**。
- 解不出的 18 張使用了尚未實作的型別（如 static array、部分 struct 與 FText history），目前用不到。
- 支援的型別：整數／浮點、bool、enum（依底層型別）、FName、FString、FText（部分）、SoftObject、Array、Set、Map、巢狀 struct、Vector/Rotator/Color 等。

## 反射參數 layout（UE 5.6 實測）

| 結構 | 欄位位移 |
|---|---|
| `FStructParams` | Name `+24`、PropertyArray `+32`、NumProperties u16 `+40`、SizeOf u16 `+42`；Super 函式 `+8` |
| `FPropertyParams` | Name `+0`、GenFlags u8 `+24`（低 6 bits 為型別）、ArrayDim u16 `+48`、Offset u16 `+50`、型別專屬指標 `+56`（enum／struct 的 Z_Construct 函式） |
| `FEnumParams` | Name `+16`、EnumeratorParams `+32`（每筆 `{char* 名稱, int64 值}`）、NumEnumerators int16 `+44` |
| `FClassParams` | StaticClass 函式 `+0`、PropertyArray `+40`、NumProperties u8 `+58` |

- Enum 的底層屬性（名稱 `UnderlyingType`）與 Array 的 inner 屬性，在 PropertyArray 裡排在容器**前面**、名稱與容器相同。
- Bool 屬性 `+50` 不是 offset（是 ElementSize），bool 的實際位置要靠 SetBit 函式，所以只用陣列順序判斷。
- Unversioned 序列化：header 是 uint16 片段（skip 7 bits／has-zero 1 bit／is-last 1 bit／count 7 bits），之後是 zero mask，再來只寫非零值；只有與預設值不同的欄位會出現在 header 中。

## 開發歷程

1. **起點**：想看 DataTable 內容，正規作法要先裝 UE4SS 進遊戲產生 `.usmap`。
   注意到執行檔內保留完整的 UHT 反射參數（屬性名稱、型別、offset），改寫靜態讀取器，免去改動遊戲。
2. **第一版** `dt2json` 以 heuristic 找 row 資料起點（嘗試每個起點，必須剛好讀到檔尾才採用），這個「剛好讀到檔尾」也成為正確性的強驗證。
3. **修正**
   - name map 起點：原本搜尋 `/Game/`，會誤抓 summary 裡的 PackageName → 改為從 summary 讀 NameCount／NameOffset。
   - enum 參數 layout 與預期不同 → dump 原始 bytes 後校正為上表。
   - inner／underlying 屬性原本以 `offset == 0` 判斷，會誤吃掉 offset 0 的一般欄位（例如 `EquipItemSaveData.EquipItemID`）→ 改為比對名稱。
   - `FName None` 應視為零值（否則 55 張表無法編碼）。
4. **`json2dt`**：先追求與原檔逐位元組相同，150 張表全部通過後才用來產生 mod。
   之後為了填入原本為 0 的欄位（檔案變長），加上單一 export 的 `SerialSize` 與 summary `BulkDataStartOffset` 修正。
5. **`xref.py`**：為了找武器生成邏輯而寫。資料表 → asset class → 載入函式 → getter → 呼叫端，
   最後由 `rand()` 的匯入呼叫（10 次）鎖定武器生成函式 `0x1415162a0`。
