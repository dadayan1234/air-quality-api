# app/calibration.py
import numpy as np
from math import sqrt

def fit_linear_calibration(sensor_values, reference_values):
    """
    Fit y = a * x + b by least squares.
    Returns (a, b, rmse)
    """
    x = np.array(sensor_values, dtype=float)
    y = np.array(reference_values, dtype=float)

    # Remove NaNs pairwise
    mask = ~np.isnan(x) & ~np.isnan(y)
    if mask.sum() < 2:
        raise ValueError("Not enough paired samples to fit linear model")

    x = x[mask]
    y = y[mask]
    A = np.vstack([x, np.ones(len(x))]).T
    a, b = np.linalg.lstsq(A, y, rcond=None)[0]
    y_hat = a * x + b
    rmse = sqrt(np.mean((y - y_hat) ** 2))
    return float(a), float(b), float(rmse)

def apply_linear(a, b, x):
    return a * x + b


def evaluate_rmse(y_true, y_pred):
    return np.sqrt(np.mean((np.array(y_true)-np.array(y_pred))**2))
