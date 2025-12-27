"""
Add displacement magnitude and von Mises stress fields to VTK file.
"""

import os
import numpy as np


def process_vtk_file(input_vtk, output_vtk):
    """
    Read VTK file, compute derived fields, and write new VTK with additional data.
    """
    print(f"Reading: {input_vtk}")

    with open(input_vtk, 'r') as f:
        lines = f.readlines()

    # Parse the VTK file
    header_lines = []
    points_section = []
    cells_section = []
    cell_types_section = []
    point_data_section = []

    i = 0
    n_points = 0
    n_cells = 0
    point_data = {}
    in_point_data = False
    current_scalar = None
    current_values = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("POINTS"):
            parts = stripped.split()
            n_points = int(parts[1])
            points_section.append(line)
            i += 1
            # Read point coordinates
            while i < len(lines) and len(points_section) < n_points + 1:
                points_section.append(lines[i])
                i += 1
            continue

        elif stripped.startswith("CELLS"):
            parts = stripped.split()
            n_cells = int(parts[1])
            cells_section.append(line)
            i += 1
            while i < len(lines) and not lines[i].strip().startswith(("CELL_TYPES", "POINT_DATA")):
                cells_section.append(lines[i])
                i += 1
            continue

        elif stripped.startswith("CELL_TYPES"):
            cell_types_section.append(line)
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("POINT_DATA"):
                cell_types_section.append(lines[i])
                i += 1
            continue

        elif stripped.startswith("POINT_DATA"):
            in_point_data = True
            i += 1
            continue

        elif in_point_data and stripped.startswith("SCALARS"):
            # Save previous scalar if any
            if current_scalar and current_values:
                point_data[current_scalar] = np.array(current_values)

            parts = stripped.split()
            current_scalar = parts[1]
            current_values = []
            i += 1
            # Skip LOOKUP_TABLE line
            if i < len(lines) and lines[i].strip().startswith("LOOKUP_TABLE"):
                i += 1
            continue

        elif in_point_data and current_scalar:
            # Read scalar values
            if stripped and not stripped.startswith(("SCALARS", "VECTORS", "CELL_DATA")):
                vals = stripped.split()
                current_values.extend([float(v) for v in vals])
            i += 1
            continue

        else:
            if not in_point_data:
                header_lines.append(line)
            i += 1

    # Save last scalar
    if current_scalar and current_values:
        point_data[current_scalar] = np.array(current_values)

    print(f"  Points: {n_points}")
    print(f"  Cells: {n_cells}")
    print(f"  Available fields: {list(point_data.keys())}")

    # Compute displacement magnitude
    disp_mag = None
    if 'u' in point_data and 'v' in point_data and 'w' in point_data:
        u = point_data['u']
        v = point_data['v']
        w = point_data['w']
        disp_mag = np.sqrt(u**2 + v**2 + w**2)
        print(f"  Displacement magnitude: min={disp_mag.min():.6e}, max={disp_mag.max():.6e} m")

    # Compute von Mises stress from membrane stress resultants
    von_mises = None
    if 'sx0' in point_data and 'sy0' in point_data and 'sxy0' in point_data:
        sx = point_data['sx0']
        sy = point_data['sy0']
        sxy = point_data['sxy0']
        # von Mises for plane stress
        von_mises = np.sqrt(sx**2 - sx*sy + sy**2 + 3*sxy**2)
        print(f"  Von Mises stress: min={von_mises.min():.6e}, max={von_mises.max():.6e} N/m")

    # Write new VTK file
    print(f"\nWriting: {output_vtk}")

    with open(output_vtk, 'w') as f:
        # Write header
        for line in header_lines:
            f.write(line)

        # Write points
        for line in points_section:
            f.write(line)

        # Write cells
        for line in cells_section:
            f.write(line)

        # Write cell types
        for line in cell_types_section:
            f.write(line)

        # Write point data
        f.write(f"POINT_DATA {n_points}\n")

        # Write displacement magnitude first (most useful)
        if disp_mag is not None:
            f.write("SCALARS displacement_magnitude float 1\n")
            f.write("LOOKUP_TABLE default\n")
            for val in disp_mag:
                f.write(f"{val:.8e}\n")

        # Write von Mises stress
        if von_mises is not None:
            f.write("SCALARS von_mises_stress float 1\n")
            f.write("LOOKUP_TABLE default\n")
            for val in von_mises:
                f.write(f"{val:.8e}\n")

        # Write displacement as a vector field
        if 'u' in point_data and 'v' in point_data and 'w' in point_data:
            f.write("VECTORS displacement float\n")
            u = point_data['u']
            v = point_data['v']
            w = point_data['w']
            for j in range(len(u)):
                f.write(f"{u[j]:.8e} {v[j]:.8e} {w[j]:.8e}\n")

        # Write original scalar fields
        for name, values in point_data.items():
            f.write(f"SCALARS {name} float 1\n")
            f.write("LOOKUP_TABLE default\n")
            for val in values:
                f.write(f"{val:.8e}\n")

    print("Done!")

    # Print summary
    print("\n" + "=" * 50)
    print("FIELDS AVAILABLE IN OUTPUT VTK:")
    print("=" * 50)
    print("  - displacement_magnitude: sqrt(u² + v² + w²) [m]")
    print("  - von_mises_stress: von Mises criterion [N/m]")
    print("  - displacement: vector (u, v, w) for Warp filter")
    print("  - Original fields: u, v, w, rotx, roty, rotz, sx0, sy0, sxy0, etc.")
    print("\nIn ParaView:")
    print("  1. Color by 'displacement_magnitude' or 'von_mises_stress'")
    print("  2. Use Filters > Warp By Vector > 'displacement' to show deformed shape")


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_vtk = os.path.join(script_dir, "nanuqx_flight_000.vtk")
    output_vtk = os.path.join(script_dir, "nanuqx_flight_with_fields.vtk")

    if not os.path.exists(input_vtk):
        print(f"Error: Input VTK file not found: {input_vtk}")
        exit(1)

    process_vtk_file(input_vtk, output_vtk)
