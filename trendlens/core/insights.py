"""Turns numbers into plain-English sentences."""


def fit_quality(r2):
    return "strong" if r2 > 0.85 else "reasonable" if r2 > 0.6 else "weak"


def plain_english_summary(name, unit, step, metrics, trend, fc, breakpoint_label):
    slope = trend["slope"]
    direction = "increasing" if slope >= 0 else "decreasing"
    last = fc[-1]
    parts = [f"{name} is {direction} by about {abs(slope):.2f} {unit} per {step}."]
    if breakpoint_label is not None:
        parts.append(f"A pattern change shows up around {breakpoint_label}, where the trend shifts.")
    else:
        parts.append("No clear pattern change was detected.")
    parts.append(
        f"The model explains {metrics['r2'] * 100:.0f}% of the variation, which is a {fit_quality(metrics['r2'])} fit."
    )
    parts.append(
        f"If this continues, the value may reach about {last['value']:.1f} by {last['label']} "
        f"(likely range {last['lower']:.1f} to {last['upper']:.1f})."
    )
    return " ".join(parts)
