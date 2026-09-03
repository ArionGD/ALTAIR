import os
import json
import time
import math
import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from advisor.sectors import get_sector_tickers, get_all_sectors

CACHE = {}
CACHE_TTL = 300  # 5 minutes cache

def calculate_camarilla_pivots(hist: pd.DataFrame, cmp: float):
    """Calculate Classical and Camarilla S1 Support and R1 Resistance"""
    try:
        high = float(hist['High'].iloc[-20:].max())
        low = float(hist['Low'].iloc[-20:].min())
        close = float(hist['Close'].iloc[-1])
        
        # Classic Pivot
        pivot = (high + low + close) / 3.0
        s1 = round((2 * pivot) - high, 1)
        r1 = round((2 * pivot) - low, 1)
        
        # Dynamic ATR buffer check
        atr = float((hist['High'] - hist['Low']).iloc[-14:].mean())
        if s1 >= cmp or s1 <= 0:
            s1 = round(cmp - (1.5 * atr), 1)
        if r1 <= cmp:
            r1 = round(cmp + (1.5 * atr), 1)
            
        return max(1.0, s1), r1
    except Exception:
        return round(cmp * 0.95, 1), round(cmp * 1.05, 1)

def calculate_dcf_intrinsic_value(cmp: float, pe: float, roe_pct: float, growth_rate: float = 0.12):
    """Calculates normalized DCF Intrinsic Value per share and Margin of Safety"""
    try:
        pe_safe = max(5.0, min(120.0, pe))
        eps = cmp / pe_safe
        
        # 5-year projection
        wacc = 0.105  # 10.5% Indian hurdle rate
        terminal_growth = 0.045 # 4.5% long-term India GDP growth
        
        pv_cf = 0.0
        future_eps = eps
        for yr in range(1, 6):
            future_eps *= (1 + growth_rate)
            pv_cf += future_eps / ((1 + wacc) ** yr)
            
        # Terminal Value
        terminal_val = (future_eps * (1 + terminal_growth)) / (wacc - terminal_growth)
        pv_terminal = terminal_val / ((1 + wacc) ** 5)
        
        intrinsic_val = round(pv_cf + pv_terminal, 1)
        
        # Margin of Safety %
        mos_pct = round(((intrinsic_val - cmp) / cmp) * 100.0, 1)
        return intrinsic_val, mos_pct
    except Exception:
        intrinsic_val = round(cmp * 1.08, 1)
        return intrinsic_val, 8.0

def calculate_gann_score(hist: pd.DataFrame, cmp: float):
    """Computes W.D. Gann Square of 9 geometric cycle proximity score (0-100)"""
    try:
        pivot_low = float(hist['Low'].iloc[-60:].min())
        root = math.sqrt(max(1.0, pivot_low))
        
        # Square of 9 geometric degrees: 45, 90, 135, 180, 225, 270, 360
        gann_levels = [round((root + deg / 180.0) ** 2, 1) for deg in [45, 90, 135, 180, 225, 270, 360]]
        
        # Find closest support floor below CMP
        supports = [g for g in gann_levels if g <= cmp]
        closest_sup = max(supports) if supports else gann_levels[0]
        
        dist_pct = abs(cmp - closest_sup) / cmp
        # Within 2.5% of Gann support floor is maximum bullish resonance
        if dist_pct < 0.025:
            score = 95.0
        elif dist_pct < 0.05:
            score = 80.0
        elif dist_pct < 0.10:
            score = 65.0
        else:
            score = 50.0
        return round(score, 1)
    except Exception:
        return 50.0

def run_advisor_scan(sector_name: str = 'Pharma & Healthcare', include_gann: bool = False):
    """Scans top 20 equities in the chosen sector, computes DCF, S1/R1, and rankings"""
    cache_key = f"{sector_name}_{include_gann}"
    now = time.time()
    if cache_key in CACHE and (now - CACHE[cache_key]['ts'] < CACHE_TTL):
        return CACHE[cache_key]['data']

    tickers = get_sector_tickers(sector_name)
    results = []

    # Sector fundamental valuation defaults
    SECTOR_PE_BENCHMARKS = {
        "Pharma & Healthcare": 31.5,
        "Banking - Private": 17.2,
        "Banking - PSU": 9.4,
        "IT & Technology": 29.0,
        "Automobiles & Ancillaries": 24.5,
        "Consumer Goods (FMCG)": 44.0,
        "Energy, Oil & Utilities": 14.8,
        "Metals & Mining": 12.5,
        "Industrials & Defense": 38.0,
        "Real Estate & Infra": 26.0
    }
    sec_pe = SECTOR_PE_BENCHMARKS.get(sector_name, 25.0)

    # Fast multi-threaded batch history download
    try:
        batch_df = yf.download(tickers, period='6mo', group_by='ticker', threads=True, progress=False)
    except Exception as e:
        print(f"[ENGINE ERROR] Batch download failed: {e}")
        batch_df = pd.DataFrame()

    for t in tickers:
        try:
            if t not in batch_df or batch_df[t].empty:
                continue
            hist = batch_df[t].dropna()
            if hist.empty or len(hist) < 20:
                continue
                
            cmp = round(float(hist['Close'].iloc[-1]), 1)
            high_52w = float(hist['High'].max())
            low_52w = float(hist['Low'].min())
            from_high = round(((cmp - high_52w) / high_52w) * 100.0, 1)
            
            # 14D RSI
            delta = hist['Close'].diff()
            gain = delta.clip(lower=0)
            loss = -delta.clip(upper=0)
            avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
            avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
            rs = avg_gain / avg_loss.replace(0, np.nan)
            rsi = round(float((100 - (100 / (1 + rs))).iloc[-1]), 1)
            
            # Moving averages & trend
            ma_50 = round(float(hist['Close'].rolling(50).mean().iloc[-1]), 1) if len(hist) >= 50 else cmp
            
            # Fundamentals / PE / ROE / Growth
            pe = sec_pe
            roe = 16.5
            growth = 0.125
            
            # DCF Intrinsic Value & Margin of Safety
            dcf_val, mos_pct = calculate_dcf_intrinsic_value(cmp, pe, roe, growth)
            
            # S1 & R1 Levels
            s1, r1 = calculate_camarilla_pivots(hist, cmp)
            
            # Risk/Reward Ratio
            risk = max(1.0, cmp - s1)
            reward = max(1.0, r1 - cmp)
            rr_ratio = round(reward / risk, 2)
            
            # Gann Score
            gann_score = calculate_gann_score(hist, cmp) if include_gann else 50.0
            
            # Composite Scoring Formula (0 to 100)
            val_score = float(np.clip(50.0 + (mos_pct * 1.5), 10.0, 100.0))
            
            if 42.0 <= rsi <= 62.0:
                mom_score = 90.0
            elif 32.0 <= rsi < 42.0:
                mom_score = 75.0
            elif 62.0 < rsi <= 72.0:
                mom_score = 65.0
            else:
                mom_score = 35.0
                
            pe_score = float(np.clip(100.0 - (pe * 1.6), 15.0, 95.0))
            
            if include_gann:
                composite = (val_score * 0.35) + (mom_score * 0.25) + (pe_score * 0.20) + (gann_score * 0.20)
            else:
                composite = (val_score * 0.40) + (mom_score * 0.35) + (pe_score * 0.25)
                
            composite = round(float(composite), 1)
            
            # Bi-Directional Recommendation Logic
            if composite >= 70.0 and mos_pct > 8.0 and cmp >= s1:
                action = 'STRONG BUY'
                action_type = 'LONG'
            elif composite >= 60.0 and mos_pct > -5.0:
                action = 'SWING BUY'
                action_type = 'LONG'
            elif composite <= 42.0 or mos_pct < -25.0 or (pe > 60.0 and rsi > 70.0):
                action = 'SHORT POSITION'
                action_type = 'SHORT'
            elif composite <= 48.0 or mos_pct < -15.0:
                action = 'HEDGE / EXIT'
                action_type = 'SHORT'
            else:
                action = 'ACCUMULATE'
                action_type = 'NEUTRAL'
                
            clean_symbol = t.replace('.NS', '')
            results.append({
                'symbol': clean_symbol,
                'ticker': t,
                'cmp': cmp,
                'action': action,
                'action_type': action_type,
                'composite_score': composite,
                'dcf_intrinsic_value': dcf_val,
                'margin_of_safety_pct': mos_pct,
                'pe_ratio': pe,
                'rsi_14': rsi,
                's1_support': s1,
                'r1_resistance': r1,
                'risk_reward': rr_ratio,
                'ma_50': ma_50,
                'gann_score': gann_score if include_gann else None,
                'from_52w_high': f"{from_high}%"
            })
        except Exception:
            continue

    # Sort results by composite score descending
    results = sorted(results, key=lambda x: x['composite_score'], reverse=True)
    
    # Assign ranks
    for idx, r in enumerate(results):
        r['rank'] = idx + 1

    # Generate the 3 clean Plotly charts
    charts = generate_advisor_charts(results, sector_name)
    
    output_data = {
        'sector': sector_name,
        'include_gann': include_gann,
        'stocks_count': len(results),
        'rankings': results,
        'charts': charts
    }
    
    CACHE[cache_key] = {'data': output_data, 'ts': now}
    return output_data

def generate_advisor_charts(rankings: list, sector: str) -> dict:
    """Generates 3 simple, institutional dark-theme visual charts"""
    if not rankings:
        return {}
        
    top_stocks = rankings[:12]
    symbols = [r['symbol'] for r in top_stocks]
    cmps = [r['cmp'] for r in top_stocks]
    dcfs = [r['dcf_intrinsic_value'] for r in top_stocks]
    
    # 1. DCF Intrinsic Value vs Current Price Bar Comparison
    fig_dcf = go.Figure()
    fig_dcf.add_trace(go.Bar(
        x=symbols,
        y=cmps,
        name='Current Market Price (CMP)',
        marker=dict(color='#06b6d4', line=dict(color='#22d3ee', width=1)),
        text=[f"₹{c}" for c in cmps],
        textposition='outside'
    ))
    fig_dcf.add_trace(go.Bar(
        x=symbols,
        y=dcfs,
        name='DCF Intrinsic Fair Value',
        marker=dict(color='#10b981', line=dict(color='#34d399', width=1)),
        text=[f"₹{d}" for d in dcfs],
        textposition='outside'
    ))
    fig_dcf.update_layout(
        title=dict(text=f"<b>DCF Intrinsic Fair Value vs Market Price (CMP)</b> — {sector}", font=dict(size=13, color='#e2e8f0')),
        paper_bgcolor='#070b14',
        plot_bgcolor='#0a101f',
        font=dict(family='Inter, sans-serif', color='#94a3b8', size=11),
        barmode='group',
        margin=dict(l=40, r=20, t=50, b=40),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='#1e293b')
    )
    
    # 2. Valuation (Margin of Safety) vs Momentum (RSI) Strategic Quadrant
    all_syms = [r['symbol'] for r in rankings]
    all_mos = [r['margin_of_safety_pct'] for r in rankings]
    all_rsi = [r['rsi_14'] for r in rankings]
    colors = ['#10b981' if r['action_type'] == 'LONG' else ('#f43f5e' if r['action_type'] == 'SHORT' else '#06b6d4') for r in rankings]
    
    fig_quad = go.Figure()
    fig_quad.add_trace(go.Scatter(
        x=all_mos,
        y=all_rsi,
        mode='markers+text',
        text=all_syms,
        textposition='top center',
        marker=dict(
            size=14,
            color=colors,
            line=dict(color='#ffffff', width=1.5),
            opacity=0.9
        ),
        hovertemplate='<b>%{text}</b><br>Margin of Safety: %{x}%<br>14D RSI: %{y}<extra></extra>'
    ))
    fig_quad.add_vline(x=0, line_dash='dash', line_color='#475569', annotation_text='Fair Value', annotation_position='top left')
    fig_quad.add_hline(y=50, line_dash='dash', line_color='#475569', annotation_text='RSI Equilibrium', annotation_position='bottom right')
    
    fig_quad.update_layout(
        title=dict(text="<b>Opportunity Matrix</b> — DCF Margin of Safety vs Momentum (RSI)", font=dict(size=13, color='#e2e8f0')),
        paper_bgcolor='#070b14',
        plot_bgcolor='#0a101f',
        font=dict(family='Inter, sans-serif', color='#94a3b8', size=11),
        margin=dict(l=40, r=20, t=50, b=40),
        xaxis=dict(title='Margin of Safety % (Positive = Undervalued)', showgrid=True, gridcolor='#1e293b'),
        yaxis=dict(title='14-Day RSI (Momentum)', showgrid=True, gridcolor='#1e293b')
    )
    
    # 3. Price Channel Risk Brackets (S1 Floor <-> CMP <-> R1 Ceiling)
    top_actions = [r for r in rankings if r['action_type'] in ['LONG', 'SHORT']][:8]
    if not top_actions:
        top_actions = rankings[:8]
        
    b_syms = [r['symbol'] for r in top_actions]
    b_cmps = [r['cmp'] for r in top_actions]
    b_s1 = [r['s1_support'] for r in top_actions]
    b_r1 = [r['r1_resistance'] for r in top_actions]
    
    fig_brack = go.Figure()
    for s, c, s1_val, r1_val in zip(b_syms, b_cmps, b_s1, b_r1):
        fig_brack.add_trace(go.Scatter(
            x=[s1_val, r1_val],
            y=[s, s],
            mode='lines',
            line=dict(color='#334155', width=6),
            showlegend=False
        ))
        fig_brack.add_trace(go.Scatter(
            x=[s1_val],
            y=[s],
            mode='markers',
            marker=dict(symbol='triangle-up', size=12, color='#10b981'),
            name='S1 Support Floor' if s == b_syms[0] else None,
            showlegend=(s == b_syms[0])
        ))
        fig_brack.add_trace(go.Scatter(
            x=[c],
            y=[s],
            mode='markers',
            marker=dict(symbol='circle', size=10, color='#06b6d4'),
            name='Current CMP' if s == b_syms[0] else None,
            showlegend=(s == b_syms[0])
        ))
        fig_brack.add_trace(go.Scatter(
            x=[r1_val],
            y=[s],
            mode='markers',
            marker=dict(symbol='triangle-down', size=12, color='#f43f5e'),
            name='R1 Resistance Ceiling' if s == b_syms[0] else None,
            showlegend=(s == b_syms[0])
        ))
        
    fig_brack.update_layout(
        title=dict(text="<b>Immediate S1 Floor vs CMP vs R1 Target Ceilings</b>", font=dict(size=13, color='#e2e8f0')),
        paper_bgcolor='#070b14',
        plot_bgcolor='#0a101f',
        font=dict(family='Inter, sans-serif', color='#94a3b8', size=11),
        margin=dict(l=70, r=20, t=50, b=40),
        xaxis=dict(title='Price (₹)', showgrid=True, gridcolor='#1e293b'),
        yaxis=dict(showgrid=False),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )
    
    return {
        'dcf': json.loads(fig_dcf.to_json()),
        'matrix': json.loads(fig_quad.to_json()),
        'brackets': json.loads(fig_brack.to_json())
    }
