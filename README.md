# ZEUS-DB

**ZEUS-DB**（*ZEUS Database Forensic Engine*）は、lab 環境向けの統合 SQLite フォレンジック解析エンジンです。

[DC3 sqlite-dissect](https://github.com/dod-cyber-crime-center/sqlite-dissect) をコアに、bring2lite / fqlite / undark・sqbrite 等の **概念・アルゴリズムを再実装で統合** しています（fqlite Java コードは非流用）。

## できること

- 本体 DB + WAL / rollback journal の **read-only** 解析（`-wal` と `-journal` は排他）
- WAL コミット単位の **バージョンタイムライン**
- 削除レコード復元: **freeblock / unallocated / freelist / Boyer-Moore / rollback journal / dropped table**
- 破損 DB 向け **raw page salvage**（`--salvage`）— **トリアージ指標**（セル復元ではない）
- **provenance 付き** JSON / TSV / CASE 出力（報告書向け・補助検証向け）
- FastAPI サービス + [AISSS](https://github.com/matrix9neonebuchadnezzar2199-sketch/Aisss) worker 連携

## クイックスタート

```powershell
uv sync --all-groups
uv run zeusdb analyze sample.db --carve --json output.json
uv run pytest
```

## HTTP サービス

```powershell
uv run uvicorn service.app:app --host 0.0.0.0 --port 8090
# GET  /health
# POST /analyze/upload
```

## ドキュメント

| ドキュメント | 内容 |
|-------------|------|
| [docs/00-index.md](docs/00-index.md) | ドキュメント索引 |
| [docs/01-algorithms-overview.md](docs/01-algorithms-overview.md) | **アルゴリズム解説**（削除領域・パイプライン・各 Recovery 手法） |
| [docs/02-source-tools-mapping.md](docs/02-source-tools-mapping.md) | **吸収元ツール対応表**（DC3 / bring2lite / fqlite 等） |
| [docs/03-architecture.md](docs/03-architecture.md) | レイヤ構成・JSON 契約・CLI |
| [docs/aisss-integration.md](docs/aisss-integration.md) | AISSS Compose / Worker 連携 |

## アーキテクチャ（概要）

```
DB/WAL/journal → Reader (sqlite-dissect)
              → Version (WAL 版タイムライン)
              → Recovery (freeblock/unallocated/freelist/BM/…)
              → Output (provenance 付き JSON/TSV/CASE)
              → CLI / HTTP / AISSS
```

## 吸収元ツール（要約）

| ソース | 形態 | 役割 |
|--------|------|------|
| **sqlite-dissect (DC3)** | コード vendor | Reader / Version / Signature / Carver 基盤 |
| **bring2lite (DFRWS2019)** | 概念 | freeblock / unallocated / freelist |
| **fqlite (論文)** | 概念再実装 | Boyer-Moore carver、dropped table |
| **undark / sqbrite** | 概念再実装 | `--salvage` raw page scan |
| **walitean** | Version Layer に包含 | WAL タイムライン |

詳細は [docs/02-source-tools-mapping.md](docs/02-source-tools-mapping.md) を参照。

## ライセンス

- ZEUS-DB: MIT
- sqlite-dissect: DC3 Open Source License — [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
