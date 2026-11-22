"""Local research records only. No credentials, outcome logs or training side effects."""
from pathlib import Path
from datetime import datetime, timezone
import os,json,hashlib,sqlite3,uuid
ROOT=Path(__file__).resolve().parents[1]
DATABASE_PATH=Path(os.environ.get('BUILDRISK_DATABASE_PATH',str(ROOT/'data/research/buildrisk.sqlite3')))
FIELDS=('mode','model','model_sha256','route','repository','commit_id','workflow_id','workflow_path','run_id','run_attempt','attempt','event_scenario','cutoff','regime','feature_contract','missing_features','raw_probability','threshold','features','sources','notice','history_policy')
def connect():
    DATABASE_PATH.parent.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(DATABASE_PATH);c.row_factory=sqlite3.Row
    c.execute('CREATE TABLE IF NOT EXISTS research_predictions (id TEXT PRIMARY KEY, repository TEXT NOT NULL, created_at TEXT NOT NULL, record_json TEXT NOT NULL)')
    c.execute('CREATE TABLE IF NOT EXISTS research_feedback (id TEXT PRIMARY KEY, prediction_id TEXT NOT NULL, assessment TEXT NOT NULL, created_at TEXT NOT NULL, FOREIGN KEY(prediction_id) REFERENCES research_predictions(id))')
    return c

def save(result):
    record={k:result[k] for k in FIELDS if k in result}
    # Probability is fractional. No heuristic advice overlay is applied here.
    record['advisory_risk_score']=None
    record['raw_probability_units']='fraction-0-to-1'
    record['input_sha256']=hashlib.sha256(json.dumps({k:record.get(k) for k in ('repository','commit_id','workflow_id','run_id','run_attempt','cutoff','feature_contract','route','features')},sort_keys=True,allow_nan=False).encode()).hexdigest()
    record['prediction_id']=uuid.uuid4().hex;record['recorded_at']=datetime.now(timezone.utc).isoformat()
    record['feedback_policy']='Manual usefulness assessment only. No verified run outcome, automatic learning or retraining.'
    with connect() as c:c.execute('INSERT INTO research_predictions VALUES (?,?,?,?)',(record['prediction_id'],record['repository'],record['recorded_at'],json.dumps(record,allow_nan=False)))
    return record

def history(repository):
    with connect() as c:rows=c.execute('SELECT record_json FROM research_predictions WHERE repository=? ORDER BY created_at DESC LIMIT 100',(repository,)).fetchall()
    return [json.loads(x['record_json']) for x in rows]

def get(prediction_id,repository):
    with connect() as c:row=c.execute('SELECT record_json FROM research_predictions WHERE id=? AND repository=?',(prediction_id,repository)).fetchone()
    if row is None:raise KeyError('Prediction not found in this repository')
    return json.loads(row['record_json'])

def feedback(prediction_id,repository,assessment):
    record=get(prediction_id,repository)
    if assessment not in ('helpful','unclear','not-helpful'):raise ValueError('Unknown feedback assessment')
    now=datetime.now(timezone.utc).isoformat();identifier=uuid.uuid4().hex
    with connect() as c:c.execute('INSERT INTO research_feedback VALUES (?,?,?,?)',(identifier,record['prediction_id'],assessment,now))
    return {'feedback_id':identifier,'prediction_id':record['prediction_id'],'assessment':assessment,'recorded_at':now,'learning_status':'Assessment stored only. No verified CI outcome, model update or retraining.'}
