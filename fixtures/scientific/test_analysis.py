"""Protected specification; this new synthetic fixture is not the Maya notebook."""

EXPECTED_PAIRS = (0.7, 0.65, 0.75, -0.5)
EXPECTED_S = 2.6


def check_correlations(actual):
    return len(actual) == 4 and all(
        abs(value - expected) < 1e-12
        for value, expected in zip(actual, EXPECTED_PAIRS)
    )
