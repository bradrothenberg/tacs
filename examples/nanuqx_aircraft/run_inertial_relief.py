"""
Inertial Relief Analysis for Nanuqx Flying Wing Aircraft

This script demonstrates 6-DOF inertial relief analysis on an aircraft structure.
Applies simulated flight loads (lift distribution) and computes equilibrium
in an accelerating reference frame.
"""

import os
import sys
import numpy as np

# Add TACS to path
tacs_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, tacs_path)

from mpi4py import MPI
from tacs import pytacs, elements, constitutive, functions


def create_element_callback(dvNum, compID, compDescript, elemDescripts, globalDVs, **kwargs):
    """
    Callback to create shell elements for aircraft structure.
    Uses aluminum 7075-T6 properties.
    """
    # Aluminum 7075-T6 properties
    rho = 2810.0      # kg/m^3
    E = 71.7e9        # Pa
    nu = 0.33
    ys = 503e6        # Yield strength (Pa)

    # Shell thickness (from BDF or default)
    t = 0.002  # 2mm default, will be read from BDF PSHELL

    # Create constitutive object
    prop = constitutive.MaterialProperties(rho=rho, E=E, nu=nu, ys=ys)
    stiff = constitutive.IsoShellConstitutive(prop, t=t, tNum=dvNum)

    # Create transform (shell normal direction)
    transform = None

    # Choose element type based on element description from BDF
    # elemDescripts contains strings like 'CTRIA3' or 'CQUAD4'
    elem = None
    for elemDescript in elemDescripts:
        if elemDescript == 'CTRIA3':
            elem = elements.Tri3Shell(transform, stiff)
            break
        elif elemDescript == 'CQUAD4':
            elem = elements.Quad4Shell(transform, stiff)
            break

    # Default to Tri3Shell if not determined
    if elem is None:
        elem = elements.Tri3Shell(transform, stiff)

    return elem


def apply_flight_loads(problem, fea_assembler, load_factor=2.5):
    """
    Apply simplified flight loads to the aircraft structure.

    For a flying wing, the lift distribution is roughly elliptical.
    We approximate this with loads applied to wing nodes.

    Parameters
    ----------
    problem : TACSStaticProblem
        The problem to add loads to
    fea_assembler : pyTACS
        The FEA assembler
    load_factor : float
        Load factor (g's) for the maneuver case
    """
    # Get mesh info
    bdf = fea_assembler.getBDFInfo()
    node_ids = list(bdf.node_ids)

    if len(node_ids) == 0:
        print("Warning: No nodes found in mesh!")
        return

    # Get node coordinates
    Xpts = fea_assembler.getOrigNodes()
    num_nodes = len(Xpts) // 3

    # Reshape to (N, 3) array
    coords = Xpts.reshape(-1, 3)

    # Find bounding box
    x_min, x_max = coords[:, 0].min(), coords[:, 0].max()
    y_min, y_max = coords[:, 1].min(), coords[:, 1].max()
    z_min, z_max = coords[:, 2].min(), coords[:, 2].max()

    print(f"\nMesh bounding box:")
    print(f"  X: {x_min:.3f} to {x_max:.3f} m")
    print(f"  Y: {y_min:.3f} to {y_max:.3f} m")
    print(f"  Z: {z_min:.3f} to {z_max:.3f} m")

    # Compute approximate aircraft weight
    # First, get total mass
    mass_func = functions.StructuralMass(fea_assembler.assembler)
    mass = fea_assembler.assembler.evalFunctions([mass_func])[0]

    print(f"\nAircraft structural mass: {mass:.2f} kg")

    # Total lift required = weight * load_factor
    g = 9.81  # m/s^2
    weight = mass * g
    total_lift = weight * load_factor

    print(f"Design load factor: {load_factor} g")
    print(f"Total lift required: {total_lift:.2f} N")

    # Apply lift as distributed load across upper surface
    # For a flying wing, assume lift acts primarily upward (Z direction)

    # Identify "upper" nodes (above mean Z)
    z_mean = (z_min + z_max) / 2
    upper_mask = coords[:, 2] > z_mean
    upper_count = np.sum(upper_mask)

    if upper_count > 0:
        # Distribute lift across upper surface nodes
        lift_per_node = total_lift / upper_count

        # Apply as point loads
        upper_node_ids = [node_ids[i] for i in range(len(node_ids)) if upper_mask[i]]

        # Lift force per node (upward = +Z)
        lift_force = np.array([0.0, 0.0, lift_per_node, 0.0, 0.0, 0.0])

        print(f"\nApplying lift to {upper_count} upper surface nodes")
        print(f"Lift per node: {lift_per_node:.4f} N")

        # Add loads one at a time (more reliable)
        for nid in upper_node_ids:
            problem.addLoadToNodes([nid], lift_force, nastranOrdering=True)
    else:
        print("Warning: Could not identify upper surface nodes")
        # Fall back to applying load to all nodes
        lift_per_node = total_lift / num_nodes
        lift_force = np.array([0.0, 0.0, lift_per_node, 0.0, 0.0, 0.0])
        for nid in node_ids:
            problem.addLoadToNodes([nid], lift_force, nastranOrdering=True)

    return total_lift, mass


def run_analysis(bdf_file, output_dir=None):
    """
    Run inertial relief analysis on the aircraft structure.
    """
    comm = MPI.COMM_WORLD
    rank = comm.rank

    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(__file__))

    print("=" * 60)
    print("NANUQX FLYING WING - INERTIAL RELIEF ANALYSIS")
    print("=" * 60)

    # Check BDF file exists
    if not os.path.exists(bdf_file):
        print(f"Error: BDF file not found: {bdf_file}")
        return None

    print(f"\nLoading mesh: {bdf_file}")

    # Create FEA assembler
    fea_assembler = pytacs.pyTACS(bdf_file, comm)

    # Debug: check what BCs are in the BDF
    bdf_info = fea_assembler.getBDFInfo()
    print(f"\nBDF SPCs found: {list(bdf_info.spcs.keys()) if hasattr(bdf_info, 'spcs') else 'None'}")
    if hasattr(bdf_info, 'spcs'):
        for spc_id in bdf_info.spcs:
            print(f"  SPC set {spc_id}: {len(bdf_info.spcs[spc_id])} entries")
            for spc in bdf_info.spcs[spc_id]:
                print(f"    Type: {spc.type}, Nodes: {spc.nodes}, Components: {spc.components}")

    fea_assembler.initialize(elemCallBack=create_element_callback)

    # Create static problem
    problem = fea_assembler.createStaticProblem("flight_loads")

    # Add output functions
    problem.addFunction("mass", functions.StructuralMass)
    problem.addFunction("ks_vmstress", functions.KSFailure, ksWeight=100.0)

    # BCs are read from the BDF file (SPC1 cards)
    # The converter script adds minimal constraints at the geometric center

    # Apply flight loads
    print("\n--- Applying Flight Loads ---")
    total_lift, mass = apply_flight_loads(problem, fea_assembler, load_factor=2.5)

    # Apply 6-DOF inertial relief
    print("\n--- Applying Inertial Relief ---")
    try:
        relief_info = problem.applyInertialRelief(dof=6)

        print(f"\nInertial Relief Results:")
        print(f"  Total mass: {relief_info['mass']:.2f} kg")
        print(f"  CG location: [{relief_info['cg'][0]:.4f}, {relief_info['cg'][1]:.4f}, {relief_info['cg'][2]:.4f}] m")
        print(f"  Applied force sum: [{relief_info['totalForce'][0]:.2f}, {relief_info['totalForce'][1]:.2f}, {relief_info['totalForce'][2]:.2f}] N")
        print(f"  Applied moment sum: [{relief_info['totalMoment'][0]:.2f}, {relief_info['totalMoment'][1]:.2f}, {relief_info['totalMoment'][2]:.2f}] N-m")
        print(f"  Linear acceleration: [{relief_info['linearAccel'][0]:.4f}, {relief_info['linearAccel'][1]:.4f}, {relief_info['linearAccel'][2]:.4f}] m/s^2")
        print(f"  Angular acceleration: [{relief_info['angularAccel'][0]:.6f}, {relief_info['angularAccel'][1]:.6f}, {relief_info['angularAccel'][2]:.6f}] rad/s^2")

    except Exception as e:
        print(f"Warning: Inertial relief failed: {e}")
        print("Proceeding without inertial relief (results may show rigid body modes)")
        relief_info = None

    # Solve the problem
    print("\n--- Solving ---")
    problem.solve()

    # Evaluate functions
    funcs = {}
    problem.evalFunctions(funcs)

    print(f"\nFunction Values:")
    for name, value in funcs.items():
        print(f"  {name}: {value:.6e}")

    # Write solution
    output_file = os.path.join(output_dir, "nanuqx_flight_solution.f5")
    problem.writeSolution(outputDir=output_dir, baseName="nanuqx_flight")
    print(f"\nSolution written to: {output_file}")

    # Get displacement statistics
    u = problem.getVariables()
    if u is not None:
        # Handle both array and vector types
        if hasattr(u, 'getArray'):
            u_array = u.getArray()
        else:
            u_array = np.array(u)

        num_nodes = len(u_array) // 6

        # Extract displacements (first 3 DOFs per node)
        disp = u_array.reshape(-1, 6)[:, :3]
        disp_mag = np.linalg.norm(disp, axis=1)

        print(f"\nDisplacement Statistics:")
        print(f"  Max displacement: {disp_mag.max():.6f} m ({disp_mag.max()*1000:.3f} mm)")
        print(f"  Mean displacement: {disp_mag.mean():.6f} m ({disp_mag.mean()*1000:.3f} mm)")

        # Find location of max displacement
        max_idx = np.argmax(disp_mag)
        Xpts = fea_assembler.getOrigNodes().reshape(-1, 3)
        max_loc = Xpts[max_idx]
        print(f"  Max displacement at: [{max_loc[0]:.4f}, {max_loc[1]:.4f}, {max_loc[2]:.4f}] m")

    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)

    return {
        "relief_info": relief_info,
        "functions": funcs,
        "total_lift": total_lift,
        "mass": mass
    }


if __name__ == "__main__":
    # BDF file path - use largest connected component
    script_dir = os.path.dirname(os.path.abspath(__file__))
    bdf_file = os.path.join(script_dir, "nanuqx_largest_component.bdf")

    # Run analysis
    results = run_analysis(bdf_file)

    if results is None:
        print("\nAnalysis failed. Make sure the BDF mesh file exists.")
        print("Run mesh_step_files.py first to generate the mesh.")
        sys.exit(1)
