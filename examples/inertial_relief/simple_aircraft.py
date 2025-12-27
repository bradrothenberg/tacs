"""
Simple Aircraft Inertial Relief Example

This example creates a simplified aircraft structure (fuselage + wings)
and demonstrates inertial relief analysis for flight loads.

The aircraft is modeled with:
- Fuselage: beam elements along the x-axis
- Wings: shell elements extending in the y-direction
- Applied loads: lift on wings, weight distribution

Inertial relief balances the loads so the structure can be analyzed
without artificial boundary conditions.
"""

import os
import numpy as np

# Create output directory
output_dir = os.path.dirname(os.path.abspath(__file__))
os.makedirs(output_dir, exist_ok=True)


def create_aircraft_bdf(filename):
    """
    Create a simple aircraft BDF file with fuselage and wings.
    """
    # Aircraft dimensions (in meters, scaled for visualization)
    fuselage_length = 20.0  # Total fuselage length
    wing_span = 15.0  # Half-span (one side)
    wing_chord = 3.0  # Wing chord
    wing_position = 8.0  # X position of wing root

    # Mesh density
    n_fuselage = 21  # Nodes along fuselage
    n_wing_span = 11  # Nodes along wing span
    n_wing_chord = 3  # Nodes along chord

    # Material properties (aluminum)
    E = 70e9  # Young's modulus (Pa)
    nu = 0.3  # Poisson's ratio
    rho = 2700.0  # Density (kg/m^3)

    # Shell thickness
    t_wing = 0.01  # 10 mm wing skin
    t_fuselage = 0.005  # 5 mm fuselage skin

    with open(filename, "w") as f:
        f.write("$ pyNastran : punch=True\n")
        f.write("$ Simple Aircraft Model for Inertial Relief Demo\n")
        f.write("$ Units: SI (meters, Newtons, kg)\n")

        node_id = 1
        elem_id = 1

        # ============ FUSELAGE NODES (along x-axis) ============
        fuselage_nodes = []
        for i in range(n_fuselage):
            x = i * fuselage_length / (n_fuselage - 1)
            y = 0.0
            z = 0.0
            f.write(f"GRID,{node_id},,{x},{y},{z}\n")
            fuselage_nodes.append(node_id)
            node_id += 1

        # ============ LEFT WING NODES ============
        left_wing_nodes = []
        # Find fuselage node closest to wing position
        wing_root_idx = int(wing_position / fuselage_length * (n_fuselage - 1))

        for j in range(n_wing_span):
            row = []
            y = -(j + 1) * wing_span / n_wing_span  # Negative y for left wing
            for k in range(n_wing_chord):
                x = wing_position + k * wing_chord / (n_wing_chord - 1)
                z = 0.0
                f.write(f"GRID,{node_id},,{x},{y},{z}\n")
                row.append(node_id)
                node_id += 1
            left_wing_nodes.append(row)

        # ============ RIGHT WING NODES ============
        right_wing_nodes = []
        for j in range(n_wing_span):
            row = []
            y = (j + 1) * wing_span / n_wing_span  # Positive y for right wing
            for k in range(n_wing_chord):
                x = wing_position + k * wing_chord / (n_wing_chord - 1)
                z = 0.0
                f.write(f"GRID,{node_id},,{x},{y},{z}\n")
                row.append(node_id)
                node_id += 1
            right_wing_nodes.append(row)

        # ============ MATERIAL ============
        f.write("$\n$ Material Properties\n$\n")
        # MAT1 format: MAT1, MID, E, G, NU, RHO, ...
        # Use small-field format (8 chars per field)
        f.write(f"MAT1,1,{E:.3e},,{nu},{rho}\n")

        # ============ SHELL PROPERTY FOR WINGS ============
        f.write("$\n$ Shell Property for Wings\n$\n")
        f.write(f"PSHELL,1,1,{t_wing},1,,1\n")

        # ============ SHELL PROPERTY FOR FUSELAGE ============
        f.write(f"PSHELL,2,1,{t_fuselage},1,,1\n")

        # ============ LEFT WING SHELL ELEMENTS ============
        f.write("$\n$ Left Wing Elements\n$\n")

        # Connect wing root to fuselage
        for k in range(n_wing_chord):
            x = wing_position + k * wing_chord / (n_wing_chord - 1)
            # Find closest fuselage node
            fuse_idx = int(x / fuselage_length * (n_fuselage - 1))
            fuse_idx = max(0, min(fuse_idx, n_fuselage - 1))

        # Wing panels
        for j in range(n_wing_span - 1):
            for k in range(n_wing_chord - 1):
                n1 = left_wing_nodes[j][k]
                n2 = left_wing_nodes[j][k + 1]
                n3 = left_wing_nodes[j + 1][k + 1]
                n4 = left_wing_nodes[j + 1][k]
                f.write(f"CQUAD4,{elem_id},1,{n1},{n2},{n3},{n4}\n")
                elem_id += 1

        # ============ RIGHT WING SHELL ELEMENTS ============
        f.write("$\n$ Right Wing Elements\n$\n")
        for j in range(n_wing_span - 1):
            for k in range(n_wing_chord - 1):
                n1 = right_wing_nodes[j][k]
                n2 = right_wing_nodes[j][k + 1]
                n3 = right_wing_nodes[j + 1][k + 1]
                n4 = right_wing_nodes[j + 1][k]
                f.write(f"CQUAD4,{elem_id},1,{n1},{n2},{n3},{n4}\n")
                elem_id += 1

        # ============ FUSELAGE SHELL ELEMENTS (simplified as beam-like shells) ============
        f.write("$\n$ Fuselage Elements (simplified)\n$\n")
        # Create a simple rectangular cross-section around fuselage axis
        fuselage_width = 1.5
        fuselage_height = 1.5

        # Add nodes for fuselage cross-section at each station
        fuselage_shell_nodes = []
        for i in range(n_fuselage):
            x = i * fuselage_length / (n_fuselage - 1)
            cross_section = []
            # Top
            f.write(f"GRID,{node_id},,{x},{0.0},{fuselage_height/2}\n")
            cross_section.append(node_id)
            node_id += 1
            # Bottom
            f.write(f"GRID,{node_id},,{x},{0.0},{-fuselage_height/2}\n")
            cross_section.append(node_id)
            node_id += 1
            fuselage_shell_nodes.append(cross_section)

        # Create fuselage shell panels (top and bottom surfaces)
        for i in range(n_fuselage - 1):
            # Top surface
            n1 = fuselage_shell_nodes[i][0]
            n2 = fuselage_shell_nodes[i + 1][0]
            n3 = fuselage_nodes[i + 1]
            n4 = fuselage_nodes[i]
            f.write(f"CQUAD4,{elem_id},2,{n1},{n2},{n3},{n4}\n")
            elem_id += 1

            # Bottom surface
            n1 = fuselage_nodes[i]
            n2 = fuselage_nodes[i + 1]
            n3 = fuselage_shell_nodes[i + 1][1]
            n4 = fuselage_shell_nodes[i][1]
            f.write(f"CQUAD4,{elem_id},2,{n1},{n2},{n3},{n4}\n")
            elem_id += 1

        # ============ RBE2 CONNECTIONS (wing root to fuselage) ============
        f.write("$\n$ Wing-Fuselage Connections\n$\n")

        # Connect left wing root nodes to fuselage
        wing_root_fuse_node = fuselage_nodes[wing_root_idx]
        left_root_nodes = [left_wing_nodes[0][k] for k in range(n_wing_chord)]
        dep_nodes_str = ",".join([str(n) for n in left_root_nodes])
        f.write(f"RBE2,{elem_id},{wing_root_fuse_node},123456,{dep_nodes_str}\n")
        elem_id += 1

        # Connect right wing root nodes to fuselage
        right_root_nodes = [right_wing_nodes[0][k] for k in range(n_wing_chord)]
        dep_nodes_str = ",".join([str(n) for n in right_root_nodes])
        f.write(f"RBE2,{elem_id},{wing_root_fuse_node},123456,{dep_nodes_str}\n")
        elem_id += 1

        # ============ MINIMAL CONSTRAINTS (for solver stability) ============
        # Add minimal constraints at nose and tail to prevent rigid body motion
        # These should have minimal effect with balanced inertial relief
        f.write("$\n$ Minimal Constraints for Solver Stability\n$\n")
        # Constrain nose in all 6 DOF
        nose_node = fuselage_nodes[0]
        f.write(f"SPC1,1,123456,{nose_node}\n")
        # Constrain tail in lateral (Y) direction to prevent rotation
        tail_node = fuselage_nodes[-1]
        f.write(f"SPC1,1,2,{tail_node}\n")

    print(f"Created aircraft BDF: {filename}")
    print(f"  Nodes: {node_id - 1}")
    print(f"  Elements: {elem_id - 1}")

    return {
        "fuselage_nodes": fuselage_nodes,
        "left_wing_nodes": left_wing_nodes,
        "right_wing_nodes": right_wing_nodes,
        "wing_root_idx": wing_root_idx,
    }


def run_inertial_relief_analysis():
    """
    Run the inertial relief analysis on the aircraft model.
    """
    from mpi4py import MPI
    from tacs import pytacs, functions, TACS

    comm = MPI.COMM_WORLD

    # Create the BDF file
    bdf_file = os.path.join(output_dir, "simple_aircraft.bdf")
    mesh_info = create_aircraft_bdf(bdf_file)

    # Create FEA assembler
    fea_assembler = pytacs.pyTACS(bdf_file, comm)
    fea_assembler.initialize()

    # Create static problem
    problem = fea_assembler.createStaticProblem("flight_loads")

    # Add functions to evaluate
    problem.addFunction("mass", functions.StructuralMass)
    problem.addFunction("ks_vmfailure", functions.KSFailure, safetyFactor=1.5, ksWeight=100.0)

    # ============ APPLY FLIGHT LOADS ============
    # Simulate 2.5g pull-up maneuver

    g = 9.81  # gravity
    load_factor = 2.5

    # Get node information
    bdf = fea_assembler.getBDFInfo()

    # Apply lift loads on wing nodes (upward force)
    # Distribute lift elliptically along span
    total_weight = None  # Will compute from mass

    # First, compute mass to determine required lift
    funcs = {}
    problem.evalFunctions(funcs)
    aircraft_mass = funcs["flight_loads_mass"]
    print(f"\nAircraft mass: {aircraft_mass:.2f} kg")

    # Total lift required for 2.5g
    total_lift = aircraft_mass * g * load_factor
    print(f"Total lift required (2.5g): {total_lift:.2f} N")

    # Distribute lift on wing nodes (simplified uniform distribution)
    left_wing_flat = [n for row in mesh_info["left_wing_nodes"] for n in row]
    right_wing_flat = [n for row in mesh_info["right_wing_nodes"] for n in row]
    all_wing_nodes = left_wing_flat + right_wing_flat

    lift_per_node = total_lift / len(all_wing_nodes)
    print(f"Lift per wing node: {lift_per_node:.2f} N")

    # Apply lift (upward in z)
    for node_id in all_wing_nodes:
        problem.addLoadToNodes(
            [node_id], [0.0, 0.0, lift_per_node, 0.0, 0.0, 0.0], nastranOrdering=True
        )

    # Apply weight (downward gravity load) - this would normally be done via inertial load
    # but for demonstration, we'll let inertial relief handle it
    # problem.addInertialLoad([0.0, 0.0, -g * load_factor])

    print("\n" + "=" * 60)
    print("APPLYING INERTIAL RELIEF")
    print("=" * 60)

    # Apply inertial relief
    relief_info = problem.applyInertialRelief(dof=6)

    print(f"\nMass: {relief_info['mass']:.4f} kg")
    print(f"Center of Gravity: [{relief_info['cg'][0]:.3f}, {relief_info['cg'][1]:.3f}, {relief_info['cg'][2]:.3f}] m")
    print(f"\nInertia Tensor (about CG):")
    print(f"  Ixx: {relief_info['inertia'][0,0]:.2f} kg*m^2")
    print(f"  Iyy: {relief_info['inertia'][1,1]:.2f} kg*m^2")
    print(f"  Izz: {relief_info['inertia'][2,2]:.2f} kg*m^2")

    print(f"\nTotal Applied Force: [{relief_info['totalForce'][0]:.2f}, {relief_info['totalForce'][1]:.2f}, {relief_info['totalForce'][2]:.2f}] N")
    print(f"Total Applied Moment: [{relief_info['totalMoment'][0]:.2f}, {relief_info['totalMoment'][1]:.2f}, {relief_info['totalMoment'][2]:.2f}] N*m")

    print(f"\nComputed Linear Acceleration: [{relief_info['linearAccel'][0]:.4f}, {relief_info['linearAccel'][1]:.4f}, {relief_info['linearAccel'][2]:.4f}] m/s^2")
    print(f"Computed Angular Acceleration: [{relief_info['angularAccel'][0]:.6f}, {relief_info['angularAccel'][1]:.6f}, {relief_info['angularAccel'][2]:.6f}] rad/s^2")

    # Check equilibrium after relief
    force_after, moment_after = problem._computeAppliedLoadResultant(relief_info["cg"])
    print(f"\nForce after relief: [{force_after[0]:.6f}, {force_after[1]:.6f}, {force_after[2]:.6f}] N")
    print(f"  (should be near zero for 3-DOF equilibrium)")

    # ============ SOLVE ============
    print("\n" + "=" * 60)
    print("SOLVING")
    print("=" * 60)

    # Note: For a truly free-free structure, we need to add some minimal constraints
    # to prevent rigid body motion. Add a single point constraint at the CG.
    # In practice, inertial relief makes the problem determinate, but numerical
    # issues may require a soft spring or single point constraint.

    # For this demo, we'll add minimal constraints at the fuselage center
    center_node = mesh_info["fuselage_nodes"][len(mesh_info["fuselage_nodes"]) // 2]

    problem.solve()

    # Evaluate functions
    problem.evalFunctions(funcs)
    print(f"\nKS Failure Index: {funcs.get('flight_loads_ks_vmfailure', 'N/A')}")

    # ============ WRITE OUTPUT ============
    print("\n" + "=" * 60)
    print("WRITING OUTPUT")
    print("=" * 60)

    # Write solution to F5 file
    problem.writeSolution(outputDir=output_dir)

    f5_file = os.path.join(output_dir, "flight_loads_000.f5")
    print(f"Solution written to: {f5_file}")

    # Convert to VTK for visualization
    vtk_file = convert_f5_to_vtk(f5_file)

    return relief_info, funcs, f5_file


def convert_f5_to_vtk(f5_file):
    """Convert F5 file to VTK using f5tovtk utility."""
    import subprocess

    vtk_file = f5_file.replace(".f5", ".vtk")

    # Try to run f5tovtk - look in extern directory relative to TACS root
    tacs_root = os.path.dirname(os.path.dirname(output_dir))
    f5tovtk_path = os.path.join(tacs_root, "extern", "f5tovtk", "f5tovtk")

    try:
        result = subprocess.run(
            [f5tovtk_path, f5_file],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(f5_file),
        )
        print(f"f5tovtk output: {result.stdout} {result.stderr}")
        if os.path.exists(vtk_file):
            print(f"Converted to VTK: {vtk_file}")
            return vtk_file
    except Exception as e:
        print(f"Could not run f5tovtk: {e}")

    return None


def read_vtk_file(vtk_file):
    """Read VTK file and extract nodes, elements, and data."""
    nodes = {}
    cells = []
    point_data = {}
    cell_data = {}

    if not os.path.exists(vtk_file):
        return None, None, None, None

    with open(vtk_file, "r") as f:
        lines = f.readlines()

    i = 0
    n_points = 0
    while i < len(lines):
        line = lines[i].strip()

        if line.startswith("POINTS"):
            parts = line.split()
            n_points = int(parts[1])
            i += 1
            for j in range(n_points):
                coords = lines[i].strip().split()
                nodes[j] = np.array([float(c) for c in coords[:3]])
                i += 1

        elif line.startswith("CELLS"):
            parts = line.split()
            n_cells = int(parts[1])
            i += 1
            for j in range(n_cells):
                cell_data_line = lines[i].strip().split()
                n_verts = int(cell_data_line[0])
                verts = [int(v) for v in cell_data_line[1 : n_verts + 1]]
                cells.append(verts)
                i += 1

        elif line.startswith("POINT_DATA"):
            n_points = int(line.split()[1])
            i += 1
            # Don't increment again at the end - continue to next iteration
            continue

        elif line.startswith("SCALARS"):
            parts = line.split()
            data_name = parts[1]
            i += 1
            if i < len(lines) and lines[i].strip().startswith("LOOKUP_TABLE"):
                i += 1
            # Read scalar data - one value per line for n_points
            values = []
            while i < len(lines) and len(values) < n_points:
                val_line = lines[i].strip()
                if val_line and not val_line.startswith(("SCALARS", "VECTORS", "CELL_DATA", "POINT_DATA")):
                    vals = val_line.split()
                    values.extend([float(v) for v in vals])
                    i += 1
                else:
                    break
            point_data[data_name] = np.array(values)
            continue

        elif line.startswith("CELL_DATA"):
            n_cells = int(line.split()[1])
            i += 1
            continue

        else:
            i += 1

    return nodes, cells, point_data, cell_data


def create_visualization(relief_info=None):
    """
    Create a matplotlib visualization of the aircraft and results.
    """
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    import matplotlib.colors as mcolors
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import Normalize

    # Try to read VTK file for stress data - use VTK data directly for accurate stress visualization
    vtk_file = os.path.join(output_dir, "flight_loads_000.vtk")
    print(f"Looking for VTK file: {vtk_file}")
    vtk_nodes, vtk_cells, vtk_point_data, vtk_cell_data = read_vtk_file(vtk_file)

    use_vtk_geometry = False
    if vtk_nodes is not None and vtk_cells is not None:
        print(f"Loaded VTK file with {len(vtk_nodes)} nodes and {len(vtk_cells)} cells")
        use_vtk_geometry = True
    else:
        print("VTK file not found or could not be read - falling back to BDF geometry")

    # Read the BDF to get geometry as fallback
    bdf_file = os.path.join(output_dir, "simple_aircraft.bdf")

    # Parse nodes and elements from BDF (comma-separated format)
    bdf_nodes = {}
    bdf_quads = []

    with open(bdf_file, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("GRID,"):
                parts = line.split(",")
                node_id = int(parts[1])
                x = float(parts[3])
                y = float(parts[4])
                z = float(parts[5])
                bdf_nodes[node_id] = np.array([x, y, z])
            elif line.startswith("CQUAD4,"):
                parts = line.split(",")
                elem_id = int(parts[1])
                prop_id = int(parts[2])
                n1 = int(parts[3])
                n2 = int(parts[4])
                n3 = int(parts[5])
                n4 = int(parts[6])
                bdf_quads.append((n1, n2, n3, n4, prop_id))

    # Compute von Mises stress from stress components if available
    von_mises = None
    if vtk_point_data is not None:
        # Shell elements output stress resultants: sx0, sy0, sxy0, etc.
        stress_vars = [k for k in vtk_point_data.keys() if k.startswith("s")]
        if stress_vars:
            print(f"Available stress variables: {stress_vars}")

        # Try to compute von Mises from membrane stresses
        if "sx0" in vtk_point_data and "sy0" in vtk_point_data and "sxy0" in vtk_point_data:
            sx = vtk_point_data["sx0"]
            sy = vtk_point_data["sy0"]
            sxy = vtk_point_data["sxy0"]
            # von Mises for plane stress (using stress resultants)
            # Note: These are stress resultants (N/m), not true stresses (Pa)
            von_mises = np.sqrt(sx**2 - sx * sy + sy**2 + 3 * sxy**2)
            print(f"Computed von Mises stress resultant: min={np.nanmin(von_mises):.2e}, max={np.nanmax(von_mises):.2e}")

    # Try to get displacements
    displacements = None
    if vtk_point_data is not None:
        print(f"Available point data fields: {list(vtk_point_data.keys())}")
        if "u" in vtk_point_data and "v" in vtk_point_data and "w" in vtk_point_data:
            u = vtk_point_data["u"]
            v = vtk_point_data["v"]
            w = vtk_point_data["w"]
            print(f"Displacement array lengths: u={len(u)}, v={len(v)}, w={len(w)}")
            displacements = np.column_stack([u, v, w])
            disp_mag_temp = np.sqrt(u**2 + v**2 + w**2)
            print(f"Displacement magnitude: min={np.nanmin(disp_mag_temp):.4e}, max={np.nanmax(disp_mag_temp):.4e}")

    # Create figure with 3x2 layout
    fig = plt.figure(figsize=(18, 14))

    # Set up colormap for von Mises stress
    stress_cmap = plt.cm.jet
    stress_norm = None
    if von_mises is not None and len(von_mises) > 0:
        valid_stress = von_mises[~np.isnan(von_mises)]
        if len(valid_stress) > 0:
            vmin, vmax = np.percentile(valid_stress, [5, 95])
            if vmax > vmin:
                stress_norm = Normalize(vmin=vmin, vmax=vmax)
            else:
                stress_norm = Normalize(vmin=0, vmax=max(1, vmax))

    # Set up colormap for displacement magnitude
    disp_cmap = plt.cm.viridis
    disp_norm = None
    disp_mag = None
    if displacements is not None:
        disp_mag = np.sqrt(displacements[:, 0]**2 + displacements[:, 1]**2 + displacements[:, 2]**2)
        valid_disp = disp_mag[~np.isnan(disp_mag)]
        if len(valid_disp) > 0:
            dmin, dmax = np.min(valid_disp), np.max(valid_disp)
            if dmax > dmin:
                disp_norm = Normalize(vmin=dmin, vmax=dmax)
            else:
                disp_norm = Normalize(vmin=0, vmax=max(1e-6, dmax))

    # Helper function to plot elements with stress coloring
    def plot_elements_stress(ax):
        if use_vtk_geometry and vtk_nodes is not None and vtk_cells is not None:
            for idx, cell in enumerate(vtk_cells):
                if len(cell) >= 3:
                    verts = [vtk_nodes[i] for i in cell if i in vtk_nodes]
                    if len(verts) >= 3:
                        if von_mises is not None and stress_norm is not None:
                            valid_nodes = [i for i in cell if i < len(von_mises)]
                            if valid_nodes:
                                elem_stress = np.mean([von_mises[i] for i in valid_nodes])
                                if not np.isnan(elem_stress):
                                    color = stress_cmap(stress_norm(elem_stress))
                                else:
                                    color = "lightgray"
                            else:
                                color = "steelblue"
                        else:
                            color = "steelblue"
                        poly = Poly3DCollection([verts], alpha=0.85, facecolor=color,
                                              edgecolor="k", linewidth=0.2)
                        ax.add_collection3d(poly)
        else:
            for idx, (n1, n2, n3, n4, prop_id) in enumerate(bdf_quads):
                if all(n in bdf_nodes for n in [n1, n2, n3, n4]):
                    verts = [bdf_nodes[n1], bdf_nodes[n2], bdf_nodes[n3], bdf_nodes[n4]]
                    color = "steelblue" if prop_id == 1 else "gray"
                    poly = Poly3DCollection([verts], alpha=0.85, facecolor=color,
                                          edgecolor="k", linewidth=0.2)
                    ax.add_collection3d(poly)

    # Helper function to plot elements with displacement coloring
    def plot_elements_displacement(ax, scale_factor=100.0):
        if use_vtk_geometry and vtk_nodes is not None and vtk_cells is not None and displacements is not None:
            for idx, cell in enumerate(vtk_cells):
                if len(cell) >= 3:
                    # Get deformed vertices
                    verts = []
                    for i in cell:
                        if i in vtk_nodes and i < len(displacements):
                            deformed = vtk_nodes[i] + scale_factor * displacements[i]
                            verts.append(deformed)
                        elif i in vtk_nodes:
                            verts.append(vtk_nodes[i])

                    if len(verts) >= 3:
                        if disp_mag is not None and disp_norm is not None:
                            valid_nodes = [i for i in cell if i < len(disp_mag)]
                            if valid_nodes:
                                elem_disp = np.mean([disp_mag[i] for i in valid_nodes])
                                if not np.isnan(elem_disp):
                                    color = disp_cmap(disp_norm(elem_disp))
                                else:
                                    color = "lightgray"
                            else:
                                color = "steelblue"
                        else:
                            color = "steelblue"
                        poly = Poly3DCollection([verts], alpha=0.85, facecolor=color,
                                              edgecolor="k", linewidth=0.2)
                        ax.add_collection3d(poly)
        else:
            for idx, (n1, n2, n3, n4, prop_id) in enumerate(bdf_quads):
                if all(n in bdf_nodes for n in [n1, n2, n3, n4]):
                    verts = [bdf_nodes[n1], bdf_nodes[n2], bdf_nodes[n3], bdf_nodes[n4]]
                    color = "steelblue" if prop_id == 1 else "gray"
                    poly = Poly3DCollection([verts], alpha=0.85, facecolor=color,
                                          edgecolor="k", linewidth=0.2)
                    ax.add_collection3d(poly)

    # Compute bounds from VTK or BDF data
    if use_vtk_geometry and vtk_nodes:
        all_coords = np.array(list(vtk_nodes.values()))
    else:
        all_coords = np.array(list(bdf_nodes.values()))

    max_range = np.max(all_coords.max(axis=0) - all_coords.min(axis=0)) / 2
    mid = all_coords.mean(axis=0)

    # Row 1: Von Mises Stress views
    # 3D view of aircraft with von Mises stress
    ax1 = fig.add_subplot(231, projection="3d")
    if von_mises is not None and stress_norm is not None:
        ax1.set_title("Von Mises Stress - Isometric", fontsize=11, fontweight="bold")
    else:
        ax1.set_title("Aircraft Structure - Isometric", fontsize=11, fontweight="bold")

    plot_elements_stress(ax1)

    ax1.set_xlim(mid[0] - max_range, mid[0] + max_range)
    ax1.set_ylim(mid[1] - max_range, mid[1] + max_range)
    ax1.set_zlim(mid[2] - max_range * 0.5, mid[2] + max_range * 0.5)
    ax1.set_xlabel("X (m)")
    ax1.set_ylabel("Y (m)")
    ax1.set_zlabel("Z (m)")
    ax1.view_init(elev=25, azim=-60)

    # Top view with stress
    ax2 = fig.add_subplot(232, projection="3d")
    if von_mises is not None and stress_norm is not None:
        ax2.set_title("Von Mises Stress - Top View", fontsize=11, fontweight="bold")
    else:
        ax2.set_title("Top View (Plan)", fontsize=11, fontweight="bold")

    plot_elements_stress(ax2)

    ax2.set_xlim(mid[0] - max_range, mid[0] + max_range)
    ax2.set_ylim(mid[1] - max_range, mid[1] + max_range)
    ax2.set_zlim(mid[2] - max_range * 0.5, mid[2] + max_range * 0.5)
    ax2.set_xlabel("X (m)")
    ax2.set_ylabel("Y (m)")
    ax2.view_init(elev=90, azim=-90)

    # Front view with stress
    ax3 = fig.add_subplot(233, projection="3d")
    if von_mises is not None and stress_norm is not None:
        ax3.set_title("Von Mises Stress - Front View", fontsize=11, fontweight="bold")
    else:
        ax3.set_title("Front View", fontsize=11, fontweight="bold")

    plot_elements_stress(ax3)

    ax3.set_xlim(mid[0] - max_range, mid[0] + max_range)
    ax3.set_ylim(mid[1] - max_range, mid[1] + max_range)
    ax3.set_zlim(mid[2] - max_range * 0.5, mid[2] + max_range * 0.5)
    ax3.set_xlabel("X (m)")
    ax3.set_ylabel("Y (m)")
    ax3.set_zlabel("Z (m)")
    ax3.view_init(elev=0, azim=0)

    # Add stress colorbar
    if von_mises is not None and stress_norm is not None:
        sm = ScalarMappable(cmap=stress_cmap, norm=stress_norm)
        sm.set_array([])
        cbar = fig.colorbar(sm, ax=[ax1, ax2, ax3], shrink=0.5, aspect=15, pad=0.02)
        cbar.set_label("Von Mises Stress Resultant (N/m)", fontsize=9)

    # Row 2: Displacement views
    # Compute displacement scale factor for visibility
    if disp_mag is not None:
        max_disp = np.nanmax(disp_mag)
        if max_disp > 0:
            # Scale displacements to be ~10% of structure size for visibility
            scale_factor = (max_range * 0.1) / max_disp
        else:
            scale_factor = 1.0
    else:
        scale_factor = 1.0

    # Displacement isometric view
    ax4 = fig.add_subplot(234, projection="3d")
    if displacements is not None and disp_norm is not None:
        ax4.set_title(f"Displacement Magnitude - Isometric\n(deformation x{scale_factor:.0f})", fontsize=11, fontweight="bold")
    else:
        ax4.set_title("Displacement - Isometric", fontsize=11, fontweight="bold")

    plot_elements_displacement(ax4, scale_factor=scale_factor)

    ax4.set_xlim(mid[0] - max_range * 1.1, mid[0] + max_range * 1.1)
    ax4.set_ylim(mid[1] - max_range * 1.1, mid[1] + max_range * 1.1)
    ax4.set_zlim(mid[2] - max_range * 0.6, mid[2] + max_range * 0.6)
    ax4.set_xlabel("X (m)")
    ax4.set_ylabel("Y (m)")
    ax4.set_zlabel("Z (m)")
    ax4.view_init(elev=25, azim=-60)

    # Displacement front view (to see bending)
    ax5 = fig.add_subplot(235, projection="3d")
    if displacements is not None and disp_norm is not None:
        ax5.set_title(f"Displacement - Front View\n(deformation x{scale_factor:.0f})", fontsize=11, fontweight="bold")
    else:
        ax5.set_title("Displacement - Front View", fontsize=11, fontweight="bold")

    plot_elements_displacement(ax5, scale_factor=scale_factor)

    ax5.set_xlim(mid[0] - max_range * 1.1, mid[0] + max_range * 1.1)
    ax5.set_ylim(mid[1] - max_range * 1.1, mid[1] + max_range * 1.1)
    ax5.set_zlim(mid[2] - max_range * 0.6, mid[2] + max_range * 0.6)
    ax5.set_xlabel("X (m)")
    ax5.set_ylabel("Y (m)")
    ax5.set_zlabel("Z (m)")
    ax5.view_init(elev=0, azim=0)

    # Add displacement colorbar
    if displacements is not None and disp_norm is not None:
        sm_disp = ScalarMappable(cmap=disp_cmap, norm=disp_norm)
        sm_disp.set_array([])
        cbar_disp = fig.colorbar(sm_disp, ax=[ax4, ax5], shrink=0.5, aspect=15, pad=0.02)
        cbar_disp.set_label("Displacement Magnitude (m)", fontsize=9)

    # Info panel
    ax6 = fig.add_subplot(236)
    ax6.axis("off")
    ax6.set_title("Inertial Relief Analysis Summary", fontsize=11, fontweight="bold")

    # Build info text with actual values if available
    if disp_mag is not None:
        max_disp_val = np.nanmax(disp_mag)
        disp_text = f"Max Displacement: {max_disp_val:.4e} m"
    else:
        disp_text = "Max Displacement: N/A"

    if von_mises is not None:
        max_stress_val = np.nanmax(von_mises)
        stress_text = f"Max Stress Resultant: {max_stress_val:.2e} N/m"
    else:
        stress_text = "Max Stress: N/A"

    info_text = f"""
INERTIAL RELIEF ANALYSIS
========================

Load Case: 2.5g Pull-up Maneuver

Aircraft Properties:
  - Wing Span: 30 m (total)
  - Fuselage Length: 20 m
  - Material: Aluminum (E=70 GPa)

Applied Loads:
  - Lift on wing surfaces
  - Total lift = 2.5 x Weight

Results:
  {disp_text}
  {stress_text}

Inertial Relief:
  - Computes rigid body acceleration
  - Applies d'Alembert (inertia) forces
  - Creates self-equilibrated system
"""
    ax6.text(0.05, 0.95, info_text, transform=ax6.transAxes,
             fontsize=9, verticalalignment="top", fontfamily="monospace",
             bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))

    plt.tight_layout()

    # Save figure
    fig_file = os.path.join(output_dir, "inertial_relief_results.png")
    plt.savefig(fig_file, dpi=150, bbox_inches="tight")
    print(f"\nVisualization saved to: {fig_file}")

    # Don't show in non-interactive mode
    # plt.show()
    plt.close()

    return fig_file


if __name__ == "__main__":
    print("=" * 60)
    print("SIMPLE AIRCRAFT INERTIAL RELIEF EXAMPLE")
    print("=" * 60)

    try:
        # Run analysis
        relief_info, funcs, f5_file = run_inertial_relief_analysis()

        # Create visualization
        fig_file = create_visualization()

        print("\n" + "=" * 60)
        print("ANALYSIS COMPLETE")
        print("=" * 60)
        print(f"\nOutput files:")
        print(f"  - BDF model: {os.path.join(output_dir, 'simple_aircraft.bdf')}")
        print(f"  - Solution: {f5_file}")
        print(f"  - Visualization: {fig_file}")

    except Exception as e:
        print(f"\nError during analysis: {e}")
        import traceback
        traceback.print_exc()

        # Still try to create visualization of geometry
        print("\nAttempting to create geometry visualization...")
        try:
            bdf_file = os.path.join(output_dir, "simple_aircraft.bdf")
            if not os.path.exists(bdf_file):
                create_aircraft_bdf(bdf_file)
            create_visualization()
        except Exception as e2:
            print(f"Visualization also failed: {e2}")
