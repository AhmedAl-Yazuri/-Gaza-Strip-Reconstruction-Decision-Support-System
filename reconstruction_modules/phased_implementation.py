# ======================================================
# phased_implementation.py - Multi-Phase Project Implementation
# ======================================================

import pandas as pd
import re
from datetime import datetime
from config import COST_ESTIMATES


def _is_arabic_column_name(name):
    """Return True if a column name contains Arabic characters."""
    if name is None:
        return False
    return re.search(r"[\u0600-\u06FF]", str(name)) is not None


def assign_project_phases(projects_df, num_phases=4):
    """Assign projects across phased implementation timelines."""

    if projects_df is None or projects_df.empty:
        return None

    total_projects = len(projects_df)
    projects_per_phase = total_projects // num_phases

    projects_df['Phase'] = 0
    projects_df['Phase_Name'] = ''
    projects_df['Phase_Start_Month'] = 0
    projects_df['Phase_End_Month'] = 0

    phase_names = {
        1: 'Phase 1 - Emergency',
        2: 'Phase 2 - Essential Services',
        3: 'Phase 3 - Development',
        4: 'Phase 4 - Optimization'
    }

    phase_durations = {
        1: (0, 12),      # 0-12 months
        2: (12, 30),     # 12-30 months
        3: (30, 54),     # 30-54 months
        4: (54, 84)      # 54-84 months
    }

    for phase in range(1, num_phases + 1):
        start_idx = (phase - 1) * projects_per_phase
        if phase == num_phases:
            end_idx = total_projects
        else:
            end_idx = phase * projects_per_phase

        projects_df.loc[start_idx:end_idx-1, 'Phase'] = phase
        projects_df.loc[start_idx:end_idx-1, 'Phase_Name'] = phase_names[phase]
        projects_df.loc[start_idx:end_idx-1, 'Phase_Start_Month'] = phase_durations[phase][0]
        projects_df.loc[start_idx:end_idx-1, 'Phase_End_Month'] = phase_durations[phase][1]

    print(f"   - Assigned {total_projects} projects across {num_phases} phases")

    return projects_df



def export_phased_excel(projects_df, output_path=None):
    """Export phased projects to Excel."""

    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"gaza_phased_projects_{timestamp}.xlsx"

    if projects_df is None or projects_df.empty:
        print("   - WARNING: No projects available for phased Excel export")
        return None

    export_df = projects_df.copy()

    if 'Latitude' not in export_df.columns and 'lat' in export_df.columns:
        export_df['Latitude'] = export_df['lat']
    if 'Longitude' not in export_df.columns and 'lon' in export_df.columns:
        export_df['Longitude'] = export_df['lon']

    area_sources = ['Municipality', 'primary_municipality', 'Governorate', 'municipality']
    if 'Area_Name' not in export_df.columns:
        area_name = pd.Series('Unknown', index=export_df.index, dtype='object')
        for col in area_sources:
            if col in export_df.columns:
                values = export_df[col].astype(str).str.strip()
                valid = values.ne('') & values.ne('nan') & values.ne('None') & values.ne('Unknown')
                area_name = area_name.where(~valid, values)
        export_df['Area_Name'] = area_name

    export_df = _drop_redundant_export_columns(export_df)

    preferred_order = [
        'Project_ID',
        'Project_Name',
        'Reference_Point_Type',
        'Reference_Point_Name',
        'Latitude',
        'Longitude',
        'Area_Name',
        'Municipality',
        'Zone_ID'
    ]
    existing_preferred = [col for col in preferred_order if col in export_df.columns]
    remaining_cols = [col for col in export_df.columns if col not in existing_preferred]
    export_df = export_df[existing_preferred + remaining_cols]

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        export_df.to_excel(writer, sheet_name='All Projects', index=False)

        agg_map = {'Project_ID': 'count'}
        if 'Timeline_Months' in export_df.columns:
            agg_map['Timeline_Months'] = 'mean'
        if 'Phase_Start_Month' in export_df.columns:
            agg_map['Phase_Start_Month'] = 'first'
        if 'Phase_End_Month' in export_df.columns:
            agg_map['Phase_End_Month'] = 'first'

        phase_summary = export_df.groupby(['Phase', 'Phase_Name']).agg(agg_map).reset_index()
        phase_summary.to_excel(writer, sheet_name='Phase Summary', index=False)

        for phase in sorted(export_df['Phase'].unique()):
            phase_projects = export_df[export_df['Phase'] == phase]
            sheet_name = f"Phase {phase}"
            phase_projects.to_excel(writer, sheet_name=sheet_name, index=False)

    print(f"   - Phased projects Excel saved to {output_path}")
    return output_path


def _drop_redundant_export_columns(df):
    """Drop columns that are duplicated by name or fully duplicated by content."""
    if df is None or df.empty:
        return df

    out = df.copy()

    drop_if_exists = ['Estimated_Cost']
    out = out.drop(columns=[c for c in drop_if_exists if c in out.columns], errors='ignore')
    out = out.loc[:, ~out.columns.duplicated(keep='first')]

    arabic_cols = [col for col in out.columns if _is_arabic_column_name(col)]
    if arabic_cols:
        out = out.drop(columns=arabic_cols)

    def _normalized(series):
        return series.astype('string').fillna('<NA>').str.strip()

    kept = []
    for col in list(out.columns):
        duplicate = False
        for kcol in kept:
            if _normalized(out[col]).equals(_normalized(out[kcol])):
                duplicate = True
                break
        if not duplicate:
            kept.append(col)

    return out[kept]
