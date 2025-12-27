"""
Check mesh connectivity and quality for the aircraft BDF.
"""

import os
import numpy as np
from collections import defaultdict


def check_mesh_connectivity(bdf_file):
    """Check mesh for disconnected components."""
    nodes = {}
    elements = []

    with open(bdf_file, 'r') as f:
        for line in f:
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

    print(f"Nodes: {len(nodes)}")
    print(f"Elements: {len(elements)}")

    # Build adjacency graph
    node_to_elements = defaultdict(set)
    for elem_id, elem_nodes in elements:
        for n in elem_nodes:
            node_to_elements[n].add(elem_id)

    # Check for unused nodes
    used_nodes = set()
    for elem_id, elem_nodes in elements:
        used_nodes.update(elem_nodes)

    unused_nodes = set(nodes.keys()) - used_nodes
    if unused_nodes:
        print(f"Warning: {len(unused_nodes)} unused nodes")

    # Find connected components using BFS
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

        # BFS from this element
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

    print(f"\nConnected components: {len(components)}")
    for i, comp in enumerate(components):
        # Get bounds of this component
        comp_nodes = set()
        for elem_id in comp:
            comp_nodes.update(elem_dict[elem_id])

        xs = [nodes[n][0] for n in comp_nodes if n in nodes]
        ys = [nodes[n][1] for n in comp_nodes if n in nodes]
        zs = [nodes[n][2] for n in comp_nodes if n in nodes]

        if xs:
            print(f"  Component {i+1}: {len(comp)} elements, {len(comp_nodes)} nodes")
            print(f"    X: {min(xs):.3f} to {max(xs):.3f}")
            print(f"    Y: {min(ys):.3f} to {max(ys):.3f}")
            print(f"    Z: {min(zs):.3f} to {max(zs):.3f}")

    # Check element quality - look for degenerate triangles
    print("\nElement quality check:")
    zero_area = 0
    small_area = 0
    min_area = float('inf')
    max_area = 0

    for elem_id, elem_nodes in elements:
        n1, n2, n3 = elem_nodes
        if n1 not in nodes or n2 not in nodes or n3 not in nodes:
            continue

        p1 = np.array(nodes[n1])
        p2 = np.array(nodes[n2])
        p3 = np.array(nodes[n3])

        # Compute area using cross product
        v1 = p2 - p1
        v2 = p3 - p1
        area = 0.5 * np.linalg.norm(np.cross(v1, v2))

        if area == 0:
            zero_area += 1
        elif area < 1e-10:
            small_area += 1

        min_area = min(min_area, area)
        max_area = max(max_area, area)

    print(f"  Zero area elements: {zero_area}")
    print(f"  Very small area (<1e-10): {small_area}")
    print(f"  Min area: {min_area:.6e}")
    print(f"  Max area: {max_area:.6e}")

    return len(components)


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    bdf_file = os.path.join(script_dir, "nanuqx_aircraft.bdf")

    print("=" * 60)
    print("MESH CONNECTIVITY CHECK")
    print("=" * 60)

    num_components = check_mesh_connectivity(bdf_file)

    if num_components > 1:
        print(f"\n*** WARNING: Mesh has {num_components} disconnected components! ***")
        print("This will cause the solver to fail.")
