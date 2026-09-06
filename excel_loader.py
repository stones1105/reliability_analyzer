import pandas as pd
import re

def parse_sheet_name(sheet_name):
    """
    解析 sheet 名称，提取 Vd 和 Vg。
    例如 "Vd=4.3V,Vg=1.5V" -> (4.3, 1.5)
    若只有 "Vd=4.3V" 则返回 (4.3, None)
    """
    vd = None
    vg = None
    # 匹配 Vd=数字V
    vd_match = re.search(r'Vd\s*=\s*([\d.]+)\s*V', sheet_name, re.IGNORECASE)
    if vd_match:
        vd = float(vd_match.group(1))
    # 匹配 Vg=数字V
    vg_match = re.search(r'Vg\s*=\s*([\d.]+)\s*V', sheet_name, re.IGNORECASE)
    if vg_match:
        vg = float(vg_match.group(1))
    return vd, vg

def load_excel(filepath):
    xls = pd.ExcelFile(filepath)
    stress_data = {}
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name, header=0)
        time_col = df.columns[0]
        time_vals = df[time_col].values
        data_cols = [col for col in df.columns if col != time_col]
        data_df = df[data_cols]
        vd, vg = parse_sheet_name(sheet_name)
        if vd is None:
            vd = 3.0  # 兼容旧格式
        stress_data[sheet_name] = {
            'time': time_vals,
            'data': data_df,
            'Vd_stress': vd,
            'Vg_stress': vg,
            'V_stress': vd   # 保留旧键兼容
        }
    return stress_data