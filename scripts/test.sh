#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export ODOO_MAJOR="${1:-19}"
python3 scripts/stage.py "$ODOO_MAJOR"
docker compose up -d db
docker compose run --rm --no-deps odoo odoo -d lettermint_test \
  -i lettermint_mail,lettermint_mass_mailing -u lettermint_mail,lettermint_mass_mailing \
  --test-enable --test-tags /lettermint_mail,/lettermint_mass_mailing \
  --stop-after-init --without-demo=all --max-cron-threads=0 --http-port=0
