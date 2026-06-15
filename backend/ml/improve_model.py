"""
Model Improvement Script
Run different strategies to improve biomass prediction accuracy.

Current baseline: R² = 0.53, MAE = 19.3 t/ha
Target: R² > 0.65, MAE < 15 t/ha
"""

import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, StackingRegressor
from sklearn.model_selection import train_test_split, RandomizedSearchCV
from sklearn.metrics import r2_score, mean_absolute_error
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from scipy.stats import randint
import matplotlib.pyplot as plt
import seaborn as sns

print("="*80)
print("BIOMASS MODEL IMPROVEMENT PIPELINE")
print("="*80)

# Load data
data_path = "sentinel_gedi_training.csv"
df = pd.read_csv(data_path)
print(f"\n✅ Loaded {len(df):,} samples")

# Define features
feature_cols = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2',
                'ndvi', 'evi', 'savi', 'ndmi', 'nbr', 'elevation', 'slope']

X = df[feature_cols]
y = df['agbd_tonnes_per_ha']

# Split data
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Normalize
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

print(f"Training: {len(X_train):,} samples")
print(f"Test: {len(X_test):,} samples")

# Store results
results = []


# ============================================================================
# BASELINE MODEL
# ============================================================================
print("\n" + "="*80)
print("1. BASELINE RANDOM FOREST")
print("="*80)

rf_baseline = RandomForestRegressor(
    n_estimators=150, max_depth=15, min_samples_split=20,
    min_samples_leaf=10, max_features='sqrt', random_state=42, n_jobs=-1
)
rf_baseline.fit(X_train_scaled, y_train)

y_test_pred_baseline = rf_baseline.predict(X_test_scaled)
baseline_r2 = r2_score(y_test, y_test_pred_baseline)
baseline_mae = mean_absolute_error(y_test, y_test_pred_baseline)

print(f"\nBaseline Performance:")
print(f"  Test R²: {baseline_r2:.4f}")
print(f"  Test MAE: {baseline_mae:.2f} t/ha")

results.append({
    'Model': 'Baseline RF',
    'R2': baseline_r2,
    'MAE': baseline_mae,
    'Improvement_R2': 0.0,
    'Improvement_MAE': 0.0
})


# ============================================================================
# STRATEGY 1: HYPERPARAMETER TUNING
# ============================================================================
print("\n" + "="*80)
print("2. HYPERPARAMETER TUNING (RF)")
print("="*80)
print("This may take 10-15 minutes...\n")

param_dist = {
    'n_estimators': randint(100, 300),
    'max_depth': randint(10, 30),
    'min_samples_split': randint(10, 50),
    'min_samples_leaf': randint(5, 20),
    'max_features': ['sqrt', 'log2', 0.5, 0.7]
}

random_search = RandomizedSearchCV(
    RandomForestRegressor(random_state=42, n_jobs=-1),
    param_dist,
    n_iter=30,
    cv=5,
    scoring='r2',
    random_state=42,
    n_jobs=-1,
    verbose=1
)

random_search.fit(X_train_scaled, y_train)

print(f"\n✅ Best parameters:")
for param, value in random_search.best_params_.items():
    print(f"     {param}: {value}")

tuned_model = random_search.best_estimator_
y_test_pred_tuned = tuned_model.predict(X_test_scaled)
tuned_r2 = r2_score(y_test, y_test_pred_tuned)
tuned_mae = mean_absolute_error(y_test, y_test_pred_tuned)

print(f"\nTuned RF Performance:")
print(f"  Test R²: {tuned_r2:.4f} ({tuned_r2 - baseline_r2:+.4f})")
print(f"  Test MAE: {tuned_mae:.2f} t/ha ({tuned_mae - baseline_mae:+.2f})")

results.append({
    'Model': 'Tuned RF',
    'R2': tuned_r2,
    'MAE': tuned_mae,
    'Improvement_R2': tuned_r2 - baseline_r2,
    'Improvement_MAE': tuned_mae - baseline_mae
})


# ============================================================================
# STRATEGY 2: GRADIENT BOOSTING
# ============================================================================
print("\n" + "="*80)
print("3. GRADIENT BOOSTING")
print("="*80)

gb_model = GradientBoostingRegressor(
    n_estimators=200,
    max_depth=8,
    learning_rate=0.1,
    subsample=0.8,
    min_samples_split=20,
    min_samples_leaf=10,
    max_features='sqrt',
    random_state=42,
    verbose=0
)

print("Training Gradient Boosting...")
gb_model.fit(X_train_scaled, y_train)

y_test_pred_gb = gb_model.predict(X_test_scaled)
gb_r2 = r2_score(y_test, y_test_pred_gb)
gb_mae = mean_absolute_error(y_test, y_test_pred_gb)

print(f"\nGradient Boosting Performance:")
print(f"  Test R²: {gb_r2:.4f} ({gb_r2 - baseline_r2:+.4f})")
print(f"  Test MAE: {gb_mae:.2f} t/ha ({gb_mae - baseline_mae:+.2f})")

results.append({
    'Model': 'Gradient Boosting',
    'R2': gb_r2,
    'MAE': gb_mae,
    'Improvement_R2': gb_r2 - baseline_r2,
    'Improvement_MAE': gb_mae - baseline_mae
})


# ============================================================================
# STRATEGY 3: REMOVE OUTLIERS
# ============================================================================
print("\n" + "="*80)
print("4. OUTLIER REMOVAL")
print("="*80)

# IQR method
Q1 = y.quantile(0.25)
Q3 = y.quantile(0.75)
IQR = Q3 - Q1
lower = Q1 - 1.5 * IQR
upper = Q3 + 1.5 * IQR

mask = (y >= lower) & (y <= upper)
X_clean = X[mask]
y_clean = y[mask]

print(f"Samples removed: {len(y) - len(y_clean):,} ({(len(y)-len(y_clean))/len(y)*100:.1f}%)")

X_train_c, X_test_c, y_train_c, y_test_c = train_test_split(
    X_clean, y_clean, test_size=0.2, random_state=42
)

scaler_c = StandardScaler()
X_train_c_scaled = scaler_c.fit_transform(X_train_c)
X_test_c_scaled = scaler_c.transform(X_test_c)

rf_clean = RandomForestRegressor(
    n_estimators=150, max_depth=15, min_samples_split=20,
    min_samples_leaf=10, max_features='sqrt', random_state=42, n_jobs=-1
)
rf_clean.fit(X_train_c_scaled, y_train_c)

y_test_pred_clean = rf_clean.predict(X_test_c_scaled)
clean_r2 = r2_score(y_test_c, y_test_pred_clean)
clean_mae = mean_absolute_error(y_test_c, y_test_pred_clean)

print(f"\nClean Data RF Performance:")
print(f"  Test R²: {clean_r2:.4f} ({clean_r2 - baseline_r2:+.4f})")
print(f"  Test MAE: {clean_mae:.2f} t/ha ({clean_mae - baseline_mae:+.2f})")

results.append({
    'Model': 'RF on Clean Data',
    'R2': clean_r2,
    'MAE': clean_mae,
    'Improvement_R2': clean_r2 - baseline_r2,
    'Improvement_MAE': clean_mae - baseline_mae
})


# ============================================================================
# STRATEGY 4: FEATURE ENGINEERING
# ============================================================================
print("\n" + "="*80)
print("5. FEATURE ENGINEERING")
print("="*80)

X_eng = X.copy()

# Ratio features
X_eng['nir_red_ratio'] = X['nir'] / (X['red'] + 1)
X_eng['swir1_nir_ratio'] = X['swir1'] / (X['nir'] + 1)
X_eng['green_red_ratio'] = X['green'] / (X['red'] + 1)

# Composite indices
X_eng['brightness'] = X['red'] + X['green'] + X['blue']
X_eng['greenness'] = X['nir'] - (X['red'] + X['green']) / 2
X_eng['wetness'] = X['blue'] - X['swir1']

# Interactions
X_eng['ndvi_evi_product'] = X['ndvi'] * X['evi']
X_eng['elevation_slope_interaction'] = X['elevation'] * X['slope']

print(f"Features added: {len(X_eng.columns) - len(X.columns)}")

X_train_e, X_test_e, y_train_e, y_test_e = train_test_split(
    X_eng, y, test_size=0.2, random_state=42
)

scaler_e = StandardScaler()
X_train_e_scaled = scaler_e.fit_transform(X_train_e)
X_test_e_scaled = scaler_e.transform(X_test_e)

rf_eng = RandomForestRegressor(
    n_estimators=150, max_depth=15, min_samples_split=20,
    min_samples_leaf=10, max_features='sqrt', random_state=42, n_jobs=-1
)
rf_eng.fit(X_train_e_scaled, y_train_e)

y_test_pred_eng = rf_eng.predict(X_test_e_scaled)
eng_r2 = r2_score(y_test_e, y_test_pred_eng)
eng_mae = mean_absolute_error(y_test_e, y_test_pred_eng)

print(f"\nEngineered Features RF Performance:")
print(f"  Test R²: {eng_r2:.4f} ({eng_r2 - baseline_r2:+.4f})")
print(f"  Test MAE: {eng_mae:.2f} t/ha ({eng_mae - baseline_mae:+.2f})")

results.append({
    'Model': 'RF + Engineered Features',
    'R2': eng_r2,
    'MAE': eng_mae,
    'Improvement_R2': eng_r2 - baseline_r2,
    'Improvement_MAE': eng_mae - baseline_mae
})


# ============================================================================
# STRATEGY 5: MODEL STACKING
# ============================================================================
print("\n" + "="*80)
print("6. MODEL STACKING (ENSEMBLE)")
print("="*80)

base_models = [
    ('rf', RandomForestRegressor(n_estimators=150, max_depth=15, random_state=42, n_jobs=-1)),
    ('gb', GradientBoostingRegressor(n_estimators=150, max_depth=8, learning_rate=0.1, random_state=42))
]

stacking_model = StackingRegressor(
    estimators=base_models,
    final_estimator=Ridge(alpha=1.0),
    cv=5,
    n_jobs=-1
)

print("Training stacked ensemble...")
stacking_model.fit(X_train_scaled, y_train)

y_test_pred_stack = stacking_model.predict(X_test_scaled)
stack_r2 = r2_score(y_test, y_test_pred_stack)
stack_mae = mean_absolute_error(y_test, y_test_pred_stack)

print(f"\nStacked Ensemble Performance:")
print(f"  Test R²: {stack_r2:.4f} ({stack_r2 - baseline_r2:+.4f})")
print(f"  Test MAE: {stack_mae:.2f} t/ha ({stack_mae - baseline_mae:+.2f})")

results.append({
    'Model': 'Stacked Ensemble',
    'R2': stack_r2,
    'MAE': stack_mae,
    'Improvement_R2': stack_r2 - baseline_r2,
    'Improvement_MAE': stack_mae - baseline_mae
})


# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "="*80)
print("FINAL RESULTS - ALL STRATEGIES")
print("="*80)

results_df = pd.DataFrame(results).sort_values('R2', ascending=False)
print("\n" + results_df.to_string(index=False))

# Find best model
best = results_df.iloc[0]
print(f"\n🏆 BEST MODEL: {best['Model']}")
print(f"   Test R²: {best['R2']:.4f} (+{best['Improvement_R2']:.4f})")
print(f"   Test MAE: {best['MAE']:.2f} t/ha ({best['Improvement_MAE']:+.2f})")

# Save best model
if best['R2'] > baseline_r2:
    print(f"\n💾 Saving improved model...")
    
    # Determine which model to save
    if best['Model'] == 'Tuned RF':
        best_model = tuned_model
        best_scaler = scaler
        best_features = feature_cols
    elif best['Model'] == 'Gradient Boosting':
        best_model = gb_model
        best_scaler = scaler
        best_features = feature_cols
    elif best['Model'] == 'RF on Clean Data':
        best_model = rf_clean
        best_scaler = scaler_c
        best_features = feature_cols
    elif best['Model'] == 'RF + Engineered Features':
        best_model = rf_eng
        best_scaler = scaler_e
        best_features = list(X_eng.columns)
    else:  # Stacked Ensemble
        best_model = stacking_model
        best_scaler = scaler
        best_features = feature_cols
    
    model_data = {
        'model': best_model,
        'scaler': best_scaler,
        'feature_cols': best_features,
        'test_r2': best['R2'],
        'test_mae': best['MAE'],
        'training_samples': len(X_train),
        'model_type': best['Model']
    }
    
    joblib.dump(model_data, "biomass_model_v2_improved.pkl")
    print(f"   ✅ Saved as: biomass_model_v2_improved.pkl")
else:
    print("\n⚠️  No improvement found. Keep baseline model.")

# Visualization
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

axes[0].barh(results_df['Model'], results_df['R2'], color='steelblue')
axes[0].axvline(baseline_r2, color='red', linestyle='--', linewidth=2, label='Baseline')
axes[0].set_xlabel('R² Score', fontsize=12)
axes[0].set_title('Model Comparison - R²', fontsize=14)
axes[0].legend()
axes[0].grid(True, alpha=0.3, axis='x')

axes[1].barh(results_df['Model'], results_df['MAE'], color='coral')
axes[1].axvline(baseline_mae, color='red', linestyle='--', linewidth=2, label='Baseline')
axes[1].set_xlabel('MAE (tonnes/ha)', fontsize=12)
axes[1].set_title('Model Comparison - MAE', fontsize=14)
axes[1].legend()
axes[1].grid(True, alpha=0.3, axis='x')

plt.tight_layout()
plt.savefig('model_comparison.png', dpi=150, bbox_inches='tight')
print("\n📊 Visualization saved as: model_comparison.png")

print("\n" + "="*80)
print("✅ IMPROVEMENT PIPELINE COMPLETE!")
print("="*80)
