"""
market_brain.py

Aggregates all signals into one plain-English GBP/AUD market report.
Now includes HTF structure layer (weekly + daily trend).
"""

from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple

from utils import pacific_offset, hours_until, fmt_pst, utc_to_pst_12h

# Local aliases matching the names used throughout this file
def _get_local_offset():   return pacific_offset()
def _hours_until(s):       return hours_until(s)
def _fmt_pst(s, style="long"): return fmt_pst(s, style)
def _utc_to_local_12h(s): return utc_to_pst_12h(s)
def _to_local(s):          return fmt_pst(s, style="long")
def _to_local_short(s):    return fmt_pst(s, style="short")


from currency_strength import get_currency_strength
from session_context   import get_session_context
from liquidity_context import get_liquidity_context
from interest_rates    import get_rate_differential
from cot_data          import get_cot_data
from regime_detection  import get_regime
from cross_market      import get_cross_market
from value_context     import get_value_context
from risk_config       import get_size_note, get_grade, RISK_RULES, GRADE_CONFIG
from run_history       import save_run, get_cross_run_intelligence, format_cross_run_block
from decision_engine   import make_decision, format_decision_block
from macro_regime      import get_macro_regime
from template_match    import get_template_match
from intraday_context  import get_intraday_context
from forex_calendar    import ForexCalendarScraper
from forex_analyzer    import ForexEventAnalyzer
from news_analysis     import analyze_economic_event
from trade_logic       import analyze_impact

_W_STRENGTH  = 0.35
_W_LIQUIDITY = 0.25
_W_NEWS      = 0.15
_W_HTF       = 0.20
_W_RATES     = 0.05   # split evenly: 0.025 carry + 0.025 path
_W_COT       = 0.05
_W_CROSS     = 0.10


def _is_real_value(val: str) -> bool:
    if not val:
        return False
    return str(val).strip().lower() not in ("", "nan", "none", "n/a", "-")


# ── Main entry point ──────────────────────────────────────────────────────────

def build_market_report(trade_type: str = "auto", instrument: str = "GBP_AUD") -> Dict:
    _pair_display = instrument.replace("_", "/")
    report: Dict = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "generated_at_12h": (lambda d: d.strftime("%b %d  ") + d.strftime("%I:%M%p").lstrip("0").lower())(datetime.now()),
        "pair": _pair_display,
        "layers": {},
    }

    # Session runs first — if market is closed, return a minimal report immediately
    report["layers"]["session"] = get_session_context()
    if report["layers"]["session"].get("market_closed"):
        ses = report["layers"]["session"]
        report["market_closed"]   = True
        report["overall_bias"]    = "NEUTRAL"
        report["conviction_score"]= 0
        report["signal_summary"]  = []
        report["decision"]        = {
            "direction": "NO TRADE", "grade": "C", "risk_pct": 0.0,
            "conviction": 0, "primary_reason": ses.get("close_reason", "Market closed"),
        }
        return report

    report["market_closed"]                = False
    report["layers"]["currency_strength"]  = get_currency_strength(["GBP", "AUD"])
    report["layers"]["liquidity"]          = get_liquidity_context()
    report["layers"]["rates"]             = get_rate_differential()
    report["layers"]["cot"]               = get_cot_data()
    report["layers"]["regime"]            = get_regime(instrument)
    _reg_raw = report["layers"]["regime"]
    if not _reg_raw.get("error"):
        try:
            from regime_classifier_logger import log_regime as _log_regime
            _log_regime(_reg_raw, instrument)
        except Exception:
            pass  # logger never breaks the report
    report["layers"]["htf"]               = {
        "current_price":      _reg_raw.get("current_price"),
        "lt_trend":           _reg_raw.get("lt_trend", "RANGING"),
        "st_trend":           _reg_raw.get("st_trend", "RANGING"),
        "weekly_trend":       _reg_raw.get("st_trend", "RANGING"),
        "daily_trend":        _reg_raw.get("regime_d1", "UNKNOWN"),
        "context":            _reg_raw.get("weekly_context", "RANGING"),
        "context_note":       _reg_raw.get("context_note", ""),
        "structure_bias":     "BULLISH" if _reg_raw.get("regime_d1") == "TRENDING_UP" else (
                              "BEARISH" if _reg_raw.get("regime_d1") == "TRENDING_DOWN" else "NEUTRAL"),
        "ma50":               _reg_raw.get("ma50"),
        "ma200":              _reg_raw.get("ma200"),
        "price_vs_ma50":      _reg_raw.get("price_vs_ma50", "below"),
        "price_vs_ma200":     _reg_raw.get("price_vs_ma200", "below"),
        "higher_low_formed":  _reg_raw.get("hl", False),
        "higher_low_note":    "",
        "near_major_support": False,
        "major_support_note": "",
        "trend_age_weeks":    0,
        "lt_pct":             0.0,
        "st_pct":             0.0,
        "weekly_high":        None,
        "weekly_low":         None,
        "lt_high":            None,
        "lt_low":             None,
        "dist_from_lt_high":  None,
        "dist_from_lt_low":   None,
        "range_position":     None,
        "range_label":        "",
        "daily_structure_type": _reg_raw.get("structure", "TRANSITIONAL"),
        "daily_structure_note": "",
        "daily_swing_highs":  _reg_raw.get("confirmed_highs", []),
        "daily_swing_lows":   _reg_raw.get("confirmed_lows", []),
        "nearest_daily_swing_high": _reg_raw.get("latest_sh"),
        "nearest_daily_swing_low":  _reg_raw.get("latest_sl"),
        "dist_to_swing_high_pips":  None,
        "dist_to_swing_low_pips":   None,
        "fib_pct":            0,
        "fib_label":          "",
        "fib_levels":         {},
        "key_levels":         {},
        "recent_weekly_high": None,
        "recent_weekly_low":  None,
        "20wk_high":          None,
        "20wk_low":           None,
        "weekly_summary":     _reg_raw.get("context_note", ""),
        "daily_summary":      "",
        "error":              _reg_raw.get("error"),
    }
    report["layers"]["cross_market"]      = get_cross_market()
    report["layers"]["news"]              = _build_events_summary()

    # ── Degraded-data detection ───────────────────────────────────────────────
    # Check each layer for error flags — surface them so the report is honest
    _critical_layers = {
        "htf":             "HTF/Big Picture structure",
        "currency_strength":"Currency Strength",
        "regime":          "Market Regime (ATR/ADX)",
        "liquidity":       "Price Levels / Sweep",
        "cross_market":    "Cross-Market (VIX/Gold)",
    }
    _degraded_components = []
    for _layer_key, _layer_name in _critical_layers.items():
        _layer = report["layers"].get(_layer_key, {})
        if _layer.get("error"):
            _degraded_components.append(f"{_layer_name}: {_layer['error'][:60]}")

    # Non-critical but worth noting
    if report["layers"].get("cot", {}).get("error"):
        _degraded_components.append(f"COT/Big Money: {report['layers']['cot']['error'][:60]}")
    if report["layers"].get("news", {}).get("error"):
        _degraded_components.append(f"Calendar/News: {report['layers']['news']['error'][:60]}")

    # Check interest rate staleness
    _rate_stale = report["layers"].get("rates", {}).get("stale_warning", "")
    if _rate_stale:
        _degraded_components.append(f"Interest Rates: {_rate_stale[:80]}")

    # Check COT data age
    _cot_date = report["layers"].get("cot", {}).get("report_date", "")
    if _cot_date:
        try:
            from datetime import date as _date
            _cot_age = (_date.today() - _date.fromisoformat(_cot_date)).days
            if _cot_age > 14:
                _degraded_components.append(f"COT data: {_cot_age} days old (>14 day threshold)")
        except Exception:
            pass

    report["degraded"] = len(_degraded_components) > 0
    report["degraded_components"] = _degraded_components
    report["degraded_summary"] = (
        f"{len(_degraded_components)} component(s) degraded: " +
        " | ".join(_degraded_components)
    ) if _degraded_components else ""

    # Value context — uses data already collected above
    _liq   = report["layers"]["liquidity"]
    _reg   = report["layers"]["regime"]
    _htf   = report["layers"]["htf"]

    # Daily closes for value_context — sourced from OANDA (same feed as all other layers)
    _closes = []
    try:
        from oanda_feed import get_daily_bars as _oanda_daily
        _raw = _oanda_daily(pair=instrument.replace("_", ""), count=65)
        if _raw is not None and not _raw.empty:
            _closes = [float(v) for v in _raw["Close"].dropna().values]
    except Exception:
        pass

    report["layers"]["value"] = get_value_context(
        current_price = _liq.get("current_price") or _reg.get("current_price", 0),
        daily_closes  = _closes,
        pwh           = _liq.get("pwh", 0) or 0,
        pwl           = _liq.get("pwl", 0) or 0,
        today_high    = _reg.get("today_high", 0) or 0,
        today_low     = _reg.get("today_low", 0) or 0,
    )

    (report["overall_bias"], report["conviction_score"],
     report["signal_summary"], report["live_vs_structural_conflict"],
     report["live_dominant"], report["struct_dominant"]) = _aggregate_bias(
        report["layers"]["currency_strength"],
        report["layers"]["liquidity"],
        report["layers"]["htf"],
        report["layers"]["rates"],
        report["layers"]["cot"],
        report["layers"]["cross_market"],
        report["layers"]["news"],
    )
    report["confidence"] = report["conviction_score"]  # backward compat alias

    # Macro quadrant — must come before make_decision() so it's available as a layer
    report["layers"]["macro"]    = get_macro_regime(
        report["layers"]["cross_market"],
        report["layers"]["news"],
    )
    report["layers"]["intraday"] = get_intraday_context()

    report["decision"] = make_decision(report, trade_type=trade_type)

    # Log signal for outcome tracking — skip NO TRADE (nothing to validate)
    if report["decision"].get("direction") not in ("NO TRADE", ""):
        try:
            from trade_outcome_logger import log_signal as _log_signal
            report["signal_id"] = _log_signal(
                regime_data   = report["layers"]["regime"],
                decision_data = report["decision"],
                instrument    = instrument,
            )
        except Exception:
            pass  # logger failure must never break the report

    # Template match — after decision so fingerprint includes direction
    tmpl = get_template_match(report)
    report["template_match"] = tmpl
    report["decision"]["template_match"] = tmpl  # also embed in decision for display

    # ── Decision brief (trader-facing output layer) ───────────────────────────
    try:
        from decision_brief import get_decision_brief
        report["decision_brief"]  = get_decision_brief(instrument)
        report["brief_formatted"] = report["decision_brief"].format()
    except Exception:
        report["decision_brief"]  = None
        report["brief_formatted"] = "Brief unavailable"

    return report


# ── Events summary ────────────────────────────────────────────────────────────

def _build_events_summary() -> Dict:
    try:
        scraper  = ForexCalendarScraper()
        analyzer = ForexEventAnalyzer()
        df       = scraper.get_weekly_calendar()
    except Exception as exc:
        return {"error": str(exc), "events": [], "net_score": 0,
                "bias": "NEUTRAL", "data_available": False,
                "news_gate_disabled": True,
                "disable_reason": "Calendar fetch failed — news gate is off"}

    if df.empty:
        _stale = scraper.stale_info
        if _stale:
            _reason = (
                f"Calendar CSV is {_stale['days_old']} days old "
                f"(last event: {_stale['most_recent']}) — stale data cannot guard entries"
            )
        else:
            _reason = "Calendar unavailable — news gate is off"
        return {"error": None, "events": [], "net_score": 0,
                "bias": "NEUTRAL", "data_available": False,
                "news_gate_disabled": True,
                "disable_reason": _reason}

    processed: List[Dict] = []
    net_score = 0

    for _, ev in df.iterrows():
        actual   = str(ev.get("actual",   "")).strip()
        forecast = str(ev.get("forecast", "")).strip()
        previous = str(ev.get("previous", "")).strip()
        currency = str(ev.get("currency", "")).strip()
        event    = str(ev.get("event",    "")).strip()
        impact   = str(ev.get("impact",   "")).strip()

        has_actual   = _is_real_value(actual)
        has_forecast = _is_real_value(forecast)

        qualitative = analyze_economic_event(event, forecast, previous, currency)

        entry: Dict = {
            "time":        str(ev.get("time", "")),
            "currency":    currency,
            "event":       event,
            "impact":      impact,
            "actual":      actual if has_actual else "",
            "forecast":    forecast if has_forecast else "",
            "previous":    previous,
            "qualitative": qualitative,
            "trade_bias":  None,
            "analysis":    None,
            "status":      "upcoming",
        }

        if has_actual and has_forecast:
            entry["status"]     = "released"
            entry["trade_bias"] = analyze_impact(event, actual, forecast, currency)
            entry["analysis"]   = analyzer.analyze_event(
                event, actual, forecast, previous, currency
            )
            weight = 2 if "High" in impact else 1 if "Medium" in impact else 0
            bias_str = (entry["trade_bias"] or "").upper()
            if "BULLISH" in bias_str:
                net_score += weight
            elif "BEARISH" in bias_str:
                net_score -= weight
        elif has_actual and not has_forecast:
            entry["status"]     = "released"
            entry["trade_bias"] = "No forecast was published  -  direction not scored"

        processed.append(entry)

    clamped = max(-100, min(100, net_score * 20))
    bias    = "BULLISH" if clamped > 10 else "BEARISH" if clamped < -10 else "NEUTRAL"

    # Freshness check  -  how old is the most recent released event?
    from datetime import datetime as _dt
    released_times = []
    for e in processed:
        if e["status"] == "released" and e["time"]:
            try:
                t = _dt.strptime(str(e["time"])[:16], "%Y-%m-%d %H:%M")
                released_times.append(t)
            except Exception:
                pass
    now = _dt.now()
    if released_times:
        most_recent = max(released_times)
        age_days = (now - most_recent).total_seconds() / 86400
    else:
        age_days = 99

    if age_days > 3:
        stale = True
        stale_note = (
            f"Calendar data is {age_days:.0f} days old  -  "
            f"this week's events may not be fully reflected. "
            f"News layer weight is reduced. Check ForexFactory for current events."
        )
    else:
        stale = False
        stale_note = ""

    return {
        "error": None, "events": processed,
        "net_score": clamped, "bias": bias, "data_available": True,
        "stale": stale, "stale_note": stale_note, "age_days": round(age_days, 1),
    }


# ── Bias aggregation ──────────────────────────────────────────────────────────

def _aggregate_bias(
    strength: Dict, liquidity: Dict, htf: Dict, rates: Dict, cot: Dict, cross: Dict, news: Dict
) -> Tuple[str, int, List[Dict]]:
    signals: List[Dict] = []

    # Strength
    diff        = strength.get("differential", 0.0)
    s_available = strength.get("error") is None
    if s_available:
        s_bias = "BULLISH" if diff > 5 else "BEARISH" if diff < -5 else "NEUTRAL"
        signals.append({
            "layer":     "Currency Strength",
            "bias":      s_bias,
            "weight":    _W_STRENGTH,
            "raw_score": diff,
            "summary":   (
                f"GBP is {'stronger' if diff > 0 else 'weaker'} than AUD "
                f"by {abs(diff):.0f} points today"
            ),
            "available": True,
            "timeframe": "LIVE",
        })

    # HTF structure — uses context (dominant 20-week trend) not just short-term
    h_available = htf.get("error") is None
    if h_available:
        context      = htf.get("context", "RANGING")
        lt_trend     = htf.get("lt_trend", "RANGING")
        st_trend     = htf.get("st_trend", "RANGING")
        age          = htf.get("trend_age_weeks", 0)
        struct_type  = htf.get("daily_structure_type", "TRANSITIONAL")

        if context == "ESTABLISHED_UPTREND":
            h_bias, h_raw = "BULLISH", 80.0
            h_sum = f"5-month UPTREND, 4-week UPTREND — both timeframes bullish"
        elif context == "ESTABLISHED_DOWNTREND":
            h_bias, h_raw = "BEARISH", -80.0
            h_sum = f"5-month DOWNTREND, 4-week DOWNTREND — both timeframes bearish"
        elif context == "COUNTER_TREND_BOUNCE":
            h_bias, h_raw = "BEARISH", -60.0
            h_sum = f"5-month DOWNTREND — {age}wk counter-trend bounce, dominant trend DOWN"
        elif context == "PULLBACK_IN_UPTREND":
            h_bias, h_raw = "BULLISH", 50.0
            h_sum = f"5-month UPTREND with short-term pullback — look for long entry on dip"
        else:
            h_bias, h_raw = "NEUTRAL", 0.0
            h_sum = f"No clear trend on either timeframe — ranging market"

        # Daily structure confirmation adds ±10 to the raw score
        if struct_type == "HH_HL" and h_bias == "BULLISH":
            h_raw += 10
            h_sum += "  |  Daily: HH/HL structure confirms bullish"
        elif struct_type == "LH_LL" and h_bias == "BEARISH":
            h_raw -= 10
            h_sum += "  |  Daily: LH/LL structure confirms bearish"
        elif struct_type == "HH_HL" and h_bias == "BEARISH":
            h_raw += 5   # daily structure fighting the dominant trend — small conflict
            h_sum += "  |  Daily: HH/HL conflicts with bearish weekly bias"
        elif struct_type == "LH_LL" and h_bias == "BULLISH":
            h_raw -= 5
            h_sum += "  |  Daily: LH/LL conflicts with bullish weekly bias"

        signals.append({
            "layer":     "Big Picture Trend",
            "bias":      h_bias,
            "weight":    _W_HTF,
            "raw_score": h_raw,
            "summary":   h_sum,
            "available": True,
            "timeframe": "STRUCTURAL",
        })

    # Rates — split into two independent signals
    r_available = rates.get("error") is None
    if r_available:
        r_stale       = bool(rates.get("stale_warning"))
        r_diff        = rates.get("differential", 0)
        r_diff_bias   = rates.get("differential_bias", "NEUTRAL")
        r_stance_bias = rates.get("stance_bias", "NEUTRAL")
        r_stance_sc   = rates.get("stance_score", 0)

        # 1) Carry Signal — which currency has the higher rate today
        carry_raw = 0.0 if r_stale else (r_diff * 10 if abs(r_diff) > 0.5 else 0.0)
        signals.append({
            "layer":     "Carry Signal",
            "bias":      r_diff_bias,
            "weight":    _W_RATES / 2,
            "raw_score": carry_raw,
            "summary":   (
                f"BoE {rates['boe_rate']}% vs RBA {rates['rba_rate']}%  -  "
                f"{abs(r_diff):.2f}% {'GBP advantage' if r_diff > 0 else 'AUD advantage'}"
            ) + (" (STALE)" if r_stale else ""),
            "available": True,
            "stale":     r_stale,
            "timeframe": "STRUCTURAL",
        })

        # 2) Rate Path Signal — where rates are heading (more market-relevant)
        # stance_score range: hawkish=2, neutral=0, dovish=-1 per bank → combined -3 to +3
        # Scale to ±36 to be comparable with other signal magnitudes
        path_raw = 0.0 if r_stale else (r_stance_sc * 12)
        signals.append({
            "layer":     "Rate Path Signal",
            "bias":      r_stance_bias,
            "weight":    _W_RATES / 2,
            "raw_score": path_raw,
            "summary":   (
                f"BoE {rates['boe'].get('stance', '?')}, RBA {rates['rba'].get('stance', '?')}  -  "
                f"rate gap {'widening' if r_stance_sc > 0 else 'narrowing' if r_stance_sc < 0 else 'stable'}, "
                f"{r_stance_bias.lower()} for GBP/AUD"
            ) + (" (STALE)" if r_stale else ""),
            "available": True,
            "stale":     r_stale,
            "timeframe": "STRUCTURAL",
        })

    # Liquidity
    l_available = liquidity.get("error") is None
    if l_available:
        if liquidity.get("sweep_down") and not liquidity.get("sweep_up"):
            l_raw, l_bias = 70.0,  "BULLISH"
            l_sum = "A low was swept and price recovered  -  bullish signal"
        elif liquidity.get("sweep_up") and not liquidity.get("sweep_down"):
            l_raw, l_bias = -70.0, "BEARISH"
            l_sum = "A high was swept and price rejected  -  bearish signal"
        elif liquidity.get("sweep_up") and liquidity.get("sweep_down"):
            l_raw, l_bias = 0.0,   "NEUTRAL"
            l_sum = "Both a high and low swept today  -  mixed signal"
        else:
            l_raw, l_bias = 0.0,   "NEUTRAL"
            l_sum = "No sweep detected today  -  no directional signal from price levels"
        signals.append({
            "layer": "Price Level Signal", "bias": l_bias,
            "weight": _W_LIQUIDITY, "raw_score": l_raw,
            "summary": l_sum, "available": True,
            "timeframe": "LIVE",
        })


    # Cross-market context
    x_available = cross.get("error") is None
    if x_available:
        x_bias = cross.get("overall_bias", "NEUTRAL")
        x_raw  = 60.0 if x_bias == "BULLISH" else -60.0 if x_bias == "BEARISH" else 0.0
        risk_mode = cross.get("risk_mode", "NEUTRAL")
        dxy_chg   = cross.get("dxy_change", 0) or 0
        risk_label = f"Risk-{'off' if risk_mode == 'RISK_OFF' else 'on' if risk_mode == 'RISK_ON' else 'neutral'}"
        x_sum = f"{risk_label}, DXY {dxy_chg:+.2f}%  -  cross-market is {x_bias.lower()} for GBP/AUD"
        signals.append({
            "layer":     "Global Market Signal",
            "bias":      x_bias,
            "weight":    _W_CROSS,
            "raw_score": x_raw,
            "summary":   x_sum,
            "available": True,
            "timeframe": "LIVE",
        })
    else:
        signals.append({
            "layer":     "Global Market Signal",
            "bias":      "UNKNOWN",
            "weight":    0,
            "raw_score": 0,
            "summary":   "Cross-market data unavailable  -  layer not counted",
            "available": False,
        })

    # COT positioning
    c_available = cot.get("error") is None
    if c_available:
        c_bias = cot.get("pair_bias", "NEUTRAL")
        c_raw  = 50.0 if c_bias == "BULLISH" else -50.0 if c_bias == "BEARISH" else 0.0
        gbp_extreme = cot.get("gbp_extreme", False)
        aud_extreme = cot.get("aud_extreme", False)
        if gbp_extreme or aud_extreme:
            c_raw  = -c_raw
            c_bias = "BULLISH" if c_raw > 0 else "BEARISH" if c_raw < 0 else "NEUTRAL"
        gbp_net = cot.get("gbp_net", 0)
        aud_net = cot.get("aud_net", 0)
        gbp_dir = "long" if gbp_net > 0 else "short"
        aud_dir = "long" if aud_net > 0 else "short"
        c_sum = f"Institutions net {gbp_dir} GBP, net {aud_dir} AUD  -  {c_bias.lower()} GBP/AUD"
        if gbp_extreme or aud_extreme:
            c_sum += " (CONTRARIAN  -  extreme positioning)"
        # Stale if report is older than 14 days — zero the score
        c_stale = False
        _cot_report_date = cot.get("report_date", "")
        if _cot_report_date:
            try:
                from datetime import date as _date
                _cot_age_days = (_date.today() - _date.fromisoformat(_cot_report_date)).days
                c_stale = _cot_age_days > 14
            except Exception:
                pass
        if c_stale:
            c_raw = 0.0
            c_sum += " (STALE — data >14 days old)"
        signals.append({
            "layer":     "Hedge Fund Positioning",
            "bias":      c_bias,
            "weight":    _W_COT,
            "raw_score": c_raw,
            "summary":   c_sum,
            "available": True,
            "stale":     c_stale,
            "timeframe": "SLOW",
        })
    else:
        signals.append({
            "layer":     "Hedge Fund Positioning",
            "bias":      "UNKNOWN",
            "weight":    0,
            "raw_score": 0,
            "summary":   "COT data unavailable  -  layer not counted",
            "available": False,
        })

    # News
    n_available = news.get("data_available", False)
    if n_available:
        n_stale = news.get("stale", False)
        n_raw   = 0.0 if n_stale else news.get("net_score", 0)
        n_bias  = news.get("bias", "NEUTRAL")
        n_sum   = (
            f"Released economic data leans {n_bias.lower()} for GBP/AUD"
            if n_bias != "NEUTRAL"
            else "Released economic data shows no strong directional push"
        )
        news_weight = _W_NEWS * 0.4 if n_stale else _W_NEWS
        signals.append({
            "layer":     "Economic News",
            "bias":      n_bias,
            "weight":    news_weight,
            "raw_score": n_raw,
            "summary":   n_sum + (" (STALE — data >3 days old)" if n_stale else ""),
            "available": True,
            "stale":     n_stale,
            "timeframe": "SLOW" if n_stale else "RECENT",
        })
    else:
        signals.append({
            "layer":     "Economic News",
            "bias":      "UNKNOWN",
            "weight":    0,
            "raw_score": 0,
            "summary":   "Calendar data unavailable  -  this layer is not counted",
            "available": False,
        })

    # Total score
    total = sum(
        s["raw_score"] * s["weight"]
        for s in signals if s["available"]
    )
    bias = "BULLISH" if total > 8 else "BEARISH" if total < -8 else "NEUTRAL"

    # Honesty check  -  if live signals contradict structural, flag it
    live_signals       = [s for s in signals if s.get("available") and s.get("timeframe") == "LIVE"]
    structural_signals = [s for s in signals if s.get("available") and s.get("timeframe") == "STRUCTURAL"]
    live_biases        = [s["bias"] for s in live_signals       if s["bias"] not in ("NEUTRAL","UNKNOWN")]
    struct_biases      = [s["bias"] for s in structural_signals if s["bias"] not in ("NEUTRAL","UNKNOWN")]

    live_bull   = live_biases.count("BULLISH")
    live_bear   = live_biases.count("BEARISH")
    struct_bull = struct_biases.count("BULLISH")
    struct_bear = struct_biases.count("BEARISH")

    live_dominant   = "BULLISH" if live_bull > live_bear else "BEARISH" if live_bear > live_bull else "NEUTRAL"
    struct_dominant = "BULLISH" if struct_bull > struct_bear else "BEARISH" if struct_bear > struct_bull else "NEUTRAL"

    live_vs_structural_conflict = (
        live_dominant != "NEUTRAL" and
        struct_dominant != "NEUTRAL" and
        live_dominant != struct_dominant
    )

    # Confidence
    active = [s for s in signals if s["available"] and s["bias"] not in ("NEUTRAL", "UNKNOWN")]
    if not active:
        confidence = 10
    else:
        bullish = [s for s in active if s["bias"] == "BULLISH"]
        bearish = [s for s in active if s["bias"] == "BEARISH"]
        majority_count = max(len(bullish), len(bearish))
        agreement_pct  = majority_count / len(active)
        majority_signals = bullish if len(bullish) >= len(bearish) else bearish
        avg_strength     = sum(abs(s["raw_score"]) for s in majority_signals) / len(majority_signals)
        strength_mult    = min(1.0, avg_strength / 100.0)
        raw_conf         = agreement_pct * (0.5 + 0.5 * strength_mult) * 100
        confidence       = int(min(95, max(10, raw_conf)))

    return bias, confidence, signals, live_vs_structural_conflict, live_dominant, struct_dominant  # confidence = conviction_score internally


# ── Plain-English printer ─────────────────────────────────────────────────────

def _classify_setup(report: Dict, bias: str, conf: int, inv: Dict) -> Dict:
    """
    Derive plain-English setup classification from existing report data.
    Returns a dict used by the decision block printer.
    No new data fetched — uses what's already in the report.
    """
    htf      = report["layers"].get("htf", {})
    liq      = report["layers"].get("liquidity", {})
    val      = report["layers"].get("value", {})
    cross    = report["layers"].get("cross_market", {})
    regime   = report["layers"].get("regime", {})
    ses      = report["layers"].get("session", {})
    news     = report["layers"].get("news", {})
    strength = report["layers"].get("currency_strength", {})

    ctx        = htf.get("context", "UNKNOWN")
    lt_trend   = htf.get("lt_trend", "UNKNOWN")
    st_trend   = htf.get("st_trend", "UNKNOWN")
    fib_pct    = htf.get("fib_pct", 0) or 0
    higher_low = htf.get("higher_low_formed", False)
    near_sup   = htf.get("near_major_support", False)
    conflict   = report.get("live_vs_structural_conflict", False)
    live_dom   = report.get("live_dominant", "NEUTRAL")
    struct_dom = report.get("struct_dominant", "NEUTRAL")
    sweep_up   = liq.get("sweep_up", False)
    sweep_down = liq.get("sweep_down", False)
    val_verdict = val.get("verdict", "FAIR VALUE")
    val_bias    = val.get("verdict_bias", "NEUTRAL")
    adx        = regime.get("adx", 0) or 0
    fuel_pct   = regime.get("fuel_pct", 50) or 50
    vix_regime = cross.get("vix_regime", "NORMAL")
    session    = ses.get("session", "")
    str_diff   = (strength.get("GBP", 0) or 0) - (strength.get("AUD", 0) or 0)

    # ── Check for high-impact event in next 2h ────────────────────────────────
    event_risk = False
    event_name = ""
    for ev in news.get("events", []):
        if ev.get("impact", "") in ("High", "Orange", "Red"):
            hrs = _hours_until(str(ev.get("time", "")))
            if -0.5 < hrs < 2:
                event_risk = True
                event_name = ev.get("event", "high-impact event")
                break

    # ── 1. Setup type ─────────────────────────────────────────────────────────
    if event_risk:
        setup_type = "Event-risk window"
        setup_note = f"{event_name} within 2 hours — do not enter new positions"
    elif sweep_down and not conflict:
        setup_type = "Liquidity sweep reversal (bullish)"
        setup_note = "Low swept and price recovered — liquidity grabbed below, potential bounce"
    elif sweep_up and not conflict:
        setup_type = "Liquidity sweep reversal (bearish)"
        setup_note = "High swept and price rejected — liquidity grabbed above, potential drop"
    elif sweep_down and conflict:
        setup_type = "Sweep present — conflicting signals"
        setup_note = "Low swept (bullish signal) but strength conflicts — wait for confirmation"
    elif sweep_up and conflict:
        setup_type = "Sweep present — conflicting signals"
        setup_note = "High swept (bearish signal) but strength conflicts — wait for confirmation"
    elif ctx == "COUNTER_TREND_BOUNCE" and bias == "BEARISH":
        setup_type = "Bullish pullback in bearish trend"
        setup_note = "Short-term bounce is active but dominant trend is down — sell the rally"
    elif ctx == "COUNTER_TREND_BOUNCE" and bias == "BULLISH":
        setup_type = "Bullish bounce — trend may be shifting"
        setup_note = f"{'Higher low confirmed — structure improving.' if higher_low else 'Bounce from low.'} Watch for trend change signals."
    elif ctx == "PULLBACK_IN_UPTREND" and bias == "BULLISH":
        setup_type = "Pullback in uptrend"
        setup_note = "Dominant trend is up — current dip is a buying opportunity"
    elif ctx == "PULLBACK_IN_UPTREND" and bias == "BEARISH":
        setup_type = "Pullback in uptrend — conflicting signals"
        setup_note = "Trend is up but signals lean bearish — unclear, reduce size"
    elif ctx == "ESTABLISHED_DOWNTREND" and bias == "BEARISH":
        setup_type = "Trend continuation (bearish)"
        setup_note = "Dominant trend and current signals aligned — continuation short opportunity"
    elif ctx == "ESTABLISHED_UPTREND" and bias == "BULLISH":
        setup_type = "Trend continuation (bullish)"
        setup_note = "Dominant trend and current signals aligned — continuation long opportunity"
    elif bias in ("BULLISH", "BEARISH") and conf < 40:
        setup_type = "Mixed / unclear"
        setup_note = "Signals too split to define a clean setup — monitor only"
    elif adx < 20:
        setup_type = "Range / chop"
        setup_note = "Low trend strength — market is ranging. Trade edges only, not the middle"
    else:
        setup_type = "No clear setup"
        setup_note = "Signals are mixed or inconclusive — stand aside"

    # ── 2. Intraday vs swing split ────────────────────────────────────────────
    # Intraday: short-term move is actionable NOW for this session
    # Swing: multi-day setup worth holding overnight

    # Intraday quality
    if event_risk:
        intraday = "avoid"
        intraday_note = f"{event_name} in less than 2h — no new entries. Wait for it to pass."
    elif sweep_down or sweep_up:
        _sweep_dir = "bullish" if sweep_down else "bearish"
        if fuel_pct < 70:
            intraday = "yes"
            intraday_note = f"Sweep {_sweep_dir} — valid intraday trigger. Get confirmation on your chart this session."
        else:
            intraday = "caution"
            intraday_note = f"Sweep signal active but {fuel_pct}% of daily range already used — limited room left today."
    elif conflict and conf >= 40:
        intraday = "caution"
        _move_dir = live_dom.lower()
        intraday_note = f"Intraday move is {_move_dir} but the larger trend disagrees. If you trade, go small."
    elif bias in ("BULLISH", "BEARISH") and conf >= 50:
        intraday = "yes"
        intraday_note = "Signals well enough aligned for intraday participation. Confirm on chart."
    elif bias in ("BULLISH", "BEARISH") and conf >= 35:
        intraday = "caution"
        intraday_note = "Some signal alignment but conviction is low. Small size only, tight stops."
    else:
        intraday = "no"
        intraday_note = "Signals too split for intraday entry. Monitor and wait."

    # Swing quality
    is_value_aligned = (val_bias == "BEARISH" and bias == "BEARISH") or                        (val_bias == "BULLISH" and bias == "BULLISH")

    if ctx == "ESTABLISHED_DOWNTREND" and bias == "BEARISH" and is_value_aligned:
        swing = "yes"
        swing_note = "Trend and location both bearish — solid swing short environment. Hold overnight is fine."
    elif ctx == "ESTABLISHED_UPTREND" and bias == "BULLISH" and is_value_aligned:
        swing = "yes"
        swing_note = "Trend and location both bullish — solid swing long environment. Hold overnight is fine."
    elif ctx == "COUNTER_TREND_BOUNCE" and lt_trend == "DOWNTREND":
        _fv = val.get("fair_value", "")
        swing = "wait"
        swing_note = (f"Swing short is the eventual play. Not yet — price needs to rally toward {_fv} first. "
                      f"When it exhausts there, that's your swing short setup." if _fv else
                      "Swing short is the eventual play. Wait for this bounce to exhaust at resistance first.")
    elif higher_low and ctx == "COUNTER_TREND_BOUNCE":
        swing = "wait"
        swing_note = "Higher low is forming — possible swing long building. Wait for price to clear resistance before committing."
    elif conf < 45:
        swing = "no"
        swing_note = "Conviction too low for overnight risk. Intraday only if anything today."
    else:
        swing = "no"
        swing_note = "No clear multi-session setup. Don't hold overnight."

    # ── 3. Best trade expression ──────────────────────────────────────────────
    if event_risk:
        best_expression = f"Stand aside — {event_name} approaching"
    elif setup_type == "Liquidity sweep reversal (bullish)" and intraday == "yes":
        best_expression = "Buy pullback from sweep low with tight stop below the swept level"
    elif setup_type == "Liquidity sweep reversal (bearish)" and intraday == "yes":
        best_expression = "Sell rally from swept high with tight stop above the swept level"
    elif ctx == "COUNTER_TREND_BOUNCE" and lt_trend == "DOWNTREND":
        fv = val.get("fair_value", "")
        wk_mid = val.get("weekly_mid", "")
        target = fv or wk_mid
        best_expression = (f"Wait for rally toward {target} (fair value), then look for rejection and sell"
                          if target else
                          "Wait for bounce to exhaust at resistance, then sell")
    elif ctx in ("PULLBACK_IN_UPTREND",) and bias == "BULLISH":
        best_expression = "Buy dip at key support — confirm with price rejection off support"
    elif ctx == "ESTABLISHED_DOWNTREND" and bias == "BEARISH":
        nearest = liq.get("nearest_pool")
        best_expression = (f"Sell rally — watch for rejection at {nearest}" if nearest
                          else "Sell rally into resistance — confirm with rejection candle")
    elif ctx == "ESTABLISHED_UPTREND" and bias == "BULLISH":
        nearest = liq.get("nearest_pool")
        best_expression = (f"Buy dip — watch for support at {nearest}" if nearest
                          else "Buy dip — confirm with support hold")
    elif adx < 20:
        best_expression = "Range play — buy near range low, sell near range high. Avoid middle."
    else:
        best_expression = "No clear best expression — monitor and wait for setup to develop"

    # ── 4. What would flip the bias ───────────────────────────────────────────
    _ma50 = htf.get("ma50", "")
    _inv_level = inv.get("invalidation", "") if inv else ""
    _fib_61 = str(htf.get("fib_levels", {}).get("61.8", "")) if htf.get("fib_levels") else ""

    if ctx == "COUNTER_TREND_BOUNCE" and lt_trend == "DOWNTREND":
        if _inv_level:
            flip_note = f"Daily close above {_inv_level} — that's when the bounce becomes a breakout and I flip bullish"
        else:
            flip_note = "Daily close above this week's high — that flips the bias bullish"
    elif ctx == "COUNTER_TREND_BOUNCE" and lt_trend == "UPTREND":
        flip_note = "Daily close below this week's low — that flips the bias bearish"
    elif ctx == "ESTABLISHED_DOWNTREND" and bias == "BEARISH":
        flip_note = (f"Daily close above MA50 ({_ma50}) — that breaks downtrend structure and flips me neutral/bullish"
                    if _ma50 else "Daily close above the 50-day average — trend structure breaking")
    elif ctx == "ESTABLISHED_UPTREND" and bias == "BULLISH":
        flip_note = (f"Daily close below MA50 ({_ma50}) — that breaks uptrend structure and flips me neutral/bearish"
                    if _ma50 else "Daily close below the 50-day average — trend structure breaking")
    elif bias == "BULLISH":
        flip_note = "Daily close below the swing low — lower low on daily flips me bearish"
    elif bias == "BEARISH":
        flip_note = "Daily close above the swing high — higher high on daily flips me bullish"
    else:
        flip_note = "No clear bias to flip — waiting for a signal to emerge"

    # ── 5. What to wait for ──────────────────────────────────────────────────
    _fv_target = val.get("fair_value", "")
    _wk_mid    = val.get("weekly_mid", "")

    if event_risk:
        wait_for = f"{event_name} to pass. No entries until after the release."
    elif ctx == "COUNTER_TREND_BOUNCE" and lt_trend == "DOWNTREND":
        _target = _fv_target or _wk_mid
        if _target:
            wait_for = (f"Price to rally to {_target} (fair value). When it gets there and shows "
                       f"rejection, that's the short entry. Don't sell the bottom of a bounce.")
        else:
            wait_for = "The bounce to exhaust at resistance. Look for rejection candle near swing high before shorting."
    elif ctx == "COUNTER_TREND_BOUNCE" and lt_trend == "UPTREND":
        wait_for = "The pullback to find support. Look for a hold above the swing low before buying."
    elif sweep_down and conflict:
        wait_for = "GBP to start outperforming AUD on the day. Sweep is bullish but AUD strength conflicts — let that resolve."
    elif sweep_up and conflict:
        wait_for = "AUD to stay weak relative to GBP. Sweep is bearish but GBP strength is fighting it — let that resolve."
    elif bias == "NEUTRAL" or conf < 40:
        wait_for = "More signals to align. Right now they're too split. Nothing to act on."
    elif intraday == "caution":
        wait_for = "Price to reach a key level before entry. Do not chase — let it come to you."
    else:
        wait_for = "Your own chart confirmation — trend line break, rejection candle, level hold. Framework gives context, chart gives timing."

    # ── 6. Setup quality ─────────────────────────────────────────────────────
    quality_score = 0
    quality_reasons = []

    if not conflict: quality_score += 2; quality_reasons.append("signals aligned")
    if is_value_aligned: quality_score += 2; quality_reasons.append("location aligned")
    if (sweep_down and bias == "BULLISH") or (sweep_up and bias == "BEARISH"):
        quality_score += 2; quality_reasons.append("sweep confirmed")
    if conf >= 60: quality_score += 1; quality_reasons.append("high conviction")
    if not event_risk: quality_score += 1
    if adx > 25: quality_score += 1; quality_reasons.append("trending market")
    if fuel_pct < 65: quality_score += 1; quality_reasons.append("range fuel available")

    if quality_score >= 7:
        quality = "HIGH"
        quality_note = "Multiple factors aligned — this is a quality setup"
    elif quality_score >= 4:
        quality = "MEDIUM"
        quality_note = "Some factors aligned but not ideal — smaller size, tighter management"
    elif quality_score >= 2:
        quality = "LOW"
        quality_note = "Weak setup — if trading at all, minimum size only"
    else:
        quality = "DO NOT TRADE"
        quality_note = "Too many factors working against — stand aside"

    # ── Derive primary state, action_now, trade_plan ────────────────────────
    # primary_state: single-phrase master label shown at top
    if event_risk:
        primary_state = "EVENT RISK / NO TRADE"
        action_now    = f"Stand down — {event_name} approaching. No new positions."
    elif setup_type == "Liquidity sweep reversal (bullish)" and not conflict:
        primary_state = "SWEEP REVERSAL — BULLISH SIGNAL"
        action_now    = "Look for long confirmation on chart this session"
    elif setup_type == "Liquidity sweep reversal (bearish)" and not conflict:
        primary_state = "SWEEP REVERSAL — BEARISH SIGNAL"
        action_now    = "Look for short confirmation on chart this session"
    elif "conflicting" in setup_type.lower() and (sweep_up or sweep_down):
        primary_state = "SWEEP PRESENT / WAIT FOR CONFIRMATION"
        action_now    = "Do not act yet — sweep signal and strength are in conflict"
    elif ctx == "ESTABLISHED_DOWNTREND" and bias == "BEARISH" and not conflict:
        primary_state = "TREND CONTINUATION — BEARISH"
        action_now    = "Look for short on rally to resistance"
    elif ctx == "ESTABLISHED_UPTREND" and bias == "BULLISH" and not conflict:
        primary_state = "TREND CONTINUATION — BULLISH"
        action_now    = "Look for long on pullback to support"
    elif ctx in ("COUNTER_TREND_BOUNCE", "PULLBACK_IN_UPTREND") and conflict:
        primary_state = "WAIT / MIXED"
        action_now    = "Do not trade — signals are split between intraday and HTF"
    elif ctx == "COUNTER_TREND_BOUNCE" and lt_trend == "DOWNTREND" and bias == "BEARISH":
        primary_state = "PULLBACK OPPORTUNITY — SHORT SETUP BUILDING"
        action_now    = f"Wait — let price rally to {val.get('fair_value','fair value')} first, then look for rejection"
    elif ctx == "PULLBACK_IN_UPTREND" and bias == "BULLISH":
        primary_state = "PULLBACK OPPORTUNITY — LONG SETUP BUILDING"
        action_now    = "Wait for dip to support, then look for hold and long"
    elif adx < 20:
        primary_state = "RANGE / CHOP"
        action_now    = "Trade edges only — avoid mid-range entries"
    elif conf < 35:
        primary_state = "NO CLEAR SETUP"
        action_now    = "Stand aside — signals too weak to justify any entry"
    else:
        primary_state = "MIXED / UNCLEAR"
        action_now    = "Monitor — no clean setup present right now"

    # trade_plan: compact execution guide derived from context
    _fv = val.get("fair_value", "")
    _wm = val.get("weekly_mid", "")
    _fib382 = str(htf.get("fib_levels", {}).get("38.2", "")) if htf.get("fib_levels") else ""
    _fib500 = str(htf.get("fib_levels", {}).get("50.0", "")) if htf.get("fib_levels") else ""
    _inv_lvl = inv.get("invalidation", "") if inv else ""
    _near_lvl = liq.get("nearest_pool", "")

    if ctx == "COUNTER_TREND_BOUNCE" and lt_trend == "DOWNTREND":
        _aplus_long  = (f"Only if sweep holds AND GBP reclaims strength — tactical bounce only, not a swing long"
                        if sweep_down else
                        "No A+ long setup right now — dominant trend is bearish")
        _zone = f"{_fv}–{_fib382}" if _fv and _fib382 else _fv or "fair value zone"
        _aplus_short = f"Rally into {_zone}, then bearish rejection with lower high confirmation — swing short entry"
        _avoid       = "Shorting at current discount — you'd be selling the cheap end of the range"
        _best_expr   = f"Patient: let price come up to {_fv}, show rejection, then enter short"
        _exec_note   = ("Intraday tactical long allowed if sweep holds and price reclaims the level. "
                       "Do NOT treat it as swing bullish — higher-timeframe is still bearish.")
    elif ctx == "ESTABLISHED_DOWNTREND" and bias == "BEARISH":
        _aplus_long  = "No long setup — trend is established downtrend"
        _aplus_short = f"Sell rally into resistance near {_near_lvl or 'nearest level'} — trend trade"
        _avoid       = "Buying into trend — high risk, low probability"
        _best_expr   = "Short on rally with momentum confirmation — trend trade, wider stops"
        _exec_note   = "Trend on your side — this is the best environment for swing shorts"
    elif ctx in ("PULLBACK_IN_UPTREND",) and bias == "BULLISH":
        _aplus_long  = f"Buy dip if price holds above support near {_near_lvl or 'key level'} — pullback in uptrend"
        _aplus_short = "No short setup — trend is upward"
        _avoid       = "Chasing the rally after it's already moved — wait for the dip"
        _best_expr   = "Buy support hold with confirmation — pullback entry"
        _exec_note   = "Let price pull back and confirm support before entering"
    elif sweep_down and not conflict:
        _aplus_long  = f"Sweep held + price reclaimed {_near_lvl or 'swept level'} + GBP showing strength — buy"
        _aplus_short = "No short setup after a bullish sweep — wrong side"
        _avoid       = "Shorting immediately after a bullish sweep"
        _best_expr   = "Long from sweep level with tight stop below swept low"
        _exec_note   = "Intraday trade only — do not hold overnight without HTF confirmation"
    elif sweep_up and not conflict:
        _aplus_long  = "No long setup after a bearish sweep — wrong side"
        _aplus_short = f"Sweep held + rejection confirmed + AUD staying strong — short"
        _avoid       = "Buying immediately after a bearish sweep"
        _best_expr   = "Short from swept level with tight stop above swept high"
        _exec_note   = "Intraday trade only — do not hold overnight without HTF confirmation"
    else:
        _aplus_long  = "No clear A+ long condition right now"
        _aplus_short = "No clear A+ short condition right now"
        _avoid       = "Forcing a trade in mixed conditions"
        _best_expr   = best_expression
        _exec_note   = "Wait for a cleaner setup — patience is a position"

    trade_plan = {
        "aplus_long":  _aplus_long,
        "aplus_short": _aplus_short,
        "avoid":       _avoid,
        "best_expr":   _best_expr,
        "exec_note":   _exec_note,
    }

    return {
        "setup_type":      setup_type,
        "setup_note":      setup_note,
        "intraday":        intraday,
        "intraday_note":   intraday_note,
        "swing":           swing,
        "swing_note":      swing_note,
        "best_expression": best_expression,
        "flip_note":       flip_note,
        "wait_for":        wait_for,
        "quality":         quality,
        "quality_note":    quality_note,
        "event_risk":      event_risk,
        "event_name":      event_name,
        "primary_state":   primary_state,
        "action_now":      action_now,
        "trade_plan":      trade_plan,
        "triggers":        _build_triggers(ctx, lt_trend, sweep_down, sweep_up, conflict, bias, val, liq, htf, strength, inv, adx),
    }



def _build_triggers(ctx, lt_trend, sweep_down, sweep_up, conflict, bias,
                    val, liq, htf, strength, inv, adx):
    """Derive trigger checklist from existing context. No new data fetched."""
    _inv_lvl = inv.get("invalidation", "") if inv else ""
    _near    = liq.get("nearest_pool", "")
    _fv2     = val.get("fair_value", "")
    _fib382  = str(htf.get("fib_levels", {}).get("38.2", "")) if htf.get("fib_levels") else ""
    _zone    = f"{_fv2}–{_fib382}" if _fv2 and _fib382 else (_fv2 or "fair value zone")

    if ctx == "COUNTER_TREND_BOUNCE" and lt_trend == "DOWNTREND":
        t = {
            "setup": "SHORT — fade the bounce at value",
            "hard_triggers": [
                f"Price rallies into {_zone}",
                "Rejection wick or bearish engulf at that zone",
                "Lower high forms on 15m/1H chart",
                "Bearish close in direction of the rejection",
            ],
            "context_filters": [
                "GBP does NOT recover — AUD stays firm or stronger",
                "No high-impact news within 2h of entry",
                "Enough daily range remaining (50+ pips)",
                "London or NY session liquidity active",
            ],
            "minimum": [
                f"Price reaches {_fv2 or 'fair value area'}",
                "At least one bearish rejection candle",
                "No GBP surge in the hour before entry",
            ],
            "invalidates": [
                f"Price bursts through {_fib382} and holds above — bounce extending" if _fib382 else "Price holds above 38.2% — bounce extending",
                "GBP suddenly outperforms AUD — strength shifts",
                f"Daily close above {_inv_lvl}" if _inv_lvl else "Daily close above this week's high",
            ],
            "lower_quality": [
                "Less than 50 pips of daily range remaining",
                "High-impact news within 2h",
                "Tokyo session — thinner GBP liquidity",
            ],
        }
        if sweep_down:
            t["secondary"] = {
                "setup": "LONG — intraday only, if sweep holds",
                "hard_triggers": [
                    f"Swept level at {_near or 'swept low'} holds on retest",
                    "Bullish close above the swept level",
                    "Higher low forms on 15m/1H",
                ],
                "context_filters": [
                    "GBP weakness narrowing vs AUD",
                    "Active session — London or NY",
                ],
                "minimum": [
                    "Swept level holds on first retest",
                    "Bullish close above level",
                ],
                "invalidates": [
                    f"Close below {_near or 'swept low'} — sweep failed",
                    "AUD keeps accelerating vs GBP",
                ],
            }
        return t

    elif ctx == "ESTABLISHED_DOWNTREND" and bias == "BEARISH":
        return {
            "setup": "SHORT — trend continuation",
            "hard_triggers": [
                f"Price rallies to resistance near {_near or 'key level'}",
                "Rejection or bearish engulf at resistance",
                "Lower high forms on execution timeframe",
                "Bearish close after rejection",
            ],
            "context_filters": [
                "AUD outperforming or stable vs GBP",
                "No high-impact news within 2h",
                "ADX still elevated — trend momentum intact",
            ],
            "minimum": [
                "Resistance level reached",
                "At least one bearish rejection signal",
                "No immediate high-impact news",
            ],
            "invalidates": [
                "Price breaks resistance and holds above",
                f"Daily close above MA50 ({htf.get('ma50','MA50')})",
            ],
            "lower_quality": [
                "ADX falling — trend momentum fading",
                "Near major long-term support",
            ],
        }

    elif sweep_down and not conflict:
        return {
            "setup": "LONG — bullish sweep reversal",
            "hard_triggers": [
                f"Swept level at {_near or 'swept low'} holds on first retest",
                "Bullish close above the swept level",
                "Higher low forms on 15m/1H",
                "Momentum confirmation — bullish close above the retest candle",
            ],
            "context_filters": [
                "GBP strength improving or narrowing vs AUD",
                "Active session liquidity (London or NY)",
                "No high-impact news within 2h",
            ],
            "minimum": [
                "Swept level holds on first retest",
                "Bullish close above level",
            ],
            "invalidates": [
                f"Close below swept low — sweep failed, bias flips",
                "AUD keeps accelerating vs GBP",
            ],
            "lower_quality": [
                "Tokyo session — thin GBP liquidity",
                "High-impact event within 2h",
            ],
        }

    elif sweep_up and not conflict:
        return {
            "setup": "SHORT — bearish sweep reversal",
            "hard_triggers": [
                f"Swept level at {_near or 'swept high'} fails on first retest",
                "Bearish close below the swept level",
                "Lower high forms on 15m/1H",
                "Momentum confirmation — bearish close below the retest candle",
            ],
            "context_filters": [
                "AUD stable or strengthening vs GBP",
                "Active session liquidity",
                "No high-impact news within 2h",
            ],
            "minimum": [
                "Swept level rejected on retest",
                "Bearish close below level",
            ],
            "invalidates": [
                "Price reclaims and holds above swept high",
                "GBP suddenly surges — strength shift",
            ],
            "lower_quality": [
                "Low fuel remaining on the day",
                "High-impact event within 2h",
            ],
        }

    else:
        return {
            "setup": "No active trigger — waiting for setup to develop",
            "aplus": ["No A+ conditions met right now"],
            "minimum": ["Wait for clearer signal alignment"],
            "invalidates": ["N/A — no active setup"],
            "lower_quality": ["N/A"],
        }



_JOURNAL_FIELDS = [
    "run_id", "date", "time_utc", "session", "framework_version",
    "primary_state", "setup_type", "quality", "action",
    "bias", "conviction_score", "live_structural_conflict",
    "best_setup", "wait_for", "flip_if", "breaks_if",
    "intraday_view", "swing_view",
    "price", "htf_context", "regime", "macro_quadrant", "fib_pct", "higher_low_formed",
    "value_zone", "value_verdict", "value_aligned", "nearest_level",
    "sweep_up", "sweep_down", "sweep_confirmed",
    "cot_extreme", "cot_aud_pct", "strength_diff",
    "vix_level", "vix_change", "vix_regime",
    "atr_pips", "fuel_pct",
    "size_note", "invalidation_level", "high_impact_event_soon",
    "degraded", "degraded_components", "rate_stale_warning", "cot_data_date",
    # Outcomes — filled manually or via label_outcomes.py
    # WIN = 20+ pips in bias direction | LOSS = 20+ pips against | NEUTRAL = within 20 pips
    "next_day_close", "next_london_open", "outcome_label",
    "trigger_fired", "framework_was_right",
    "trade_taken", "trade_direction",
    "entry", "stop", "target", "exit", "pnl_r", "notes",
]


def _write_journal(report: Dict, inv: Dict, setup: Dict) -> None:
    """Append one row to run_journal.csv. Never raises — journal must not break the report."""
    try:
        import csv
        import uuid
        from pathlib import Path
        log = Path(__file__).parent / "run_journal.csv"

        liq  = report["layers"].get("liquidity", {})
        reg  = report["layers"].get("regime", {})
        crs  = report["layers"].get("cross_market", {})
        val  = report["layers"].get("value", {})
        ses  = report["layers"].get("session", {})
        htf  = report["layers"].get("htf", {})
        cot  = report["layers"].get("cot", {})
        str_ = report["layers"].get("currency_strength", {})
        rat  = report["layers"].get("rates", {})
        nws  = report["layers"].get("news", {})

        bias      = report.get("overall_bias", "")
        conv      = report.get("conviction_score", report.get("confidence", 0))
        conflict  = report.get("live_vs_structural_conflict", False)
        htf_ctx   = htf.get("context", "")

        if bias in ("BULLISH", "BEARISH") and conv >= 55 and not conflict:
            action = "LOOK FOR LONGS" if bias == "BULLISH" else "LOOK FOR SHORTS"
        elif conflict or conv < 40:
            action = "WAIT"
        else:
            action = "PLAN ONLY"

        high_event = ""
        for ev in nws.get("events", []):
            if ev.get("impact", "") in ("High", "Orange", "Red"):
                hrs = _hours_until(str(ev.get("time", "")))
                if 0 < hrs < 6:
                    high_event = f"{ev.get('event','')} in {hrs:.0f}h"
                    break

        sweep_up   = bool(liq.get("sweep_up"))
        sweep_down = bool(liq.get("sweep_down"))
        str_diff   = round((str_.get("GBP", 0) or 0) - (str_.get("AUD", 0) or 0), 1)
        sweep_conf = (
            ("YES-BULLISH" if str_diff >= 0 else "YES-CONFLICT") if sweep_down else
            ("YES-BEARISH" if str_diff <= 0 else "YES-CONFLICT") if sweep_up else "NO"
        )

        row = {
            "run_id":                   str(uuid.uuid4())[:8],
            "date":                     report.get("generated_at", "")[:10],
            "time_utc":                 report.get("generated_at", "")[11:16],
            "session":                  ses.get("session", ""),
            "framework_version":        "1.0",
            "primary_state":            setup.get("primary_state", ""),
            "setup_type":               setup.get("setup_type", ""),
            "quality":                  setup.get("quality", ""),
            "action":                   setup.get("action_now", action),
            "bias":                     bias,
            "conviction_score":         conv,
            "live_structural_conflict": "YES" if conflict else "NO",
            "best_setup":               setup.get("best_expression", ""),
            "wait_for":                 setup.get("wait_for", "")[:80],
            "flip_if":                  setup.get("flip_note", "")[:80],
            "breaks_if":                inv.get("invalidation", "") if inv else "",
            "intraday_view":            setup.get("intraday", ""),
            "swing_view":               setup.get("swing", ""),
            "price":                    liq.get("current_price", ""),
            "htf_context":              htf_ctx,
            "regime":                   reg.get("regime", ""),
            "macro_quadrant":           report["layers"].get("macro", {}).get("quadrant", ""),
            "fib_pct":                  htf.get("fib_pct", ""),
            "higher_low_formed":        "YES" if htf.get("higher_low_formed") else "NO",
            "value_zone":               val.get("verdict", ""),
            "value_verdict":            val.get("verdict_bias", ""),
            "value_aligned":            "YES" if val.get("verdict_bias") == (
                                            "BEARISH" if bias == "BEARISH" else "BULLISH"
                                        ) else "NO",
            "sweep_up":                 "YES" if sweep_up else "NO",
            "sweep_down":               "YES" if sweep_down else "NO",
            "sweep_confirmed":          sweep_conf,
            "cot_extreme":              "YES" if cot.get("aud_extreme") else "NO",
            "cot_aud_pct":              cot.get("aud_pct_long", ""),
            "strength_diff":            str_diff,
            "vix_level":                crs.get("vix_level", ""),
            "vix_change":               crs.get("vix_change", ""),
            "vix_regime":               crs.get("vix_regime", "NORMAL"),
            "atr_pips":                 reg.get("atr_pips", ""),
            "fuel_pct":                 reg.get("fuel_pct", ""),
            "invalidation_level":       inv.get("invalidation", "") if inv else "",
            "high_impact_event_soon":   high_event,
            "degraded":                 "YES" if report.get("degraded") else "NO",
            "degraded_components":      "; ".join(report.get("degraded_components", [])),
            "rate_stale_warning":       rat.get("stale_warning", ""),
            "cot_data_date":            cot.get("report_date", ""),
            "nearest_level":            liq.get("nearest_pool", ""),
            "size_note":                "",
            **{k: "" for k in (
                "next_day_close", "next_london_open", "outcome_label",
                "trigger_fired", "framework_was_right",
                "trade_taken", "trade_direction",
                "entry", "stop", "target", "exit", "pnl_r", "notes",
            )},
        }

        write_header = not log.exists()
        with open(log, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=_JOURNAL_FIELDS)
            if write_header:
                w.writeheader()
            w.writerow(row)
    except Exception:
        pass


def _print_quick_read(report: Dict, signals: list, bias: str, conf: int, inv: Dict = None) -> None:
    """10-line executive summary - read this first, details follow below."""
    W = 66

    # ── Build setup classification once — used by both journal and printer ───
    setup = _classify_setup(report, bias, conf, inv)
    report["setup"] = setup
    _write_journal(report, inv, setup)

    live_conflict = report.get("live_vs_structural_conflict", False)
    live_dom      = report.get("live_dominant",  "NEUTRAL")
    struct_dom    = report.get("struct_dominant", "NEUTRAL")

    # ── DECISION LAYER (Layer 1) — read this, act on this ───────────────────
    _, _tz = _get_local_offset()
    _gen_dt  = report.get("generated_at_12h", report.get("generated_at",""))
    _ses_hdr = report["layers"].get("session", {}).get("session_label", "")
    _tp = setup.get("trade_plan", {})

    _q_icons = {"HIGH": "✅", "MEDIUM": "⚡", "LOW": "⚠️ ", "DO NOT TRADE": "🚫"}
    _q_icon  = _q_icons.get(setup["quality"], "")
    _intra_icon = {"yes": "✅", "caution": "⚡", "no": "✗ ", "avoid": "🚫"}.get(setup["intraday"], "  ")
    _swing_icon = {"yes": "✅", "wait": "⏳", "no": "✗ "}.get(setup["swing"], "  ")

    # ── Header ───────────────────────────────────────────────────────────────
    print()
    print("=" * W)
    print(f"  GBP/AUD  |  {_gen_dt} {_tz}  |  {_ses_hdr}")
    print("=" * W)

    # ── Grade — use decision engine result (already computed in build_market_report) ──
    _dec = report.get("decision", {})
    report["grade"]    = _dec.get("grade", "C")
    report["risk_pct"] = _dec.get("risk_pct", 0.0)

    # ── LAYER 1: THE DECISION — one screen, everything you need ──────────────
    _ps          = setup.get("primary_state", setup["setup_type"]).upper()
    _inv_lvl     = inv.get("invalidation","") if inv else ""
    _inv_dir     = "above" if "SHORT" in setup.get("setup_type","").upper() else "below"
    _wait        = setup.get("wait_for","")
    _flip        = setup.get("flip_note","")
    _live_px     = report["layers"].get("liquidity",{}).get("current_price","")
    _val_zone    = report["layers"].get("value",{}).get("verdict","")
    _conf_str    = (
        "stay out" if conf < 25 else "weak" if conf < 45 else
        "moderate" if conf < 65 else "solid" if conf < 80 else "strong"
    )
    _bias_icon   = {"BEARISH": "▼", "BULLISH": "▲"}.get(bias, "→")
    _sig_aligned = sum(1 for s in signals if s.get("bias","") in (
        ("BEARISH",) if bias == "BEARISH" else ("BULLISH",)
    ))
    _sig_total   = len(signals) if signals else 7

    # Session timing note
    _sess_lbl    = report["layers"].get("session",{}).get("session_label","")
    _london_warn = ""
    try:
        import datetime as _dtt
        _utc_hr = _dtt.datetime.utcnow().hour
        _mins_to_london = ((7 - _utc_hr) % 24) * 60 - _dtt.datetime.utcnow().minute
        if 0 < _mins_to_london <= 90:
            _london_warn = f"  ⚡ London open in ~{_mins_to_london//60}h{_mins_to_london%60:02d}m"
        elif _mins_to_london == 0 or (0 <= _dtt.datetime.utcnow().hour - 7 < 4):
            _london_warn = "  🔴 London session ACTIVE"
    except Exception:
        pass

    print()
    print("-" * W)
    print(f"  {_ps}")
    print("-" * W)
    print(f"  Grade    : {_dec.get('grade_label', _dec.get('grade', ''))}  ({_dec.get('risk_pct', 0)}% risk)")
    if _dec.get("grade", "C") == "C" and _dec.get("grade_reason"):
        print(f"  ⛔ NO TRADE — {_dec['grade_reason']}")
    print(f"  Price    : {_live_px}  [{_val_zone}]")
    print(f"  Bias     : {_bias_icon} {bias}  —  {_sig_aligned}/{_sig_total} signals aligned")
    if _london_warn:
        print(_london_warn)
    print()
    if _inv_lvl:
        print(f"  Invalid  : daily close {_inv_dir} {_inv_lvl}")
    # Wrap flip text at word boundary
    _flip_max = W - 13
    if len(_flip) <= _flip_max:
        print(f"  Flip if  : {_flip}")
    else:
        _break = _flip[:_flip_max].rfind(" ")
        _break = _break if _break > 0 else _flip_max
        print(f"  Flip if  : {_flip[:_break]}")
        _flip_rest = _flip[_break:].strip()
        if _flip_rest:
            print(f"             {_flip_rest[:_flip_max]}")
    print()

    # ── TRADE PLAN + TRIGGERS — Layer 1 detail ──────────────────────────────
    if _tp:
        print("-" * W)
        print("  TRADE PLAN")
        print("-" * W)
        print(f"  A+ long   :  {_tp.get('aplus_long','')}")
        print(f"  A+ short  :  {_tp.get('aplus_short','')}")
        print(f"  Avoid     :  {_tp.get('avoid','')}")
        print(f"  Execute   :  {_tp.get('exec_note','')}")
        print()

    # ── TRIGGER CHECKLIST ────────────────────────────────────────────────────
    _trg = setup.get("triggers", {})
    if _trg and _trg.get("setup", "").lower() != "no active trigger":
        print("-" * W)
        print(f"  TRIGGER CHECKLIST  —  {_trg.get('setup','')}")
        print("-" * W)

        # ── HARD TRIGGERS — the actual price-action requirements ───────────────
        _hard = _trg.get("hard_triggers", _trg.get("aplus", []))
        if _hard:
            print("  HARD TRIGGERS  (price-action requirements):")
            for item in _hard:
                print(f"    ☐  {item}")
            print()

        # ── CONTEXT FILTERS — improve or reduce quality, not the trigger itself ─
        _ctx_f = _trg.get("context_filters", [])
        if _ctx_f:
            print("  CONTEXT FILTERS  (improve quality — not the trigger):")
            for item in _ctx_f:
                print(f"    ⚙  {item}")
            print()

        # ── Minimum to act ────────────────────────────────────────────────────
        _min = _trg.get("minimum", [])
        if _min:
            print("  MINIMUM TO ACT  (non-negotiable):")
            for item in _min:
                print(f"    ✓  {item}")
            print()

        # What invalidates the trigger
        _inv_trg = _trg.get("invalidates", [])
        if _inv_trg:
            print("  Trigger invalidated if:")
            for item in _inv_trg:
                print(f"    ✗  {item}")
            print()

        # Lower quality flags
        _lq = _trg.get("lower_quality", [])
        if _lq and _lq[0] != "N/A":
            print("  Lower quality if:")
            for item in _lq:
                print(f"    ⚠  {item}")
            print()

        # Secondary setup (e.g. intraday long inside a bearish swing setup)
        _sec = _trg.get("secondary")
        if _sec:
            print(f"  ─ ─ ─")
            print(f"  SECONDARY — {_sec.get('setup','')}")
            _sec_hard = _sec.get("hard_triggers", _sec.get("aplus", []))
            if _sec_hard:
                print("  Hard triggers:")
                for item in _sec_hard:
                    print(f"    ☐  {item}")
            _sec_ctx = _sec.get("context_filters", [])
            if _sec_ctx:
                print("  Context filters:")
                for item in _sec_ctx:
                    print(f"    ⚙  {item}")
            if _sec.get("invalidates"):
                print("  Invalidated if:")
                for item in _sec.get("invalidates", []):
                    print(f"    ✗  {item}")
            print()
    elif _trg:
        print("-" * W)
        print("  TRIGGER CHECKLIST")
        print("-" * W)
        print(f"  {_trg.get('aplus', ['No active trigger — monitoring only'])[0]}")
        print()

    # ── 6. Current conditions snapshot ───────────────────────────────────────
    print("-" * W)
    print("  MARKET CONTEXT")
    print("-" * W)

    _sn_ses      = report["layers"].get("session", {})
    _sn_liq      = report["layers"].get("liquidity", {})
    _sn_reg      = report["layers"].get("regime", {})
    _sn_val      = report["layers"].get("value", {})
    _sn_str      = report["layers"].get("currency_strength", {})
    _sn_cot      = report["layers"].get("cot", {})
    _sn_cross    = report["layers"].get("cross_market", {})
    _sn_news     = report["layers"].get("news", {})
    _sn_intraday = report["layers"].get("intraday", {})

    # Day of week + session
    _dow_label = _sn_ses.get("day_of_week", "")
    _sn_alert  = _sn_ses.get("alert", "")
    _sess_line = f"{_sn_ses.get('session_label','')}  —  {_sn_ses.get('liquidity','')}"
    print(f"  Session  : {_sess_line}")
    if _dow_label:
        _dow_char = _sn_ses.get('dow_character','')
        _dow_disp = _dow_char[:W - 18] if len(_dow_char) > (W - 18) else _dow_char
        print(f"  Day      : {_dow_label}  —  {_dow_disp}")
    if _sn_alert:
        print(f"  ⚡ {_sn_alert}")

    # Price + range + nearest level
    if not _sn_liq.get("error"):
        _sn_price  = _sn_liq.get("current_price", "")
        _sn_near   = _sn_liq.get("nearest_pool")
        _sn_pdir   = _sn_liq.get("pool_direction", "")
        _sn_swp_dn = _sn_liq.get("sweep_down", False)
        _sn_swp_up = _sn_liq.get("sweep_up",   False)
        _sn_r_used = _sn_reg.get("range_used")
        _sn_r_rem  = _sn_reg.get("range_remaining")
        _sn_atr    = _sn_reg.get("atr_pips", 0) or 0

        _sn_psrc = _sn_liq.get("price_source", "")
        _sn_psrc_tag = "  [live]" if "OANDA" in _sn_psrc else "  [last close]"
        print(f"  Price    : {_sn_price}{_sn_psrc_tag}")
        if _sn_r_used is not None:
            print(f"  Range    : {_sn_r_used} of {_sn_atr:.0f} pips used  —  {round(_sn_r_rem)} pips left")
        if _sn_near:
            print(f"  Level    : {_sn_near} ({_sn_pdir})  —  watch for sweep + reversal")

        # Value zone
        if _sn_val and not _sn_val.get("error"):
            _sn_verd    = _sn_val.get("verdict", "")
            _sn_vdiff   = _sn_val.get("fv_diff_pips", 0) or 0
            _sn_fv      = _sn_val.get("fair_value", "")
            _sn_wkpct   = _sn_val.get("wk_pct", 50) or 50
            _sn_fv_zone = _sn_val.get("fv_zone", "")
            _sn_is_prem = "PREMIUM" in _sn_verd
            _sn_fv_prem = _sn_fv_zone == "PREMIUM"
            if _sn_is_prem == _sn_fv_prem or abs(_sn_vdiff) <= 20:
                _sn_vabs = abs(_sn_vdiff)
                _sn_vdir = "above" if _sn_vdiff > 0 else "below"
                if _sn_vabs <= 20:
                    print(f"  Value    : {_sn_verd}  (near fair value {_sn_fv})")
                else:
                    print(f"  Value    : {_sn_verd}  ({_sn_vabs} pips {_sn_vdir} fair value {_sn_fv})")
            else:
                print(f"  Value    : {_sn_verd}  ({_sn_wkpct:.0f}% of weekly range)")

        # Sweep signal with confirmation
        _sn_sdiff = (_sn_str.get("GBP", 0) or 0) - (_sn_str.get("AUD", 0) or 0)
        if _sn_swp_dn:
            _sn_conf_lbl = "✅ confirmed by GBP strength" if _sn_sdiff >= 0 else "⚠️  conflicts with AUD strength"
            print(f"  Sweep    : Low swept  {_sn_conf_lbl}  —  potential bounce")
        elif _sn_swp_up:
            _sn_conf_lbl = "✅ confirmed by AUD strength" if _sn_sdiff <= 0 else "⚠️  conflicts with GBP strength"
            print(f"  Sweep    : High swept  {_sn_conf_lbl}  —  potential drop")

    # Risk + event + macro
    if _sn_cot.get("aud_extreme"):
        _sn_pct = _sn_cot.get("aud_pct_long", 89)
        if bias == "BEARISH":
            print(f"  Risk     : AUD {_sn_pct:.0f}% crowded long — short squeeze risk if AUD rallies")
        else:
            print(f"  Risk     : AUD {_sn_pct:.0f}% crowded long — AUD reversal risk elevated")
    elif _sn_cot.get("gbp_extreme"):
        print(f"  Risk     : GBP positioning extreme — GBP reversal risk")

    _sn_upcoming = [e for e in _sn_news.get("events", []) if e.get("status") == "upcoming"]
    if _sn_upcoming:
        _sn_ev   = _sn_upcoming[0]
        _sn_itag = "🔴" if _sn_ev.get("impact") == "High" else "🟡" if _sn_ev.get("impact") == "Medium" else "🟢"
        _sn_eloc = _fmt_pst(str(_sn_ev["time"]), style="short")
        _sn_ehrs = _hours_until(str(_sn_ev["time"]))
        _sn_estr = f"{_sn_ehrs:.0f}h" if _sn_ehrs > 0 else "NOW"
        print(f"  Event    : {_sn_itag} {_sn_ev['event']} ({_sn_ev.get('currency','')})  {_sn_eloc}  ({_sn_estr})")

    _sn_vix_regime = _sn_cross.get("vix_regime", "NORMAL")
    if _sn_vix_regime == "PANIC_FADING":
        print(f"  Macro    : 🔄 VIX spike fading — relief bounce more likely than continuation down")
    elif _sn_vix_regime == "PANIC_BUILDING":
        print(f"  Macro    : ⚡ VIX panic building — AUD likely stays under pressure")

    # ── Intraday session structure ────────────────────────────────────────────
    if _sn_intraday and not _sn_intraday.get("error"):
        _id_high   = _sn_intraday.get("asian_high")
        _id_low    = _sn_intraday.get("asian_low")
        _id_pips   = _sn_intraday.get("asian_range_pips")
        _id_bias   = _sn_intraday.get("intraday_bias", "WAIT")
        _id_ft     = _sn_intraday.get("fakeout_detected", False)
        _id_ftype  = _sn_intraday.get("fakeout_type", "")
        _id_fnote  = _sn_intraday.get("fakeout_note", "")
        _id_entry  = _sn_intraday.get("entry_note", "")
        _id_window = _sn_intraday.get("optimal_window", "")
        _id_warn   = _sn_intraday.get("warning", "")
        _id_pos    = _sn_intraday.get("price_position", "")

        print()
        print("-" * W)
        if _id_ft:
            _ft_icon = "🔥" if _id_ftype == "BULLISH" else "🔥"
            print(f"  {_ft_icon} INTRADAY FAKEOUT DETECTED — {_id_ftype}")
        else:
            print(f"  INTRADAY SESSION STRUCTURE")
        print("-" * W)

        if _id_high and _id_low:
            print(f"  Asian range : {_id_low:.4f} – {_id_high:.4f}  ({_id_pips} pips)")
            pos_label = {
                "ABOVE_RANGE":  f"ABOVE Asian high ({_id_high:.4f})",
                "BELOW_RANGE":  f"BELOW Asian low ({_id_low:.4f})",
                "INSIDE_RANGE": f"Inside Asian range",
            }.get(_id_pos, _id_pos)
            print(f"  Position    : {pos_label}")

        if _id_fnote:
            print()
            import textwrap as _tw
            for _ln in _tw.wrap(_id_fnote, width=W - 4, initial_indent="  ", subsequent_indent="  "):
                print(_ln)

        print()
        for _ln in _tw.wrap(_id_entry, width=W - 4, initial_indent="  Entry : ", subsequent_indent="          "):
            print(_ln)

        if _id_window:
            print(f"  Window  : {_id_window}")

        if _id_warn:
            print()
            print(f"  ⚠  {_id_warn}")

    print()

    # ── SINCE LAST RUN — compare vs previous run ──────────────────────────────
    try:
        import json as _json
        from pathlib import Path as _Path2
        _lr_path = _Path2(__file__).parent / "last_run.json"
        if _lr_path.exists():
            _lr = _json.loads(_lr_path.read_text())
            _lr_time  = _lr.get("time_utc", "?")
            _lr_time_pt_saved = _lr.get("time_pt", "")
            _lr_price = _lr.get("price", 0) or 0
            _lr_bias  = _lr.get("bias", "?")
            _lr_qual  = _lr.get("quality", "?")
            _lr_action= _lr.get("action", "?")
            _lr_conv  = _lr.get("conviction_score", 0) or 0
            _lr_state = _lr.get("primary_state", "?")

            _cur_price = float(_sn_liq.get("current_price", 0) or 0)
            _cur_bias  = report.get("overall_bias", "?")
            _cur_qual  = setup.get("quality", "?")
            _cur_conv  = conf
            _cur_action = setup.get("action_now", "?")

            _price_diff = round((_cur_price - _lr_price) * 10000) if _lr_price else 0
            _price_dir  = "▲" if _price_diff > 0 else "▼" if _price_diff < 0 else "→"

            _changes = []
            if _lr_bias != _cur_bias:
                _changes.append(f"bias: {_lr_bias} → {_cur_bias}")
            if _lr_qual != _cur_qual:
                _changes.append(f"quality: {_lr_qual} → {_cur_qual}")
            if abs(_cur_conv - _lr_conv) >= 5:
                _conv_dir = "↑" if _cur_conv > _lr_conv else "↓"
                _changes.append(f"alignment: {_lr_conv} {_conv_dir} {_cur_conv}")
            # Only flag action change if meaningfully different
            _lr_action_key = _lr_action[:30].lower().strip()
            _cur_action_key = _cur_action[:30].lower().strip()
            if _lr_action_key != _cur_action_key:
                _changes.append(f"action changed")

            print("-" * W)
            # Use saved PT time directly — no conversion needed
            _lr_time_pt = _lr_time_pt_saved if _lr_time_pt_saved else f"{_lr_time} UTC"
            print(f"  SINCE LAST RUN  (previous run: {_lr_time_pt})")
            print("-" * W)
            print(f"  Price  : {_lr_price} → {_cur_price}  ({_price_dir} {abs(_price_diff)} pips)")
            _state_disp = _lr_state[:W - 12] if len(_lr_state) > (W - 12) else _lr_state
            print(f"  State  : {_state_disp}")
            _change_str = ' | '.join(_changes) if _changes else "No significant change since last run"
            _change_disp = _change_str[:W - 12] if len(_change_str) > (W - 12) else _change_str
            print(f"  Change : {_change_disp}")
            print()
    except Exception:
        pass  # Never break the report over last-run comparison



def _build_invalidation(htf: Dict, liquidity: Dict, bias: str) -> Dict:
    """
    Build the thesis invalidation block.
    Returns a dict with:
      - thesis      : plain-English description of the trade idea
      - invalidation: the price level that proves the idea wrong
      - invalidation_note: why that level matters
      - warning_level: an earlier warning price
      - warning_note: what the warning means
      - action_on_break: what to do if invalidation is hit
    """
    context     = htf.get("context", "RANGING")
    fib_levels  = htf.get("fib_levels", {})
    pwh         = liquidity.get("pwh")   # this week's high
    pwl         = liquidity.get("pwl")   # this week's low
    ma50        = htf.get("ma50")
    price       = htf.get("current_price") or liquidity.get("current_price", 0)
    fib_pct     = htf.get("fib_pct", 0)

    # Find next Fibonacci level ABOVE current price for the warning
    # Must be at least 80 pips above current price to be a meaningful warning
    # (anything closer is already the immediate resistance, not a warning)
    next_fib_above = None
    for lvl in ["38.2", "50.0", "61.8", "78.6"]:
        fib_price = fib_levels.get(lvl)
        if fib_price and fib_price > price + 0.0080:  # 80 pips minimum
            next_fib_above = (lvl, fib_price)
            break

    # Find next Fibonacci level BELOW current price (for pullback warning)
    next_fib_below = None
    for lvl in ["61.8", "50.0", "38.2", "23.6"]:
        fib_price = fib_levels.get(lvl)
        if fib_price and fib_price < price - 0.0010:
            next_fib_below = (lvl, fib_price)
            break

    if context == "COUNTER_TREND_BOUNCE" and bias in ("BEARISH", "NEUTRAL"):
        inv_level = pwh
        inv_note  = (
            f"This week's high ({pwh}) is the top of the current bounce. "
            f"A daily candle closing ABOVE this level means the bounce is "
            f"not exhausted — the dominant downtrend thesis is wrong for now."
        )
        warn_level = next_fib_above[1] if next_fib_above else None
        warn_note  = (
            f"If price reaches the {next_fib_above[0]}% Fibonacci level "
            f"({next_fib_above[1]}), the bounce is deeper than expected. "
            f"Tighten stops or reduce short exposure."
        ) if next_fib_above else "Watch for price approaching the weekly high."
        return {
            "thesis": "SHORT — fading a counter-trend bounce in a 5-month downtrend",
            "invalidation": inv_level,
            "invalidation_note": inv_note,
            "warning_level": warn_level,
            "warning_note": warn_note,
            "action_on_break": "Exit all shorts. Bounce is stronger than expected. Re-assess next session.",
        }

    elif context == "PULLBACK_IN_UPTREND" and bias in ("BULLISH", "NEUTRAL"):
        inv_level = pwl
        inv_note  = (
            f"This week's low ({pwl}) is the floor of the current pullback. "
            f"A daily candle closing BELOW this level means the pullback "
            f"is deeper than a normal correction — the uptrend may be reversing."
        )
        warn_level = next_fib_below[1] if next_fib_below else None
        warn_note  = (
            f"If price falls to the {next_fib_below[0]}% Fibonacci level "
            f"({next_fib_below[1]}), the pullback is deep. "
            f"Reduce long exposure until price stabilises."
        ) if next_fib_below else "Watch for price breaking below the weekly low."
        return {
            "thesis": "LONG — buying a pullback in a 5-month uptrend",
            "invalidation": inv_level,
            "invalidation_note": inv_note,
            "warning_level": warn_level,
            "warning_note": warn_note,
            "action_on_break": "Exit all longs. Pullback is too deep. Wait for new structure.",
        }

    elif context == "ESTABLISHED_DOWNTREND" and bias == "BEARISH":
        inv_level = ma50
        inv_note  = (
            f"The 50-day average ({ma50}) is key resistance in a downtrend. "
            f"A daily close ABOVE it means price is recovering through "
            f"the trend's central structure — the downtrend is breaking."
        )
        warn_level = pwh
        warn_note  = f"A rally to this week's high ({pwh}) is an early warning."
        return {
            "thesis": "SHORT — trading with the established 5-month downtrend",
            "invalidation": inv_level,
            "invalidation_note": inv_note,
            "warning_level": warn_level,
            "warning_note": warn_note,
            "action_on_break": "Exit shorts. Downtrend structure is breaking. Wait for confirmation.",
        }

    elif context == "ESTABLISHED_UPTREND" and bias == "BULLISH":
        inv_level = ma50
        inv_note  = (
            f"The 50-day average ({ma50}) is key support in an uptrend. "
            f"A daily close BELOW it means price is breaking through "
            f"the trend's central structure — the uptrend is in trouble."
        )
        warn_level = pwl
        warn_note  = f"A drop to this week's low ({pwl}) is an early warning."
        return {
            "thesis": "LONG — trading with the established 5-month uptrend",
            "invalidation": inv_level,
            "invalidation_note": inv_note,
            "warning_level": warn_level,
            "warning_note": warn_note,
            "action_on_break": "Exit longs. Uptrend structure is breaking. Wait for confirmation.",
        }

    elif context in ("ESTABLISHED_DOWNTREND", "COUNTER_TREND_BOUNCE") and bias == "BULLISH":
        # Live vs structural conflict: structural is bearish but today's session is running bullish.
        # Show the level that ends the intraday bullish case — not a trade thesis, just context.
        inv_level = pwl
        inv_note  = (
            f"Today's move is bullish but the 5-month trend is DOWN. "
            f"A daily close below this week's low ({pwl}) confirms the downtrend "
            f"has resumed — the intraday rally was a counter-trend bounce."
        )
        warn_level = ma50
        warn_note  = (
            f"MA50 ({ma50}) is the key structural dividing line. "
            f"Price holding above it keeps the intraday bullish case alive. "
            f"A daily close below MA50 favours the bears."
        )
        return {
            "thesis": "CONFLICTED — intraday BULLISH, structural BEARISH. No trade.",
            "invalidation": inv_level,
            "invalidation_note": inv_note,
            "warning_level": warn_level,
            "warning_note": warn_note,
            "action_on_break": "Structural downtrend has reasserted. Do not chase longs.",
        }

    elif context in ("ESTABLISHED_UPTREND", "PULLBACK_IN_UPTREND") and bias == "BEARISH":
        # Live vs structural conflict: structural is bullish but today's session is bearish.
        inv_level = pwh
        inv_note  = (
            f"Today's move is bearish but the 5-month trend is UP. "
            f"A daily close above this week's high ({pwh}) confirms the uptrend "
            f"has resumed — the intraday sell-off was a counter-trend pullback."
        )
        warn_level = ma50
        warn_note  = (
            f"MA50 ({ma50}) is key support in an uptrend. "
            f"Price holding above it keeps the intraday bearish case contained. "
            f"A daily close below MA50 would be the first real structural warning."
        )
        return {
            "thesis": "CONFLICTED — intraday BEARISH, structural BULLISH. No trade.",
            "invalidation": inv_level,
            "invalidation_note": inv_note,
            "warning_level": warn_level,
            "warning_note": warn_note,
            "action_on_break": "Uptrend has resumed. Do not chase shorts.",
        }

    else:
        return {
            "thesis": "No clear directional bias — no trade thesis active",
            "invalidation": None,
            "invalidation_note": "No active thesis to invalidate.",
            "warning_level": None,
            "warning_note": "Wait for bias to develop before committing.",
            "action_on_break": "N/A",
        }


def _print_executive_brief(report: Dict, W: int = 66) -> None:
    """
    Five-question narrative brief — the primary output.
    Answers the questions a professional trader asks before any trade:
      1. Macro bias
      2. Market condition
      3. Price condition
      4. Price structure / market showing its hand
      5. Trade decision
    """
    import textwrap

    def _para(text: str):
        """Print a wrapped paragraph."""
        for line in textwrap.wrap(text, width=W - 4):
            print(f"  {line}")

    rates    = report["layers"].get("rates",    {})
    cross    = report["layers"].get("cross",    {})
    htf      = report["layers"].get("htf",      {})
    liq      = report["layers"].get("liquidity",{})
    val      = report["layers"].get("value",    {})
    reg      = report["layers"].get("regime",   {})
    sess     = report["layers"].get("session",  {})
    intra    = report["layers"].get("intraday", {})
    dec      = report.get("decision", {})
    bias     = report.get("overall_bias", "NEUTRAL")
    conf     = report.get("conviction_score", 50)

    # ── 1. MACRO BIAS ─────────────────────────────────────────────────────────
    print(f"\n  {'─'*W}")
    print(f"  1. MACRO BIAS")
    print(f"  {'─'*W}")

    boe_rate    = rates.get("boe", {}).get("current_rate", "?")
    rba_rate    = rates.get("rba", {}).get("current_rate", "?")
    boe_stance  = rates.get("boe", {}).get("stance", "neutral").lower()
    rba_stance  = rates.get("rba", {}).get("stance", "neutral").lower()
    diff        = rates.get("differential", 0) or 0
    rate_bias   = rates.get("overall_bias", "NEUTRAL")
    macro_quad  = dec.get("macro_quadrant", "")
    macro_mod   = dec.get("macro_modifier", 0)

    boe_desc = {"dovish": "cutting cycle", "hawkish": "hiking cycle", "neutral": "on hold"}.get(boe_stance, boe_stance)
    rba_desc = {"dovish": "cutting cycle", "hawkish": "hiking cycle", "neutral": "on hold"}.get(rba_stance, rba_stance)

    macro_regime_text = {
        "REFLATION":   "The macro regime is REFLATION — growth rising, inflation picking up. Risk-on conditions favour AUD as a commodity currency.",
        "GOLDILOCKS":  "The macro regime is GOLDILOCKS — strong growth, low inflation. Risk assets outperform. AUD benefits from the positive sentiment.",
        "STAGFLATION": "The macro regime is STAGFLATION — growth slowing while inflation stays elevated. GBP tends to hold up better than AUD in this environment.",
        "DEFLATION":   "The macro regime is DEFLATION — both growth and inflation falling. Risk-off. AUD sells off faster than GBP in these conditions, which is a GBP/AUD tailwind.",
        "TRANSITIONAL":"The macro regime is TRANSITIONAL — mixed signals, no clear dominant theme. Macro is not adding conviction either way.",
    }.get(macro_quad, "")

    rate_text = (
        f"The BoE is in a {boe_desc} ({boe_rate}%) while the RBA is {rba_desc} ({rba_rate}%). "
        f"The rate gap of {diff:+.2f}% currently favours GBP on yield, "
        f"but with the BoE {boe_stance} that advantage is {'narrowing' if boe_stance == 'dovish' else 'holding'}. "
        f"On rates alone, the signal is {rate_bias.lower()} for GBP/AUD."
    )
    _para(rate_text)
    if macro_regime_text:
        print()
        _para(macro_regime_text)

    # ── 2. MARKET CONDITION ───────────────────────────────────────────────────
    print(f"\n  {'─'*W}")
    print(f"  2. MARKET CONDITION")
    print(f"  {'─'*W}")

    vix      = cross.get("vix_level", 0) or 0
    vix_chg  = cross.get("vix_change", 0) or 0
    sp       = cross.get("sp500_change", 0) or 0
    dxy      = cross.get("dxy_change", 0) or 0
    risk_reg = cross.get("risk_regime", "NEUTRAL")
    cx_bias  = cross.get("overall_bias", "NEUTRAL")

    if vix < 15:
        vix_text = f"VIX at {vix:.1f} — market is calm and complacent."
    elif vix < 20:
        vix_text = f"VIX at {vix:.1f} — relatively calm conditions."
    elif vix < 25:
        vix_text = f"VIX at {vix:.1f} — elevated volatility, some caution in the market."
    else:
        vix_text = f"VIX at {vix:.1f} — fear elevated. Risk-off conditions."

    dxy_text = (
        f"The dollar is {'weakening' if dxy < 0 else 'strengthening'} ({dxy:+.2f}%), "
        f"which {'supports' if dxy < 0 else 'pressures'} GBP/AUD on the cross."
    )

    risk_text = {
        "RISK_ON":  "Risk appetite is ON — money is flowing into higher-beta currencies. AUD typically benefits from this, which is a headwind for GBP/AUD longs.",
        "RISK_OFF": "Risk appetite is OFF — money rotating into safe havens. GBP holds up better than AUD in this environment.",
        "NEUTRAL":  "Risk sentiment is neutral — no strong directional push from the macro backdrop today.",
    }.get(risk_reg, "Risk sentiment is mixed.")

    _para(f"{vix_text} {dxy_text}")
    print()
    _para(risk_text)

    # ── 3. PRICE CONDITION ────────────────────────────────────────────────────
    print(f"\n  {'─'*W}")
    print(f"  3. PRICE CONDITION")
    print(f"  {'─'*W}")

    trend_lt    = htf.get("lt_trend", "")       # long-term  (~5-month / 20wk)
    trend_st    = htf.get("st_trend", "")       # short-term (~4-week)
    trend_day   = htf.get("daily_trend", "")
    adx         = reg.get("adx", 0) or 0
    atr         = reg.get("atr_pips", 0) or 0   # regime layer holds ATR
    fuel        = reg.get("fuel_pct", 50) or 50  # regime layer holds fuel
    price       = liq.get("current_price", 0) or 0
    fv          = val.get("fair_value", 0) or 0
    fv_diff     = val.get("fv_diff_pips", 0) or 0
    val_verdict = val.get("verdict", "")

    trend_dir     = trend_lt or trend_st or trend_day or ""
    # Aligned = both long and short-term agree on direction
    trend_aligned = (
        ("DOWN" in str(trend_lt).upper() and "DOWN" in str(trend_st).upper()) or
        ("UP"   in str(trend_lt).upper() and "UP"   in str(trend_st).upper())
    )

    if trend_aligned and "DOWN" in str(trend_dir).upper():
        condition_text = (
            f"GBP/AUD is in an established downtrend across the 5-month and 4-week timeframes. "
            f"This is a trending environment — I'm looking for continuation on pullbacks, not reversals. "
            f"The trend is the edge."
        )
    elif trend_aligned and "UP" in str(trend_dir).upper():
        condition_text = (
            f"GBP/AUD is in an established uptrend across both timeframes. "
            f"Trending environment — looking for longs on dips, not chasing tops."
        )
    else:
        condition_text = (
            f"The trend is mixed or transitioning — 5-month and short-term timeframes are not aligned. "
            f"This is a more cautious environment. I need the range extremes to be clear before committing."
        )

    adx_text = (
        f"ADX at {adx:.1f} — " + (
            "strong directional momentum confirmed." if adx > 25 else
            "trend building but not yet confirmed strong. Treat like a developing trend, not a full trending market." if adx > 20 else
            "no real trend momentum — this is a range or choppy market. Fade extremes, not breakouts."
        )
    )

    fv_text = (
        f"Price ({price}) is {'above' if fv_diff > 0 else 'below'} fair value ({fv}) by {abs(fv_diff):.0f} pips — "
        f"trading at a {'premium' if fv_diff > 0 else 'discount'}. "
        + (
            "Shorting a discount means entering where buyers are — I want to see a rally toward fair value first." if fv_diff < -15 and bias == "BEARISH" else
            "Buying a premium means entering where sellers are — I want to see a pullback toward fair value first." if fv_diff > 15 and bias == "BULLISH" else
            "Price location aligns with the trade direction — no value conflict."
        )
    )

    fuel_text = (
        f"The daily range is {atr:.0f} pips average and {fuel:.0f}% has already been used today. "
        + ("Plenty of range left — room to run." if fuel < 50 else
           "Range is running low — limited move left today. Better entries tomorrow or at session open." if fuel > 70 else
           "Moderate range remaining.")
    )

    _para(condition_text)
    print()
    _para(adx_text)
    print()
    _para(fv_text)
    print()
    _para(fuel_text)

    # ── 4. PRICE STRUCTURE ────────────────────────────────────────────────────
    print(f"\n  {'─'*W}")
    print(f"  4. PRICE STRUCTURE")
    print(f"  {'─'*W}")

    asian_hi    = intra.get("asian_high", 0) or 0
    asian_lo    = intra.get("asian_low", 0) or 0
    asian_pips  = intra.get("asian_range_pips", 0) or 0
    pos_in_rng  = intra.get("price_position", "")
    fakeout     = intra.get("fakeout_detected", False)
    fakeout_typ = intra.get("fakeout_type", "")
    sweep_up    = liq.get("sweep_up", False)
    sweep_down  = liq.get("sweep_down", False)
    nearest_lvl = liq.get("nearest_pool", 0) or 0
    sess_label  = sess.get("session_label", "")

    if asian_hi and asian_lo:
        range_text = (
            f"The Asian range is set: {asian_lo} to {asian_hi} ({asian_pips} pips). "
        )
        if "INSIDE" in str(pos_in_rng).upper():
            range_text += (
                "Price is still inside that range — no sweep yet, no clear institutional footprint. "
                "I'm watching the extremes. The first move that takes a level and reverses is the signal."
            )
        elif "ABOVE" in str(pos_in_rng).upper():
            range_text += "Price has broken above the Asian high — watch for acceptance or rejection at this level."
        elif "BELOW" in str(pos_in_rng).upper():
            range_text += "Price has broken below the Asian low — watch for acceptance or rejection at this level."
        _para(range_text)
    print()

    if fakeout and fakeout_typ not in ("NONE", "INSIDE", ""):
        sweep_text = (
            f"The market has shown its hand — a {fakeout_typ.lower().replace('_',' ')} was detected. "
            f"That's an institutional stop hunt: price took liquidity then reversed. "
            f"This is the clearest signal the framework generates. The reversal after the sweep is the trade."
        )
    elif sweep_up and not sweep_down:
        sweep_text = (
            f"A high was swept and price rejected. Institutional sellers used the sweep to fill short orders. "
            f"The sweep + reversal is the bearish signal — this confirms supply above."
        )
    elif sweep_down and not sweep_up:
        sweep_text = (
            f"A low was swept and price recovered. Institutional buyers used the sweep to fill long orders. "
            f"The sweep + reversal is the bullish signal — this confirms demand below."
        )
    else:
        nearest_text = f"nearest level is {nearest_lvl}" if nearest_lvl else "key levels are defined"
        sweep_text = (
            f"No sweep yet today — the market hasn't shown its hand. "
            f"The {nearest_text}. "
            f"If price takes that level and immediately reverses, that's the institutional footprint I'm waiting for."
        )
    _para(sweep_text)

    print()
    sess_timing = {
        "Tokyo":     "Tokyo is active — AUD has some liquidity but GBP is thin. Low-conviction session for GBP/AUD.",
        "London":    "London is the prime session for GBP/AUD. Biggest moves happen here. Full participation.",
        "New York":  "New York is open — USD-driven volatility can push GBP/AUD. Watch USD pairs for context.",
        "London/NY": "London and New York are both open — the busiest window of the day. Best conditions for GBP/AUD entries.",
        "Sydney":    "Sydney session — early AUD activity, GBP barely moving. Thin liquidity, wide spreads. Wait.",
        "Off-hours": "Off-hours — most banks closed. Thin market, unpredictable moves. I'm not trading now.",
    }.get(sess_label, f"Current session: {sess_label}.")
    _para(sess_timing)

    # ── 5. TRADE DECISION ─────────────────────────────────────────────────────
    print(f"\n  {'─'*W}")
    print(f"  5. TRADE DECISION")
    print(f"  {'─'*W}")

    grade       = dec.get("grade", "C")
    direction   = dec.get("direction", "NO TRADE")
    entry_cond  = dec.get("entry_condition", "")
    cap_reason  = dec.get("grade_cap_reason", "")
    come_back   = dec.get("come_back_at", "")
    inv_note    = ""
    for iv in dec.get("invalidation", []):
        inv_note = iv
        break

    grade_plain = {
        "A+": "A+ — everything aligned. Full size.",
        "A":  "A — strong setup with minor caveats. Standard size.",
        "B+": "B+ — valid setup, one or two things not perfect. Slightly reduced size.",
        "B":  "B — direction is there but meaningful conflicts exist. Half size, actively managed.",
        "C":  "C — do not trade.",
    }.get(grade, grade)

    dec_conv = dec.get("conviction", conf)   # Decision Engine conviction — canonical

    if grade == "C":
        decision_text = (
            f"Grade C — standing aside. "
            f"{cap_reason + '. ' if cap_reason else ''}"
            f"Conviction is {dec_conv}/100 — signals are not aligned enough to justify risk. "
            f"{'Come back at ' + come_back + '.' if come_back else 'Wait for conditions to improve.'}"
        )
    else:
        decision_text = (
            f"Grade {grade_plain} "
            f"Conviction {dec_conv}/100. "
            f"Direction: {direction}. "
            f"{entry_cond + ' ' if entry_cond else ''}"
            f"{'Thesis is wrong if: ' + inv_note + '.' if inv_note else ''}"
        )

    _para(decision_text)

    if dec.get("is_counter"):
        print()
        _para("This is a counter-trend trade — trading against the dominant trend. Higher risk, reduced size, tighter management.")

    print(f"\n  {'═'*W}\n")



def print_report(report: Dict) -> None:
    import textwrap as _tw
    W = 66

    def _sec(title: str):
        print()
        print("-" * W)
        print(f"  {title}")
        print("-" * W)

    def _wrap(text: str, indent: str = "  ") -> None:
        for line in _tw.wrap(text, width=W - 2):
            print(f"{indent}{line}")

    # ── Data extraction ──────────────────────────────────────────────────────
    _, _tz_lbl = _get_local_offset()
    _gen_12h   = report.get("generated_at_12h", report["generated_at"])
    bias       = report["overall_bias"]
    conf       = report.get("conviction_score", report.get("confidence", 50))
    signals    = report.get("signal_summary", [])

    sess     = report["layers"].get("session",           {})
    htf      = report["layers"].get("htf",               {})
    liq      = report["layers"].get("liquidity",         {})
    reg      = report["layers"].get("regime",            {})
    val      = report["layers"].get("value",             {})
    cot      = report["layers"].get("cot",               {})
    cross    = report["layers"].get("cross_market",      {})
    rates    = report["layers"].get("rates",             {})
    strength = report["layers"].get("currency_strength", {})
    intra    = report["layers"].get("intraday",          {})
    news     = report["layers"].get("news",              {})

    sess_lbl = sess.get("session_label", "")
    dow      = sess.get("day_of_week", "")
    price    = liq.get("current_price", "?")

    # ── Setup classification + journal (side effects only, no output) ────────
    inv   = _build_invalidation(htf, liq, bias)
    setup = _classify_setup(report, bias, conf, inv)
    report["setup"] = setup
    _write_journal(report, inv, setup)
    _dec = report.get("decision", {})
    report["grade"]    = _dec.get("grade", "C")
    report["risk_pct"] = _dec.get("risk_pct", 0.0)

    grade    = _dec.get("grade", "C")
    dec_conv = _dec.get("conviction", conf)
    risk_pct = _dec.get("risk_pct", 0.0)

    # ── Calendar gate disabled? Cap grade at B ───────────────────────────────
    _news_gate_disabled = news.get("news_gate_disabled", False)
    _original_grade     = grade
    if _news_gate_disabled and grade not in ("C", "B"):
        grade    = "B"
        risk_pct = 0.25   # B-grade risk

    # ── News blockers (computed once, used in multiple sections) ─────────────
    _news_hard_blocks = []
    try:
        import csv as _csv_nr, datetime as _dt_nr
        from pathlib import Path as _Path_nr
        _cal_nr = _Path_nr(__file__).parent / "calendar.csv"
        if _cal_nr.exists():
            _now_nr = _dt_nr.datetime.utcnow()
            for _row_nr in _csv_nr.DictReader(open(_cal_nr, newline="", encoding="utf-8")):
                if _row_nr.get("impact", "").lower() != "high":
                    continue
                if _row_nr.get("currency", "") not in ("GBP", "AUD"):
                    continue
                try:
                    _ev_nr   = _dt_nr.datetime.strptime(_row_nr["time"][:16], "%Y-%m-%d %H:%M")
                    _mins_nr = (_ev_nr - _now_nr).total_seconds() / 60
                    _act_nr  = str(_row_nr.get("actual", "")).strip()
                    if -90 <= _mins_nr <= 60 and not _act_nr:
                        _cur_nr = _row_nr.get("currency", "")
                        _evn_nr = _row_nr.get("event", "")
                        if _mins_nr <= 0:
                            _news_hard_blocks.append(
                                f"{_cur_nr} {_evn_nr} — releasing NOW, no actuals yet"
                            )
                        elif _mins_nr <= 15:
                            _news_hard_blocks.append(
                                f"{_cur_nr} {_evn_nr} — in {int(_mins_nr)} min, do not enter"
                            )
                        else:
                            _news_hard_blocks.append(
                                f"{_cur_nr} {_evn_nr} — in {int(_mins_nr)} min"
                            )
                except ValueError:
                    continue
    except Exception:
        pass

    # ── Value location conflict (computed once — used in conviction matrix) ──
    _val_verdict_str = str(val.get("verdict", ""))
    _val_conflict    = (
        ("STRONG DISCOUNT" in _val_verdict_str and bias == "BEARISH") or
        ("STRONG PREMIUM"  in _val_verdict_str and bias == "BULLISH")
    )
    _val_conflict_note = ""
    if _val_conflict:
        _fv_dist = abs(val.get("fv_diff_pips", 0) or 0)
        _fv_ref  = val.get("fair_value", "")
        _fv_dist_str = f" ({int(_fv_dist)} pips from fair value {_fv_ref})" if _fv_dist and _fv_ref else ""
        if "STRONG DISCOUNT" in _val_verdict_str:
            _val_conflict_note = (
                f"LOCATION CONFLICT: {_val_verdict_str}{_fv_dist_str} — "
                "shorting the cheap end of the range; buyers have structural advantage here"
            )
        else:
            _val_conflict_note = (
                f"LOCATION CONFLICT: {_val_verdict_str}{_fv_dist_str} — "
                "buying the expensive end of the range; sellers have structural advantage here"
            )

    # ── Calendar conflict (computed once — used in conviction matrix) ────────
    _cal_conflict      = False
    _cal_conflict_note = ""
    try:
        _e_all = news.get("events", [])
        _e_rel = [e for e in _e_all
                  if e.get("currency") in ("GBP", "AUD")
                  and str(e.get("actual", "")).strip() not in ("", "nan", "None", "N/A")]
        if _e_rel:
            _e_gbp        = [e for e in _e_rel if e.get("currency") == "GBP"]
            _e_aud        = [e for e in _e_rel if e.get("currency") == "AUD"]
            _e_gbp_beats  = sum(1 for e in _e_gbp if "beat"   in str(e.get("trade_bias","")).lower() or "✅" in str(e.get("trade_bias","")))
            _e_gbp_misses = sum(1 for e in _e_gbp if "missed" in str(e.get("trade_bias","")).lower() or "❌" in str(e.get("trade_bias","")))
            _e_aud_beats  = sum(1 for e in _e_aud if "beat"   in str(e.get("trade_bias","")).lower() or "✅" in str(e.get("trade_bias","")))
            _e_aud_misses = sum(1 for e in _e_aud if "missed" in str(e.get("trade_bias","")).lower() or "❌" in str(e.get("trade_bias","")))
            _e_net_score  = (_e_gbp_beats - _e_gbp_misses) - (_e_aud_beats - _e_aud_misses)
            if _e_net_score > 0 and bias == "BEARISH":
                _cal_conflict = True
                _cal_conflict_note = (
                    f"FUNDAMENTAL CONFLICT: Released data net BULLISH "
                    f"({_e_gbp_beats} GBP beat{'s' if _e_gbp_beats != 1 else ''}) — "
                    "data does not support shorts today"
                )
            elif _e_net_score < 0 and bias == "BULLISH":
                _cal_conflict = True
                _cal_conflict_note = (
                    f"FUNDAMENTAL CONFLICT: Released data net BEARISH "
                    f"({_e_aud_beats} AUD beat{'s' if _e_aud_beats != 1 else ''}, "
                    f"{_e_gbp_misses} GBP miss{'es' if _e_gbp_misses != 1 else ''}) — "
                    "data does not support longs today"
                )
    except Exception:
        pass

    # ── Fix Economic News in tier_signals to agree with calendar beat/miss score ─
    # decision_engine builds tier_signals before calendar beat/miss counts exist,
    # so the directional label and verdict can be wrong when stale.
    # Rule: stale = score zeroed = "=" icon regardless of direction.
    # Direction label is corrected to match the actual beat/miss outcome.
    try:
        import re as _re_fix
        _tier_sigs_fix = _dec.get("tier_signals", {})
        for _tier_entries in _tier_sigs_fix.values():
            for _ts in _tier_entries:
                if _ts.get("name") == "Economic News":
                    # Correct the icon — zeroed score is always neutral
                    _ts["verdict"] = "neutral"
                    # Correct the direction label if we have calendar data
                    if _e_rel and _e_net_score != 0:
                        _cal_dir_label = "bullish" if _e_net_score > 0 else "bearish"
                        _ts["note"] = _re_fix.sub(
                            r"leans \w+ for",
                            f"leans {_cal_dir_label} for",
                            _ts.get("note", ""),
                        )
    except Exception:
        pass

    # ═══════════════════════════════════════════════════════════════════════
    # HEADER
    # ═══════════════════════════════════════════════════════════════════════
    print("=" * W)
    print(f"  GBP/AUD  |  {_gen_12h} {_tz_lbl}  |  {dow}  |  {sess_lbl}")
    print("=" * W)

    # ── Market closed short circuit ──────────────────────────────────────────
    if report.get("market_closed"):
        print()
        print(f"  ⛔  {sess.get('close_reason', 'Market closed').upper()}")
        print(f"  Next open  : {sess.get('next_open', '')}")
        print(f"  Best use   : {sess.get('dow_best_for', '')}")
        print()
        print("=" * W)
        return

    # ── Since last run (compact — always useful at a glance) ─────────────────
    try:
        import json as _json_lr
        from pathlib import Path as _Path_lr
        _lr_path = _Path_lr(__file__).parent / "last_run.json"
        if _lr_path.exists():
            _lr        = _json_lr.loads(_lr_path.read_text())
            _lr_price  = _lr.get("price", 0) or 0
            _lr_time_pt= _lr.get("time_pt", _lr.get("time_utc", "?"))
            _cur_price = float(str(liq.get("current_price", 0) or 0))
            if _lr_price and _cur_price:
                _pdiff = round((_cur_price - _lr_price) * 10000)
                _pdir  = "▲" if _pdiff > 0 else "▼" if _pdiff < 0 else "→"
                print(f"  Since {_lr_time_pt}: {_lr_price} → {_cur_price}  ({_pdir} {abs(_pdiff)} pips)")
    except Exception:
        pass

    # ── Degraded data banner ─────────────────────────────────────────────────
    if report.get("degraded"):
        _dc = " | ".join(report.get("degraded_components", [])[:3])
        print(f"  ⚠️  DATA: {_dc}" if _dc else "  ⚠️  DATA: Some sources unavailable")

    # ═══════════════════════════════════════════════════════════════════════
    # SECTION 1 — IMMEDIATE ACTION
    # ═══════════════════════════════════════════════════════════════════════
    _grade_labels = {
        "A+": "EXECUTE — full size",
        "A":  "EXECUTE — standard size",
        "B+": "EXECUTE — reduced size",
        "B":  "EXECUTE — half size, manage actively",
        "C":  "NO TRADE — stand aside",
    }
    _action      = _grade_labels.get(grade, "NO TRADE — stand aside")
    _bias_icon   = {"BEARISH": "▼", "BULLISH": "▲"}.get(bias, "→")
    _sig_aligned = sum(1 for s in signals if s.get("bias", "") in (
        ("BEARISH",) if bias == "BEARISH" else ("BULLISH",)
    ))
    _sig_nonneutral = sum(1 for s in signals if s.get("bias", "NEUTRAL") != "NEUTRAL")
    _sig_total = _sig_nonneutral if _sig_nonneutral > 0 else (len(signals) if signals else 7)

    _sec("IMMEDIATE ACTION")
    print(f"  Status   : {_action}")
    print(f"  Bias     : {_bias_icon} {bias}  ({_sig_aligned}/{_sig_total} signals aligned)")
    print(f"  Grade    : {grade}  |  Conviction {dec_conv}/100  |  {risk_pct}% risk/trade")

    for _blk in _news_hard_blocks:
        print(f"  ⛔ NEWS   : {_blk}")

    if _news_gate_disabled:
        import re as _re_cal
        _cal_reason = news.get("disable_reason", "")
        _days_m = _re_cal.search(r'(\d+) days old', _cal_reason)
        _date_m = _re_cal.search(r'last event: ([^)]+)', _cal_reason)
        _days_s = _days_m.group(1) if _days_m else ""
        _date_s = (_date_m.group(1).strip() if _date_m else "").rstrip(")")
        if _days_s and _date_s:
            print(f"  ⛔ CALENDAR: CSV {_days_s}d old (last: {_date_s}) — news gate OFF")
        else:
            print(f"  ⛔ CALENDAR: Unavailable — manual check required")
        if _original_grade != grade:
            print(f"  ⚠️  Grade capped to {grade} (was {_original_grade}) — no news gate active")

    print()

    if grade == "C":
        _conflicts  = _dec.get("conflicts", [])
        _cap_reason = _dec.get("grade_cap_reason", "")
        _come_back  = _dec.get("come_back_at", "")
        print("  WHY NO TRADE:")
        if _news_hard_blocks:
            print("    • Active news event — execution blocked until actuals posted")
        for _c in _conflicts[:3]:
            print(f"    • {_c}")
        if _cap_reason and _cap_reason not in str(_conflicts):
            print(f"    • {_cap_reason}")
        if _val_conflict_note:
            print(f"    • {_val_conflict_note}")
        if _cal_conflict_note:
            print(f"    • {_cal_conflict_note}")
        if _come_back:
            print(f"  Come back: {_come_back}")
    else:
        _entry_cond  = _dec.get("entry_condition", "")
        _inv_note    = next(iter(_dec.get("invalidation", [])), "")
        _trade_type  = _dec.get("trade_type", "auto")
        _setup_lvls  = _dec.get("setup_levels", {})
        if _entry_cond:
            _wrap(f"Entry: {_entry_cond}")
        if _inv_note:
            _wrap(f"Wrong if: {_inv_note}")
        # ── Active conflicts — shown before setup levels ───────────────────
        if _val_conflict or _cal_conflict:
            print()
            print("  ⚠️  CONFLICTS:")
            if _val_conflict_note:
                print(f"    • {_val_conflict_note}")
            if _cal_conflict_note:
                print(f"    • {_cal_conflict_note}")

        # ── SETUP LEVELS block (grade B and above) ────────────────────────
        if _setup_lvls:
            print()
            _type_label = (
                "INTRADAY" if _trade_type == "intraday"
                else "SWING" if _trade_type == "swing"
                else "AUTO"
            )
            _wait_note = _setup_lvls.get("wait_note", "")
            if _wait_note:
                print(f"  ┌─ SETUP LEVELS ({_type_label}) {'─' * (W - 22 - len(_type_label))}")
                _wrap(f"  │  ⏳  {_wait_note}")
                print(f"  └{'─' * (W - 4)}")
            else:
                print(f"  ┌─ SETUP LEVELS ({_type_label}) {'─' * (W - 22 - len(_type_label))}")
                _ez   = _setup_lvls.get("entry_zone", "")
                _sl   = _setup_lvls.get("stop_loss", "")
                _tgt  = _setup_lvls.get("target", "")
                _sp   = _setup_lvls.get("stop_pips", "")
                _tp   = _setup_lvls.get("target_pips", "")
                _rr   = _setup_lvls.get("risk_reward", "")
                _rrf  = _setup_lvls.get("rr_flag", "")
                _lname = _setup_lvls.get("level_name", "")
                _tlvl  = _setup_lvls.get("tested_level", "")
                if _lname and _tlvl:
                    print(f"  │  Anchor      : {_lname} @ {_tlvl}")
                if _ez:
                    print(f"  │  Entry zone  : {_ez}")
                if _sl and _sp:
                    print(f"  │  Stop loss   : {_sl}  ({_sp} pips)")
                if _tgt and _tp:
                    print(f"  │  Target      : {_tgt}  ({_tp} pips)")
                if _rr:
                    print(f"  │  Risk:Reward : {_rr}:1")
                if _rrf:
                    _wrap(f"  │  ⚠  {_rrf}")
                print(f"  └{'─' * (W - 4)}")

    # ═══════════════════════════════════════════════════════════════════════
    # SECTION 2 — STRATEGIC BIAS
    # ═══════════════════════════════════════════════════════════════════════
    _sec("STRATEGIC BIAS")

    _lt     = htf.get("lt_trend", "")
    _st     = htf.get("st_trend", "")
    _lt_pct = htf.get("lt_pct", 0)
    _st_pct = htf.get("st_pct", 0)
    _ma50   = htf.get("ma50", "")

    def _ti(t): return "▼" if "DOWN" in str(t) else "▲" if "UP" in str(t) else "—"

    _trend_aligned = (
        ("DOWN" in str(_lt) and "DOWN" in str(_st)) or
        ("UP"   in str(_lt) and "UP"   in str(_st))
    )

    if _lt and _st:
        print(f"  Trend  : {_ti(_lt)} {_lt} ({_lt_pct:+.1f}%)  /  {_ti(_st)} {_st} ({_st_pct:+.1f}%)")
        if _trend_aligned:
            _dir_word = "downtrend" if "DOWN" in str(_lt) else "uptrend"
            print(f"           Both timeframes aligned — {_dir_word} is established")
        else:
            print(f"           Timeframes diverging — mixed signal, higher caution required")

    if _ma50:
        try:
            _p_f = float(str(price).replace(",", ""))
            _m_f = float(str(_ma50).replace(",", ""))
            _rel = "below" if _p_f < _m_f else "above"
            print(f"           Price {_rel} MA50 ({_ma50}) — {'bearish' if _rel == 'below' else 'bullish'} context")
        except Exception:
            pass

    # Rates: carry vs forward momentum — explicitly separated
    print()
    _boe      = rates.get("boe", {})
    _rba      = rates.get("rba", {})
    _r_diff   = rates.get("differential", 0) or 0
    _boe_s    = _boe.get("stance", "neutral").lower()
    _rba_s    = _rba.get("stance", "neutral").lower()
    _boe_r    = _boe.get("current_rate", "?")
    _rba_r    = _rba.get("current_rate", "?")
    _boe_desc = {"dovish": "cutting", "hawkish": "hiking", "neutral": "on hold"}.get(_boe_s, _boe_s)
    _rba_desc = {"dovish": "cutting", "hawkish": "hiking", "neutral": "on hold"}.get(_rba_s, _rba_s)
    _c_dir    = "GBP yields more" if _r_diff > 0 else "AUD yields more" if _r_diff < 0 else "equal yield"
    _c_bias   = "carry: bullish GBP/AUD" if _r_diff > 0 else "carry: bearish GBP/AUD"
    _mom_note = (
        "BoE cutting while RBA holds — spread narrowing, GBP-negative forward"
        if _boe_s == "dovish" and _rba_s != "dovish"
        else "RBA cutting while BoE holds — spread narrowing, AUD-negative forward"
        if _rba_s == "dovish" and _boe_s != "dovish"
        else "both banks stable — spread steady"
    )
    print(f"  Rates  : BoE {_boe_r}% ({_boe_desc})  vs  RBA {_rba_r}% ({_rba_desc})")
    print(f"           Gap {_r_diff:+.2f}% — {_c_dir}  ({_c_bias})")
    print(f"           Path: {_mom_note}")

    # Macro quadrant
    print()
    _macro_q   = _dec.get("macro_quadrant", "")
    _macro_mod = _dec.get("macro_modifier", 0)
    if _macro_q:
        _macro_effects = {
            "DEFLATION":    "risk-off — GBP typically holds vs AUD",
            "REFLATION":    "risk-on — AUD benefits as commodity currency",
            "GOLDILOCKS":   "risk-on, low inflation — AUD positive",
            "STAGFLATION":  "growth slowing — GBP holds better than AUD",
            "TRANSITIONAL": "mixed signals — macro not adding conviction either way",
        }
        _m_eff     = _macro_effects.get(_macro_q, "")
        _macro_dir = _dec.get("macro_direction", "")   # "reduce" = conflict, "boost" = aligned
        _macro_bio = _dec.get("macro_bias", "")        # BULLISH or BEARISH macro signal
        _conflict  = _macro_dir == "reduce" or (_macro_bio and _macro_bio != bias)
        _m_flag    = "  ⚡ conflicts with directional bias" if _conflict else ""
        print(f"  Macro  : {_macro_q} — {_m_eff}{_m_flag}")

    # Strategic valid-until level
    _inv_lvl = inv.get("invalidation", "")
    if _inv_lvl:
        _inv_dir = "above" if bias == "BEARISH" else "below"
        print()
        print(f"  Bias valid until: daily close {_inv_dir} {_inv_lvl} (MA50)")

    # ── REVERSAL WATCH — intermediate trend state (Priority 4) ─────────────
    _ctx_htf    = htf.get("context", "")
    _struct_htf = htf.get("daily_structure_type", "")
    _rev_watch  = False
    _rev_note   = ""
    _rev_zone   = ""
    _rev_conf   = ""
    try:
        _p_f2      = float(str(price)) if price != "?" else 0.0
        _atr_px    = (_atr or 0) * 0.0001
        _pdl_f     = float(str(liq.get("pdl", 0) or 0))
        _pdh_f     = float(str(liq.get("pdh", 0) or 0))

        if _ctx_htf == "COUNTER_TREND_BOUNCE" and _struct_htf == "HH_HL" and _p_f2 and _atr_px:
            _buf_req = _atr_px * 1.5
            _dist    = _p_f2 - _pdl_f if _pdl_f else _atr_px * 2
            _rev_watch = True
            _rev_note  = "Downtrend bounce — daily HH/HL forming, ST trend flipped UP"
            if _dist >= _buf_req:
                _rev_zone = (
                    f"Watching zone: {_pdl_f:.4f} – {_pdh_f:.4f}"
                    if _pdh_f else f"Above {_pdl_f:.4f}"
                )
                _rev_conf = "Confirm reversal: close back below recent higher low"
            else:
                _req_pips = round(_buf_req * 10000)
                _rev_zone = f"Too early — need {_req_pips} pip buffer from low ({_pdl_f:.4f})"
                _rev_conf = "Wait for price to establish distance before treating as reversal"

        elif _ctx_htf == "PULLBACK_IN_UPTREND" and _struct_htf == "LH_LL" and _p_f2 and _atr_px:
            _buf_req   = _atr_px * 1.5
            _dist      = _pdh_f - _p_f2 if _pdh_f else _atr_px * 2
            _rev_watch = True
            _rev_note  = "Uptrend pullback — daily LH/LL forming, ST trend flipped DOWN"
            if _dist >= _buf_req:
                _rev_zone = f"Watching zone: {_pdl_f:.4f} – {_pdh_f:.4f}" if _pdl_f else ""
                _rev_conf = "Confirm reversal: close back above recent lower high"
            else:
                _req_pips = round(_buf_req * 10000)
                _rev_zone = f"Too early — need {_req_pips} pip buffer from high ({_pdh_f:.4f})"
                _rev_conf = "Wait for price to establish distance before treating as reversal"
    except Exception:
        pass

    if _rev_watch:
        print()
        print(f"  ⚡ REVERSAL WATCH")
        for _rl in _tw.wrap(f"  → {_rev_note}", width=W - 2):
            print(_rl)
        if _rev_zone:
            for _rl in _tw.wrap(f"  → Zone: {_rev_zone}", width=W - 2):
                print(_rl)
        if _rev_conf:
            for _rl in _tw.wrap(f"  → Confirm: {_rev_conf}", width=W - 2):
                print(_rl)

    # ── Conflict note — max 2 lines, only when conflict exists (Priority 5) ──
    _macro_in_conflict = bool(_macro_q) and (
        _dec.get("macro_direction", "") == "reduce" or
        (bool(_dec.get("macro_bias")) and _dec.get("macro_bias") != bias)
    )
    _lt_st_conflict = not _trend_aligned and bool(_lt) and bool(_st)

    if _lt_st_conflict or _macro_in_conflict:
        print()
        if _lt_st_conflict:
            _lt_dir = "DOWN" if "DOWN" in str(_lt) else "UP"
            _st_dir = "DOWN" if "DOWN" in str(_st) else "UP"
            _c_line = f"⚡ Conflict: LT {_lt_dir} vs ST {_st_dir} — timeframes disagree"
            _i_line = "Impact: grade capped — await ST realignment before entry"
        else:
            _c_line = f"⚡ Conflict: {_macro_q} macro opposes directional bias"
            _i_line = "Impact: conviction capped — macro-driven moves likely to fade"
        print(_tw.fill(_c_line, width=W, initial_indent="  ", subsequent_indent="    "))
        print(_tw.fill(_i_line, width=W, initial_indent="     ", subsequent_indent="     "))

    # ═══════════════════════════════════════════════════════════════════════
    # SECTION 3 — SETUP STATE + NEXT TRADE
    # ═══════════════════════════════════════════════════════════════════════
    _sec("SETUP STATE")

    _id_high  = intra.get("asian_high")
    _id_low   = intra.get("asian_low")
    _id_pips  = intra.get("asian_range_pips")
    _id_pos   = intra.get("price_position", "")
    _id_ft    = intra.get("fakeout_detected", False)
    _id_ftype = intra.get("fakeout_type", "")
    _id_entry = intra.get("entry_note", "")
    _r_used   = reg.get("range_used")
    _r_rem    = reg.get("range_remaining")
    _atr      = reg.get("atr_pips", 0) or 0
    _fuel_pct = reg.get("fuel_pct", 0) or 0
    _adx      = reg.get("adx", 0) or 0
    _psrc     = liq.get("price_source", "")
    _psrc_tag = "[live]" if "OANDA" in str(_psrc) else "[last close]"

    print(f"  Price    : {price}  {_psrc_tag}")
    if _r_used is not None and _atr:
        print(f"  Range    : {_r_used}/{_atr:.0f} pips used ({_fuel_pct:.0f}%)  —  {round(_r_rem or 0)} pips left today")
    if _adx:
        _adx_lbl = "strong trend" if _adx > 25 else "trend building" if _adx > 20 else "ranging/choppy"
        print(f"  Momentum : ADX {_adx:.1f}  ({_adx_lbl})")

    if _id_high and _id_low:
        _pos_lbl = {
            "ABOVE_RANGE":  f"ABOVE Asian high ({_id_high:.4f})",
            "BELOW_RANGE":  f"BELOW Asian low ({_id_low:.4f})",
            "INSIDE_RANGE": "Inside Asian range",
        }.get(_id_pos, _id_pos)
        print(f"  Session  : Asian range {_id_low:.4f}–{_id_high:.4f}  ({_id_pips} pips)  |  Price {_pos_lbl}")

    if _id_ft and _id_ftype not in ("NONE", "INSIDE", ""):
        print(f"  ⚡ FAKEOUT: {_id_ftype.lower().replace('_', ' ')} detected — reversal signal active")

    _sess_notes = {
        "Tokyo":     "Tokyo — GBP illiquid. Wait for London open.",
        "London":    "London — prime session for GBP/AUD. Full participation.",
        "New York":  "New York — USD-driven. Watch DXY for context.",
        "London/NY": "London + NY overlap — busiest window. Best entries.",
        "Sydney":    "Sydney — thin market, wider spreads. Wait.",
        "Off-hours": "Off-hours. Market closed. Do not trade.",
    }
    print(f"  Window   : {_sess_notes.get(sess_lbl, sess_lbl)}")


    # ── NEXT VALID TRADE (or WHAT TO WAIT FOR when grade is C) ──────────────
    print()
    _trg   = setup.get("triggers", {})
    _tp    = setup.get("trade_plan", {})
    _d_lbl = "SHORT" if bias == "BEARISH" else "LONG" if bias == "BULLISH" else "NONE"
    _ideal_key = "aplus_short" if bias == "BEARISH" else "aplus_long"
    _ideal     = _tp.get(_ideal_key, "")
    _avoid     = _tp.get("avoid", "")
    _exec_note = _tp.get("exec_note", "")
    _hard      = _trg.get("hard_triggers", _trg.get("aplus", []))
    _ctx_f     = _trg.get("context_filters", [])
    _min       = _trg.get("minimum", [])

    # ── Hard conviction floor: < 35 = no triggers, just come-back note ───────
    _come_back_note = _dec.get("come_back_at", "")
    if dec_conv < 35:
        print(f"  Conviction {dec_conv}/100 — too low to generate setup triggers.")
        if _come_back_note:
            print(f"  Come back: {_come_back_note}")
        else:
            _sess_optimal = sess_lbl in ("London", "New York", "London/NY")
            _cb_suffix = "" if _sess_optimal else " or session improves"
            print(f"  Come back: when conviction reaches 35{_cb_suffix}")
    elif grade == "C":
        # Grade C but conviction is 35+ — show monitoring conditions
        print(f"  WHAT TO WAIT FOR  ({_d_lbl}):")
        if _ideal:
            print(f"    Setup    : {_ideal}")
        if _hard:
            print(f"    Triggers :")
            for _item in (_hard or [])[:4]:
                print(f"      ☐ {_item}")
        if _min:
            print(f"    Minimum  :")
            for _item in _min:
                print(f"      ✓ {_item}")
    else:
        print(f"  TRADE ({_d_lbl}):")
        if _exec_note:
            print(f"    Execute  : {_exec_note}")
        if _ideal:
            print(f"    Setup    : {_ideal}")
        if _hard:
            print(f"    Triggers :")
            for _item in (_hard or [])[:4]:
                print(f"      ☐ {_item}")
        if _ctx_f:
            print(f"    Filters  :")
            for _item in _ctx_f[:3]:
                print(f"      ⚙ {_item}")
        if _avoid:
            print(f"    Avoid    : {_avoid}")

    # ═══════════════════════════════════════════════════════════════════════
    # SECTION 4 — INVALIDATION
    # ═══════════════════════════════════════════════════════════════════════
    _sec("INVALIDATION")

    _inv_dir       = "above" if bias == "BEARISH" else "below"
    _inv_strategic = inv.get("invalidation") or ""   # guard against explicit None
    _inv_action    = inv.get("action_on_break", "")
    _warn_lvl      = inv.get("warning_level") or ""

    # Safe price float — defined before any try blocks so both blocks can use it
    try:
        _p_float_inv = float(str(price)) if str(price) not in ("?", "None", "") else 0.0
    except (ValueError, TypeError):
        _p_float_inv = 0.0

    # Nearest resistance above price — short-thesis invalidation level
    # Priority: key levels above price → fib retracements above price → prior swing high label
    _nearest_res       = None
    _nearest_res_label = ""        # human-readable source label
    _nearest_res_below = False     # True when the fallback level is already below price
    if _p_float_inv:
        try:
            _res_cands = []
            for _k_lv, _k_lb in (("pdh", "PDH"), ("pwh", "week high")):
                _v = liq.get(_k_lv)
                if _v:
                    _fv = float(str(_v))
                    if _fv > _p_float_inv:
                        _res_cands.append((_fv, _k_lb))
            for _eq in liq.get("equal_highs", []):
                _fv = float(str(_eq))
                if _fv > _p_float_inv:
                    _res_cands.append((_fv, "equal highs"))
            if _res_cands:
                _res_cands.sort()
                _nearest_res, _nearest_res_label = _res_cands[0]
        except Exception:
            pass

        # Fallback 1: fib retracement level above current price (structural)
        if not _nearest_res:
            _fib_lvls_inv = htf.get("fib_levels", {})
            _fib_above = []
            for _pct in ("23.6", "38.2", "50.0", "61.8", "78.6"):
                _fv2 = _fib_lvls_inv.get(_pct)
                if _fv2:
                    try:
                        _fv2f = float(str(_fv2))
                        if _fv2f > _p_float_inv:
                            _fib_above.append((_fv2f, f"{_pct}% retracement"))
                    except (ValueError, TypeError):
                        pass
            if _fib_above:
                _fib_above.sort()
                _nearest_res, _nearest_res_label = _fib_above[0]

        # Fallback 2: prior week high — price has already broken above it, note that
        if not _nearest_res:
            _pwh_v = liq.get("pwh") or liq.get("pdh")
            if _pwh_v:
                _nearest_res       = float(str(_pwh_v))
                _nearest_res_label = "prior week high"
                _nearest_res_below = True   # level is below current price

    # Nearest support below price — long-thesis invalidation level
    _nearest_sup = None
    if _p_float_inv:
        try:
            _sup_cands = []
            for _k_lv in ("pdl", "pwl"):
                _v = liq.get(_k_lv)
                if _v:
                    _fv = float(str(_v))
                    if _fv < _p_float_inv:
                        _sup_cands.append(_fv)
            for _eq in liq.get("equal_lows", []):
                _fv = float(str(_eq))
                if _fv < _p_float_inv:
                    _sup_cands.append(_fv)
            if _sup_cands:
                _nearest_sup = max(_sup_cands)
        except Exception:
            pass
        # Fallback: nearest quarter-handle round number below price
        if not _nearest_sup:
            _step = 0.0025
            _nearest_sup = round((round(_p_float_inv / _step) - 1) * _step, 4)

    # Fallback: use pwl/pwh directly if level-search came up empty
    if not _inv_strategic:
        if bias == "BEARISH":
            _inv_strategic = str(liq.get("pwh") or liq.get("pdh") or "")
        else:
            _inv_strategic = str(liq.get("pwl") or liq.get("pdl") or "")

    if grade == "C":
        # Line 1: current bias invalidation (structural level)
        if _inv_strategic:
            _dir_word = "Short" if bias == "BEARISH" else "Long"
            print(f"  {_dir_word} thesis invalidates on daily close {_inv_dir} {_inv_strategic}")
        elif bias in ("BULLISH", "BEARISH"):
            print(f"  No structural invalidation level available — check data feeds")

        # Line 2: opposite-side thesis (always show when bias is directional)
        if bias == "BULLISH" and _nearest_res and _p_float_inv:
            if _nearest_res_below:
                _lbl = f"  ({_nearest_res_label})" if _nearest_res_label else ""
                print(f"  Short thesis: price above prior swing high {_nearest_res:.4f}{_lbl} — no structural resistance above")
            else:
                _res_pips = round((_nearest_res - _p_float_inv) * 10000)
                _lbl = f"  ({_nearest_res_label})" if _nearest_res_label else ""
                print(f"  Short thesis invalidates on daily close above {_nearest_res:.4f}{_lbl}  ({_res_pips} pips)")
        elif bias == "BEARISH" and _nearest_sup and _p_float_inv:
            _sup_pips = round((_p_float_inv - _nearest_sup) * 10000)
            print(f"  Long thesis invalidates on daily close below {_nearest_sup:.4f}  ({_sup_pips} pips)")
    else:
        # Setup — kills this specific entry idea
        _trg_inv = (_trg.get("invalidates") or []) if _trg else []
        if _trg_inv:
            print(f"  Setup    : {_trg_inv[0]}")
            if len(_trg_inv) > 1:
                print(f"             {_trg_inv[1]}")

        # Tactical — weakens weekly directional lean
        if _warn_lvl:
            print(f"  Tactical : daily close {_inv_dir} {_warn_lvl}  —  lean weakens, reduce size")

        # Strategic — ends the multi-week view entirely
        if _inv_strategic:
            _short_action = _inv_action.split(".")[0] if _inv_action else "reassess direction"
            print(f"  Strategic: daily close {_inv_dir} {_inv_strategic}  —  {_short_action}")

        # Opposite-side thesis — always show when bias is directional
        if bias == "BULLISH" and _nearest_res and _p_float_inv:
            if _nearest_res_below:
                _lbl = f"  ({_nearest_res_label})" if _nearest_res_label else ""
                print(f"  Short thesis: price above prior swing high {_nearest_res:.4f}{_lbl} — no structural resistance above")
            else:
                _res_pips = round((_nearest_res - _p_float_inv) * 10000)
                _lbl = f"  ({_nearest_res_label})" if _nearest_res_label else ""
                print(f"  Short thesis invalidates on daily close above {_nearest_res:.4f}{_lbl}  ({_res_pips} pips)")
        elif bias == "BEARISH" and _nearest_sup and _p_float_inv:
            _sup_pips = round((_p_float_inv - _nearest_sup) * 10000)
            print(f"  Long thesis invalidates on daily close below {_nearest_sup:.4f}  ({_sup_pips} pips)")

    # ═══════════════════════════════════════════════════════════════════════
    # SECTION 5 — CONVICTION MATRIX
    # ═══════════════════════════════════════════════════════════════════════
    _sec("CONVICTION MATRIX")

    _s_score = _dec.get("structural_score", 50)
    _t_score = _dec.get("tactical_score",   50)
    _e_score = _dec.get("execution_score",  50)
    _tier_sigs = _dec.get("tier_signals",   {})
    _upgrade   = _dec.get("upgrade_hints",  [])
    _leg_data  = _dec.get("legs",           {})

    def _bar(score: int, width: int = 10) -> str:
        filled = round(score / 100 * width)
        return "█" * filled + "░" * (width - filled)

    def _tier_label(score: int) -> str:
        if score >= 70: return "strong"
        if score >= 50: return "moderate"
        if score >= 35: return "weak"
        return "blocking"

    _verdict_icons = {
        "confirm":  "✓",
        "conflict": "✗",
        "neutral":  "=",
        "no_data":  "?",
    }

    def _print_tier(name: str, score: int, sigs: list) -> None:
        lbl = _tier_label(score)
        print(f"  {name:<12} [{_bar(score)}]  {score:>3}%  — {lbl}")
        for sig in sigs:
            icon = _verdict_icons.get(sig.get("verdict", "neutral"), "=")
            sname = sig.get("name", "")[:24]
            snote = sig.get("note", "")
            print(f"    {icon} {sname:<24}", end="")
            # Wrap note if it exists
            if snote:
                _note_words = snote.split()
                _line = ""
                _first = True
                for _w in _note_words:
                    if len(_line) + len(_w) + 1 > W - 30:
                        if _first:
                            print(_line)
                            _first = False
                        else:
                            print(f"{'':30}{_line}")
                        _line = _w
                    else:
                        _line = (_line + " " + _w).strip()
                if _line:
                    if _first:
                        print(_line)
                    else:
                        print(f"{'':30}{_line}")
            else:
                print()

    _print_tier("Structural", _s_score, _tier_sigs.get("structural", []))
    print()
    _print_tier("Tactical",   _t_score, _tier_sigs.get("tactical",   []))
    print()
    _print_tier("Execution",  _e_score, _tier_sigs.get("execution",  []))

    # Leg decomposition detail
    if _leg_data.get("driver", "UNKNOWN") not in ("UNKNOWN", "NEUTRAL"):
        print()
        _gbpu = _leg_data.get("gbpusd_change")
        _audu = _leg_data.get("audusd_change")
        _drv  = _leg_data.get("driver", "")
        if _gbpu is not None and _audu is not None:
            print(f"  Leg detail: GBP/USD {_gbpu:+.3f}%  |  AUD/USD {_audu:+.3f}%")
            for _ln in _tw.wrap(_leg_data.get("note", ""), width=W - 4):
                print(f"    {_ln}")

    # Upgrade hints — what would lift the grade
    if _upgrade:
        print()
        print(f"  TO REACH A GRADE:")
        for _uh in _upgrade[:3]:
            for _ul in _tw.wrap(f"→ {_uh}", width=W - 4):
                print(f"    {_ul}")

    # Live vs structural conflict callout
    if report.get("live_vs_structural_conflict"):
        _ld2 = report.get("live_dominant", "NEUTRAL")
        _sd2 = report.get("struct_dominant", "NEUTRAL")
        print()
        print(f"  ⚡ SHORT-TERM vs LONG-TERM CONFLICT")
        print(f"     Today: {_ld2}  |  HTF: {_sd2}")
        print(f"     Intraday move is against the dominant trend — likely a pullback.")

    # ═══════════════════════════════════════════════════════════════════════
    # SECTION 6 — KEY LEVELS
    # ═══════════════════════════════════════════════════════════════════════
    _sec("KEY LEVELS")

    _pdh = liq.get("pdh", "")
    _pdl = liq.get("pdl", "")
    _pwh = liq.get("pwh", "")
    _pwl = liq.get("pwl", "")

    try:
        _p_float = float(str(price))
    except Exception:
        _p_float = 0

    if _p_float:
        _eq_ha      = sorted([v for v in liq.get("equal_highs", [])
                              if v > _p_float and (v - _p_float) / _p_float < 0.015])
        _eq_la      = sorted([v for v in liq.get("equal_lows", [])
                              if v > _p_float and (v - _p_float) / _p_float < 0.015])
        _eq_hb      = sorted([v for v in liq.get("equal_highs", [])
                              if v < _p_float and (_p_float - v) / _p_float < 0.015], reverse=True)
        _eq_lb      = sorted([v for v in liq.get("equal_lows", [])
                              if v < _p_float and (_p_float - v) / _p_float < 0.015], reverse=True)
        _resistance = sorted(set(_eq_ha + _eq_la))[:3]
        _support    = sorted(set(_eq_lb + _eq_hb), reverse=True)[:3]
    else:
        _resistance, _support = [], []

    print(f"  Price now : {price}")
    print()

    # Breakout flags — when price has cleared a key prior level
    if _p_float:
        try:
            _pdh_f2 = float(str(_pdh)) if _pdh else 0.0
            _pwh_f2 = float(str(_pwh)) if _pwh else 0.0
            _pdl_f2 = float(str(_pdl)) if _pdl else 0.0
            _pwl_f2 = float(str(_pwl)) if _pwl else 0.0
            if _pdh_f2 and _p_float > _pdh_f2:
                _bo_pips = round((_p_float - _pdh_f2) * 10000)
                print(f"  ⚡ Price ABOVE PDH ({_pdh}) — {_bo_pips} pips above prior session range")
            elif _pwh_f2 and _p_float > _pwh_f2:
                _bo_pips = round((_p_float - _pwh_f2) * 10000)
                print(f"  ⚡ Price ABOVE week high ({_pwh}) — {_bo_pips} pips above prior week range")
            if _pdl_f2 and _p_float < _pdl_f2:
                _bd_pips = round((_pdl_f2 - _p_float) * 10000)
                print(f"  ⚡ Price BELOW PDL ({_pdl}) — {_bd_pips} pips below prior session range")
            elif _pwl_f2 and _p_float < _pwl_f2:
                _bd_pips = round((_pwl_f2 - _p_float) * 10000)
                print(f"  ⚡ Price BELOW week low ({_pwl}) — {_bd_pips} pips below prior week range")
        except (ValueError, TypeError):
            pass

    if _resistance:
        print(f"  Resistance: {'  |  '.join(str(v) for v in _resistance)}")

    # Fib resistance above current price — structural targets
    _fib_res_display = []
    if _p_float:
        _fib_lvls_kl = htf.get("fib_levels", {})
        for _fl in ("23.6", "38.2", "50.0", "61.8"):
            _fv_lvl = _fib_lvls_kl.get(_fl)
            if _fv_lvl:
                try:
                    _fv_f = float(str(_fv_lvl))
                    if _fv_f > _p_float:
                        _dist = round((_fv_f - _p_float) * 10000)
                        _fib_res_display.append(f"{_fv_lvl} ({_fl}%  +{_dist}p)")
                except (ValueError, TypeError):
                    pass
    if _fib_res_display:
        print(f"  Fib resist: {'  |  '.join(_fib_res_display[:3])}")

    _hl = []
    if _pdh: _hl.append(f"PDH {_pdh}")
    if _pwh: _hl.append(f"Week high {_pwh}")
    if _hl:
        print(f"  Prior high: {'  |  '.join(_hl)}")
    if _support:
        print(f"  Support   : {'  |  '.join(str(v) for v in _support)}")
    _ll = []
    if _pdl: _ll.append(f"PDL {_pdl}")
    if _pwl: _ll.append(f"Week low {_pwl}")
    if _ll:
        print(f"  Prior low : {'  |  '.join(_ll)}")

    _sweep = liq.get("sweep_note", "").strip()
    if _sweep and "no sweep" not in _sweep.lower():
        _sw_lines = _tw.wrap(_sweep, width=W - 16)
        for _si, _sl in enumerate(_sw_lines):
            print(f"  {'Sweep     : ' if _si == 0 else ' ' * 12}{_sl}")
    else:
        _near = liq.get("nearest_pool", "")
        if _near:
            print(f"  Watch     : {_near} — prior high/low. Sweep + reversal is the entry signal.")

    _fib_levels = htf.get("fib_levels", {})
    if _fib_levels:
        _fd = []
        _cur_price_f = float(str(price).replace("?", "0") or 0)
        _atr_price   = (_atr or 0) * 0.0001  # convert pips to price
        for _fl in ["23.6", "38.2", "50.0", "61.8"]:
            _fv_lvl = _fib_levels.get(_fl)
            if _fv_lvl and _cur_price_f and _atr_price:
                if abs(float(_fv_lvl) - _cur_price_f) <= _atr_price:
                    _fd.append(f"{_fl}%={_fv_lvl}")
        if _fd:
            print()
            print(f"  Fib levels: {' | '.join(_fd)}")

    # ═══════════════════════════════════════════════════════════════════════
    # SECTION 7 — MARKET DATA
    # ═══════════════════════════════════════════════════════════════════════
    _sec("MARKET DATA")

    # Value
    _val_v   = val.get("verdict", "")
    _fv_prc  = val.get("fair_value", "")
    _fv_diff = val.get("fv_diff_pips", 0) or 0
    if _val_v:
        _vd = "above" if _fv_diff > 0 else "below"
        print(f"  Value     : {_val_v}  ({abs(_fv_diff):.0f} pips {_vd} fair value {_fv_prc})")

    # Regime / momentum
    if _adx:
        _adx_ctx = "strong trend" if _adx > 25 else "trend building" if _adx > 20 else "ranging/choppy"
        _vol_lbl = reg.get("volatility", "")
        _vol_note = reg.get("vol_note", "")
        print(f"  Momentum  : ADX {_adx:.1f} ({_adx_ctx})  |  ATR {_atr:.0f} pips avg  |  {_fuel_pct:.0f}% of range used")
        if _vol_lbl:
            print(f"  Volatility: {_vol_lbl}  —  {_vol_note}")

    # Cross-market — always use cross-market source (avoids defaulted 0.0 from brief)
    print()
    _vix     = cross.get("vix_level")
    _vix_c   = cross.get("vix_change")
    _sp      = cross.get("sp500_change")
    _dxy     = cross.get("dxy_change")
    _gold    = cross.get("gold_change")
    _bhp     = cross.get("bhp_change")
    _risk    = cross.get("risk_mode", "NEUTRAL")
    _cx_bias = cross.get("overall_bias", "NEUTRAL")

    if _vix and _vix > 0:
        print(f"  Risk      : VIX {_vix:.1f}  ({_vix_c:+.1f})  |  S&P500 {_sp:+.2f}%  |  {_risk.replace('_', '-')}")
    if _dxy is not None:
        _dxy_lbl = "USD weak — generally supportive for GBP/AUD" if _dxy < 0 else "USD strong — headwind for GBP/AUD"
        print(f"  DXY       : {_dxy:+.3f}%  ({_dxy_lbl})")
    if _gold is not None and _bhp is not None:
        print(f"  Drivers   : Gold {_gold:+.3f}%  |  Iron ore {_bhp:+.3f}%")
    if _cx_bias and _cx_bias != "NEUTRAL":
        _cx_narr2 = cross.get("narrative", "") or f"{_cx_bias} for GBP/AUD"
        print(f"  Cross-mkt :")
        for _cl in _tw.wrap(_cx_narr2, width=W - 4):
            print(f"    {_cl}")

    _vr = cross.get("vix_regime", "NORMAL")
    if _vr in ("PANIC_FADING", "PANIC_BUILDING", "FEAR_CLEARING"):
        _vr_note = cross.get("vix_regime_note", "")
        _vr_icon = {"PANIC_FADING": "🔄", "PANIC_BUILDING": "⚡", "FEAR_CLEARING": "📉"}.get(_vr, "")
        if _vr_note:
            print(f"  {_vr_icon} {_vr_note[:W - 6]}")

    # Currency strength
    print()
    _gbp_s = strength.get("GBP", 0) or 0
    _aud_s = strength.get("AUD", 0) or 0
    _str_d = round(_gbp_s - _aud_s, 1)
    if abs(_str_d) < 10:
        print(f"  Strength  : GBP {_gbp_s:+.0f}  |  AUD {_aud_s:+.0f}  — no clear intraday strength edge")
    elif _str_d > 0:
        print(f"  Strength  : GBP {_gbp_s:+.0f}  vs  AUD {_aud_s:+.0f}  — GBP outperforming by {abs(_str_d):.0f} pts")
    else:
        print(f"  Strength  : AUD {_aud_s:+.0f}  vs  GBP {_gbp_s:+.0f}  — AUD outperforming by {abs(_str_d):.0f} pts")

    # COT
    _gbp_pct  = cot.get("gbp_pct_long", 0) or 0
    _aud_pct  = cot.get("aud_pct_long", 0) or 0
    _aud_extr = cot.get("aud_extreme", False)
    _cot_dt   = cot.get("report_date", "")
    _cot_str  = f"GBP {_gbp_pct:.0f}% long  |  AUD {_aud_pct:.0f}% long"
    if _aud_extr:
        _cot_str += "  (CROWDED — contrarian bearish signal)"
    if _cot_dt:
        _cot_str += f"  [{_cot_dt}]"
    print(f"  COT       : {_cot_str}")


    # ═══════════════════════════════════════════════════════════════════════
    # SECTION 8 — ECONOMIC CALENDAR
    # ═══════════════════════════════════════════════════════════════════════
    _sec("ECONOMIC CALENDAR")

    _all_evs = news.get("events", [])
    _rel_evs = [e for e in _all_evs
                if e.get("currency") in ("GBP", "AUD")
                and str(e.get("actual", "")).strip() not in ("", "nan", "None", "N/A")]
    _upc_evs = [e for e in _all_evs
                if e.get("currency") in ("GBP", "AUD")
                and str(e.get("actual", "")).strip() in ("", "nan", "None", "N/A")]

    _stale_evs    = []
    _real_upcoming = []
    for _ev in _upc_evs:
        _hrs = _hours_until(str(_ev.get("time", "")))
        if _hrs < -2:
            _stale_evs.append(_ev)
        else:
            _real_upcoming.append(_ev)

    # Stale events — need actuals added (shown prominently)
    if _stale_evs:
        print(f"  ⚠️  {len(_stale_evs)} event(s) need actuals — add to calendar.csv:")
        _seen_st = set()
        for _ev in _stale_evs:
            _k = str(_ev.get("time", ""))[:16]
            if _k not in _seen_st:
                _seen_st.add(_k)
                _t = _fmt_pst(str(_ev["time"]), style="short")
                print(f"     → {_ev.get('currency', '')} {_ev.get('event', '')}  {_t}")
        print()

    # Upcoming events
    if _real_upcoming:
        print(f"  UPCOMING:")
        _seen2 = set()
        for _ev in _real_upcoming[:6]:
            _k2 = (str(_ev.get("time", ""))[:16], _ev.get("currency", ""))
            if _k2 in _seen2:
                continue
            _seen2.add(_k2)
            _t_str = _fmt_pst(str(_ev["time"]), style="long")
            _hrs2  = _hours_until(str(_ev["time"]))
            _hstr  = f"{_hrs2:.0f}h" if _hrs2 > 0 else "NOW"
            _fc2   = str(_ev.get("forecast", "")).strip()
            _pr2   = str(_ev.get("previous", "")).strip()
            _imp2  = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(_ev.get("impact", ""), "  ")
            _fc_s  = f"  exp {_fc2}" if _fc2 and _fc2 not in ("nan", "None", "") else ""
            _pr_s  = f"  prev {_pr2}" if _pr2 and _pr2 not in ("nan", "None", "") else ""
            print(f"  {_imp2} {_ev.get('event', '')} ({_ev.get('currency', '')})  {_t_str}  ({_hstr}){_fc_s}{_pr_s}")
        print()

    # Released events
    if _rel_evs:
        # Compute net score from beat/miss counts — single source of truth for both header and reading
        _gbp_rel    = [e for e in _rel_evs if e.get("currency") == "GBP"]
        _aud_rel    = [e for e in _rel_evs if e.get("currency") == "AUD"]
        _gbp_beats  = sum(1 for e in _gbp_rel if "beat"   in str(e.get("trade_bias","")).lower() or "✅" in str(e.get("trade_bias","")))
        _gbp_misses = sum(1 for e in _gbp_rel if "missed" in str(e.get("trade_bias","")).lower() or "❌" in str(e.get("trade_bias","")))
        _aud_beats  = sum(1 for e in _aud_rel if "beat"   in str(e.get("trade_bias","")).lower() or "✅" in str(e.get("trade_bias","")))
        _aud_misses = sum(1 for e in _aud_rel if "missed" in str(e.get("trade_bias","")).lower() or "❌" in str(e.get("trade_bias","")))
        # Positive = GBP outperformed = bullish GBP/AUD
        _net_score  = (_gbp_beats - _gbp_misses) - (_aud_beats - _aud_misses)
        _cal_verdict = "BULLISH" if _net_score > 0 else "BEARISH" if _net_score < 0 else "MIXED"

        print(f"  RELEASED  ({len(_rel_evs)} events — net {_cal_verdict}):")
        _seen3 = set()
        for _ev in _rel_evs:
            _k3 = (str(_ev.get("time", ""))[:16], _ev.get("event", "")[:20])
            if _k3 in _seen3:
                continue
            _seen3.add(_k3)
            _act  = str(_ev.get("actual", "")).strip()
            _fc3  = str(_ev.get("forecast", "")).strip()
            _t3   = _fmt_pst(str(_ev["time"]), style="short")
            _tb   = str(_ev.get("trade_bias", "") or "")
            if "✅" in _tb or "beat" in _tb.lower():
                _ic = "✅"
            elif "❌" in _tb or "missed" in _tb.lower():
                _ic = "❌"
            elif "matched" in _tb.lower():
                _ic = "= "
            else:
                _ic = "  "
            _fc_s3 = f"  exp {_fc3}" if _fc3 and _fc3 not in ("nan", "None", "") else ""
            print(f"  {_ic} {_ev.get('event', '')[:38]:<38} {_act:>8}{_fc_s3}  ({_ev.get('currency', '')})  {_t3}")

        # Reading paragraph — uses same _net_score as header
        _cal_narr_parts = []
        if _net_score > 0:
            _cal_narr_parts.append(
                f"Today's economic releases have been GBP-positive on balance "
                f"({_gbp_beats} GBP beat{'s' if _gbp_beats != 1 else ''} vs {_aud_beats} AUD beat{'s' if _aud_beats != 1 else ''}). "
                f"This adds fundamental support to a bullish GBP/AUD lean."
            )
            if bias == "BEARISH":
                _cal_narr_parts.append(
                    "Note: this conflicts with the overall bearish bias — the data does not support shorts today."
                )
        elif _net_score < 0:
            _cal_narr_parts.append(
                f"Today's economic releases have been AUD-positive or GBP-negative on balance "
                f"({_aud_beats} AUD beat{'s' if _aud_beats != 1 else ''}, {_gbp_misses} GBP miss{'es' if _gbp_misses != 1 else ''}). "
                f"This adds fundamental pressure to GBP/AUD."
            )
            if bias == "BEARISH":
                _cal_narr_parts.append("This supports the bearish bias from a data perspective.")
        else:
            _cal_narr_parts.append(
                "Today's economic releases have been mixed with no clear winner between GBP and AUD. "
                "The calendar is not adding directional edge today."
            )
        if _news_hard_blocks:
            _cal_narr_parts.append(
                "Note: there is an active high-impact event nearby — wait for actuals before entering."
            )
        _cal_narr = " ".join(_cal_narr_parts)
        if _cal_narr:
            print()
            _wrap(f"Reading: {_cal_narr}")

    # ═══════════════════════════════════════════════════════════════════════
    # FOOTER — Cross-run state tracking (compact)
    # ═══════════════════════════════════════════════════════════════════════
    try:
        _cr_setup = report.get("setup", {}) or {}
        _cr_inv   = report["layers"].get("invalidation", {}) or {}
        _cur_run_data = {
            "primary_state":    (_cr_setup.get("primary_state") or report.get("primary_state", "")),
            "conviction_score": dec_conv,
            "price":            float(liq.get("current_price", 0) or 0),
            "grade":            report.get("grade", ""),
            "trigger_price":    None,
            "invalidation":     _cr_inv.get("invalidation", ""),
            "session":          sess_lbl,
            "bias":             report.get("overall_bias", ""),
            "wait_for":         _cr_setup.get("wait_for", ""),
            # extra context for synthesis line (Priority 6)
            "sweep_confirmed":  bool(liq.get("sweep_note", "") and "no sweep" not in str(liq.get("sweep_note", "")).lower()),
            "value_verdict":    val.get("verdict", ""),
        }
        import re as _re_lr
        _nums_lr = _re_lr.findall(r'1\.\d{3,4}', str(_cur_run_data["wait_for"]))
        if _nums_lr:
            _cur_run_data["trigger_price"] = float(_nums_lr[0])
        _intelligence = get_cross_run_intelligence(_cur_run_data)
        _intel_block  = format_cross_run_block(_intelligence, width=W)
        if _intel_block:
            print()
            print(_intel_block)
    except Exception:
        pass

    # ── Save last_run.json for next-run comparison ───────────────────────────
    try:
        import json as _json2
        from pathlib import Path as _Path3

        _sv_setup = report.get("setup", {}) or {}
        _sv_liq   = report.get("layers", {}).get("liquidity", {}) or {}
        _sv_inv   = report.get("layers", {}).get("invalidation", {}) or {}
        _sv_val   = report.get("layers", {}).get("value", {}) or {}
        _sv_sess  = report.get("layers", {}).get("session", {}) or {}
        _sv_conf  = report.get("conviction_score", 0) or 0
        _sv_grade = report.get("grade", "") or ""
        _sv_risk  = report.get("risk_pct", 0) or 0

        try:
            from datetime import datetime as _dt2, timedelta as _td2
            _now = _dt2.now()
            _yr2 = _now.year
            _mar = _dt2(_yr2, 3, 8)
            _nov = _dt2(_yr2, 11, 1)
            _pdt_start = _mar + _td2(days=(6 - _mar.weekday()) % 7)
            _pst_start = _nov + _td2(days=(6 - _nov.weekday()) % 7)
            _pt_suffix    = "PDT" if _pdt_start <= _now < _pst_start else "PST"
            _time_pt_save = f"{_now.strftime('%-I:%M%p')} {_pt_suffix}"
        except Exception:
            _time_pt_save = report.get("generated_at", "")[11:16] + " UTC"

        _sess_lbl_sv = (
            _sv_sess.get("session_label") or
            _sv_sess.get("session") or ""
        )
        _lr_save = {
            "time_utc":         report.get("generated_at", "")[11:16],
            "time_pt":          _time_pt_save,
            "date":             report.get("generated_at", "")[:10],
            "pair":             report.get("pair", _pair_display),
            "price":            float(_sv_liq.get("current_price", 0) or 0),
            "bias":             report.get("overall_bias", ""),
            "conviction_score": report.get("decision", {}).get("conviction", _sv_conf),
            "quality":          _sv_setup.get("quality", ""),
            "primary_state":    (
                _sv_setup.get("primary_state") or
                report.get("primary_state", "")
            ),
            "setup_type":       _sv_setup.get("setup_type", ""),
            "action":           _sv_setup.get("action_now", ""),
            "intraday":         _sv_setup.get("intraday", ""),
            "swing":            _sv_setup.get("swing", ""),
            "best_expression":  _sv_setup.get("best_expression", ""),
            "wait_for":         _sv_setup.get("wait_for", ""),
            "session":          _sess_lbl_sv,
            "invalidation":     _sv_inv.get("invalidation", ""),
            "value_zone":       _sv_val.get("verdict", ""),
            "nearest_level":    _sv_liq.get("nearest_pool", ""),
            "grade":            _sv_grade,
            "risk_pct":         _sv_risk,
            "trigger_price":    None,
        }
        import re as _re
        _nums = _re.findall(r'1\.\d{3,4}', _lr_save["wait_for"])
        if _nums:
            _lr_save["trigger_price"] = float(_nums[0])

        try:
            from levels_context import get_key_levels
            _lr_save["levels"] = get_key_levels()
        except Exception:
            _lr_save["levels"] = {}

        try:
            import csv as _csv2
            from pathlib import Path as _cal_path
            _cal_file = _cal_path(__file__).parent / "calendar.csv"
            _upcoming_news = []
            if _cal_file.exists():
                _now_str = __import__('datetime').datetime.utcnow()
                with open(_cal_file, newline="", encoding="utf-8") as _cf:
                    for _row in _csv2.DictReader(_cf):
                        if _row.get("impact", "").lower() != "high":
                            continue
                        if _row.get("currency", "") not in ("GBP", "AUD"):
                            continue
                        try:
                            _ev_dt = __import__('datetime').datetime.strptime(
                                _row["time"][:16], "%Y-%m-%d %H:%M"
                            )
                            _mins = (_ev_dt - _now_str).total_seconds() / 60
                            if -15 <= _mins <= 120:
                                _upcoming_news.append({
                                    "event":    _row.get("event", ""),
                                    "currency": _row.get("currency", ""),
                                    "time":     _row["time"][:16],
                                    "minutes":  round(_mins),
                                })
                        except ValueError:
                            continue
            _lr_save["upcoming_news"] = _upcoming_news
        except Exception:
            _lr_save["upcoming_news"] = []

        _save_path = _Path3(__file__).parent / "last_run.json"
        _save_path.write_text(_json2.dumps(_lr_save, indent=2))
        save_run(_lr_save)
    except Exception as _save_err:
        import sys as _sys2
        print(f"  ⚠️  last_run.json save failed: {_save_err}", file=_sys2.stderr)

    print()
    print("=" * W)

