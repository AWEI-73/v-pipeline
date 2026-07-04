# Supervisor Correction: stress_provider_stock_20260704_master_report.json

The raw master report is internally inconsistent and should not be read as
standalone truth.

Observed correction:

- `normal` and `multi` are labeled `provider_classification=true_provider`.
- Their search reports contain Pexels candidates.
- Their run folders contain downloaded files:
  - `runs/stress_provider_stock_20260704_01_normal_city_solo/fetch/stock_download.mp4`
    at 8,381,180 bytes.
  - `runs/stress_provider_stock_20260704_02_multi_query_multi_segment/fetch/stock_download.mp4`
    at 9,252,536 bytes.
- The same master report still records `live_provider_result=false`,
  `fail_closed=true`, and `stop_point=provider/search error or partial
  outcome`.

Supervisor interpretation: live provider calls and downloads did occur, but the
probe's summary labels are not reliable enough to claim a clean provider-chain
pass. Use the downloaded artifacts plus per-run reports for evidence, and treat
the master summary as corrected by this note.
