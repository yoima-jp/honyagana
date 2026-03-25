---
name: minecraft-version-up
description: >
  Honyagana resource pack version-up workflow for Minecraft updates. Use when
  the pack needs to be moved to a new Minecraft release and the language files,
  item assets, or pack metadata must be reconciled with the latest vanilla data.
---

# Honyagana Version-Up Skill

Minecraft のバージョン更新時に、このリソースパックへ反映する作業をまとめた手順です。

## 使う場面

- 新しい Minecraft バージョン向けにパックを更新するとき
- `ja_jp.json` の未更新キーや漢字残りを洗い出したいとき
- 新規追加アイテムの表示がそのまま残っているとき
- `pack.mcmeta` の互換情報を更新するとき

## 手順

1. 対象バージョンの最新 vanilla データを取る
   - 公式の version manifest から対象バージョンを確認する
   - そのバージョンの asset index を取得して `minecraft/lang/ja_jp.json` を読む

2. `ja_jp.json` を比較する
   - 取得した vanilla `ja_jp.json` と `Honyagana/assets/minecraft/lang/ja_jp.json` を比較する
   - 足りないキー、名称変更されたキー、漢字が残った文言を埋める
   - ほにゃがな表記は、必要なら既存の語尾・言い回しに合わせて統一する

3. 新規アイテム/ブロックを確認する
   - vanilla 側で増えた item/block のキーを探す
   - 必要なら以下を追加する
     - `assets/minecraft/items/<id>.json`
     - `assets/minecraft/models/item/honyagana_block/<id>.json`
     - `assets/minecraft/textures/item/<id>.png`
   - 文字だけで表現する方針に合わせて、生成テクスチャを作る

4. `pack.mcmeta` を更新する
   - 新しいバージョンの resource pack format に合わせる
   - `min_format` / `max_format` を使う形式なら `pack_format` は置かない

5. 取りこぼしを潰す
   - `git grep` や差分スクリプトで、未対応キーが残っていないか確認する
   - 表示名が旧バージョン向けのままなら、最新版の文言へ合わせる

6. 最後に検証する
   - JSON が壊れていないか確認する
   - 追加した item/model/texture が同じ名前で揃っているか確認する
   - `git status` で更新漏れがないか見る

## このパックの考え方

- アイテムやブロックは「文字だけの見た目」で統一する
- 新要素は見た目をそのままにしない
- 言語ファイルは最新 vanilla を基準にする
- 旧バージョン向けと言われないように、互換表記も毎回見直す
