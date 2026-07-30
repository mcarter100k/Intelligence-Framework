"""
forex_analyzer.py
─────────────────
ForexEventAnalyzer — wraps news_analysis and trade_logic functions
into the class interface expected by main.py and market_brain.py.
"""

from news_analysis import analyze_economic_event
from trade_logic   import analyze_impact


class ForexEventAnalyzer:
    """Thin wrapper around existing analysis functions."""

    def analyze_event(
        self,
        event: str,
        actual: str,
        forecast: str,
        previous: str,
        currency: str = "GBP",
    ) -> str:
        """
        Return a text analysis of a released economic event.
        Combines trade bias direction with qualitative context.
        """
        try:
            bias    = analyze_impact(event, actual, forecast, currency)
            context = analyze_economic_event(event, forecast, previous, currency)

            lines = []
            if bias and bias.strip():
                lines.append(f"  Signal   : {bias}")
            if context and context.strip():
                lines.append(f"  Context  : {context}")

            return "\n".join(lines) if lines else ""
        except Exception:
            return ""
