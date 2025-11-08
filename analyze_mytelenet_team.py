#!/usr/bin/env python3
"""
Team Performance Analysis for MyTelenet-app Team
Generates dashboard and coaching report following the Team_Performance_Analysis_Prompt specifications
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# Read and clean data
print("Reading CSV data...")
df = pd.read_csv('MyTelenetAppTeamProductivity20251108.csv', encoding='utf-8-sig')

# Clean the data - replace "/" and "#VALUE!" with NaN
print("Cleaning data...")
df = df.replace('/', np.nan)
df = df.replace('#VALUE!', np.nan)

# Convert numeric columns
numeric_cols = ['Target Velocity', 'Committed SP', 'Delivered SP', 'Inflation correction',
                'Normalized Target Velocity', 'Normalized Planned SP', 'Normalized Delivered SP',
                'Normalized Inflation SP']

for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

# Convert percentage columns (remove % sign and convert)
def clean_percentage(val):
    if pd.isna(val):
        return np.nan
    if isinstance(val, str):
        return float(val.strip('%')) / 100 if '%' in val else float(val)
    return val

df['Productivity_num'] = df['Productivity'].apply(clean_percentage)
df['Predictability_num'] = df['Predictability'].apply(clean_percentage)

# Filter to rows with actual data
df_clean = df[df['Productivity_num'].notna()].copy()

print(f"Total sprints: {len(df)}")
print(f"Sprints with data: {len(df_clean)}")

# Calculate statistics
avg_productivity = df_clean['Productivity_num'].mean()
avg_predictability = df_clean['Predictability_num'].mean()
std_productivity = df_clean['Productivity_num'].std()
cv_productivity = (std_productivity / avg_productivity) * 100

# Phase analysis - model transition at S25.19 (120 SP -> 158 SP)
old_model = df_clean[df_clean['Target Velocity'] == 120]
new_model = df_clean[df_clean['Target Velocity'] == 158]

print(f"\nOverall Statistics:")
print(f"Average Productivity: {avg_productivity:.1%}")
print(f"Average Predictability: {avg_predictability:.1%}")
print(f"Coefficient of Variation: {cv_productivity:.1f}%")

print(f"\nOld Model (120 SP): {len(old_model)} sprints")
if len(old_model) > 0:
    print(f"  Avg Productivity: {old_model['Productivity_num'].mean():.1%}")
    print(f"  Avg Predictability: {old_model['Predictability_num'].mean():.1%}")

print(f"\nNew Model (158 SP): {len(new_model)} sprints")
if len(new_model) > 0:
    print(f"  Avg Productivity: {new_model['Productivity_num'].mean():.1%}")
    print(f"  Avg Predictability: {new_model['Predictability_num'].mean():.1%}")

# Inflation analysis
total_inflation = df_clean['Inflation correction'].sum()
inflation_count = len(df_clean[df_clean['Inflation correction'] != 0])
print(f"\nInflation: {total_inflation:.0f} SP across {inflation_count} sprints")

# Create comprehensive dashboard
print("\nGenerating performance dashboard...")

fig = plt.figure(figsize=(20, 12))
gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.3)

# Define colors
color_primary = '#1f77b4'
color_secondary = '#ff7f0e'
color_success = '#2ca02c'
color_danger = '#d62728'
color_old = '#ff6b6b'
color_new = '#51cf66'

# Identify transition point
transition_idx = df_clean[df_clean['Sprint'] == 'S25.19'].index[0] if 'S25.19' in df_clean['Sprint'].values else None

# Chart 1: Productivity Trend Line (Top Left, spans 2 columns)
ax1 = fig.add_subplot(gs[0, :2])
ax1.plot(df_clean['Sprint'], df_clean['Productivity_num'] * 100,
         marker='o', linewidth=2.5, markersize=8, color=color_primary, label='Productivity')
ax1.fill_between(range(len(df_clean)), df_clean['Productivity_num'] * 100, alpha=0.3, color=color_primary)
ax1.axhline(y=avg_productivity * 100, color=color_success, linestyle='--', linewidth=2,
            label=f'Average ({avg_productivity:.0%})', alpha=0.7)

# Mark transition
if transition_idx is not None:
    transition_pos = df_clean.index.get_loc(transition_idx)
    ax1.axvline(x=transition_pos, color=color_danger, linestyle='--', linewidth=2.5,
                label='Model Transition (120→158 SP)', alpha=0.8)

ax1.set_title('Productivity Trend Over Sprints', fontsize=16, fontweight='bold', pad=15)
ax1.set_xlabel('Sprint', fontsize=12, fontweight='bold')
ax1.set_ylabel('Productivity (%)', fontsize=12, fontweight='bold')
ax1.legend(fontsize=10, loc='best')
ax1.grid(True, alpha=0.3)
ax1.set_ylim([0, max(df_clean['Productivity_num'] * 100) * 1.2])
ax1.tick_params(axis='both', labelsize=8, width=1.5)
plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right', fontweight='bold')
plt.setp(ax1.yaxis.get_majorticklabels(), fontweight='bold')

# Chart 2: Predictability Trend Line (Top Right)
ax2 = fig.add_subplot(gs[0, 2])
ax2.plot(df_clean['Sprint'], df_clean['Predictability_num'] * 100,
         marker='s', linewidth=2.5, markersize=7, color=color_secondary, label='Predictability')
ax2.axhline(y=avg_predictability * 100, color=color_success, linestyle='--', linewidth=2,
            label=f'Average ({avg_predictability:.0%})', alpha=0.7)

if transition_idx is not None:
    ax2.axvline(x=transition_pos, color=color_danger, linestyle='--', linewidth=2, alpha=0.8)

ax2.set_title('Predictability Evolution', fontsize=14, fontweight='bold', pad=15)
ax2.set_xlabel('Sprint', fontsize=11, fontweight='bold')
ax2.set_ylabel('Predictability (%)', fontsize=11, fontweight='bold')
ax2.legend(fontsize=9, loc='best')
ax2.grid(True, alpha=0.3)
ax2.set_ylim([0, 105])
ax2.tick_params(axis='both', labelsize=8, width=1.5)
plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right', fontweight='bold')
plt.setp(ax2.yaxis.get_majorticklabels(), fontweight='bold')

# Chart 3: Commitment vs Delivery Bar Chart (Middle Left, spans 2 columns)
ax3 = fig.add_subplot(gs[1, :2])
x_pos = np.arange(len(df_clean))
width = 0.35

bars1 = ax3.bar(x_pos - width/2, df_clean['Committed SP'], width,
                label='Committed SP', color=color_secondary, alpha=0.8)
bars2 = ax3.bar(x_pos + width/2, df_clean['Delivered SP'], width,
                label='Delivered SP', color=color_primary, alpha=0.8)

if transition_idx is not None:
    ax3.axvline(x=transition_pos, color=color_danger, linestyle='--', linewidth=2.5,
                label='Model Transition', alpha=0.8)

ax3.set_title('Commitment vs Delivery Comparison', fontsize=16, fontweight='bold', pad=15)
ax3.set_xlabel('Sprint', fontsize=12, fontweight='bold')
ax3.set_ylabel('Story Points', fontsize=12, fontweight='bold')
ax3.set_xticks(x_pos)
ax3.set_xticklabels(df_clean['Sprint'], rotation=45, ha='right')
ax3.legend(fontsize=10, loc='best')
ax3.grid(True, alpha=0.3, axis='y')
ax3.tick_params(axis='both', labelsize=8, width=1.5)
plt.setp(ax3.xaxis.get_majorticklabels(), fontweight='bold')
plt.setp(ax3.yaxis.get_majorticklabels(), fontweight='bold')

# Chart 4: Model Comparison Box Plot (Middle Right)
ax4 = fig.add_subplot(gs[1, 2])
if len(old_model) > 0 and len(new_model) > 0:
    box_data = [old_model['Productivity_num'] * 100, new_model['Productivity_num'] * 100]
    bp = ax4.boxplot(box_data, labels=['Old Model\n(120 SP)', 'New Model\n(158 SP)'],
                     patch_artist=True, widths=0.6)
    bp['boxes'][0].set_facecolor(color_old)
    bp['boxes'][1].set_facecolor(color_new)
    for box in bp['boxes']:
        box.set_alpha(0.7)
else:
    ax4.text(0.5, 0.5, 'Insufficient data\nfor comparison',
             ha='center', va='center', fontsize=12, transform=ax4.transAxes)

ax4.set_title('Productivity by Model', fontsize=14, fontweight='bold', pad=15)
ax4.set_ylabel('Productivity (%)', fontsize=11, fontweight='bold')
ax4.grid(True, alpha=0.3, axis='y')
ax4.tick_params(axis='both', labelsize=8, width=1.5)
plt.setp(ax4.xaxis.get_majorticklabels(), fontweight='bold')
plt.setp(ax4.yaxis.get_majorticklabels(), fontweight='bold')

# Chart 5: Inflation Corrections Horizontal Bar (Bottom Left)
ax5 = fig.add_subplot(gs[2, 0])
colors_inflation = [color_danger if x < 0 else color_success for x in df_clean['Inflation correction']]
ax5.barh(df_clean['Sprint'], df_clean['Inflation correction'], color=colors_inflation, alpha=0.7)
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

# Add quadrant lines
ax6.axhline(y=avg_predictability * 100, color='gray', linestyle='--', linewidth=1, alpha=0.5)
ax6.axvline(x=avg_productivity * 100, color='gray', linestyle='--', linewidth=1, alpha=0.5)

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
ax7.plot(df_clean['Sprint'], df_clean['Productivity_num'] * 100,
         marker='o', linewidth=2, markersize=6, alpha=0.5, label='Actual', color=color_primary)

# Calculate moving averages
ma2 = df_clean['Productivity_num'].rolling(window=2).mean() * 100
ma3 = df_clean['Productivity_num'].rolling(window=3).mean() * 100

ax7.plot(df_clean['Sprint'], ma2, linewidth=2.5, label='MA(2)', color=color_secondary)
ax7.plot(df_clean['Sprint'], ma3, linewidth=2.5, label='MA(3)', color=color_success, linestyle='--')

ax7.set_title('Moving Averages', fontsize=14, fontweight='bold', pad=15)
ax7.set_xlabel('Sprint', fontsize=11, fontweight='bold')
ax7.set_ylabel('Productivity (%)', fontsize=11, fontweight='bold')
ax7.legend(fontsize=9, loc='best')
ax7.grid(True, alpha=0.3)
ax7.tick_params(axis='both', labelsize=8, width=1.5)
plt.setp(ax7.xaxis.get_majorticklabels(), rotation=45, ha='right', fontweight='bold')
plt.setp(ax7.yaxis.get_majorticklabels(), fontweight='bold')

# Add main title
fig.suptitle('MyTelenet-app Team Performance Dashboard',
             fontsize=20, fontweight='bold', y=0.98)

# Save dashboard
output_file = 'MyTelenet_Performance_Dashboard.png'
plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
print(f"Dashboard saved: {output_file}")
plt.close()

# Generate detailed statistics for report
print("\n" + "="*60)
print("DETAILED STATISTICS FOR REPORT")
print("="*60)

print(f"\nProductivity Statistics:")
print(f"  Mean: {avg_productivity:.1%}")
print(f"  Std Dev: {std_productivity:.1%}")
print(f"  CV: {cv_productivity:.1f}%")
print(f"  Min: {df_clean['Productivity_num'].min():.1%}")
print(f"  Max: {df_clean['Productivity_num'].max():.1%}")

print(f"\nPredictability Statistics:")
print(f"  Mean: {avg_predictability:.1%}")
print(f"  Std Dev: {df_clean['Predictability_num'].std():.1%}")
print(f"  Min: {df_clean['Predictability_num'].min():.1%}")
print(f"  Max: {df_clean['Predictability_num'].max():.1%}")

print(f"\nDelivery Statistics:")
print(f"  Average Committed: {df_clean['Committed SP'].mean():.1f} SP")
print(f"  Average Delivered: {df_clean['Delivered SP'].mean():.1f} SP")
print(f"  Gap: {df_clean['Committed SP'].mean() - df_clean['Delivered SP'].mean():.1f} SP")

print(f"\nInflation Analysis:")
print(f"  Total Inflation: {total_inflation:.0f} SP")
print(f"  Sprints with Inflation: {inflation_count}/{len(df_clean)} ({inflation_count/len(df_clean):.0%})")
print(f"  Average per Sprint: {total_inflation/len(df_clean):.1f} SP")

# Sprint-by-sprint notes analysis
print("\nKey Sprint Notes:")
for idx, row in df_clean.iterrows():
    if pd.notna(row['Notes']) and row['Notes'].strip():
        print(f"  {row['Sprint']}: {row['Notes']}")

print("\nAnalysis complete!")
