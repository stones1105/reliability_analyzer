def jedec_judgment(tau_years, target_years):
    if tau_years >= target_years:
        status = "PASS"
        detail = f"工作寿命 {tau_years:.2f} 年 ≥ {target_years:.2f} 年，通过"
        color = "green"
    else:
        status = "FAIL"
        detail = f"工作寿命 {tau_years:.2f} 年 < {target_years:.2f} 年，未通过"
        color = "red"
    return status, detail, color