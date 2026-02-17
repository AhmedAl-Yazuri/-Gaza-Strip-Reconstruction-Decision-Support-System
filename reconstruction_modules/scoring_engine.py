# ======================================================
# reconstruction_modules/scoring_engine.py
# AI-Enhanced Scoring and Weighting Engine
# ======================================================

from config import *
import numpy as np
import pandas as pd
try:
    from sklearn.cluster import KMeans, DBSCAN
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except Exception:
    KMeans = None
    DBSCAN = None
    StandardScaler = None
    SKLEARN_AVAILABLE = False

# ======================================================
# Simple Normalization (Alternative to MinMaxScaler)
# ======================================================

def simple_minmax_scaler(data):
    """Simple MinMaxScaler alternative that doesn't require sklearn"""
    if len(data) == 0:
        return data

    min_val = np.min(data)
    max_val = np.max(data)

    if max_val == min_val:
        return np.zeros_like(data)  # All values are the same

    return (data - min_val) / (max_val - min_val)

# ======================================================
# Feature Normalization
# ======================================================

def normalize_features(df, feature_columns):
    """Normalize features using simple MinMaxScaler alternative"""
    normalized_data = {}

    for col in feature_columns:
        if col in df.columns:
            normalized_data[col] = simple_minmax_scaler(df[col].values)
        else:
            normalized_data[col] = np.zeros(len(df))  # Default to zeros

    normalized_df = pd.DataFrame(normalized_data, index=df.index)
    return normalized_df

# ======================================================
# Enhanced Age Ranking Algorithm
# ======================================================

def calculate_age_score(row):
    """Enhanced age ranking with multi-factor analysis"""
    base_age = row.get('age_days', 0)

    # Factor 1: Severity-weighted persistence
    severity_multiplier = 1 + (row.get('damage_severity', 1) * 0.2)

    # Factor 2: Time-decay weighting (older damage gets higher priority)
    time_decay = min(base_age / 365, 3)  # Cap at 3 years

    # Factor 3: Consecutive damage bonus (persistent issues)
    consecutive_bonus = min(row.get('consecutive_damage_days', 0) / 30, 2)  # Monthly bonus

    # Factor 4: Trend analysis (increasing damage patterns)
    trend_multiplier = 1 + (row.get('damage_trend', 0) * 0.1)

    # Combined score with weights
    age_score = (
        time_decay * AGE_RANKING_WEIGHTS["time_decay"] +
        consecutive_bonus * AGE_RANKING_WEIGHTS["consecutive_bonus"] +
        severity_multiplier * AGE_RANKING_WEIGHTS["severity_multiplier"] +
        trend_multiplier * AGE_RANKING_WEIGHTS["trend_multiplier"]
    )

    return age_score

# ======================================================
# AI-Enhanced Scoring Algorithm
# ======================================================

def calculate_ai_score(row, normalized_features):
    """Calculate AI-enhanced score with municipality-based adjustments"""
    base_score = 0

    # Get normalized feature values
    damage_norm = normalized_features.loc[row.name, 'damage_count'] if 'damage_count' in normalized_features.columns else 0
    major_hospitals_norm = normalized_features.loc[row.name, 'major_hospitals_count'] if 'major_hospitals_count' in normalized_features.columns else 0
    hospitals_norm = normalized_features.loc[row.name, 'hospitals_count'] if 'hospitals_count' in normalized_features.columns else 0
    water_norm = normalized_features.loc[row.name, 'water_util_count'] if 'water_util_count' in normalized_features.columns else 0
    fuel_norm = normalized_features.loc[row.name, 'fuel_util_count'] if 'fuel_util_count' in normalized_features.columns else 0
    streets_norm = normalized_features.loc[row.name, 'streets_count'] if 'streets_count' in normalized_features.columns else 0
    schools_norm = normalized_features.loc[row.name, 'schools_count'] if 'schools_count' in normalized_features.columns else 0
    universities_norm = normalized_features.loc[row.name, 'universities_count'] if 'universities_count' in normalized_features.columns else 0
    municipalities_norm = normalized_features.loc[row.name, 'municipalities_count'] if 'municipalities_count' in normalized_features.columns else 0
    population_norm = normalized_features.loc[row.name, 'population_density'] if 'population_density' in normalized_features.columns else 0
    education_norm = normalized_features.loc[row.name, 'education_count'] if 'education_count' in normalized_features.columns else 0
    age_norm = normalized_features.loc[row.name, 'damage_age_score'] if 'damage_age_score' in normalized_features.columns else 0
    centrality_norm = normalized_features.loc[row.name, 'street_centrality_sum'] if 'street_centrality_sum' in normalized_features.columns else 0
    impedance_norm = normalized_features.loc[row.name, 'street_impedance_sum'] if 'street_impedance_sum' in normalized_features.columns else 0
    critical_streets_norm = normalized_features.loc[row.name, 'critical_streets_count'] if 'critical_streets_count' in normalized_features.columns else 0

    # Apply municipality-based strategy weights
    strategy_weights = row.get('rebuilding_strategy', {}).get('priority_weights', SCORING_WEIGHTS["default"])

    # Calculate weighted score
    ai_score = (
        damage_norm * strategy_weights.get("damage", SCORING_WEIGHTS["default"]["damage"]) +
        major_hospitals_norm * (strategy_weights.get("hospitals", 0.9) * 1.7) +
        hospitals_norm * (strategy_weights.get("hospitals", 0.9) * 0.3) +
        water_norm * strategy_weights.get("water", SCORING_WEIGHTS["default"]["water"]) +
        fuel_norm * strategy_weights.get("fuel", SCORING_WEIGHTS["default"]["fuel"]) +
        streets_norm * strategy_weights.get("streets", SCORING_WEIGHTS["default"]["streets"]) +
        schools_norm * strategy_weights.get("schools", SCORING_WEIGHTS["default"]["schools"]) +
        universities_norm * strategy_weights.get("universities", SCORING_WEIGHTS["default"]["universities"]) +
        municipalities_norm * strategy_weights.get("municipalities", SCORING_WEIGHTS["default"]["municipalities"]) +
        population_norm * SCORING_WEIGHTS["population_density"] +
        education_norm * SCORING_WEIGHTS["education"] +
        age_norm * SCORING_WEIGHTS["age_score"] +
        centrality_norm * 0.20 +
        impedance_norm * 0.25 +
        critical_streets_norm * 0.35
    )

    # Apply non-linear scaling for prioritization
    if ai_score > 0.8:
        ai_score = ai_score * 1.2  # Boost high-priority areas
    elif ai_score < 0.2:
        ai_score = ai_score * 0.8  # Reduce low-priority areas

    # Connectivity bottlenecks with real damage get maximum priority floor.
    if row.get('critical_streets_count', 0) > 0 and row.get('road_damage_severity', 0) >= 2:
        ai_score = max(ai_score, 0.98)

    return min(ai_score, 1.0)  # Cap at 1.0

# ======================================================
# Priority Ranking System
# ======================================================

def calculate_priority_rank(row):
    """Calculate final priority ranking"""
    ai_score = row.get('ai_score', 0)
    age_score = row.get('damage_age_score', 0)

    # Combine AI score with age ranking
    combined_score = (
        ai_score * PRIORITY_WEIGHTS["ai_score"] +
        age_score * PRIORITY_WEIGHTS["age_score"]
    )

    # Apply reconstruction order bonus
    reconstruction_order = row.get('reconstruction_order', 0)
    order_multiplier = 1 + (reconstruction_order * 0.1)

    final_score = combined_score * order_multiplier

    return final_score


def _profile_clusters(df, feature_cols):
    """Create readable cluster profile names from cluster feature means."""
    if 'ml_cluster' not in df.columns:
        return {}

    cluster_means = df.groupby('ml_cluster')[feature_cols].mean(numeric_only=True)
    if cluster_means.empty:
        return {}

    # Normalize means for profile heuristics
    norm = (cluster_means - cluster_means.min()) / (cluster_means.max() - cluster_means.min() + 1e-9)
    profile_map = {}
    for cluster_id, row in norm.iterrows():
        high_damage = row.get('damage_count', 0) > 0.7
        high_pop = row.get('population_density', 0) > 0.7
        high_infra = (
            row.get('hospitals_count', 0) > 0.6 or
            row.get('water_util_count', 0) > 0.6 or
            row.get('major_hospitals_count', 0) > 0.5
        )
        high_bottleneck = (
            row.get('critical_streets_count', 0) > 0.5 or
            row.get('street_centrality_sum', 0) > 0.7
        )

        if high_bottleneck and high_damage:
            label = "Critical Infrastructure Hubs"
        elif high_damage and high_pop:
            label = "High Density / High Damage"
        elif high_pop and not high_damage:
            label = "High Density / Low Damage"
        elif high_infra and not high_damage:
            label = "Service Hubs Under Pressure"
        elif high_damage:
            label = "Severe Damage Clusters"
        else:
            label = "Lower Priority Recovery Zones"

        profile_map[int(cluster_id)] = label
    return profile_map


def apply_unsupervised_clustering(hex_gdf):
    """
    Cluster zones into natural groups using ML.
    Adds:
    - ml_cluster
    - ml_cluster_profile
    """
    if hex_gdf is None or hex_gdf.empty:
        return hex_gdf

    feature_cols = [
        'damage_count',
        'population_density',
        'hospitals_count',
        'major_hospitals_count',
        'water_util_count',
        'streets_count',
        'road_damage_severity',
        'street_centrality_sum',
        'street_impedance_sum',
        'critical_streets_count',
        'ai_score'
    ]
    available = [c for c in feature_cols if c in hex_gdf.columns]
    if not available:
        hex_gdf['ml_cluster'] = -1
        hex_gdf['ml_cluster_profile'] = "Unclustered"
        return hex_gdf

    if not SKLEARN_AVAILABLE:
        # Lightweight fallback: one cluster for continuity when sklearn is unavailable.
        hex_gdf['ml_cluster'] = 0
        hex_gdf['ml_cluster_profile'] = "Unclustered (scikit-learn missing)"
        return hex_gdf

    X = hex_gdf[available].fillna(0).astype(float).values
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    n_samples = len(hex_gdf)
    k = min(6, max(3, int(np.sqrt(max(n_samples, 1) / 2))))

    # Prefer KMeans for full partitioning, fallback to DBSCAN for irregular structure.
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(Xs)

    # If KMeans collapsed to one group behaviorally, try DBSCAN.
    unique_labels = set(labels.tolist())
    if len(unique_labels) <= 1:
        dbscan = DBSCAN(eps=1.1, min_samples=max(5, n_samples // 40))
        labels = dbscan.fit_predict(Xs)

    hex_gdf['ml_cluster'] = labels.astype(int)
    profile_map = _profile_clusters(hex_gdf, available)
    hex_gdf['ml_cluster_profile'] = hex_gdf['ml_cluster'].map(profile_map).fillna("Unclustered/Outlier")

    return hex_gdf

# ======================================================
# Scoring Pipeline
# ======================================================

def apply_scoring_pipeline(hex_gdf, damage_analysis):
    """Apply complete scoring pipeline to hexagonal grid data"""
    print("   - Applying enhanced age ranking...")

    # Calculate age scores
    hex_gdf['damage_age_score'] = hex_gdf.apply(calculate_age_score, axis=1)

    # Define feature columns for normalization
    feature_columns = [
        'damage_count', 'major_hospitals_count', 'hospitals_count', 'water_util_count', 'fuel_util_count',
        'streets_count', 'schools_count', 'universities_count', 'population_density', 'education_count',
        'damage_age_score', 'street_centrality_sum', 'street_impedance_sum', 'critical_streets_count'
    ]

    # Filter to existing columns
    available_features = [col for col in feature_columns if col in hex_gdf.columns]

    if available_features:
        print(f"   - Normalizing {len(available_features)} features...")
        normalized_features = normalize_features(hex_gdf, available_features)

        # Calculate AI scores
        print("   - Calculating AI-enhanced scores...")
        hex_gdf['ai_score'] = hex_gdf.apply(
            lambda row: calculate_ai_score(row, normalized_features), axis=1
        )
    else:
        print("   - Warning: No feature columns available for normalization")
        hex_gdf['ai_score'] = 0.0

    # Calculate final priority ranks
    print("   - Calculating final priority rankings...")
    hex_gdf['priority_rank'] = hex_gdf.apply(calculate_priority_rank, axis=1)

    # ML clustering for natural zone classes
    print("   - Clustering zones with unsupervised ML...")
    hex_gdf = apply_unsupervised_clustering(hex_gdf)

    # Sort by priority
    hex_gdf = hex_gdf.sort_values('priority_rank', ascending=False).reset_index(drop=True)

    print(f"   - Scoring complete: {len(hex_gdf)} zones prioritized")

    return hex_gdf
