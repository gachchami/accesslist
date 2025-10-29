#!/usr/bin/env bash
set -e
export FLASK_APP=app
python - <<'PY'
from app import app, db
with app.app_context():
    db.drop_all()
    db.create_all()
print("✅ Database initialized (acl.db)")
PY
