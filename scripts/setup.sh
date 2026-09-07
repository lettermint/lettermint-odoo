#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export ODOO_MAJOR="${1:-19}"
case "$ODOO_MAJOR" in
  19) export ODOO_PORT=8069 ;;
  18) export ODOO_PORT=8070 ;;
  *) echo 'Use version 18 or 19.' >&2; exit 1 ;;
esac
python3 - <<'PY'
import os, secrets
from pathlib import Path
path = Path('.env')
if not path.exists():
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as stream:
        stream.write('ODOO_DEMO_PASSWORD=' + secrets.token_urlsafe(24) + '\n')
PY
python3 scripts/stage.py "$ODOO_MAJOR"
docker compose up -d db
docker compose stop odoo
docker compose run --rm --no-deps odoo odoo -d lettermint_demo \
  -i contacts,sale_management,account,lettermint_mail,lettermint_mass_mailing \
  -u lettermint_mail,lettermint_mass_mailing --stop-after-init --without-demo=all --max-cron-threads=0 --http-port=0
docker compose run --rm -T --no-deps odoo odoo shell -d lettermint_demo \
  --no-http --max-cron-threads=0 < scripts/seed.py
docker compose up -d --wait odoo
printf 'Odoo %s: http://localhost:%s/web?db=lettermint_demo\nLogin: admin. Password: ODOO_DEMO_PASSWORD in .env\n' "$ODOO_MAJOR" "$ODOO_PORT"
