#!/usr/bin/env python3
"""
Plot GY-91 sensor data from CSV file.
Creates visualizations of accelerometer, gyroscope, pressure, and altitude data.

pip install pandas matplotlib
"""

import pandas as pd
import matplotlib.pyplot as plt
import sys
import os
from datetime import datetime


def plot_gy91_data(csv_file):
    """
    Create beautiful plots of GY-91 sensor data.
    
    Args:
        csv_file: Path to the CSV file containing sensor data
    """
    # Check if file exists
    if not os.path.exists(csv_file):
        print(f"Error: File '{csv_file}' not found!")
        sys.exit(1)
    
    # Read CSV data
    print(f"Reading data from {csv_file}...")
    df = pd.read_csv(csv_file)
    
    print(f"Loaded {len(df)} samples")
    
    # Create time axis (sample number or elapsed time)
    time_axis = range(len(df))
    sample_rate = 25  # Hz
    time_seconds = [t / sample_rate for t in time_axis]
    
    # Set up the plot style
    plt.style.use('seaborn-v0_8-darkgrid')
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    
    # Create figure with subplots
    fig = plt.figure(figsize=(16, 10))
    fig.suptitle('GY-91 Sensor Data Visualization', fontsize=16, fontweight='bold')
    
    # Plot 1: Accelerometer data
    ax1 = plt.subplot(2, 2, 1)
    ax1.plot(time_seconds, df['accel_x'], label='X', color=colors[0], linewidth=1.0, alpha=0.8)
    ax1.plot(time_seconds, df['accel_y'], label='Y', color=colors[1], linewidth=1.0, alpha=0.8)
    ax1.plot(time_seconds, df['accel_z'], label='Z', color=colors[2], linewidth=1.0, alpha=0.8)
    ax1.set_xlabel('Time (seconds)', fontsize=11)
    ax1.set_ylabel('Acceleration (g)', fontsize=11)
    ax1.set_title('Accelerometer Data', fontsize=13, fontweight='bold')
    ax1.legend(loc='upper right', framealpha=0.9)
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Gyroscope data
    ax2 = plt.subplot(2, 2, 2)
    ax2.plot(time_seconds, df['gyro_x'], label='X', color=colors[0], linewidth=1.0, alpha=0.8)
    ax2.plot(time_seconds, df['gyro_y'], label='Y', color=colors[1], linewidth=1.0, alpha=0.8)
    ax2.plot(time_seconds, df['gyro_z'], label='Z', color=colors[2], linewidth=1.0, alpha=0.8)
    ax2.set_xlabel('Time (seconds)', fontsize=11)
    ax2.set_ylabel('Angular Velocity (°/s)', fontsize=11)
    ax2.set_title('Gyroscope Data', fontsize=13, fontweight='bold')
    ax2.legend(loc='upper right', framealpha=0.9)
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Pressure
    ax3 = plt.subplot(2, 2, 3)
    ax3.plot(time_seconds, df['pressure'], color=colors[3], linewidth=1, alpha=0.8)
    ax3.set_xlabel('Time (seconds)', fontsize=11)
    ax3.set_ylabel('Pressure (hPa)', fontsize=11)
    ax3.set_title('Barometric Pressure', fontsize=13, fontweight='bold')
    ax3.set_ylim(df['pressure'].min() * 0.999, df['pressure'].max() * 1.001)
    ax3.grid(True, alpha=0.3)
    ax3.fill_between(time_seconds, df['pressure'], alpha=0.2, color=colors[3])
    
    # Plot 4: Altitude
    ax4 = plt.subplot(2, 2, 4)
    ax4.plot(time_seconds, df['altitude'], color=colors[4], linewidth=1, alpha=0.8)
    ax4.set_xlabel('Time (seconds)', fontsize=11)
    ax4.set_ylabel('Altitude (m)', fontsize=11)
    ax4.set_title('Estimated Altitude', fontsize=13, fontweight='bold')
    ax4.grid(True, alpha=0.3)
    ax4.set_ylim(df['altitude'].min() * 0.99, df['altitude'].max() * 1.01)
    ax4.fill_between(time_seconds, df['altitude'], alpha=0.2, color=colors[4])
    
    # Add statistics text
    stats_text = f"Statistics:\n"
    stats_text += f"Duration: {time_seconds[-1]:.1f}s\n"
    stats_text += f"Samples: {len(df)}\n"
    stats_text += f"Sample Rate: ~{sample_rate} Hz"
    
    fig.text(0.99, 0.01, stats_text, ha='right', va='bottom', 
             fontsize=9, family='monospace',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    # Adjust layout
    plt.tight_layout(rect=[0, 0.03, 1, 0.96])
    
    # Save figure
    output_file = csv_file.replace('.csv', '_plot.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\nPlot saved to: {output_file}")
    
    # Show plot
    plt.show()
    
    # Print summary statistics
    print("\n=== Summary Statistics ===")
    print(f"\nAccelerometer (g):")
    print(f"  X: mean={df['accel_x'].mean():.4f}, std={df['accel_x'].std():.4f}")
    print(f"  Y: mean={df['accel_y'].mean():.4f}, std={df['accel_y'].std():.4f}")
    print(f"  Z: mean={df['accel_z'].mean():.4f}, std={df['accel_z'].std():.4f}")
    
    print(f"\nGyroscope (°/s):")
    print(f"  X: mean={df['gyro_x'].mean():.4f}, std={df['gyro_x'].std():.4f}")
    print(f"  Y: mean={df['gyro_y'].mean():.4f}, std={df['gyro_y'].std():.4f}")
    print(f"  Z: mean={df['gyro_z'].mean():.4f}, std={df['gyro_z'].std():.4f}")
    
    print(f"\nPressure (hPa):")
    print(f"  mean={df['pressure'].mean():.2f}, min={df['pressure'].min():.2f}, max={df['pressure'].max():.2f}")
    
    print(f"\nAltitude (m):")
    print(f"  mean={df['altitude'].mean():.2f}, min={df['altitude'].min():.2f}, max={df['altitude'].max():.2f}")


def main():
    if len(sys.argv) < 2:
        # Default to the specified file
        csv_file = "gy91_data_20261116_155307.csv"
        print(f"No file specified, using default: {csv_file}")
    else:
        csv_file = sys.argv[1]
    
    plot_gy91_data(csv_file)


if __name__ == "__main__":
    main()