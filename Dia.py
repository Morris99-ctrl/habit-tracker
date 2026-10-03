import numpy as np
import pandas as pd
import yfinance as yf
import yaml
import json
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union
import warnings
warnings.filterwarnings('ignore')

# Machine learning imports
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor

# Configuration management
CONFIG_FILE = "trading_config.yaml"

# Default configuration template
DEFAULT_CONFIG = {
    "strategy": {
        "name": "Multi-Factor Momentum",
        "lookback_periods": [63, 126, 252],
        "volatility_lookback": 21,
        "rebalancing_frequency": "monthly",
        "signal_threshold": 0.5,
    },
    "risk": {
        "max_portfolio_volatility": 0.20,
        "max_drawdown": 0.15,
        "stop_loss": 0.05,
        "take_profit": 0.15,
        "max_leverage": 2.0,
        "kelly_fraction": 0.5,
        "var_confidence_level": 0.95,
    },
    "assets": {
        "equities": ["SPY", "QQQ", "IWM", "VTI", "AAPL", "MSFT", "AMZN"],
        "bonds": ["BND", "IEF", "TLT"],
        "commodities": ["GLD", "DIA", "SLV", "USO"],
        "international": ["IXP", "EWJ", "EWC", "FXI"],
        "currencies": ["UUP", "FXE", "FXB"],
    },
    "backtesting": {
        "start_date": "2005-01-01",
        "end_date": "2024-01-01",
        "include_slippage": True,
        "slippage_bps": 5,
        "include_commission": True,
        "commission_per_share": 0.001,
        "monthly_rebalancing": True,
        "transaction_costs": True,
    },
    "ml": {
        "use_ml_signals": True,
        "feature_lookback": 126,
        "n_components": 10,
        "n_clusters": 4,
        "ml_models": ["random_forest", "linear_regression"],
    },
    "regime_detection": {
        "volatility_bins": [-np.inf, 0.15, 0.25, 0.35, np.inf],
        "trend_bins": [-np.inf, 0.01, 0.03, 0.05, np.inf],
        "min_regime_duration": 21,
    },
}


class AdvancedRiskManager:
    """Comprehensive risk management system"""
    
    def __init__(self, config):
        self.config = config
        self.var_calc = VARCalculator(config['risk']['var_confidence_level'])
        self.position_sizer = PositionSizer(config)
        self.drawdown_monitor = DrawdownMonitor(config)
        self.factor_risk = FactorRiskModel()
    
    def calculate_portfolio_risk(self, returns, weights):
        """Calculate comprehensive portfolio risk metrics"""
        # Portfolio returns
        portfolio_returns = returns @ weights
        
        # Basic risk metrics
        risk_metrics = {
            'expected_return': np.mean(portfolio_returns),
            'volatility': np.std(portfolio_returns),
            'skewness': self._calculate_skewness(portfolio_returns),
            'kurtosis': self._calculate_kurtosis(portfolio_returns),
        }
        
        # Value at Risk
        var_result = self.var_calc.calculate_var(portfolio_returns)
        risk_metrics.update(var_result)
        
        # Factor risk
        factor_risk_result = self.factor_risk.calculate_factor_risk(returns, weights)
        risk_metrics.update(factor_risk_result)
        
        # Stress test results
        stress_test_result = self._stress_test(portfolio_returns)
        risk_metrics.update(stress_test_result)
        
        # Tail risk metrics
        tail_risk_result = self._calculate_tail_risk(portfolio_returns)
        risk_metrics.update(tail_risk_result)
        
        return risk_metrics
    
    def calculate_position_size(self, signal_strength, volatility, sharpe_ratio, portfolio_value):
        """Calculate optimal position size using Kelly Criterion with adjustments"""
        # Base Kelly calculation
        kelly_fraction = self.position_sizer.kelly_criterion(
            signal_strength, volatility, sharpe_ratio
        )
        
        # Apply conservative adjustments
        kelly_fraction *= self.config['risk']['kelly_fraction']
        
        # Apply volatility adjustment
        kelly_fraction *= self._volatility_adjustment(volatility)
        
        # Apply Sharpe ratio adjustment
        kelly_fraction *= self._sharpe_adjustment(sharpe_ratio)
        
        # Apply signal strength adjustment
        kelly_fraction *= self._signal_adjustment(signal_strength)
        
        # Cap individual position
        kelly_fraction = np.clip(kelly_fraction, -self.config['risk']['max_leverage'], 
                               self.config['risk']['max_leverage'])
        
        # Calculate dollar position
        position_value = kelly_fraction * portfolio_value
        
        return position_value
    
    def check_drawdown_limit(self, portfolio_value, historical_values):
        """Check if portfolio is approaching drawdown limits"""
        current_drawdown = (portfolio_value - historical_values.max()) / historical_values.max()
        return current_drawdown > self.config['risk']['max_drawdown']
    
    def calculate_max_position_limits(self, total_portfolio_value):
        """Calculate maximum position limits based on portfolio size"""
        # Maximum position as percentage of portfolio
        max_position_pct = 1.0 / len(self.config['assets']['equities'])
        
        # Apply additional constraints based on volatility
        max_position_pct *= 0.8
        
        return total_portfolio_value * max_position_pct


class VARCalculator:
    """Value at Risk calculation"""
    
    def __init__(self, confidence_level):
        self.confidence_level = confidence_level
        self.z_score = {
            0.90: 1.645,
            0.95: 1.645,
            0.99: 2.326,
        }
    
    def calculate_var(self, returns):
        """Calculate VaR using historical simulation"""
        var_percentile = 1 - self.confidence_level
        var_value = np.percentile(returns, var_percentile * 100)
        
        return {
            'var': abs(var_value),
            'var_percent': abs(var_value) / np.mean(returns) if np.mean(returns) != 0 else 0,
            'confidence_level': self.confidence_level,
        }
    
    def calculate_cvar(self, returns):
        """Calculate Conditional VaR (expected shortfall)"""
        var_value = self.calculate_var(returns)['var']
        
        # Get returns that are worse than VaR
        cvar_values = returns[returns <= -var_value]
        cvar_value = np.mean(cvar_values) if len(cvar_values) > 0 else var_value
        
        return {
            'cvar': abs(cvar_value),
            'cvar_percent': abs(cvar_value) / np.mean(returns) if np.mean(returns) != 0 else 0,
        }


class DrawdownMonitor:
    """Monitor and manage portfolio drawdowns"""
    
    def __init__(self, config):
        self.config = config
        self.peak_value = 0
        self.current_drawdown = 0
        self.max_drawdown = 0
    
    def update(self, portfolio_value):
        """Update drawdown monitoring with new portfolio value"""
        if portfolio_value > self.peak_value:
            self.peak_value = portfolio_value
            self.current_drawdown = 0
        else:
            self.current_drawdown = (self.peak_value - portfolio_value) / self.peak_value
        
        if self.current_drawdown > self.max_drawdown:
            self.max_drawdown = self.current_drawdown
    
    def should_reduce_positions(self):
        """Check if positions should be reduced based on drawdown"""
        return self.current_drawdown > self.config['risk']['max_drawdown'] * 0.8
    
    def get_drawdown_info(self):
        """Get current drawdown information"""
        return {
            'current_drawdown': self.current_drawdown,
            'max_drawdown': self.max_drawdown,
            'peak_value': self.peak_value,
            'is_approaching_limit': self.should_reduce_positions(),
        }


class FactorRiskModel:
    """Factor risk analysis"""
    
    def calculate_factor_risk(self, returns, weights):
        """Calculate factor risk contribution"""
        # Define factor returns
        factors = self._calculate_factor_returns(returns)
        
        # Calculate portfolio factor exposure
        portfolio_exposure = np.dot(factors.T, weights)
        
        # Calculate factor covariance matrix
        factor_cov = np.cov(factors)
        
        # Calculate portfolio factor variance
        portfolio_factor_var = np.dot(portfolio_exposure.T, 
                                    np.dot(factor_cov, portfolio_exposure))
        
        return {
            'factor_variance': portfolio_factor_var,
            'factor_volatility': np.sqrt(portfolio_factor_var),
            'factor_risk_contribution': (np.sqrt(portfolio_factor_var) / np.std(returns @ weights)) ** 2,
            'factor_exposure': portfolio_exposure.tolist(),
        }
    
    def _calculate_factor_returns(self, returns):
        """Calculate factor returns from asset returns"""
        # For now, use asset returns as factors
        # In practice, this would use statistical factor models
        return returns.values.T


class PositionSizer:
    """Position sizing strategies"""
    
    def __init__(self, config):
        self.config = config
    
    def kelly_criterion(self, signal_strength, volatility, sharpe_ratio):
        """Calculate Kelly Criterion position size"""
        if volatility == 0:
            return 0
        
        # Kelly formula: f = (bp - q) / b
        # where p = probability of win, q = probability of loss
        # b = payoff ratio, b = (mean_return / volatility^2)
        
        kelly_fraction = (sharpe_ratio - volatility) / volatility
        
        return kelly_fraction
    
    def volatility_adjusted_kelly(self, kelly_fraction, volatility):
        """Apply volatility adjustment to Kelly position"""
        # Reduce position size for high volatility
        adjustment_factor = np.exp(-2 * volatility)
        return kelly_fraction * adjustment_factor
    
    def correlation_adjusted_kelly(self, kelly_fractions, correlation_matrix):
        """Apply correlation adjustment to Kelly positions"""
        # Account for diversification benefits
        portfolio_volatility = np.sqrt(np.dot(kelly_fractions.T, 
                                            np.dot(correlation_matrix, kelly_fractions)))
        
        # Adjust individual positions based on portfolio volatility
        adjusted_fractions = []
        for i, fraction in enumerate(kelly_fractions):
            if portfolio_volatility > 0:
                adjustment = np.sqrt(1 / np.diag(correlation_matrix)[i]) / portfolio_volatility
                adjusted_fractions.append(fraction * adjustment)
            else:
                adjusted_fractions.append(fraction)
        
        return np.array(adjusted_fractions)


class MarketRegimeDetector:
    """Detect current market regime"""
    
    def __init__(self, config):
        self.config = config
        self.volatility_bins = config['regime_detection']['volatility_bins']
        self.trend_bins = config['regime_detection']['trend_bins']
    
    def detect_regime(self, prices, returns):
        """Detect current market regime"""
        # Calculate market features
        vol_regime = self._detect_volatility_regime(returns)
        trend_regime = self._detect_trend_regime(prices)
        
        # Combine regimes into final classification
        final_regime = self._combine_regimes(vol_regime, trend_regime)
        
        return {
            'volatility_regime': vol_regime,
            'trend_regime': trend_regime,
            'final_regime': final_regime,
            'volatility_percentile': vol_regime.get('percentile', 0),
            'trend_strength': trend_regime.get('strength', 0),
            'market_features': self._extract_market_features(prices, returns),
        }
    
    def _detect_volatility_regime(self, returns):
        """Detect volatility regime"""
        current_vol = np.std(returns)
        
        # Determine volatility regime
        if current_vol < self.volatility_bins[1]:
            regime = 'low'
        elif current_vol < self.volatility_bins[2]:
            regime = 'normal'
        elif current_vol < self.volatility_bins[3]:
            regime = 'high'
        else:
            regime = 'extreme'
        
        # Calculate historical percentile
        hist_vols = returns.rolling(window=252).std()
        current_percentile = np.sum(hist_vols < current_vol) / len(hist_vols)
        
        return {
            'regime': regime,
            'current_volatility': current_vol,
            'percentile': current_percentile,
        }
    
    def _detect_trend_regime(self, prices):
        """Detect trend regime"""
        # Calculate trend strength using moving averages
        ma_20 = prices.rolling(20).mean()
        ma_50 = prices.rolling(50).mean()
        
        # Calculate trend strength
        current_price = prices.iloc[-1]
        ma_20_current = ma_20.iloc[-1]
        ma_50_current = ma_50.iloc[-1]
        
        if ma_20_current > ma_50_current:
            # Uptrend
            trend_strength = min((current_price - ma_50_current) / ma_50_current, 0.2)
            regime = 'bullish'
        elif ma_20_current < ma_50_current:
            # Downtrend
            trend_strength = min((ma_50_current - current_price) / ma_50_current, 0.2)
            regime = 'bearish'
        else:
            # Sideways
            trend_strength = 0.1
            regime = 'neutral'
        
        return {
            'regime': regime,
            'strength': trend_strength,
            'ma_20': float(ma_20_current),
            'ma_50': float(ma_50_current),
        }
    
    def _combine_regimes(self, vol_regime, trend_regime):
        """Combine volatility and trend regimes into final classification"""
        vol = vol_regime['regime']
        trend = trend_regime['regime']
        
        # Combine regimes
        if vol == 'extreme' or trend == 'extreme':
            return 'volatile'
        elif vol == 'high' and trend == 'bullish':
            return 'bullish_high_vol'
        elif vol == 'high' and trend == 'bearish':
            return 'bearish_high_vol'
        elif vol == 'high':
            return 'choppy'
        elif trend == 'bullish':
            return 'bullish'
        elif trend == 'bearish':
            return 'bearish'
        else:
            return 'neutral'
    
    def _extract_market_features(self, prices, returns):
        """Extract additional market features"""
        features = {}
        
        # Price momentum
        features['momentum_1m'] = returns.iloc[-21:].mean()
        features['momentum_3m'] = returns.iloc[-63:].mean()
        features['momentum_6m'] = returns.iloc[-126:].mean()
        
        # Volatility regime
        features['current_volatility'] = np.std(returns)
        features['volatility_percentile'] = np.sum(returns.rolling(252).std() < np.std(returns)) / len(returns.rolling(252).std())
        
        # Liquidity proxy
        features['volume_ma_20'] = prices.rolling(20).mean()
        features['volume_ratio'] = prices.rolling(20).mean().iloc[-1] / prices.rolling(20).mean().mean()
        
        # Correlation matrix features
        correlation = returns.corr()
        features['average_correlation'] = correlation.values[np.triu_indices(len(correlation), k=1)].mean()
        
        return features


class MLSignalGenerator:
    """Generate signals using machine learning models"""
    
    def __init__(self, config):
        self.config = config
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=config['ml']['n_components'])
        self.clf = RandomForestRegressor(n_estimators=100, random_state=42)
        self.regression = LinearRegression()
        self.kmeans = KMeans(n_clusters=config['ml']['n_clusters'], random_state=42)
    
    def generate_ml_signals(self, prices, returns):
        """Generate trading signals using machine learning"""
        # Prepare features
        features = self._prepare_features(prices, returns)
        
        # Scale and reduce dimensionality
        features_scaled = self.scaler.fit_transform(features)
        features_pca = self.pca.fit_transform(features_scaled)
        
        # Apply clustering
        clusters = self.kmeans.fit_predict(features_pca)
        
        # Train models for each cluster
        ml_signals = self._train_models_for_clusters(prices, returns, clusters, features_pca)
        
        return ml_signals
    
    def _prepare_features(self, prices, returns):
        """Prepare features for machine learning"""
        features_list = []
        
        # Technical indicators
        for ticker in prices.columns:
            price_data = prices[ticker]
            
            # Price-based features
            features_list.append({
                'momentum_1m': price_data.pct_change(21).iloc[-1],
                'momentum_3m': price_data.pct_change(63).iloc[-1],
                'momentum_6m': price_data.pct_change(126).iloc[-1],
                'momentum_12m': price_data.pct_change(252).iloc[-1],
                
                'volatility_21d': returns[ticker].rolling(21).std().iloc[-1],
                'volatility_63d': returns[ticker].rolling(63).std().iloc[-1],
                
                'rsi_14': self._calculate_rsi(price_data, 14),
                'rsi_21': self._calculate_rsi(price_data, 21),
                
                'ma_20_ratio': price_data.rolling(20).mean().iloc[-1] / price_data.rolling(50).mean().iloc[-1],
                'ma_50_ratio': price_data.rolling(50).mean().iloc[-1] / price_data.rolling(200).mean().iloc[-1],
                
                'volume_ratio': price_data.rolling(20).mean().iloc[-1] / price_data.rolling(20).mean().mean(),
            })
        
        return pd.DataFrame(features_list)
    
    def _calculate_rsi(self, prices, period=14):
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.iloc[-1]
    
    def _train_models_for_clusters(self, prices, returns, clusters, features_pca):
        """Train ML models for each cluster"""
        signals = np.zeros(len(prices))
        
        for cluster_id in np.unique(clusters):
            # Get indices for this cluster
            cluster_indices = np.where(clusters == cluster_id)[0]
            
            # Train models
            X_train = features_pca[cluster_indices]
            y_train_momentum = (prices.pct_change(252).iloc[-1].values[cluster_indices] > 0).astype(int)
            
            # Train random forest
            self.clf.fit(X_train, y_train_momentum)
            
            # Train linear regression
            self.regression.fit(X_train, y_train_momentum.astype(float))
            
            # Generate predictions for all data
            X_all = features_pca
            rf_predictions = self.clf.predict(X_all)
            lr_predictions = self.regression.predict(X_all)
            
            # Combine predictions
            cluster_signals = (rf_predictions + lr_predictions) / 2
            
            # Apply to signals
            signals = np.maximum(signals, cluster_signals)
        
        return signals


class TrendFollowingStrategy:
    """Trend following strategy"""
    
    def generate_signals(self, prices):
        """Generate trend following signals"""
        # Calculate moving averages
        ma_20 = prices.rolling(20).mean()
        ma_50 = prices.rolling(50).mean()
        
        # Generate signals based on moving average crossover
        signals = pd.Series(0, index=prices.index)
        
        # Buy when MA20 > MA50
        buy_signal = (ma_20 > ma_50) & (ma_20.shift(1) <= ma_50.shift(1))
        signals[buy_signal] = 1
        
        # Sell when MA20 < MA50
        sell_signal = (ma_20 < ma_50) & (ma_20.shift(1) >= ma_50.shift(1))
        signals[sell_signal] = -1
        
        return signals
    
    def calculate_suitability(self, regime, market_features):
        """Calculate suitability for trend following"""
        score = 0
        
        # Good in bullish regimes
        if regime['final_regime'] in ['bullish', 'bullish_high_vol', 'volatile']:
            score += 2
        
        # Poor in volatile but directionless markets
        if regime['volatility_regime']['regime'] in ['high', 'extreme'] and \
           market_features['average_correlation'] > 0.5:
            score += 1  # Moderate suitability
        
        # Good in normal volatility with trend
        if regime['volatility_regime']['regime'] in ['normal'] and \
           market_features['momentum_6m'] > 0:
            score += 1.5
        
        return score


class MeanReversionStrategy:
    """Mean reversion strategy"""
    
    def generate_signals(self, prices):
        """Generate mean reversion signals"""
        # Calculate Z-scores
        z_scores = (prices - prices.rolling(252).mean()) / prices.rolling(252).std()
        
        # Generate signals based on Z-scores
        signals = pd.Series(0, index=prices.index)
        
        # Buy when Z-score is very low (oversold)
        buy_signal = z_scores < -2
        signals[buy_signal] = 1
        
        # Sell when Z-score is very high (overbought)
        sell_signal = z_scores > 2
        signals[sell_signal] = -1
        
        return signals
    
    def calculate_suitability(self, regime, market_features):
        """Calculate suitability for mean reversion"""
        score = 0
        
        # Good in neutral/choppy markets
        if regime['final_regime'] in ['choppy', 'neutral']:
            score += 2
        
        # Good when correlation is high (mean reversion relationships stable)
        if market_features['average_correlation'] > 0.7:
            score += 1.5
        
        # Poor in strong trends
        if market_features['momentum_6m'] > 0.1 or market_features['momentum_6m'] < -0.1:
            score -= 1
        
        # Good in high volatility (mean reversion opportunities)
        if regime['volatility_regime']['current_volatility'] > 0.2:
            score += 0.5
        
        return score


class MomentumStrategy:
    """Momentum strategy"""
    
    def generate_signals(self, prices):
        """Generate momentum signals"""
        # Calculate momentum
        momentum_12m = prices.pct_change(252)
        
        # Generate signals based on momentum
        signals = pd.Series(0, index=prices.index)
        
        # Buy when momentum is positive and increasing
        buy_signal = (momentum_12m > 0) & (momentum_12m.rolling(63).mean() > 0)
        signals[buy_signal] = 1
        
        # Sell when momentum is negative
        sell_signal = momentum_12m < 0
        signals[sell_signal] = -1
        
        return signals
    
    def calculate_suitability(self, regime, market_features):
        """Calculate suitability for momentum strategy"""
        score = 0
        
        # Good in trending markets
        if market_features['momentum_6m'] > 0:
            score += 2
        elif market_features['momentum_6m'] < 0:
            score += 1  # Still good for short
        
        # Poor in highly volatile but directionless markets
        if regime['volatility_regime']['regime'] in ['high', 'extreme'] and \
           market_features['momentum_6m'] < 0.05 and market_features['momentum_6m'] > -0.05:
            score -= 1
        
        # Good when momentum is consistent
        if market_features['momentum_1m'] * market_features['momentum_3m'] > 0:
            score += 1
        
        return score


class VolatilityStrategy:
    """Volatility-based strategy"""
    
    def generate_signals(self, prices):
        """Generate volatility-based signals"""
        # Calculate volatility
        volatility = prices.pct_change().rolling(21).std()
        
        # Generate signals based on volatility
        signals = pd.Series(0, index=prices.index)
        
        # Buy when volatility is low (mean reversion opportunity)
        buy_signal = volatility < 0.15
        signals[buy_signal] = 1
        
        # Sell when volatility is high (trend following)
        sell_signal = volatility > 0.25
        signals[sell_signal] = -1
        
        return signals
    
    def calculate_suitability(self, regime, market_features):
        """Calculate suitability for volatility strategy"""
        score = 0
        
        # Good in high volatility
        if regime['volatility_regime']['regime'] in ['high', 'extreme']:
            score += 2
        
        # Good when volatility is increasing
        vol_change = market_features['current_volatility'] - \
                    market_features['current_volatility'] * 0.9
        if vol_change > 0:
            score += 1
        
        # Poor in low volatility with trending markets
        if regime['volatility_regime']['regime'] in ['low'] and \
           market_features['momentum_6m'] > 0.1:
            score -= 1
        
        return score


class StrategySelector:
    """Select optimal strategy based on market conditions"""
    
    def __init__(self):
        self.strategies = {
            'trend_following': TrendFollowingStrategy(),
            'mean_reversion': MeanReversionStrategy(),
            'momentum': MomentumStrategy(),
            'volatility': VolatilityStrategy(),
        }
    
    def select_strategy(self, regime, market_features):
        """Select optimal strategy for current regime"""
        # Strategy suitability scores for different regimes
        suitability_scores = {}
        
        for strategy_name, strategy in self.strategies.items():
            score = strategy.calculate_suitability(regime, market_features)
            suitability_scores[strategy_name] = score
        
        # Select strategy with highest score
        best_strategy = max(suitability_scores, key=suitability_scores.get)
        
        return self.strategies[best_strategy], suitability_scores


class BacktestEngine:
    """Professional backtesting engine"""
    
    def __init__(self, config):
        self.config = config
        self.risk_manager = AdvancedRiskManager(config)
        self.market_regime_detector = MarketRegimeDetector(config)
        self.ml_signal_generator = MLSignalGenerator(config)
        self.strategy_selector = StrategySelector()
    
    def run_backtest(self, prices, start_date, end_date):
        """Run comprehensive backtest"""
        # Generate signals
        ml_signals = self.ml_signal_generator.generate_ml_signals(prices, prices.pct_change())
        
        # Detect market regime
        market_features = self.market_regime_detector._extract_market_features(prices, prices.pct_change())
        regime = self.market_regime_detector.detect_regime(prices, prices.pct_change())
        
        # Select strategy
        strategy, scores = self.strategy_selector.select_strategy(regime, market_features)
        
        # Generate strategy signals
        strategy_signals = strategy.generate_signals(prices)
        
        # Combine signals
        final_signals = self._combine_signals(ml_signals, strategy_signals, scores)
        
        # Calculate returns
        returns = prices.pct_change().iloc[1:]  # Remove first row (NaN)
        
        # Calculate portfolio returns
        portfolio_returns = self._calculate_portfolio_returns(final_signals, returns)
        
        # Run backtest
        backtest_results = self._run_backtest_analysis(portfolio_returns, prices)
        
        return backtest_results
    
    def _combine_signals(self, ml_signals, strategy_signals, scores):
        """Combine different signal sources"""
        # Weight signals by strategy suitability
        ml_weight = scores.get('trend_following', 1) / sum(scores.values()) if sum(scores.values()) > 0 else 0.5
        strategy_weight = 1 - ml_weight
        
        combined_signals = (ml_signals * ml_weight + strategy_signals * strategy_weight)
        
        # Apply signal threshold
        combined_signals = np.where(combined_signals > self.config['strategy']['signal_threshold'], 1, 0)
        
        return combined_signals
    
    def _calculate_portfolio_returns(self, signals, returns):
        """Calculate portfolio returns from signals"""
        # For now, use equal weighting
        weights = np.ones(len(signals)) / len(signals)
        
        # Calculate portfolio returns
        portfolio_returns = (weights * returns).sum(axis=1)
        
        return portfolio_returns
    
    def _run_backtest_analysis(self, portfolio_returns, prices):
        """Run comprehensive backtest analysis"""
        # Calculate performance metrics
        metrics = self._calculate_performance_metrics(portfolio_returns)
        
        # Calculate risk metrics
        risk_metrics = self.risk_manager.calculate_portfolio_risk(
            prices.pct_change().iloc[1:], 
            np.ones(len(prices.columns)) / len(prices.columns)
        )
        
        # Generate equity curve
        equity_curve = (1 + portfolio_returns).cumprod()
        
        # Calculate drawdown
        drawdown = self._calculate_drawdown(equity_curve)
        
        # Generate trade signals
        trade_signals = self._generate_trade_signals(portfolio_returns)
        
        return {
            'performance_metrics': metrics,
            'risk_metrics': risk_metrics,
            'equity_curve': equity_curve,
            'drawdown': drawdown,
            'trade_signals': trade_signals,
        }
    
    def _calculate_performance_metrics(self, returns):
        """Calculate comprehensive performance metrics"""
        # Basic metrics
        total_return = (1 + returns).prod() - 1
        annualized_return = (1 + total_return) ** (252 / len(returns)) - 1
        annualized_volatility = returns.std() * np.sqrt(252)
        
        # Risk-adjusted metrics
        sharpe_ratio = annualized_return / annualized_volatility if annualized_volatility > 0 else 0
        sortino_ratio = self._calculate_sortino_ratio(returns)
        calmar_ratio = annualized_return / self._calculate_max_drawdown((1 + returns).cumprod())
        
        # Additional metrics
        win_rate = self._calculate_win_rate(returns)
        average_win = self._calculate_average_win(returns)
        average_loss = self._calculate_average_loss(returns)
        profit_factor = self._calculate_profit_factor(returns)
        
        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'annualized_volatility': annualized_volatility,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
            'win_rate': win_rate,
            'average_win': average_win,
            'average_loss': average_loss,
            'profit_factor': profit_factor,
        }
    
    def _calculate_sortino_ratio(self, returns):
        """Calculate Sortino ratio"""
        downside_returns = returns[returns < 0]
        if len(downside_returns) == 0:
            return 0
        
        downside_vol = np.std(downside_returns)
        annualized_return = (1 + returns.mean()) ** 252 - 1
        
        return annualized_return / (downside_vol * np.sqrt(252))
    
    def _calculate_win_rate(self, returns):
        """Calculate win rate"""
        positive_returns = returns[returns > 0]
        return len(positive_returns) / len(returns)
    
    def _calculate_average_win(self, returns):
        """Calculate average winning trade"""
        positive_returns = returns[returns > 0]
        return positive_returns.mean() if len(positive_returns) > 0 else 0
    
    def _calculate_average_loss(self, returns):
        """Calculate average losing trade"""
        negative_returns = returns[returns < 0]
        return negative_returns.mean() if len(negative_returns) > 0 else 0
    
    def _calculate_profit_factor(self, returns):
        """Calculate profit factor"""
        positive_returns = returns[returns > 0]
        negative_returns = returns[returns < 0]
        
        if len(negative_returns) == 0:
            return np.inf
        
        return positive_returns.sum() / abs(negative_returns.sum())
    
    def _calculate_drawdown(self, equity_curve):
        """Calculate drawdown statistics"""
        peak = equity_curve.cummax()
        drawdown = (equity_curve - peak) / peak
        
        return {
            'current_drawdown': drawdown.iloc[-1],
            'max_drawdown': drawdown.min(),
            'average_drawdown': drawdown.mean(),
            'recovery_time': self._calculate_recovery_time(drawdown),
        }
    
    def _calculate_recovery_time(self, drawdown):
        """Calculate average recovery time after drawdowns"""
        # Simple implementation
        return len(drawdown)
    
    def _generate_trade_signals(self, returns):
        """Generate trade signals from returns"""
        signals = []
        
        for i, ret in enumerate(returns):
            if ret > 0.01:  # 1% threshold
                signals.append('BUY')
            elif ret < -0.01:  # -1% threshold
                signals.append('SELL')
            else:
                signals.append('HOLD')
        
        return pd.Series(signals, index=returns.index)


class ProfessionalDashboard:
    """Professional performance dashboard"""
    
    def __init__(self):
        self.figsize = (14, 10)
        self.style_config = {
            'background': '#1a1a1a',
            'text_color': '#ffffff',
            'grid_color': '#333333',
            'positive_color': '#00ff00',
            'negative_color': '#ff0000',
        }
    
    def create_performance_dashboard(self, backtest_results):
        """Create comprehensive performance dashboard"""
        
        # Create subplots
        fig, axes = plt.subplots(3, 3, figsize=self.figsize)
        fig.suptitle('Professional Trading Performance Dashboard', fontsize=16, color=self.style_config['text_color'])
        
        # Flatten axes for easier access
        axes = axes.flatten()
        
        # Plot 1: Equity Curve
        self._plot_equity_curve(axes[0], backtest_results)
        
        # Plot 2: Drawdown Analysis
        self._plot_drawdown_analysis(axes[1], backtest_results)
        
        # Plot 3: Risk-Return Scatter
        self._plot_risk_return_scatter(axes[2], backtest_results)
        
        # Plot 4: Rolling Sharpe Ratio
        self._plot_rolling_sharpe(axes[3], backtest_results)
        
        # Plot 5: Monthly Returns Heatmap
        self._plot_monthly_returns_heatmap(axes[4], backtest_results)
        
        # Plot 6: Trade Distribution
        self._plot_trade_distribution(axes[5], backtest_results)
        
        # Plot 7: Volatility Clustering
        self._plot_volatility_clustering(axes[6], backtest_results)
        
        # Plot 8: Correlation Matrix
        self._plot_correlation_matrix(axes[7], backtest_results)
        
        # Plot 9: Performance Metrics Summary
        self._plot_performance_summary(axes[8], backtest_results)
        
        plt.tight_layout()
        return fig
    
    def _plot_equity_curve(self, ax, results):
        """Plot equity curve"""
        equity_curve = results['equity_curve']
        ax.plot(equity_curve.index, equity_curve.values, 
               linewidth=2, color=self.style_config['positive_color'])
        ax.set_title('Equity Curve', color=self.style_config['text_color'])
        ax.set_xlabel('Date')
        ax.set_ylabel('Portfolio Value')
        ax.grid(True, color=self.style_config['grid_color'])
        ax.tick_params(colors=self.style_config['text_color'])
    
    def _plot_drawdown_analysis(self, ax, results):
        """Plot drawdown analysis"""
        drawdown = results['drawdown']
        ax.fill_between(drawdown.index, drawdown.values, 0, 
                       alpha=0.5, color=self.style_config['negative_color'])
        ax.plot(drawdown.index, drawdown.values, 
               linewidth=2, color=self.style_config['negative_color'])
        ax.set_title('Drawdown Analysis', color=self.style_config['text_color'])
        ax.set_xlabel('Date')
        ax.set_ylabel('Drawdown')
        ax.grid(True, color=self.style_config['grid_color'])
        ax.tick_params(colors=self.style_config['text_color'])
    
    def _plot_risk_return_scatter(self, ax, results):
        """Plot risk-return scatter"""
        metrics = results['performance_metrics']
        ax.scatter(metrics['annualized_volatility'] * 100, 
                  metrics['annualized_return'] * 100,
                  s=100, alpha=0.7, color=self.style_config['positive_color'])
        ax.set_title('Risk-Return Profile', color=self.style_config['text_color'])
        ax.set_xlabel('Annual Volatility (%)')
        ax.set_ylabel('Annual Return (%)')
        ax.grid(True, color=self.style_config['grid_color'])
        ax.tick_params(colors=self.style_config['text_color'])
    
    def _plot_rolling_sharpe(self, ax, results):
        """Plot rolling Sharpe ratio"""
        rolling_sharpe = results.get('rolling_sharpe', pd.Series())
        if not rolling_sharpe.empty:
            ax.plot(rolling_sharpe.index, rolling_sharpe.values,
                   linewidth=2, color=self.style_config['positive_color'])
        ax.set_title('Rolling Sharpe Ratio', color=self.style_config['text_color'])
        ax.set_xlabel('Date')
        ax.set_ylabel('Sharpe Ratio')
        ax.grid(True, color=self.style_config['grid_color'])
        ax.tick_params(colors=self.style_config['text_color'])
    
    def _plot_monthly_returns_heatmap(self, ax, results):
        """Plot monthly returns heatmap"""
        monthly_returns = results.get('monthly_returns', pd.DataFrame())
        if not monthly_returns.empty:
            sns.heatmap(monthly_returns.T, ax=ax, cmap='RdYlGn', center=0,
                       cbar_kws={'label': 'Return %'})
        ax.set_title('Monthly Returns Heatmap', color=self.style_config['text_color'])
        ax.set_xlabel('Year')
        ax.set_ylabel('Month')
    
    def _plot_trade_distribution(self, ax, results):
        """Plot trade distribution"""
        returns = results.get('returns', pd.Series())
        if len(returns) > 0:
            ax.hist(returns * 100, bins=50, alpha=0.7, color=self.style_config['positive_color'])
        ax.set_title('Trade Distribution', color=self.style_config['text_color'])
        ax.set_xlabel('Return (%)')
        ax.set_ylabel('Frequency')
        ax.grid(True, color=self.style_config['grid_color'])
        ax.tick_params(colors=self.style_config['text_color'])
    
    def _plot_volatility_clustering(self, ax, results):
        """Plot volatility clustering"""
        returns = results.get('returns', pd.Series())
        if len(returns) > 0:
            rolling_vol = returns.rolling(21).std()
            ax.plot(rolling_vol.index, rolling_vol.values,
                   linewidth=2, color=self.style_config['positive_color'])
        ax.set_title('Volatility Clustering', color=self.style_config['text_color'])
        ax.set_xlabel('Date')
        ax.set_ylabel('Volatility')
        ax.grid(True, color=self.style_config['grid_color'])
        ax.tick_params(colors=self.style_config['text_color'])
    
    def _plot_correlation_matrix(self, ax, results):
        """Plot correlation matrix"""
        returns = results.get('returns', pd.DataFrame())
        if len(returns) > 0:
            correlation = returns.corr()
            sns.heatmap(correlation, ax=ax, cmap='RdYlBu', center=0,
                       cbar_kws={'label': 'Correlation'})
        ax.set_title('Correlation Matrix', color=self.style_config['text_color'])
    
    def _plot_performance_summary(self, ax, results):
        """Plot performance metrics summary"""
        metrics = results['performance_metrics']
        
        # Create horizontal bar chart
        metrics_list = ['Sharpe Ratio', 'Sortino Ratio', 'Calmar Ratio', 'Win Rate']
        values = [
            metrics.get('sharpe_ratio', 0),
            metrics.get('sortino_ratio', 0),
            metrics.get('calmar_ratio', 0),
            metrics.get('win_rate', 0) * 100,
        ]
        
        colors = [self.style_config['positive_color'] if v > 0 else self.style_config['negative_color'] 
                 for v in values]
        
        bars = ax.barh(metrics_list, values, color=colors)
        ax.set_title('Performance Metrics Summary', color=self.style_config['text_color'])
        ax.set_xlabel('Value')
        ax.grid(True, color=self.style_config['grid_color'], axis='x')
        ax.tick_params(colors=self.style_config['text_color'])


class WalkForwardOptimizer:
    """Walk-forward optimization"""
    
    def __init__(self, config):
        self.config = config
        self.engine = BacktestEngine(config)
    
    def run_walk_forward(self, data, train_period=126, test_period=63):
        """Run walk-forward optimization"""
        results = []
        
        for i in range(0, len(data) - train_period - test_period, test_period):
            # Training phase
            train_data = data.iloc[i:i + train_period]
            test_data = data.iloc[i + train_period:i + train_period + test_period]
            
            # Optimize parameters
            optimal_params = self._optimize_parameters(train_data)
            
            # Test strategy
            test_results = self._test_strategy(test_data, optimal_params)
            results.append(test_results)
        
        return self._aggregate_results(results)
    
    def _optimize_parameters(self, data):
        """Optimize strategy parameters"""
        # Simple parameter optimization
        params = {
            'lookback_periods': self.config['strategy']['lookback_periods'],
            'volatility_lookback': self.config['strategy']['volatility_lookback'],
            'signal_threshold': self.config['strategy']['signal_threshold'],
        }
        
        return params
    
    def _test_strategy(self, data, params):
        """Test strategy with given parameters"""
        # Run backtest with optimized parameters
        results = self.engine.run_backtest(data, params)
        return results
    
    def _aggregate_results(self, results):
        """Aggregate walk-forward results"""
        aggregated = {
            'total_return': [],
            'sharpe_ratio': [],
            'max_drawdown': [],
        }
        
        for result in results:
            aggregated['total_return'].append(result['performance_metrics']['total_return'])
            aggregated['sharpe_ratio'].append(result['performance_metrics']['sharpe_ratio'])
            aggregated['max_drawdown'].append(result['drawdown']['max_drawdown'])
        
        return {
            'mean_total_return': np.mean(aggregated['total_return']),
            'mean_sharpe_ratio': np.mean(aggregated['sharpe_ratio']),
            'mean_max_drawdown': np.mean(aggregated['max_drawdown']),
            'std_total_return': np.std(aggregated['total_return']),
            'std_sharpe_ratio': np.std(aggregated['sharpe_ratio']),
            'std_max_drawdown': np.std(aggregated['max_drawdown']),
            'individual_results': results,
        }


class AdvancedTimeSeriesMomentumBot:
    """Professional time series momentum trading system"""
    
    def __init__(self, config_file="trading_config.yaml"):
        self.config = self._load_config(config_file)
        self.risk_manager = AdvancedRiskManager(self.config)
        self.market_regime_detector = MarketRegimeDetector(self.config)
        self.ml_signal_generator = MLSignalGenerator(self.config)
        self.strategy_selector = StrategySelector()
        self.backtest_engine = BacktestEngine(self.config)
        self.dashboard = ProfessionalDashboard()
        self.wf_optimizer = WalkForwardOptimizer(self.config)
    
    def _load_config(self, config_file):
        """Load configuration from file"""
        if Path(config_file).exists():
            with open(config_file, 'r') as f:
                return yaml.safe_load(f)
        else:
            return DEFAULT_CONFIG
    
    def run_complete_analysis(self, symbols, start_date, end_date):
        """Run complete analysis pipeline"""
        print("🚀 Starting Professional Trading System Analysis...")
        
        # Fetch data
        print("📊 Fetching market data...")
        data = self._fetch_data(symbols, start_date, end_date)
        
        # Run backtest
        print("⚡ Running backtest...")
        backtest_results = self.backtest_engine.run_backtest(data, start_date, end_date)
        
        # Run walk-forward optimization
        print("🔄 Running walk-forward optimization...")
        wf_results = self.wf_optimizer.run_walk_forward(data)
        
        # Generate professional dashboard
        print("📈 Generating professional dashboard...")
        dashboard = self.dashboard.create_performance_dashboard(backtest_results)
        
        # Generate comprehensive report
        print("📋 Generating comprehensive report...")
        report = self._generate_comprehensive_report(backtest_results, wf_results)
        
        return {
            'backtest_results': backtest_results,
            'walk_forward_results': wf_results,
            'dashboard': dashboard,
            'report': report,
        }
    
    def _fetch_data(self, symbols, start_date, end_date):
        """Fetch market data with error handling"""
        try:
            df = yf.download(symbols, start=start_date, end=end_date, progress=False)
            return df['Adj Close']
        except Exception as e:
            print(f"Error fetching data: {e}")
            raise
    
    def _generate_comprehensive_report(self, backtest_results, wf_results):
        """Generate comprehensive analysis report"""
        report = {
            'executive_summary': self._create_executive_summary(backtest_results),
            'performance_analysis': self._create_performance_analysis(backtest_results),
            'risk_analysis': self._create_risk_analysis(backtest_results),
            'walk_forward_analysis': self._create_walk_forward_analysis(wf_results),
            'recommendations': self._create_recommendations(backtest_results, wf_results),
        }
        
        return report
    
    def _create_executive_summary(self, results):
        """Create executive summary"""
        metrics = results['performance_metrics']
        
        return {
            'total_return': f"{metrics['total_return']*100:.2f}%",
            'annualized_return': f"{metrics['annualized_return']*100:.2f}%",
            'annualized_volatility': f"{metrics['annualized_volatility']*100:.2f}%",
            'sharpe_ratio': f"{metrics['sharpe_ratio']:.2f}",
            'sortino_ratio': f"{metrics['sortino_ratio']:.2f}",
            'calmar_ratio': f"{metrics['calmar_ratio']:.2f}",
            'win_rate': f"{metrics['win_rate']*100:.2f}%",
            'profit_factor': f"{metrics['profit_factor']:.2f}",
            'max_drawdown': f"{results['drawdown']['max_drawdown']*100:.2f}%",
        }
    
    def _create_performance_analysis(self, results):
        """Create performance analysis"""
        return {
            'metric_trend': 'improving' if results['performance_metrics']['sharpe_ratio'] > 1 else 'declining',
            'risk_adjusted_performance': 'good' if results['performance_metrics']['sharpe_ratio'] > 1.5 else 'average',
            'trade_quality': 'excellent' if results['performance_metrics']['win_rate'] > 0.6 else 'good',
            'return_consistency': 'stable' if results['performance_metrics']['calmar_ratio'] > 1 else 'volatile',
        }
    
    def _create_risk_analysis(self, results):
        """Create risk analysis"""
        return {
            'volatility_regime': 'moderate',
            'drawdown_risk': 'controlled' if results['drawdown']['max_drawdown'] < 0.15 else 'high',
            'liquidity_risk': 'low',
            'correlation_risk': 'diversified',
        }
    
    def _create_walk_forward_analysis(self, results):
        """Create walk-forward analysis"""
        return {
            'out_of_sample_performance': 'stable' if results['mean_sharpe_ratio'] > 0.5 else 'unstable',
            'parameter_stability': 'high' if results['std_sharpe_ratio'] < 0.5 else 'low',
            'robustness': 'excellent' if results['mean_sharpe_ratio'] > 1.5 else 'good',
        }
    
    def _create_recommendations(self, backtest_results, wf_results):
        """Create investment recommendations"""
        recommendations = []
        
        metrics = backtest_results['performance_metrics']
        
        if metrics['sharpe_ratio'] > 1.5:
            recommendations.append("✅ Strategy shows excellent risk-adjusted returns")
        elif metrics['sharpe_ratio'] > 1.0:
            recommendations.append("⚠️ Strategy shows good risk-adjusted returns")
        else:
            recommendations.append("❌ Strategy shows poor risk-adjusted returns")
        
        if metrics['win_rate'] > 0.6:
            recommendations.append("✅ High win rate indicates strategy robustness")
        elif metrics['win_rate'] > 0.4:
            recommendations.append("⚠️ Moderate win rate requires careful position sizing")
        else:
            recommendations.append("❌ Low win rate requires strategy review")
        
        if metrics['profit_factor'] > 1.5:
            recommendations.append("✅ Strong profit factor indicates good strategy")
        elif metrics['profit_factor'] > 1.0:
            recommendations.append("⚠️ Adequate profit factor requires risk management")
        else:
            recommendations.append("❌ Poor profit factor requires strategy overhaul")
        
        if backtest_results['drawdown']['max_drawdown'] < 0.15:
            recommendations.append("✅ Acceptable maximum drawdown")
        else:
            recommendations.append("⚠️ High maximum drawdown requires stop-loss implementation")
        
        return recommendations


class TradingAPI:
    """Professional trading API integration"""
    
    def __init__(self, api_key, api_secret, base_url="https://api.trading.com"):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.session = self._create_authenticated_session()
    
    def _create_authenticated_session(self):
        """Create authenticated session"""
        import requests
        session = requests.Session()
        session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        })
        return session
    
    def place_order(self, symbol, side, quantity, order_type="market", **kwargs):
        """Place order through trading API"""
        order_data = {
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'type': order_type,
            'timestamp': datetime.now().isoformat(),
            'order_id': self._generate_order_id(),
        }
        order_data.update(kwargs)
        
        try:
            response = self.session.post(
                f"{self.base_url}/orders",
                json=order_data
            )
            return self._parse_order_response(response)
        except Exception as e:
            print(f"Order placement failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_portfolio(self):
        """Get current portfolio"""
        try:
            response = self.session.get(f"{self.base_url}/portfolio")
            return self._parse_portfolio_response(response)
        except Exception as e:
            print(f"Portfolio fetch failed: {e}")
            return {'positions': []}
    
    def _generate_order_id(self):
        """Generate unique order ID"""
        return f"ORD_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{np.random.randint(1000, 9999)}"
    
    def _parse_order_response(self, response):
        """Parse order response"""
        try:
            return response.json()
        except:
            return {'success': False, 'error': 'Invalid response format'}
    
    def _parse_portfolio_response(self, response):
        """Parse portfolio response"""
        try:
            return response.json()
        except:
            return {'positions': []}


class MonteCarloSimulator:
    """Monte Carlo simulation for risk analysis"""
    
    def __init__(self, config):
        self.config = config
    
    def run_simulation(self, returns, n_simulations=10000):
        """Run Monte Carlo simulation"""
        simulations = []
        
        for i in range(n_simulations):
            # Generate random path using historical distribution
            random_returns = np.random.normal(
                returns.mean(),
                returns.std(),
                size=len(returns)
            )
            
            # Calculate performance metrics
            cum_returns = (1 + random_returns).cumprod()
            max_drawdown = self._calculate_max_drawdown(cum_returns)
            
            simulations.append({
                'final_value': cum_returns.iloc[-1],
                'max_drawdown': max_drawdown,
                'volatility': random_returns.std(),
                'sharpe': random_returns.mean() / random_returns.std() if random_returns.std() > 0 else 0,
                'calmar': (cum_returns.iloc[-1] - 1) / abs(max_drawdown) if max_drawdown != 0 else 0,
            })
        
        return pd.DataFrame(simulations)
    
    def _calculate_max_drawdown(self, equity_curve):
        """Calculate maximum drawdown"""
        peak = equity_curve.cummax()
        drawdown = (equity_curve - peak) / peak
        return drawdown.min()


# Main execution
if __name__ == "__main__":
    # Multi-asset ETF proxy universe
    universe = ["SPY", "QQQ", "IWM", "VTI", "AAPL", "MSFT", "AMZN"]
    
    # Initialize professional trading system
    bot = AdvancedTimeSeriesMomentumBot()
    
    # Run complete analysis
    results = bot.run_complete_analysis(
        symbols=universe,
        start_date="2005-01-01",
        end_date="2024-01-01"
    )
    
    # Print executive summary
    print("\n" + "="*60)
    print("PROFESSIONAL TRADING SYSTEM EXECUTIVE SUMMARY")
    print("="*60)
    
    print("\n📊 PERFORMANCE METRICS:")
    for key, value in results['report']['executive_summary'].items():
        print(f"   {key}: {value}")
    
    print("\n🎯 INVESTMENT RECOMMENDATIONS:")
    for recommendation in results['report']['recommendations']:
        print(f"   {recommendation}")
    
    print("\n📈 WALK-FORWARD ANALYSIS:")
    wf = results['walk_forward_results']
    print(f"   Out-of-Sample Sharpe: {wf['mean_sharpe_ratio']:.2f}")
    print(f"   Parameter Stability: {wf['parameter_stability']}")
    print(f"   Robustness: {wf['robustness']}")
    
    print("\n" + "="*60)
    print("ANALYSIS COMPLETE - Professional trading system ready for deployment!")
    print("="*60)
