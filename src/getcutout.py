#!/usr/bin/env python3

import os
import sys
import re
import json
import fnmatch
import subprocess
from svg.path import Path, Line, Arc, CubicBezier, QuadraticBezier, parse_path

if os.getuid() != 0:
    print("must run as root, exiting")
    sys.exit(1)

def parse_svg_string(svg_string, width):
    target_x = width / 2

    if '@right' in svg_string:
        target_x = width * 90 / 100
        svg_string = svg_string.replace('@right', '')
    elif '@left' in svg_string:
        target_x = width * 10 / 100
        svg_string = svg_string.replace('@left', '')

    return svg_string, target_x

def reposition_svg(svg_string, width):
    svg_string, target_x = parse_svg_string(svg_string, width)
    # Extract the d attribute from the path
    path_d_match = re.search('M(.*?)Z', svg_string)
    if path_d_match is None:
        print('No matching path found in SVG string')
        return None

    path_d = path_d_match.group(0)
    path = parse_path(path_d)

    # Compute the current center
    x_coordinates = [point.real for segment in path for point in [segment.start, segment.end]]

    min_x, max_x = min(x_coordinates), max(x_coordinates)
    current_center_x = (min_x + max_x) / 2
    shift_distance = target_x - current_center_x
    new_path = Path()

    for segment in path:
        # Create a new segment of the same type
        if isinstance(segment, Line):
            new_segment = Line(segment.start + complex(shift_distance, 0), segment.end + complex(shift_distance, 0))
        elif isinstance(segment, CubicBezier):
            new_segment = CubicBezier(segment.start + complex(shift_distance, 0), segment.control1 + complex(shift_distance, 0), segment.control2 + complex(shift_distance, 0), segment.end + complex(shift_distance, 0))
        elif isinstance(segment, QuadraticBezier):
            new_segment = QuadraticBezier(segment.start + complex(shift_distance, 0), segment.control + complex(shift_distance, 0), segment.end + complex(shift_distance, 0))
        elif isinstance(segment, Arc):
            new_segment = Arc(segment.start + complex(shift_distance, 0), segment.radius, segment.rotation, segment.large_arc, segment.sweep, segment.end + complex(shift_distance, 0))
        else:
            continue

        new_path.append(new_segment)

    return new_path.d()

def extract_value_from_prop(file, prop):
    with open(file, 'r') as f:
        for line in f:
            if line.startswith(prop):
                return line.split('=')[1].strip()

def get_cutout(rro_file):
    command = ['getoverlay', '-p', rro_file, '-c', 'config_mainBuiltInDisplayCutout']
    cutout_bytes = subprocess.check_output(command)
    cutout = cutout_bytes.decode('utf-8', 'ignore').strip()
    if "Failed to get value" in cutout:
        return None

    return cutout

def find_apk_with_properties(root_dir):
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if not 'emulation' in d.lower()]
        files = [f for f in files if not 'emulation' in f.lower()]
        for filename in files:
            if filename.endswith('.apk'):
                rro_file = os.path.join(root, filename)
                radius = os.popen(f'getoverlay -p {rro_file} -c rounded_corner_radius_top').read().strip()
                if "Failed to get value" in radius:
                    continue

                cutout = get_cutout(rro_file)
                if cutout is None:
                    continue

                return rro_file

    return None

prop_files = [
    '/var/lib/lxc/android/rootfs/vendor/build.prop',
    '/android/vendor/build.prop',
    '/vendor/build.prop'
]

prop_file = None
for file in prop_files:
    if os.path.exists(file):
        prop_file = file
        break

if prop_file is None:
    print("no valid prop files found, exiting")
    sys.exit(0)

manufacturer = extract_value_from_prop(prop_file, 'ro.product.vendor.manufacturer')
model = extract_value_from_prop(prop_file, 'ro.product.vendor.model')
apiver = extract_value_from_prop(prop_file, 'ro.vendor.build.version.sdk')

rro_file = find_apk_with_properties('/vendor/overlay')

if rro_file is None:
    print("no valid files found, exiting")
    sys.exit(0)

if rro_file and os.path.exists(rro_file):
    radius = os.popen(f'getoverlay -p {rro_file} -c rounded_corner_radius_top').read().strip()
    if "Failed to get value" not in radius:
        radius = int(radius.rstrip('px').rstrip('dp'))
    else:
        radius = None

    if os.path.exists(rro_file):
        cutout = get_cutout(rro_file)
        if cutout is not None:
            cutout = reposition_svg(cutout, 1080)

    if radius is None and cutout is None:
        print("Device does not have a display cutout or a specified border radius.")
        sys.exit(0)

    json_obj = {
        "name": f"{manufacturer} {model}"
    }

    # "x-res": 1080,
    # "y-res": 2340
    # these can be added later if needed but it seems to work fine without it

    if radius is not None:
        json_obj["border-radius"] = radius
    if cutout is not None:
        json_obj["cutouts"] = [{"name": "notch", "path": cutout}]

    with open('output.json', 'w') as json_file:
        json.dump(json_obj, json_file, indent=4)

else:
    print(f"{rro_file} does not exist, exiting")
    sys.exit(0)