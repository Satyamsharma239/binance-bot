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
