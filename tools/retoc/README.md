# retoc — IoStore 解包／打包工具（第三方）

- 作者：trumank，<https://github.com/trumank/retoc>
- 版本：**v0.1.5**（2026-01-02 發佈），`retoc_cli-x86_64-pc-windows-msvc.zip`
- 下載檔 SHA-256 與官方 `.sha256` 相符：`cc036b06ad3bdcf7003690b00d82719980c374e48a95bf0654f9959148d263aa`
- `retoc.exe` SHA-256：`a145f3557ec60b163ed1b78b2f380232d2753fa30350c8013c98e171db3ae7e7`
- 授權見 `LICENSE`；官方說明保留為 `README.upstream.md`

## 在本專案的用途

UE5 的 IoStore 容器（`.utoc`／`.ucas`）存的是 Zen 格式資料，一般工具無法直接編輯。
retoc 負責兩個方向的轉換：

- Zen → Legacy（`.uasset`／`.uexp`）：取出來給 `DataTableTools` 解析
- Legacy → Zen：把修改後的資料打包成 mod

## 常用指令

`<Paks>` = `G:\SteamLibrary\steamapps\common\DW3CE_RE\DW3CE_RE\Content\Paks`

```bash
# 容器資訊／列出檔案
retoc info <Paks>\DW3CE_RE-Windows.utoc
retoc list --path --size --hash <Paks>\DW3CE_RE-Windows.utoc

# 取出特定資源（-f 是檔名過濾；輸入給整個 Paks 資料夾，才會一起讀到 global.utoc）
retoc to-legacy --no-shaders -f DataAsset/DT_ <Paks> out

# 打包成 mod（輸入資料夾需包含 scriptobjects.bin 與 <專案名>\Content\... 結構）
retoc to-zen --version UE5_6 mod_src zMyMod_P.utoc
```

產出的 `.pak`／`.utoc`／`.ucas` 三個檔案一起放進 `Paks\~mods\`，檔名結尾 `_P` 代表 patch，優先順序高於原版。

## 注意事項

- **引擎版本一定要用 `UE5_6`**：
  用 UE5_3／5_4／5_5 打包會出現 `failed to fill whole buffer`；
  UE5_6 打包未修改的資源，chunk hash 與原版完全一致（`DT_SkillNumRandomTable` 為 `38cf14dd…`），因此確認是 5.6。
- `to-zen` 的輸入資料夾若缺少 `scriptobjects.bin` 也會出現 `failed to fill whole buffer`。這個檔案由 `to-legacy` 產生，已備份在 `..\game_data\legacy\`。
- 遊戲的 `.pak` 索引有 AES 加密，但 utoc／ucas 沒有加密，所以不需要金鑰。
