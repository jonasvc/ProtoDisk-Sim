"""
Module for running a single RADMC-3D simulation
Supports 'Advanced UI' (Visual Progress) and 'Raw' (Standard RADMC Output).
The Advanced option is still work in progress, so use at your own risk.
"""

import os
import sys
import shutil
import logging
import time
import subprocess
import shlex
import re
from contextlib import contextmanager
from radmc3dPy import analyze, setup, image
from terminal_ui import print_success, print_error


# ===========================================================================
# DETAILED LOGGING HELPERS
# ===========================================================================

def log_phase_start(phase_name):
    """Log the start of a phase with timestamp"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    logging.info("=" * 70)
    logging.info(f"[PHASE_START] {phase_name}")
    logging.info(f"[TIMESTAMP] {timestamp}")
    logging.info("=" * 70)
    return time.time()


def log_phase_end(phase_name, start_time):
    """Log the end of a phase with duration"""
    end_time = time.time()
    duration = end_time - start_time
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    # Format duration intelligently
    if duration < 60:
        duration_str = f"{duration:.2f} seconds"
    elif duration < 3600:
        duration_str = f"{duration/60:.2f} minutes ({duration:.1f} seconds)"
    else:
        duration_str = f"{duration/3600:.2f} hours ({duration/60:.1f} minutes)"
    
    logging.info("-" * 70)
    logging.info(f"[PHASE_END] {phase_name}")
    logging.info(f"[TIMESTAMP] {timestamp}")
    logging.info(f"[DURATION] {duration_str}")
    logging.info("-" * 70)
    logging.info("")  # Empty line for readability


def log_command(command_str, cwd=None):
    """Log a command that will be executed"""
    logging.info(f"[CMD] {command_str}")
    if cwd:
        logging.info(f"[CWD] {cwd}")
    else:
        logging.info(f"[CWD] {os.getcwd()}")

# --- OS-LEVEL SILENCER (Only for Advanced Mode) ---
@contextmanager
def suppress_output():
    """Redirects stdout/stderr to devnull at OS level."""
    with open(os.devnull, "w") as devnull:
        old_stdout = os.dup(1)
        old_stderr = os.dup(2)
        try:
            os.dup2(devnull.fileno(), 1)
            os.dup2(devnull.fileno(), 2)
            yield
        finally:
            os.dup2(old_stdout, 1)
            os.dup2(old_stderr, 2)
            os.close(old_stdout)
            os.close(old_stderr)


#########################################################################
### RAW TRACKER - Minimal UI for debugging and direct RADMC-3D output ###
#########################################################################

class RawTracker:
    """
    Dummy tracker class for Raw output mode.
    
    Purpose:
    --------
    In Raw mode, we want to see RADMC-3D's native terminal output directly
    without any filtering, parsing, or fancy UI elements. This tracker
    implements the same interface as AdvancedPhaseTracker but does nothing
    for most methods, allowing the simulation code to use the same
    API regardless of UI mode.
    
    When to use:
    ------------
    - When you want unfiltered simulation output
    
    Interface methods:
    ------------------
    All methods are none except start_phase/complete_phase which print
    simple phase markers to help orient the user in the output stream.
    """
    
    def start(self): 
        """Start tracking - no-op in raw mode"""
        pass
    
    def stop(self): 
        """Stop tracking - no-op in raw mode"""
        pass
    
    def start_phase(self, name): 
        """
        Mark the start of a simulation phase
        Prints a simple header so user knows which phase is running
        """
        print(f"\n>>> Starting Phase: {name}")
    
    def complete_phase(self, name): 
        """
        Mark the completion of a simulation phase
        Prints a simple footer to indicate phase finished
        """
        print(f">>> Completed Phase: {name}\n")
    
    def log(self, msg): 
        """
        Log messages - no-op in raw mode
        We don't log because RADMC-3D output goes directly to terminal
        """
        pass
    
    def set_phase_total(self, n): 
        """Set total steps for current phase - no-op in raw mode"""
        pass
    
    def update_progress(self, n): 
        """Update progress counter - no-op in raw mode"""
        pass
    
    def print_summary(self): 
        """Print timing summary - no-op in raw mode"""
        pass


#################################################################
### RADMC-3D COMMAND EXECUTION with dual-mode output handling ###
#################################################################

def run_radmc_command(command_str, tracker, total_photons=None):
    """
    Execute a RADMC-3D command with mode-dependent output handling.
    
    This function is the core of the dual-mode UI system. It runs RADMC-3D
    commands differently based on which tracker type is provided:
    
    RAW MODE (RawTracker):
    ----------------------
    - Streams RADMC-3D output directly to terminal (unfiltered)
    - Best for debugging or verifying correct operation
    - Uses subprocess.call() which inherits stdout/stderr
    
    ADVANCED MODE (AdvancedPhaseTracker):
    -------------------------------------
    - Captures RADMC-3D output line-by-line
    - Parses output for photon numbers ("Photon nr: 12345")
    - Updates progress bar in real-time based on photon count
    - Logs all output through the tracker (scrolls above progress bar)
    - Uses subprocess.Popen() with PIPE to capture output
    - captured output is needed because ottherwise the progress bars will "scroll" with the output
    
    Parameters:
    -----------
    command_str : str
        Full RADMC-3D command string (e.g., "radmc3d mctherm setthreads 32")
    tracker : RawTracker or AdvancedPhaseTracker
        UI tracker object that determines output handling mode
    total_photons : int or str, optional
        Expected total photon count for progress tracking
        Only used in Advanced mode to set progress bar maximum
    
    Raises:
    -------
    FileNotFoundError : If RADMC-3D executable not found
    RuntimeError : If RADMC-3D command returns non-zero exit code
    
    Technical notes:
    ----------------
    - Command string is split using shlex.split() to handle quoted args
    - In Advanced mode, stderr is redirected to stdout for unified capture
    - Progress regex matches both "Photon nr: X" and "Photon nr. X" formats.
    - Line buffering (bufsize=1) ensures real-time output processing
    """
    
    # Log the command that will be executed
    log_command(command_str)
    cmd_start_time = time.time()
    
    # Parse command string into argument list (handles quotes properly)
    cmd_args = shlex.split(command_str)
    
    # Verify RADMC-3D executable exists in system PATH
    if not shutil.which(cmd_args[0]):
        print(f"Error: Command '{cmd_args[0]}' not found!")
        logging.error(f"Command not found: {cmd_args[0]}")
        raise FileNotFoundError(f"Command not found: {cmd_args[0]}")

    ###########################################
    ### RAW MODE: Direct stream to terminal ###
    ###########################################
    
    if isinstance(tracker, RawTracker):
        """
        Raw mode execution path:
        - subprocess.call() runs command and waits for completion
        - stdout/stderr automatically go to terminal (inherited file descriptors)
        - No parsing, no capture, just pass through
        - User sees RADMC-3D output exactly as it would appear standalone
        """
        return_code = subprocess.call(cmd_args)
        
        # Log command completion
        cmd_duration = time.time() - cmd_start_time
        if cmd_duration < 60:
            duration_str = f"{cmd_duration:.2f}s"
        else:
            duration_str = f"{cmd_duration/60:.2f}min"
        
        logging.info(f"[RETURN_CODE] {return_code}")
        logging.info(f"[CMD_DURATION] {duration_str}")
        
        # Check if command succeeded
        if return_code != 0:
            logging.error(f"Command failed with return code {return_code}: {command_str}")
            raise RuntimeError(f"Command failed: {command_str}")
        return  # Exit early - nothing more to do in raw mode

    #############################################################
    ### ADVANCED MODE: Capture, parse, and update progress UI ###
    #############################################################
    
    # Set up progress bar with total photon count if provided
    if total_photons:
        try:
            # Convert to int (handles both int and string inputs like "1e6")
            safe_total = int(float(total_photons))
            tracker.set_phase_total(safe_total)
        except ValueError:
            # If parsing fails, warn user but continue (progress bar will be indeterminate)
            tracker.log(f"[yellow]Warning: Could not parse total_photons '{total_photons}'.[/yellow]")

    # Compile regex pattern to extract photon numbers from RADMC-3D output
    # Matches: "Photon nr: 12345" or "Photon nr. 12345" (case insensitive)
    # \s+ matches one or more whitespace characters
    # [:.]? matches optional colon or period
    # (\d+) captures the photon number
    photon_pattern = re.compile(r"Photon\s+nr[:.]?\s+(\d+)", re.IGNORECASE)

    # Start RADMC-3D process with output capture
    # stdout=PIPE: Capture standard output
    # stderr=STDOUT: Redirect errors to stdout (unified stream)
    # text=True: Return strings instead of bytes
    # bufsize=1: Line buffering for real-time processing
    process = subprocess.Popen(
        cmd_args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    # Process output line-by-line in real-time
    with process.stdout:
        # iter(callable, sentinel) creates iterator that calls readline() until empty string
        for line in iter(process.stdout.readline, ''):
            clean_line = line.strip()
            
            # Only process non-empty lines
            if clean_line: 
                # Send line to tracker's log (appears above progress bars)
                tracker.log(f"[dim]{clean_line}[/dim]")
                
                # If we're tracking photons, try to parse the current photon number
                if total_photons:
                    match = photon_pattern.search(clean_line)
                    if match:
                        try:
                            # Extract photon number and update progress bar
                            current_photon = int(match.group(1))
                            tracker.update_progress(current_photon)
                        except ValueError:
                            # If conversion fails, skip this line (shouldn't happen)
                            pass
    
    # Wait for process to complete and get exit code
    return_code = process.wait()
    
    # Log command completion
    cmd_duration = time.time() - cmd_start_time
    if cmd_duration < 60:
        duration_str = f"{cmd_duration:.2f}s"
    else:
        duration_str = f"{cmd_duration/60:.2f}min"
    
    logging.info(f"[RETURN_CODE] {return_code}")
    logging.info(f"[CMD_DURATION] {duration_str}")
    
    # Check if command failed
    if return_code != 0:
        # Log error through tracker (will appear in UI with formatting)
        tracker.log(f"[red bold]Process failed with code {return_code}[/red bold]")
        logging.error(f"Command failed with return code {return_code}: {command_str}")
        raise RuntimeError(f"Command failed: {command_str}")


def run_single_simulation(params, run_dir, name, timestamp, make_images=False, 
                         wavelength=2.2, threads=32, ui_mode='advanced'):
    """
    Run a single RADMC-3D simulation
    
    Parameters:
    -----------
    params : dict
        Simulation parameters
    run_dir : str
        Directory to save results
    name : str
        Run name
    timestamp : str
        Timestamp string
    make_images : bool
        Whether to compute images
    wavelength : float
        Wavelength for image computation (µm)
    threads : int
        Number of OpenMP threads
    ui_mode : str
        'advanced' or 'raw'
    """
    
    phases = ["Setup", "Configure Model", "MC Thermal", "SED Calculation"]
    if make_images:
        phases.append("Generate Image")
    phases.append("Save Files")
    
    estimates = {
        # Replaced the minutes by "none" until its correctly implemented
        "MC Thermal": None,
        "SED Calculation": None,
        "Generate Image": None
    }
    
    # Select Tracker and Silencer logic based on mode
    if ui_mode == 'advanced':
        from terminal_ui import AdvancedPhaseTracker
        tracker = AdvancedPhaseTracker(phases, estimates)
        use_silencer = True
    else:
        # Raw mode - no UI, direct output
        tracker = RawTracker()
        use_silencer = False

    tracker.start()
    start_time = time.time()
    
    try:
        ######################
        ### Phase 1: Setup ###
        ######################
        
        tracker.start_phase("Setup")
        phase_start = log_phase_start("Setup")
        logging.info("Starting RADMC-3D simulation")
        
        # For Python calls (analyze/setup/image), we use the silencer context 
        # only in Advanced mode. In Raw mode, let them print.
        if use_silencer:
            with suppress_output():
                analyze.writeDefaultParfile('ppdisk_complete')
        else:
            analyze.writeDefaultParfile('ppdisk_complete')

        log_phase_end("Setup", phase_start)
        tracker.complete_phase("Setup")
        
        ################################
        ### Phase 2: Configure Model ###
        ################################
        
        tracker.start_phase("Configure Model")
        phase_start = log_phase_start("Configure Model")
        tracker.log("Writing input files...")
        logging.info("Writing RADMC-3D input files and grid setup")
        
        dust_setup_args = {
            'xbound': params['xbound'], 'nx': params['nx'],
            'ybound': params['ybound'], 'ny': params['ny'],
            'zbound': params['zbound'], 'nz': params['nz'],
            'wbound': params['wbound'], 'nw': params['nw'],
            'rstar': params['rstar'], 'mstar': params['mstar'], 'tstar': params['tstar'],
            'istar_sphere': params['istar_sphere'],
            'mdisk': params['mdisk'], 'sig0': params['sig0'],
            'rin': params['rin'], 'rdisk': params['rdisk'],
            'hrdisk': params['hrdisk'], 'hrpivot': params['hrpivot'],
            'plsig1': params['plsig1'], 'plh': params['plh'],
            'sigma_type': params['sigma_type'],
            'hpr_prim_rout': params['hpr_prim_rout'], 'prim_rout': params['prim_rout'],
            'srim_rout': params['srim_rout'], 'srim_plsig': params['srim_plsig'],
            'dustkappa_ext': params['dustkappa'],
            'gsmax': params['gsmax'], 'gsmin': params['gsmin'],
            'mixabun': params['mixabun'],
            'nphot': params['nphot'], 'nphot_scat': params['nphot_scat'],
            'nphot_spec': params['nphot_spec'],
            'modified_random_walk': params['modified_random_walk'],
            'scattering_mode_max': params['scattering_mode_max'],
            'h_fourier_aj': params['h_fourier_aj'], 'h_fourier_bj': params['h_fourier_bj'],
            'sig_fourier_aj': params['sig_fourier_aj'], 'sig_fourier_bj': params['sig_fourier_bj'],
            'h_modulation_strength': params['h_modulation_strength'],
            'h_asymmetry_factor': params['h_asymmetry_factor'],
            'sig_asymmetry_factor': params['sig_asymmetry_factor'],
            'sig_modulation_strength': params['sig_modulation_strength'],
            'h_spiral_amp': params['h_spiral_amp'], 'sig_spiral_amp': params['sig_spiral_amp'],
            'spiral_pitch': params['spiral_pitch'], 'n_arms': params['n_arms'],
            'spiral_width_phi': params['spiral_width_phi'],
            'spiral_sharpness': params['spiral_sharpness'],
            'h_vortex_amp': params['h_vortex_amp'], 'h_vortex_phi0': params['h_vortex_phi0'],
            'h_vortex_r0': params['h_vortex_r0'], 'h_vortex_width_phi': params['h_vortex_width_phi'],
            'h_vortex_width_r': params['h_vortex_width_r'],
            'sig_vortex_amp': params['sig_vortex_amp'], 'sig_vortex_phi0': params['sig_vortex_phi0'],
            'sig_vortex_r0': params['sig_vortex_r0'], 'sig_vortex_width_phi': params['sig_vortex_width_phi'],
            'sig_vortex_width_r': params['sig_vortex_width_r'],
            'vortex_sharpness': params['vortex_sharpness'],
            'use_radial_damping': params['use_radial_damping'],
            'azimuthal_r_max': params['azimuthal_r_max'],
            'azimuthal_r_width': params['azimuthal_r_width'],
            'enable_warp': params['enable_warp'],
            'warp_amplitude': params['warp_amplitude'],
            'warp_phase': params['warp_phase'],
            'warp_mode': params['warp_mode'],
            'use_inner_edge_shadow': params['use_inner_edge_shadow'],
            'inner_edge_radius': params['inner_edge_radius'],
            'inner_edge_width': params['inner_edge_width'],
            'inner_edge_height': params['inner_edge_height'],
            'inner_edge_azimuthal': params['inner_edge_azimuthal'],
            'inner_edge_phi': params['inner_edge_phi'],
            'inner_edge_phi_width': params['inner_edge_phi_width'],
            'vertical_steepness': params['vertical_steepness'],
            'binary': True
        }

        if use_silencer:
            with suppress_output():
                setup.problemSetupDust('ppdisk_complete', **dust_setup_args)
        else:
            setup.problemSetupDust('ppdisk_complete', **dust_setup_args)
        
        with open("radmc3d.inp", "a") as f:
            f.write(f"mc_scat_maxtauabs         = {params['mc_scat_maxtauabs']}\n")
        
        log_phase_end("Configure Model", phase_start)
        tracker.complete_phase("Configure Model")

        ###########################
        ### Phase 3: MC Thermal ###
        ###########################
        
        tracker.start_phase("MC Thermal")
        phase_start = log_phase_start("MC Thermal")
        run_radmc_command(
            f'radmc3d mctherm setthreads {threads} sloppy', # WE use slopppy here, but be beware of it!
            tracker,
            total_photons=params['nphot']
        )
        log_phase_end("MC Thermal", phase_start)
        tracker.complete_phase("MC Thermal")
        
        # --- Phase 4: SED Calculation ---
        tracker.start_phase("SED Calculation")
        phase_start = log_phase_start("SED Calculation")
        run_radmc_command(
            f'radmc3d sed incl {params["incl"]} setthreads {threads} sloppy',  # WE use slopppy here, but be beware of it!
            tracker,
            total_photons=params['nphot_spec']
        )
        log_phase_end("SED Calculation", phase_start)
        tracker.complete_phase("SED Calculation")

        #######################
        ### Phase 5: Images ###
        #######################
        
        if make_images:
            tracker.start_phase("Generate Image")
            phase_start = log_phase_start("Generate Image")
            tracker.log(f"Computing image at {wavelength} µm...")
            logging.info(f"Computing image at wavelength {wavelength} µm")
            
            # Wir bauen den Befehl manuell zusammen, statt radmc3dPy zu nutzen.
            # So läuft der Output durch deinen Tracker.
            
            # Basis-Befehl
            cmd = (f"radmc3d image "
                   f"npix {params['npix']} "
                   f"incl {params['incl']} "
                   f"sizeau {params['sizeau']} "
                   f"lambda {wavelength} "
                   f"phi {params['phi']} "
                   f"setthreads {threads}")
            
            # Optionale Flags hinzufügen
            if params['nostar']:
                cmd += " nostar"
                
            # Befehl über den Tracker ausführen (Output landet im Log)
            run_radmc_command(cmd, tracker)
            
            # Danach nutzen wir wieder Python nur zum Einlesen und Speichern
            # (Das erzeugt keinen Output im Terminal)
            im = image.readImage()
            
            fits_filename = f'Img_{name}_{timestamp}.fits'
            im.writeFits(fits_filename, dpc=params['pc'])
            shutil.move(fits_filename, os.path.join(run_dir, fits_filename))
            
            import matplotlib.pyplot as plt
            png_filename = f'Image_{name}_{timestamp}.png'
            fig = plt.figure(figsize=(10, 10))
            ax = fig.add_subplot(111)
            image.plotImage(im, au=True, log=True, cmap='gist_heat', ax=ax)
            fig.savefig(png_filename, dpi=300, bbox_inches='tight')
            plt.close(fig)
            shutil.move(png_filename, os.path.join(run_dir, png_filename))
            
            log_phase_end("Generate Image", phase_start)
            tracker.complete_phase("Generate Image")
        #####################
        ### Phase 6: Save ###
        #####################
        
        tracker.start_phase("Save Files")
        phase_start = log_phase_start("Save Files")
        logging.info("Reading output files and saving to run directory")
        
        spec = analyze.readSpectrum(fname='spectrum.out')
        shutil.copy("spectrum.out", os.path.join(run_dir, f"spectrum_{timestamp}.out"))
        star = analyze.readStars()
        grid = analyze.readGrid()
        
        files_to_save = [
            ("problem_params.inp", f"problem_params_{timestamp}.inp"),
            ("radmc3d.inp", f"radmc3d_{timestamp}.inp"),
            ("amr_grid.inp", "amr_grid.inp"),
            ("dust_density.binp", "dust_density.binp"),
            ("dust_temperature.bdat", "dust_temperature.bdat")
        ]
        for src, dst in files_to_save:
            if os.path.exists(src):
                file_size = os.path.getsize(src) / (1024**2)  # Size in MB
                shutil.copy(src, os.path.join(run_dir, dst))
                logging.info(f"Saved: {src} ({file_size:.2f} MB) -> {dst}")
        
        log_phase_end("Save Files", phase_start)
        tracker.complete_phase("Save Files")
        tracker.stop()
        
        try:
            from export import log_simulation
            log_simulation(params, run_dir, name, timestamp, 
                         (time.time() - start_time) / 60, "SUCCESS")
        except Exception:
            pass
            
        tracker.print_summary()
        return spec, star, grid

    except Exception as e:
        tracker.stop()
        logging.error(f"Simulation failed: {e}")
        print_error(f"Simulation failed: {e}")
        raise e