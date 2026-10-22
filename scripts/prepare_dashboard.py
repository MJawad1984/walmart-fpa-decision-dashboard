"""Build deterministic, historical-only dashboard inputs and an auditable run record."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from analysis import load_rules, load_financials, load_guidance, export_outputs


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    output = ROOT / 'generated'
    output.mkdir(exist_ok=True)
    db = sqlite3.connect(output / 'governance_ledger.sqlite')
    db.execute('''CREATE TABLE IF NOT EXISTS governance_ledger (
        timestamp_utc TEXT NOT NULL, run_id TEXT NOT NULL, module TEXT NOT NULL,
        model TEXT NOT NULL, prompt_hash TEXT NOT NULL, input_hash TEXT NOT NULL,
        output_hash TEXT NOT NULL, status TEXT NOT NULL, latency_ms INTEGER NOT NULL,
        error_message TEXT NOT NULL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS deterministic_runs (
        run_id TEXT PRIMARY KEY, timestamp_utc TEXT NOT NULL, input_hash TEXT NOT NULL,
        rules_hash TEXT NOT NULL, output_hash TEXT NOT NULL, status TEXT NOT NULL,
        error_message TEXT NOT NULL)''')
    sources = sorted((ROOT / 'data').glob('*.csv'))
    input_hash = hashlib.sha256(''.join(digest(p) for p in sources).encode()).hexdigest()
    rules_hash = digest(ROOT / 'config/rules.yaml')
    run_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        rules = load_rules()
        wc, guidance = export_outputs()
        financials = load_financials()
        payload = {
            'as_of_date': rules['publication']['as_of_date'],
            'rules': rules,
            'financials': json.loads(financials.to_json(orient='records')),
            'guidance': json.loads(guidance.to_json(orient='records')),
            'working_capital': json.loads(wc.to_json(orient='records')),
            'scope': 'Historical financial analysis and initial public guidance comparison. No internal company budget.',
            'input_hash': input_hash, 'rules_hash': rules_hash,
        }
        path = output / 'dashboard_inputs.json'
        path.write_text(json.dumps(payload, indent=2, allow_nan=False) + '\n')
        output_hash = digest(path)
        db.execute('INSERT INTO deterministic_runs VALUES (?,?,?,?,?,?,?)',
                   (run_id, timestamp, input_hash, rules_hash, output_hash, 'COMPLETED', ''))
        db.commit()
        print(json.dumps({'status': 'COMPLETED', 'run_id': run_id, 'output_hash': output_hash,
                          'llm_calls': db.execute('SELECT COUNT(*) FROM governance_ledger').fetchone()[0]}))
    except Exception as exc:
        db.execute('INSERT INTO deterministic_runs VALUES (?,?,?,?,?,?,?)',
                   (run_id, timestamp, input_hash, rules_hash, '', 'EXCEPTION_PENDING_REVIEW', str(exc)))
        db.commit()
        raise
    finally:
        db.close()


if __name__ == '__main__':
    main()
