import pandas as pd
import re
import numpy as np

def extract_voltage_from_string(text):
    if not isinstance(text, str):
        return None
    match = re.search(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', text)
    if match:
        try:
            return float(match.group())
        except ValueError:
            return None
    return None

def load_three_end_currents(filepath):
    xls = pd.ExcelFile(filepath)
    current_data = {}
    expected_params = ['DataName', 'IdOp', 'IsubOp', 'IgOp', 'Idstress', 'Isubstress', 'Igstress']
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
        first_col = df.iloc[:, 0].dropna().tolist()
        param_names_clean = [str(p).strip().lower() for p in first_col]
        expected_clean = [p.lower() for p in expected_params]
        missing = [p for p in expected_clean if p not in param_names_clean]
        if missing:
            raise ValueError(f"Sheet '{sheet_name}' 缺少必要的参数行: {missing}")
        data_rows = {}
        for idx, row in df.iterrows():
            name = str(row[0]).strip()
            matched = None
            for exp in expected_params:
                if name.lower() == exp.lower():
                    matched = exp
                    break
            if matched:
                values = []
                for v in row[1:]:
                    if pd.isna(v):
                        values.append(np.nan)
                    else:
                        try:
                            values.append(abs(float(v)))
                        except (ValueError, TypeError):
                            values.append(np.nan)
                data_rows[matched] = values
        device_names = df.iloc[0, 1:].tolist()
        if not device_names or all(pd.isna(x) for x in device_names):
            device_names = [f"Col{i+1}" for i in range(len(df.columns)-1)]
        devices = []
        for i in range(len(device_names)):
            devices.append({
                'name': device_names[i] if i < len(device_names) else f"Col{i+1}",
                'IdOp': data_rows['IdOp'][i] if i < len(data_rows['IdOp']) else np.nan,
                'IsubOp': data_rows['IsubOp'][i] if i < len(data_rows['IsubOp']) else np.nan,
                'IgOp': data_rows['IgOp'][i] if i < len(data_rows['IgOp']) else np.nan,
                'Idstress': data_rows['Idstress'][i] if i < len(data_rows['Idstress']) else np.nan,
                'Isubstress': data_rows['Isubstress'][i] if i < len(data_rows['Isubstress']) else np.nan,
                'Igstress': data_rows['Igstress'][i] if i < len(data_rows['Igstress']) else np.nan,
            })
        vd = extract_voltage_from_string(sheet_name)
        if vd is None:
            vd = 3.0
        current_data[sheet_name] = {
            'Vd_stress': vd,
            'devices': devices
        }
    return current_data