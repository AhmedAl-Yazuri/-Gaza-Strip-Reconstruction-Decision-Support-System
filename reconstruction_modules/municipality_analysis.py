# ======================================================
# reconstruction_modules/municipality_analysis.py
# Municipality-Based Damage Analysis and Strategies
# ======================================================

from config import *

# ======================================================
# Damage Pattern Analysis
# ======================================================

def analyze_damage_patterns(damage_gdf):
    """Analyze actual damage patterns to determine rebuilding strategies"""
    if damage_gdf.empty or 'Municipality' not in damage_gdf.columns:
        return {
            'high_damage_areas': [],
            'moderate_damage_areas': [],
            'low_damage_areas': [],
            'total_damage_sites': 0
        }

    # Calculate damage statistics by municipality
    municipality_stats = damage_gdf.groupby('Municipality').agg({
        'geometry': 'count'  # Count of damage sites
    }).rename(columns={'geometry': 'damage_sites'}).reset_index()

    # Sort by damage sites
    municipality_stats = municipality_stats.sort_values('damage_sites', ascending=False)

    total_damage = municipality_stats['damage_sites'].sum()

    # Classify municipalities by damage level (relative to total)
    high_threshold = total_damage * DAMAGE_CLASSIFICATION_THRESHOLDS["high_damage"]  # Top 30% of damage
    moderate_threshold = total_damage * DAMAGE_CLASSIFICATION_THRESHOLDS["moderate_damage"]  # Next 15% of damage

    high_damage_areas = municipality_stats[municipality_stats['damage_sites'] >= high_threshold]['Municipality'].tolist()
    moderate_damage_areas = municipality_stats[
        (municipality_stats['damage_sites'] < high_threshold) &
        (municipality_stats['damage_sites'] >= moderate_threshold)
    ]['Municipality'].tolist()
    low_damage_areas = municipality_stats[municipality_stats['damage_sites'] < moderate_threshold]['Municipality'].tolist()

    print(f"   - Damage Analysis: {len(high_damage_areas)} high-damage areas, {len(moderate_damage_areas)} moderate, {len(low_damage_areas)} low")
    print(f"   - Most affected: {high_damage_areas[:3]}")

    return {
        'high_damage_areas': [area.lower() for area in high_damage_areas],
        'moderate_damage_areas': [area.lower() for area in moderate_damage_areas],
        'low_damage_areas': [area.lower() for area in low_damage_areas],
        'total_damage_sites': total_damage
    }

# ======================================================
# Rebuilding Strategy Determination
# ======================================================

def determine_rebuilding_strategy(row, damage_analysis):
    """Determine rebuilding strategy based on municipality and destruction level"""
    municipality = str(row.get('primary_municipality', 'Unknown')).lower()
    damage_count = row.get("damage_count", 0)
    max_damage = row.get("max_damage_count", 1)

    # Calculate relative destruction level
    if max_damage > 0:
        destruction_level = damage_count / max_damage
    else:
        destruction_level = 0

    # Use data-driven classification
    high_damage = damage_analysis.get('high_damage_areas', [])
    moderate_damage = damage_analysis.get('moderate_damage_areas', [])
    low_damage = damage_analysis.get('low_damage_areas', [])

    # Check for high damage areas (complete devastation)
    if (any(area in municipality for area in high_damage) or
        municipality in high_damage or
        destruction_level > 0.7 or
        damage_count > 100):
        return {
            "strategy": "Basic_Infrastructure_First",
            "priority_weights": {
                "hospitals": 0.35, "water": 0.25, "fuel": 0.20, "damage": 0.15, "streets": 0.05
            },
            "description": "High damage area - establish basic infrastructure and life support first"
        }
    # Check for moderate damage areas (balanced reconstruction)
    elif (any(area in municipality for area in moderate_damage) or
          municipality in moderate_damage or
          (destruction_level >= 0.3 and destruction_level <= 0.7) or
          (damage_count >= 50 and damage_count <= 100)):
        return {
            "strategy": "Balanced_Reconstruction",
            "priority_weights": {
                "hospitals": 0.30, "damage": 0.25, "water": 0.20, "fuel": 0.15, "streets": 0.10
            },
            "description": "Moderate damage - balanced infrastructure reconstruction"
        }
    # Low damage areas (street reconstruction priority)
    else:
        return {
            "strategy": "Street_Reconstruction_Priority",
            "priority_weights": {
                "streets": 0.35, "hospitals": 0.25, "water": 0.20, "fuel": 0.15, "damage": 0.05
            },
            "description": "Low damage area - focus on street rebuilding and connectivity restoration"
        }

# ======================================================
# Expert Explanation Generation
# ======================================================

def generate_expert_explanation(row):
    """Generate contextual explanations for reconstruction priorities"""
    reasons = []
    strategy_info = row["rebuilding_strategy"]

    # Add strategy-based reasoning
    reasons.append(f"STRATEGY: {strategy_info['strategy']} - {strategy_info['description']}")

    if row["hospitals_count"] >= 2: reasons.append("Critical hospitals/clinics affected - HIGH PRIORITY")
    if row["damage_age_score"] >= 2: reasons.append("Long-term persistent damage (older sites) - AGE PRIORITY")
    elif row["damage_age_score"] >= 1: reasons.append("Established damage sites requiring attention")
    if row["water_util_count"] >= 1: reasons.append("Municipal water facilities disrupted")
    if row["fuel_util_count"] >= 1: reasons.append("Fuel/energy services compromised")
    if row["population_density"] >= 3: reasons.append("High population density area")
    if row["education_count"] >= 3: reasons.append("Education services affected")

    # Area-specific recommendations
    if strategy_info['strategy'] == 'Street_Reconstruction_Priority':
        reasons.append("FOCUS: Street rebuilding and transportation connectivity priority")
    elif strategy_info['strategy'] == 'Basic_Infrastructure_First':
        reasons.append("FOCUS: Establish basic life-support infrastructure first - high damage area")
    elif strategy_info['strategy'] == 'Balanced_Reconstruction':
        reasons.append("FOCUS: Balanced infrastructure reconstruction for moderate damage")
    elif strategy_info['strategy'] == 'Comprehensive_Northern_Rebuilding':
        reasons.append("FOCUS: Complete infrastructure rebuilding required for northern areas")

    if not reasons:
        if row["ai_score"] > 0.3:
            return "Moderate infrastructure needs detected"
        return "Limited critical infrastructure impact"

    return " | ".join(reasons)