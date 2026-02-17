# ======================================================
# interactive_charts.py - Interactive Animated Visualizations
# ======================================================

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime

def create_interactive_dashboard(hex_gdf, projects_df, damage_analysis, infrastructure_layers=None, output_path=None):
    """Create comprehensive interactive dashboard with animated charts"""

    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"gaza_interactive_dashboard_{timestamp}.html"

    use_clusters = 'ml_cluster' in hex_gdf.columns and 'ml_cluster_profile' in hex_gdf.columns

    municipality_damage = hex_gdf.groupby('primary_municipality').agg({
        'damage_count': 'sum',
        'ai_score': 'mean',
        'population_total': 'sum'
    }).reset_index().sort_values('damage_count', ascending=False)

    fig = make_subplots(
        rows=3, cols=2,
        subplot_titles=(
            'Damage by Municipality',
            'Priority Zones (ML Cluster-Aware)',
            'Project Cost by Type',
            'Timeline Distribution',
            'Population vs Damage (Clustered)',
            'Rebuilding Strategy Distribution'
        ),
        specs=[
            [{"type": "bar"}, {"type": "scatter"}],
            [{"type": "bar"}, {"type": "box"}],
            [{"type": "scatter"}, {"type": "pie"}]
        ],
        vertical_spacing=0.12,
        horizontal_spacing=0.15
    )

    fig.add_trace(
        go.Bar(
            x=municipality_damage['primary_municipality'],
            y=municipality_damage['damage_count'],
            marker=dict(color=municipality_damage['damage_count'], colorscale='Reds', showscale=True),
            text=municipality_damage['damage_count'],
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Damage: %{y:,}<extra></extra>'
        ),
        row=1, col=1
    )

    top_zones = hex_gdf.head(50)
    marker_color = top_zones['ml_cluster'] if use_clusters else top_zones['ai_score']
    marker_scale = 'Turbo' if use_clusters else 'RdYlGn_r'
    marker_title = 'Cluster ID' if use_clusters else 'AI Score'

    fig.add_trace(
        go.Scatter(
            x=list(range(1, len(top_zones) + 1)),
            y=top_zones['ai_score'],
            mode='markers+lines',
            marker=dict(
                size=(top_zones['damage_count'].fillna(0) / 10).clip(lower=6),
                color=marker_color,
                colorscale=marker_scale,
                showscale=True,
                colorbar=dict(title=marker_title, x=1.02),
                line=dict(width=1, color='white')
            ),
            text=top_zones['zone_id'],
            customdata=top_zones['ml_cluster_profile'] if use_clusters else None,
            hovertemplate='<b>Zone: %{text}</b><br>Rank: %{x}<br>AI: %{y:.3f}' + ('<br>Cluster: %{customdata}' if use_clusters else '') + '<extra></extra>'
        ),
        row=1, col=2
    )

    if projects_df is not None and not projects_df.empty and 'Estimated_Cost' in projects_df.columns:
        project_costs = projects_df.groupby('Infrastructure_Type').agg({
            'Estimated_Cost': lambda x: pd.to_numeric(x.astype(str).str.replace(r'[$,]', '', regex=True), errors='coerce').sum()
        }).reset_index().sort_values('Estimated_Cost', ascending=True)

        fig.add_trace(
            go.Bar(
                y=project_costs['Infrastructure_Type'],
                x=project_costs['Estimated_Cost'],
                orientation='h',
                marker=dict(color=project_costs['Estimated_Cost'], colorscale='Viridis', showscale=True),
                text=[f'${x:,.0f}' for x in project_costs['Estimated_Cost']],
                textposition='outside'
            ),
            row=2, col=1
        )

    if projects_df is not None and not projects_df.empty and 'Timeline_Months' in projects_df.columns:
        fig.add_trace(
            go.Box(
                y=projects_df['Timeline_Months'],
                x=projects_df['Infrastructure_Type'] if 'Infrastructure_Type' in projects_df.columns else None,
                boxmean='sd',
                marker=dict(color='#FF6B6B')
            ),
            row=2, col=2
        )

    pop_color = hex_gdf['ml_cluster'] if use_clusters else hex_gdf['ai_score']
    pop_scale = 'Turbo' if use_clusters else 'Plasma'
    pop_title = 'Cluster ID' if use_clusters else 'Priority'
    pop_text = hex_gdf['ml_cluster_profile'] if use_clusters else hex_gdf['primary_municipality']

    fig.add_trace(
        go.Scatter(
            x=hex_gdf['population_density'],
            y=hex_gdf['damage_count'],
            mode='markers',
            marker=dict(
                size=8,
                color=pop_color,
                colorscale=pop_scale,
                showscale=True,
                colorbar=dict(title=pop_title, x=1.02, y=0.15),
                opacity=0.6,
                line=dict(width=0.5, color='white')
            ),
            text=pop_text,
            hovertemplate='<b>%{text}</b><br>Density: %{x:,.0f}<br>Damage: %{y}<extra></extra>'
        ),
        row=3, col=1
    )

    strategy_counts = hex_gdf['rebuilding_strategy'].apply(
        lambda x: x.get('strategy', 'Unknown') if isinstance(x, dict) else 'Unknown'
    ).value_counts()

    fig.add_trace(
        go.Pie(
            labels=strategy_counts.index,
            values=strategy_counts.values,
            marker=dict(colors=['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8'])
        ),
        row=3, col=2
    )

    fig.update_layout(
        title={'text': 'Gaza Reconstruction Interactive Dashboard (ML Clustering)', 'x': 0.5, 'xanchor': 'center'},
        showlegend=False,
        height=1400,
        template='plotly_white',
        font=dict(family='Arial', size=11),
        hovermode='closest'
    )

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(fig.to_html())
    print(f"   - Interactive dashboard saved to {output_path}")
    return output_path

def create_damage_animation(hex_gdf, output_path=None):
    """Create cluster-based animated damage visualization"""

    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"gaza_damage_animation_{timestamp}.html"

    use_clusters = 'ml_cluster' in hex_gdf.columns and 'ml_cluster_profile' in hex_gdf.columns

    if use_clusters:
        grp = hex_gdf.groupby(['ml_cluster', 'ml_cluster_profile'], dropna=False).agg({
            'damage_count': 'sum',
            'population_total': 'sum',
            'zone_id': 'count',
            'ai_score': 'mean'
        }).reset_index().rename(columns={'zone_id': 'Zones'})
        grp = grp.sort_values('damage_count', ascending=False)
        x_vals = grp['ml_cluster_profile']
        bar_color = grp['ml_cluster']
        color_title = 'Cluster ID'
    else:
        grp = hex_gdf.groupby('primary_municipality', dropna=False).agg({
            'damage_count': 'sum',
            'population_total': 'sum',
            'zone_id': 'count',
            'ai_score': 'mean'
        }).reset_index().rename(columns={'zone_id': 'Zones'})
        grp = grp.sort_values('damage_count', ascending=False)
        x_vals = grp['primary_municipality']
        bar_color = grp['damage_count']
        color_title = 'Damage'

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=x_vals,
        y=grp['damage_count'],
        marker=dict(color=bar_color, colorscale='Turbo', showscale=True, colorbar=dict(title=color_title)),
        text=grp['damage_count'],
        textposition='outside',
        customdata=grp[['Zones', 'population_total', 'ai_score']],
        hovertemplate='<b>%{x}</b><br>Damage: %{y:,}<br>Zones: %{customdata[0]}<br>Population: %{customdata[1]:,.0f}<br>Avg AI: %{customdata[2]:.3f}<extra></extra>'
    ))

    fig.update_layout(
        title={'text': 'Damage Distribution by Natural Clusters', 'x': 0.5, 'xanchor': 'center'},
        xaxis_title='Cluster' if use_clusters else 'Municipality',
        yaxis_title='Total Damage',
        template='plotly_white',
        height=600,
        font=dict(family='Arial', size=13),
        xaxis_tickangle=-45
    )

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(fig.to_html())
    print(f"   - Damage animation saved to {output_path}")
    return output_path

def create_reconstruction_timeline(projects_df, hex_gdf, output_path=None):
    """Create interactive reconstruction timeline"""
    
    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"gaza_reconstruction_timeline_{timestamp}.html"
    
    if projects_df is None or projects_df.empty:
        print("   - No projects data for timeline")
        return None
    
    # Prepare timeline data
    projects_df['Start_Month'] = 0
    projects_df['End_Month'] = projects_df['Timeline_Months']
    
    # Create Gantt-style chart
    fig = go.Figure()
    
    colors = {
        'Healthcare': '#E74C3C',
        'Education': '#3498DB',
        'Universities': '#9B59B6',
        'Transportation': '#F39C12',
        'Municipal': '#1ABC9C',
        'Utilities': '#27AE60'
    }
    
    for idx, project in projects_df.head(30).iterrows():
        infra_type = project.get('Infrastructure_Type', 'Unknown')
        color = colors.get(infra_type, '#95A5A6')
        
        fig.add_trace(go.Bar(
            x=[project['Timeline_Months']],
            y=[f"#{project.get('Final_Priority_Rank', idx+1)} - {project.get('Municipality', 'Unknown')}"],
            orientation='h',
            name=infra_type,
            marker=dict(color=color),
            text=f"{project['Timeline_Months']} شهر",
            textposition='inside',
            hovertemplate=f"<b>{infra_type}</b><br>" +
                         f"المحافظة: {project.get('Municipality', 'Unknown')}<br>" +
                         f"المدة: {project['Timeline_Months']} شهر<br>" +
                         f"التكلفة: {project.get('Estimated_Cost', 'N/A')}<extra></extra>",
            showlegend=idx < 6
        ))
    
    fig.update_layout(
        title={
            'text': '🏗️ الجدول الزمني لمشاريع إعادة الإعمار - أعلى 30 أولوية',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20, 'color': '#2C3E50'}
        },
        xaxis_title="المدة الزمنية (شهر)",
        yaxis_title="المشروع",
        template='plotly_white',
        height=900,
        font=dict(family='Arial', size=11),
        barmode='overlay',
        legend=dict(
            title="نوع البنية التحتية",
            orientation="v",
            x=1.02,
            y=1
        )
    )
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(fig.to_html())
    print(f"   - Reconstruction timeline saved to {output_path}")
    return output_path


def create_3d_damage_visualization(hex_gdf, output_path=None):
    """Create 3D visualization of damage and priorities (cluster-aware)"""

    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"gaza_3d_visualization_{timestamp}.html"

    rep = hex_gdf.geometry.representative_point()
    hex_gdf = hex_gdf.copy()
    hex_gdf['lon'] = rep.x
    hex_gdf['lat'] = rep.y

    use_clusters = 'ml_cluster' in hex_gdf.columns
    marker_color = hex_gdf['ml_cluster'] if use_clusters else hex_gdf['ai_score']
    color_title = 'Cluster ID' if use_clusters else 'AI Score'

    fig = go.Figure(data=[go.Scatter3d(
        x=hex_gdf['lon'],
        y=hex_gdf['lat'],
        z=hex_gdf['damage_count'],
        mode='markers',
        marker=dict(
            size=5,
            color=marker_color,
            colorscale='Turbo',
            showscale=True,
            colorbar=dict(title=color_title),
            opacity=0.8,
            line=dict(width=0.5, color='white')
        ),
        text=hex_gdf['zone_id'],
        customdata=hex_gdf['ml_cluster_profile'] if 'ml_cluster_profile' in hex_gdf.columns else None,
        hovertemplate='<b>Zone: %{text}</b><br>Damage: %{z}<br>Color: %{marker.color}<br>' + ('Cluster: %{customdata}<br>' if 'ml_cluster_profile' in hex_gdf.columns else '') + '<extra></extra>'
    )])

    fig.update_layout(
        title={'text': '3D Damage and Priority Visualization (ML Clusters)', 'x': 0.5, 'xanchor': 'center'},
        scene=dict(
            xaxis_title='Longitude',
            yaxis_title='Latitude',
            zaxis_title='Damage Sites',
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.3))
        ),
        height=700,
        template='plotly_dark'
    )

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(fig.to_html())
    print(f"   - 3D visualization saved to {output_path}")
    return output_path