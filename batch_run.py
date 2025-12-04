"""
Module for running batch simulations with multiple parameter combinations
Edit the param_combinations list to define your parameter grid
"""

import os
import time
import logging
import shutil
import copy
from main import setup_logging, get_params_dict
from single_run import run_single_simulation
from plots import create_all_plots
import config


############################
### NAMING CONFIGURATION ###
############################

# Set how batch run names should be formatted:
# "simple"   -> mytest_baseline_batch001
# "detailed" -> baseline_run_20231115_143022_batch001_mytest_baseline  
BATCH_NAMING_MODE = "detailed"

###############################################
### DEFINE YOUR PARAMETER COMBINATIONS HERE ###
###############################################

param_combinations = [
    # Example 1: Baseline model
    {
        "name_suffix": "baseline",
        "mdisk": "0.01*ms",
        "hrdisk": 0.117,
        "h_spiral_amp": 0.0,
        "sig_spiral_amp": 0.0,
    },
    
    # Example 2: With spiral structure
    {
        "name_suffix": "spiral_weak",
        "mdisk": "0.01*ms",
        "hrdisk": 0.117,
        "h_spiral_amp": 0.1,
        "sig_spiral_amp": 0.2,
        "n_arms": 2,
        "spiral_pitch": 1.0,
    },
    
    # Example 3: Stronger spiral
    {
        "name_suffix": "spiral_strong",
        "mdisk": "0.01*ms",
        "hrdisk": 0.117,
        "h_spiral_amp": 0.2,
        "sig_spiral_amp": 0.5,
        "n_arms": 2,
        "spiral_pitch": 1.0,
    },
    
    # Example 4: With vortex
    {
        "name_suffix": "vortex",
        "mdisk": "0.01*ms",
        "hrdisk": 0.117,
        "sig_vortex_amp": [0.5, 0.5],
        "h_vortex_amp": [0.2, 0.2],
    },
    
    # Example 5: Higher mass disk
    {
        "name_suffix": "highmass",
        "mdisk": "0.02*ms",
        "hrdisk": 0.117,
    },
    
    # Example 6: Different flaring
    {
        "name_suffix": "flared",
        "mdisk": "0.01*ms",
        "hrdisk": 0.15,
        "plh": 0.4,
    },
    
    # Add more combinations as needed...
]


########################
### HELPER FUNCTIONS ###
########################

def merge_params(base_params, override_params):
    """
    Merge base parameters with override parameters
    
    Parameters:
    -----------
    base_params : dict
        Base parameter dictionary from config
    override_params : dict
        Parameters to override
        
    Returns:
    --------
    dict with merged parameters
    """
    # Use simple dict copy instead of deepcopy to avoid module pickling issues
    merged = base_params.copy()
    
    # Don't merge the name_suffix into params
    override = {k: v for k, v in override_params.items() if k != 'name_suffix'}
    merged.update(override)
    
    return merged


def create_batch_run_directory(base_name, name_suffix, params, batch_idx, base_timestamp):
    """
    Create directory for a batch run with simplified naming
    
    Parameters:
    -----------
    base_name : str
        User-provided base name
    name_suffix : str
        Suffix from param_combinations
    params : dict
        Simulation parameters
    batch_idx : int
        Batch index (1, 2, 3, ...)
    base_timestamp : str
        Base timestamp
        
    Returns:
    --------
    run_dir : str
        Directory path
    run_name : str
        Run name
    timestamp : str
        Timestamp with batch number
    """
    
    timestamp = base_timestamp + f"_batch{batch_idx:03d}"
    
    if BATCH_NAMING_MODE == "simple":
        # Simple format: basename_suffix_batchXXX
        run_name = f"{base_name}_{name_suffix}_batch{batch_idx:03d}"
        base_dir = "../../Simulations/Batch"
        run_dir = os.path.join(base_dir, run_name)
    else:
        # Detailed format: uses naming.py with full categorization
        from naming import generate_run_directory
        combined_name = f"{base_name}_{name_suffix}"
        base_dir = "../../Simulations/Batch"
        run_dir, run_name = generate_run_directory(base_dir, combined_name, params, timestamp)
    
    return run_dir, run_name, timestamp


###########################
### BATCH RUN EXECUTION ###
###########################

def run_batch_mode(user_inputs, base_timestamp):
    """
    Execute batch runs with multiple parameter combinations
    
    Parameters:
    -----------
    user_inputs : dict
        User input configuration from main.py
    base_timestamp : str
        Base timestamp string
    """
    
    base_name = user_inputs['name']
    make_images = user_inputs['make_images']
    wavelength = user_inputs['wavelength']
    reference_sed = user_inputs['reference_sed']
    ui_mode = user_inputs['ui_mode'] 
    
    print("\n" + "="*60)
    print(f"BATCH MODE: Running {len(param_combinations)} simulations")
    print(f"Naming mode: {BATCH_NAMING_MODE}")
    print("="*60 + "\n")
    
    # Get base parameters from config
    base_params = get_params_dict()
    
    # Track overall batch timing
    batch_start_time = time.time()
    results_summary = []
    
    # Loop over all parameter combinations
    for idx, param_combo in enumerate(param_combinations, start=1):
        
        print(f"\n{'='*60}")
        print(f"Batch Progress: Simulation {idx}/{len(param_combinations)}")
        print(f"Configuration: {param_combo.get('name_suffix', 'unnamed')}")
        print(f"{'='*60}\n")
        
        # Get name suffix
        name_suffix = param_combo.get('name_suffix', f'combo_{idx}')
        
        # Merge parameters
        params = merge_params(base_params, param_combo)
        
        # Create run directory with appropriate naming
        run_dir, run_name, timestamp = create_batch_run_directory(
            base_name, name_suffix, params, idx, base_timestamp
        )
        
        # Create directory
        os.makedirs(run_dir, exist_ok=True)
        
        # Setup logging
        setup_logging(run_dir, run_name, timestamp)
        
        logging.info(f"Batch run {idx}/{len(param_combinations)}: {run_name}")
        logging.info(f"Making Images = {make_images}")
        if make_images:
            logging.info(f"Image wavelength = {wavelength} µm")
        
        # Log parameter changes
        logging.info("Modified parameters:")
        for key, value in param_combo.items():
            if key != 'name_suffix':
                logging.info(f"  {key} = {value}")
        
        # Run simulation
        run_start_time = time.time()
        
        try:
            spec, star, grid = run_single_simulation(
                params=params,
                run_dir=run_dir,
                name=run_name,
                timestamp=timestamp,
                make_images=make_images,
                wavelength=wavelength,
                threads=config.threads,
                ui_mode=ui_mode
            )
            
            # Create plots
            create_all_plots(
                run_dir=run_dir,
                name=run_name,
                timestamp=timestamp,
                pc=config.pc,
                wav=wavelength,
                reference_file=reference_sed
            )
            
            # Save configuration files
            if os.path.exists("config.py"):
                shutil.copy("config.py", os.path.join(run_dir, f"config_{run_name}_{timestamp}.py"))
            if os.path.exists("batch_run.py"):
                shutil.copy("batch_run.py", os.path.join(run_dir, f"batch_run_{run_name}_{timestamp}.py"))
            
            run_end_time = time.time()
            runtime = (run_end_time - run_start_time) / 60
            
            logging.info(f"Runtime: {runtime:.2f} minutes")
            
            results_summary.append({
                'index': idx,
                'name': run_name,
                'suffix': name_suffix,
                'runtime': runtime,
                'status': 'SUCCESS',
                'dir': run_dir
            })
            
            print(f"\n✓ Simulation {idx} completed successfully in {runtime:.2f} minutes")
            
        except Exception as e:
            run_end_time = time.time()
            runtime = (run_end_time - run_start_time) / 60
            
            error_msg = f"ERROR in simulation {idx}: {str(e)}"
            logging.error(error_msg)
            print(f"\n✗ {error_msg}")
            
            results_summary.append({
                'index': idx,
                'name': run_name,
                'suffix': name_suffix,
                'runtime': runtime,
                'status': 'FAILED',
                'error': str(e),
                'dir': run_dir
            })
    
    # Batch completion summary
    batch_end_time = time.time()
    total_runtime = (batch_end_time - batch_start_time) / 60
    
    print("\n" + "="*60)
    print("BATCH RUN COMPLETED")
    print("="*60)
    print(f"\nTotal simulations: {len(param_combinations)}")
    print(f"Successful: {sum(1 for r in results_summary if r['status'] == 'SUCCESS')}")
    print(f"Failed: {sum(1 for r in results_summary if r['status'] == 'FAILED')}")
    print(f"Total runtime: {total_runtime:.2f} minutes ({total_runtime/60:.2f} hours)")
    print("\nResults summary:")
    print("-" * 60)
    
    for result in results_summary:
        status_symbol = "✓" if result['status'] == 'SUCCESS' else "✗"
        print(f"{status_symbol} [{result['index']:2d}] {result['suffix']:20s} - "
              f"{result['runtime']:6.2f} min - {result['status']}")
        if result['status'] == 'FAILED':
            print(f"    Error: {result.get('error', 'Unknown error')}")
    
    print("-" * 60)
    
    # Save summary to file
    summary_dir = os.path.join("../../Simulations/Batch", f"batch_{base_timestamp}_{base_name}")
    os.makedirs(summary_dir, exist_ok=True)
    
    summary_file = os.path.join(summary_dir, "batch_summary.txt")
    with open(summary_file, 'w') as f:
        f.write("BATCH RUN SUMMARY\n")
        f.write("="*60 + "\n\n")
        f.write(f"Base name: {base_name}\n")
        f.write(f"Timestamp: {base_timestamp}\n")
        f.write(f"Naming mode: {BATCH_NAMING_MODE}\n")
        f.write(f"Total simulations: {len(param_combinations)}\n")
        f.write(f"Successful: {sum(1 for r in results_summary if r['status'] == 'SUCCESS')}\n")
        f.write(f"Failed: {sum(1 for r in results_summary if r['status'] == 'FAILED')}\n")
        f.write(f"Total runtime: {total_runtime:.2f} minutes ({total_runtime/60:.2f} hours)\n\n")
        f.write("Individual results:\n")
        f.write("-"*60 + "\n")
        
        for result in results_summary:
            f.write(f"\n[{result['index']:2d}] {result['name']}\n")
            f.write(f"    Suffix: {result['suffix']}\n")
            f.write(f"    Status: {result['status']}\n")
            f.write(f"    Runtime: {result['runtime']:.2f} minutes\n")
            f.write(f"    Directory: {result['dir']}\n")
            if result['status'] == 'FAILED':
                f.write(f"    Error: {result.get('error', 'Unknown error')}\n")
    
    print(f"\nBatch summary saved to: {summary_file}")
    print("="*60 + "\n")


if __name__ == "__main__":
    print("This module is meant to be called from main.py")
    print("Please run: python main.py")