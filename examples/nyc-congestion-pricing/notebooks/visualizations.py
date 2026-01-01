"""
NYC Taxi Data Visualizations
Creates interactive and static visualizations from the analysis results.
"""

import polars as pl
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Set style for matplotlib
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# Create outputs directory
output_dir = Path("../outputs")
output_dir.mkdir(exist_ok=True)

# Load the data
print("Loading data from ../outputs/result.parquet...")
df = pl.read_parquet("../outputs/result.parquet")
print(f"Loaded {len(df)} months of data")
print("\nDataset columns:", df.columns)
print("\nData shape:", df.shape)
print("Sample data loaded successfully!")

# Convert to pandas for easier plotting (some libraries prefer pandas)
df_pd = df.to_pandas()

# Ensure year_month is treated as datetime for better plotting
df_pd['date'] = df['year_month'].str.to_date(format='%Y-%m').to_pandas()

print("\n" + "="*60)
print("Creating Visualizations")
print("="*60)

# 1. Time Series: Trip Count Over Time
print("\n1. Creating trip count time series...")
fig1 = px.line(
    df_pd,
    x='date',
    y='trip_count',
    title='NYC Yellow Taxi Trips Over Time (2020-2025)',
    labels={'date': 'Date', 'trip_count': 'Number of Trips'},
    template='plotly_white'
)
fig1.update_traces(line_color='#FFD700', line_width=2)
fig1.update_layout(
    hovermode='x unified',
    font=dict(size=12),
    height=500
)
fig1.write_html(output_dir / "trips_over_time.html")
fig1.write_image(output_dir / "trips_over_time.png", width=1200, height=600)
print("   [OK] Saved: trips_over_time.html and .png")

# 2. Revenue Time Series
print("\n2. Creating revenue time series...")
fig2 = go.Figure()
fig2.add_trace(go.Scatter(
    x=df_pd['date'],
    y=df_pd['total_revenue'] / 1_000_000,  # Convert to millions
    mode='lines',
    name='Total Revenue',
    line=dict(color='#2ECC71', width=2),
    fill='tozeroy',
    fillcolor='rgba(46, 204, 113, 0.2)'
))
fig2.update_layout(
    title='NYC Yellow Taxi Revenue Over Time',
    xaxis_title='Date',
    yaxis_title='Revenue (Million $)',
    template='plotly_white',
    hovermode='x unified',
    height=500
)
fig2.write_html(output_dir / "revenue_over_time.html")
fig2.write_image(output_dir / "revenue_over_time.png", width=1200, height=600)
print("   [OK]Saved: revenue_over_time.html and .png")

# 3. Average Fare and Distance - Dual Axis
print("\n3. Creating average fare and distance chart...")
fig3 = make_subplots(specs=[[{"secondary_y": True}]])

fig3.add_trace(
    go.Scatter(
        x=df_pd['date'],
        y=df_pd['avg_fare'],
        name="Avg Fare ($)",
        line=dict(color='#3498DB', width=2)
    ),
    secondary_y=False
)

fig3.add_trace(
    go.Scatter(
        x=df_pd['date'],
        y=df_pd['avg_distance'],
        name="Avg Distance (mi)",
        line=dict(color='#E74C3C', width=2)
    ),
    secondary_y=True
)

fig3.update_layout(
    title='Average Fare and Trip Distance Over Time',
    template='plotly_white',
    hovermode='x unified',
    height=500
)
fig3.update_xaxes(title_text="Date")
fig3.update_yaxes(title_text="Average Fare ($)", secondary_y=False)
fig3.update_yaxes(title_text="Average Distance (miles)", secondary_y=True)

fig3.write_html(output_dir / "avg_fare_distance.html")
fig3.write_image(output_dir / "avg_fare_distance.png", width=1200, height=600)
print("   [OK]Saved: avg_fare_distance.html and .png")

# 4. Monthly Comparison - Heatmap
print("\n4. Creating monthly heatmap...")
# Pivot data for heatmap
heatmap_data = df_pd.pivot_table(
    values='trip_count',
    index='month',
    columns='year',
    aggfunc='mean'
)

fig4, ax = plt.subplots(figsize=(12, 6))
sns.heatmap(
    heatmap_data,
    annot=True,
    fmt='.0f',
    cmap='YlOrRd',
    cbar_kws={'label': 'Trip Count'},
    ax=ax
)
ax.set_title('Monthly Trip Count Heatmap by Year', fontsize=16, pad=20)
ax.set_xlabel('Year', fontsize=12)
ax.set_ylabel('Month', fontsize=12)
plt.tight_layout()
plt.savefig(output_dir / "monthly_heatmap.png", dpi=300, bbox_inches='tight')
plt.close()
print("   [OK]Saved: monthly_heatmap.png")

# 5. Year-over-Year Growth
print("\n5. Creating year-over-year comparison...")
yearly_totals = df_pd.groupby('year').agg({
    'trip_count': 'sum',
    'total_revenue': 'sum'
}).reset_index()

fig5 = go.Figure()
fig5.add_trace(go.Bar(
    x=yearly_totals['year'],
    y=yearly_totals['trip_count'] / 1_000_000,
    name='Total Trips (Millions)',
    marker_color='#9B59B6',
    text=yearly_totals['trip_count'] / 1_000_000,
    texttemplate='%{text:.1f}M',
    textposition='outside'
))

fig5.update_layout(
    title='Annual Trip Count Comparison',
    xaxis_title='Year',
    yaxis_title='Total Trips (Millions)',
    template='plotly_white',
    height=500,
    showlegend=False
)
fig5.write_html(output_dir / "yearly_comparison.html")
fig5.write_image(output_dir / "yearly_comparison.png", width=1200, height=600)
print("   [OK]Saved: yearly_comparison.html and .png")

# 6. Statistical Distribution - Box Plot
print("\n6. Creating statistical distribution plots...")
fig6 = go.Figure()

for year in sorted(df_pd['year'].unique()):
    year_data = df_pd[df_pd['year'] == year]
    fig6.add_trace(go.Box(
        y=year_data['trip_count'] / 1000,
        name=str(year),
        boxmean='sd'
    ))

fig6.update_layout(
    title='Monthly Trip Count Distribution by Year',
    yaxis_title='Trips (Thousands)',
    xaxis_title='Year',
    template='plotly_white',
    height=500
)
fig6.write_html(output_dir / "trip_distribution.html")
fig6.write_image(output_dir / "trip_distribution.png", width=1200, height=600)
print("   [OK]Saved: trip_distribution.html and .png")

# 7. Dashboard-style Summary
print("\n7. Creating dashboard summary...")
fig7 = make_subplots(
    rows=2, cols=2,
    subplot_titles=(
        'Monthly Trips',
        'Monthly Revenue (Million $)',
        'Average Fare ($)',
        'Average Distance (mi)'
    ),
    vertical_spacing=0.12,
    horizontal_spacing=0.1
)

# Trips
fig7.add_trace(
    go.Scatter(x=df_pd['date'], y=df_pd['trip_count']/1000,
               mode='lines', line=dict(color='#3498DB', width=2),
               name='Trips (K)'),
    row=1, col=1
)

# Revenue
fig7.add_trace(
    go.Scatter(x=df_pd['date'], y=df_pd['total_revenue']/1_000_000,
               mode='lines', line=dict(color='#2ECC71', width=2),
               name='Revenue (M)'),
    row=1, col=2
)

# Avg Fare
fig7.add_trace(
    go.Scatter(x=df_pd['date'], y=df_pd['avg_fare'],
               mode='lines', line=dict(color='#E67E22', width=2),
               name='Avg Fare'),
    row=2, col=1
)

# Avg Distance
fig7.add_trace(
    go.Scatter(x=df_pd['date'], y=df_pd['avg_distance'],
               mode='lines', line=dict(color='#E74C3C', width=2),
               name='Avg Dist'),
    row=2, col=2
)

fig7.update_layout(
    title_text='NYC Yellow Taxi Dashboard (2020-2025)',
    showlegend=False,
    template='plotly_white',
    height=800
)

fig7.update_yaxes(title_text="Trips (Thousands)", row=1, col=1)
fig7.update_yaxes(title_text="Revenue (Million $)", row=1, col=2)
fig7.update_yaxes(title_text="Fare ($)", row=2, col=1)
fig7.update_yaxes(title_text="Distance (mi)", row=2, col=2)

fig7.write_html(output_dir / "dashboard.html")
fig7.write_image(output_dir / "dashboard.png", width=1400, height=900)
print("   [OK]Saved: dashboard.html and .png")

# Generate summary statistics
print("\n" + "="*60)
print("Summary Statistics")
print("="*60)
print(f"\nTotal months analyzed: {len(df)}")
print(f"Date range: {df_pd['year_month'].min()} to {df_pd['year_month'].max()}")
print(f"\nTotal trips: {df_pd['trip_count'].sum():,.0f}")
print(f"Total revenue: ${df_pd['total_revenue'].sum():,.2f}")
print(f"Average monthly trips: {df_pd['trip_count'].mean():,.0f}")
print(f"Average monthly revenue: ${df_pd['total_revenue'].mean():,.2f}")
print(f"\nAverage fare: ${df_pd['avg_fare'].mean():.2f}")
print(f"Average distance: {df_pd['avg_distance'].mean():.2f} miles")

print("\n" + "="*60)
print("All visualizations saved to outputs/ directory!")
print("="*60)
print("\nGenerated files:")
print("  Interactive HTML:")
print("    - trips_over_time.html")
print("    - revenue_over_time.html")
print("    - avg_fare_distance.html")
print("    - yearly_comparison.html")
print("    - trip_distribution.html")
print("    - dashboard.html")
print("\n  Static PNG:")
print("    - trips_over_time.png")
print("    - revenue_over_time.png")
print("    - avg_fare_distance.png")
print("    - monthly_heatmap.png")
print("    - yearly_comparison.png")
print("    - trip_distribution.png")
print("    - dashboard.png")
