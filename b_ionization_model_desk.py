# import for visualization

import numpy as np
from scipy.integrate import quad
import matplotlib.pyplot as plt
import copy
import sys
from z_library import *

"""  
Methods
"""

if False: # import data colapse to see statements
    # using .npy data
    # Mesh Grid in Space
    x = np.array(np.load("input_data/coordinates_x.npy", mmap_mode='r'))
    y = np.array(np.load("input_data/coordinates_y.npy", mmap_mode='r'))
    z = np.array(np.load("input_data/coordinates_z.npy", mmap_mode='r'))

    # Velocity Dispersion
    vel_disp = np.array(np.load("input_data/velocity_dispersion.npy", mmap_mode='r'))

    # this is temperature in [x,y,z]
    temp = np.array(np.load("input_data/Temperature.npy", mmap_mode='r'))

    # magnetic field in [x,y,z]
    Bx = np.array(np.load("input_data/magnetic_field_x.npy", mmap_mode='r'))
    By = np.array(np.load("input_data/magnetic_field_y.npy", mmap_mode='r'))
    Bz = np.array(np.load("input_data/magnetic_field_z.npy", mmap_mode='r'))

    # Cosmic Ray Density
    cr_den = np.array(np.load("input_data/cr_energy_density.npy", mmap_mode='r'))

    # Molecular Cloud Density
    # Ion Fraction
    ion_frac = np.array(np.load("input_data/ionization_fraction.npy", mmap_mode='r'))

gas_den = np.array(np.load("input_data/gas_number_density.npy", mmap_mode='r'))

def process_line(line):
    """
    Process a line of data containing information about a trajectory.

    Args:
        line (str): Input line containing comma-separated values.

    Returns:
        dict or None: A dictionary containing processed data if the line is valid, otherwise None.
    """
    parts = line.split(',')
    if len(parts) > 1:
        iteration = int(parts[0])
        traj_distance = float(parts[1])
        initial_position = [float(parts[2:5][0]), float(parts[2:5][1]), float(parts[2:5][2])]
        field_magnitude = float(parts[5])
        field_vector = [float(parts[6:9][0]), float(parts[6:9][1]), float(parts[6:9][2])]
        posit_index = [float(parts[9:][0]), float(parts[9:][1]), float(parts[9:][2])]

        data_dict = {
            'iteration': int(iteration),
            'trajectory (s)': traj_distance,
            'Initial Position (r0)': initial_position,
            'field magnitude': field_magnitude,
            'field vector': field_vector,
            'indexes': posit_index
        }

        return data_dict
    else:
        return None

global itera, scoord, posit, bmag

# Specify the file path
#file_path = 'critical_points.txt'
file_path = sys.argv[1]

# Displaying a message about reading from the file
with open(file_path, 'r') as file:
    lines = file.readlines()

# Process each line and create a list of dictionaries
data_list = [process_line(line) for line in lines[:] if process_line(line) is not None]

# Creating a DataFrame from the list of dictionaries
#df = pd.DataFrame(data_list)

# Extracting data into separate lists for further analysis
itera, scoord, posit, xpos, ypos, zpos, field_v, bmag, field_x, field_y, field_z, index = [], [], [], [], [], [], [], [], [], [], [], []

for iter in data_list: # Data into variables
    itera.append(iter['iteration'])
    scoord.append(iter['trajectory (s)'])
    posit.append(iter['Initial Position (r0)'])
    xpos.append(iter['Initial Position (r0)'][0])
    ypos.append(iter['Initial Position (r0)'][1])
    zpos.append(iter['Initial Position (r0)'][2])
    field_v.append(iter['field vector'])
    bmag.append(iter['field magnitude'])
    field_x.append(iter['field vector'][0])
    field_y.append(iter['field vector'][1])
    field_z.append(iter['field vector'][2])
    index.append(iter['indexes'])
print(" Data Successfully Loaded")

# Global Constants for Ionization Calculation

# Threshold parameters for the power-law distribution
global d, a, Lstar, Jstar, Estar, epsilon

# mean energy epsilon lost by a CR particle per ionization event
epsilon = 0.028837732137317718 #eV

# Fraction of energy deposited locally (1 - d)
d = 0.82

# Exponent of the power-law distribution (a = 1 - d)
a = 0.1 #1 - d

# Luminosity per unit volume for cosmic rays (eV cm^2)
Lstar = 1.4e-14

# Flux constant (eV^-1 cm^-2 s^-1 sr^-1)
C = 2.43e+15            # Proton in Low Regime (A. Ivlev 2015) https://iopscience.iop.org/article/10.1088/0004-637X/812/2/135
Enot = 500e+6
Jstar = 2.4e+15*(10e+6)**(0.1)/(Enot**2.8)

# Energy scale for cosmic rays (1 MeV = 1e+6 eV)
Estar = 1.0e+6

def PowerLaw(Eparam, E, power, const):
    """
    Power-law function to model cosmic ray distribution. (Energy Losses)

    Parameters:
    - Eparam (float): Reference energy scale.
    - E (float): Energy variable.
    - power (float): Exponent of the power-law.
    - const (float): Constant factor.

    Returns:
    - float: Computed value of the power-law function.
    """
    return const * (E / Eparam) ** (power)

def ColumnDensity(sf, mu):
    """
    Compute column density for a given pitch angle and distance traveled.

    Parameters:
    - sf (float): Final distance traveled (stopping point of simulation).
    - mu (float): Cosine of the pitch angle (0 < pitch_angle < pi).

    Returns:
    - float: Computed column density.
    """

    dColumnDensity = 0.0
    index_sf = scoord.index(sf)  # Find index corresponding to the final distance
    Bats = bmag[index_sf]  # Magnetic field strength at the stopping point
    prev_sc = scoord[0]

    for i, sc in enumerate(scoord):
        
        trunc = False
        
        if sc == sf:  # Stop simulation at the final distance
            return dColumnDensity , sc

        if i < 1:
            ds = scoord[1] - scoord[0] # of order 10e+19
        else:
            ds = scoord[i] - scoord[i-1]

        gaspos = index[i]  # Position for s in structured grid
        gasden = interpolate_scalar_field(gaspos[0], gaspos[1], gaspos[2], gas_den)  # Interpolated gas density order of 1.0^0
        Bsprime = bmag[i]
        
        try:
            bdash = Bsprime / Bats  # Ratio of magnetic field strengths
            deno = 1 - bdash * (1 - mu**2)
            if deno < 0:
                return dColumnDensity, prev_sc
            one_over = 1.0 / np.sqrt(deno)  # Reciprocal of the square root term
            dColumnDensity += gasden * one_over * ds  # Accumulate the contribution to column density
        except ZeroDivisionError:
            if dColumnDensity is None:
                dColumnDensity = 0.0
            print("Error: Division by zero. Check values of B(s')/B(s) and \mu")
            return dColumnDensity, sc
        prev_sc = sc
        
        #print("{:<10}  {:<10}  {:<10}  {:<10} {:<10}".format(gasden,bdash,mu,ds, dColumnDensity))

def Energy(E, mu, cd, d=0.82): 
    """
    Compute new energy based on the given parameters.

    Parameters:
    - Ei (float): Initial energy.
    - mu (float): Cosine of the pitch angle (0 < pitch_angle < pi).
    - s (float): Distance traveled.
    - ds (float): Step size for distance.
    - cd (float): Column density up to s
    - d (float): Constant parameter (default value: 0.82).

    Returns:
    - float: New energy calculated based on the given parameters.
    """
    try:
        # Calculate the new energy using the given formula
        Ei = (E**(1 + d) + (1 + d) * Lstar * cd * Estar**(d))**(1 / (1 + d))

    except Exception as e:
        # Catch forbiden values in Ei expression
        print("Error:", e)
        exit()

    return Ei

def Jcurr(Ei, E, cd):
    """
    Calculate current J(E, mu, s) based on given parameters.

    Parameters:
    - Ei (float): Lower bound initial energy. E_exp
    - E (float): Integration variable.
    - mu (float): Pitch angle cosine.
    - s (float): Upper bound for distance integration (lower bound is 0.0).
    - ds (float): Distance between consecutive points [s, s + ds].

    Returns:
    - list: Three approximations of J(E, mu, s) based on different cases.
    """
    try:

        # Calculate Jcurr using the PowerLaw function
        Jcurr = PowerLaw(Estar, Ei, a, Jstar) * PowerLaw(Estar, Ei, -d, Lstar) / PowerLaw(Estar, E, -d, Lstar)

    except Exception as e:
        Jcurr = 0.0
        print("Error:", e)
        print("Jcurr() has issues")
        exit()

    return Jcurr, PowerLaw(Estar, Ei, a, Jstar)

""" Ionization Calculation

- [x] Integrate over the trajectory to obtain column density
- [ ] Integrate over all posible energies E in \[1 MeV, 1GeV\]
- [ ] Integrate over all posible values of pitch angle d(cos(alpha_i)) with alpha_i in \[0, pi\]
- [ ] Add all three CR populations
"""

def Ionization(reverse, mirror=False):
    with open(f"b_output_data/io_data.txt", "w") as io_data: #tests
        # precision of simulation depends on data characteristics
        data_size = 10e+3

        import copy

        pockets, globalmaxinfo = pocket_finder(bmag)
        print(pockets)

        globalmax_index = globalmaxinfo[0]
        globalmax_field = globalmaxinfo[1]

        # in the case of mirroring we'll have $\mu_i < \mu <\mu_{i+1}$ between the ith-pocket 
        def calculate_mu(B_i):
            return ((1 - B_i / globalmax_field) ** 0.5)        

        io_scoord = copy.copy(scoord)

        if reverse: # if mirror is True this will be skipped
            io_scoord = reversed(io_scoord[1:globalmax_index]) # backward mirrored particles
        elif mirror == False:
            io_scoord = io_scoord[1:globalmax_index]

        # Forward moving particles (-1 < \mu < \mu_h) where \mu_h is at the lowest peak 
        ionization_pop = 0.0
        
        # 1.60218e-6 ergs (1 MeV = 1.0e+6 eV)
        Ei = 1.0e+3 # eV
        Ef = 1.0e+9
        
        # ten thousand of precision to try
        dE  = ( Ef - Ei ) / data_size

        # 0.0 < pitch < np.pi/2 da = np.pi/(2*data_size)
        dmu = 1 / (data_size)

        if mirror:
            mu_pockets = []
            a = [pockets[i][1] for i in range(len(pockets))]

            for i in range(len(a) - 1):
                if a[i] != max(a[i], a[i + 1]):
                    mu_pockets.append((a[i], a[i + 1]))
            mu = []        
            for group in mu_pockets: # d = (b-a)/N => N= d/(b-a)
                start = group[0]
                end   = group[1]
                N = dmu / abs(end -start) 
                for j in range(int(N)):
                    curr = start + j*dmu  
                    mu.append(curr)      
        else:
            
            da = np.pi / (2*data_size)
            ang = np.array([ da * j for j in range(int(data_size)) ])
            mu = np.cos(ang)    

        print("Initial Conditions")
        print(("Size", "Init Energy (eV)", "Energy Diff (eV)", "Pitch A. Diff", "\mu Diff"), "\n")
        print(data_size, Ei, dE, da, "\n")
        
        ColumnH2       = [0.0]
        Ionization     = [0.0]
        EnergiesLog    = [0.0]
        Energies       = [0.0]
        for mui in reversed(mu):   
            
            cd, s_trunc = 0.0, float("inf")#ColumnDensity(io_scoord[-1], mui)

            if cd == cd: # tests if cd = Nan
                continue
            
            ColumnH2.append(cd)

            print(ionization_pop,cd, mui, (1/epsilon),J,dmu,dE)
            
            Evar           = Ei
            Spectrum       = []
            Spectrumi      = []
            
            print("Ionization (s): ", ionization_pop, "Column Density: ", cd) 

            for k, sc in enumerate(io_scoord): # forward

                #print("{:<10} {:<10} {:<10} {:<10}".format(Ei, E, k, dE))            

                if sc > io_scoord[globalmax_index] or sc > s_trunc: # stop calculation at s final point
                    break

                # E in 1 MeV => 1 GeV
                Evar = Ei + k*dE

                # E_exp = Ei^(1+d) = E^(1+d) + L_(1+d) N E_^d   
                E_exp = Energy(Evar, mui, cd, d) 

                # Current for J_+(E, mu, s)
                J, _ = Jcurr(E_exp, Evar, cd)
                J_i  = PowerLaw(Estar, Evar, a, Jstar)
                
                # Current using model
                Spectrum.append(np.log10(J))    
                Spectrumi.append(np.log10(J_i))    

                # Log10 (E / ev)
                EnergiesLog.append(np.log10(Evar))  
                Energies.append(Evar)  
                
                try:
                    ionization_pop += (1/epsilon)*J*dmu*dE           
                except Exception as e:
                    print(e)
                    print("JSpectrum() has issues")
            
        Ionization.append(np.log10(ionization_pop)) # Ionization for that Column Density for that population
        io_data.write(f"{Ionization[-1]}, {ColumnH2[-1]}, {EnergiesLog[-1]}, {Energies[-1]}\n") 

        print("Resulting Ionization: ", ionization_pop)       
        
    return (Ionization, ColumnH2, EnergiesLog, Energies) 

# Choose a test case for the streamline coordinate

#ionization inputs are sf,

# Test Ionization function and print the result
# ionization_result = Ionization(sf, 0)

# Calculating different Populations

# Forward moving particles (-1 < \mu < \mu_l) where \mu_h is at the lowest peak $\mu_l = \sqrt{1-B(s)/B_l}$
forward_ionization = Ionization(reverse = False)

# Backward moving particles (-1 < \mu < \mu_h) where \mu_h is at the highest peak $\mu_h = \sqrt{1-B(s)/B_h}$
# backward_ionization = Ionization(reverse = True)

# such that s_h and s_l form a pocket

# Mirrored particles (\mu_l < \mu < \mu_h)
# mirrored_ionization = Ionization(sf, mirror=True)

logIonization = forward_ionization[0] # Current using model
ColumnH    = forward_ionization[1] # 
LogEnergies= forward_ionization[2] # 
Energies   = forward_ionization[3] # 

# Save data in files
print(len(logIonization))
print(len(ColumnH))
print(len(LogEnergies))
print(len(Energies))

logscoord  = [np.log10(s) for s in scoord[1:]]

# Create a 1x3 subplot grid
fig, axs   = plt.subplots(2, 1, figsize=(8, 15))

# Scatter plot for Case Zero
axs[0].plot(ColumnH, logIonization, label='$log_{10}(J(E) Energy Spectrum$', linestyle='--', color='blue')
axs[1].plot(LogEnergies,  logIonization, label='$log_{10}(J_i(E_i)) $', linestyle='--', color='black')

axs[0].set_ylabel('$log_{10}(X \ eV^-1 cm^-2 s^-1 sr^-1) )  $')
axs[1].set_ylabel('$log_{10}(E_i(E) \ eV) ) $')

axs[0].set_xlabel('$s-coordinate (cm)$')
axs[1].set_xlabel('$E \ eV$')

# Add legends to each subplot
axs[0].legend()
axs[1].legend()

# Adjust layout for better spacing
#plt.tight_layout()

# Save Figure
plt.savefig("IonizationVSColumnDensity.pdf")

# Display the plot
plt.show()