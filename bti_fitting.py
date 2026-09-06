import numpy as np
from scipy import stats

def fit_single_device_individual(time_sec, data_vals, criteria_type, criteria_value, n_last_points=5):
    """
    独立拟合单个器件，返回 (斜率 n, 截距 A, 传统 TTF)
    仅用于获取斜率，不用于最终 TTF 计算。
    """
    time_sec = np.asarray(time_sec, dtype=np.float64)
    data_vals = np.asarray(data_vals, dtype=np.float64)
    n_last = min(n_last_points, len(time_sec))
    if n_last < 2:
        return np.nan, np.nan, np.inf
    init = data_vals[0]
    if criteria_type == 'percent':
        if init == 0:
            return np.nan, np.nan, np.inf
        deg = (init - data_vals) / init
    else:
        deg = np.abs(data_vals - init)
    # 取最后 n_last 个点
    deg_last = deg[-n_last:]
    time_last = time_sec[-n_last:]
    valid = (deg_last > 0) & np.isfinite(deg_last) & (time_last > 0)
    if not np.any(valid):
        return np.nan, np.nan, np.inf
    log_t = np.log10(time_last[valid])
    log_deg = np.log10(deg_last[valid])
    slope, intercept, _, _, _ = stats.linregress(log_t, log_deg)
    n = slope
    A = 10 ** intercept
    if n <= 0 or A <= 0:
        return np.nan, np.nan, np.inf
    tf = (criteria_value / A) ** (1 / n)
    return n, A, tf

def fit_device_multiple_n(time_sec, data_vals, criteria_type, criteria_value,
                          n_last_points, common_slope):
    """
    多点平均法（新版）：
    使用固定的斜率 common_slope，从最后一个点开始向前，
    选取最多 n_last_points 个退化量尚未达到判据的点，
    对每个点计算 TTF，取对数平均后返回。
    """
    time_sec = np.asarray(time_sec, dtype=np.float64)
    data_vals = np.asarray(data_vals, dtype=np.float64)
    if len(time_sec) < 1 or len(data_vals) < 1:
        return np.inf
    init = data_vals[0]
    if criteria_type == 'percent':
        if init == 0:
            return np.inf
        deg = (init - data_vals) / init
    else:
        deg = np.abs(data_vals - init)

    # 从后向前扫描，收集退化量 < criteria_value 且 > 0 的点
    points = []
    for i in range(len(deg)-1, -1, -1):
        if len(points) >= n_last_points:
            break
        if deg[i] > 0 and deg[i] < criteria_value and time_sec[i] > 0:
            points.append((time_sec[i], deg[i]))
    # 反向排序（使时间从小到大，便于理解，但不影响计算）
    points.reverse()
    if len(points) < 2:
        return np.inf

    n = common_slope
    if n <= 0:
        return np.inf

    log10_ttf_list = []
    for t, d in points:
        A = d / (t ** n)
        if A <= 0:
            continue
        ttf = (criteria_value / A) ** (1 / n)
        if np.isfinite(ttf) and ttf > 0:
            log10_ttf_list.append(np.log10(ttf))
    if not log10_ttf_list:
        return np.inf
    avg_log10_ttf = np.mean(log10_ttf_list)
    return 10 ** avg_log10_ttf

def fit_device_simple(time_sec, data_vals, criteria_type, criteria_value, n_last_points):
    """简单法：使用最后 n_last_points 个点拟合，返回 TTF（兼容旧版）"""
    time_sec = np.asarray(time_sec, dtype=np.float64)
    data_vals = np.asarray(data_vals, dtype=np.float64)
    if len(time_sec) < n_last_points or len(data_vals) < n_last_points:
        return np.inf
    init = data_vals[0]
    if criteria_type == 'percent':
        if init == 0:
            return np.inf
        deg = (init - data_vals) / init
    else:
        deg = np.abs(data_vals - init)
    deg_last = deg[-n_last_points:]
    time_last = time_sec[-n_last_points:]
    valid = (deg_last > 0) & np.isfinite(deg_last) & (time_last > 0)
    if not np.any(valid):
        return np.inf
    deg_last = deg_last[valid]
    time_last = time_last[valid]
    if len(time_last) < 2:
        return np.inf
    log_t = np.log10(time_last)
    log_deg = np.log10(deg_last)
    slope, intercept, _, _, _ = stats.linregress(log_t, log_deg)
    if slope <= 0:
        return np.inf
    A = 10 ** intercept
    if A <= 0:
        return np.inf
    log10_ttf = np.log10(criteria_value / A) / slope
    return 10 ** log10_ttf

def process_stress_group_global_average(data, criteria_type, criteria_value, n_last_points=5, device_points=None):
    """
    计算所有应力所有器件的平均斜率（用于总体平均模式）
    """
    all_n = []
    for stress_name, stress_dict in data.items():
        data_df = stress_dict['data']
        time = stress_dict['time']
        for col in data_df.columns:
            vals = data_df[col].values
            points = n_last_points
            if device_points is not None:
                key = f"{stress_name}|{col}"
                if key in device_points:
                    points = device_points[key]
            n, A, tf = fit_single_device_individual(time, vals, criteria_type, criteria_value, n_last_points=points)
            if np.isfinite(n) and n > 0:
                all_n.append(n)
    if not all_n:
        return np.nan
    return np.mean(all_n)