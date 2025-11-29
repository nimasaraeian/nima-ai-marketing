import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import tensorflow as tf
import numpy as np

# ============================================
# What This Script Does
# ============================================
# This script trains a small TensorFlow model to predict bookings
# from ad budget, CTR, and leads.

print("=" * 60)
print("BOOKING PREDICTION MODEL (Budget + CTR + Leads)")
print("=" * 60)
print("This model learns: [Budget, CTR, Leads] -> Bookings")
print()

# ============================================
# STEP 2: Define Training Data
# ============================================
# Synthetic but realistic dataset from past ad campaigns

budgets = [1000, 2000, 3000, 4000, 5000, 6000]
ctrs    = [0.020, 0.035, 0.045, 0.055, 0.065, 0.075]
leads   = [40,   90,   140,  190,  250,  310]
bookings = [5, 12, 20, 28, 37, 47]

# Convert each list to NumPy array with dtype=float
budgets = np.array(budgets, dtype=float)
ctrs = np.array(ctrs, dtype=float)
leads = np.array(leads, dtype=float)
bookings = np.array(bookings, dtype=float)

# Scale budgets by dividing by 1000.0
# This makes numbers smaller and easier for the model to learn
# 1000 -> 1.0, 2000 -> 2.0, 3000 -> 3.0, etc.
budgets_scaled = budgets / 1000.0

# Scale leads by dividing by 100.0 to keep values in similar range
# This helps the model learn more stable relationships
# 40 -> 0.4, 90 -> 0.9, 140 -> 1.4, etc.
leads_scaled = leads / 100.0

# Keep CTR as it is (values already small, between 0.02 and 0.075)

# Build input matrix X with shape (n_samples, 3)
# Each row contains: [budget_scaled, ctr, leads_scaled]
X = np.column_stack([budgets_scaled, ctrs, leads_scaled])

# Store bookings as a 1D array y
y = bookings

print("Training Data:")
print("Budget ($) | CTR    | Leads | Bookings")
print("-" * 45)
for i in range(len(budgets)):
    print(f"${budgets[i]:.0f}      | {ctrs[i]:.3f}  | {leads[i]:.0f}   | {bookings[i]:.0f}")
print()
print(f"Input shape (X): {X.shape}")  # Should be (6, 3)
print(f"Output shape (y): {y.shape}")  # Should be (6,)
print()

# ============================================
# STEP 3: Build the TensorFlow Model
# ============================================
# 3 inputs (budget_scaled, ctr, leads_scaled) -> 1 output (bookings)

model = tf.keras.Sequential([
    tf.keras.layers.Input(shape=(3,)),  # 3 input features: [budget_scaled, ctr, leads_scaled]
    tf.keras.layers.Dense(units=1)       # 1 output: bookings
])

# Compile the model
model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.01),
    loss='mean_squared_error'
)

print("Model Architecture:")
print("  Input: 3 features [budget_scaled, ctr, leads_scaled]")
print("  Layer: Dense (1 unit)")
print("  Output: Bookings")
print()

# Train the model
print("Training the model...")
print("(This may take a moment)\n")

history = model.fit(
    X, y,
    epochs=1000,
    verbose=0
)

print("Training finished!\n")

# ============================================
# STEP 4: Make Predictions for Test Scenarios
# ============================================
# Test cases with new budget, CTR, and leads combinations

test_cases = [
    {"budget": 3500, "ctr": 0.050, "leads": 160},
    {"budget": 2500, "ctr": 0.030, "leads": 80},
    {"budget": 5500, "ctr": 0.070, "leads": 280}
]

print("=" * 60)
print("PREDICTIONS")
print("=" * 60)

for case in test_cases:
    budget = case["budget"]
    ctr = case["ctr"]
    leads = case["leads"]
    
    # Scale budget just like training: budget_scaled = budget / 1000.0
    budget_scaled = budget / 1000.0
    
    # Scale leads just like training: leads_scaled = leads / 100.0
    leads_scaled = leads / 100.0
    
    # Build input row with shape (1, 3): [[budget_scaled, ctr, leads_scaled]]
    test_input = np.array([[budget_scaled, ctr, leads_scaled]])
    
    # Make prediction
    prediction = model.predict(test_input, verbose=0)
    
    # Print result in human-readable format
    print(f"If budget = ${budget:,}, ctr = {ctr:.3f}, leads = {leads} -> predicted bookings ~ {prediction[0][0]:.2f}")

print()

# ============================================
# STEP 5: Show Learned Weights and Interpret Them
# ============================================
# Extract weights and bias from the Dense layer

weights, bias = model.layers[0].get_weights()
w1 = weights[0][0]  # Weight for budget_scaled
w2 = weights[1][0]  # Weight for ctr
w3 = weights[2][0]  # Weight for leads_scaled
bias_value = bias[0]

print("=" * 60)
print("WHAT THE MODEL LEARNED")
print("=" * 60)
print(f"w1 (weight for budget/1000): {w1:.4f}")
print(f"w2 (weight for ctr):         {w2:.4f}")
print(f"w3 (weight for leads/100):    {w3:.4f}")
print(f"bias:                        {bias_value:.4f}")
print()
print("The learned equation:")
print(f"  bookings ~ {w1:.4f} * (budget/1000) + {w2:.4f} * ctr + {w3:.4f} * (leads/100) + {bias_value:.4f}")
print()
print("In simple terms:")
print(f"  - Each +$1000 in budget adds about {w1:.2f} bookings")
print(f"  - Each +0.01 (1%) increase in CTR adds about {w2 * 0.01:.2f} bookings")
print(f"  - Each +100 leads adds about {w3:.2f} bookings")
print("=" * 60)
print()

# ============================================
# STEP 6: How to Run
# ============================================
print("To run this model:")
print("  python py/main_budget_ctr_leads.py")






