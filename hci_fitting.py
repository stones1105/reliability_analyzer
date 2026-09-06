import numpy as np
from scipy import stats

def fit_single_device_individual(time_sec, idsat, failure_criteria=0.10, n_last_points=5):
    if len(idsat) == 0:
        return np.nan, np.nan, np.inf
    init = idsat[0]
    deg = (init - idsat) / init
    if len(deg) < n_last_points:
        n_last_points = len(deg)
    deg_last = deg[-n_last_points:]
    time_last = time_sec[-n_last_points:]
    valid = (deg_last > 0) & np.isfinite(deg_last) & (time_last > 0)
    if not np.any(valid):
        return np.nan, np.nan, np.inf
    deg_last = deg_last[valid]
    time_last = time_last[valid]
    if len(time_last) < 2:
        return np.nan, np.nan, np.inf
    log_t = np.log10(time_last)
    log_deg = np.log10(deg_last)
    slope, intercept, _, _, _ = stats.linregress(log_t, log_deg)
    n = slope
    A = 10 ** intercept
    if A > 0 and n > 0:
        tf = (failure_criteria / A) ** (1 / n)
    else:
        tf = np.inf
    return n, A, tf

def fit_single_device_common_slope(time_sec, idsat, n_common, failure_criteria=0.10, n_last_points=5):
    if len(idsat) == 0:
        return np.nan, np.inf
    init = idsat[0]
    deg = (init - idsat) / init
    if len(deg) < n_last_points:
        n_last_points = len(deg)
    deg_last = deg[-n_last_points:]
    time_last = time_sec[-n_last_points:]
    valid = (deg_last > 0) & np.isfinite(deg_last) & (time_last > 0)
    if not np.any(valid):
        return np.nan, np.inf
    deg_last = deg_last[valid]
    time_last = time_last[valid]
    if len(time_last) < 1:
        return np.nan, np.inf
    log_t = np.log10(time_last)
    log_deg = np.log10(deg_last)
    log_A_vals = log_deg - n_common * log_t
    log_A = np.mean(log_A_vals)
    A = 10 ** log_A
    if A > 0 and n_common > 0:
        tf = (failure_criteria / A) ** (1 / n_common)
    else:
        tf = np.inf
    return A, tf

def process_stress_group_individual(stress_dict, failure_criteria=0.10, n_last_points=5):
    time = stress_dict['time']
    data_df = stress_dict['data']
    tf_list = []
    n_list = []
    for col in data_df.columns:
        vals = data_df[col].values
        if np.any(np.isnan(vals)) or np.any(vals <= 0):
            continue
        n, A, tf = fit_single_device_individual(time, vals, failure_criteria, n_last_points)
        if np.isfinite(n) and n > 0 and np.isfinite(tf) and tf > 0:
            n_list.append(n)
            tf_list.append(tf)
    return np.array(tf_list), n_list

def process_stress_group_average(stress_dict, failure_criteria=0.10, n_last_points=5):
    time = stress_dict['time']
    data_df = stress_dict['data']
    device_n_list = []
    tf_list = []
    for col in data_df.columns:
        vals = data_df[col].values
        if np.any(np.isnan(vals)) or np.any(vals <= 0):
            continue
        n, A, tf = fit_single_device_individual(time, vals, failure_criteria, n_last_points)
        if np.isfinite(n) and n > 0:
            device_n_list.append(n)
    if len(device_n_list) == 0:
        return np.array([]), np.nan
    n_avg = np.mean(device_n_list)
    for col in data_df.columns:
        vals = data_df[col].values
        if np.any(np.isnan(vals)) or np.any(vals <= 0):
            continue
        A, tf = fit_single_device_common_slope(time, vals, n_avg, failure_criteria, n_last_points)
        if np.isfinite(tf) and tf > 0:
            tf_list.append(tf)
    return np.array(tf_list), n_avg