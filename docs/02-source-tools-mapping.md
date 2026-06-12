# ソースツール対応表

ZEUS-DB は複数ツールの **概念・アルゴリズム** を統合しています。コードの直接流用は sqlite-dissect（DC3）のみです。fqlite（Java/GPL）等は **概念再実装** です。

## 一覧

| ソース | 吸収形態 | ZEUS-DB での役割 | 実装 |
|--------|---------|-----------------|------|
| [sqlite-dissect](https://github.com/dod-cyber-crime-center/sqlite-dissect) (DC3) | **コード vendor** | Reader / Version / Signature / Carver 実行基盤 | `vendor/sqlite-dissect/` |
| [bring2lite](https://github.com/bring2lite/bring2lite) (DFRWS 2019) | 概念 → SignatureCarver | freeblock / unallocated / freelist | `recover/freeblock.py` 等 |
| [fqlite](https://github.com/pawlaszczyk/fqlite) (論文) | 概念再実装 | Boyer-Moore carver、dropped table | `recover/carver.py`, `dropped_table.py` |
| [xsqlite](https://github.com/NetherlandsForensicInstitute/xsqlite) (NFI) | 未実装（将来の検証基準） | クロスチェック用 | — |
| [walitean](https://github.com/n0fate/walitean) | Version Layer に包含 | WAL→DB 相当 | `version/timeline.py` 経由 |
| sqlite-carver / SQLite-Deleted-Records-Parser | 出力形式参考 | TSV エクスポート | `output/tsv_export.py` |
| [undark](https://github.com/inflex/undark) / [sqbrite](https://github.com/mattboyer/sqbrite) | 概念再実装 | 破損 DB salvage | `salvage/raw_carver.py` |

---

## 1. sqlite-dissect（DC3）— コア基盤

**出自**: 米国防総省サイバー犯罪センター（DC3）。公的機関開発・公開。

### 吸収した機能

| 機能 | 用途 |
|------|------|
| ページ / B-tree / serial type / varint / overflow パーサ | 低レベル read-only 解釈 |
| `VersionHistory` + WAL フレーム解析 | コミット単位の版管理・タイムライン |
| `Signature` | スキーマから列型フィンガープリント生成 |
| `SignatureCarver` | freeblock / unallocated の実 carve 処理 |
| `VersionHistoryParser` | WAL 各版での carved_cells 収集 |

### ZEUS-DB でのラッパ

- `reader/database.py` — アーティファクト束ね（DB + WAL + journal）
- `version/timeline.py` — タイムライン JSON 化
- `recover/engine.py` — live 行 + VersionHistoryParser 連携

### ライセンス

DC3 SQLite Dissect Open Source License（寛容）。`THIRD_PARTY_NOTICES.md` 参照。

---

## 2. bring2lite（DFRWS 2019 査読論文）

**論文**: *bring2lite: A Structural Concept and Tool for Forensic Data Analysis and Recovery of Deleted SQLite Records*

### 吸収したアルゴリズム

| 論文 | SQLite 領域 | ZEUS-DB | algorithm ラベル |
|------|------------|---------|-----------------|
| Algorithm 3 | freeblock | `recover/freeblock.py` | `bring2lite-freeblock+sqlite-dissect` |
| Algorithm 4 | unallocated | `recover/unallocated.py` | `bring2lite-unallocated+sqlite-dissect` |
| freelist trunk/leaf | freelist ページ | `recover/freelist.py` | `bring2lite-freelist+sqlite-dissect` |

### 実装方針

論文の構造解析ロジックの **考え方** を取り込み、実処理は sqlite-dissect の `SignatureCarver` に委譲。bring2lite の Python コードは流用していません。

---

## 3. fqlite（論文 + Java ツール）

**論文**: *Making the Invisible Visible – Techniques for Recovering Deleted SQLite Data Records*

### 吸収した概念

| fqlite の技法 | ZEUS-DB 実装 | 状態 |
|--------------|-------------|------|
| serial-type フィンガープリント + 高速バイト探索 | `recover/carver.py` Boyer-Moore | 実装済み |
| dropped table（DROP 後の SQL 断片） | `recover/dropped_table.py` | 実装済み（簡易版） |
| overflow / 多バイト列 / BLOB 型判定 | sqlite-dissect Signature 経由 | 間接的 |
| GUI / protobuf / bplist デコード | — | v1 未実装 |

### 実装方針

Java ソース（GPL）は **非流用**。論文で説明される Boyer-Moore 探索と dropped table スキャンのみ Python で再実装。

---

## 4. xsqlite（NFI）

**出自**: オランダ法科学研究所（NFI）。

計画上は削除レコード復元結果の **クロスチェック基準** として位置づけ。v1 では独立モジュールは未実装。将来、bring2lite + sqlite-dissect の出力と xsqlite 結果を突合するテストを追加予定。

---

## 5. walitean

WAL ファイルからレコードを抽出して SQLite DB にエクスポートする専用ツール。ZEUS-DB では **専用実装なし**。sqlite-dissect の Version Layer（WAL フレーム → コミット版）で同等のタイムライン解析を行います。

---

## 6. SQLite-Deleted-Records-Parser / sqlite-carver

フォレンジック界隈の定番削除レコードパーサ。TSV 出力が扱いやすい点を参考に、ZEUS-DB は **provenance 列付き TSV**（`output/tsv_export.py`）を提供。carving アルゴリズム自体は sqlite-dissect + bring2lite 系に統合済み。

---

## 7. undark / sqbrite

**思想**: 破損・切断 DB から生き残った行/ページを raw ダンプ。

| 元ツール | ZEUS-DB |
|---------|---------|
| undark (C) — 全行ダンプ | `salvage/raw_carver.py` — ページ単位 non-zero スキャン |
| sqbrite (Python) — オンディスク形式独自解釈 | 同上（`--salvage` フラグ） |

v1 の salvage は **行レベル完全復元ではなく**、データ残存領域の地図（page_number, sample_hex, confidence）を返します。undark/sqbrite 相当の深い cell パースは将来拡張です。

---

## 設計上の統合判断

| 判断 | 理由 |
|------|------|
| sqlite-dissect を vendor 主軸 | DC3 出自・WAL 版管理・SignatureCarver の実績 |
| 他ツールは概念再実装 | ライセンス差異（fqlite GPL）回避、Python 単一言語統合 |
| provenance 必須 | 報告書で「どの根拠で復元したか」を説明可能に |
| read-only 厳守 | 原本不改変（フォレンジック証拠性） |
