#!/usr/bin/env python3
"""
View and search the simulation logbook
"""

import sys
from export import view_logbook, SimulationLogbook

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "view":
            # View last N simulations
            n = int(sys.argv[2]) if len(sys.argv) > 2 else 20
            view_logbook(last_n=n)
        
        elif command == "search":
            # Search for specific parameters
            # Example: python view_logbook.py search mdisk=0.01*ms n_arms=2
            logbook = SimulationLogbook()
            criteria = {}
            for arg in sys.argv[2:]:
                if '=' in arg:
                    key, value = arg.split('=', 1)
                    # Try to convert to appropriate type
                    try:
                        value = int(value)
                    except:
                        try:
                            value = float(value)
                        except:
                            pass  # Keep as string
                    criteria[key] = value
            
            results = logbook.search(**criteria)
            if results is not None and len(results) > 0:
                print(f"\nFound {len(results)} matching simulations:")
                print(results[['Timestamp', 'Name', 'Status', 'Runtime_min', 
                              'mdisk', 'hrdisk', 'h_spiral_amp']].to_string(index=False))
            else:
                print("No matching simulations found.")
        
        elif command == "export":
            # Export to CSV
            output = sys.argv[2] if len(sys.argv) > 2 else "simulation_logbook.csv"
            logbook = SimulationLogbook()
            logbook.export_to_csv(output)
        
        elif command == "help":
            print(__doc__)
            print("\nUsage:")
            print("  python view_logbook.py view [N]           - View last N simulations (default 20)")
            print("  python view_logbook.py search key=value   - Search for specific parameters")
            print("  python view_logbook.py export [file.csv]  - Export logbook to CSV")
            print("\nExamples:")
            print("  python view_logbook.py view 50")
            print("  python view_logbook.py search mdisk=\"0.01*ms\" n_arms=2")
            print("  python view_logbook.py export my_sims.csv")
        
        else:
            print(f"Unknown command: {command}")
            print("Run 'python view_logbook.py help' for usage")
    
    else:
        # Default: show last 20
        view_logbook(last_n=20)
