import json
from datetime import datetime,UTC

LOG_FILE="logs/investigation_log.jsonl"

def log_step(action:str,detail:str):
    log={
        "timestamp":datetime.now(UTC).isoformat(),
        "action":action,
        "detail":detail,
    }
    with open(LOG_FILE,"a") as f:
        f.write(json.dump(log)+"\n")