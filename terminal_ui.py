"""
Terminal UI module for RADMC-3D simulations
Includes basic helper functions and advanced progress tracking
"""

import os
import time
import psutil
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich import box

console = Console()


# ===========================================================================
# BASIC UI FUNCTIONS (Banner, Messages, Tables)
# ===========================================================================

def print_banner(mode, name, category, timestamp):
    """Print fancy banner at start"""
    banner_text = """
[bold cyan]╔══════════════════════════════════════════════════════════╗
║          RADMC-3D Simulation Pipeline v1.0               ║
║          Protoplanetary Disk Modeling                    ║
╚══════════════════════════════════════════════════════════╝[/bold cyan]
"""
    console.print(banner_text)
    
    # Run info table
    info_table = Table(show_header=False, box=None, padding=(0, 2))
    info_table.add_column(style="cyan")
    info_table.add_column(style="white")
    
    info_table.add_row("Mode:", mode.upper())
    info_table.add_row("Name:", name)
    info_table.add_row("Category:", f"[bold]{category}[/bold]")
    info_table.add_row("Timestamp:", timestamp)
    info_table.add_row("Started:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    console.print(info_table)
    console.print()


def print_success(message):
    """Print success message with checkmark in bright neon green"""
    console.print(f"[bold bright_green]✓[/bold bright_green] [bright_green]{message}[/bright_green]")


def print_warning(message):
    """Print warning message"""
    console.print(f"[yellow]⚠[/yellow] {message}")


def print_error(message):
    """Print error message"""
    console.print(f"[red]✗[/red] {message}")


def print_info(message):
    """Print info message"""
    console.print(f"[cyan]→[/cyan] {message}")


def print_separator():
    """Print separator line"""
    console.print("[dim]" + "─" * 60 + "[/dim]")


def print_parameter_table(params, show_all=False):
    """Print parameter table"""
    key_params = [
        'mdisk', 'hrdisk', 'plh', 'tstar', 'incl', 
        'h_spiral_amp', 'sig_spiral_amp', 'n_arms',
        'nphot', 'nphot_spec', 'threads'
    ]
    
    table = Table(title="Key Parameters", box=box.ROUNDED)
    table.add_column("Parameter", style="cyan")
    table.add_column("Value", style="white")
    
    if show_all:
        for key, value in params.items():
            table.add_row(key, str(value))
    else:
        for key in key_params:
            if key in params:
                table.add_row(key, str(params[key]))
    
    console.print(table)
    console.print()


def print_system_info():
    """Print system information"""
    
    table = Table(title="System Information", box=box.ROUNDED, show_header=False)
    table.add_column(style="cyan")
    table.add_column(style="white")
    
    cpu_count = os.cpu_count()
    table.add_row("CPU Threads", str(cpu_count))
    
    mem = psutil.virtual_memory()
    mem_total_gb = mem.total / (1024**3)
    mem_avail_gb = mem.available / (1024**3)
    table.add_row("RAM Available", f"{mem_avail_gb:.1f} GB / {mem_total_gb:.1f} GB")
    
    disk = psutil.disk_usage('.')
    disk_free_gb = disk.free / (1024**3)
    table.add_row("Disk Free", f"{disk_free_gb:.1f} GB")
    
    console.print(table)
    console.print()


# ===========================================================================
# ADVANCED PROGRESS TRACKER
# ===========================================================================

class AdvancedPhaseTracker:
    """
    Advanced phase tracker with progress bars and real-time updates.
    Logs scroll naturally up, Progress bars stick to bottom.
    """
    
    def __init__(self, phases, estimated_times=None, max_log_lines=12):
        """
        Initialize the advanced phase tracker
        
        Parameters:
        -----------
        phases : list
            List of phase names
        estimated_times : dict
            Dictionary mapping phase names to estimated durations (minutes)
        max_log_lines : int
            Maximum number of log lines (unused, kept for compatibility)
        """
        self.phases = phases
        self.estimated_times = estimated_times or {}
        self.current_phase_idx = -1
        self.start_time = time.time()
        self.phase_start_time = None
        self.phase_times = {}
        
        # Standard Progress Bar (transient=False -> bars remain visible)
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("{task.completed}/{task.total}"), 
            TimeElapsedColumn(),
            console=console,
            transient=False 
        )
        
        self.overall_task = self.progress.add_task("Total", total=len(phases))
        self.phase_task = self.progress.add_task("Waiting...", total=None, visible=False)

    def start(self):
        """Start the progress tracker"""
        self.progress.start()

    def stop(self):
        """Stop the progress tracker"""
        self.progress.stop()

    def log(self, message):
        """
        Prints messages ABOVE the progress bar.
        Text scrolls naturally upward.
        """
        # Escape square brackets if they appear without closing brackets
        if "[" in message and "]" not in message:
            message = message.replace("[", "\\[")
            
        # Print without dim - let RADMC output be readable
        self.progress.console.print(f"  {message}")

    def set_phase_total(self, total_steps):
        """Sets maximum for current phase (e.g., total photons)"""
        self.progress.update(self.phase_task, total=total_steps, completed=0)

    def update_progress(self, step):
        """Updates current progress value (e.g., current photon number)"""
        self.progress.update(self.phase_task, completed=step)

    def start_phase(self, phase_name):
        """Start a new phase"""
        self.current_phase_idx = self.phases.index(phase_name)
        self.phase_start_time = time.time()
        
        self.progress.update(self.overall_task, completed=self.current_phase_idx)
        
        estimated = self.estimated_times.get(phase_name)
        desc = f"[yellow]{phase_name}[/yellow]"
        if estimated:
            desc += f" (~{estimated} min)"
            
        # Reset task to "indeterminate" (spinner) until set_phase_total is called
        self.progress.reset(self.phase_task)
        self.progress.update(self.phase_task, description=desc, total=None, visible=True)
        
        self.log(f"[bold bright_green]→[/bold bright_green] Starting: [bold bright_green]{phase_name}[/bold bright_green]")

    def complete_phase(self, phase_name):
        """Complete current phase"""
        if self.phase_start_time:
            duration = time.time() - self.phase_start_time
            self.phase_times[phase_name] = duration
            duration_str = f"{int(duration)}s"
            self.log(f"[bold bright_green]✓[/bold bright_green] Done: [bold]{phase_name}[/bold] [bright_green]({duration_str})[/bright_green]")
        
        self.progress.update(self.overall_task, completed=self.current_phase_idx + 1)
        self.progress.update(self.phase_task, completed=100)

    def get_total_time(self):
        """Get total elapsed time in seconds"""
        return time.time() - self.start_time

    def print_summary(self):
        """Print a summary table of phase times"""
        console.print("\n[bold]Summary:[/bold]")
        table = Table(box=None, show_header=False)
        table.add_column(style="cyan")
        table.add_column(style="white")
        
        for phase in self.phases:
            d = self.phase_times.get(phase, 0)
            if phase in self.phase_times:
                table.add_row(phase, f"{d:.1f}s")
            else:
                table.add_row(phase, "skipped")
                
        console.print(table)