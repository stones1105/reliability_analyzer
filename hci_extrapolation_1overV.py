import numpy as np
from scipy import stats

def extrapolate_by_1overV(devices_df, vd_work):
    inv_vd = 1.0 / devices_df['Vd_stress'].values
    log_tf = np.log(devices_df['tf_s'].values)

    if np.std(inv_vd) < 1e-12:
        raise ValueError("所有应力的 Vd_stress 值几乎相同，无法进行线性回归。")

    slope, intercept, r_value, _, _ = stats.linregress(inv_vd, log_tf)
    b = slope
    a = intercept
    r_sq = r_value ** 2

    inv_vd_work = 1.0 / vd_work
    log_tau_work = a + b * inv_vd_work
    tau_sec = np.exp(log_tau_work)
    tau_years = tau_sec / (365 * 24 * 3600)

    ref_vd = devices_df['Vd_stress'].min()
    acceleration_factor = np.exp(b * (1/vd_work - 1/ref_vd))

    return {
        'a': a,
        'b': b,
        'tau_sec': tau_sec,
        'tau_years': tau_years,
        'r_sq': r_sq,
        'slope': slope,
        'intercept': intercept,
        'acceleration_factor': acceleration_factor,
        'ref_stress_voltage': ref_vd
    }