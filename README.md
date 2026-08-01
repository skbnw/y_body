# y_body

Yahoo News Scraper Repository.

## GCS JSON 並列パス（CSV とは別系統）

既存の Schedule-g01〜g16（CSV をリポジトリにコミット）は**変更しません**。  
別ワークフローが CSV を記事単位 JSON に変換し、GCS へアップロードします。

| 項目 | 内容 |
|------|------|
| ワークフロー | `.github/workflows/upload-yahoo-json-gcs.yml` |
| スクリプト | `py/csv_to_gcs_yahoo_json.py` |
| 入力 CSV | `{YYYY-MMDD}/{YYYYMMDD}-{media}.csv`（スクレイパーと同じ） |
| GCS | `gs://gcs-json-collector-raw/yahoo/YYYY/MM/{id}.json` |
| 主 cron | **UTC 22:00 = JST 07:00**（g16 ≈ UTC 21:00 の約1時間後） |
| 手動 | Actions →「Upload Yahoo JSON to GCS」→ Run workflow |
| 副トリガー | Schedule g16 成功後の `workflow_run`（任意） |

**JST 03:00 / 04:00 は使わない。** g01–g16 は UTC 16:00–21:00（≈ JST 01:00–06:00）のため、深夜帯だと後半メディアが未完了になる。

### GitHub に設定する値（Variables）

設定済み（Repository variables）:

| Name | Value |
|------|-------|
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `projects/953881338951/locations/global/workloadIdentityPools/github-y-body/providers/github` |
| `GCP_SERVICE_ACCOUNT` | `y-body-gcs-uploader@gcs-rss-collector.iam.gserviceaccount.com` |

GCP: SA `y-body-gcs-uploader` + WIF pool `github-y-body`（repo `skbnw/y_body` 限定）+ bucket `gcs-json-collector-raw` の `roles/storage.objectAdmin`。

### ローカル dry-run

```powershell
pip install -r py/requirements-gcs.txt
python py/csv_to_gcs_yahoo_json.py --date 2026-0302 --dry-run --limit 3 --local-out output/yahoo_json_smoke
```

## CSS Selector Note (as of 2026-02-25)

Yahoo! News has recently updated its HTML structure, changing many functional classes (hashes) to Styled-Components classes.
The scraper now uses the following stable classes:

- **Article Link**: `sc-1gg21n8-0` (formerly hash-based like `cDTGMJ`)
- **Content Wrapper**: `sc-278a0v-0` (formerly `iiJVBF`)
- **Title**: `sc-3ls169-0` (formerly `dHAJpi`)
- **Time info**: `sc-16vsoxb-1` (formerly `faCsgc`)
- **Article Body**: `article_body` (remains standard)

These `sc-*` classes appear more consistent across different media outlets and page versions as of late February 2026.
If scraping fails with "Found 0 articles", please verify if these classes have been updated again.
