import numpy as np
import pandas as pd
from .hci_fitting import process_stress_group_average, process_stress_group_individual
from .hci_extrapolation_isub import extrapolate_by_isub
from .hci_extrapolation_1overV import extrapolate_by_1overV
from common import plot_degradation, plot_extrapolation, plot_cdf

def run_hci_analysis(data, vd_work, target_years, model_type,
                     device_points=None, n_last_default=5,
                     slope_mode='average',
                     cdf_quantiles=None, cdf_xlim=(0.1, 100),
                     current_data=None,
                     isub_work_method="算术平均",
                     failure_criteria=0.10):
    DEFAULT_POINTS = n_last_default
    stress_summary = []
    device_details = []
    device_records = []

    # 按 Vd 排序，并提取 Vg
    sorted_stress = sorted(data.items(), key=lambda x: x[1]['Vd_stress'])
    vg_dict = {}
    for stress_name, stress_dict in sorted_stress:
        vg = stress_dict.get('Vg_stress')
        vg_dict[stress_name] = str(vg) if vg is not None else ""

    for stress_name, stress_dict in sorted_stress:
        data_df = stress_dict['data']
        device_cols = data_df.columns.tolist()
        vd = stress_dict['Vd_stress']
        vg = vg_dict.get(stress_name, "")

        device_points_for_stress = {}
        if device_points is not None:
            for col in device_cols:
                key = f"{stress_name}|{col}"
                if key in device_points:
                    device_points_for_stress[col] = device_points[key]
                else:
                    device_points_for_stress[col] = DEFAULT_POINTS
        else:
            device_points_for_stress = None

        if slope_mode == 'individual':
            tf_array, n_list = process_stress_group_individual(
                stress_dict, failure_criteria=failure_criteria, n_last_points=DEFAULT_POINTS
            )
            n_avg = np.mean(n_list) if n_list else np.nan
            device_n_map = {col: n_list[i] for i, col in enumerate(device_cols) if i < len(n_list)}
        else:
            tf_array, n_avg = process_stress_group_average(
                stress_dict, failure_criteria=failure_criteria, n_last_points=DEFAULT_POINTS
            )
            device_n_map = {col: n_avg for col in device_cols}

        if len(tf_array) == 0:
            continue
        log_tf = np.log(tf_array)
        sigma_est = np.std(log_tf, ddof=1)
        t50 = np.exp(np.mean(log_tf))
        init_vals = data_df.iloc[0].values

        stress_summary.append({
            'stress_name': stress_name,
            'Vd_stress': vd,
            'Vg_stress': vg,
            'tf_list': tf_array,
            't50': t50,
            'sigma': sigma_est,
            'n_devices': len(tf_array),
            'n_avg': n_avg,
        })

        # ---- 获取三端电流数据（按 Vd 匹配，忽略 Vg） ----
        current_devices = None
        if current_data is not None:
            # 在 current_data 中查找相同 Vd 的 sheet（忽略 Vg）
            for cur_stress_name, cur_stress_info in current_data.items():
                if abs(cur_stress_info['Vd_stress'] - vd) < 1e-6:
                    current_devices = cur_stress_info['devices']
                    break

        for idx, col in enumerate(device_cols):
            if idx < len(tf_array):
                detail = {
                    'stress_name': stress_name,
                    'device_name': col,
                    'device_index': idx,
                    'n_slope_avg': n_avg,
                    'n_slope_ind': device_n_map.get(col, np.nan),
                    'ttf': tf_array[idx],
                    'init_idsat': init_vals[idx] if idx < len(init_vals) else np.nan,
                }
                if current_devices is not None and idx < len(current_devices):
                    cur = current_devices[idx]
                    detail['IdOp'] = cur.get('IdOp', np.nan)
                    detail['IsubOp'] = cur.get('IsubOp', np.nan)
                    detail['IgOp'] = cur.get('IgOp', np.nan)
                    detail['Idstress'] = cur.get('Idstress', np.nan)
                    detail['Isubstress'] = cur.get('Isubstress', np.nan)
                    detail['Igstress'] = cur.get('Igstress', np.nan)
                else:
                    for k in ['IdOp','IsubOp','IgOp','Idstress','Isubstress','Igstress']:
                        detail[k] = np.nan
                device_details.append(detail)

                device_records.append({
                    'stress_name': stress_name,
                    'device_name': col,
                    'device_index': idx,
                    'Vd_stress': vd,
                    'tf_s': tf_array[idx],
                })

    if not stress_summary:
        raise ValueError("所有应力条件下均未获得有效失效时间")

    devices_df = pd.DataFrame(device_records)

    # ---- 计算 Isub_over_Id（按 Vd 匹配三端电流） ----
    if model_type == 'isub' and current_data is not None:
        ratio_map = {}
        for s_name, s_info in current_data.items():
            vd_cur = s_info['Vd_stress']
            for idx, cur in enumerate(s_info['devices']):
                isub = cur.get('Isubstress', np.nan)
                id_val = cur.get('Idstress', np.nan)
                if pd.notna(isub) and pd.notna(id_val) and id_val != 0:
                    ratio = abs(isub / id_val)
                else:
                    ratio = np.nan
                ratio_map[(vd_cur, idx)] = ratio

        def get_ratio(row):
            return ratio_map.get((row['Vd_stress'], row['device_index']), np.nan)

        devices_df['Isub_over_Id'] = devices_df.apply(get_ratio, axis=1)
        if devices_df['Isub_over_Id'].isna().all():
            devices_df['Isub_over_Id'] = 1e-6 * (devices_df['Vd_stress'] ** 3.5)
        else:
            for idx, row in devices_df.iterrows():
                if pd.isna(row['Isub_over_Id']):
                    devices_df.at[idx, 'Isub_over_Id'] = 1e-6 * (row['Vd_stress'] ** 3.5)
    else:
        devices_df['Isub_over_Id'] = 1e-6 * (devices_df['Vd_stress'] ** 3.5)

    # ---- 计算 isub_work（从电流文件提取，同样按 Vd 匹配所有器件） ----
    if model_type == 'isub' and current_data is not None:
        work_ratios = []
        for s_info in current_data.values():
            for cur in s_info['devices']:
                isub_op = cur.get('IsubOp', np.nan)
                id_op = cur.get('IdOp', np.nan)
                if pd.notna(isub_op) and pd.notna(id_op) and id_op != 0:
                    work_ratios.append(abs(isub_op / id_op))
        if work_ratios:
            isub_work = np.mean(work_ratios)
        else:
            isub_work = 1e-6 * (vd_work ** 3.5)
    else:
        isub_work = 1e-6 * (vd_work ** 3.5)

    # 外推
    if model_type == 'isub':
        result = extrapolate_by_isub(devices_df, vd_work, isub_work=isub_work)
        x_work = np.log(result['isub_work'])
    else:
        result = extrapolate_by_1overV(devices_df, vd_work)
        result['vd_work'] = vd_work
        x_work = 1.0 / vd_work

    slope = result['slope']
    if model_type == 'isub':
        x_stress = np.log(devices_df['Isub_over_Id'].values)
    else:
        x_stress = 1.0 / devices_df['Vd_stress'].values
    tf_work_sec = devices_df['tf_s'].values * np.exp(slope * (x_work - x_stress))
    tf_work_sec = tf_work_sec[np.isfinite(tf_work_sec) & (tf_work_sec > 0)]
    tf_work_list = tf_work_sec.tolist()

    # 为 device_details 添加工作寿命
    tf_work_map = {}
    for idx, row in devices_df.iterrows():
        key = (row['stress_name'], row['device_name'])
        tf_stress = row['tf_s']
        if model_type == 'isub':
            x_i = np.log(row['Isub_over_Id'])
        else:
            x_i = 1.0 / row['Vd_stress']
        tf_work = tf_stress * np.exp(slope * (x_work - x_i))
        if np.isfinite(tf_work) and tf_work > 0:
            tf_work_map[key] = tf_work
        else:
            tf_work_map[key] = np.nan

    for detail in device_details:
        key = (detail['stress_name'], detail['device_name'])
        detail['tf_work_sec'] = tf_work_map.get(key, np.nan)
        detail['tf_work_years'] = detail['tf_work_sec'] / (365 * 24 * 3600) if not np.isnan(detail['tf_work_sec']) else np.nan

    return {
        'summary': stress_summary,
        'devices_df': devices_df,
        'result': result,
        'tf_work_list': tf_work_list,
        'target_years': target_years,
        'cdf_quantiles': cdf_quantiles,
        'cdf_xlim': cdf_xlim,
        'model_type': model_type,
        'device_points': device_points,
        'device_details': device_details,
        'data': data,
        'failure_criteria': failure_criteria,
        'vg_dict': vg_dict
    }