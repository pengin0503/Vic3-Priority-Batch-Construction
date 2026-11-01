# Priority Batch Construction

**日本語** | [English](README.en.md)

Victoria 3 1.14.xで建設をまとめて最高優先度に追加するための実験的MODです。

## 操作

| 操作 | 建設数 |
|---|---|
| 通常クリック | 1 |
| Shift＋クリック | 5 |
| Ctrl＋クリック | 10 |
| Alt＋クリック | 最高優先度で1 |
| Shift＋Alt＋クリック | 最高優先度で5を意図 |
| Ctrl＋Alt＋クリック | 最高優先度で10を意図 |

Shift／Ctrlによる5件／10件の一括キャンセルも維持します。**組み合わせキーの挙動はゲーム内で未確認**です。

## Windowsへの導入

Python 3.10以上とVictoria 3の完全な1.14.xのインストールが必要です。パッケージを展開し、フォルダ内でPowerShellを開いて実行します。

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\install.ps1
```

ゲームを検出できない場合は `-GameDir "K:\SteamLibrary\steamapps\common\Victoria 3"` を追加して実際の場所を指定します。生成先は通常 `Documents\Paradox Interactive\Victoria 3\mod\Vic3PriorityBatch` です。ランチャーで有効化し、[ゲーム内確認手順](docs/runtime-verification.md)に従ってください。

mod-only ZIPが配布されている場合は、`Vic3PriorityBatch` を上記の `mod` フォルダに展開して有効化できます。その場合Pythonは不要です。生成されたMODは元のゲームファイルに依存するため、ゲーム更新後は再生成してください。

## 互換性と制限

ゲームのGUIファイルを変更する他のMODとは競合する場合があります。GUI MODに合わせる場合は元のMODを有効のまま、対応するGUIオーバーレイを指定して生成し、生成パッチを後に読み込みます。詳細は[GUIの対応手順](docs/gui-audit-2026-10-04.md)を参照してください。

Shift＋AltやCtrl＋Altが期待どおりに処理されない場合、`tools/install.ps1 -Probe` で診断版を作り、[診断手順](docs/modifier-dispatch-probe.md)に従ってください。必要に応じて同梱のAutoHotkey v2用ヘルパーを使えますが、導入前に単一操作と5／10件の結果を確認してください。正常に動作する純MODとヘルパーの同時使用は二重処理の原因になります。
