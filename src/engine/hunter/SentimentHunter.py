import yfinance as yf
import pandas as pd

class SentimentHunter:
    """
    ALTAIR: News-Based Forensic Sentiment Module.
    Scavenges for 'Fear' and 'Fragility' keywords in the market news flow.
    """

    def __init__(self):
        # Keywords that indicate a 'Strike' or 'Weak Link'
        self.fear_keywords = [
            "loss", "debt", "down", "decrease", "worry", "crash", "default", 
            "pledge", "selling", "investigation", "probe", "sell-off", 
            "underperform", "missed", "downgrade", "pressure", "lower", 
            "fall", "slide", "tumble", "slip", "plunge", "weak", "soften", 
            "slow", "drag", "lag", "cut", "trim", "caution"
        ]
        
        # Keywords that indicate an 'Iron Fortress' (Strong)
        self.resilient_keywords = [
            "profit", "dividend", "buyback", "growth", "record", "expand", 
            "strong", "upgrade", "outperform", "resilient", "surplus", 
            "higher", "rise", "jump", "climb", "surge", "beat", "positive", 
            "outlook", "guidance"
        ]

    def hunt_ticker_sentiment(self, ticker_symbol):
        """
        Analyzes the latest 10 news items for a ticker.
        Returns a score from 0-100 (High = High Fear/Fragility).
        """
        print(f"[*] Hunting Sentiment Forensics for {ticker_symbol}...")
        ticker = yf.Ticker(ticker_symbol)
        news = ticker.news
        
        if not news:
            print(f"    [!] No news found for {ticker_symbol}. Neutral sentiment.")
            return 50.0 # Neutral

        fear_count = 0
        resilient_count = 0
        total_items = len(news[:10]) # Look at last 10 news items

        for item in news[:10]:
            title = item.get('title', '').lower()
            
            # Count fear-inducing words
            for word in self.fear_keywords:
                if word in title:
                    fear_count += 1
            
            # Count resilience words
            for word in self.resilient_keywords:
                if word in title:
                    resilient_count += 1

        # Calculate Logic:
        # Fear + 10, Resilient - 10
        raw_sentiment = 50 + (fear_count * 10) - (resilient_count * 10)
        
        # Normalize between 0 and 100
        final_score = max(0, min(100, raw_sentiment))
        
        print(f"    [+] Sentiment Score: {final_score} (Fear Context: {fear_count}, Strength Context: {resilient_count})")
        return round(float(final_score), 2)

if __name__ == "__main__":
    hunter = SentimentHunter()
    # Test on a 'Glass Pillar'
    hunter.hunt_ticker_sentiment("NYKAA.NS")
    # Test on an 'Iron Fortress'
    hunter.hunt_ticker_sentiment("TCS.NS")
