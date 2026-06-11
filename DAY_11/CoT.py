import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.tsa.seasonal import STL
from statsmodels.tsa.stattools import adfuller
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf

# ==========================
# LOAD DATA
# ==========================

df = pd.read_csv("sakshi_ppg_20260611T074737_len148s.csv")

target = "red_corrected"
time_col = "timestamp_ms"

print("="*50)
print("DATASET OVERVIEW")
print("="*50)

print(df.head())
print("\nShape:", df.shape)

# ==========================
# MISSING VALUE ANALYSIS
# ==========================

print("\n" + "="*50)
print("MISSING VALUE REPORT")
print("="*50)

missing_pct = (df.isnull().sum()/len(df))*100

print(missing_pct)

# ==========================
# STATISTICS
# ==========================

print("\n" + "="*50)
print("STATISTICAL SUMMARY")
print("="*50)

print("Mean :", df[target].mean())
print("Median :", df[target].median())
print("Std :", df[target].std())
print("Min :", df[target].min())
print("Max :", df[target].max())

# ==========================
# FEATURE ENGINEERING
# ==========================

print("\n" + "="*50)
print("FEATURE ENGINEERING")
print("="*50)

df['lag_1'] = df[target].shift(1)
df['lag_5'] = df[target].shift(5)

df['rolling_mean_10'] = (
    df[target]
    .rolling(10)
    .mean()
)

df['rolling_std_10'] = (
    df[target]
    .rolling(10)
    .std()
)

print(df[['lag_1',
          'lag_5',
          'rolling_mean_10',
          'rolling_std_10']].head())

# ==========================
# TIME SERIES PLOT
# ==========================

plt.figure(figsize=(15,5))

plt.plot(
    df[time_col],
    df[target]
)

plt.title("Time Series Plot")
plt.xlabel("Timestamp(ms)")
plt.ylabel(target)

plt.savefig("01_timeseries.png")
plt.close()

print("\nSaved: 01_timeseries.png")

# ==========================
# TREND ANALYSIS
# ==========================

df['trend'] = (
    df[target]
    .rolling(100)
    .mean()
)

plt.figure(figsize=(15,5))

plt.plot(df[target], label='Signal')

plt.plot(df['trend'], label='Trend')

plt.legend()

plt.title("Trend Analysis")

plt.savefig("02_trend.png")
plt.close()

print("Saved: 02_trend.png")

# ==========================
# DECOMPOSITION
# ==========================

print("\nRunning STL decomposition...")

sample = df[target].iloc[:2000]

stl = STL(
    sample,
    period=50
)

result = stl.fit()

# Combined decomposition

fig = result.plot()
fig.set_size_inches(12,8)

plt.tight_layout()

plt.savefig("03_decomposition.png")

plt.close()

print("Saved: 03_decomposition.png")

# ==========================
# STATIONARITY TEST
# ==========================

print("\n" + "="*50)
print("ADF TEST")
print("="*50)

adf_result = adfuller(sample)

print("ADF Statistic:", adf_result[0])
print("P-value:", adf_result[1])

if adf_result[1] < 0.05:
    print("Series is Stationary")
else:
    print("Series is Non-Stationary")

# ==========================
# ACF
# ==========================

plt.figure(figsize=(10,5))

plot_acf(
    sample,
    lags=30
)

plt.savefig("04_acf.png")

plt.close()

print("Saved: 04_acf.png")

# ==========================
# PACF
# ==========================

plt.figure(figsize=(10,5))

plot_pacf(
    sample,
    lags=30,
    method='ywm'
)

plt.savefig("05_pacf.png")

plt.close()

print("Saved: 05_pacf.png")

# ==========================
# FINAL SUMMARY
# ==========================

print("\n" + "="*50)
print("FINAL REPORT")
print("="*50)

print(f"""
Dataset Rows : {len(df)}

Target Column : {target}

Features Created:
- lag_1
- lag_5
- rolling_mean_10
- rolling_std_10

Generated Files:
- 01_timeseries.png
- 02_trend.png
- 03_decomposition.png
- 04_acf.png
- 05_pacf.png
""")