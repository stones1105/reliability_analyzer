import os
import webbrowser
from datetime import datetime
import numpy as np
from scipy.stats import norm
from .plotting import plot_degradation, plot_extrapolation, plot_cdf
from .jedec import jedec_judgment

class ReportExporter:
    def __init__(self, result, params):
        self.result = result
        self.params = params

    def export(self, output_dir=None):
        if output_dir is None:
            output_dir = os.getcwd()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = os.path.join(output_dir, f"Report_{timestamp}")
        os.makedirs(report_dir, exist_ok=True)

        fig_degradation = plot_degradation(self.result['summary'], self.result['data'])
        fig_extrapolation = plot_extrapolation(self.result['devices_df'], self.result['result'], self.result['model_type'])
        cdf_quantiles = self.result.get('cdf_quantiles', ['t63.2%', 't50%', 't0.1%', 't0.01%', 't0.001%'])
        fig_cdf, _ = plot_cdf(
            self.result['tf_work_list'],
            self.params['vd_work'],
            self.result['target_years'],
            cdf_quantiles,
            self.result.get('cdf_xlim', (0.1, 100))
        )
        fig_degradation.savefig(os.path.join(report_dir, "degradation.png"), dpi=150)
        fig_extrapolation.savefig(os.path.join(report_dir, "extrapolation.png"), dpi=150)
        fig_cdf.savefig(os.path.join(report_dir, "cdf_plot.png"), dpi=150)

        report_txt = os.path.join(report_dir, "summary.txt")
        with open(report_txt, 'w', encoding='utf-8') as f:
            self._write_summary(f)
        webbrowser.open(report_dir)
        return report_dir

    def _write_summary(self, f):
        res = self.result
        p = self.params
        f.write("可靠性分析报告\n")
        f.write("="*50 + "\n\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"工作电压: {p['vd_work']} V\n")
        f.write(f"目标寿命: {res['target_years']} 年\n")
        f.write(f"外推模型: {p['model_type']}\n")
        f.write(f"斜率模式: {'平均斜率' if p['slope_mode'] == 'average' else '独立斜率'}\n")
        f.write(f"失效判据: {p['failure_criteria']*100:.1f}%\n")
        f.write(f"拟合点数: {'自定义' if p['device_points'] else '默认 5 点'}\n\n")
        f.write("【各应力统计】\n")
        for item in res['summary']:
            f.write(f"  应力 {item['stress_name']}: 器件数={item['n_devices']}, "
                    f"t50={item['t50']:.2e}s, σ={item['sigma']:.3f}\n")
        f.write("\n【寿命外推结果】\n")
        r = res['result']
        if res['model_type'] in ('isub', 'Isub'):
            f.write(f"  m = {r['m']:.4f}, C = {r['C']:.4e}\n")
            f.write(f"  加速因子 AF = {r['acceleration_factor']:.2f}x\n")
        else:
            f.write(f"  a = {r['a']:.4f}, b = {r['b']:.4f}\n")
        f.write(f"  工作寿命 (t50): {r['tau_years']:.2e} 年\n")
        tf_work_years = np.array(res['tf_work_list']) / (365*24*3600)
        if len(tf_work_years) >= 2:
            log_tf = np.log(tf_work_years)
            mu = np.mean(log_tf)
            sigma = np.std(log_tf, ddof=1)
            t50_work = np.exp(mu)
            f.write(f"\n【工作电压下寿命分布】\n")
            f.write(f"  器件数: {len(res['tf_work_list'])}\n")
            f.write(f"  中位寿命 (t50): {t50_work:.2e} 年\n")
            f.write(f"  对数标准差 σ: {sigma:.3f}\n")
            quantiles = [0.632, 0.50, 0.001, 0.0001, 0.00001]
            labels = ['t63.2%', 't50%', 't0.1%', 't0.01%', 't0.001%']
            for q, lab in zip(quantiles, labels):
                z = norm.ppf(q)
                t = t50_work * np.exp(sigma * z)
                f.write(f"  {lab}: {t:.2e} 年\n")
        status, detail, _ = jedec_judgment(r['tau_years'], res['target_years'])
        f.write(f"\n【JEDEC 判定】\n{detail}\n")