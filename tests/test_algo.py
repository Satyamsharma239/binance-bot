import pytest
import pandas as pd
import pandas_ta as ta

def test_rsi_calculation():
    """Test that RSI calculates correctly using pandas-ta."""
    # Create mock closing prices
    data = {
        'close': [40, 42, 45, 48, 50, 49, 47, 45, 42, 40, 38, 35, 30, 25, 20, 15]
    }
    df = pd.DataFrame(data)
    
    # Calculate RSI
    df['RSI'] = df.ta.rsi(length=14)
    
    # Assert RSI column was created
    assert 'RSI' in df.columns
    # Assert there are NaN values at the beginning due to the 14-period rolling window
    assert pd.isna(df['RSI'].iloc[0])
    # Assert the final RSI is calculated (not NaN)
    assert not pd.isna(df['RSI'].iloc[-1])
    
    # With this straight downward trend, the final RSI should be quite low (oversold)
    assert df['RSI'].iloc[-1] < 35

def test_macd_and_bb():
    """Test MACD and Bollinger Bands calculation for V3 Confluence."""
    # Need at least 50 points for reliable MACD(26,9) calculation
    data = {
        'close': [40, 42, 45, 48, 50, 49, 47, 45, 42, 40, 38, 35, 30, 25, 20, 15, 12, 10, 8, 5, 
                  4, 3, 2, 3, 4, 5, 6, 8, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75,
                  80, 85, 90, 95, 100, 105, 110, 115]
    }
    df = pd.DataFrame(data)
    
    df.ta.macd(fast=12, slow=26, signal=9, append=True)
    df.ta.bbands(length=20, std=2, append=True)
    
    assert 'MACD_12_26_9' in df.columns
    assert 'BBL_20_2.0_2.0' in df.columns
    assert not pd.isna(df['MACD_12_26_9'].iloc[-1])

