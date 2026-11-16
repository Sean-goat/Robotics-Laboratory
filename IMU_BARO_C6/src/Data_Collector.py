#!/usr/bin/env python3
"""
Collect data from GY-91 (BMP280 + MPU6050) attached to ESP32-C3.
Data is logged over USB serial to a connected computer and saved to a CSV file.
Data fields:
 accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, pressure, altitude
"""

import serial
import serial.tools.list_ports
import csv
import sys
from datetime import datetime
import time


def list_serial_ports():
    """List all available serial ports."""
    ports = serial.tools.list_ports.comports()
    return [(port.device, port.description) for port in ports]


def select_serial_port():
    """Let user select a serial port."""
    ports = list_serial_ports()
    
    if not ports:
        print("No serial ports found!")
        sys.exit(1)
    
    print("\nAvailable serial ports:")
    for i, (device, description) in enumerate(ports, 1):
        print(f"{i}. {device} - {description}")
    
    while True:
        try:
            choice = input("\nSelect port number (or press Enter for port 1): ").strip()
            if choice == "":
                choice = 1
            else:
                choice = int(choice)
            
            if 1 <= choice <= len(ports):
                return ports[choice - 1][0]
            else:
                print(f"Please enter a number between 1 and {len(ports)}")
        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(0)


def main():
    """Main data collection loop."""
    print("=== GY-91 Data Collector ===")
    
    # Select serial port
    port = select_serial_port()
    baud_rate = 115200
    
    # Create output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"gy91_data_{timestamp}.csv"
    
    print(f"\nConnecting to {port} at {baud_rate} baud...")
    print(f"Data will be saved to: {output_file}")
    print("Press Ctrl+C to stop collection\n")
    
    try:
        # Open serial connection
        ser = serial.Serial(port, baud_rate, timeout=1)
        time.sleep(2)  # Wait for connection to stabilize
        
        # Flush any stale data in buffer
        ser.reset_input_buffer()
        
        # Open CSV file for writing
        with open(output_file, 'w', newline='') as csvfile:
            # Write CSV header (we know the format from the C++ code)
            headers = ['timestamp', 'accel_x', 'accel_y', 'accel_z', 'gyro_x', 'gyro_y', 'gyro_z', 'pressure', 'altitude']
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(headers)
            csvfile.flush()
            
            data_count = 0
            
            print("Collecting data...\n")
            
            while True:
                try:
                    # Read line from serial
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    
                    if not line:
                        continue
                    
                    # Skip the header line if it appears
                    if 'accel_x' in line:
                        continue
                    
                    # Check if line looks like CSV data (contains commas and starts with number/minus)
                    if ',' in line and (line[0].isdigit() or line[0] == '-'):
                        try:
                            # Validate that we can split into expected number of fields
                            fields = line.split(',')
                            if len(fields) == 8:  # Expected number of data fields
                                # Verify fields are numeric
                                _ = [float(f) for f in fields]
                                
                                # Add timestamp
                                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                                csv_writer.writerow([timestamp] + fields)
                                csvfile.flush()
                                
                                data_count += 1
                                print(f"Collected {data_count} samples...", end='\r')
                        except (ValueError, IndexError):
                            # Skip malformed lines
                            pass
                    else:
                        # Print initialization messages
                        if line and not line.startswith(',') and 'accel' not in line.lower():
                            print(f"ESP32: {line}")
                
                except UnicodeDecodeError:
                    # Skip lines with decode errors
                    continue
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    print(f"\nError reading data: {e}")
                    continue
    
    except serial.SerialException as e:
        print(f"\nSerial connection error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n\nData collection stopped.")
        print(f"Total samples collected: {data_count}")
        print(f"Data saved to: {output_file}")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("Serial connection closed.")


if __name__ == "__main__":
    main()


