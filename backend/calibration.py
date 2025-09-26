import numpy as np

def fit_linear_calibration(sensor_values, reference_values):
    # y = a*x + b
    x = np.array(sensor_values)
    y = np.array(reference_values)
    A = np.vstack([x, np.ones(len(x))]).T
    a, b = np.linalg.lstsq(A, y, rcond=None)[0]
    return a, b

def apply_linear(a, b, x):
    return a*x + b

def evaluate_rmse(y_true, y_pred):
    return np.sqrt(np.mean((np.array(y_true)-np.array(y_pred))**2))
