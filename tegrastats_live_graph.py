import sys
import re
import time
import asciichartpy
import csv
import shutil
from datetime import datetime

CHART_HEIGHT = 10
save_csv = True
csv_file = "tegrastats_log.csv"

history = {
    "cpu": [],
    "ram": [],
    "gpu": [],
    "temp": [],
    "power": [],
    "cpu_freq": [],
    "gpu_freq": []
}

def get_terminal_widths():
    term_size = shutil.get_terminal_size((120, 40))
    total_width = term_size.columns
    gutter = 4
    usable = total_width - gutter
    half_width = (usable // 2) - 1
    return half_width, half_width, gutter

def format_stats(data, unit):
    if not data:
        return ""
    return f"Min: {min(data):.2f} {unit}   Max: {max(data):.2f} {unit}   Last: {data[-1]:.2f} {unit}"

def get_scaled_chart(data, height, width, fixed_min=None, fixed_max=None):
    data = data[-width:]
    if data:
        data += [data[-1]]

    data_min = min(data)
    data_max = max(data)

    if fixed_min is not None:
        data_min = fixed_min
    if fixed_max is not None:
        data_max = fixed_max
    if data_min == data_max:
        data_max += 1

    raw_chart = asciichartpy.plot(data, {
        'height': height,
        'min': data_min,
        'max': data_max,
        'offset': 2
    }).splitlines()

    return [line[:width].ljust(width) for line in raw_chart]

def format_dual_column(label1, data1, unit1, label2, data2, unit2, min1=None, max1=None, min2=None, max2=None):
    left_width, right_width, gutter = get_terminal_widths()

    chart1 = get_scaled_chart(data1, CHART_HEIGHT, left_width, min1, max1)
    chart2 = get_scaled_chart(data2, CHART_HEIGHT, right_width, min2, max2)

    header1 = f"{label1} ({unit1})".ljust(left_width)
    header2 = f"{label2} ({unit2})".ljust(right_width)
    stats1 = format_stats(data1, unit1).ljust(left_width)
    stats2 = format_stats(data2, unit2).ljust(right_width)

    lines = [f"{header1}{' ' * gutter}{header2}",
             f"{stats1}{' ' * gutter}{stats2}"]

    for l1, l2 in zip(chart1, chart2):
        lines.append(f"{l1}{' ' * gutter}{l2}")

    return "\n".join(lines)

def format_full_width(label, data, unit):
    total_width = shutil.get_terminal_size((120, 40)).columns
    chart = get_scaled_chart(data, CHART_HEIGHT, total_width)
    header = f"{label} ({unit})".center(total_width)
    stats = format_stats(data, unit).center(total_width)
    return f"{header}\n{stats}\n" + "\n".join(chart)

def parse_tegrastats_line(line):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    ram_match = re.search(r"RAM (\d+)/(\d+)MB", line)
    ram_used = int(ram_match.group(1))

    cpu_matches = re.findall(r"(\d+)%@", line)
    cpu_usages = list(map(int, cpu_matches))
    cpu_avg = sum(cpu_usages) / len(cpu_usages) if cpu_usages else 0

    cpu_freqs_match = re.findall(r"%@(\d+)", line)
    cpu_freqs = list(map(int, cpu_freqs_match))
    cpu_freq_avg = sum(cpu_freqs) / len(cpu_freqs) if cpu_freqs else 0

    gpu_match = re.search(r"GR3D_FREQ (\d+)%", line)
    gpu = int(gpu_match.group(1)) if gpu_match else 0
    gpu_freq = gpu * 10  # estimate assuming 1000 MHz max

    temp_match = re.search(r"cpu@([\d.]+)C", line)
    temp = float(temp_match.group(1)) if temp_match else 0

    power_match = re.search(r"VDD_IN (\d+)mW", line)
    power = int(power_match.group(1)) / 1000 if power_match else 0  # Watts

    return timestamp, cpu_avg, ram_used, gpu, temp, power, cpu_freq_avg, gpu_freq

# Init CSV
if save_csv:
    with open(csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "cpu_usage", "ram_used_mb", "gpu_usage", "temp_c", "power_w", "cpu_freq_mhz", "gpu_freq_mhz"])

try:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            timestamp, cpu, ram, gpu, temp, power, cpu_freq, gpu_freq = parse_tegrastats_line(line)
        except Exception:
            continue

        for key, val in zip(history.keys(), [cpu, ram, gpu, temp, power, cpu_freq, gpu_freq]):
            history[key].append(val)
            if len(history[key]) > shutil.get_terminal_size().columns:
                history[key].pop(0)

        if save_csv:
            with open(csv_file, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, cpu, ram, gpu, temp, power, cpu_freq, gpu_freq])

        print("\033[H\033[J", end="")  # clear screen

        print(format_dual_column("CPU Usage", history["cpu"], "%",
                                 "GPU Usage", history["gpu"], "%"))
        print()
        print(format_dual_column("RAM Usage", history["ram"], "MB",
                                 "Power Draw", history["power"], "W"))
        print()
        print(format_dual_column("CPU Frequency", history["cpu_freq"], "MHz",
                                 "GPU Frequency (est.)", history["gpu_freq"], "MHz",
                                 min1=500, max1=1800, min2=0, max2=1000))
        print()
        print(format_full_width("CPU Temperature", history["temp"], "°C"))
        time.sleep(0.2)

except KeyboardInterrupt:
    print("\nExiting.")
