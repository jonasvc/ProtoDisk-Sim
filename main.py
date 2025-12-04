"""
Main entry point for RADMC-3D simulations
Handles user input and coordinates single or batch runs
"""

import os
import sys
import datetime
import logging
import time
import shutil
from single_run import run_single_simulation
from plots import create_all_plots
from terminal_ui import print_banner, print_success, print_error, print_system_info, print_parameter_table


def get_user_inputs():
    ### Get user inputs for simulation configuration ###
    
    # Get run name
    name = input("Please define a name for this run: ").strip()
    if not name:
        print("Name cannot be empty. Exiting.")
        sys.exit(1)
    
    #################################
    ###  Ask for config selection ###
    #################################
    
    print("\nSelect configuration:")
    print("1 - Default (config.py)")
    print("2 - Reference configs (baseline, spiral, etc.)")
    print("3 - Custom config file")
    config_choice = input("Please choose 1, 2, or 3: ").strip()
    
    config_name = None
    if config_choice == "1":
        config_name = None
    if config_choice == "2":
        # List available reference configs
        from config_loader import REFERENCE_CONFIGS
        
        ### MAKE SURE YOU ADD YOUR CONFIGS IN CONFIG_LOADER.PY ###
        
        print("\nAvailable reference configurations:")
        for i, key in enumerate(REFERENCE_CONFIGS.keys(), start=1):
            print(f"  {i} - {key}")
        
        ref_choice = input("\nEnter configuration number: ").strip()
        
        try:
            ref_idx = int(ref_choice) - 1
            if 0 <= ref_idx < len(REFERENCE_CONFIGS):
                config_name = list(REFERENCE_CONFIGS.keys())[ref_idx]
            else:
                print("Invalid number. Please concentrate and start the simulation again.")
                sys.exit(1)
        except ValueError:
            print("Please enter a valid number. Please concentrate and start the simulation again.")
            sys.exit(1)
    
    elif config_choice == "3":
        custom_path = input("Enter path to custom config file: ").strip()
        if os.path.exists(custom_path):
            config_name = custom_path
        else:
            print(f"File not found: {custom_path}. Please check the path and start again.")
            sys.exit(1)

    ########################
    ### Ask for run mode ###
    ########################
    
    print("\nSelect run mode:")
    print("1 - Single run")
    print("2 - Batch run")
    mode_choice = input("Please choose 1 or 2: ").strip()
    
    if mode_choice == "1":
        run_mode = "single"
    elif mode_choice == "2":
        run_mode = "batch"
    else:
        print("Invalid choice. Exiting.")
        sys.exit(1)

    ##############################################
    ### Ask for UI Mode - Only two options now ###
    ##############################################

    ### Possible to do: Include simple gui ###
    
    print("\nSelect Output Mode:")
    print("1 - Advanced UI (Visual progress bars / experimental)")
    print("2 - Raw Output (Standard RADMC-3D terminal output)")
    ui_choice = input("Please choose 1 or 2: ").strip()
    
    if ui_choice == "1":
        ui_mode = "advanced"
    else:
        ui_mode = "raw" 

    ###################################
    ### Ask about image computation ###
    ###################################
    
    input_images = input("\nCompute images? (y/n): ").strip().lower()
    make_images = input_images == 'y'
    
    if make_images:
        wavelength_input = input("Wavelength to compute (in micron): ").strip()
        try:
            wavelength = float(wavelength_input) if wavelength_input else 2.2
        except ValueError:
            print("Falling back to 2.2 micron")
            wavelength = 2.2
    else:
        wavelength = 2.2
        print("Falling back to 2.2 micron")

    ###############################
    ### Ask about reference SED ###
    ###############################
    
    print("\nPlease choose a reference SED for AB Aur:")
    print("1 - ABAur_Dominik.txt")
    print("2 - ABAur_Dullemond.txt")
    print("3 - None")
    
    choice = input("Please choose 1, 2 or 3: ").strip()
    if choice == "1":
        reference_sed = "ABAur_Dominik.txt"
    elif choice == "2":
        reference_sed = "ABAur_Dullemond.txt"
    else:
        reference_sed = None

    # Returning choices    
    return {
        'name': name,
        'config_name': config_name,
        'make_images': make_images,
        'wavelength': wavelength,
        'reference_sed': reference_sed,
        'run_mode': run_mode,
        'ui_mode': ui_mode
    }

#######################
### Import PY FILES ###
#######################

def setup_run_directory(name, timestamp, base_dir="../../Simulations/Batch"):
    # Create the run-directory
    os.makedirs(base_dir, exist_ok=True)
    run_dir = os.path.join(base_dir, f"run_{timestamp}_{name}")
    os.makedirs(run_dir, exist_ok=True)
    return run_dir


def setup_logging(run_dir, name, timestamp):
    # Setup the logging
    log_file = os.path.join(run_dir, f"log_{timestamp}_{name}.txt")
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s %(levelname)s:%(message)s'
    )


def get_params_dict(config_module):
    # Extract parameters from config module
    # Returns only parameter values (filters module objects to prevent errors)
    params = {}
    for key in dir(config_module):
        if not key.startswith('__'):
            value = getattr(config_module, key)
            # Skip module imports
            if not str(type(value)).startswith("<class 'module'>"):
                params[key] = value
    return params


def run_single_mode(user_inputs, timestamp):
    # Execute a single simulation run for 1 model
    # Read the corresponding user inputs
    name = user_inputs['name']
    config_name = user_inputs['config_name']
    make_images = user_inputs['make_images']
    wavelength = user_inputs['wavelength']
    reference_sed = user_inputs['reference_sed']
    ui_mode = user_inputs['ui_mode'] 
    
    # Load configuration
    from config_loader import load_config
    if config_name:
        config = load_config(config_name)
        print(f"\nUsing configuration: {config_name}")
    else:
        import config
        # Load default if import fails
        print("\nUsing default configuration: config.py")
    
    # Get parameters from config.py
    params = get_params_dict(config)
    
    from naming import generate_run_directory, determine_category
    # Define the naming structure for run-folders
    base_dir = "../../Simulations/Batch"
    run_dir, full_run_name = generate_run_directory(base_dir, name, params, timestamp)
    category = determine_category(params)
    
    print_banner("single", name, category, timestamp) # Output the banner defined in terminal_ui.py
    print_system_info() # Print available system resources
    print_parameter_table(params, show_all=False) # Print most important configuration parameters
    
    os.makedirs(run_dir, exist_ok=True)
    setup_logging(run_dir, full_run_name, timestamp)
    
    logging.info(f"Starting single run: {full_run_name}")
    logging.info(f"Configuration: {config_name if config_name else 'default'}")
    logging.info(f"UI Mode: {ui_mode}")
    
    start_time = time.time()
    
    spec, star, grid = run_single_simulation(
        params=params,
        run_dir=run_dir,
        name=full_run_name,
        timestamp=timestamp,
        make_images=make_images,
        wavelength=wavelength,
        threads=params['threads'],
        ui_mode=ui_mode
    )
    
    # Create plots
    create_all_plots(
        run_dir=run_dir,
        name=full_run_name,
        timestamp=timestamp,
        pc=params['pc'],
        wav=wavelength,
        reference_file=reference_sed
    )
    
    # Save scripts
    if os.path.exists("main.py"):
        shutil.copy("main.py", os.path.join(run_dir, f"main_{full_run_name}_{timestamp}.py"))
    
    # Save config file (works for both default and reference configs)
    if config_name:
        # Reference or custom config
        from config_loader import REFERENCE_CONFIGS
        if config_name in REFERENCE_CONFIGS:
            config_path = os.path.join('configs', REFERENCE_CONFIGS[config_name])
        else:
            config_path = config_name
    else:
        # Default config
        config_path = "config.py"
    
    if os.path.exists(config_path):
        shutil.copy(config_path, os.path.join(run_dir, f"config_{full_run_name}_{timestamp}.py"))
    
    end_time = time.time()
    runtime = (end_time - start_time) / 60
    
    logging.info(f"Runtime: {runtime:.2f} minutes")
    
    print("\n")
    print_success(f"Simulation completed successfully in {runtime:.1f} minutes!")
    print_success(f"Results saved to: {run_dir}")
    print("\n")


def main():
    print("\n" + "="*60)
    print("RADMC-3D Simulation Suite")
    print("="*60 + "\n")
    
    user_inputs = get_user_inputs()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if user_inputs['run_mode'] == 'single':
        run_single_mode(user_inputs, timestamp)
    elif user_inputs['run_mode'] == 'batch':
        from batch_run import run_batch_mode
        run_batch_mode(user_inputs, timestamp)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()