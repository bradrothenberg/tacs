"""
Extract the largest connected component from the aircraft mesh.
"""

import os
import numpy as np
from collections import defaultdict


def extract_largest_component(bdf_file, output_file):
    """Extract largest connected component to a new BDF."""
    nodes = {}
    elements = []
    other_cards = []

    with open(bdf_file, 'r') as f:
        for line in f:
            orig_line = line
            line = line.strip()
            if line.startswith('GRID,'):
                parts = line.split(',')
                node_id = int(parts[1])
                x = float(parts[3])
                y = float(parts[4])
                z = float(parts[5])
                nodes[node_id] = (x, y, z)

            elif line.startswith('CTRIA3,'):
                parts = line.split(',')
                elem_id = int(parts[1])
                n1 = int(parts[3])
                n2 = int(parts[4])
                n3 = int(parts[5])
                elements.append((elem_id, [n1, n2, n3]))

            elif line.startswith('$') or line.startswith('MAT1') or line.startswith('PSHELL'):
                other_cards.append(orig_line)

    print(f"Original mesh: {len(nodes)} nodes, {len(elements)} elements")

    # Build adjacency and find connected components
    node_to_elements = defaultdict(set)
    for elem_id, elem_nodes in elements:
        for n in elem_nodes:
            node_to_elements[n].add(elem_id)

    elem_set = set(e[0] for e in elements)
    elem_dict = {e[0]: e[1] for e in elements}

    elem_to_neighbors = defaultdict(set)
    for n, elems in node_to_elements.items():
        elem_list = list(elems)
        for i in range(len(elem_list)):
            for j in range(i+1, len(elem_list)):
                elem_to_neighbors[elem_list[i]].add(elem_list[j])
                elem_to_neighbors[elem_list[j]].add(elem_list[i])

    visited = set()
    components = []

    for start_elem in elem_set:
        if start_elem in visited:
            continue

        component = []
        queue = [start_elem]
        while queue:
            elem = queue.pop(0)
            if elem in visited:
                continue
            visited.add(elem)
            component.append(elem)

            for neighbor in elem_to_neighbors[elem]:
                if neighbor not in visited:
                    queue.append(neighbor)

        components.append(component)

    # Find largest component
    largest_comp = max(components, key=len)
    print(f"Largest component: {len(largest_comp)} elements")

    # Get nodes used in largest component
    used_nodes = set()
    for elem_id in largest_comp:
        used_nodes.update(elem_dict[elem_id])

    print(f"Nodes in largest component: {len(used_nodes)}")

    # Create new node numbering
    old_to_new = {}
    new_nodes = []
    for new_id, old_id in enumerate(sorted(used_nodes), 1):
        old_to_new[old_id] = new_id
        new_nodes.append((new_id, nodes[old_id]))

    # Write new BDF
    with open(output_file, 'w') as f:
        f.write("$ pyNastran : punch=True\n")
        f.write("$ Nanuqx Flying Wing - Largest Connected Component\n")
        f.write("$\n")

        # Write nodes
        f.write("$ GRID POINTS\n")
        for node_id, (x, y, z) in new_nodes:
            f.write(f"GRID,{node_id},,{x:.6e},{y:.6e},{z:.6e}\n")

        f.write("$\n")
        f.write("$ MATERIAL (Aluminum 7075-T6)\n")
        E = 71.7e9
        nu = 0.33
        rho = 2810.0
        f.write(f"MAT1,1,{E:.4e},,{nu:.2f},{rho:.1f}\n")

        f.write("$\n")
        f.write("$ SHELL PROPERTY\n")
        thickness = 0.002
        f.write(f"PSHELL,1,1,{thickness:.4f},1,,1\n")

        f.write("$\n")
        f.write("$ ELEMENTS\n")
        new_elem_id = 1
        for elem_id in sorted(largest_comp):
            elem_nodes = elem_dict[elem_id]
            n1 = old_to_new[elem_nodes[0]]
            n2 = old_to_new[elem_nodes[1]]
            n3 = old_to_new[elem_nodes[2]]
            f.write(f"CTRIA3,{new_elem_id},1,{n1},{n2},{n3}\n")
            new_elem_id += 1

        # Add minimal constraints
        # Find center node
        coords = np.array([nodes[old_id] for old_id in sorted(used_nodes)])
        center = coords.mean(axis=0)
        distances = np.linalg.norm(coords - center, axis=1)
        ref_idx = np.argmin(distances)
        ref_node = ref_idx + 1  # 1-based

        # Find far nodes
        x_dist = np.abs(coords[:, 0] - center[0])
        far_x_idx = np.argmax(x_dist)
        far_x_node = far_x_idx + 1

        y_dist = np.abs(coords[:, 1] - center[1])
        far_y_idx = np.argmax(y_dist)
        far_y_node = far_y_idx + 1

        f.write("$\n")
        f.write("$ MINIMAL CONSTRAINTS\n")
        f.write(f"SPC1,1,123456,{ref_node}\n")
        f.write(f"SPC1,1,23,{far_x_node}\n")
        f.write(f"SPC1,1,3,{far_y_node}\n")

    print(f"Written to: {output_file}")

    # Get bounds
    xs = coords[:, 0]
    ys = coords[:, 1]
    zs = coords[:, 2]
    print(f"\nBounding box:")
    print(f"  X: {xs.min():.3f} to {xs.max():.3f} m")
    print(f"  Y: {ys.min():.3f} to {ys.max():.3f} m")
    print(f"  Z: {zs.min():.3f} to {zs.max():.3f} m")


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    bdf_file = os.path.join(script_dir, "nanuqx_aircraft.bdf")
    output_file = os.path.join(script_dir, "nanuqx_largest_component.bdf")

    print("=" * 60)
    print("EXTRACTING LARGEST CONNECTED COMPONENT")
    print("=" * 60)

    extract_largest_component(bdf_file, output_file)
