# matter-hub 公開準備（1週間・日別タスク）

目的: 社内の数人が安全に利用できる状態で `matter-hub` を1週間で公開する。
前提: 現状は開発向け構成（認証未実装、Vite dev運用、CI未整備）を含むため、公開最低ラインを優先して整える。

---

## 現時点の確定事項（2026-04-29）

- [x] ホスティング方針: **A案（安価VPS 1台 + Docker Compose）**
- [x] アクセス制限方針: **認証済みメールアドレスのドメイン制限**
- [ ] VPS事業者の最終決定（DigitalOcean / Vultr / Hetzner など）
- [ ] 許可ドメイン一覧の確定（例: `example.co.jp`）

メモ:
- メールドメイン制限は「認証済みメールアドレス」が取得できることが前提。
- フロントから渡されたメール文字列は信用せず、IDプロバイダ検証済みトークンから `email` を取得する。
- 当面はハードコード実装で開始し、運用安定後に環境変数化を検討する。

---

## Day 1: 公開方針の確定と要件凍結（Must）

- [ ] 公開範囲を決定する（社内VPN限定 / 社内ネットワーク限定 / インターネット非公開）
- [ ] 認証方式を決定する（社内SSO/OIDC優先。難しければ暫定構成を定義）
- [ ] 認可ポリシーを決定する（閲覧者 / 運用者 / 管理者）
- [ ] デプロイ先を決定する（単一VM + Docker Compose）
- [ ] 運用責任者を決定する（一次対応、二次対応、承認者）
- [ ] 成功条件を定義する（公開判定チェックリストを確定）
- [ ] 許可メールドメイン一覧を確定する（本番反映対象）

成果物:
- `docs/publication/decision-log.md`（意思決定ログ）
- `docs/publication/release-criteria.md`（公開判定基準）

---

## Day 2: 認証・認可とAPI保護（Must）

- [ ] Web APIに認証を導入する
- [ ] 検証済み `email` クレームを取得できるようにする
- [ ] 許可メールドメインをハードコードし、ドメイン不一致を `403` にする
- [ ] 更新系API（sync/delete/restore/summarize等）に認可チェックを適用する
- [ ] 未認証/権限不足時のレスポンス仕様を統一する（401/403）
- [ ] フロント側で認証エラー時の導線を整備する（再ログイン/問い合わせ案内）
- [ ] 管理者操作と一般操作の境界を明文化する

成果物:
- 実装PR（認証・認可）
- `docs/security/account-and-access.md`（権限仕様）

---

## Day 3: 本番構成化（フロント配信・CORS・環境変数）（Must）

- [ ] フロントを `vite build` + 静的配信へ変更する（`npm run dev` を本番から排除）
- [ ] API配信と静的配信のルーティングを確定する（例: `/` と `/api`）
- [ ] CORSを本番設定に固定する（`MATTER_HUB_CORS_STRICT=1`、許可Origin最小化）
- [ ] VPSの公開ポートを最小化する（80/443のみ公開）
- [ ] API側 `.env.example` を作成する（必須/任意/説明付き）
- [ ] 本番環境変数一覧を文書化する（初期設定手順含む）
- [ ] 起動設定から開発オプション（`--reload` など）を除去する

成果物:
- 実装PR（本番配信構成）
- `docs/operations/env-vars.md`（環境変数ガイド）

---

## Day 4: データ保護（シークレット管理・バックアップ/復元）（Must）

- [ ] トークン保存方針を確定する（保存場所、アクセス権、ローテーション）
- [ ] シークレット取り扱いルールを明文化する（共有禁止、期限、失効手順）
- [ ] SQLiteバックアップ手順を作成する（定期、世代、保管先）
- [ ] SQLiteリストア手順を作成し、実際に復元テストを行う
- [ ] 障害時のRTO/RPO目標を定める

成果物:
- `docs/operations/backup-restore.md`
- `docs/security/secrets-policy.md`
- 復元テスト記録

---

## Day 5: 可観測性と品質ゲート（Must/Should）

- [ ] `/healthz` と `/readyz` を追加する
- [ ] 最低限のログ方針を適用する（エラー追跡可能、機微情報は出さない）
- [ ] CIを導入する（最低: `pytest` + frontend build）
- [ ] 可能ならフロントのlint/typecheckを追加する
- [ ] 失敗時通知（Slack等）を設定する

成果物:
- 実装PR（healthcheck/CI）
- `docs/operations/monitoring.md`

---

## Day 6: 運用ドキュメント・利用者導線整備（Must）

- [ ] 利用者オンボーディング手順を作成する（申請→認証→初回同期→基本操作）
- [ ] 運用Runbookを作成する（再起動、障害切り分け、復旧、ロールバック）
- [ ] 問い合わせ窓口・対応時間・一次回答目安を明記する
- [ ] FAQ（よくある失敗と対処）を作成する
- [ ] 退職/異動時の権限剥奪手順を追記する

成果物:
- `docs/publication/onboarding.md`
- `docs/operations/runbook.md`
- `docs/support/contact.md`
- `docs/support/faq.md`

---

## Day 7: リハーサルと公開判定（Must）

- [ ] 公開前チェックリストを全項目確認する
- [ ] 想定障害リハーサルを実施する（認証失敗、API停止、DB復元）
- [ ] 数人の社内ユーザーで受け入れ確認を行う
- [ ] 残課題を `Must/Should/Could` に再分類して合意する
- [ ] 公開Go/No-Go判定を実施し、Goなら公開・告知する

成果物:
- `docs/publication/go-live-checklist.md`
- `docs/publication/uat-report.md`
- 公開アナウンス文面

---

## 公開判定チェックリスト（抜粋）

- [ ] 利用者認証が有効
- [ ] 更新系APIに認可がある
- [ ] CORSが本番設定
- [ ] フロントが本番ビルド配信
- [ ] `.env`/シークレット運用ルールが文書化済み
- [ ] バックアップ/復元を検証済み
- [ ] `/healthz` `/readyz` が監視可能
- [ ] CIが必須チェックとして動作
- [ ] Runbook/問い合わせ導線が利用者に共有済み

---

## 参考（現状根拠ファイル）

- `docs/features.md`
- `README.md`
- `compose.yml`
- `matter_hub/webapp/api_routes.py`
- `matter_hub/webapp/main.py`
- `matter_hub/config.py`
- `matter_hub/db.py`
- `frontend/package.json`

---

## 実装メモ（メールドメイン制限）

- 想定実装:
  - 認証ミドルウェア/依存関数で `email` を取得
  - `ALLOWED_EMAIL_DOMAINS = {"example.co.jp"}` のようにハードコード
  - `email` の `@` 以降が未許可なら `403 Forbidden`
- 適用範囲:
  - 少なくとも更新系API（`sync`, `delete`, `restore`, `summarize`）
  - 可能なら `/api` 全体
- セキュリティ注意:
  - メールアドレスは必ず署名検証済みトークン由来に限定する
  - クライアント送信値（ヘッダー/ボディ）を認可判定に使わない
