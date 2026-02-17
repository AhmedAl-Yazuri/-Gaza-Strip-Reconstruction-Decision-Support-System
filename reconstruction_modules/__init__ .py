# ======================================================
# reconstruction_modules/__init__.py
# Package initialization for Gaza Reconstruction DSS modules
# ======================================================

"""
Gaza Reconstruction Decision Support System

A modular system for analyzing damage assessment data and generating
prioritized reconstruction strategies for Gaza municipalities.

Modules:
- config: System configuration and constants
- data_loader: Data loading and preprocessing functions
- spatial_analysis: Hexagonal grid generation and spatial operations
- municipality_analysis: Damage pattern analysis and rebuilding strategies
- scoring_engine: AI-enhanced scoring and weighting algorithms
- project_generator: Project creation and Excel template generation
- visualization: Interactive maps and statistical dashboards
"""

__version__ = "1.0.0"
__author__ = "Gaza Reconstruction DSS Team"

# Import key functions for easy access
from .config import print_system_info
from .data_loader import load_damage_data, load_infrastructure_layers
from .spatial_analysis import create_hex_grid, integrate_spatial_data
from .municipality_analysis import analyze_damage_patterns, determine_rebuilding_strategy
from .scoring_engine import apply_scoring_pipeline
from .project_generator import generate_projects_from_zones, export_projects_to_excel
from .visualization import create_interactive_map, create_statistical_dashboard

__all__ = [
    'print_system_info',
    'load_damage_data',
    'load_infrastructure_layers',
    'create_hex_grid',
    'integrate_spatial_data',
    'analyze_damage_patterns',
    'determine_rebuilding_strategy',
    'apply_scoring_pipeline',
    'generate_projects_from_zones',
    'export_projects_to_excel',
    'create_interactive_map',
    'create_statistical_dashboard'
]