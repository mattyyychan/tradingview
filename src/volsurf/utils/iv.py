import math
from typing import Optional


SQRT_2 = math.sqrt(2.0)
SQRT_2PI = math.sqrt(2.0 * math.pi)


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / SQRT_2PI


def _norm_cdf(x: float) -> float:
    # Use math.erf for a fast and accurate normal CDF
    return 0.5 * (1.0 + math.erf(x / SQRT_2))


def _black_scholes_price(s: float, k: float, t: float, r: float, sigma: float, is_call: bool) -> float:
    if t <= 0 or sigma <= 0 or s <= 0 or k <= 0:
        return max(0.0, (s - k) if is_call else (k - s))
    d1 = (math.log(s / k) + (r + 0.5 * sigma * sigma) * t) / (sigma * math.sqrt(t))
    d2 = d1 - sigma * math.sqrt(t)
    if is_call:
        return s * _norm_cdf(d1) - k * math.exp(-r * t) * _norm_cdf(d2)
    return k * math.exp(-r * t) * _norm_cdf(-d2) - s * _norm_cdf(-d1)


def implied_volatility_newton(price: float, s: float, k: float, t: float, r: float, is_call: bool, initial_sigma: float = 0.3, tol: float = 1e-6, max_iter: int = 100) -> Optional[float]:
    if price <= 0 or s <= 0 or k <= 0 or t <= 0:
        return None
    sigma = max(1e-4, float(initial_sigma))
    for _ in range(max_iter):
        d1 = (math.log(s / k) + (r + 0.5 * sigma * sigma) * t) / (sigma * math.sqrt(t))
        vega = s * _norm_pdf(d1) * math.sqrt(t)
        if vega < 1e-8:
            return None
        model = _black_scholes_price(s, k, t, r, sigma, is_call)
        diff = model - price
        if abs(diff) < tol:
            return max(1e-6, min(5.0, sigma))
        sigma -= diff / vega
        if sigma <= 0:
            sigma = 1e-4
    return None
