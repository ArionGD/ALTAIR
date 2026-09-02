import os
import math
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json

SECTOR_NICHE_MAP = {
    "Adani Group": ["ADANIPORTS.NS", "AWL.NS", "ATGL.NS", "ADANIGREEN.NS", "ADANIENT.NS", "ADANIPOWER.NS"],
    "Auto - 2-Wheelers": ["BAJAJ-AUTO.NS", "TVSMOTOR.NS", "HEROMOTOCO.NS", "EICHERMOT.NS"],
    "Auto - 4W & CV": ["TATAMOTORS.NS", "M&M.NS", "MARUTI.NS", "ASHOKLEY.NS", "BHARATFORG.NS"],
    "Banking - Private": ["HDFCBANK.NS", "ICICIBANK.NS", "KOTAKBANK.NS", "AXISBANK.NS", "INDUSINDBK.NS"],
    "Banking - PSU": ["SBIN.NS", "BANKBARODA.NS", "PNB.NS", "CANBK.NS", "UNIONBANK.NS"],
    "Pharma & Healthcare": ["SUNPHARMA.NS", "CIPLA.NS", "DRREDDY.NS", "DIVISLAB.NS", "LUPIN.NS", "TORNTPHARM.NS"],
    "FMCG & Consumer": ["ITC.NS", "HINDUNILVR.NS", "NESTLEIND.NS", "BRITANNIA.NS", "TATACONSUM.NS", "DABUR.NS", "COLPAL.NS"],
    "Energy & Power": ["RELIANCE.NS", "ONGC.NS", "NTPC.NS", "POWERGRID.NS", "TATAPOWER.NS"]
}

def scan_subfield(field_name: str = "Auto - 2-Wheelers"):
    tickers = SECTOR_NICHE_MAP.get(field_name, SECTOR_NICHE_MAP["Auto - 2-Wheelers"])
    results = []
    
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="1y")
            if hist.empty or len(hist) < 50:
                continue
                
            close = float(hist['Close'].iloc[-1])
            ma_20 = float(hist['Close'].rolling(20).mean().iloc[-1])
            ma_50 = float(hist['Close'].rolling(50).mean().iloc[-1])
            ma_200 = float(hist['Close'].rolling(200).mean().iloc[-1]) if len(hist) >= 200 else ma_50
            
            delta = hist['Close'].diff()
            gain = delta.clip(lower=0)
            loss = -delta.clip(upper=0)
            avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
            avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
            rs = avg_gain / avg_loss.replace(0, np.nan)
            rsi = float((100 - (100 / (1 + rs))).iloc[-1])
            
            tr = pd.concat([
                hist['High'] - hist['Low'],
                (hist['High'] - hist['Close'].shift()).abs(),
                (hist['Low'] - hist['Close'].shift()).abs()
            ], axis=1).max(axis=1)
            atr = float(tr.rolling(14).mean().iloc[-1])
            
            info = t.info or {}
            de = float(info.get('debtToEquity') or 25.0)
            roe = float((info.get('returnOnEquity') or 0.15) * 100)
            op_margin = float((info.get('operatingMargins') or 0.12) * 100)
            
            fund_score = 50.0
            if de < 50: fund_score += 20
            elif de < 100: fund_score += 10
            if roe > 15: fund_score += 15
            if op_margin > 12: fund_score += 15
            fund_score = min(100.0, max(10.0, fund_score))
            
            tech_score = 50.0
            if close > ma_50: tech_score += 20
            if ma_50 > ma_200: tech_score += 15
            if close > ma_20: tech_score += 15
            tech_score = min(100.0, max(10.0, tech_score))
            
            if 45 <= rsi <= 65: rsi_score = 90.0
            elif rsi < 35: rsi_score = 80.0
            elif rsi > 70: rsi_score = 40.0
            else: rsi_score = 60.0
                
            sqrt_p = math.sqrt(close)
            sq9_support = (sqrt_p - 0.25) ** 2
            sq9_dist = abs((close - sq9_support) / close) * 100
            gann_score = 90.0 if sq9_dist < 1.5 else (80.0 if sq9_dist < 3.0 else 65.0)
            
            swing_index = (0.25 * fund_score) + (0.30 * tech_score) + (0.20 * rsi_score) + (0.25 * gann_score)
            target = round(close + (2.5 * atr), 2)
            stop_loss = round(close - (1.5 * atr), 2)
            target_pct = round(((target - close) / close) * 100, 1)
            sl_pct = round(((close - stop_loss) / close) * 100, 1)
            rrr = round((target - close) / (close - stop_loss), 1) if (close - stop_loss) > 0 else 1.7
            
            verdict = "STRONG BUY" if swing_index >= 82 else ("BUY ON DIP" if swing_index >= 68 else "NEUTRAL / WATCH")
            
            results.append({
                'Company': ticker.replace('.NS', ''),
                'Ticker': ticker,
                'CMP': round(close, 2),
                'Swing_Index': round(swing_index, 1),
                'Action': verdict,
                'Target_Price': target,
                'Target_Gain': f"+{target_pct}%",
                'Stop_Loss': stop_loss,
                'Risk_Buffer': f"-{sl_pct}%",
                'RR_Ratio': f"1:{rrr}",
                'RSI_14': round(rsi, 1),
                'Fund_Pts': round(0.25 * fund_score, 1),
                'Tech_Pts': round(0.30 * tech_score, 1),
                'RSI_Pts': round(0.20 * rsi_score, 1),
                'Gann_Pts': round(0.25 * gann_score, 1)
            })
        except Exception:
            continue
            
    df_ranked = pd.DataFrame(results).sort_values(by='Swing_Index', ascending=False).reset_index(drop=True)
    df_ranked.index = [f"#{i+1}" for i in range(len(df_ranked))]
    df_ranked.index.name = "Rank"
    
    # Plotly Stacked Bar + Range Bullet Chart
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=False, vertical_spacing=0.18, row_heights=[0.55, 0.45],
        subplot_titles=(f"4-Pillar Score Breakdown ({field_name})", "Trade Target vs Stop Loss Brackets")
    )
    comps = df_ranked['Company'].tolist()
    fig.add_trace(go.Bar(name='Fundamentals', y=comps, x=df_ranked['Fund_Pts'], orientation='h', marker=dict(color='#10b981')), row=1, col=1)
    fig.add_trace(go.Bar(name='Trend Momentum', y=comps, x=df_ranked['Tech_Pts'], orientation='h', marker=dict(color='#3b82f6')), row=1, col=1)
    fig.add_trace(go.Bar(name='RSI Sweet-Spot', y=comps, x=df_ranked['RSI_Pts'], orientation='h', marker=dict(color='#a855f7')), row=1, col=1)
    fig.add_trace(go.Bar(name='Gann Proximity', y=comps, x=df_ranked['Gann_Pts'], orientation='h', marker=dict(color='#f59e0b')), row=1, col=1)
    
    for idx, row in df_ranked.iterrows():
        c = row['Company']
        fig.add_trace(go.Scatter(
            x=[row['CMP'], row['Target_Price']], y=[c, c], mode='lines+markers',
            line=dict(color='#22c55e', width=4), marker=dict(size=[7, 11], symbol=['circle', 'triangle-right'], color='#22c55e'),
            showlegend=False
        ), row=2, col=1)
        fig.add_trace(go.Scatter(
            x=[row['Stop_Loss'], row['CMP']], y=[c, c], mode='lines+markers',
            line=dict(color='#ef4444', width=4), marker=dict(size=[11, 7], symbol=['triangle-left', 'circle'], color=['#ef4444', '#22c55e']),
            showlegend=False
        ), row=2, col=1)
        
    fig.update_layout(barmode='stack', height=650, template="plotly_dark", margin=dict(l=20, r=20, t=50, b=20))
    return df_ranked.reset_index().to_dict(orient='records'), json.loads(fig.to_json())

def nifty_gann_analysis():
    nifty_raw = yf.download("^NSEI", period="1y", interval="1d", progress=False)
    if isinstance(nifty_raw.columns, pd.MultiIndex):
        nifty_raw.columns = [col[0] for col in nifty_raw.columns]
    
    nifty = nifty_raw.copy()
    nifty['MA_50'] = nifty['Close'].rolling(50).mean()
    nifty['MA_200'] = nifty['Close'].rolling(200).mean()
    
    pivot_window = 15
    nifty['Is_High'] = (nifty['High'] == nifty['High'].rolling(window=pivot_window*2+1, center=True).max())
    nifty['Is_Low'] = (nifty['Low'] == nifty['Low'].rolling(window=pivot_window*2+1, center=True).min())
    
    pivots = []
    for dt, row in nifty[nifty['Is_High']].iterrows():
        pivots.append({'date': dt, 'type': 'HIGH', 'price': float(row['High'])})
    for dt, row in nifty[nifty['Is_Low']].iterrows():
        pivots.append({'date': dt, 'type': 'LOW', 'price': float(row['Low'])})
    pivots.sort(key=lambda x: x['date'])
    
    latest_pivot = pivots[-1] if pivots else {'price': float(nifty['Close'].iloc[-1]), 'type': 'HIGH'}
    sqrt_p = math.sqrt(latest_pivot['price'])
    sq9 = {
        'R_90': round((sqrt_p + 0.5) ** 2, 2),
        'R_45': round((sqrt_p + 0.25) ** 2, 2),
        'S_45': round((sqrt_p - 0.25) ** 2, 2),
        'S_90': round((sqrt_p - 0.5) ** 2, 2)
    }
    
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=nifty.index.strftime('%Y-%m-%d'), open=nifty['Open'], high=nifty['High'], low=nifty['Low'], close=nifty['Close'],
        name="NIFTY 50"
    ))
    fig.add_trace(go.Scatter(x=nifty.index.strftime('%Y-%m-%d'), y=nifty['MA_50'], line=dict(color='#f59e0b', width=1.5), name="50 DMA"))
    fig.add_trace(go.Scatter(x=nifty.index.strftime('%Y-%m-%d'), y=nifty['MA_200'], line=dict(color='#06b6d4', width=1.5), name="200 DMA"))
    
    fig.add_hline(y=sq9['R_90'], line_dash="dash", line_color="rgba(239, 68, 68, 0.6)", annotation_text=f"Gann +90° R ({sq9['R_90']})")
    fig.add_hline(y=sq9['S_90'], line_dash="dash", line_color="rgba(34, 197, 94, 0.6)", annotation_text=f"Gann -90° S ({sq9['S_90']})")
    fig.update_layout(title="NIFTY 50: W.D. Gann Cycle & Square of 9 Geometric Levels", height=500, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=20, r=20, t=50, b=20))
    
    summary = {
        'current_price': round(float(nifty['Close'].iloc[-1]), 2),
        'ma_50': round(float(nifty['MA_50'].iloc[-1]), 2),
        'ma_200': round(float(nifty['MA_200'].iloc[-1]), 2),
        'latest_pivot_price': round(latest_pivot['price'], 2),
        'latest_pivot_type': latest_pivot['type'],
        'gann_resistance_90': sq9['R_90'],
        'gann_support_90': sq9['S_90']
    }
    return summary, json.loads(fig.to_json())

def precious_metals_analysis():
    raw = yf.download(["GC=F", "SI=F"], period="1y", interval="1d", progress=False)['Close'].dropna()
    gold_cmp = float(raw['GC=F'].iloc[-1])
    silver_cmp = float(raw['SI=F'].iloc[-1])
    gsr = round(gold_cmp / silver_cmp, 2)
    
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, subplot_titles=("Gold ($) & Silver ($)", f"Gold/Silver Ratio: {gsr}"))
    fig.add_trace(go.Scatter(x=raw.index.strftime('%Y-%m-%d'), y=raw['GC=F'], line=dict(color='#fbbf24', width=2), name="Gold"), row=1, col=1)
    fig.add_trace(go.Scatter(x=raw.index.strftime('%Y-%m-%d'), y=raw['GC=F'].rolling(50).mean(), line=dict(color='#3b82f6', width=1.5, dash='dot'), name="Gold 50 DMA"), row=1, col=1)
    
    fig.add_trace(go.Scatter(x=raw.index.strftime('%Y-%m-%d'), y=raw['GC=F'] / raw['SI=F'], line=dict(color='#a855f7', width=2), name="GSR"), row=2, col=1)
    fig.add_hline(y=80, line_dash="dot", line_color="#22c55e", annotation_text="Silver Undervalued (>80)", row=2, col=1)
    fig.update_layout(height=550, template="plotly_dark", margin=dict(l=20, r=20, t=50, b=20))
    
    summary = {
        'gold_cmp': f"${gold_cmp:.2f}",
        'silver_cmp': f"${silver_cmp:.2f}",
        'gold_silver_ratio': gsr,
        'ratio_status': "Silver Historically Undervalued" if gsr > 75 else "Balanced Valuation",
        'silver_verdict': "STRONG BUY (High Beta Catch-up)" if gsr > 75 else "BUY ON DIP"
    }
    return summary, json.loads(fig.to_json())

def value_quality_macro_scan():
    MACRO_UNIVERSE = {
        "Pharma": ["SUNPHARMA.NS", "CIPLA.NS", "DRREDDY.NS", "DIVISLAB.NS", "LUPIN.NS", "TORNTPHARM.NS"],
        "BFSI": ["HDFCBANK.NS", "ICICIBANK.NS", "KOTAKBANK.NS", "AXISBANK.NS", "SBIN.NS", "BANKBARODA.NS"],
        "FMCG": ["ITC.NS", "HINDUNILVR.NS", "NESTLEIND.NS", "BRITANNIA.NS", "DABUR.NS", "COLPAL.NS"]
    }
    
    macro_results = []
    for sector, tickers in MACRO_UNIVERSE.items():
        for ticker in tickers:
            try:
                t = yf.Ticker(ticker)
                hist = t.history(period="1y")
                if hist.empty or len(hist) < 50:
                    continue
                close = float(hist['Close'].iloc[-1])
                high_52w = float(hist['High'].max())
                discount_ath = ((high_52w - close) / high_52w) * 100
                
                # RSI
                delta = hist['Close'].diff()
                gain = delta.clip(lower=0)
                loss = -delta.clip(upper=0)
                avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
                avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
                rs = avg_gain / avg_loss.replace(0, np.nan)
                rsi = float((100 - (100 / (1 + rs))).iloc[-1])
                
                tr = pd.concat([hist['High'] - hist['Low'], (hist['High'] - hist['Close'].shift()).abs(), (hist['Low'] - hist['Close'].shift()).abs()], axis=1).max(axis=1)
                atr = float(tr.rolling(14).mean().iloc[-1])
                
                info = t.info or {}
                pe = float(info.get('trailingPE') or info.get('forwardPE') or 28.0)
                de = float(info.get('debtToEquity') or 20.0)
                roe = float((info.get('returnOnEquity') or 0.16) * 100)
                
                q_score = 75.0 if de < 30 or "BFSI" in sector else 60.0
                v_score = 85.0 if 12 <= discount_ath <= 35 else 65.0
                m_score = 80.0 if 30 <= rsi <= 55 else 60.0
                
                score = (0.40 * q_score) + (0.35 * v_score) + (0.25 * m_score)
                target = round(close + (2.5 * atr), 2)
                stop_loss = round(close - (1.5 * atr), 2)
                target_pct = round(((target - close) / close) * 100, 1)
                sl_pct = round(((close - stop_loss) / close) * 100, 1)
                
                macro_results.append({
                    'Company': ticker.replace('.NS', ''),
                    'Sector': sector,
                    'CMP': round(close, 2),
                    'Value_Score': round(score, 1),
                    'Verdict': 'PRIME VALUE SWING' if score >= 80 else 'QUALITY ACCUMULATE',
                    'Target_Price': target,
                    'Target_Gain': f"+{target_pct}%",
                    'Stop_Loss': stop_loss,
                    'Risk_Buffer': f"-{sl_pct}%",
                    'RSI_14': round(rsi, 1),
                    'Discount_from_ATH': f"-{round(discount_ath, 1)}%",
                    'PE_Ratio': round(pe, 1)
                })
            except Exception:
                continue
                
    df_val = pd.DataFrame(macro_results).sort_values(by='Value_Score', ascending=False).reset_index(drop=True)
    df_val.index = [f"#{i+1}" for i in range(len(df_val))]
    
    top8 = df_val.head(8)
    fig = go.Figure()
    for idx, r in top8.iterrows():
        c = r['Company']
        fig.add_trace(go.Scatter(x=[r['CMP'], r['Target_Price']], y=[c, c], mode='lines+markers', line=dict(color='#10b981', width=4), marker=dict(size=[7, 11], symbol=['circle', 'triangle-right'], color='#10b981'), name=c, showlegend=False))
        fig.add_trace(go.Scatter(x=[r['Stop_Loss'], r['CMP']], y=[c, c], mode='lines+markers', line=dict(color='#ef4444', width=4), marker=dict(size=[11, 7], symbol=['triangle-left', 'circle'], color=['#ef4444', '#10b981']), showlegend=False))
        
    fig.update_layout(title="Top Undervalued FMCG, BFSI & Pharma Compounders", height=450, template="plotly_dark", margin=dict(l=20, r=20, t=50, b=20))
    return df_val.head(10).reset_index().to_dict(orient='records'), json.loads(fig.to_json())

def run_stock_screener(
    sector_filter: str = "All",
    min_rsi: float = 0.0,
    max_rsi: float = 100.0,
    max_pe: float = 120.0,
    max_debt: float = 300.0,
    min_roe: float = 0.0
):
    """
    Universal Stock Screener across all sector universes.
    Filters by RSI, Valuation P/E, Debt-to-Equity, and ROE.
    """
    candidates = []
    
    # Build list of (sector, ticker)
    universe = []
    for sec, tickers in SECTOR_NICHE_MAP.items():
        if sector_filter == "All" or sector_filter.lower() in sec.lower():
            for tk in tickers:
                universe.append((sec, tk))
                
    for sec, tk in universe:
        try:
            t = yf.Ticker(tk)
            hist = t.history(period="1y")
            if hist.empty or len(hist) < 50:
                continue
                
            close = float(hist['Close'].iloc[-1])
            ath = float(hist['High'].max())
            discount_ath = ((ath - close) / ath) * 100
            
            delta = hist['Close'].diff()
            gain = delta.clip(lower=0)
            loss = -delta.clip(upper=0)
            avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
            avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
            rs = avg_gain / avg_loss.replace(0, np.nan)
            rsi = float((100 - (100 / (1 + rs))).iloc[-1])
            
            info = t.info or {}
            pe = float(info.get('trailingPE') or info.get('forwardPE') or 28.0)
            de = float(info.get('debtToEquity') or 20.0)
            roe = float((info.get('returnOnEquity') or 0.15) * 100)
            
            # Apply user filters
            if not (min_rsi <= rsi <= max_rsi):
                continue
            if pe > max_pe:
                continue
            if de > max_debt and "Bank" not in sec:
                continue
            if roe < min_roe:
                continue
                
            # Composite Scoring: Value (30%), Momentum (30%), Quality (25%), Discount (15%)
            v_sub = max(0.0, 100.0 - (pe * 1.5))
            m_sub = 90.0 if 30 <= rsi <= 55 else (70.0 if rsi < 30 else 50.0)
            q_sub = min(100.0, roe * 3.5) if "Bank" in sec else (90.0 if de < 35 else 60.0)
            d_sub = min(100.0, discount_ath * 2.5)
            
            score = round((0.30 * v_sub) + (0.30 * m_sub) + (0.25 * q_sub) + (0.15 * d_sub), 1)
            
            verdict = "STRONG ACCUMULATE" if score >= 78 else ("SWING BUY" if score >= 65 else "NEUTRAL / WATCH")
            
            candidates.append({
                'Symbol': tk.replace('.NS', ''),
                'Sector': sec,
                'CMP': round(close, 2),
                'Quant_Score': score,
                'Verdict': verdict,
                'PE_Ratio': round(pe, 1),
                'RSI_14': round(rsi, 1),
                'Debt_Equity': round(de, 1) if "Bank" not in sec else "N/A (Bank)",
                'ROE_Pct': f"{round(roe, 1)}%",
                'From_52W_High': f"-{round(discount_ath, 1)}%"
            })
        except Exception:
            continue
            
    if not candidates:
        return [], None
        
    df_screen = pd.DataFrame(candidates).sort_values(by='Quant_Score', ascending=False).reset_index(drop=True)
    df_screen.index = [f"#{i+1}" for i in range(len(df_screen))]
    top_picks = df_screen.head(22).copy()
    
    # ─── CHART 1: Modern Clean 2D Quadrant Matrix ──────────────────────────────────────────
    fig_quad = go.Figure()
    
    # Custom hoverdata arrays
    custom_data = []
    for _, row in top_picks.iterrows():
        custom_data.append([
            row['Sector'],
            row['CMP'],
            row['Verdict'],
            row['ROE_Pct'],
            row['Debt_Equity'],
            row['From_52W_High']
        ])
        
    # Scatter trace with glowing bubbles
    fig_quad.add_trace(go.Scatter(
        x=top_picks['PE_Ratio'],
        y=top_picks['RSI_14'],
        mode='markers+text',
        text=top_picks['Symbol'],
        textposition='top right',
        textfont=dict(family='Inter, sans-serif', size=11, color='#e2e8f0'),
        customdata=custom_data,
        marker=dict(
            size=[max(16, min(36, float(str(r).replace('%', '')) * 1.15)) for r in top_picks['ROE_Pct']],
            color=top_picks['Quant_Score'],
            colorscale=[
                [0.0, '#0284c7'],    # Ocean Cyan
                [0.4, '#06b6d4'],    # Vibrant Cyan
                [0.7, '#3b82f6'],    # Electric Blue
                [1.0, '#10b981']     # Emerald Glow
            ],
            showscale=True,
            colorbar=dict(
                title=dict(text="Quant Score", font=dict(color="#94a3b8", size=11)),
                tickfont=dict(color="#94a3b8", size=10),
                thickness=12,
                len=0.85,
                bgcolor="rgba(0,0,0,0)",
                bordercolor="rgba(255,255,255,0.1)"
            ),
            line=dict(width=1.5, color='rgba(255, 255, 255, 0.85)')
        ),
        hovertemplate=(
            "<b>%{text}</b> • %{customdata[0]}<br>"
            "───────────────────────────<br>"
            "• Current Price: <b>₹%{customdata[1]}</b><br>"
            "• Composite Score: <b>%{marker.color:.1f} / 100</b> (%{customdata[2]})<br>"
            "• Valuation P/E: <b>%{x:.1f}x</b><br>"
            "• 14D RSI: <b>%{y:.1f}</b><br>"
            "• Return on Equity: <b>%{customdata[3]}</b><br>"
            "• Debt/Equity: <b>%{customdata[4]}</b><br>"
            "• Gap from 52W High: <b>%{customdata[5]}</b><br>"
            "<extra></extra>"
        )
    ))
    
    # 4 Subtle Shaded Quadrant Backgrounds
    max_x = max(55.0, float(top_picks['PE_Ratio'].max()) + 8.0)
    shapes = [
        # Top-Left: High Momentum Value Breakout
        dict(type="rect", x0=0, x1=25, y0=50, y1=85, fillcolor="rgba(16, 185, 129, 0.04)", line_width=0, layer="below"),
        # Bottom-Left: Deep Value Accumulation Zone
        dict(type="rect", x0=0, x1=25, y0=20, y1=50, fillcolor="rgba(6, 182, 212, 0.06)", line_width=0, layer="below"),
        # Top-Right: Premium Growth / Expensive Momentum
        dict(type="rect", x0=25, x1=max_x, y0=50, y1=85, fillcolor="rgba(245, 158, 11, 0.03)", line_width=0, layer="below"),
        # Bottom-Right: Stagnant / High P/E Consolidation
        dict(type="rect", x0=25, x1=max_x, y0=20, y1=50, fillcolor="rgba(239, 68, 68, 0.03)", line_width=0, layer="below"),
        # Threshold Lines
        dict(type="line", x0=25, x1=25, y0=20, y1=85, line=dict(color="#06b6d4", width=1.5, dash="dot")),
        dict(type="line", x0=0, x1=max_x, y0=40, y1=40, line=dict(color="#10b981", width=1.5, dash="dot")),
        dict(type="line", x0=0, x1=max_x, y0=70, y1=70, line=dict(color="#ef4444", width=1.5, dash="dot"))
    ]
    
    # Elegant annotations for quadrants & thresholds
    annotations = [
        dict(x=12.5, y=47, text="💎 ACCUMULATION ZONE (RSI < 50 & PE < 25)", showarrow=False, font=dict(size=10, color="rgba(6, 182, 212, 0.55)")),
        dict(x=12.5, y=78, text="⚡ MOMENTUM VALUE (PE < 25)", showarrow=False, font=dict(size=10, color="rgba(16, 185, 129, 0.5)")),
        dict(x=max_x - 10, y=78, text="⚠️ EXPENSIVE MOMENTUM", showarrow=False, font=dict(size=10, color="rgba(245, 158, 11, 0.45)")),
        dict(x=max_x - 10, y=25, text="📉 HIGH PE / CONSOLIDATING", showarrow=False, font=dict(size=10, color="rgba(239, 68, 68, 0.45)")),
        dict(x=max_x - 2, y=41, text="RSI 40 (Oversold)", showarrow=False, font=dict(size=9, color="#10b981"), xanchor="right"),
        dict(x=max_x - 2, y=71, text="RSI 70 (Overbought)", showarrow=False, font=dict(size=9, color="#ef4444"), xanchor="right"),
        dict(x=25.5, y=83, text="PE 25 (Value Cap)", showarrow=False, font=dict(size=9, color="#06b6d4"), xanchor="left")
    ]
    
    fig_quad.update_layout(
        title=dict(
            text="<b>2D Quadrant Matrix</b> • Valuation (P/E) vs Momentum (14D RSI)",
            font=dict(size=14, color="#f8fafc", family="Inter, sans-serif")
        ),
        shapes=shapes,
        annotations=annotations,
        xaxis=dict(
            title=dict(text="Price-to-Earnings Ratio (P/E)", font=dict(color="#94a3b8", size=11)),
            gridcolor="rgba(255, 255, 255, 0.05)",
            zerolinecolor="rgba(255, 255, 255, 0.1)",
            tickfont=dict(color="#94a3b8", size=10),
            range=[0, max_x]
        ),
        yaxis=dict(
            title=dict(text="14-Day RSI (Momentum Indicator)", font=dict(color="#94a3b8", size=11)),
            gridcolor="rgba(255, 255, 255, 0.05)",
            zerolinecolor="rgba(255, 255, 255, 0.1)",
            tickfont=dict(color="#94a3b8", size=10),
            range=[20, 85]
        ),
        plot_bgcolor="#070b14",
        paper_bgcolor="#060911",
        height=500,
        margin=dict(l=45, r=35, t=55, b=45)
    )

    # ─── CHART 2: Quant Composite Score Leaderboard (Ranked Horizontal Bars) ───────────────
    df_sorted_bars = top_picks.sort_values(by='Quant_Score', ascending=True).tail(16)
    
    fig_rank = go.Figure()
    bar_colors = [
        '#10b981' if score >= 78 else ('#06b6d4' if score >= 68 else ('#3b82f6' if score >= 58 else '#f59e0b'))
        for score in df_sorted_bars['Quant_Score']
    ]
    
    fig_rank.add_trace(go.Bar(
        x=df_sorted_bars['Quant_Score'],
        y=df_sorted_bars['Symbol'],
        orientation='h',
        text=[f"{s:.1f} • {v}" for s, v in zip(df_sorted_bars['Quant_Score'], df_sorted_bars['Verdict'])],
        textposition='inside',
        insidetextanchor='start',
        textfont=dict(color='#ffffff', size=11, family='Inter, sans-serif'),
        marker=dict(
            color=bar_colors,
            line=dict(color='rgba(255, 255, 255, 0.25)', width=1)
        ),
        customdata=[[sec, cmp, pe, rsi, roe] for sec, cmp, pe, rsi, roe in zip(
            df_sorted_bars['Sector'], df_sorted_bars['CMP'], df_sorted_bars['PE_Ratio'],
            df_sorted_bars['RSI_14'], df_sorted_bars['ROE_Pct']
        )],
        hovertemplate=(
            "<b>%{y}</b> (%{customdata[0]})<br>"
            "───────────────────────────<br>"
            "• Composite Score: <b>%{x:.1f} / 100</b><br>"
            "• Price: <b>₹%{customdata[1]}</b><br>"
            "• P/E Ratio: <b>%{customdata[2]}x</b><br>"
            "• 14D RSI: <b>%{customdata[3]}</b><br>"
            "• ROE: <b>%{customdata[4]}</b><br>"
            "<extra></extra>"
        )
    ))
    
    fig_rank.add_vline(x=78, line_dash="dash", line_color="#10b981", annotation_text="Strong Accumulate (Score ≥ 78)", annotation_position="top right")
    fig_rank.add_vline(x=65, line_dash="dot", line_color="#06b6d4", annotation_text="Swing Buy (Score ≥ 65)", annotation_position="top left")
    
    fig_rank.update_layout(
        title=dict(
            text="<b>Quant Score Leaderboard</b> • Ranked Overall Composite Strength",
            font=dict(size=14, color="#f8fafc", family="Inter, sans-serif")
        ),
        xaxis=dict(
            title=dict(text="Composite Quant Score (0 to 100)", font=dict(color="#94a3b8", size=11)),
            gridcolor="rgba(255, 255, 255, 0.05)",
            tickfont=dict(color="#94a3b8", size=10),
            range=[30, 100]
        ),
        yaxis=dict(
            tickfont=dict(color="#f1f5f9", size=11, family='Inter, sans-serif')
        ),
        plot_bgcolor="#070b14",
        paper_bgcolor="#060911",
        height=500,
        margin=dict(l=75, r=35, t=55, b=45)
    )

    # ─── CHART 3: Valuation vs ROE Quality Frontier ─────────────────────────────────────────
    fig_front = go.Figure()
    
    fig_front.add_trace(go.Scatter(
        x=top_picks['PE_Ratio'],
        y=[float(str(r).replace('%', '')) for r in top_picks['ROE_Pct']],
        mode='markers+text',
        text=top_picks['Symbol'],
        textposition='top center',
        textfont=dict(color='#e2e8f0', size=11, family='Inter, sans-serif'),
        marker=dict(
            size=[max(14, min(34, s * 0.35)) for s in top_picks['Quant_Score']],
            color=top_picks['RSI_14'],
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(
                title=dict(text="14D RSI", font=dict(color="#94a3b8", size=11)),
                thickness=12,
                len=0.85,
                bgcolor="rgba(0,0,0,0)"
            ),
            line=dict(color='#38bdf8', width=1.5)
        ),
        customdata=[[s, c, v] for s, c, v in zip(top_picks['Sector'], top_picks['CMP'], top_picks['Verdict'])],
        hovertemplate=(
            "<b>%{text}</b> (%{customdata[0]})<br>"
            "• P/E Ratio: <b>%{x:.1f}x</b><br>"
            "• ROE %: <b>%{y:.1f}%</b><br>"
            "• Price: <b>₹%{customdata[1]}</b><br>"
            "• 14D RSI: <b>%{marker.color:.1f}</b><br>"
            "<extra></extra>"
        )
    ))
    
    # Golden Sweet Spot Box: PE < 25, ROE > 15%
    fig_front.add_shape(
        type="rect", x0=0, x1=25, y0=15, y1=50,
        fillcolor="rgba(16, 185, 129, 0.08)", line=dict(color="#10b981", width=1.5, dash="dash")
    )
    fig_front.add_annotation(
        x=12.5, y=35, text="🌟 ALPHA SWEET-SPOT<br>(Low PE & High ROE)",
        showarrow=False, font=dict(color="#10b981", size=11, family="Inter, sans-serif")
    )
    
    fig_front.update_layout(
        title=dict(
            text="<b>Capital Efficiency Frontier</b> • Valuation (P/E) vs Return on Equity (ROE %)",
            font=dict(size=14, color="#f8fafc", family="Inter, sans-serif")
        ),
        xaxis=dict(
            title=dict(text="Price-to-Earnings Ratio (P/E)", font=dict(color="#94a3b8", size=11)),
            gridcolor="rgba(255, 255, 255, 0.05)",
            tickfont=dict(color="#94a3b8", size=10)
        ),
        yaxis=dict(
            title=dict(text="Return on Equity (ROE %)", font=dict(color="#94a3b8", size=11)),
            gridcolor="rgba(255, 255, 255, 0.05)",
            tickfont=dict(color="#94a3b8", size=10)
        ),
        plot_bgcolor="#070b14",
        paper_bgcolor="#060911",
        height=500,
        margin=dict(l=45, r=35, t=55, b=45)
    )

    # ─── CHART 4: Sector Heatmap & Strength Aggregation ────────────────────────────────────
    sec_summary = df_screen.groupby('Sector').agg({
        'Quant_Score': 'mean',
        'RSI_14': 'mean',
        'PE_Ratio': 'mean',
        'Symbol': 'count'
    }).reset_index().rename(columns={'Symbol': 'Count'})
    
    fig_sec = go.Figure()
    fig_sec.add_trace(go.Bar(
        x=sec_summary['Sector'],
        y=sec_summary['Quant_Score'],
        name="Avg Quant Score",
        text=[f"{s:.1f}" for s in sec_summary['Quant_Score']],
        textposition='outside',
        textfont=dict(color='#06b6d4', size=11),
        marker=dict(color='#06b6d4', opacity=0.85)
    ))
    fig_sec.add_trace(go.Bar(
        x=sec_summary['Sector'],
        y=sec_summary['RSI_14'],
        name="Avg 14D RSI",
        text=[f"{r:.1f}" for r in sec_summary['RSI_14']],
        textposition='outside',
        textfont=dict(color='#a855f7', size=11),
        marker=dict(color='#a855f7', opacity=0.85)
    ))
    
    fig_sec.update_layout(
        title=dict(
            text="<b>Sector Breakdown</b> • Average Quant Score vs Average Momentum (RSI)",
            font=dict(size=14, color="#f8fafc", family="Inter, sans-serif")
        ),
        barmode='group',
        xaxis=dict(tickfont=dict(color="#e2e8f0", size=11), gridcolor="rgba(255, 255, 255, 0.05)"),
        yaxis=dict(
            title=dict(text="Score / RSI Level", font=dict(color="#94a3b8", size=11)),
            gridcolor="rgba(255, 255, 255, 0.05)",
            tickfont=dict(color="#94a3b8", size=10),
            range=[0, 100]
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            font=dict(color="#94a3b8", size=11)
        ),
        plot_bgcolor="#070b14",
        paper_bgcolor="#060911",
        height=500,
        margin=dict(l=45, r=35, t=65, b=45)
    )

    multi_charts = {
        "quadrant": json.loads(fig_quad.to_json()),
        "ranking": json.loads(fig_rank.to_json()),
        "frontier": json.loads(fig_front.to_json()),
        "sector": json.loads(fig_sec.to_json())
    }

    return df_screen.head(15).reset_index().to_dict(orient='records'), multi_charts["quadrant"], multi_charts


