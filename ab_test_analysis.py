# ============================================================
# A/B TEST STATISTICAL ANALYSIS
# Project  : Olist E-Commerce Analytics
# Test     : Simplified Checkout (Treatment) vs Standard (Control)
# Source   : Udacity A/B Testing Dataset (reframed as ecommerce)
# Author   : Adeeb
# ============================================================
#
# REFRAMING:
#   Pageviews   → Product Detail Page (PDP) views
#   Clicks      → Checkout initiated
#   Enrollments → Cart additions (add to cart)
#   Payments    → Completed purchases
#
# HYPOTHESIS:
#   H0: No difference between Control and Treatment
#   H1: Simplified checkout improves purchase conversion
#   Alpha = 0.05 (95% confidence)

import pandas as pd
import numpy as np
from scipy import stats
import math
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# STEP 1 — DATA
# ============================================================

control_data = {
    'Date': ['Sat, Oct 11','Sun, Oct 12','Mon, Oct 13','Tue, Oct 14','Wed, Oct 15',
             'Thu, Oct 16','Fri, Oct 17','Sat, Oct 18','Sun, Oct 19','Mon, Oct 20',
             'Tue, Oct 21','Wed, Oct 22','Thu, Oct 23','Fri, Oct 24','Sat, Oct 25',
             'Sun, Oct 26','Mon, Oct 27','Tue, Oct 28','Wed, Oct 29','Thu, Oct 30',
             'Fri, Oct 31','Sat, Nov 1','Sun, Nov 2','Mon, Nov 3','Tue, Nov 4',
             'Wed, Nov 5','Thu, Nov 6','Fri, Nov 7','Sat, Nov 8','Sun, Nov 9',
             'Mon, Nov 10','Tue, Nov 11','Wed, Nov 12','Thu, Nov 13','Fri, Nov 14',
             'Sat, Nov 15','Sun, Nov 16'],
    'Pageviews':   [7723,9102,10511,9871,10014,9670,9008,7434,8459,10667,
                    10660,9947,8324,9434,8687,8896,9535,9363,9327,9345,
                    8890,8460,8836,9437,9420,9570,9921,9424,8827,9282,
                    10165,9083,9684,8671,8555,8287,8176],
    'Clicks':      [687,779,909,836,837,823,748,632,691,861,
                    867,838,665,673,691,708,759,736,739,734,
                    706,681,693,788,781,805,830,781,756,786,
                    851,753,800,743,722,709,668],
    'Enrollments': [134,147,167,156,163,138,146,110,131,165,
                    196,162,127,220,176,161,233,154,196,167,
                    174,156,206,175,191,291,234,190,178,185,
                    227,None,None,None,None,None,None],
    'Payments':    [70,70,95,105,64,82,76,70,60,97,
                    105,92,56,122,128,104,124,91,86,75,
                    101,93,112,89,97,190,133,126,113,108,
                    162,None,None,None,None,None,None]
}

experiment_data = {
    'Date': ['Sat, Oct 11','Sun, Oct 12','Mon, Oct 13','Tue, Oct 14','Wed, Oct 15',
             'Thu, Oct 16','Fri, Oct 17','Sat, Oct 18','Sun, Oct 19','Mon, Oct 20',
             'Tue, Oct 21','Wed, Oct 22','Thu, Oct 23','Fri, Oct 24','Sat, Oct 25',
             'Sun, Oct 26','Mon, Oct 27','Tue, Oct 28','Wed, Oct 29','Thu, Oct 30',
             'Fri, Oct 31','Sat, Nov 1','Sun, Nov 2','Mon, Nov 3','Tue, Nov 4',
             'Wed, Nov 5','Thu, Nov 6','Fri, Nov 7','Sat, Nov 8','Sun, Nov 9',
             'Mon, Nov 10','Tue, Nov 11','Wed, Nov 12','Thu, Nov 13','Fri, Nov 14',
             'Sat, Nov 15','Sun, Nov 16'],
    'Pageviews':   [7716,9288,10480,9867,9793,9500,9088,7664,8434,10496,
                    10551,9737,8176,9402,8669,8881,9655,9396,9262,9308,
                    8715,8448,8836,9359,9427,9633,9842,9272,8969,9282,
                    10178,9008,9070,8640,8512,8179,8221],
    'Clicks':      [686,785,884,827,832,788,780,652,697,860,
                    864,801,642,697,669,693,771,736,727,728,
                    722,695,724,789,743,808,831,767,760,786,
                    862,712,800,759,712,643,681],
    'Enrollments': [105,116,145,138,140,129,127,94,120,153,
                    143,128,122,194,127,153,213,162,201,207,
                    182,142,182,156,171,244,191,155,166,164,
                    232,None,None,None,None,None,None],
    'Payments':    [34,91,79,92,94,61,44,62,77,98,
                    71,70,68,94,81,101,119,120,96,67,
                    123,100,103,88,95,163,119,87,100,117,
                    153,None,None,None,None,None,None]
}

control    = pd.DataFrame(control_data)
experiment = pd.DataFrame(experiment_data)

print('=' * 60)
print('A/B TEST — SIMPLIFIED CHECKOUT EXPERIMENT')
print('Ecommerce Funnel: PDP Views → Checkout → Cart → Purchase')
print('=' * 60)


# ============================================================
# STEP 2 — SANITY CHECKS (Invariant Metrics)
# Pageviews and Clicks should be equal across both groups
# ============================================================

print('\n--- STEP 1: SANITY CHECKS (Invariant Metrics) ---')
print('Verifying traffic split is truly 50/50\n')

def sanity_check(control_val, experiment_val, metric_name):
    total    = control_val + experiment_val
    p_expect = 0.5
    observed = control_val / total
    se       = math.sqrt(p_expect * (1 - p_expect) / total)
    ci_lower = p_expect - 1.96 * se
    ci_upper = p_expect + 1.96 * se
    passed   = ci_lower <= observed <= ci_upper
    print(f'{metric_name}:')
    print(f'  Control: {control_val:,} | Experiment: {experiment_val:,}')
    print(f'  Observed fraction: {observed:.4f}')
    print(f'  95% CI: [{ci_lower:.4f}, {ci_upper:.4f}]')
    print(f'  Sanity Check: {"✅ PASSED" if passed else "❌ FAILED"}')
    print()

# Total pageviews
ctrl_pv = int(control['Pageviews'].sum())
exp_pv  = int(experiment['Pageviews'].sum())
sanity_check(ctrl_pv, exp_pv, 'PDP Views (Pageviews)')

# Total clicks
ctrl_cl = int(control['Clicks'].sum())
exp_cl  = int(experiment['Clicks'].sum())
sanity_check(ctrl_cl, exp_cl, 'Checkout Initiated (Clicks)')

# Click-through probability (CTP)
ctrl_ctp = ctrl_cl / ctrl_pv
exp_ctp  = exp_cl / exp_pv
pool_ctp = (ctrl_cl + exp_cl) / (ctrl_pv + exp_pv)
se_ctp   = math.sqrt(pool_ctp * (1 - pool_ctp) * (1/ctrl_pv + 1/exp_pv))
ci_lower = (exp_ctp - ctrl_ctp) - 1.96 * se_ctp
ci_upper = (exp_ctp - ctrl_ctp) + 1.96 * se_ctp
print(f'Checkout Rate (CTP):')
print(f'  Control: {ctrl_ctp:.4f} | Experiment: {exp_ctp:.4f}')
print(f'  Difference: {exp_ctp - ctrl_ctp:.4f}')
print(f'  95% CI: [{ci_lower:.4f}, {ci_upper:.4f}]')
print(f'  Sanity Check: {"✅ PASSED" if ci_lower <= 0 <= ci_upper else "❌ FAILED"}')


# ============================================================
# STEP 3 — DROP NULL ROWS (last 14 days have no payment data)
# ============================================================

control_clean    = control.dropna(subset=['Enrollments', 'Payments'])
experiment_clean = experiment.dropna(subset=['Enrollments', 'Payments'])

# Totals for analysis
ctrl_pv_c  = int(control_clean['Pageviews'].sum())
exp_pv_c   = int(experiment_clean['Pageviews'].sum())
ctrl_cl_c  = int(control_clean['Clicks'].sum())
exp_cl_c   = int(experiment_clean['Clicks'].sum())
ctrl_enr   = int(control_clean['Enrollments'].sum())
exp_enr    = int(experiment_clean['Enrollments'].sum())
ctrl_pay   = int(control_clean['Payments'].sum())
exp_pay    = int(experiment_clean['Payments'].sum())

print('\n\n--- STEP 2: SAMPLE SUMMARY (Enrollment period only) ---\n')
summary = pd.DataFrame({
    'Metric': ['PDP Views', 'Checkout Initiated', 'Cart Additions', 'Completed Purchases'],
    'Control': [ctrl_pv_c, ctrl_cl_c, ctrl_enr, ctrl_pay],
    'Treatment': [exp_pv_c, exp_cl_c, exp_enr, exp_pay]
})
print(summary.to_string(index=False))


# ============================================================
# STEP 4 — Z-TEST FUNCTION
# ============================================================

def z_test(x_cont, n_cont, x_exp, n_exp, metric_name, d_min):
    p_cont  = x_cont / n_cont
    p_exp   = x_exp  / n_exp
    p_pool  = (x_cont + x_exp) / (n_cont + n_exp)
    se_pool = math.sqrt(p_pool * (1 - p_pool) * (1/n_cont + 1/n_exp))
    diff    = p_exp - p_cont
    z_score = diff / se_pool
    p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))
    ci_lower = diff - 1.96 * se_pool
    ci_upper = diff + 1.96 * se_pool
    stat_sig = abs(diff) > 1.96 * se_pool   # p < 0.05
    prac_sig = abs(diff) >= d_min            # practical significance

    print(f'\n{metric_name}:')
    print(f'  Control rate:   {p_cont:.4f} ({x_cont:,}/{n_cont:,})')
    print(f'  Treatment rate: {p_exp:.4f} ({x_exp:,}/{n_exp:,})')
    print(f'  Difference:     {diff:+.4f}')
    print(f'  Z-score:        {z_score:.4f}')
    print(f'  P-value:        {p_value:.4f}')
    print(f'  95% CI:         [{ci_lower:.4f}, {ci_upper:.4f}]')
    print(f'  d_min:          {d_min}')
    print(f'  Statistical Significance:  {"✅ YES (p < 0.05)" if stat_sig else "❌ NO (p >= 0.05)"}')
    print(f'  Practical Significance:    {"✅ YES" if prac_sig else "❌ NO (below d_min)"}')

    lift = round((p_exp - p_cont) / p_cont * 100, 2)
    return {
        'metric': metric_name,
        'control_rate': round(p_cont, 4),
        'treatment_rate': round(p_exp, 4),
        'difference': round(diff, 4),
        'lift_%': lift,
        'z_score': round(z_score, 4),
        'p_value': round(p_value, 4),
        'ci_lower': round(ci_lower, 4),
        'ci_upper': round(ci_upper, 4),
        'd_min': d_min,
        'stat_significant': stat_sig,
        'prac_significant': prac_sig
    }


# ============================================================
# STEP 5 — EVALUATION METRICS
# ============================================================

print('\n\n--- STEP 3: HYPOTHESIS TESTING (Evaluation Metrics) ---')
print('H0: No difference between Control and Treatment')
print('H1: Treatment (simplified checkout) changes conversion rates')
print('Alpha = 0.05 | Two-tailed test\n')

# Metric 1: Gross Conversion (Cart Additions / Checkout Initiated)
# d_min = 0.01 (1% minimum practical change)
r1 = z_test(ctrl_enr, ctrl_cl_c, exp_enr, exp_cl_c,
            'Gross Conversion (Cart Add Rate = Cart Additions / Checkout Initiated)',
            d_min=0.01)

# Metric 2: Net Conversion (Purchases / Checkout Initiated)
# d_min = 0.0075
r2 = z_test(ctrl_pay, ctrl_cl_c, exp_pay, exp_cl_c,
            'Net Conversion (Purchase Rate = Purchases / Checkout Initiated)',
            d_min=0.0075)


# ============================================================
# STEP 6 — RESULTS SUMMARY
# ============================================================

print('\n\n--- STEP 4: RESULTS SUMMARY ---\n')
results = pd.DataFrame([r1, r2])
print(results[['metric','control_rate','treatment_rate','lift_%','p_value','stat_significant','prac_significant']].to_string(index=False))


# ============================================================
# STEP 7 — CONCLUSION
# ============================================================

print('\n\n--- STEP 5: CONCLUSION ---\n')

gc_stat = r1['stat_significant']
gc_prac = r1['prac_significant']
nc_stat = r2['stat_significant']
nc_prac = r2['prac_significant']

print('Gross Conversion (Cart Add Rate):')
if gc_stat and gc_prac:
    print('  → Statistically AND practically significant.')
    print(f'  → Treatment reduced cart additions by {abs(r1["lift_%"])}%')
    print('  → Simplified checkout filters out less-committed users.')
elif gc_stat and not gc_prac:
    print('  → Statistically significant but NOT practically significant.')
    print('  → Change exists but too small to matter in business.')
else:
    print('  → NOT statistically significant. No meaningful difference.')

print()
print('Net Conversion (Purchase Rate):')
if nc_stat and nc_prac:
    print('  → Statistically AND practically significant.')
    print(f'  → Treatment changed purchase rate by {r2["lift_%"]}%')
elif nc_stat and not nc_prac:
    print('  → Statistically significant but NOT practically significant.')
else:
    print('  → NOT statistically significant.')
    print('  → Simplified checkout did NOT hurt purchase completion rate.')

print()
print('=' * 60)
print('FINAL RECOMMENDATION:')
print()
if gc_stat and not nc_stat:
    print('✅ LAUNCH the simplified checkout.')
    print()
    print('Rationale:')
    print('- Cart addition rate decreased (fewer uncommitted users entering checkout)')
    print('- Purchase completion rate unchanged (serious buyers still convert)')
    print('- Net effect: fewer drop-offs, same revenue, better UX for committed buyers')
    print('- Aligns with original goal: reduce checkout friction without losing revenue')
else:
    print('⚠️  DO NOT LAUNCH without further investigation.')
    print('The treatment did not achieve its intended goals.')
print('=' * 60)

print('\n✅ Analysis complete. Use these results in Power BI Page 6.')



# ============================================================
# STEP 8 — SAVE RESULTS TO MYSQL
# ============================================================

from sqlalchemy import create_engine

DB_USER     = 'root'
DB_PASSWORD = 'your_password_here'
DB_HOST     = 'localhost'
DB_PORT     = '3306'
DB_NAME     = 'olist_ecommerce'

engine = create_engine(
    f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4'
)

# Results table
results_df = pd.DataFrame([r1, r2])
results_df.to_sql('ab_test_statistics', con=engine, if_exists='replace', index=False)
print('\n✅ Results saved to MySQL → ab_test_statistics')

# Daily funnel table for trend charts
control_clean['variant']    = 'control'
experiment_clean['variant'] = 'treatment'

daily = pd.concat([control_clean, experiment_clean], ignore_index=True)
daily.columns = ['date','pdp_views','checkout_initiated','cart_additions','purchases','variant']
daily['date'] = pd.to_datetime(daily['date'] + ' 2023', format='%a, %b %d %Y')
daily['cart_add_rate']    = (daily['cart_additions'] / daily['checkout_initiated']).round(4)
daily['purchase_rate']    = (daily['purchases'] / daily['checkout_initiated']).round(4)
daily.to_sql('ab_test_daily', con=engine, if_exists='replace', index=False)
print('✅ Daily data saved to MySQL → ab_test_daily')
