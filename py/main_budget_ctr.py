import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import tensorflow as tf
import numpy as np

# ============================================
# What This Script Does
# ============================================
# This script trains a small TensorFlow model to predict bookings from:
#   - budget (ad spend in dollars)
#   - ctr (click-through rate, e.g. 0.045 = 4.5%)

print("=" * 60)
print("BOOKING PREDICTION MODEL (Budget + CTR)")
print("=" * 60)
print("This model learns: [Budget, CTR] -> Bookings")
print()

# ============================================
# STEP 2: Define Training Data
# ============================================
# Small, realistic dataset from past ad campaigns

# Budgets in dollars
budgets = [1000, 2000, 3000, 4000, 5000, 6000]

# CTR values as fractions (0.020 = 2%, 0.035 = 3.5%, etc.)
ctrs = [0.020, 0.035, 0.045, 0.055, 0.065, 0.075]

# Bookings (targets to predict)
bookings = [5, 12, 20, 28, 37, 47]

# Convert to NumPy arrays
budgets = np.array(budgets, dtype=float)
ctrs = np.array(ctrs, dtype=float)
bookings = np.array(bookings, dtype=float)

# Scale budgets by dividing by 1000.0
# This makes numbers smaller and easier for the model to learn
# 1000 -> 1.0, 2000 -> 2.0, 3000 -> 3.0, etc.
budgets_scaled = budgets / 1000.0

# Stack scaled budgets and CTRs into a 2-column matrix
# Shape: (6, 2) - 6 samples, each with 2 features [budget_scaled, ctr]
X = np.column_stack([budgets_scaled, ctrs])

# Store bookings as a 1D array
# Shape: (6,) - 6 target values
y = bookings

print("Training Data:")
print("Budget ($) | CTR    | Bookings")
print("-" * 35)
for i in range(len(budgets)):
    print(f"${budgets[i]:.0f}      | {ctrs[i]:.3f}  | {bookings[i]:.0f}")
print()
print(f"Input shape (X): {X.shape}")  # Should be (6, 2)
print(f"Output shape (y): {y.shape}")  # Should be (6,)
print()

# ============================================
# STEP 3: Build the TensorFlow Model
# ============================================
# 2 inputs (budget_scaled, ctr) -> 1 output (bookings)

model = tf.keras.Sequential([
    tf.keras.layers.Input(shape=(2,)),  # 2 input features: [budget_scaled, ctr]
    tf.keras.layers.Dense(units=1)       # 1 output: bookings
])

# Compile the model
model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.01),
    loss='mean_squared_error'
)

print("Model Architecture:")
print("  Input: 2 features [budget_scaled, ctr]")
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
# Test cases with new budget and CTR combinations

test_cases = [
    {"budget": 3500, "ctr": 0.050},
    {"budget": 2500, "ctr": 0.030},
    {"budget": 5000, "ctr": 0.070}
]

print("=" * 60)
print("PREDICTIONS")
print("=" * 60)

for case in test_cases:
    budget = case["budget"]
    ctr = case["ctr"]
    
    # Scale the budget by dividing by 1000.0
    budget_scaled = budget / 1000.0
    
    # Build input array with shape (1, 2): [[budget_scaled, ctr]]
    input_data = np.array([[budget_scaled, ctr]])
    
    # Make prediction
    prediction = model.predict(input_data, verbose=0)
    
    # Print result in human-readable format
    print(f"If budget = ${budget:,} and ctr = {ctr:.3f} -> predicted bookings ~ {prediction[0][0]:.2f}")

# ============================================
# Show What the Model Learned
# ============================================
# Display the learned weights and bias

weights, bias = model.layers[0].get_weights()
weight_budget = weights[0][0]  # Weight for budget_scaled
weight_ctr = weights[1][0]      # Weight for CTR
learned_bias = bias[0]

print("=" * 60)
print("WHAT THE MODEL LEARNED")
print("=" * 60)
w1 = weight_budget
w2 = weight_ctr
print(f"w1 (weight for budget/1000): {w1:.4f}")
print(f"w2 (weight for CTR):         {w2:.4f}")
print(f"bias:                        {learned_bias:.4f}")
print()
print("The learned equation:")
print(f"  bookings ~ {w1:.4f} * (budget/1000) + {w2:.4f} * ctr + {learned_bias:.4f}")
print()
print("In simple terms:")
print(f"  - Each $1000 in budget contributes about {w1:.2f} bookings")
print(f"  - Each 0.01 (1%) increase in CTR contributes about {w2 * 0.01:.2f} bookings")
print(f"  - Base bookings (budget=$0, ctr=0): {learned_bias:.2f}")
print("=" * 60)
print()

print("To run this model:")
print("  python py/main_budget_ctr.py")

