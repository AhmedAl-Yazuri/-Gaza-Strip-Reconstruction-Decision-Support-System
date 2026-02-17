# ======================================================
# reconstruction_modules/config.py
# Configuration and Constants for Gaza Reconstruction DSS
# ======================================================

import os

# ======================================================
# System Information
# ======================================================

SYSTEM_VERSION = "1.0.0"
TEMPLATE_VERSION = "1.0"
HEX_GRID_SIZE = 500  # meters

# ======================================================
# Data Paths and Configuration
# ======================================================

BASE_DATA_DIR = "reconstruction_modules/gaza_gis_data"

candidate_dirs = [
    BASE_DATA_DIR,
    os.path.join(BASE_DATA_DIR, "gaza_gis_data"),
    ".",  # Current directory
    "..",  # Parent directory
]

DATA_DIR = None
for d in candidate_dirs:
    if os.path.isdir(d):
        try:
            # Check for .gpkg files or .gdb directory
            has_gpkg = any(f.lower().endswith(".gpkg") for f in os.listdir(d))
            has_gdb = os.path.exists(os.path.join(d, "UNOSAT_GazaStrip_CDA_11October2025.gdb"))
            if has_gpkg or has_gdb:
                DATA_DIR = d
                break
        except Exception:
            pass

if DATA_DIR is None:
    for d in candidate_dirs:
        if os.path.isdir(d):
            DATA_DIR = d
            break

if DATA_DIR is None:
    raise FileNotFoundError("Could not find DATA_DIR. Expected gaza_gis_data/ or current directory with GIS data")

# File paths
GDB_PATH = os.path.join(os.path.dirname(__file__), "UNOSAT_GazaStrip_CDA_11October2025.gdb")  # GDB in reconstruction_modules directory
DATA_DIR_INFRA = os.path.join(os.path.dirname(__file__), "gaza_gis_data")  # Infrastructure data location
TARGET_CRS = "EPSG:32636"

# Output files
TEMPLATE_XLSX = "Gaza_Projects_Template.xlsx"
EXPERT_XLSX = "Gaza_Projects_ExpertEdits.xlsx"
TOP20_CSV = "Gaza_Top20_Projects.csv"
OUTPUT_HTML = "Gaza_Reconstruction_DSS_Map.html"

# Damage analysis output files
HIGH_DAMAGE_CSV = "Gaza_HighDamageAreas_Top15_Projects.csv"
MODERATE_DAMAGE_CSV = "Gaza_ModerateDamageAreas_Top10_Projects.csv"
LOW_DAMAGE_CSV = "Gaza_LowDamageAreas_Top10_Projects.csv"

# ======================================================
# Reconstruction Priority Order (as requested)
# ======================================================
RECONSTRUCTION_ORDER = [
    "Rebuild destroyed streets (access corridors first)",
    "Hospitals & health centers",
    "Water treatment plants (municipal + civil defense)",
    "Fuel stations / fuel production & distribution (gasoline/diesel/natural gas)",
    "Rubble removal",
    "Apartments & government buildings",
    "Homes (final)"
]

# ======================================================
# Age Ranking Algorithm Parameters
# ======================================================

AGE_RANKING_WEIGHTS = {
    "time_decay": 0.4,
    "consecutive_bonus": 0.3,
    "severity_multiplier": 0.3,
    "trend_multiplier": 0.2
}

# ======================================================
# Scoring Weights and Parameters
# ======================================================


# --- Healthcare Priority Multipliers ---
MAJOR_HOSPITAL_MULTIPLIER = 1.7 
CLINIC_MULTIPLIER = 0.3       



# AI Scoring weights
SCORING_WEIGHTS = {
    "default": {
        "damage": 0.20,
        "major_hospitals": 0.60, 
        "hospitals": 0.10,
        "water": 0.15,
        "fuel": 0.12,
        "streets": 0.10,
        "schools": 0.06,
        "universities": 0.08,
        "municipalities": 0.04
    },
    "population_density": 0.15,  
    "education": 0.02,
    "age_score": 0.25
}

# Priority weights for final ranking
PRIORITY_WEIGHTS = {
    "ai_score": 0.7,
    "age_score": 0.3
}

# ======================================================
# Project Generation Parameters
# ======================================================

TOP_PROJECTS_COUNT = 20
MINIMUM_UNITS = 500
MINIMUM_UNITS_HIGH_DAMAGE = 750
MAXIMUM_UNITS_LOW_DAMAGE = 300
UNITS_PER_DAMAGE_SITE = 10  # Units per damage site
COST_ESTIMATES = {"per_unit": 50000}  # $50k per unit
TIMELINE_ESTIMATES = {
    "Basic_Infrastructure_First": 18,  # months
    "Balanced_Reconstruction": 12,
    "Street_Reconstruction_Priority": 8,
    "Comprehensive_Northern_Rebuilding": 24
}

# ======================================================
# Funding and Scoring Parameters
# ======================================================

# Funding thresholds (expanded)
FUNDING_THRESHOLDS = {
    "hospitals_max": 1.0,
    "damage_age_boost": 2.5,
    "water_max": 0.5,
    "fuel_max": 0.5,
    "population_max": 2.0,
    "education_max": 10.0
}

# ======================================================
# Age Ranking Parameters
# ======================================================

AGE_RANKING_WEIGHTS = {
    "time_decay": 0.4,
    "consecutive_bonus": 0.3,
    "severity_multiplier": 0.2,
    "trend_multiplier": 0.1
}

TIME_WEIGHTS = {
    "min_weight": 0.5,
    "max_weight": 2.0
}

# ======================================================
# Project Generation Parameters
# ======================================================

PROJECT_PARAMS = {
    "hospitals": {
        "base_medical": 150,
        "base_pop_weight": 1.2,
        "base_speed_bias": 40,
        "prefix": "HOSPITAL"
    },
    
    "water": {
        "base_medical": 120,
        "base_pop_weight": 1.1,
        "base_speed_bias": 35,
        "prefix": "WATER"
    },
    "fuel": {
        "base_medical": 100,
        "base_pop_weight": 0.9,
        "base_speed_bias": 45,
        "prefix": "FUEL"
    },
    "education": {
        "base_medical": 30,
        "base_pop_weight": 0.7,
        "base_speed_bias": 80,
        "prefix": "EDU"
    },
    "destroyed": {
        "base_medical": 80,
        "base_pop_weight": 1.0,
        "base_speed_bias": 50,
        "prefix": "DESTROYED"
    }
}

# Final scoring weights
FINAL_SCORING_WEIGHTS = {
    "medical": 0.4,
    "population": 0.4,
    "speed": 0.2
}

# Scoring ranges (expanded for funding appeal)
SCORING_RANGES = {
    "min_score": 0,
    "max_score": 200
}

# ======================================================
# Spatial Analysis Parameters
# ======================================================

HEX_GRID_PARAMS = {
    "radius": 300,  # meters
    "crs": TARGET_CRS
}

# ======================================================
# Gaza Strip Boundaries (to filter out non-Gaza data)
# ======================================================

# Gaza Strip bounding box (strict boundaries to exclude Israeli/Egyptian territory)
GAZA_BBOX = {
    "min_lon": 34.216,   # Western border (Mediterranean Sea)
    "max_lon": 34.545,   # Eastern border (Gaza-Israel border)
    "min_lat": 31.220,   # Southern border (Gaza-Egypt border)
    "max_lat": 31.590    # Northern border (Gaza-Israel border)
}

# ======================================================
# Visualization Parameters
# ======================================================

MAP_CONFIG = {
    "location": [31.4, 34.35],
    "zoom_start": 11,
    "tiles": "CartoDB positron"
}

PRIORITY_COLORS = {
    "Critical": "#8B0000",      # Dark red for highest priority
    "Very High": "#FF0000",     # Bright red
    "High": "#FF4500",          # Orange red
    "Medium": "#FFD700",        # Gold
    "Low": "#32CD32",           # Lime green
    "Very Low": "#1E90FF",      # Dodger blue
    "default": "gray"
}

PRIORITY_THRESHOLDS = {
    "Critical": 0.80,
    "Very High": 0.60,
    "High": 0.40,
    "Medium": 0.25,
    "Low": 0.10
}

FUNDING_THRESHOLDS_LABELS = {
    "Maximum Funding": 1.8,
    "High Funding": 1.4,
    "Standard Funding": 1.0,
    "Moderate Funding": 0.6,
    "Low Funding": 0.3
}

# ======================================================
# Municipality Analysis Parameters
# ======================================================

DAMAGE_CLASSIFICATION_THRESHOLDS = {
    "high_damage": 0.3,      # Top 30% of total damage
    "moderate_damage": 0.15  # Next 15% of total damage
}

MINIMUM_PROJECTS_REQUIRED = 500

# ======================================================
# Logging and Output
# ======================================================

def print_system_info():
    """Print system configuration information"""
    print(" System Strategy: Loading spatial data layers...")
    print(f"   - DATA_DIR resolved to: {os.path.abspath(DATA_DIR)}")
    print("   - Files in DATA_DIR:")
    for f in os.listdir(DATA_DIR):
        print(f"     • {f}")
    print(f"   - Target CRS: {TARGET_CRS}")
    print(f"   - GDB Path: {GDB_PATH}")