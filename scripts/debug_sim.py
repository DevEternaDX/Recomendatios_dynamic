from datetime import date
import os, sys

# Asegura que el directorio raíz del repo está en sys.path para poder importar 'backend'
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.rules_engine.features import load_base_dataframe, build_features
from backend.rules_engine.engine import evaluate_user
from backend.rules_engine.persistence import get_enabled_rules

USER = "4f620746-1ee2-44c4-8338-789cfdb2078f"
DAY = date(2025, 3, 5)
TENANT = "default"

print("Loading dataframe...")
df = load_base_dataframe()
print("df rows:", len(df))

print("Building features...")
feats = build_features(df, DAY, USER)
print("steps feature:", feats.get("steps"))

print("Enabled rules for tenant:", TENANT)
en = get_enabled_rules(TENANT)
print("enabled count:", len(en))
print([r.id for r in en])

print("Evaluating user with debug=True...")
res = evaluate_user(USER, DAY, tenant_id=TENANT, debug=True)
try:
    results, per_rule_debug = res
    print("results count:", len(results))
    print("per_rule_debug count:", len(per_rule_debug))
    for d in per_rule_debug:
        print(d)
except Exception as e:
    print("evaluate_user returned:", res)
    print("exception:", e)
