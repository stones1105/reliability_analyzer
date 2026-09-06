import numpy as np
import pandas as pd
from .bti_fitting import (
    fit_single_device_individual,
    fit_device_multiple_n,
    fit_device_simple,
    process_stress_group_global_average
)
from .bti_extrapolation import extrapolate_by_vg, extrapolate_by_1overV

def run_bti_analysis(data, vg_work, failure_criteria_type, failure_criteria_value,
                     slope_mode='average', n_last_points=5,
                     extrapolation_model='Vg',
                     cdf_quantiles=None, cdf_xlim=(0.1, 100),
                     ttf_method='多点平均法',
                     device_points=None):
    # 数据预处理
    for stress_name, stress_dict in data.items():
        time_vals = pd.to_numeric(stress_dict['time'], errors='coerce')
        stress_dict['time'] = np.asarray(time_vals, dtype=np.float64)
        df = stress_dict['data']
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna(axis=1, how='all')
        stress_dict['data'] = df

    stress_summary = []
    device_details = []
    device_records = []

    sorted_stress = sorted(data.items(), key=lambda x: x[1].get('Vd_stress', 0))
    vg_dict = {}
    for stress_name, stress_dict in sorted_stress:
        vg = stress_dict.get('Vg_stress')
        vg_dict[stress_name] = float(vg) if vg is not None else np.nan

    # 如果是全局平均斜率模式，先计算整体平均斜率
    global_n_avg = None
    if slope_mode == 'global_average':
        global_n_avg = process_stress_group_global_average(
            data, failure_criteria_type, failure_criteria_value,
            n_last_points=n_last_points, device_points=device_points
        )
        if not np.isfinite(global_n_avg):
            raise ValueError("无法计算全局平均斜率")

    for stress_name, stress_dict in sorted_stress:
        data_df = stress_dict['data']
        if data_df.empty:
            continue
        device_cols = data_df.columns.tolist()
        vd = stress_dict.get('Vd_stress', 0.0)
        vg = vg_dict.get(stress_name, np.nan)

        # 收集该应力下所有器件的斜率和 TTF
        n_list = []
        ttf_list = []
        device_n_map = {}
        init_vals = data_df.iloc[0].values

        for idx, col in enumerate(device_cols):
            vals = data_df[col].values
            points = n_last_points
            if device_points is not None:
                key = f"{stress_name}|{col}"
                if key in device_points:
                    points = device_points[key]

            # 确定该器件的斜率
            if slope_mode == 'individual':
                n, A, tf = fit_single_device_individual(
                    stress_dict['time'], vals, failure_criteria_type, failure_criteria_value,
                    n_last_points=points
                )
                if not (np.isfinite(n) and n > 0):
                    continue
                common_slope = n
            elif slope_mode == 'global_average':
                common_slope = global_n_avg
            else:  # average（应力平均斜率）
                # 先不计算，后面统一算
                pass

            # 对于 average 模式，需要先收集所有器件的斜率，再计算平均斜率
            if slope_mode == 'average':
                n, A, tf = fit_single_device_individual(
                    stress_dict['time'], vals, failure_criteria_type, failure_criteria_value,
                    n_last_points=points
                )
                if np.isfinite(n) and n > 0:
                    n_list.append(n)
            else:
                # 直接计算 TTF
                if ttf_method == '多点平均法':
                    ttf = fit_device_multiple_n(
                        stress_dict['time'], vals, failure_criteria_type, failure_criteria_value,
                        n_last_points=points, common_slope=common_slope
                    )
                else:  # 简单法
                    ttf = fit_device_simple(
                        stress_dict['time'], vals, failure_criteria_type, failure_criteria_value,
                        n_last_points=points
                    )
                if np.isfinite(ttf) and ttf > 0:
                    ttf_list.append(ttf)
                    device_n_map[col] = common_slope

        # 如果是 average 模式，计算平均斜率并重新计算 TTF
        if slope_mode == 'average':
            if not n_list:
                continue
            n_avg = np.mean(n_list)
            for idx, col in enumerate(device_cols):
                vals = data_df[col].values
                points = n_last_points
                if device_points is not None:
                    key = f"{stress_name}|{col}"
                    if key in device_points:
                        points = device_points[key]
                if ttf_method == '多点平均法':
                    ttf = fit_device_multiple_n(
                        stress_dict['time'], vals, failure_criteria_type, failure_criteria_value,
                        n_last_points=points, common_slope=n_avg
                    )
                else:
                    ttf = fit_device_simple(
                        stress_dict['time'], vals, failure_criteria_type, failure_criteria_value,
                        n_last_points=points
                    )
                if np.isfinite(ttf) and ttf > 0:
                    ttf_list.append(ttf)
                    device_n_map[col] = n_avg
            # n_avg 用于 summary
            n_avg_for_summary = n_avg
        else:
            # 对于 individual 和 global_average，n_avg 取该应力下有效器件的平均斜率（用于显示）
            n_avg_for_summary = np.mean(list(device_n_map.values())) if device_n_map else np.nan

        # 如果该应力下没有有效 TTF，跳过
        if len(ttf_list) == 0:
            continue

        tf_array = np.array(ttf_list)
        log_tf = np.log(tf_array)
        sigma_est = np.std(log_tf, ddof=1)
        t50 = np.exp(np.mean(log_tf))

        stress_summary.append({
            'stress_name': stress_name,
            'Vd_stress': vd,
            'Vg_stress': vg,
            'tf_list': tf_array,
            't50': t50,
            'sigma': sigma_est,
            'n_devices': len(tf_array),
            'n_avg': n_avg_for_summary,
        })

        # 构建 device_details 和 device_records
        for idx, col in enumerate(device_cols):
            if idx < len(tf_array):
                detail = {
                    'stress_name': stress_name,
                    'device_name': col,
                    'n_slope_avg': n_avg_for_summary,
                    'n_slope_ind': device_n_map.get(col, np.nan),
                    'ttf': tf_array[idx],
                    'init_value': init_vals[idx] if idx < len(init_vals) else np.nan,
                }
                device_details.append(detail)
                device_records.append({
                    'stress_name': stress_name,
                    'device_name': col,
                    'Vg_stress': vg,
                    'tf_s': tf_array[idx],
                })

    if not stress_summary:
        raise ValueError("所有应力条件下均未获得有效失效时间")

    devices_df = pd.DataFrame(device_records)
    devices_df['Vg_stress'] = devices_df['Vg_stress'].astype(float)

    if extrapolation_model == 'Vg':
        result = extrapolate_by_vg(devices_df, vg_work)
        x_work = vg_work
        x_stress = devices_df['Vg_stress'].values
    else:
        result = extrapolate_by_1overV(devices_df, vg_work)
        x_work = 1.0 / vg_work
        x_stress = 1.0 / devices_df['Vg_stress'].values

    slope = result['slope']
    tf_work_sec = devices_df['tf_s'].values * np.exp(slope * (x_work - x_stress))
    tf_work_sec = tf_work_sec[np.isfinite(tf_work_sec) & (tf_work_sec > 0)]
    tf_work_list = tf_work_sec.tolist()

    tf_work_map = {}
    for idx, row in devices_df.iterrows():
        key = (row['stress_name'], row['device_name'])
        tf_stress = row['tf_s']
        if extrapolation_model == 'Vg':
            x_i = row['Vg_stress']
        else:
            x_i = 1.0 / row['Vg_stress']
        tf_work = tf_stress * np.exp(slope * (x_work - x_i))
        if np.isfinite(tf_work) and tf_work > 0:
            tf_work_map[key] = tf_work
        else:
            tf_work_map[key] = np.nan

    for detail in device_details:
        key = (detail['stress_name'], detail['device_name'])
        detail['tf_work_sec'] = tf_work_map.get(key, np.nan)
        detail['tf_work_years'] = detail['tf_work_sec'] / (365 * 24 * 3600) if not np.isnan(detail['tf_work_sec']) else np.nan

    vg_dict_float = {item['stress_name']: item.get('Vg_stress', np.nan) for item in stress_summary}

    return {
        'summary': stress_summary,
        'devices_df': devices_df,
        'result': result,
        'tf_work_list': tf_work_list,
        'cdf_quantiles': cdf_quantiles,
        'cdf_xlim': cdf_xlim,
        'extrapolation_model': extrapolation_model,
        'device_details': device_details,
        'data': data,
        'failure_criteria_type': failure_criteria_type,
        'failure_criteria_value': failure_criteria_value,
        'vg_dict': vg_dict_float
    }