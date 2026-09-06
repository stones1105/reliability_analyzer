import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm, linregress
import os
from datetime import datetime

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'WenQuanYi Zen Hei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

class LognormalCDFAnalyzer:
    def __init__(self, stress_groups, target_years):
        self.stress_groups = stress_groups
        self.target_years = target_years
        self.results = []
        self.fig = None

    def analyze(self):
        for group in self.stress_groups:
            tf = np.array(group['tf_list'])
            if len(tf) < 2:
                print(f"警告: {group['name']} 器件数量不足，跳过CDF拟合")
                continue
            tf_years = tf / (365 * 24 * 3600)
            sorted_tf = np.sort(tf_years)
            n = len(sorted_tf)
            F = (np.arange(1, n+1) - 0.3) / (n + 0.4)
            probit = norm.ppf(F)
            log_t = np.log(sorted_tf)
            slope, intercept, r_value, _, _ = linregress(log_t, probit)
            sigma = 1.0 / slope if slope != 0 else np.nan
            mu = -intercept / slope if slope != 0 else np.nan
            t50 = np.exp(mu)
            self.results.append({
                'name': group['name'],
                'Vd_stress': group.get('Vd_stress', 0),
                't50_sec': t50 * (365*24*3600),
                't50_years': t50,
                'mu': mu,
                'sigma': sigma,
                'n_devices': n,
                'r_sq': r_value**2
            })
        return self.results

    def plot_probit(self, show=True, save_path=None, xlim=None, show_quantiles=None):
        if not self.results:
            self.analyze()
        fig, ax = plt.subplots(figsize=(8, 6))
        if not self.results:
            ax.text(0.5, 0.5, "无有效数据点\n（至少需要两个器件才能绘制CDF）",
                    ha='center', va='center', fontsize=14, color='red', transform=ax.transAxes)
            ax.set_title('CDF 分布 - 无数据')
            ax.set_xlabel('ln(寿命) [年]')
            ax.set_ylabel('累积失效率 (Probit)')
            fig.tight_layout()
            if save_path:
                plt.savefig(save_path, dpi=150, bbox_inches='tight')
            if show:
                plt.show()
            else:
                plt.close(fig)
            self.fig = fig
            return fig

        if show_quantiles is None:
            show_quantiles = ['t63.2%', 't50%', 't0.1%', 't0.01%', 't0.001%']
        colors = ['blue', 'green', 'red', 'purple', 'orange', 'brown', 'pink', 'gray']
        quantile_map = {'t63.2%': 0.632, 't50%': 0.50, 't0.1%': 0.001,
                        't0.01%': 0.0001, 't0.001%': 0.00001}
        first_mu = first_sigma = None

        for i, res in enumerate(self.results):
            group = next(g for g in self.stress_groups if g['name'] == res['name'])
            tf_list = np.array(group['tf_list'])
            tf_years = tf_list / (365 * 24 * 3600)
            sorted_tf = np.sort(tf_years)
            n = len(sorted_tf)
            F = (np.arange(1, n+1) - 0.3) / (n + 0.4)
            probit = norm.ppf(F)
            log_tf = np.log(sorted_tf)
            ax.scatter(log_tf, probit, marker='o', s=40,
                       label=f"{res['name']} (实测)", color=colors[i % len(colors)])
            mu = res['mu']
            sigma = res['sigma']
            x_theory = np.linspace(log_tf.min()-0.5, log_tf.max()+0.5, 100)
            y_theory = (x_theory - mu) / sigma
            ax.plot(x_theory, y_theory, '--', color=colors[i % len(colors)],
                    label=f"{res['name']} 拟合 (σ={sigma:.3f})")
            if i == 0:
                first_mu = mu
                first_sigma = sigma
                for label in show_quantiles:
                    if label in quantile_map:
                        Fq = quantile_map[label]
                        z = norm.ppf(Fq)
                        t_q = np.exp(mu + sigma * z)
                        ax.scatter(np.log(t_q), z, marker='s', s=80,
                                   color='black', edgecolors='white', linewidth=1,
                                   label=f'{label} = {t_q:.2f}年')

        if first_mu is not None and first_sigma is not None:
            formula = f"ln(t) = {first_mu:.3f} + {first_sigma:.3f} · Φ⁻¹(F)\n"
            formula += f"   μ = {first_mu:.3f}, σ = {first_sigma:.3f}"
            ax.text(0.05, 0.95, formula, transform=ax.transAxes,
                    fontsize=10, verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax.legend(by_label.values(), by_label.keys(), loc='best')
        y_ticks = norm.ppf([0.001, 0.01, 0.05, 0.10, 0.50, 0.90, 0.99])
        y_labels = ['0.1%', '1%', '5%', '10%', '50%', '90%', '99%']
        ax.set_yticks(y_ticks)
        ax.set_yticklabels(y_labels)
        ax.set_xlabel('ln(寿命) [年]')
        ax.set_ylabel('累积失效率 (Probit)')
        ax.set_title('对数正态概率图 (Probit Plot)')
        ax.grid(True, alpha=0.3)
        if xlim is not None:
            ax.set_xlim(np.log(xlim[0]), np.log(xlim[1]))
        else:
            xmin, xmax = ax.get_xlim()
            ax.set_xlim(xmin - 0.2, xmax + 0.2)
        fig.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        if show:
            plt.show()
        else:
            plt.close(fig)
        self.fig = fig
        return fig

    def export_report(self, output_dir=None, include_plot=True):
        # 简化导出，可自行扩展
        return None