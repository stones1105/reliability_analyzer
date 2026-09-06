import numpy as np
from scipy import stats

def extrapolate_by_vg(devices_df, vg_work):
    x_data = devices_df['Vg_stress'].values.astype(float)
    y_data = np.log(devices_df['tf_s'].values.astype(float))
    if np.std(x_data) < 1e-12:
        raise ValueError("所有应力的 Vg 值几乎相同，无法进行线性回归。")
    slope, intercept, r_value, _, _ = stats.linregress(x_data, y_data)
    b = slope
    a = intercept
    r_sq = r_value ** 2
    log_tau_work = a + b * vg_work
    tau_sec = np.exp(log_tau_work)
    tau_years = tau_sec / (365 * 24 * 3600)
    return {
        'a': a,
        'b': b,
        'tau_sec': tau_sec,
        'tau_years': tau_years,
        'r_sq': r_sq,
        'slope': slope,
        'intercept': intercept,
        'model_type': 'Vg'
    }

def extrapolate_by_1overV(devices_df, vg_work):
    x_data = 1.0 / devices_df['Vg_stress'].values.astype(float)
    y_data = np.log(devices_df['tf_s'].values.astype(float))
    if np.std(x_data) < 1e-12:
        raise ValueError("所有应力的 Vg 值几乎相同，无法进行线性回归。")
    slope, intercept, r_value, _, _ = stats.linregress(x_data, y_data)
    b = slope
    a = intercept
    r_sq = r_value ** 2
    x_work = 1.0 / vg_work
    log_tau_work = a + b * x_work
    tau_sec = np.exp(log_tau_work)
    tau_years = tau_sec / (365 * 24 * 3600)
    return {
        'a': a,
        'b': b,
        'tau_sec': tau_sec,
        'tau_years': tau_years,
        'r_sq': r_sq,
        'slope': slope,
        'intercept': intercept,
        'model_type': '1/Vg'
    }