"""Analysis module for ticket metrics and trend calculation."""

from __future__ import annotations

from .strategies import (
    MetricsCalculator,
    TrendAnalysisStrategy,
    StatisticalAnalysisStrategy
)
from .analysis_service import (
    AnalysisEngine,
    TicketDataProcessor,
    AnalysisPerformanceMonitor
)
from .calculators import (
    ResolutionTimeCalculator,
    StatusDistributionCalculator,
    VolumeAnalyzer,
    SeverityAnalyzer,
    TeamPerformanceCalculator
)
from .trends import (
    TrendAnalyzer,
    ForecastingEngine
)
from .data_processor import (
    TicketDataProcessor,
    ValidationRuleEngine,
    DataCleaner,
    EdgeCaseHandler,
    DataQualityAssessor
)

__all__ = [
    'MetricsCalculator',
    'TrendAnalysisStrategy', 
    'StatisticalAnalysisStrategy',
    'AnalysisEngine',
    'TicketDataProcessor',
    'AnalysisPerformanceMonitor',
    'ResolutionTimeCalculator',
    'StatusDistributionCalculator',
    'VolumeAnalyzer',
    'SeverityAnalyzer',
    'TeamPerformanceCalculator',
    'TrendAnalyzer',
    'ForecastingEngine',
    'ValidationRuleEngine',
    'DataCleaner',
    'EdgeCaseHandler',
    'DataQualityAssessor'
]