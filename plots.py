"""
Module for creating plots from RADMC-3D simulation results
"""

import os
import shutil
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.pylab as plb
from radmc3dPy import analyze, natconst


def mirror_tauy(data):
    """
    Mirror tauy data across the midplane for symmetric representation. If you want
    to use radial tau=1 line, just use taux, it needs no mirroring!
    
    Parameters:
    -----------
    data : object
        Data object with tauy attribute
        
    Returns:
    --------
    tauy_symmetric : array
        Mirrored tauy array
    """
    print("Mirroring tauy for symmetric representation...")
    
    # Find midplane index (where theta is closest to pi/2)
    theta_midplane_idx = np.argmin(np.abs(data.grid.y - np.pi/2))
    
    tauy_symmetric = data.tauy.copy()
    
    for i in range(theta_midplane_idx):
        # Mirror the upper half to the lower half
        mirror_idx = 2 * theta_midplane_idx - i
        if mirror_idx < tauy_symmetric.shape[1]:
            tauy_symmetric[:, mirror_idx, :] = data.tauy[:, i, :]
    
    print("Mirroring completed")
    return tauy_symmetric


def plot_sed(spec, star, grid, pc, run_dir, name, timestamp, reference_file=None):
    """
    Plot the Spectral Energy Distribution (SED)
    
    Parameters:
    -----------
    spec : array
        Spectrum data from RADMC-3D
    star : object
        Star data from RADMC-3D
    grid : object
        Grid data from RADMC-3D
    pc : float
        Distance in parsec
    run_dir : str
        Directory to save the plot
    name : str
        Name identifier for this run
    timestamp : str
        Timestamp string for file naming
    reference_file : str, optional
        Path to reference SED file (e.g., 'ABAur_Dominik.txt')
    """
    
    plt.figure()
    plb.title(r'SED')
    plt.xscale('log')
    plt.yscale('log')
    
    # Plot reference SED if provided
    if reference_file is not None:
        data = np.loadtxt(reference_file)
        x = data[:, 0]
        y = data[:, 1]
        plt.plot(x, y, label=f'{os.path.basename(reference_file)}')
    
    # Plot disk SED
    analyze.plotSpectrum(
        a=spec,
        nufnu=True,
        micron=True,
        xlg=True,
        ylg=True,
        dpc=float(pc),
        oplot=True,
        label=r'Disk'
    )
    
    # Plot stellar contribution
    flux = star.fnustar / (pc**2)
    flux = np.reshape(flux, len(spec))
    plt.plot(grid.wav, grid.freq * flux, label='Stellar contribution')
    
    plt.xlabel(r'$\lambda$ [$\mu$m]')
    plt.ylabel(r'log $\nu F_{\nu}$ [erg.s$^{-1}$.cm$^{-2}$]')
    plt.xlim(0.1, 3000)
    plt.ylim(1e-15, 10**-6)
    plt.legend(loc='lower left')
    
    filename = f"SED_{name}_{timestamp}.png"
    plt.savefig(filename, dpi=250, bbox_inches='tight')
    shutil.move(filename, os.path.join(run_dir, filename))
    plt.close()


def plot_dust_density(data, run_dir, name, timestamp, wav=2.2):
    """
    Plot dust density contours with tau=1 surface
    
    Parameters:
    -----------
    data : object
        Data object with density and optical depth
    run_dir : str
        Directory to save the plot
    name : str
        Name identifier for this run
    timestamp : str
        Timestamp string for file naming
    wav : float
        Wavelength for optical depth calculation
    """
    
    # Mirror tauy for symmetric representation
    tauy_symmetric = mirror_tauy(data)
    
    plb.figure()
    plb.title(r'Dust density contours with $\tau=1$')
    c1 = plb.contourf(
        data.grid.x / natconst.au,
        np.pi / 2. - data.grid.y,
        np.log10(data.rhodust[:, :, 0, 0].T),
        30
    )
    plb.xlabel('r [AU]')
    plb.ylabel(r'$\pi/2-\theta$')
    plb.xscale('log')
    cb = plb.colorbar(c1)
    cb.ax.yaxis.labelpad = 20
    cb.set_label(r'$\log_{10}{\rho}$', rotation=270.)
    c2 = plb.contour(
        data.grid.x / natconst.au,
        np.pi / 2. - data.grid.y,
        tauy_symmetric[:, :, 0].T,
        [1.0],
        colors='w',
        linestyles='solid'
    )
    plb.clabel(c2, inline=1, fontsize=10, fmt='%g')
    
    filename = f"dust_density_contours_{name}_{timestamp}.png"
    plb.savefig(filename, dpi=300)
    shutil.move(filename, os.path.join(run_dir, filename))
    plb.close()


def plot_dust_temperature(data, run_dir, name, timestamp):
    """
    Plot dust temperature contours
    
    Parameters:
    -----------
    data : object
        Data object with temperature information
    run_dir : str
        Directory to save the plot
    name : str
        Name identifier for this run
    timestamp : str
        Timestamp string for file naming
    """
    
    plb.figure()
    plb.title(r'Dust temperature contours')
    c3 = plb.contourf(
        data.grid.x / natconst.au,
        np.pi / 2. - data.grid.y,
        data.dusttemp[:, :, 0, 0].T,
        30
    )
    plb.xlabel('r [AU]')
    plb.ylabel(r'$\pi/2-\theta$')
    plb.xscale('log')
    cb = plb.colorbar(c3)
    cb.set_label('T [K]', rotation=270.)
    c4 = plb.contour(
        data.grid.x / natconst.au,
        np.pi / 2. - data.grid.y,
        data.dusttemp[:, :, 0, 0].T,
        10,
        colors='k',
        linestyles='solid'
    )
    plb.clabel(c4, inline=1, fontsize=10)
    cb.ax.yaxis.labelpad = 20
    
    filename = f"dust_temperature_contours_{name}_{timestamp}.png"
    plb.savefig(filename, dpi=300)
    shutil.move(filename, os.path.join(run_dir, filename))
    plb.close()


def plot_temp_dens_combined(data, data_dens, run_dir, name, timestamp):
    """
    Plot temperature and density structure combined
    
    Parameters:
    -----------
    data : object
        Data object with temperature information
    data_dens : object
        Data object with density information
    run_dir : str
        Directory to save the plot
    name : str
        Name identifier for this run
    timestamp : str
        Timestamp string for file naming
    """
    
    plb.figure()
    plb.title(r'Temperature and density structure')
    plt.xlim(0.5, 200)
    plt.ylim(0, 0.4)
    
    c5 = plb.contourf(
        data_dens.grid.x / natconst.au,
        np.pi / 2 - data_dens.grid.y,
        np.log10(data_dens.rhodust[:, :, 0, 0].T),
        30
    )
    plb.xlabel('r [AU]')
    plb.ylabel(r'$\pi/2-\theta$')
    plb.xscale('log')
    plb.colorbar(c5, label=r'$\log_{10}(\rho)$')
    
    c_lines = plb.contour(
        data.grid.x / natconst.au,
        np.pi / 2 - data.grid.y,
        data.dusttemp[:, :, 0, 0].T,
        30,
        linestyles='solid'
    )
    plb.clabel(c_lines, inline=1, fontsize=10)
    
    filename = f"temperature_density_contours_{name}_{timestamp}.png"
    plb.savefig(filename, dpi=300)
    shutil.move(filename, os.path.join(run_dir, filename))
    plb.close()


def plot_density_zoom(data, run_dir, name, timestamp):
    """
    Plot zoomed dust density contours with tau=1 surface
    
    Parameters:
    -----------
    data : object
        Data object with density and optical depth
    run_dir : str
        Directory to save the plot
    name : str
        Name identifier for this run
    timestamp : str
        Timestamp string for file naming
    """
    
    # Mirror tauy for symmetric representation
    tauy_symmetric = mirror_tauy(data)
    
    plb.figure()
    plb.title(r'Dust density contours with $\tau=1$')
    c7 = plb.contourf(
        data.grid.x / natconst.au,
        np.pi / 2. - data.grid.y,
        np.log10(data.rhodust[:, :, 0, 0].T),
        30
    )
    plb.xlabel('r [AU]')
    plb.ylabel(r'$\pi/2-\theta$')
    plb.xscale('log')
    cb = plb.colorbar(c7)
    cb.ax.yaxis.labelpad = 20
    cb.set_label(r'$\log_{10}{\rho}$', rotation=270.)
    c8 = plb.contour(
        data.grid.x / natconst.au,
        np.pi / 2. - data.grid.y,
        tauy_symmetric[:, :, 0].T,
        [1.0],
        colors='w',
        linestyles='solid'
    )
    plb.clabel(c8, inline=1, fontsize=10, fmt='%g')
    plt.ylim(0, 0.5)
    plt.xlim(0.5,)
    
    filename = f"density_zoom_{name}_{timestamp}.png"
    plb.savefig(filename, dpi=300)
    shutil.move(filename, os.path.join(run_dir, filename))
    plb.close()


def create_all_plots(run_dir, name, timestamp, pc, wav=2.2, reference_file=None):
    """
    Create all plots for a simulation run
    
    Parameters:
    -----------
    run_dir : str
        Directory to save plots
    name : str
        Name identifier for this run
    timestamp : str
        Timestamp string for file naming
    pc : float
        Distance in parsec
    wav : float
        Wavelength for optical depth calculation
    reference_file : str, optional
        Path to reference SED file
    """
    
    # Read spectrum, star, and grid data
    spec = analyze.readSpectrum(fname='spectrum.out')
    star = analyze.readStars()
    grid = analyze.readGrid()
    
    # Plot SED
    plot_sed(spec, star, grid, pc, run_dir, name, timestamp, reference_file)
    
    # Read data for density and temperature plots
    data = analyze.readData(dtemp=True, ddens=True)
    opac = analyze.readOpac(ext=['astrosilicateoptool'])
    data.getTau(wav=wav)
    
    # Create all contour plots
    plot_dust_density(data, run_dir, name, timestamp, wav)
    plot_dust_temperature(data, run_dir, name, timestamp)
    
    # Read density data separately for combined plot
    data_dens = analyze.readData(ddens=True)
    plot_temp_dens_combined(data, data_dens, run_dir, name, timestamp)
    
    # Create zoomed density plot
    plot_density_zoom(data, run_dir, name, timestamp)