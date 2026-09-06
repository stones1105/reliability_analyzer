import numpy as np
from scipy import stats

def extrapolate_by_isub(devices_df, vd_work, isub_work=None):
    log_isub = np.log(devices_df['Isub_over_Id'].values)
    log_tf = np.log(devices_df['tf_s'].values)

    if np.std(log_isub) < 1e-12:
        raise ValueError("所有器件的 Isub/Id 值几乎相同，无法进行线性回归。")

    slope, intercept, r_value, _, _ = stats.linregress(log_isub, log_tf)
    m = -slope
    ln_C = intercept
    C = np.exp(ln_C)
    r_sq = r_value ** 2

    if isub_work is None:
        min_vd = devices_df['Vd_stress'].min()
        min_isub = devices_df.loc[devices_df['Vd_stress'] == min_vd, 'Isub_over_Id'].iloc[0]
        isub_work = min_isub * (vd_work / min_vd) ** 3.5

    log_tau_work = -m * np.log(isub_work) + ln_C
    tau_sec = np.exp(log_tau_work)
    tau_years = tau_sec / (365 * 24 * 3600)

    ref_vd = devices_df['Vd_stress'].min()
    ref_isub = devices_df.loc[devices_df['Vd_stress'] == ref_vd, 'Isub_over_Id'].iloc[0]
    acceleration_factor = (ref_isub / isub_work) ** m if isub_work > 0 else 1.0

    return {
        'm': m,
        'C': C,
        'isub_work': isub_work,
        'tau_sec': tau_sec,
        'tau_years': tau_years,
        'r_sq': r_sq,
        'slope': slope,
        'intercept': intercept,
        'acceleration_factor': acceleration_factor,
        'ref_stress_voltage': ref_vd,
        'ref_isub': ref_isub
    }