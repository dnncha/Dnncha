# Verbatim function excerpts from Tutorial/SABench.py, lines 336-386,
# upstream commit 54d4e17c6dff5eab7ad93fee2a9bd70385ac750b.
# This is not the full source blob. Imports supplied by the test harness.
def Overlap_accuracy(adata1, adata2, spatial_key):
    coords1 = adata1.obsm[spatial_key]
    coords2 = adata2.obsm[spatial_key]

    x_min = max(np.min(coords1[:, 0]), np.min(coords2[:, 0]))
    x_max = min(np.max(coords1[:, 0]), np.max(coords2[:, 0]))
    y_min = max(np.min(coords1[:, 1]), np.min(coords2[:, 1]))
    y_max = min(np.max(coords1[:, 1]), np.max(coords2[:, 1]))

    overlap_indices1 = (coords1[:, 0] >= x_min) & (coords1[:, 0] <= x_max) & \
                       (coords1[:, 1] >= y_min) & (coords1[:, 1] <= y_max)
    overlap_indices2 = (coords2[:, 0] >= x_min) & (coords2[:, 0] <= x_max) & \
                       (coords2[:, 1] >= y_min) & (coords2[:, 1] <= y_max)

    overlapping_adata1 = adata1[overlap_indices1, :]
    overlapping_adata2 = adata2[overlap_indices2, :]

    overlap_coords1 = overlapping_adata1.obsm[spatial_key]
    overlap_coords2 = overlapping_adata2.obsm[spatial_key]

    tree = cKDTree(overlap_coords1)

    distances, indices = tree.query(overlap_coords2)

    if len(indices)==0:
        accuracy=0
    else:
        # check Region
        matching_labels_count = 0
        for idx, target_idx in enumerate(indices):
            if target_idx < len(overlapping_adata1.obs) and idx < len(overlapping_adata2.obs):
                label1 = overlapping_adata1.obs['Region'][target_idx]
                label2 = overlapping_adata2.obs['Region'][idx]

                if label1 == label2:
                    matching_labels_count += 1

        accuracy = matching_labels_count / len(indices)
    return accuracy

def Average_Accuracy(method_results):
    accuracy_values=[]
    for i in range(len(method_results)-1):
        slice1 = method_results[i]
        slice2 = method_results[i+1]
        accuracy = Overlap_accuracy(slice1,slice2,'spatial')
        accuracy_values.append(accuracy)
        
      
    average_accuracy = np.average(accuracy_values)
    return average_accuracy
