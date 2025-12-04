"""
Module for automatic naming and categorization of simulations
"""

import os


def determine_category(params):
    """
    Determine simulation category based on active features
    
    Parameters:
    -----------
    params : dict
        Simulation parameters
        
    Returns:
    --------
    category : str
        Category name (e.g., 'baseline', 'spiral', 'vortex', etc.)
    """
    
    active_features = []
    
    # Check for spiral structures
    if params.get('h_spiral_amp', 0) > 0 or params.get('sig_spiral_amp', 0) > 0:
        n_arms = params.get('n_arms', 0)
        if n_arms > 0:
            active_features.append(f'spiral_{n_arms}arms')
        else:
            active_features.append('spiral')
    
    # Check for vortex structures
    vortex_h = params.get('h_vortex_amp', [0.0, 0.0])
    vortex_sig = params.get('sig_vortex_amp', [0.0, 0.0])
    if isinstance(vortex_h, (list, tuple)):
        has_vortex = any(v > 0 for v in vortex_h) or any(v > 0 for v in vortex_sig)
    else:
        has_vortex = vortex_h > 0 or vortex_sig > 0
    
    if has_vortex:
        active_features.append('vortex')
    
    # Check for Fourier modulation
    fourier_h_a = params.get('h_fourier_aj', [0.0] * 5)
    fourier_h_b = params.get('h_fourier_bj', [0.0] * 5)
    fourier_sig_a = params.get('sig_fourier_aj', [0.0] * 5)
    fourier_sig_b = params.get('sig_fourier_bj', [0.0] * 5)
    
    has_fourier = (any(v != 0 for v in fourier_h_a) or 
                   any(v != 0 for v in fourier_h_b) or
                   any(v != 0 for v in fourier_sig_a) or
                   any(v != 0 for v in fourier_sig_b))
    
    if has_fourier:
        active_features.append('fourier')
    
    # Check for warp
    if params.get('enable_warp', False):
        active_features.append('warp')
    
    # Check for inner edge shadow
    if params.get('use_inner_edge_shadow', False):
        active_features.append('inner_edge')
    
    # Check for radial damping
    if params.get('use_radial_damping', False):
        active_features.append('damping')
    
    # Determine category
    if len(active_features) == 0:
        return 'baseline'
    elif len(active_features) == 1:
        return active_features[0]
    else:
        # Multiple features - combine them
        return 'combined_' + '_'.join(active_features)


def generate_run_name(base_name, params, timestamp):
    """
    Generate full run name with category prefix
    
    Parameters:
    -----------
    base_name : str
        User-provided base name
    params : dict
        Simulation parameters
    timestamp : str
        Timestamp string
        
    Returns:
    --------
    full_name : str
        Full run name with category prefix
    """
    
    category = determine_category(params)
    
    # Format: category_run_timestamp_basename
    full_name = f"{category}_run_{timestamp}_{base_name}"
    
    return full_name


def generate_run_directory(base_dir, base_name, params, timestamp):
    """
    Generate full run directory path with category prefix
    
    Parameters:
    -----------
    base_dir : str
        Base directory for simulations
    base_name : str
        User-provided base name
    params : dict
        Simulation parameters
    timestamp : str
        Timestamp string
        
    Returns:
    --------
    run_dir : str
        Full path to run directory
    run_name : str
        Full run name (without path)
    """
    
    run_name = generate_run_name(base_name, params, timestamp)
    run_dir = os.path.join(base_dir, run_name)
    
    return run_dir, run_name