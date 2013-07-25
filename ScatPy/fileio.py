# -*- coding: utf-8 -*-
"""
Functions for reading and writing from files.

"""
from __future__ import division
import subprocess
import os
import os.path
import time

import utils
import ranges
import targets
import posixpath

def build_ddscat_par(settings, target):
    '''
    Return a string suitable for creating a ddscat.par file.
    
    '''

    out=''        
    out+='===Generated by PyScat (%s)===\n' % time.asctime()

    out+='**** Preliminaries ****\n'
    out+='DOTORQ\n' if settings.CMDTRQ else 'NOTORQ\n'
    out+=settings.CMDSOL +'\n'        
    out+=settings.CMDFFT +'\n'
    out+=settings.CALPHA +'\n'
    out+=settings.CBINFLAG +'\n'
    
    out+='**** Initial Memory Allocation ****'+'\n'
    out+=settings.InitialMalloc.__str__()[1:-1]+'\n'
    
    out+=target.save_str()#Target def goes here
    
    out+='**** Additional Nearfield calculation? ****\n'
    out+='1\n' if settings.NRFLD else '0\n'
    out+=settings.NRFLD_EXT.__str__()[1:-1]+'\n'

    out+='**** Error Tolerance ****\n'
    out+=str(settings.TOL)+'\n'

    out+='**** maximum number of iterations allowed ****\n'
    out+=str(settings.MXITER)+'\n'
    
    out+='**** Interaction cutoff parameter for PBC calculations ****\n'
    out+=str(settings.GAMMA)+'\n'
    
    out+='**** Angular resolution for calculation of <cos>, etc. ****\n'
    out+=str(settings.ETASCA)+'\n'

    out+='**** Vacuum wavelengths (micron) ****\n'
    out+=settings.wavelengths.__str__()+'\n'

    out+='**** Refractive index of ambient medium\n'
    out+=str(settings.NAMBIENT)+'\n'
    
    out+='**** Effective Radii (micron) **** \n'
    out+=str(ranges.How_Range(target.aeff, target.aeff, 1))+'\n'

    out+='**** Define Incident Polarizations ****\n'
    out+=utils.str_complex_v(settings.Epol)+'\n'
    out+=str(settings.IORTH)+'\n'

    out+='**** Specify which output files to write ****\n'
    out+= '1\n' if settings.IWRKSC else '0\n'

    out+='**** Prescribe Target Rotations ****\n'
    out+=settings.beta.__str__()+'  = BETAMI, BETAMX, NBETA (beta=rotation around a1)\n'
    out+=settings.theta.__str__()+'  = THETMI, THETMX, NTHETA (theta=angle between a1 and k)\n'
    out+=settings.phi.__str__()+'  = PHIMIN, PHIMAX, NPHI (phi=rotation angle of a1 around k)\n'

    out+='**** Specify first IWAV, IRAD, IORI (normally 0 0 0) ****\n'
    out+=settings.first_I.__str__()[1:-1]+'\n'

    out+='**** Select Elements of S_ij Matrix to Print ****'+'\n'
    out+=str(len(settings.S_INDICES))+'\n'
    for s in settings.S_INDICES:
        out+='%d '%s
    out+='\n'
    
    out+='**** Specify Scattered Directions ****\n'
    out+=settings.CMDFRM+'\n'
    out+=str(len(settings.scat_planes))+'\n'
    for s in settings.scat_planes:
        out+=str(s)+'\n'
    out+='\n'
    
    return out


def read_Target_FROM_FILE(folder=None, fname=None, material=None):

    """
    Load a Target from File
    
    **This doesn't work**
    """

    if folder is None:
        folder='.'

    if fname is None:
        fname='shape.dat'
        
    with open(os.path.join(folder, fname), 'Ur') as f:
        l=f.readline()

        if 'FROM_FILE_Helix' in l:
            p=a.partition('(')[2].rpartition(')')[0].split()
            p=map(float, p)
            
            t=targets.Target_FROM_FILE_Helix(p[0], p[1], p[2], p[3], build=False)


    
def QSub_Batchfile(fname, base_folder, folders):
    '''
    Create a bash script for batch submission via qsub.
    
    Changes execute permissions to allow the script to be run    
    
    Arguments:
        fname: the name of the batch file
        base_folder: the path from which the folders will be resolved.
                     This must be an absolute path on the server.
        folders: a list of folders (relative to base_folder) containing
                 the submission scripts (.sge files)
    '''

    norm=posixpath.normpath
    join=posixpath.join

    with open(fname, 'wb') as f:
        f.write('#!/bin/csh\n' )
        for l in folders:
            folder=norm(join(base_folder, norm(l)))
            sge_file=join(folder, 'submit.sge')
            f.write('qsub -wd %s %s \n' % (folder, sge_file))
    
    try:        
        subprocess.call(['chmod', '+x', fname])
    except (OSError):
        pass