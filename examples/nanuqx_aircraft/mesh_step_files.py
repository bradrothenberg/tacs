"""
Mesh STEP files for Nanuqx Flying Wing Aircraft
Uses Gmsh to convert STEP geometry to BDF mesh for TACS analysis.
"""

import os
import sys
import gmsh
import numpy as np


def mesh_step_to_bdf(step_files, output_bdf, mesh_size=0.01, mesh_size_min=0.005, mesh_size_max=0.05):
    """
    Mesh multiple STEP files and output a combined BDF file.

    Parameters
    ----------
    step_files : list of str
        Paths to STEP files to mesh
    output_bdf : str
        Output BDF file path
    mesh_size : float
        Target mesh element size
    mesh_size_min : float
        Minimum element size
    mesh_size_max : float
        Maximum element size
    """
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 1)
    gmsh.option.setNumber("General.Verbosity", 5)  # Moderate verbosity

    # OCC import options for faster processing
    gmsh.option.setNumber("Geometry.OCCFixDegenerated", 0)
    gmsh.option.setNumber("Geometry.OCCFixSmallEdges", 0)
    gmsh.option.setNumber("Geometry.OCCFixSmallFaces", 0)
    gmsh.option.setNumber("Geometry.OCCSewFaces", 0)
    gmsh.option.setNumber("Geometry.OCCMakeSolids", 0)
    gmsh.option.setNumber("Geometry.Tolerance", 1e-3)  # Coarser tolerance for speed
    gmsh.option.setNumber("Geometry.ToleranceBoolean", 1e-3)

    gmsh.model.add("nanuqx_aircraft")

    # Import all STEP files
    for i, step_file in enumerate(step_files):
        if not os.path.exists(step_file):
            print(f"Warning: STEP file not found: {step_file}")
            continue

        print(f"\nImporting: {os.path.basename(step_file)}")
        print("This may take a few minutes for complex geometry...")
        sys.stdout.flush()

        try:
            # Import STEP file with healing disabled for speed
            entities = gmsh.model.occ.importShapes(step_file, highestDimOnly=True)
            print(f"  Import complete, synchronizing...")
            sys.stdout.flush()
            gmsh.model.occ.synchronize()

            print(f"  Imported {len(entities)} entities")

            # Print entity breakdown
            dims = {}
            for dim, tag in entities:
                dims[dim] = dims.get(dim, 0) + 1
            print(f"  Dimensions: {dims}")

        except Exception as e:
            print(f"  Error importing {step_file}: {e}")
            continue

    # Get all entities by dimension
    all_volumes = [tag for dim, tag in gmsh.model.getEntities(3)]
    all_surfaces = [tag for dim, tag in gmsh.model.getEntities(2)]
    all_curves = [tag for dim, tag in gmsh.model.getEntities(1)]
    all_points = [tag for dim, tag in gmsh.model.getEntities(0)]

    print(f"\nEntities after import:")
    print(f"  Points (dim 0): {len(all_points)}")
    print(f"  Curves (dim 1): {len(all_curves)}")
    print(f"  Surfaces (dim 2): {len(all_surfaces)}")
    print(f"  Volumes (dim 3): {len(all_volumes)}")

    # If we only have volumes, extract their boundary surfaces
    if not all_surfaces and all_volumes:
        print("\nExtracting surfaces from volumes...")
        for vol in all_volumes:
            bounds = gmsh.model.getBoundary([(3, vol)], oriented=False, recursive=False)
            for dim, tag in bounds:
                if dim == 2 and abs(tag) not in all_surfaces:
                    all_surfaces.append(abs(tag))

    print(f"\nTotal volumes: {len(all_volumes)}")
    print(f"Total surfaces: {len(all_surfaces)}")

    if not all_surfaces:
        print("Error: No surfaces found to mesh!")
        gmsh.finalize()
        return False

    # Set mesh size - use simpler settings for shell surfaces
    gmsh.option.setNumber("Mesh.CharacteristicLengthMin", mesh_size_min)
    gmsh.option.setNumber("Mesh.CharacteristicLengthMax", mesh_size_max)

    # Very simple mesh settings for fast surface meshing
    gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
    gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)

    # Use a uniform mesh size field for speed
    gmsh.option.setNumber("Mesh.MeshSizeMin", mesh_size_min)
    gmsh.option.setNumber("Mesh.MeshSizeMax", mesh_size_max)

    # Algorithm options - Delaunay is often faster for complex geometry
    gmsh.option.setNumber("Mesh.Algorithm", 5)  # Delaunay (fast)
    gmsh.option.setNumber("Mesh.RecombineAll", 0)  # Triangles only
    gmsh.option.setNumber("Mesh.ElementOrder", 1)  # Linear elements
    gmsh.option.setNumber("Mesh.Optimize", 0)  # Skip optimization for speed
    gmsh.option.setNumber("Mesh.OptimizeNetgen", 0)
    gmsh.option.setNumber("Mesh.RandomFactor", 1e-9)  # Tiny for deterministic meshing

    print("\nGenerating 2D surface mesh on shell surfaces...")
    print("Processing surfaces one at a time for stability...")
    sys.stdout.flush()

    # Mesh surfaces one by one for better control and progress reporting
    successful_surfaces = 0
    failed_surfaces = []

    for idx, surf_tag in enumerate(all_surfaces):
        if (idx + 1) % 10 == 0 or idx == 0:
            print(f"  Meshing surface {idx + 1}/{len(all_surfaces)}...")
            sys.stdout.flush()

        try:
            gmsh.model.mesh.generate(2)
            successful_surfaces += 1
            break  # If full mesh works, we're done
        except Exception as e:
            # Try meshing just this surface
            pass

    # If individual approach didn't work, try full mesh with simpler settings
    if successful_surfaces == 0:
        print("Trying full mesh generation...")
        sys.stdout.flush()
        try:
            gmsh.model.mesh.generate(2)
        except Exception as e:
            print(f"Mesh generation failed: {e}")
            gmsh.finalize()
            return False

    # Get mesh statistics
    node_tags, node_coords, _ = gmsh.model.mesh.getNodes()
    num_nodes = len(node_tags)

    elem_types, elem_tags, elem_node_tags = gmsh.model.mesh.getElements(2)
    num_elements = sum(len(tags) for tags in elem_tags)

    print(f"\nMesh statistics:")
    print(f"  Nodes: {num_nodes}")
    print(f"  Elements: {num_elements}")

    # Export to BDF
    print(f"\nExporting to BDF: {output_bdf}")

    # Write BDF manually for better control
    write_bdf_from_gmsh(output_bdf)

    # Also save MSH for reference
    msh_file = output_bdf.replace('.bdf', '.msh')
    gmsh.write(msh_file)
    print(f"Also saved MSH file: {msh_file}")

    gmsh.finalize()

    return True


def write_bdf_from_gmsh(bdf_file):
    """Write BDF file from current Gmsh model."""

    # Get nodes
    node_tags, node_coords, _ = gmsh.model.mesh.getNodes()

    # Create node ID mapping (Gmsh tags may not be contiguous)
    node_map = {tag: i+1 for i, tag in enumerate(node_tags)}

    # Get elements
    elem_types, elem_tags_list, elem_node_tags_list = gmsh.model.mesh.getElements(2)

    with open(bdf_file, 'w') as f:
        f.write("$ pyNastran : punch=True\n")
        f.write("$ Nanuqx Flying Wing - Meshed from STEP files\n")
        f.write("$ Generated by Gmsh\n")
        f.write("$\n")

        # Write nodes
        f.write("$ GRID POINTS\n")
        for i, tag in enumerate(node_tags):
            x = node_coords[i*3]
            y = node_coords[i*3 + 1]
            z = node_coords[i*3 + 2]
            node_id = node_map[tag]
            f.write(f"GRID,{node_id},,{x:.8e},{y:.8e},{z:.8e}\n")

        f.write("$\n")
        f.write("$ MATERIAL (Aluminum 7075-T6)\n")
        E = 71.7e9  # Young's modulus (Pa)
        nu = 0.33   # Poisson's ratio
        rho = 2810  # Density (kg/m^3)
        f.write(f"MAT1,1,{E:.3e},,{nu},{rho}\n")

        f.write("$\n")
        f.write("$ SHELL PROPERTY\n")
        thickness = 0.002  # 2mm shell thickness (adjust as needed)
        f.write(f"PSHELL,1,1,{thickness},1,,1\n")

        f.write("$\n")
        f.write("$ ELEMENTS\n")

        elem_id = 1
        for elem_type, elem_tags, elem_nodes in zip(elem_types, elem_tags_list, elem_node_tags_list):

            if elem_type == 2:  # 3-node triangle
                nodes_per_elem = 3
                for i in range(len(elem_tags)):
                    n1 = node_map[elem_nodes[i*nodes_per_elem]]
                    n2 = node_map[elem_nodes[i*nodes_per_elem + 1]]
                    n3 = node_map[elem_nodes[i*nodes_per_elem + 2]]
                    f.write(f"CTRIA3,{elem_id},1,{n1},{n2},{n3}\n")
                    elem_id += 1

            elif elem_type == 3:  # 4-node quad
                nodes_per_elem = 4
                for i in range(len(elem_tags)):
                    n1 = node_map[elem_nodes[i*nodes_per_elem]]
                    n2 = node_map[elem_nodes[i*nodes_per_elem + 1]]
                    n3 = node_map[elem_nodes[i*nodes_per_elem + 2]]
                    n4 = node_map[elem_nodes[i*nodes_per_elem + 3]]
                    f.write(f"CQUAD4,{elem_id},1,{n1},{n2},{n3},{n4}\n")
                    elem_id += 1

        print(f"  Written {node_map[node_tags[-1]]} nodes and {elem_id-1} elements")


def get_mesh_bounds(bdf_file):
    """Get bounding box of mesh from BDF file."""
    x_coords = []
    y_coords = []
    z_coords = []

    with open(bdf_file, 'r') as f:
        for line in f:
            if line.startswith('GRID,'):
                parts = line.strip().split(',')
                x_coords.append(float(parts[3]))
                y_coords.append(float(parts[4]))
                z_coords.append(float(parts[5]))

    if x_coords:
        return {
            'x_min': min(x_coords), 'x_max': max(x_coords),
            'y_min': min(y_coords), 'y_max': max(y_coords),
            'z_min': min(z_coords), 'z_max': max(z_coords),
            'num_nodes': len(x_coords)
        }
    return None


if __name__ == "__main__":
    # Define STEP files - using the structure file with actual surfaces
    base_path = "/mnt/c/Users/bradrothenberg/OneDrive - nTop/OUT/parts/Group3_Test/OUT"

    step_files = [
        os.path.join(base_path, "Structure_Test1.stp"),
    ]

    # Output directory
    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_bdf = os.path.join(output_dir, "nanuqx_aircraft.bdf")

    print("=" * 60)
    print("MESHING NANUQX FLYING WING STEP FILES")
    print("=" * 60)

    # Check which files exist
    print("\nSTEP files to process:")
    for sf in step_files:
        exists = os.path.exists(sf)
        print(f"  [{'+' if exists else '-'}] {os.path.basename(sf)}")

    # Mesh with very coarse size for initial test
    # Use larger elements for faster meshing
    success = mesh_step_to_bdf(
        step_files,
        output_bdf,
        mesh_size=0.1,        # 100mm target (very coarse for speed)
        mesh_size_min=0.05,   # 50mm minimum
        mesh_size_max=0.2     # 200mm maximum
    )

    if success:
        print("\n" + "=" * 60)
        print("MESHING COMPLETE")
        print("=" * 60)

        bounds = get_mesh_bounds(output_bdf)
        if bounds:
            print(f"\nMesh bounding box:")
            print(f"  X: {bounds['x_min']:.4f} to {bounds['x_max']:.4f} m")
            print(f"  Y: {bounds['y_min']:.4f} to {bounds['y_max']:.4f} m")
            print(f"  Z: {bounds['z_min']:.4f} to {bounds['z_max']:.4f} m")
            print(f"  Nodes: {bounds['num_nodes']}")

        print(f"\nOutput BDF: {output_bdf}")
    else:
        print("\nMeshing failed!")
        sys.exit(1)
