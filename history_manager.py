import json
import os
from datetime import datetime

HISTORY_FILE = "analysis_history.json"
MAX_HISTORY = 10

def _get_key(record):
    return (
        record.get('test_type'),
        record.get('file_path'),
        record.get('vd_work'),
        record.get('target_years'),
        record.get('model_type')
    )

def save_history(test_type, file_path, vd_work, target_years, model_type, device_points=None):
    history = load_all_history()
    new_record = {
        "test_type": test_type,
        "file_path": file_path,
        "vd_work": vd_work,
        "target_years": target_years,
        "model_type": model_type,
        "device_points": device_points,
        "timestamp": datetime.now().isoformat()
    }
    new_key = _get_key(new_record)
    updated = False
    for i, rec in enumerate(history):
        if _get_key(rec) == new_key:
            history[i] = new_record
            updated = True
            break
    if not updated:
        history.append(new_record)
    history.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    if len(history) > MAX_HISTORY:
        history = history[:MAX_HISTORY]
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"保存历史记录失败: {e}")

def load_all_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    data.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
                    return data
                return []
        except Exception as e:
            print(f"加载历史记录失败: {e}")
    return []

def load_history():
    history = load_all_history()
    return history[0] if history else None

def get_history_list():
    history = load_all_history()
    summaries = []
    for rec in history[:MAX_HISTORY]:
        try:
            dt = datetime.fromisoformat(rec.get('timestamp', ''))
            time_str = dt.strftime('%Y-%m-%d %H:%M')
        except:
            time_str = rec.get('timestamp', '')
        file_name = os.path.basename(rec.get('file_path', ''))
        display = f"{time_str} | {rec.get('test_type', '')} | {file_name}"
        summaries.append({
            'display': display,
            'record': rec
        })
    return summaries

def clear_history():
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)