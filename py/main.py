from api.rewrite_engine import rewrite_text
from api.models.rewrite_models import RewriteInput, RewriteOutput

import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import tensorflow as tf
import numpy as np

# ============================================
# STEP 1: What This Model Does
# ============================================
# This model predicts how many bookings a beauty clinic will get
# based on how much money they spend on advertising.
# Input: Ad budget (in dollars)
# Output: Number of bookings (appointments)

print("=" * 60)
print("BOOKING PREDICTION MODEL")
print("=" * 60)
print("This model learns: Budget -> Bookings")
print("Example: If you spend $3000 on ads, how many bookings?")
print()

# ============================================
# STEP 2: Prepare Training Data
# ============================================
# Historical data from past ad campaigns

budgets = np.array([1000, 2000, 3000, 4000, 5000, 6000], dtype=float)
bookings = np.array([8, 15, 23, 31, 39, 48], dtype=float)

# Scale budgets by dividing by 1000
# This makes numbers smaller and easier for the model to learn
# 1000 -> 1, 2000 -> 2, 3000 -> 3, etc.
X = budgets / 1000.0  # Scaled budgets
y = bookings  # Bookings stay as-is

# Reshape for TensorFlow (needs 2D arrays)
X = X.reshape(-1, 1)  # Shape: (6, 1)
y = y.reshape(-1, 1)  # Shape: (6, 1)

print("Training Data:")
print("Budget ($) -> Bookings")
for i in range(len(budgets)):
    print(f"  ${budgets[i]:.0f} -> {bookings[i]:.0f} bookings")
print()

# ============================================
# STEP 3: Build the Model
# ============================================
# Simple linear model: 1 input, 1 Dense layer, 1 output

model = tf.keras.Sequential([
    tf.keras.layers.Input(shape=(1,)),  # 1 input feature (scaled budget)
    tf.keras.layers.Dense(units=1)       # 1 output (bookings)
])

# Compile with Adam optimizer and MSE loss
model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.01),
    loss='mean_squared_error'
)

print("Model Architecture:")
print("  Input: Scaled budget (budget / 1000)")
print("  Layer: Dense (1 unit)")
print("  Output: Bookings")
print()

# ============================================
# STEP 4: Train the Model
# ============================================
# Train for 500 epochs

print("Training the model...")
print("(This may take a moment)\n")

history = model.fit(
    X, y,
    epochs=500,
    verbose=0  # Set to 1 if you want to see training progress
)

print("Training completed!\n")

# ============================================
# STEP 5: Make Predictions
# ============================================
# Predict bookings for new budgets

test_budgets = [1500, 2500, 3500, 4500]

print("=" * 60)
print("PREDICTIONS")
print("=" * 60)

for budget in test_budgets:
    # Scale the input (divide by 1000)
    scaled_budget = budget / 1000.0
    # Make prediction
    prediction = model.predict(np.array([[scaled_budget]]), verbose=0)
    # Print result
    print(f"Budget ${budget:,.0f} -> Predicted: {prediction[0][0]:.2f} bookings")

print()

# ============================================
# STEP 6: Show Learned Weight and Bias
# ============================================
# The model learned: bookings = weight * (budget/1000) + bias

weights, bias = model.layers[0].get_weights()
learned_weight = weights[0][0]
learned_bias = bias[0]

print("=" * 60)
print("WHAT THE MODEL LEARNED")
print("=" * 60)
print(f"Weight: {learned_weight:.4f}")
print(f"Bias:   {learned_bias:.4f}")
print()
print("The learned equation:")
print(f"  bookings ~ {learned_weight:.4f} * (budget/1000) + {learned_bias:.4f}")
print()
print("In simple words:")
print(f"  - For every $1000 spent, you get about {learned_weight:.2f} bookings")
print(f"  - Even with $0 budget, you'd get about {learned_bias:.2f} bookings")
print("=" * 60)
print()

# ============================================
# STEP 7: How to Run
# ============================================
print("To run this model:")
print("  python py/main.py")
print()
