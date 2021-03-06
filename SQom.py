#!/usr/bin/env python

import numpy as np
from phonopy import load
from phonopy.spectrum.dynamic_structure_factor import atomic_form_factor_WK1995
from phonopy.phonon.degeneracy import degenerate_sets
import matplotlib.pyplot as plt
import matplotlib.colors as colors

def get_func_AFF(f_params):
    def func(symbol, Q):
        return atomic_form_factor_WK1995(Q, f_params[symbol])
    return func

phonon = load(np.diag([2, 2, 2]),
              primitive_matrix=[[0, 0.5, 0.5],
                                [0.5, 0, 0.5],
                                [0.5, 0.5, 0]],
              unitcell_filename="POSCAR",
              force_sets_filename="FORCE_SETS",
              born_filename="BORN")
phonon.symmetrize_force_constants()

# Mesh sampling calculation is needed for Debye-Waller factor
# This must be done with is_mesh_symmetry=False and is_eigenvectors=True.
mesh = [11, 11, 11]
phonon.set_mesh(mesh,
                is_mesh_symmetry=False,
                is_eigenvectors=True)

# Path in FCC conventional basis
direction = np.array([0.5, 0.5, 0.5])
G_cubic = np.array([3, 3, 3])
n_points = 51
temperature = 30

# For constructing spectra
E = np.linspace(-5, 35, 100)
kb = 0.08617330
gamma = 0.3 #HWHM
THztomeV = 4.13567

print("# Distance from Gamma point, 4 band frequencies in meV, "
      "4 dynamic structure factors")
print("# For degenerate bands, summations are made.")
print("# Gamma point is omitted due to different number of bands.")
print("")

# With atomic form factor
print("# Running with atomic form factor")
# D. Waasmaier and A. Kirfel, Acta Cryst. A51, 416 (1995)
# f(Q) = \sum_i a_i \exp((-b_i Q^2) + c
# Q is in angstron^-1
# a1, b1, a2, b2, a3, b3, a4, b4, a5, b5, c
f_params = {'Na': [3.148690, 2.594987, 4.073989, 6.046925,
                   0.767888, 0.070139, 0.995612, 14.1226457,
                   0.968249, 0.217037, 0.045300],  # 1+
            'Cl': [1.061802, 0.144727, 7.139886, 1.171795,
                   6.524271, 19.467656, 2.355626, 60.320301,
                   35.829404, 0.000436, -34.916604]}  # 1-


func_AFF=get_func_AFF(f_params)
verbose=True

P = phonon.primitive_matrix

dsfs = []

G_prim = np.dot(G_cubic, P)

direction_prim = np.dot(direction, P)

if verbose:
    print("# %s to %s (Primitive: %s to %s)".format(G_cubic, G_cubic + direction,
             G_prim, G_prim + direction_prim))

# Remove Gamma point because number of bands is different.
qpoints = np.array([direction_prim * x
                    for x in np.arange(1, n_points) / float(n_points - 1)])

phonon.set_band_structure([qpoints])
_, distances, frequencies, _ = phonon.get_band_structure()
distances = distances[0]
frequencies = frequencies[0] * THztomeV

phonon.set_dynamic_structure_factor(
    qpoints,
    G_prim,
    temperature,
    func_atomic_form_factor=func_AFF,
    freq_min=1e-3,
    run_immediately=False)

dsf = phonon.dynamic_structure_factor
for i, S in enumerate(dsf):  # Use as iterator
    Q_cubic = np.dot(dsf.qpoints[i], np.linalg.inv(P))

    if verbose:
        f = frequencies[i]
        bi_sets = degenerate_sets(f)
        text = "%f  " % distances[i]
        text += "%f %f %f  " % tuple(Q_cubic)
        text += " ".join(["%f" % (f[bi].sum() / len(bi))
                          for bi in bi_sets])
        text += "  "
        text += " ".join(["%f" % (S[bi].sum()) for bi in bi_sets])
        print(text)

if verbose:
    print("")
    print("")

S_q_modes = np.array([line for line in dsf])
E_ = E[:, np.newaxis]
bose = 1./ (1 - np.exp(-E/(kb * temperature)) + 1j*gamma*0.01)

chi = sum(4*S_q*gamma*E_*f_q / (np.pi *((E_**2-f_q**2)**2 + 4*E_**2*gamma**2))
       for S_q, f_q in zip(S_q_modes.T, frequencies.T)
       )

I = np.abs(bose[:, np.newaxis] * chi)

fig, ax = plt.subplots()
x_axis = np.linspace(0, 1, I.shape[1])
art = ax.pcolor(x_axis, E, I,
                norm=colors.LogNorm(vmin=np.percentile(I, 5), vmax=np.percentile(I, 95)),
                cmap='inferno')
cb = plt.colorbar(art, ax=ax)

for x_axis_val, f_q in zip(x_axis, frequencies):
    for f in f_q:
        ax.plot(x_axis_val, f, 'g.', alpha=0.5)

cb.set_label('$S(Q,\omega)$')
ax.set_xlabel("{} to {}".format(G_cubic, G_cubic + direction))
ax.set_ylabel('Energy (meV)')

try:
    if __IPYTHON__:
        fig.show()
except NameError:
    fig.savefig('Sqom.pdf')
