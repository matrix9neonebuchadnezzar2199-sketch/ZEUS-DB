# アーキテクチャ

## レイヤ構成

```
入力 (DB / WAL / journal / 破損DB)
  ↓
Reader Layer     … sqlite-dissect fork（read-only パース）
  ↓
Version Layer    … WAL/journal を commit 単位で版管理
  ↓
Recovery Layer   … 削除レコード復元（複数アルゴリズム）
  ↓
Salvage Layer    … 破損 DB 救出（オプション）
  ↓
Output Layer     … provenance 付き JSON / TSV / CASE
  ↓
CLI / HTTP       … zeusdb / FastAPI / AISSS worker
```

## ディレクトリ

```
ZEUS-DB/
├── vendor/sqlite-dissect/     # DC3 コア（fork/vendor）
├── src/zeusdb/
│   ├── reader/                # アーティファクト読込
│   ├── version/               # タイムライン
│   ├── recover/               # 削除復元アルゴリズム群
│   ├── salvage/               # 破損 DB salvage
│   ├── output/                # JSON / TSV / CASE
│   ├── engine.py              # ForensicEngine オーケストレータ
│   ├── models.py              # NormalizedRecord / Provenance
│   └── cli.py                 # CLI
├── service/                   # FastAPI + Dockerfile
├── tests/                     # pytest + 合成 DB フィクスチャ
└── docs/                      # 本ドキュメント群
```

## データ契約（JSON schema 1.0）

`AnalysisResult.to_dict()` の主要フィールド:

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `schema_version` | `"1.0"` | 契約バージョン |
| `database_path` | string | 本体 DB パス |
| `wal_path` / `journal_path` | string \| null | サイドカー |
| `page_size` / `encoding` | number / string | ヘッダ情報 |
| `tables` | string[] | 対象テーブル名 |
| `timeline` | TimelineEntry[] | 版タイムライン |
| `records` | NormalizedRecord[] | 統一レコード |
| `summary` | object | total / live / deleted 件数 |

### NormalizedRecord

```json
{
  "table_name": "users",
  "row_id": 1,
  "columns": {"name": "Alice", "email": "alice@lab.local"},
  "is_live": false,
  "is_deleted": true,
  "provenance": {
    "source": "freeblock",
    "algorithm": "bring2lite-freeblock+sqlite-dissect",
    "page_number": 2,
    "file_offset": 8144,
    "version": 0,
    "confidence": 0.85
  }
}
```

## CLI オプション

| オプション | 既定 | 説明 |
|-----------|------|------|
| `--carve` | off | 削除レコード復元を有効化 |
| `--no-freelist` | — | freelist carve 無効 |
| `--no-boyer-moore` | — | Boyer-Moore carver 無効 |
| `--salvage` | off | 破損 DB raw page scan |
| `--json` / `--tsv` / `--case` | — | 出力先 |
| `--wal` / `--journal` | 自動検出 | 明示パス |
| `--tables` | 全テーブル | カンマ区切り限定 |
| `--relaxed` | — | strict format check 無効 |

## HTTP エンドポイント

| メソッド | パス | 用途 |
|---------|------|------|
| GET | `/health` | ヘルスチェック |
| POST | `/analyze/upload` | ファイルアップロード解析 |
| POST | `/analyze/path` | マウント済みパス解析 |
| POST | `/analyze/text` | RAG 向けテキスト要約 |

AISSS 連携の詳細は [aisss-integration.md](aisss-integration.md) を参照。
