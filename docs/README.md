# 設計書インデックス

このディレクトリは、現在のコードを読み解いて整理した設計書です。

- [current-design.md](current-design.md): 現行システムの目的、構成、処理フロー、ファイル責務
- [data-contracts.md](data-contracts.md): `state/` と `daily/` に置かれるデータの契約
- [operations.md](operations.md): セットアップ、日次運用、障害時の見方、既知の注意点
- [mobile-notification-design.md](mobile-notification-design.md): LINE 通知と携帯閲覧の確定設計

現状の実装は、Mac ローカルで note 記事を収集し、AI が評価・選抜・執筆した Markdown を `daily/` に出力し、Mac の通知センターへ完了通知を出す構成です。

今後の携帯対応は、Phase 1 で「ローカル実行後に GitHub へ自動 push し、LINE Messaging API で当日の GitHub URL を送る」構成にします。Phase 2 では、UI から `気になる` フィードバックを返して学習に使う仕組みを検討します。
