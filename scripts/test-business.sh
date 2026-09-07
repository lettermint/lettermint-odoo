#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export ODOO_MAJOR="${1:-19}"
docker compose run --rm -T --no-deps odoo odoo shell -d lettermint_demo \
  --no-http --max-cron-threads=0 < scripts/check_business_flows.py
