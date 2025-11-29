import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import tensorflow as tf
import numpy as np

# Try to import sklearn for metrics and train_test_split
try:
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    sklearn_available = True
except ImportError:
    sklearn_available = False
    print("Warning: sklearn not available. Using manual implementations.")

# ============================================
# STEP 1: Generate Extended Synthetic Dataset
# ============================================

def generate_data(n_samples=1000, random_seed=42, include_noise=True):
    """
    Generate synthetic marketing data with rich features and realistic market noise.
    
    This function creates realistic relationships between multiple marketing metrics
    including budget, CTR, leads, CPC, CPM, impressions, conversion rate, platform, and day of week.
    
    Args:
        n_samples: Number of samples to generate
        random_seed: Random seed for reproducibility
        include_noise: If True, adds market noise, platform shocks, and outliers
    """
    np.random.seed(random_seed)
    
    # Sample budget between 500 and 10000 dollars
    budgets = np.random.uniform(500, 10000, n_samples)
    
    # Sample CTR between 0.01 (1%) and 0.10 (10%)
    ctrs = np.random.uniform(0.01, 0.10, n_samples)
    
    # Derive impressions from budget and an assumed CPM (Cost Per Mille) range
    # CPM typically ranges from $1 to $20 per 1000 impressions
    cpm = np.random.uniform(1.0, 20.0, n_samples)  # Cost per 1000 impressions
    # Impressions = (budget / CPM) * 1000
    impressions = (budgets / cpm) * 1000
    impressions = np.maximum(impressions, 0)
    
    # Derive clicks from impressions and CTR
    clicks = impressions * ctrs
    
    # Derive CPC (Cost Per Click) from budget and clicks
    # CPC = budget / clicks (avoid division by zero)
    cpc = np.where(clicks > 0, budgets / clicks, np.random.uniform(0.5, 5.0, n_samples))
    cpc = np.clip(cpc, 0.1, 10.0)  # Reasonable CPC range
    
    # Derive leads from clicks and a random lead conversion rate
    # Lead conversion rate: percentage of clicks that become leads (typically 2-10%)
    lead_conversion_rate = np.random.uniform(0.02, 0.10, n_samples)
    leads = clicks * lead_conversion_rate
    leads = np.maximum(leads, 0)
    
    # Sample platform: 0 = Meta (Facebook/Instagram), 1 = Google, 2 = TikTok
    platform = np.random.choice([0, 1, 2], n_samples)
    
    # Sample day of week: 0 = Monday, 6 = Sunday
    day_of_week = np.random.randint(0, 7, n_samples)
    
    # Add temporal features
    # Week of year: 1-52 (randomly distributed)
    week_of_year = np.random.randint(1, 53, n_samples)
    
    # Month: 1-12 (randomly distributed)
    month = np.random.randint(1, 13, n_samples)
    
    # Is weekend: 1 if Saturday (5) or Sunday (6), 0 otherwise
    is_weekend = np.where((day_of_week >= 5), 1, 0)
    
    # Season index: 0=Winter (Dec-Feb), 1=Spring (Mar-May), 2=Summer (Jun-Aug), 3=Fall (Sep-Nov)
    season_index = np.where(month <= 2, 0,  # Dec, Jan, Feb -> Winter
                   np.where(month <= 5, 1,   # Mar, Apr, May -> Spring
                   np.where(month <= 8, 2,   # Jun, Jul, Aug -> Summer
                   3)))                      # Sep, Oct, Nov -> Fall
    
    # Derive conversion_rate: percentage of leads that become bookings
    # This varies by platform and day of week
    base_conversion = np.random.uniform(0.05, 0.25, n_samples)  # Base 5-25%
    # Platform-specific conversion behavior:
    # Meta (0): balanced, normal conversion
    # Google (1): higher intent, better conversion per lead
    # TikTok (2): higher CTR but lower conversion (younger audience, lower intent)
    platform_boost = np.where(platform == 1, 0.02,  # Google: +2%
                      np.where(platform == 2, -0.03, 0.0))  # TikTok: -3%, Meta: 0
    # Weekends (5,6) might have different conversion
    weekend_boost = np.where((day_of_week >= 5), -0.01, 0.0)
    conversion_rate = base_conversion + platform_boost + weekend_boost
    conversion_rate = np.clip(conversion_rate, 0.01, 0.30)  # Keep in reasonable range
    
    # Initialize flags for tracking market shocks and outliers
    is_shock = np.zeros(n_samples, dtype=int)  # 1 if platform instability occurred
    is_outlier = np.zeros(n_samples, dtype=int)  # 1 if outlier was applied
    
    # ============================================
    # Add Market Noise: Platform Instability Effects
    # ============================================
    # Simulate real-world platform issues (algorithm changes, ad delivery problems, etc.)
    if include_noise:
        # 5-10% of samples experience platform instability
        shock_probability = np.random.uniform(0.05, 0.10)
        n_shocks = int(n_samples * shock_probability)
        shock_indices = np.random.choice(n_samples, n_shocks, replace=False)
        is_shock[shock_indices] = 1
        
        for idx in shock_indices:
            shock_type = np.random.choice(['ctr_drop', 'conversion_drop', 'leads_drop'])
            
            if shock_type == 'ctr_drop':
                # CTR suddenly drops (e.g., algorithm change, ad fatigue)
                ctrs[idx] = ctrs[idx] * np.random.uniform(0.3, 0.6)  # Drop by 40-70%
                # Recalculate clicks and leads with reduced CTR
                clicks[idx] = impressions[idx] * ctrs[idx]
                leads[idx] = clicks[idx] * lead_conversion_rate[idx]
                leads[idx] = max(leads[idx], 0)
                
            elif shock_type == 'conversion_drop':
                # Conversion rate drops (e.g., landing page issues, market saturation)
                conversion_rate[idx] = conversion_rate[idx] * np.random.uniform(0.4, 0.7)  # Drop by 30-60%
                conversion_rate[idx] = max(conversion_rate[idx], 0.01)  # Keep minimum
                
            elif shock_type == 'leads_drop':
                # Leads are lower than expected (e.g., quality issues, bot traffic)
                leads[idx] = leads[idx] * np.random.uniform(0.3, 0.6)  # Drop by 40-70%
                leads[idx] = max(leads[idx], 0)
        
        # Recalculate CPC after potential CTR changes
        cpc = np.where(clicks > 0, budgets / clicks, np.random.uniform(0.5, 5.0, n_samples))
        cpc = np.clip(cpc, 0.1, 10.0)
    
    # Define bookings as a function of multiple features
    # This simulates the real relationship we want the model to learn
    base = 1.0  # Base bookings
    noise_bookings = np.random.normal(0, 2, n_samples)  # Random Gaussian noise
    
    # True rule: bookings depend on budget, CTR, leads, conversion_rate, platform, and temporal features
    # Add temporal effects to make the model learn these patterns
    month_effect = np.sin(2 * np.pi * month / 12) * 3  # Seasonal variation
    week_effect = np.sin(2 * np.pi * week_of_year / 52) * 2  # Weekly variation
    weekend_effect = is_weekend * 1.5  # Weekend boost
    season_effect = season_index * 0.5  # Season variation
    
    # Platform-specific multipliers for bookings:
    # Meta (0): 1.0 (balanced), Google (1): 1.2 (higher intent), TikTok (2): 0.8 (lower conversion)
    platform_multiplier = np.where(platform == 0, 1.0,
                           np.where(platform == 1, 1.2, 0.8))
    
    true_bookings = (
        0.003 * budgets +                    # Budget contribution
        25.0 * ctrs +                        # CTR contribution
        0.08 * leads +                       # Leads contribution
        50.0 * conversion_rate +             # Conversion rate contribution
        -0.3 * day_of_week +                 # Day of week effect (slight variation)
        month_effect +                       # Monthly seasonal pattern
        week_effect +                        # Weekly pattern
        weekend_effect +                     # Weekend effect
        season_effect +                      # Season effect
        base                                 # Base bookings
    ) * platform_multiplier + noise_bookings  # Apply platform multiplier
    
    bookings = np.maximum(true_bookings, 0)  # Ensure bookings are non-negative
    
    # ============================================
    # Add Outliers: Extreme Values (1-2% of samples)
    # ============================================
    # Simulate tracking errors, data quality issues, or unusual campaign behavior
    if include_noise:
        outlier_probability = np.random.uniform(0.01, 0.02)
        n_outliers = int(n_samples * outlier_probability)
        outlier_indices = np.random.choice(n_samples, n_outliers, replace=False)
        is_outlier[outlier_indices] = 1
        
        for idx in outlier_indices:
            outlier_type = np.random.choice(['extreme_high', 'extreme_low'])
            
            if outlier_type == 'extreme_high':
                # Very high bookings compared to budget (e.g., viral campaign, tracking error)
                # Multiply bookings by 2-4x
                bookings[idx] = bookings[idx] * np.random.uniform(2.0, 4.0)
                
            elif outlier_type == 'extreme_low':
                # Very low bookings despite high budget/leads (e.g., technical issues, fraud)
                # Reduce bookings by 70-90%
                bookings[idx] = bookings[idx] * np.random.uniform(0.1, 0.3)
    
    # Final safety check: ensure all values are realistic and non-negative
    bookings = np.maximum(bookings, 0)  # Clamp to minimum of 0
    ctrs = np.clip(ctrs, 0.001, 0.15)  # Keep CTR in reasonable range
    leads = np.maximum(leads, 0)  # Leads cannot be negative
    conversion_rate = np.clip(conversion_rate, 0.01, 0.35)  # Keep conversion rate reasonable
    
    # ============================================
    # Compute Lead Quality Score
    # ============================================
    # Lead quality depends on conversion_rate, platform, and CTR
    # Higher quality for: better conversion, better platforms, reasonable CTR
    
    # Platform quality scores (Google > Meta > TikTok)
    platform_quality = np.where(platform == 1, 1.0,      # Google: highest quality
                       np.where(platform == 0, 0.85, 0.7))  # Meta: medium, TikTok: lower
    
    # CTR quality: optimal around 0.04-0.06, lower for extremes
    # Use a bell curve: quality peaks at 0.05 CTR
    optimal_ctr = 0.05
    ctr_quality = 1.0 - np.abs(ctrs - optimal_ctr) / 0.05  # Penalize deviation from optimal
    ctr_quality = np.clip(ctr_quality, 0.0, 1.0)
    
    # Conversion rate quality: higher conversion = higher quality
    conversion_quality = (conversion_rate - 0.01) / (0.30 - 0.01)  # Normalize to 0-1
    conversion_quality = np.clip(conversion_quality, 0.0, 1.0)
    
    # Combine factors to compute lead_quality (weighted average)
    lead_quality = (
        0.4 * conversion_quality +    # Conversion rate is most important (40%)
        0.35 * platform_quality +       # Platform matters (35%)
        0.25 * ctr_quality              # CTR quality matters (25%)
    )
    
    # Add some noise to make it realistic
    quality_noise = np.random.normal(0, 0.05, n_samples)
    lead_quality = lead_quality + quality_noise
    
    # Normalize to [0, 1] range
    lead_quality = np.clip(lead_quality, 0.0, 1.0)
    
    return (budgets, ctrs, leads, cpc, cpm, impressions, conversion_rate, 
            platform, day_of_week, week_of_year, month, is_weekend, season_index, 
            bookings, lead_quality, is_shock, is_outlier)

print("=" * 60)
print("PROFESSIONAL BOOKING PREDICTION MODEL (Extended Features)")
print("=" * 60)
print("Generating synthetic dataset with 9 features...")

# Generate data with noise (for final model)
budgets, ctrs, leads, cpc, cpm, impressions, conversion_rate, platform, day_of_week, week_of_year, month, is_weekend, season_index, bookings, lead_quality, is_shock, is_outlier = generate_data(n_samples=1000, random_seed=42, include_noise=True)

# Also generate clean data for comparison (without noise)
budgets_clean, ctrs_clean, leads_clean, cpc_clean, cpm_clean, impressions_clean, conversion_rate_clean, platform_clean, day_of_week_clean, week_of_year_clean, month_clean, is_weekend_clean, season_index_clean, bookings_clean, lead_quality_clean, _, _ = generate_data(n_samples=1000, random_seed=42, include_noise=False)

print(f"Generated {len(budgets)} samples")
print(f"Budget range: ${budgets.min():.0f} - ${budgets.max():.0f}")
print(f"CTR range: {ctrs.min():.3f} - {ctrs.max():.3f}")
print(f"Leads range: {leads.min():.0f} - {leads.max():.0f}")
print(f"CPC range: ${cpc.min():.2f} - ${cpc.max():.2f}")
print(f"CPM range: ${cpm.min():.2f} - ${cpm.max():.2f}")
print(f"Impressions range: {impressions.min():.0f} - {impressions.max():.0f}")
print(f"Conversion rate range: {conversion_rate.min():.3f} - {conversion_rate.max():.3f}")
print(f"Platform: {np.sum(platform == 0)} Meta, {np.sum(platform == 1)} Google, {np.sum(platform == 2)} TikTok")
print(f"Week of year range: {week_of_year.min()} - {week_of_year.max()}")
print(f"Month range: {month.min()} - {month.max()}")
print(f"Weekends: {np.sum(is_weekend == 1)}, Weekdays: {np.sum(is_weekend == 0)}")
print(f"Seasons: Winter={np.sum(season_index == 0)}, Spring={np.sum(season_index == 1)}, Summer={np.sum(season_index == 2)}, Fall={np.sum(season_index == 3)}")
print(f"Bookings range: {bookings.min():.1f} - {bookings.max():.1f}")
print(f"Lead quality range: {lead_quality.min():.3f} - {lead_quality.max():.3f} (0-1 scale)")
print(f"Market noise: {np.sum(is_shock)} platform shocks ({np.sum(is_shock)/len(is_shock)*100:.1f}%), {np.sum(is_outlier)} outliers ({np.sum(is_outlier)/len(is_outlier)*100:.1f}%)")
print()

# ============================================
# STEP 2: Build Feature Matrix X
# ============================================

# Scale features to similar ranges for better training
budget_scaled = budgets / 1000.0           # Scale budgets by dividing by 1000
leads_scaled = leads / 100.0                # Scale leads by dividing by 100
impressions_scaled = impressions / 1000.0    # Scale impressions by dividing by 1000
cpc_scaled = cpc / 10.0                      # Scale CPC by dividing by 10
cpm_scaled = cpm / 10.0                      # Scale CPM by dividing by 10
# Keep CTR as is (already between 0.01 and 0.10)
# Keep conversion_rate as is (already between 0.01 and 0.30)
# Keep day_of_week as is (0-6)

# Convert platform to one-hot encoding (3 features instead of 1)
# This allows the model to learn distinct patterns for each platform
platform_meta = (platform == 0).astype(float)      # 1 if Meta, 0 otherwise
platform_google = (platform == 1).astype(float)    # 1 if Google, 0 otherwise
platform_tiktok = (platform == 2).astype(float)    # 1 if TikTok, 0 otherwise

# Build base feature matrix X_base with shape (n_samples, 11)
# Columns: [budget_scaled, ctr, leads_scaled, cpc_scaled, cpm_scaled, 
#           impressions_scaled, conversion_rate, platform_meta, platform_google, 
#           platform_tiktok, day_of_week]
X_base = np.column_stack([
    budget_scaled,
    ctrs,
    leads_scaled,
    cpc_scaled,
    cpm_scaled,
    impressions_scaled,
    conversion_rate,
    platform_meta,      # One-hot: Meta
    platform_google,    # One-hot: Google
    platform_tiktok,    # One-hot: TikTok
    day_of_week
])

# ============================================
# Add Interaction Features
# ============================================
# Create interaction features to capture relationships between variables
budget_ctr = budget_scaled * ctrs                    # Budget-CTR interaction
ctr_conv = ctrs * conversion_rate                     # CTR-Conversion interaction
# Platform interactions: interact with each platform separately
leads_meta = leads_scaled * platform_meta            # Leads-Meta interaction
leads_google = leads_scaled * platform_google        # Leads-Google interaction
leads_tiktok = leads_scaled * platform_tiktok        # Leads-TikTok interaction
budget_meta = budget_scaled * platform_meta          # Budget-Meta interaction
budget_google = budget_scaled * platform_google      # Budget-Google interaction
budget_tiktok = budget_scaled * platform_tiktok      # Budget-TikTok interaction

# Build extended feature matrix X with base + interaction features (18 total)
# Base: 11 features, Interactions: 7 features (budget_ctr, ctr_conv, 3 leads_platform, 3 budget_platform)
X_with_interactions = np.column_stack([
    X_base,              # 11 base features (includes 3 one-hot platform features)
    budget_ctr,          # Interaction: budget * CTR
    ctr_conv,            # Interaction: CTR * conversion_rate
    leads_meta,          # Interaction: leads * Meta
    leads_google,        # Interaction: leads * Google
    leads_tiktok,        # Interaction: leads * TikTok
    budget_meta,         # Interaction: budget * Meta
    budget_google,       # Interaction: budget * Google
    budget_tiktok        # Interaction: budget * TikTok
])

# Add temporal features (scaled appropriately)
week_of_year_scaled = week_of_year / 52.0    # Scale to 0-1 range
month_scaled = month / 12.0                  # Scale to 0-1 range
# is_weekend and season_index are already 0-1 or 0-3, keep as is or scale
season_index_scaled = season_index / 3.0     # Scale to 0-1 range

# Build final feature matrix X with base + interactions + temporal features (22 total)
# Base: 11, Interactions: 7, Temporal: 4 = 22 features
X = np.column_stack([
    X_with_interactions,  # 18 features (11 base + 7 interactions)
    week_of_year_scaled,  # Temporal: week of year (scaled)
    month_scaled,         # Temporal: month (scaled)
    is_weekend,           # Temporal: is weekend (0 or 1)
    season_index_scaled   # Temporal: season index (scaled)
])

# Build target matrix Y with shape (n_samples, 2) for multi-task learning
# Task 1: bookings (column 0)
# Task 2: lead_quality (column 1)
Y = np.column_stack([bookings, lead_quality])

# Split into train and test sets (80% train, 20% test)
# Y is now a 2-column matrix: [bookings, lead_quality]
if sklearn_available:
    X_train_base, X_test_base, Y_train, Y_test = train_test_split(
        X_base, Y, test_size=0.2, random_state=42
    )
    X_train, X_test, _, _ = train_test_split(
        X, Y, test_size=0.2, random_state=42
    )
else:
    # Manual split if sklearn is not available
    split_idx = int(0.8 * len(X))
    X_train_base, X_test_base = X_base[:split_idx], X_base[split_idx:]
    X_train, X_test = X[:split_idx], X[split_idx:]
    Y_train, Y_test = Y[:split_idx], Y[split_idx:]

print("Data Preprocessing:")
print(f"Training samples: {len(X_train)}")
print(f"Test samples: {len(X_test)}")
print()
print("Base features (11): budget, CTR, leads, CPC, CPM, impressions, conversion_rate,")
print("  platform_meta, platform_google, platform_tiktok (one-hot), day_of_week")
print("Interaction features (8): budget*CTR, CTR*conversion_rate,")
print("  leads*Meta, leads*Google, leads*TikTok, budget*Meta, budget*Google, budget*TikTok")
print("Temporal features (4): week_of_year, month, is_weekend, season_index")
print(f"Total features: {X_train.shape[1]} (11 base + 8 interactions + 4 temporal = 23)")
print()

# ============================================
# STEP 3: Build and Train Models
# ============================================
# Train two models: one with base features, one with interaction features

def build_model(input_shape, multi_task=False):
    """
    Build a neural network model with the specified input shape.
    
    Args:
        input_shape: Number of input features
        multi_task: If True, output 2 values (bookings, lead_quality), else 1 (bookings only)
    """
    output_units = 2 if multi_task else 1
    
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(input_shape,)),
        tf.keras.layers.Dense(16, activation="relu"),   # Hidden layer 1: 16 neurons
        tf.keras.layers.Dense(8, activation="relu"),     # Hidden layer 2: 8 neurons
        tf.keras.layers.Dense(output_units)              # Output: 1 or 2 predictions
    ])
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss="mse"  # MSE works for both single and multi-output
    )
    return model

# Train Model 1: Base features only (11 features with one-hot platform)
# For comparison, keep single-task (bookings only)
print("=" * 60)
print("MODEL 1: Base Features Only (11 features) - Single Task")
print("=" * 60)
print("Training model with base features (bookings only)...")

# Extract bookings only for single-task model
y_train_bookings = Y_train[:, 0]
y_test_bookings = Y_test[:, 0]

model_base = build_model(11, multi_task=False)
history_base = model_base.fit(
    X_train_base, y_train_bookings,
    epochs=200,
    batch_size=32,
    validation_split=0.2,
    verbose=0
)

print("Training finished!\n")

# Train Model 2: Base + Interaction features (19 features: 11 base + 8 interactions)
# For comparison, keep single-task
print("=" * 60)
print("MODEL 2: Base + Interaction Features (19 features) - Single Task")
print("=" * 60)
print("Training model with base + interaction features (bookings only)...")

# Split X_with_interactions for model 2
if sklearn_available:
    X_train_interactions, X_test_interactions, _, _ = train_test_split(
        X_with_interactions, Y, test_size=0.2, random_state=42
    )
else:
    split_idx = int(0.8 * len(X_with_interactions))
    X_train_interactions, X_test_interactions = X_with_interactions[:split_idx], X_with_interactions[split_idx:]

y_train_interactions = Y_train[:, 0]  # Bookings only for single-task comparison
y_test_interactions = Y_test[:, 0]

model_interactions = build_model(19, multi_task=False)
history_interactions = model_interactions.fit(
    X_train_interactions, y_train_interactions,
    epochs=200,
    batch_size=32,
    validation_split=0.2,
    verbose=0
)

print("Training finished!\n")

# Train Model 3: Base + Interactions + Temporal features (23 features) - MULTI-TASK
print("=" * 60)
print("MODEL 3: Base + Interactions + Temporal Features (23 features) - MULTI-TASK")
print("=" * 60)
print("Training multi-task model: predicting bookings AND lead_quality...")

model_temporal = build_model(23, multi_task=True)
history_temporal = model_temporal.fit(
    X_train, Y_train,  # Y_train has shape (n_samples, 2): [bookings, lead_quality]
    epochs=200,
    batch_size=32,
    validation_split=0.2,
    verbose=0
)

print("Training finished!\n")

# ============================================
# STEP 4: Evaluate Both Models on Test Set
# ============================================

def evaluate_model(model, X_test_data, y_test_data, model_name, multi_task=False):
    """
    Evaluate a model and return metrics.
    
    Args:
        model: Trained model
        X_test_data: Test input features
        y_test_data: Test targets (1D for single-task, 2D for multi-task)
        model_name: Name for logging
        multi_task: If True, y_test_data is 2D with [bookings, lead_quality]
    
    Returns:
        For single-task: mae, rmse, r2, y_pred
        For multi-task: (mae_bookings, rmse_bookings, r2_bookings), 
                       (mae_quality, rmse_quality, r2_quality), y_pred
    """
    y_pred = model.predict(X_test_data, verbose=0)
    
    if multi_task:
        # Multi-task: y_pred has shape (n_samples, 2)
        # Extract predictions for each task
        y_pred_bookings = y_pred[:, 0]
        y_pred_quality = y_pred[:, 1]
        y_true_bookings = y_test_data[:, 0]
        y_true_quality = y_test_data[:, 1]
        
        # Evaluate bookings (task 1)
        if sklearn_available:
            mae_bookings = mean_absolute_error(y_true_bookings, y_pred_bookings)
            rmse_bookings = np.sqrt(mean_squared_error(y_true_bookings, y_pred_bookings))
            r2_bookings = r2_score(y_true_bookings, y_pred_bookings)
        else:
            mae_bookings = np.mean(np.abs(y_true_bookings - y_pred_bookings))
            rmse_bookings = np.sqrt(np.mean((y_true_bookings - y_pred_bookings) ** 2))
            ss_res = np.sum((y_true_bookings - y_pred_bookings) ** 2)
            ss_tot = np.sum((y_true_bookings - np.mean(y_true_bookings)) ** 2)
            r2_bookings = 1 - (ss_res / ss_tot)
        
        # Evaluate lead_quality (task 2)
        if sklearn_available:
            mae_quality = mean_absolute_error(y_true_quality, y_pred_quality)
            rmse_quality = np.sqrt(mean_squared_error(y_true_quality, y_pred_quality))
            r2_quality = r2_score(y_true_quality, y_pred_quality)
        else:
            mae_quality = np.mean(np.abs(y_true_quality - y_pred_quality))
            rmse_quality = np.sqrt(np.mean((y_true_quality - y_pred_quality) ** 2))
            ss_res = np.sum((y_true_quality - y_pred_quality) ** 2)
            ss_tot = np.sum((y_true_quality - np.mean(y_true_quality)) ** 2)
            r2_quality = 1 - (ss_res / ss_tot)
        
        return (mae_bookings, rmse_bookings, r2_bookings), (mae_quality, rmse_quality, r2_quality), y_pred
    else:
        # Single-task: y_pred is 1D
        y_pred = y_pred.flatten()
        
        if sklearn_available:
            mae = mean_absolute_error(y_test_data, y_pred)
            rmse = np.sqrt(mean_squared_error(y_test_data, y_pred))
            r2 = r2_score(y_test_data, y_pred)
        else:
            mae = np.mean(np.abs(y_test_data - y_pred))
            rmse = np.sqrt(np.mean((y_test_data - y_pred) ** 2))
            ss_res = np.sum((y_test_data - y_pred) ** 2)
            ss_tot = np.sum((y_test_data - np.mean(y_test_data)) ** 2)
            r2 = 1 - (ss_res / ss_tot)
        
        return mae, rmse, r2, y_pred

# Evaluate Model 1 (base features) - single-task
mae_base, rmse_base, r2_base, y_pred_base = evaluate_model(
    model_base, X_test_base, y_test_bookings, "Base Model", multi_task=False
)

# Evaluate Model 2 (base + interactions) - single-task
mae_interactions, rmse_interactions, r2_interactions, y_pred_interactions = evaluate_model(
    model_interactions, X_test_interactions, y_test_interactions, "Interactions Model", multi_task=False
)

# Evaluate Model 3 (base + interactions + temporal) - MULTI-TASK
(mae_bookings, rmse_bookings, r2_bookings), (mae_quality, rmse_quality, r2_quality), y_pred_temporal = evaluate_model(
    model_temporal, X_test, Y_test, "Multi-Task Model", multi_task=True
)

print("=" * 60)
print("MODEL COMPARISON - BOOKINGS PREDICTION")
print("=" * 60)
print(f"{'Metric':<10} {'Base (11)':<12} {'+Interactions (19)':<20} {'Multi-Task (23)':<18} {'Improvement':<15}")
print("-" * 75)
print(f"{'MAE':<10} {mae_base:<12.2f} {mae_interactions:<20.2f} {mae_bookings:<18.2f} {mae_interactions - mae_bookings:>+.2f}")
print(f"{'RMSE':<10} {rmse_base:<12.2f} {rmse_interactions:<20.2f} {rmse_bookings:<18.2f} {rmse_interactions - rmse_bookings:>+.2f}")
print(f"{'R²':<10} {r2_base:<12.4f} {r2_interactions:<20.4f} {r2_bookings:<18.4f} {r2_bookings - r2_interactions:>+.4f}")
print()

# Multi-task evaluation report
print("=" * 60)
print("MULTI-TASK MODEL EVALUATION REPORT")
print("=" * 60)
print("Task 1: Bookings Prediction")
print("-" * 60)
print(f"  MAE  = {mae_bookings:.2f} bookings")
print(f"  RMSE = {rmse_bookings:.2f} bookings")
print(f"  R²   = {r2_bookings:.4f}")
print()
print("Task 2: Lead Quality Prediction")
print("-" * 60)
print(f"  MAE  = {mae_quality:.4f} (on 0-1 scale)")
print(f"  RMSE = {rmse_quality:.4f} (on 0-1 scale)")
print(f"  R²   = {r2_quality:.4f}")
print()
print("Summary:")
print(f"  The model predicts both bookings and lead_quality simultaneously.")
print(f"  Bookings: {r2_bookings:.1%} of variation explained")
print(f"  Lead Quality: {r2_quality:.1%} of variation explained")
print("=" * 60)
print()

# Determine if multi-task model improved performance compared to interactions model
if mae_bookings < mae_interactions:
    improvement = f"Multi-task model improved MAE by {mae_interactions - mae_bookings:.2f} bookings"
    improvement_pct = ((mae_interactions - mae_bookings) / mae_interactions) * 100
    print(f"Summary - Multi-Task Model Impact (Bookings):")
    print(f"  {improvement} ({improvement_pct:.1f}% reduction)")
else:
    improvement = f"Multi-task model increased MAE by {mae_bookings - mae_interactions:.2f} bookings"
    print(f"Summary - Multi-Task Model Impact (Bookings):")
    print(f"  {improvement}")

if r2_bookings > r2_interactions:
    r2_improvement = f"R² improved by {r2_bookings - r2_interactions:.4f}"
    print(f"  {r2_improvement}")
elif r2_bookings < r2_interactions:
    r2_improvement = f"R² decreased by {r2_interactions - r2_bookings:.4f}"
    print(f"  {r2_improvement}")
else:
    print(f"  R² remained the same")

# Compare multi-task model to base model
print()
print("Multi-Task Model vs Base Model (Bookings):")
if mae_bookings < mae_base:
    print(f"  MAE improved by {mae_base - mae_bookings:.2f} bookings ({((mae_base - mae_bookings) / mae_base) * 100:.1f}% reduction)")
else:
    print(f"  MAE increased by {mae_bookings - mae_base:.2f} bookings")
if r2_bookings > r2_base:
    print(f"  R² improved by {r2_bookings - r2_base:.4f}")
else:
    print(f"  R² decreased by {r2_base - r2_bookings:.4f}")
print()

# Show 5 random examples from test set (using temporal model)
print("Sample Predictions - Multi-Task Model (5 random examples):")
print("-" * 140)
print(f"{'Budget':<8} {'CTR':<6} {'Platform':<9} {'Actual B':<10} {'Pred B':<10} {'Error B':<9} {'Actual Q':<10} {'Pred Q':<10} {'Error Q':<9}")
print("-" * 140)

# Get random indices
np.random.seed(42)
random_indices = np.random.choice(len(X_test), 5, replace=False)

for idx in random_indices:
    # Convert back to original scale for display
    budget_original = X_test[idx][0] * 1000
    ctr_original = X_test[idx][1]
    leads_original = X_test[idx][2] * 100
    cpc_original = X_test[idx][3] * 10
    conversion_original = X_test[idx][6]
    # Platform is now one-hot encoded at indices 7, 8, 9
    platform_meta_val = X_test[idx][7]
    platform_google_val = X_test[idx][8]
    platform_tiktok_val = X_test[idx][9]
    # Determine platform from one-hot encoding
    if platform_meta_val > 0.5:
        platform_original = 0  # Meta
    elif platform_google_val > 0.5:
        platform_original = 1  # Google
    else:
        platform_original = 2  # TikTok
    day_original = int(X_test[idx][10])
    actual_bookings = Y_test[idx][0]
    actual_quality = Y_test[idx][1]
    predicted_bookings = y_pred_temporal[idx][0]
    predicted_quality = y_pred_temporal[idx][1]
    error_bookings = abs(actual_bookings - predicted_bookings)
    error_quality = abs(actual_quality - predicted_quality)
    
    # Get temporal features for display (indices: 19-22 for temporal features)
    week_original = int(X_test[idx][19] * 52)
    month_original = int(X_test[idx][20] * 12)
    is_weekend_original = int(X_test[idx][21])
    season_original = int(X_test[idx][22] * 3)
    
    platform_names = ["Meta", "Google", "TikTok"]
    platform_name = platform_names[platform_original]
    
    print(f"${budget_original:>6.0f}  {ctr_original:>5.3f}  {platform_name:<9} "
          f"{actual_bookings:>9.2f}  {predicted_bookings:>9.2f}  {error_bookings:>8.2f}  "
          f"{actual_quality:>9.3f}  {predicted_quality:>9.3f}  {error_quality:>8.3f}")

print()

# ============================================
# STEP 5: Brief Interpretation
# ============================================

print("=" * 60)
print("MODEL INTERPRETATION")
print("=" * 60)

# Interpret results for temporal model
if mae_temporal < 3:
    mae_interpretation = "very small"
elif mae_temporal < 5:
    mae_interpretation = "small"
elif mae_temporal < 10:
    mae_interpretation = "moderate"
else:
    mae_interpretation = "large"

print(f"Error Analysis (Model with Temporal Features):")
print(f"  The model's average error is {mae_interpretation} ({mae_temporal:.2f} bookings).")

# Interpret R²
if r2_temporal > 0.9:
    r2_interpretation = "excellent"
    r2_explanation = "The model explains over 90% of the variation in bookings."
elif r2 > 0.7:
    r2_interpretation = "good"
    r2_explanation = "The model explains over 70% of the variation in bookings."
elif r2 > 0.5:
    r2_interpretation = "moderate"
    r2_explanation = "The model explains over 50% of the variation in bookings."
else:
    r2_interpretation = "needs improvement"
    r2_explanation = "The model could benefit from more features or different architecture."

print(f"  R² score is {r2_temporal:.4f}, which indicates {r2_interpretation} model fit.")
print(f"  {r2_explanation}")
print()
print("Temporal Features Explained:")
print("  - week_of_year: Captures weekly patterns and seasonal trends throughout the year")
print("  - month: Identifies monthly variations and seasonal effects")
print("  - is_weekend: Distinguishes weekend vs weekday booking patterns")
print("  - season_index: Captures broader seasonal trends (Winter, Spring, Summer, Fall)")
print()
print("Practical Use:")
print("  The model with temporal features can identify when bookings are higher or lower")
print("  based on time patterns, helping clinics plan campaigns and allocate resources")
print("  more effectively throughout the year.")
print("=" * 60)
print()

# ============================================
# Compare Model Performance: With vs Without Market Noise
# ============================================

print("=" * 60)
print("MARKET NOISE IMPACT ANALYSIS")
print("=" * 60)
print("Comparing model trained on noisy data vs clean data...")
print()

# Build clean data features (same preprocessing as noisy data)
budget_scaled_clean = budgets_clean / 1000.0
leads_scaled_clean = leads_clean / 100.0
impressions_scaled_clean = impressions_clean / 1000.0
cpc_scaled_clean = cpc_clean / 10.0
cpm_scaled_clean = cpm_clean / 10.0

# Convert platform to one-hot encoding for clean data
platform_meta_clean = (platform_clean == 0).astype(float)
platform_google_clean = (platform_clean == 1).astype(float)
platform_tiktok_clean = (platform_clean == 2).astype(float)

X_base_clean = np.column_stack([
    budget_scaled_clean,
    ctrs_clean,
    leads_scaled_clean,
    cpc_scaled_clean,
    cpm_scaled_clean,
    impressions_scaled_clean,
    conversion_rate_clean,
    platform_meta_clean,
    platform_google_clean,
    platform_tiktok_clean,
    day_of_week_clean
])

budget_ctr_clean = budget_scaled_clean * ctrs_clean
ctr_conv_clean = ctrs_clean * conversion_rate_clean
leads_meta_clean = leads_scaled_clean * platform_meta_clean
leads_google_clean = leads_scaled_clean * platform_google_clean
leads_tiktok_clean = leads_scaled_clean * platform_tiktok_clean
budget_meta_clean = budget_scaled_clean * platform_meta_clean
budget_google_clean = budget_scaled_clean * platform_google_clean
budget_tiktok_clean = budget_scaled_clean * platform_tiktok_clean

X_with_interactions_clean = np.column_stack([
    X_base_clean,
    budget_ctr_clean,
    ctr_conv_clean,
    leads_meta_clean,
    leads_google_clean,
    leads_tiktok_clean,
    budget_meta_clean,
    budget_google_clean,
    budget_tiktok_clean
])

week_of_year_scaled_clean = week_of_year_clean / 52.0
month_scaled_clean = month_clean / 12.0
season_index_scaled_clean = season_index_clean / 3.0

X_clean = np.column_stack([
    X_with_interactions_clean,
    week_of_year_scaled_clean,
    month_scaled_clean,
    is_weekend_clean,
    season_index_scaled_clean
])

# Build Y_clean with both bookings and lead_quality
Y_clean = np.column_stack([bookings_clean, lead_quality_clean])

# Split clean data
if sklearn_available:
    X_train_clean, X_test_clean, Y_train_clean, Y_test_clean = train_test_split(
        X_clean, Y_clean, test_size=0.2, random_state=42
    )
else:
    split_idx = int(0.8 * len(X_clean))
    X_train_clean, X_test_clean = X_clean[:split_idx], X_clean[split_idx:]
    Y_train_clean, Y_test_clean = Y_clean[:split_idx], Y_clean[split_idx:]

# Train model on clean data (single-task for comparison)
print("Training model on clean data (without noise, bookings only)...")
model_clean = build_model(23, multi_task=False)  # Single-task for comparison
y_train_clean_bookings = Y_train_clean[:, 0]
history_clean = model_clean.fit(
    X_train_clean, y_train_clean_bookings,
    epochs=200,
    batch_size=32,
    validation_split=0.2,
    verbose=0
)
print("Training finished!\n")

# Evaluate clean model (single-task for comparison)
y_test_clean_bookings = Y_test_clean[:, 0]  # Extract bookings only
mae_clean, rmse_clean, r2_clean, _ = evaluate_model(
    model_clean, X_test_clean, y_test_clean_bookings, "Clean Model", multi_task=False
)

# Compare metrics
print("=" * 60)
print("PERFORMANCE COMPARISON: Clean Data vs Noisy Data (Bookings)")
print("=" * 60)
print(f"{'Metric':<10} {'Clean Data':<15} {'Noisy Data':<15} {'Difference':<15} {'Change':<15}")
print("-" * 70)
print(f"{'MAE':<10} {mae_clean:<15.2f} {mae_bookings:<15.2f} {mae_bookings - mae_clean:>+14.2f} {((mae_bookings - mae_clean) / mae_clean * 100):>+14.1f}%")
print(f"{'RMSE':<10} {rmse_clean:<15.2f} {rmse_bookings:<15.2f} {rmse_bookings - rmse_clean:>+14.2f} {((rmse_bookings - rmse_clean) / rmse_clean * 100):>+14.1f}%")
print(f"{'R²':<10} {r2_clean:<15.4f} {r2_bookings:<15.4f} {r2_bookings - r2_clean:>+14.4f} {((r2_bookings - r2_clean) / r2_clean * 100):>+14.1f}%")
print()

# Interpretation
print("Analysis:")
if mae_bookings > mae_clean * 1.1:  # More than 10% worse
    print("  The model performance degraded significantly with market noise.")
    print("  This is expected - real-world data contains noise and outliers.")
    print("  The model remains useful but predictions are less precise.")
elif mae_bookings > mae_clean:
    print("  The model performance slightly decreased with market noise.")
    print("  This is normal - the model learned to handle realistic data variations.")
    print("  The model is robust and ready for real-world deployment.")
else:
    print("  The model maintained good performance despite market noise.")
    print("  This indicates strong robustness to data quality issues.")

if r2_bookings > 0.9:
    print(f"  R² of {r2_bookings:.4f} shows the model still explains most variation,")
    print("  even with platform shocks and outliers present.")
print()
print("Market Noise Effects Simulated:")
print(f"  - Platform instability: {np.sum(is_shock)} samples ({np.sum(is_shock)/len(is_shock)*100:.1f}%)")
print(f"  - Outliers: {np.sum(is_outlier)} samples ({np.sum(is_outlier)/len(is_outlier)*100:.1f}%)")
print("  These effects simulate real-world issues like algorithm changes,")
print("  ad delivery problems, tracking errors, and unusual campaign behavior.")
print("=" * 60)
print()

# ============================================
# Platform Differentiation Analysis
# ============================================

print("=" * 60)
print("PLATFORM DIFFERENTIATION ANALYSIS")
print("=" * 60)
print("Analyzing how well the model distinguishes between platforms...")
print()

# Group test predictions by platform
platform_test = []
for idx in range(len(X_test)):
    if X_test[idx][7] > 0.5:  # Meta
        platform_test.append(0)
    elif X_test[idx][8] > 0.5:  # Google
        platform_test.append(1)
    else:  # TikTok
        platform_test.append(2)
platform_test = np.array(platform_test)

# Calculate average predictions and errors per platform
platform_names = ["Meta", "Google", "TikTok"]
platform_stats = []

for p in range(3):
    platform_mask = platform_test == p
    if np.sum(platform_mask) > 0:
        platform_actual = y_test[platform_mask]
        platform_pred = y_pred_temporal[platform_mask]
        platform_mae = np.mean(np.abs(platform_actual - platform_pred))
        platform_avg_actual = np.mean(platform_actual)
        platform_avg_pred = np.mean(platform_pred)
        
        platform_stats.append({
            'name': platform_names[p],
            'count': np.sum(platform_mask),
            'avg_actual': platform_avg_actual,
            'avg_pred': platform_avg_pred,
            'mae': platform_mae
        })

print("Platform Performance Summary:")
print("-" * 70)
print(f"{'Platform':<10} {'Samples':<10} {'Avg Actual':<15} {'Avg Predicted':<15} {'MAE':<10}")
print("-" * 70)
for stat in platform_stats:
    print(f"{stat['name']:<10} {stat['count']:<10} {stat['avg_actual']:<15.2f} "
          f"{stat['avg_pred']:<15.2f} {stat['mae']:<10.2f}")
print()

# Check if model learned platform differences
print("Platform Differentiation:")
if len(platform_stats) == 3:
    meta_avg = platform_stats[0]['avg_pred']
    google_avg = platform_stats[1]['avg_pred']
    tiktok_avg = platform_stats[2]['avg_pred']
    
    print(f"  Meta average bookings: {meta_avg:.2f}")
    print(f"  Google average bookings: {google_avg:.2f}")
    print(f"  TikTok average bookings: {tiktok_avg:.2f}")
    print()
    
    # Check if differences match expected behavior
    if google_avg > meta_avg and meta_avg > tiktok_avg:
        print("  [OK] Model correctly learned: Google > Meta > TikTok (as expected)")
        print("    - Google has higher intent and better conversion")
        print("    - Meta has balanced behavior")
        print("    - TikTok has higher CTR but lower conversion")
    elif abs(google_avg - meta_avg) > 5 or abs(meta_avg - tiktok_avg) > 5:
        print("  [OK] Model learned distinct patterns for each platform")
        print("    The model can differentiate between platform behaviors.")
    else:
        print("  Model shows similar predictions across platforms.")
        print("  This may indicate the model needs more training or platform effects are subtle.")
else:
    print("  Could not analyze all platforms (insufficient test samples)")

print()
print("One-Hot Encoding Benefits:")
print("  - Each platform gets its own feature, allowing independent learning")
print("  - Model can learn platform-specific interactions (e.g., budget*Google)")
print("  - Better than single numeric encoding for categorical variables")
print("=" * 60)
print()

# ============================================
# STEP 6: Advanced Platform-Aware Optimization
# ============================================

print("=" * 60)
print("AI MEDIA PLANNING ASSISTANT")
print("Advanced Platform-Aware Optimization")
print("=" * 60)
print()

# Helper function to predict bookings for a specific platform
def predict_bookings_for_platform(model, budget, ctr, platform_name, avg_cpm, avg_lead_conversion, 
                                   avg_conversion_rate, default_day=3, default_week=26, 
                                   default_month=6, default_is_weekend=0, default_season=2):
    """
    Predict bookings for a given platform, budget, and CTR.
    
    Args:
        model: Trained TensorFlow model
        budget: Budget in dollars
        ctr: Click-through rate (0.02 = 2%)
        platform_name: 'Meta', 'Google', or 'TikTok'
        avg_cpm: Average cost per mille
        avg_lead_conversion: Average lead conversion rate
        avg_conversion_rate: Average conversion rate
        default_day, default_week, etc.: Default temporal values
    
    Returns:
        tuple: (predicted_bookings, leads_val)
    """
    # Set platform one-hot encoding
    platform_meta = 1.0 if platform_name == 'Meta' else 0.0
    platform_google = 1.0 if platform_name == 'Google' else 0.0
    platform_tiktok = 1.0 if platform_name == 'TikTok' else 0.0
    
    # Derive leads from budget and CTR
    impressions_val = (budget / avg_cpm) * 1000
    clicks = impressions_val * ctr
    leads_val = clicks * avg_lead_conversion
    leads_val = max(leads_val, 0)
    
    # Derive CPC
    cpc_val = budget / clicks if clicks > 0 else avg_cpm / 1000
    
    # Scale features
    budget_scaled = budget / 1000.0
    leads_scaled = leads_val / 100.0
    impressions_scaled = impressions_val / 1000.0
    cpc_scaled = cpc_val / 10.0
    cpm_scaled = avg_cpm / 10.0
    
    # Build base features
    base_features = np.array([[
        budget_scaled,
        ctr,
        leads_scaled,
        cpc_scaled,
        cpm_scaled,
        impressions_scaled,
        avg_conversion_rate,
        platform_meta,
        platform_google,
        platform_tiktok,
        default_day
    ]])
    
    # Add interaction features
    budget_ctr_interaction = budget_scaled * ctr
    ctr_conv_interaction = ctr * avg_conversion_rate
    leads_meta_interaction = leads_scaled * platform_meta
    leads_google_interaction = leads_scaled * platform_google
    leads_tiktok_interaction = leads_scaled * platform_tiktok
    budget_meta_interaction = budget_scaled * platform_meta
    budget_google_interaction = budget_scaled * platform_google
    budget_tiktok_interaction = budget_scaled * platform_tiktok
    
    interactions = np.array([[
        budget_ctr_interaction,
        ctr_conv_interaction,
        leads_meta_interaction,
        leads_google_interaction,
        leads_tiktok_interaction,
        budget_meta_interaction,
        budget_google_interaction,
        budget_tiktok_interaction
    ]])
    
    # Add temporal features
    week_scaled = default_week / 52.0
    month_scaled = default_month / 12.0
    season_scaled = default_season / 3.0
    
    temporal = np.array([[
        week_scaled,
        month_scaled,
        default_is_weekend,
        season_scaled
    ]])
    
    # Combine all features
    X_scenario = np.column_stack([base_features, interactions, temporal])
    
    # Predict bookings
    predicted_bookings = model.predict(X_scenario, verbose=0)[0][0]
    
    return predicted_bookings, leads_val

# Use average/default values for optimization
avg_cpm = np.mean(cpm)
avg_lead_conversion = 0.06  # Average lead conversion rate (2-10%, use 6%)
avg_conversion_rate = np.mean(conversion_rate)
default_day = 3  # Thursday (mid-week)
default_week = 26  # Mid-year
default_month = 6  # June (mid-year)
default_is_weekend = 0
default_season = 2  # Summer

# Optimization parameters
budget_min = 1000
budget_max = 10000
budget_step = 500
ctr_min = 0.02
ctr_max = 0.08
ctr_step = 0.01

target_bookings = 50
budget_cap = 5000

# Platform-specific CTR ranges (realistic ranges per platform)
platform_ctr_ranges = {
    'Meta': (0.015, 0.06),      # Meta typically has moderate CTR
    'Google': (0.02, 0.08),     # Google has higher intent, better CTR
    'TikTok': (0.03, 0.10)      # TikTok has high engagement, highest CTR
}

# ============================================
# PART 1: Platform-Aware Optimization
# ============================================

print("=" * 60)
print("PART 1: PLATFORM-AWARE OPTIMIZATION")
print("=" * 60)
print("Analyzing each platform separately to find optimal budget/CTR combinations")
print()

platforms = ['Meta', 'Google', 'TikTok']

for platform in platforms:
    print(f"\n{'='*60}")
    print(f"PLATFORM: {platform.upper()}")
    print(f"{'='*60}")
    
    # Use platform-specific CTR range
    platform_ctr_min, platform_ctr_max = platform_ctr_ranges[platform]
    ctr_values_platform = np.arange(platform_ctr_min, platform_ctr_max + ctr_step, ctr_step)
    budget_values = np.arange(budget_min, budget_max + budget_step, budget_step)
    
    print(f"Searching over {len(budget_values)} budget values and {len(ctr_values_platform)} CTR values...")
    print(f"CTR range: {platform_ctr_min:.3f} - {platform_ctr_max:.3f}")
    print()
    
    # Store scenarios for this platform
    platform_scenarios = []
    
    for budget in budget_values:
        for ctr in ctr_values_platform:
            predicted_bookings, leads_val = predict_bookings_for_platform(
                model_temporal, budget, ctr, platform, avg_cpm, avg_lead_conversion,
                avg_conversion_rate, default_day, default_week, default_month,
                default_is_weekend, default_season
            )
            
            platform_scenarios.append({
                'budget': budget,
                'ctr': ctr,
                'leads': leads_val,
                'predicted_bookings': predicted_bookings
            })
    
    # Convert to numpy array for sorting
    platform_scenarios = np.array([(s['budget'], s['ctr'], s['leads'], s['predicted_bookings']) 
                                   for s in platform_scenarios],
                                  dtype=[('budget', float), ('ctr', float), ('leads', float), ('bookings', float)])
    
    # Find minimum budget to reach target
    print(f"Target: At least {target_bookings} bookings")
    meets_target = platform_scenarios[platform_scenarios['bookings'] >= target_bookings]
    
    if len(meets_target) > 0:
        meets_target_sorted = np.sort(meets_target, order='budget')
        min_budget_scenario = meets_target_sorted[0]
        print(f"  ✓ Minimum budget: ${min_budget_scenario['budget']:.0f} (CTR: {min_budget_scenario['ctr']:.3f})")
        print(f"    -> Predicted bookings: {min_budget_scenario['bookings']:.2f}")
    else:
        print(f"  ✗ No combination found that reaches {target_bookings} bookings")
    
    # Find maximum bookings under budget cap
    print(f"\nBudget cap: ${budget_cap:,.0f}")
    under_cap = platform_scenarios[platform_scenarios['budget'] <= budget_cap]
    
    if len(under_cap) > 0:
        under_cap_sorted = np.sort(under_cap, order='bookings')[::-1]
        max_bookings_scenario = under_cap_sorted[0]
        print(f"  ✓ Maximum bookings: {max_bookings_scenario['bookings']:.2f} (Budget: ${max_bookings_scenario['budget']:.0f}, CTR: {max_bookings_scenario['ctr']:.3f})")
    else:
        print(f"  ✗ No combination found under ${budget_cap:,.0f} budget cap")
    
    # Top 3 scenarios for this platform
    print(f"\n{'─'*60}")
    print(f"TOP 3 SCENARIOS FOR {platform.upper()}")
    print(f"{'─'*60}")
    print(f"{'Platform':<10} {'Budget ($)':<12} {'CTR':<8} {'Leads':<10} {'Predicted Bookings':<20}")
    print(f"{'─'*60}")
    
    # Sort by bookings descending and take top 3
    top_scenarios = np.sort(platform_scenarios, order='bookings')[::-1][:3]
    for i, scenario in enumerate(top_scenarios, 1):
        print(f"{platform:<10} ${scenario['budget']:>10.0f}  {scenario['ctr']:>6.3f}  {scenario['leads']:>8.0f}  {scenario['bookings']:>18.2f}")
    print()

# ============================================
# PART 2: Combined Budget Allocation Scenario
# ============================================

print("\n" + "=" * 60)
print("PART 2: COMBINED BUDGET ALLOCATION")
print("=" * 60)
print("Exploring optimal budget splits across all platforms")
print()

total_budget_cap = 5000
print(f"Total budget cap: ${total_budget_cap:,.0f}")
print()

# Generate coarse grid of budget allocations
# We'll test various splits: (Meta, Google, TikTok)
allocation_splits = []

# Generate some representative splits
for meta_budget in range(0, total_budget_cap + 500, 1000):
    remaining = total_budget_cap - meta_budget
    for google_budget in range(0, remaining + 500, 1000):
        tiktok_budget = total_budget_cap - meta_budget - google_budget
        if tiktok_budget >= 0:
            allocation_splits.append((meta_budget, google_budget, tiktok_budget))

# Remove duplicates and sort
allocation_splits = list(set(allocation_splits))
allocation_splits.sort()

print(f"Testing {len(allocation_splits)} budget allocation combinations...")
print()

# Store results for each allocation
allocation_results = []

for meta_budget, google_budget, tiktok_budget in allocation_splits:
    total_predicted_bookings = 0
    platform_results = []
    
    # Meta allocation
    if meta_budget > 0:
        # Use typical CTR for Meta (middle of range)
        meta_ctr = (platform_ctr_ranges['Meta'][0] + platform_ctr_ranges['Meta'][1]) / 2
        meta_bookings, meta_leads = predict_bookings_for_platform(
            model_temporal, meta_budget, meta_ctr, 'Meta', avg_cpm, avg_lead_conversion,
            avg_conversion_rate, default_day, default_week, default_month,
            default_is_weekend, default_season
        )
        total_predicted_bookings += meta_bookings
        platform_results.append(('Meta', meta_budget, meta_ctr, meta_leads, meta_bookings))
    
    # Google allocation
    if google_budget > 0:
        # Use typical CTR for Google
        google_ctr = (platform_ctr_ranges['Google'][0] + platform_ctr_ranges['Google'][1]) / 2
        google_bookings, google_leads = predict_bookings_for_platform(
            model_temporal, google_budget, google_ctr, 'Google', avg_cpm, avg_lead_conversion,
            avg_conversion_rate, default_day, default_week, default_month,
            default_is_weekend, default_season
        )
        total_predicted_bookings += google_bookings
        platform_results.append(('Google', google_budget, google_ctr, google_leads, google_bookings))
    
    # TikTok allocation
    if tiktok_budget > 0:
        # Use typical CTR for TikTok
        tiktok_ctr = (platform_ctr_ranges['TikTok'][0] + platform_ctr_ranges['TikTok'][1]) / 2
        tiktok_bookings, tiktok_leads = predict_bookings_for_platform(
            model_temporal, tiktok_budget, tiktok_ctr, 'TikTok', avg_cpm, avg_lead_conversion,
            avg_conversion_rate, default_day, default_week, default_month,
            default_is_weekend, default_season
        )
        total_predicted_bookings += tiktok_bookings
        platform_results.append(('TikTok', tiktok_budget, tiktok_ctr, tiktok_leads, tiktok_bookings))
    
    allocation_results.append({
        'meta_budget': meta_budget,
        'google_budget': google_budget,
        'tiktok_budget': tiktok_budget,
        'total_bookings': total_predicted_bookings,
        'platform_results': platform_results
    })

# Sort by total bookings (descending)
allocation_results.sort(key=lambda x: x['total_bookings'], reverse=True)

# Print top 5 allocations
print("=" * 60)
print("TOP 5 BUDGET ALLOCATIONS")
print("=" * 60)
print(f"{'Rank':<6} {'Meta ($)':<10} {'Google ($)':<12} {'TikTok ($)':<12} {'Total Bookings':<15}")
print(f"{'─'*60}")

for i, result in enumerate(allocation_results[:5], 1):
    print(f"{i:<6} ${result['meta_budget']:>8.0f}  ${result['google_budget']:>10.0f}  ${result['tiktok_budget']:>10.0f}  {result['total_bookings']:>14.2f}")

print(f"\n{'─'*60}")
print("DETAILED BREAKDOWN OF TOP ALLOCATION:")
print(f"{'─'*60}")
top_allocation = allocation_results[0]
print(f"Total Budget: ${total_budget_cap:,.0f}")
print(f"Total Predicted Bookings: {top_allocation['total_bookings']:.2f}")
print()
print(f"{'Platform':<10} {'Budget ($)':<12} {'CTR':<8} {'Leads':<10} {'Bookings':<12}")
print(f"{'─'*60}")

for platform, budget, ctr, leads, bookings in top_allocation['platform_results']:
    if budget > 0:
        print(f"{platform:<10} ${budget:>10.0f}  {ctr:>6.3f}  {leads:>8.0f}  {bookings:>11.2f}")

print()

# ============================================
# STEP 7: How to Run
# ============================================

print("=" * 60)
print("To run this model:")
print("  python py/booking_model_pro.py")
print("=" * 60)
