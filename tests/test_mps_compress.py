from tenpy.algorithms.mps_compress import *
import numpy as np
import tenpy.linalg.np_conserved as npc
import tenpy
from tenpy.models.spins import SpinChain
import pytest

def test_mps_compress():
    # Test compression of a sum of a state with itself
    L=5
    sites=[tenpy.networks.site.SpinHalfSite() for i in range(L)]
    psi=tenpy.networks.mps.MPS.from_product_state(sites, [[1, 1] for i in range(L)], bc='finite')
    psiOrth=tenpy.networks.mps.MPS.from_product_state(sites, [[1, -1] for i in range(L)], bc='finite')
    psiSum = psi.add(psiOrth, .5, .5)
    mps_compress(psiSum, {})
    psiSum2= psiSum.add(psiSum, .5, .5)
    mps_compress(psiSum2, {})
    psiSum2.test_sanity()
    assert(np.abs(psiSum.overlap(psiSum2)-1)<1e-7)

@pytest.mark.parametrize('bc_MPS', ['finite', 'infinite'])
def test_UI(bc_MPS, g=0.5):
    # Test a time evolution against exact diagonalization for finite bc
    L=10
    dt=0.01
    if bc_MPS=='finite':
        L = 6
    model_pars = dict(L=L, Jx=0., Jy=0., Jz=-4., hx=2. * g, bc_MPS=bc_MPS, conserve=None)
    M = SpinChain(model_pars)
    state = ([[1/np.sqrt(2), -1/np.sqrt(2)]] * L)  # pointing in (-x)-direction
    psi = tenpy.networks.mps.MPS.from_product_state(M.lat.mps_sites(), state, bc=bc_MPS)
    psi.test_sanity()

    U=make_U(M.calc_H_MPO(), dt*1j, which='I')

    if bc_MPS=='finite': 
        ED=tenpy.algorithms.exact_diag.ExactDiag(M)
        ED.build_full_H_from_mpo()
        ED.full_diagonalization()
        psiED=ED.mps_to_full(psi)
        psiED/=psiED.norm()
    
        UED=ED.exp_H(dt)
        for i in range(30):
            psi=apply_mpo(psi, U, {})
            psiED=npc.tensordot(UED, psiED, ('ps*',[0]))
            assert(np.abs(npc.inner(psiED, ED.mps_to_full(psi))-1)<1e-2)

    if bc_MPS=='infinite':
        psiTEBD=psi.copy() 
        TEBD_params={'dt':dt, 'N_steps':1}
        EngTEBD=tenpy.algorithms.tebd.Engine(psiTEBD, M, TEBD_params)
        for i in range(30):
            EngTEBD.run()
            psi=apply_mpo(psi, U, {})
            print(np.abs(psi.overlap(psiTEBD)-1))
            #This test fails
            assert(np.abs(psi.overlap(psiTEBD)-1)<1e-2)

