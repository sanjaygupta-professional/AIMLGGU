#!/usr/bin/env python3
"""
Team Performance Analysis Generator
Generates dashboard and coaching report from team performance CSV

Usage:
    python generate_team_analysis.py <csv_file_path>

Example:
    python generate_team_analysis.py MyTeamProductivity20251108.csv
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import sys
import os
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

class TeamPerformanceAnalyzer:
    """Analyzes team performance data and generates reports"""

    def __init__(self, csv_file):
        self.csv_file = csv_file
        self.df = None
        self.df_clean = None
        self.team_name = None
        self.stats = {}

    def read_and_clean_data(self):
        """Read CSV and clean data"""
        print(f"Reading CSV data from: {self.csv_file}")
        self.df = pd.read_csv(self.csv_file, encoding='utf-8-sig')

        # Extract team name from first row
        self.team_name = str(self.df.iloc[0]['Team']).strip()
        print(f"Team name: {self.team_name}")

        # Clean the data - replace "/" and "#VALUE!" with NaN
        print("Cleaning data...")
        self.df = self.df.replace('/', np.nan)
        self.df = self.df.replace('#VALUE!', np.nan)
        self.df['Inflation correction'] = self.df['Inflation correction'].replace('', np.nan)

        # Convert numeric columns
        numeric_cols = ['Target Velocity', 'Committed SP', 'Delivered SP', 'Inflation correction',
                        'Normalized Target Velocity', 'Normalized Planned SP', 'Normalized Delivered SP',
                        'Normalized Inflation SP']

        for col in numeric_cols:
            if col in self.df.columns:
                self.df[col] = pd.to_numeric(self.df[col], errors='coerce')

        # Fill NaN inflation corrections with 0
        self.df['Inflation correction'] = self.df['Inflation correction'].fillna(0)

        # Convert percentage columns
        def clean_percentage(val):
            if pd.isna(val):
                return np.nan
            if isinstance(val, str):
                return float(val.strip('%')) / 100 if '%' in val else float(val)
            return val

        self.df['Productivity_num'] = self.df['Productivity'].apply(clean_percentage)
        self.df['Predictability_num'] = self.df['Predictability'].apply(clean_percentage)

        # Filter to rows with actual data
        self.df_clean = self.df[self.df['Productivity_num'].notna()].copy()

        print(f"Total sprints in file: {len(self.df)}")
        print(f"Sprints with complete data: {len(self.df_clean)}")

    def calculate_statistics(self):
        """Calculate performance statistics"""
        df = self.df_clean

        # Overall statistics
        avg_productivity = df['Productivity_num'].mean()
        avg_predictability = df['Predictability_num'].mean()
        std_productivity = df['Productivity_num'].std()
        cv_productivity = (std_productivity / avg_productivity) * 100

        # Find model transition (significant change in Target Velocity)
        velocities = df['Target Velocity'].unique()
        transition_sprint = None
        old_velocity = None
        new_velocity = None

        if len(velocities) > 1:
            # Find where velocity changes
            for i in range(1, len(df)):
                if df.iloc[i]['Target Velocity'] != df.iloc[i-1]['Target Velocity']:
                    transition_sprint = df.iloc[i]['Sprint']
                    old_velocity = df.iloc[i-1]['Target Velocity']
                    new_velocity = df.iloc[i]['Target Velocity']
                    break

        # Phase analysis
        if old_velocity is not None:
            old_model = df[df['Target Velocity'] == old_velocity]
            new_model = df[df['Target Velocity'] == new_velocity]
        else:
            old_model = df
            new_model = pd.DataFrame()
            old_velocity = df['Target Velocity'].iloc[0]

        # Inflation analysis
        total_inflation = df['Inflation correction'].sum()
        inflation_count = len(df[df['Inflation correction'] != 0])

        self.stats = {
            'avg_productivity': avg_productivity,
            'avg_predictability': avg_predictability,
            'std_productivity': std_productivity,
            'cv_productivity': cv_productivity,
            'min_productivity': df['Productivity_num'].min(),
            'max_productivity': df['Productivity_num'].max(),
            'min_predictability': df['Predictability_num'].min(),
            'max_predictability': df['Predictability_num'].max(),
            'avg_committed': df['Committed SP'].mean(),
            'avg_delivered': df['Delivered SP'].mean(),
            'total_inflation': total_inflation,
            'inflation_count': inflation_count,
            'total_sprints': len(df),
            'transition_sprint': transition_sprint,
            'old_velocity': old_velocity,
            'new_velocity': new_velocity,
            'old_model': old_model,
            'new_model': new_model,
            'old_model_productivity': old_model['Productivity_num'].mean() if len(old_model) > 0 else None,
            'old_model_predictability': old_model['Predictability_num'].mean() if len(old_model) > 0 else None,
            'new_model_productivity': new_model['Productivity_num'].mean() if len(new_model) > 0 else None,
            'new_model_predictability': new_model['Predictability_num'].mean() if len(new_model) > 0 else None,
        }

        # Print statistics
        print(f"\n{'='*60}")
        print("STATISTICS SUMMARY")
        print(f"{'='*60}")
        print(f"Average Productivity: {avg_productivity:.1%}")
        print(f"Average Predictability: {avg_predictability:.1%}")
        print(f"Coefficient of Variation: {cv_productivity:.1f}%")
        print(f"Total Inflation: {total_inflation:.0f} SP across {inflation_count} sprints")

        if transition_sprint:
            print(f"\nModel Transition at: {transition_sprint}")
            print(f"  {old_velocity} SP → {new_velocity} SP")
            print(f"  Old Model Productivity: {self.stats['old_model_productivity']:.1%}")
            print(f"  New Model Productivity: {self.stats['new_model_productivity']:.1%}")

    def generate_dashboard(self):
        """Generate 7-chart performance dashboard"""
        print("\nGenerating performance dashboard...")

        df = self.df_clean
        stats = self.stats

        fig = plt.figure(figsize=(20, 12))
        gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.3)

        # Define colors
        color_primary = '#1f77b4'
        color_secondary = '#ff7f0e'
        color_success = '#2ca02c'
        color_danger = '#d62728'
        color_old = '#ff6b6b'
        color_new = '#51cf66'

        # Find transition point for visualization
        transition_idx = None
        transition_pos = None
        if stats['transition_sprint']:
            if stats['transition_sprint'] in df['Sprint'].values:
                transition_idx = df[df['Sprint'] == stats['transition_sprint']].index[0]
                transition_pos = df.index.get_loc(transition_idx)

        # Chart 1: Productivity Trend Line (Top Left, spans 2 columns)
        ax1 = fig.add_subplot(gs[0, :2])
        ax1.plot(df['Sprint'], df['Productivity_num'] * 100,
                 marker='o', linewidth=2.5, markersize=8, color=color_primary, label='Productivity')
        ax1.fill_between(range(len(df)), df['Productivity_num'] * 100, alpha=0.3, color=color_primary)
        ax1.axhline(y=stats['avg_productivity'] * 100, color=color_success, linestyle='--', linewidth=2,
                    label=f'Average ({stats["avg_productivity"]:.0%})', alpha=0.7)

        if transition_pos is not None:
            ax1.axvline(x=transition_pos, color=color_danger, linestyle='--', linewidth=2.5,
                        label=f'Model Transition ({stats["old_velocity"]:.1f}→{stats["new_velocity"]:.1f} SP)', alpha=0.8)

        ax1.set_title('Productivity Trend Over Sprints', fontsize=16, fontweight='bold', pad=15)
        ax1.set_xlabel('Sprint', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Productivity (%)', fontsize=12, fontweight='bold')
        ax1.legend(fontsize=10, loc='best')
        ax1.grid(True, alpha=0.3)
        ax1.set_ylim([0, max(df['Productivity_num'] * 100) * 1.2])
        ax1.tick_params(axis='both', labelsize=8, width=1.5)
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right', fontweight='bold')
        plt.setp(ax1.yaxis.get_majorticklabels(), fontweight='bold')

        # Chart 2: Predictability Trend Line (Top Right)
        ax2 = fig.add_subplot(gs[0, 2])
        ax2.plot(df['Sprint'], df['Predictability_num'] * 100,
                 marker='s', linewidth=2.5, markersize=7, color=color_secondary, label='Predictability')
        ax2.axhline(y=stats['avg_predictability'] * 100, color=color_success, linestyle='--', linewidth=2,
                    label=f'Average ({stats["avg_predictability"]:.0%})', alpha=0.7)

        if transition_pos is not None:
            ax2.axvline(x=transition_pos, color=color_danger, linestyle='--', linewidth=2, alpha=0.8)

        ax2.set_title('Predictability Evolution', fontsize=14, fontweight='bold', pad=15)
        ax2.set_xlabel('Sprint', fontsize=11, fontweight='bold')
        ax2.set_ylabel('Predictability (%)', fontsize=11, fontweight='bold')
        ax2.legend(fontsize=9, loc='best')
        ax2.grid(True, alpha=0.3)
        y_max = max(105, max(df['Predictability_num'] * 100) * 1.1)
        ax2.set_ylim([0, y_max])
        ax2.tick_params(axis='both', labelsize=8, width=1.5)
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right', fontweight='bold')
        plt.setp(ax2.yaxis.get_majorticklabels(), fontweight='bold')

        # Chart 3: Commitment vs Delivery Bar Chart (Middle Left, spans 2 columns)
        ax3 = fig.add_subplot(gs[1, :2])
        x_pos = np.arange(len(df))
        width = 0.35

        bars1 = ax3.bar(x_pos - width/2, df['Committed SP'], width,
                        label='Committed SP', color=color_secondary, alpha=0.8)
        bars2 = ax3.bar(x_pos + width/2, df['Delivered SP'], width,
                        label='Delivered SP', color=color_primary, alpha=0.8)

        if transition_pos is not None:
            ax3.axvline(x=transition_pos, color=color_danger, linestyle='--', linewidth=2.5,
                        label='Model Transition', alpha=0.8)

        ax3.set_title('Commitment vs Delivery Comparison', fontsize=16, fontweight='bold', pad=15)
        ax3.set_xlabel('Sprint', fontsize=12, fontweight='bold')
        ax3.set_ylabel('Story Points', fontsize=12, fontweight='bold')
        ax3.set_xticks(x_pos)
        ax3.set_xticklabels(df['Sprint'], rotation=45, ha='right')
        ax3.legend(fontsize=10, loc='best')
        ax3.grid(True, alpha=0.3, axis='y')
        ax3.tick_params(axis='both', labelsize=8, width=1.5)
        plt.setp(ax3.xaxis.get_majorticklabels(), fontweight='bold')
        plt.setp(ax3.yaxis.get_majorticklabels(), fontweight='bold')

        # Chart 4: Model Comparison Box Plot (Middle Right)
        ax4 = fig.add_subplot(gs[1, 2])
        old_model = stats['old_model']
        new_model = stats['new_model']

        if len(old_model) > 0 and len(new_model) > 0:
            box_data = [old_model['Productivity_num'] * 100, new_model['Productivity_num'] * 100]
            bp = ax4.boxplot(box_data, labels=[f'Old Model\n({stats["old_velocity"]:.1f} SP)',
                                                f'New Model\n({stats["new_velocity"]:.1f} SP)'],
                             patch_artist=True, widths=0.6)
            bp['boxes'][0].set_facecolor(color_old)
            bp['boxes'][1].set_facecolor(color_new)
            for box in bp['boxes']:
                box.set_alpha(0.7)
        else:
            ax4.text(0.5, 0.5, 'No model transition\ndetected',
                     ha='center', va='center', fontsize=12, transform=ax4.transAxes)

        ax4.set_title('Productivity by Model', fontsize=14, fontweight='bold', pad=15)
        ax4.set_ylabel('Productivity (%)', fontsize=11, fontweight='bold')
        ax4.grid(True, alpha=0.3, axis='y')
        ax4.tick_params(axis='both', labelsize=8, width=1.5)
        plt.setp(ax4.xaxis.get_majorticklabels(), fontweight='bold')
        plt.setp(ax4.yaxis.get_majorticklabels(), fontweight='bold')

        # Chart 5: Inflation Corrections Horizontal Bar (Bottom Left)
        ax5 = fig.add_subplot(gs[2, 0])
        colors_inflation = [color_danger if x < 0 else color_success if x > 0 else 'gray'
                            for x in df['Inflation correction']]
        ax5.barh(df['Sprint'], df['Inflation correction'], color=colors_inflation, alpha=0.7)
        ax5.set_title('Inflation Corrections', fontsize=14, fontweight='bold', pad=15)
        ax5.set_xlabel('Story Points', fontsize=11, fontweight='bold')
        ax5.set_ylabel('Sprint', fontsize=11, fontweight='bold')
        ax5.axvline(x=0, color='black', linewidth=1)
        ax5.grid(True, alpha=0.3, axis='x')
        ax5.invert_yaxis()
        ax5.tick_params(axis='both', labelsize=8, width=1.5)
        plt.setp(ax5.xaxis.get_majorticklabels(), fontweight='bold')
        plt.setp(ax5.yaxis.get_majorticklabels(), fontweight='bold')

        # Chart 6: Productivity vs Predictability Scatter (Bottom Center)
        ax6 = fig.add_subplot(gs[2, 1])
        if len(old_model) > 0:
            ax6.scatter(old_model['Productivity_num'] * 100, old_model['Predictability_num'] * 100,
                        s=120, c=color_old, alpha=0.7, label='Old Model', edgecolors='black', linewidth=1)
        if len(new_model) > 0:
            ax6.scatter(new_model['Productivity_num'] * 100, new_model['Predictability_num'] * 100,
                        s=120, c=color_new, alpha=0.7, label='New Model', edgecolors='black', linewidth=1)
        if len(new_model) == 0:
            ax6.scatter(df['Productivity_num'] * 100, df['Predictability_num'] * 100,
                        s=120, c=color_primary, alpha=0.7, label='All Sprints', edgecolors='black', linewidth=1)

        # Add quadrant lines
        ax6.axhline(y=stats['avg_predictability'] * 100, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        ax6.axvline(x=stats['avg_productivity'] * 100, color='gray', linestyle='--', linewidth=1, alpha=0.5)

        ax6.set_title('Productivity vs Predictability', fontsize=14, fontweight='bold', pad=15)
        ax6.set_xlabel('Productivity (%)', fontsize=11, fontweight='bold')
        ax6.set_ylabel('Predictability (%)', fontsize=11, fontweight='bold')
        ax6.legend(fontsize=9, loc='best')
        ax6.grid(True, alpha=0.3)
        ax6.tick_params(axis='both', labelsize=8, width=1.5)
        plt.setp(ax6.xaxis.get_majorticklabels(), fontweight='bold')
        plt.setp(ax6.yaxis.get_majorticklabels(), fontweight='bold')

        # Chart 7: Moving Average Trends (Bottom Right)
        ax7 = fig.add_subplot(gs[2, 2])
        ax7.plot(df['Sprint'], df['Productivity_num'] * 100,
                 marker='o', linewidth=2, markersize=6, alpha=0.5, label='Actual', color=color_primary)

        # Calculate moving averages
        ma2 = df['Productivity_num'].rolling(window=2).mean() * 100
        ma3 = df['Productivity_num'].rolling(window=3).mean() * 100

        ax7.plot(df['Sprint'], ma2, linewidth=2.5, label='MA(2)', color=color_secondary)
        ax7.plot(df['Sprint'], ma3, linewidth=2.5, label='MA(3)', color=color_success, linestyle='--')

        ax7.set_title('Moving Averages', fontsize=14, fontweight='bold', pad=15)
        ax7.set_xlabel('Sprint', fontsize=11, fontweight='bold')
        ax7.set_ylabel('Productivity (%)', fontsize=11, fontweight='bold')
        ax7.legend(fontsize=9, loc='best')
        ax7.grid(True, alpha=0.3)
        ax7.tick_params(axis='both', labelsize=8, width=1.5)
        plt.setp(ax7.xaxis.get_majorticklabels(), rotation=45, ha='right', fontweight='bold')
        plt.setp(ax7.yaxis.get_majorticklabels(), fontweight='bold')

        # Add main title
        team_name_clean = self.team_name.replace(' ', '').replace('-', '')
        fig.suptitle(f'{self.team_name} Team Performance Dashboard',
                     fontsize=20, fontweight='bold', y=0.98)

        # Save dashboard
        output_file = f'{team_name_clean}_Performance_Dashboard.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"Dashboard saved: {output_file}")
        plt.close()

        return output_file

    def generate_markdown_report(self):
        """Generate coaching-focused markdown analysis report"""
        print("\nGenerating markdown analysis report...")

        df = self.df_clean
        stats = self.stats
        team_name_clean = self.team_name.replace(' ', '').replace('-', '')

        # Determine sprint range
        first_sprint = df.iloc[0]['Sprint']
        last_sprint = df.iloc[-1]['Sprint']

        # Analyze key patterns
        productivity_status = "exceeding 75-85% benchmark" if stats['avg_productivity'] > 0.75 else "below 75-85% benchmark"
        cv_status = "mature and stable" if stats['cv_productivity'] < 15 else "volatile and unstable"
        inflation_frequency = stats['inflation_count'] / stats['total_sprints']

        # Generate report
        report = f"""# {self.team_name} Team Performance Analysis Report
**Sprint Range:** {first_sprint} to {last_sprint} ({stats['total_sprints']} sprints)
**Team:** {self.team_name}
**Analysis Date:** {datetime.now().strftime('%Y-%m-%d')}

---

## Executive Summary

**Key Findings:**
- **Productivity:** {stats['avg_productivity']:.1%} average ({productivity_status})
- **Predictability:** {stats['avg_predictability']:.1%} average
- **Volatility:** {stats['cv_productivity']:.1f}% coefficient of variation ({cv_status}, benchmark: <15%)
- **Inflation:** {stats['total_inflation']:.0f} SP across {stats['inflation_count']} sprints ({inflation_frequency:.0%} of sprints)
"""

        if stats['transition_sprint']:
            productivity_change = stats['new_model_productivity'] - stats['old_model_productivity']
            change_direction = "improved" if productivity_change > 0 else "declined"
            report += f"- **Model Transition Impact:** Productivity {change_direction} from {stats['old_model_productivity']:.1%} to {stats['new_model_productivity']:.1%} after switching from {stats['old_velocity']:.1f} SP to {stats['new_velocity']:.1f} SP at {stats['transition_sprint']}\n"

        # EBP Readiness Assessment
        ebp_ready = (stats['cv_productivity'] < 15 and
                     stats['avg_productivity'] > 0.70 and
                     inflation_frequency < 0.3)

        report += f"\n**Bottom Line:** "
        if ebp_ready:
            report += f"Team demonstrates stable performance and is ready for Epic-Based Pricing consideration.\n"
        else:
            issues = []
            if stats['cv_productivity'] >= 15:
                issues.append(f"reduce volatility from {stats['cv_productivity']:.1f}% to <15%")
            if stats['avg_productivity'] <= 0.70:
                issues.append(f"improve productivity from {stats['avg_productivity']:.0%} to 70%+")
            if inflation_frequency >= 0.3:
                issues.append(f"reduce inflation frequency from {inflation_frequency:.0%} to <30%")
            report += f"Not ready for EBP until: {', '.join(issues)}.\n"

        report += f"""
---

## Performance Metrics

### Overall Statistics

| Metric | Value | Industry Benchmark |
|--------|-------|-------------------|
| Average Productivity | {stats['avg_productivity']:.1%} | 75-85% |
| Average Predictability | {stats['avg_predictability']:.1%} | 70-80% |
| Coefficient of Variation | {stats['cv_productivity']:.1f}% | <15% |
| Productivity Range | {stats['min_productivity']:.1%} - {stats['max_productivity']:.1%} | - |
| Predictability Range | {stats['min_predictability']:.1%} - {stats['max_predictability']:.1%} | - |

### Delivery Performance

| Metric | Value |
|--------|-------|
| Average Committed SP | {stats['avg_committed']:.1f} |
| Average Delivered SP | {stats['avg_delivered']:.1f} |
| Average Gap | {stats['avg_committed'] - stats['avg_delivered']:.1f} SP |
| Total Inflation | {stats['total_inflation']:.0f} SP |
| Sprints with Inflation | {stats['inflation_count']}/{stats['total_sprints']} ({inflation_frequency:.0%}) |
"""

        if stats['transition_sprint']:
            report += f"""
### Model Transition Analysis

**Transition Point:** {stats['transition_sprint']} ({stats['old_velocity']:.1f} SP → {stats['new_velocity']:.1f} SP)

| Metric | Old Model | New Model | Change |
|--------|-----------|-----------|--------|
| Avg Productivity | {stats['old_model_productivity']:.1%} | {stats['new_model_productivity']:.1%} | {(stats['new_model_productivity'] - stats['old_model_productivity']):.1%} |
| Avg Predictability | {stats['old_model_predictability']:.1%} | {stats['new_model_predictability']:.1%} | {(stats['new_model_predictability'] - stats['old_model_predictability']):.1%} |
| Sprint Count | {len(stats['old_model'])} | {len(stats['new_model'])} | - |
"""

        report += """
---

## Key Observations

### Productivity Analysis
"""

        if stats['avg_productivity'] > 0.85:
            report += f"- **High Capability:** {stats['avg_productivity']:.1%} productivity exceeds industry benchmarks\n"
        elif stats['avg_productivity'] < 0.60:
            report += f"- **Below Benchmark:** {stats['avg_productivity']:.1%} productivity suggests systemic constraints or blockers\n"
        else:
            report += f"- **Moderate Performance:** {stats['avg_productivity']:.1%} productivity within acceptable range\n"

        if stats['cv_productivity'] > 30:
            report += f"- **High Volatility:** {stats['cv_productivity']:.1f}% CV indicates severe instability in delivery patterns\n"
        elif stats['cv_productivity'] > 15:
            report += f"- **Moderate Volatility:** {stats['cv_productivity']:.1f}% CV suggests need for process stabilization\n"
        else:
            report += f"- **Stable Performance:** {stats['cv_productivity']:.1f}% CV indicates predictable delivery rhythm\n"

        report += "\n### Predictability Analysis\n"

        if stats['avg_predictability'] > 0.85:
            report += f"- **Strong Commitment Discipline:** {stats['avg_predictability']:.1%} predictability shows team hits commitments consistently\n"
        elif stats['avg_predictability'] < 0.60:
            report += f"- **Commitment Issues:** {stats['avg_predictability']:.1%} predictability suggests over-commitment or estimation problems\n"
        else:
            report += f"- **Moderate Predictability:** {stats['avg_predictability']:.1%} predictability indicates room for improvement\n"

        report += "\n### Inflation Pattern\n"

        if inflation_frequency > 0.7:
            report += f"- **Systematic Inflation Issue:** {inflation_frequency:.0%} of sprints require corrections, indicating weak Definition of Ready\n"
        elif inflation_frequency > 0.3:
            report += f"- **Frequent Adjustments:** {inflation_frequency:.0%} of sprints need inflation corrections\n"
        elif stats['total_inflation'] != 0:
            report += f"- **Occasional Corrections:** {inflation_frequency:.0%} of sprints have inflation adjustments\n"
        else:
            report += "- **Clean Estimation:** No inflation corrections needed\n"

        # Add sprint notes if available
        notes_list = []
        for idx, row in df.iterrows():
            if pd.notna(row['Notes']) and row['Notes'].strip():
                notes_list.append(f"- **{row['Sprint']}:** {row['Notes']}")

        if notes_list:
            report += "\n### Sprint Notes\n\n"
            report += "\n".join(notes_list[:10])  # Limit to first 10 notes
            if len(notes_list) > 10:
                report += f"\n- *...and {len(notes_list) - 10} more sprint notes*\n"

        report += f"""

---

## Visual Analysis Dashboard

![{self.team_name} Performance Dashboard]({team_name_clean}_Performance_Dashboard.png)

**Dashboard Insights:**
- **Top Left:** Productivity trend shows {'stable progression' if stats['cv_productivity'] < 15 else 'high volatility'} over sprint range
- **Top Right:** Predictability evolution indicates {'consistent delivery' if stats['avg_predictability'] > 0.75 else 'variable commitment accuracy'}
- **Middle Left:** Commitment vs delivery gap averages {stats['avg_committed'] - stats['avg_delivered']:.1f} SP per sprint
- **Bottom Left:** Inflation corrections total {stats['total_inflation']:.0f} SP across {stats['inflation_count']} sprints
- **Bottom Center:** Scatter plot reveals {'clustered performance pattern' if stats['cv_productivity'] < 20 else 'dispersed performance pattern'}
- **Bottom Right:** Moving averages {'converge toward stable baseline' if stats['cv_productivity'] < 20 else 'show continued volatility'}

---

## Coaching Recommendations

### Priority Interventions
"""

        # Generate recommendations based on data
        recommendations = []

        if stats['cv_productivity'] > 20:
            recommendations.append({
                'title': 'Volatility Reduction Workshop',
                'priority': 1,
                'description': f"Address {stats['cv_productivity']:.1f}% coefficient of variation through root cause analysis"
            })

        if inflation_frequency > 0.5:
            recommendations.append({
                'title': 'Definition of Ready Enhancement',
                'priority': 1,
                'description': f"Fix systematic inflation pattern affecting {inflation_frequency:.0%} of sprints"
            })

        if stats['avg_productivity'] < 0.65:
            recommendations.append({
                'title': 'Productivity Blockers Analysis',
                'priority': 1,
                'description': f"Identify constraints limiting productivity to {stats['avg_productivity']:.1%}"
            })

        if stats['transition_sprint'] and len(stats['new_model']) < 5:
            recommendations.append({
                'title': 'New Model Baseline Discovery',
                'priority': 2,
                'description': f"Run learning sprints to establish stable baseline under {stats['new_velocity']:.1f} SP model"
            })

        if stats['avg_predictability'] < 0.70:
            recommendations.append({
                'title': 'Estimation Calibration Workshop',
                'priority': 2,
                'description': f"Improve commitment accuracy from {stats['avg_predictability']:.1%} to 75%+"
            })

        # Add capacity planning if there are notes about holidays/capacity
        capacity_notes = [note for note in notes_list if any(word in note.lower() for word in ['holiday', 'fte', 'capacity', 'absence'])]
        if capacity_notes:
            recommendations.append({
                'title': 'Capacity-Adjusted Planning Protocol',
                'priority': 2,
                'description': "Implement systematic capacity adjustment for holidays and team changes"
            })

        # Sort by priority and add to report
        recommendations.sort(key=lambda x: x['priority'])

        for i, rec in enumerate(recommendations[:6], 1):
            report += f"\n#### {i}. {rec['title']}\n"
            report += f"**Purpose:** {rec['description']}\n\n"
            report += "**Method:**\n"
            report += "- Facilitate team workshop to identify root causes\n"
            report += "- Co-create targeted experiments with measurable outcomes\n"
            report += "- Track improvements over next 3-6 sprints\n\n"
            report += "**Success Indicator:** Measurable improvement in target metric within 2-3 sprints\n"

        report += """
---

## Bottom Line for Coaching

**What the Team Has:**
"""

        strengths = []
        if stats['avg_productivity'] > 0.75:
            strengths.append(f"Strong productivity capability ({stats['avg_productivity']:.1%})")
        if stats['avg_predictability'] > 0.75:
            strengths.append(f"Reliable commitment discipline ({stats['avg_predictability']:.1%})")
        if stats['cv_productivity'] < 20:
            strengths.append(f"Relatively stable delivery rhythm ({stats['cv_productivity']:.1f}% CV)")
        if not strengths:
            strengths.append("Willingness to improve and track metrics")

        for strength in strengths[:3]:
            report += f"- {strength}\n"

        report += "\n**What the Team Needs:**\n"

        needs = []
        if stats['cv_productivity'] > 15:
            needs.append(f"Volatility reduction from {stats['cv_productivity']:.1f}% to <15% CV")
        if stats['avg_productivity'] < 0.70:
            needs.append(f"Productivity improvement from {stats['avg_productivity']:.0%} to 70%+")
        if inflation_frequency > 0.3:
            needs.append(f"Inflation frequency reduction from {inflation_frequency:.0%} to <30%")
        if not needs:
            needs.append("Continued focus on maintaining stable performance")

        for need in needs[:3]:
            report += f"- {need}\n"

        report += f"""

**Coaching Stance:**
Focus on {'celebrating strengths while addressing specific process gaps' if strengths else 'systematic improvement in core delivery practices'}. The path forward involves {'stabilizing the new model baseline and reducing volatility' if stats['transition_sprint'] else 'targeted interventions to improve consistency and predictability'}.

---

**Prepared by:** Enterprise Transformation Coaching AI
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        # Save report
        output_file = f'{team_name_clean}_Performance_Analysis.md'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"Analysis report saved: {output_file}")
        print(f"Report word count: {len(report.split())}")

        return output_file


def main():
    """Main execution function"""
    if len(sys.argv) < 2:
        print("Usage: python generate_team_analysis.py <csv_file_path>")
        print("\nExample:")
        print("  python generate_team_analysis.py MyTeamProductivity20251108.csv")
        sys.exit(1)

    csv_file = sys.argv[1]

    if not os.path.exists(csv_file):
        print(f"Error: File '{csv_file}' not found")
        sys.exit(1)

    print(f"\n{'='*60}")
    print("TEAM PERFORMANCE ANALYSIS GENERATOR")
    print(f"{'='*60}\n")

    try:
        # Create analyzer instance
        analyzer = TeamPerformanceAnalyzer(csv_file)

        # Read and clean data
        analyzer.read_and_clean_data()

        # Calculate statistics
        analyzer.calculate_statistics()

        # Generate dashboard
        dashboard_file = analyzer.generate_dashboard()

        # Generate markdown report
        report_file = analyzer.generate_markdown_report()

        print(f"\n{'='*60}")
        print("ANALYSIS COMPLETE")
        print(f"{'='*60}")
        print(f"\nGenerated files:")
        print(f"  1. Dashboard: {dashboard_file}")
        print(f"  2. Report:    {report_file}")
        print(f"\nTeam: {analyzer.team_name}")
        print(f"Sprints analyzed: {analyzer.stats['total_sprints']}")
        print(f"Average productivity: {analyzer.stats['avg_productivity']:.1%}")
        print(f"Coefficient of variation: {analyzer.stats['cv_productivity']:.1f}%")

    except Exception as e:
        print(f"\nError during analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
