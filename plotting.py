import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm
from .cdf_analyzer import LognormalCDFAnalyzer

def plot_degradation(summary, data, vg_dict=None, show_vd=True):
    """
    绘制退化曲线。
    - 每个应力一种颜色和一种标记。
    - 图例显示 Vd（可选）、Vg（若存在）和平均斜率。
    """
    fig, ax = plt.subplots(figsize=(6, 4))
    colors = plt.cm.tab10(np.linspace(0, 1, 10))
    markers = ['o', 's', '^', 'D', 'v', 'p', '*', 'h', 'x', '+']

    for idx, item in enumerate(summary):
        stress_name = item['stress_name']
        stress_dict = data[stress_name]
        data_df = stress_dict['data']
        time_vals = stress_dict['time']
        color = colors[idx % len(colors)]
        marker = markers[idx % len(markers)]

        vd = item.get('Vd_stress', None)
        vg = vg_dict.get(stress_name, "") if vg_dict else item.get('Vg_stress', "")
        n_avg = item.get('n_avg', np.nan)

        # 构建图例
        parts = []
        if show_vd and vd is not None:
            parts.append(f"Vd={vd:.2f}V")
        if vg:
            parts.append(f"Vg={vg}V")
        if not np.isnan(n_avg):
            parts.append(f"n={n_avg:.4f}")
        label = ", ".join(parts) if parts else stress_name

        for j, col in enumerate(data_df.columns):
            vals = data_df[col].values
            init = vals[0]
            deg = (init - vals) / init
            ax.plot(time_vals, deg,
                    linestyle='-', linewidth=1,
                    marker=marker,
                    markersize=4,
                    alpha=0.6,
                    color=color,
                    label=label if j == 0 else "")  # 只显示一次图例

    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlabel('时间 (s)')
    ax.set_ylabel('退化率')
    ax.set_title('退化曲线')
    ax.legend()
    ax.grid(True, which='both', linestyle='--', alpha=0.5)
    fig.tight_layout()
    return fig

def plot_extrapolation(devices_df, result, model_type):
    fig, ax = plt.subplots(figsize=(6, 4))
    if model_type in ('isub', 'Isub'):
        x_data = np.log(devices_df['Isub_over_Id'])
        x_label = 'ln(Isub/Id)'
        x_work = np.log(result['isub_work'])
    elif model_type in ('Vg', '1/Vg'):
        if model_type == 'Vg':
            x_data = devices_df['Vg_stress']
            x_label = 'Vg (V)'
            x_work = result.get('vd_work', 0)
        else:
            x_data = 1.0 / devices_df['Vg_stress']
            x_label = '1/Vg (1/V)'
            x_work = 1.0 / result.get('vd_work', 1)
    else:  # 1/Vd
        x_data = 1.0 / devices_df['Vd_stress']
        x_label = '1/Vd (1/V)'
        x_work = 1.0 / result['vd_work']
    y_data = np.log(devices_df['tf_s'])
    slope = result['slope']
    intercept = result['intercept']
    ax.scatter(x_data, y_data, color='red', s=40, alpha=0.5, label='器件点')
    x_fit = np.linspace(x_data.min()-0.2, x_data.max()+0.2, 100)
    y_fit = slope * x_fit + intercept
    ax.plot(x_fit, y_fit, 'b-', label=f'拟合 (R²={result["r_sq"]:.4f})')
    y_work = np.log(result['tau_sec'])
    ax.scatter(x_work, y_work, color='green', s=120, zorder=5, label='工作点')
    ax.axvline(x_work, color='gray', linestyle=':', alpha=0.6)
    ax.axhline(y_work, color='gray', linestyle=':', alpha=0.6)
    ax.set_xlabel(x_label)
    ax.set_ylabel('ln(失效时间 tf) [秒]')
    ax.set_title('电压加速外推')
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig

def plot_cdf(tf_work_list, vd_work, target_years, show_quantiles, xlim=(0.1, 100)):
    stress_groups = [{
        'name': f'All devices (work voltage = {vd_work} V)',
        'tf_list': tf_work_list,
        'Vd_stress': vd_work
    }]
    cdf_analyzer = LognormalCDFAnalyzer(stress_groups, target_years=target_years)
    cdf_analyzer.analyze()
    fig = cdf_analyzer.plot_probit(show=False, xlim=xlim, show_quantiles=show_quantiles)
    fig.axes[0].set_title('工作电压下所有器件的寿命分布 (对数正态概率图)')
    return fig, cdf_analyzer