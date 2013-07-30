# -*- coding: utf-8 -*-
"""
Functions for reading and writing from files.

"""
from __future__ import division
import subprocess
import os
import os.path
import time
import numpy as np
import posixpath

import core
import utils
import ranges
import targets

def build_ddscat_par(settings, target):
    '''
    Return a string with the contents of the ddscat.par file.
    
    :param settings: a :class:`core.Settings` object
    :param target: a :class:`core.Target` object
    '''

    out=''        
    out+='===Generated by ScatPy (%s)===\n' % time.asctime()

    out+='**** Preliminaries ****\n'
    out+='DOTORQ\n' if settings.CMDTRQ else 'NOTORQ\n'
    out+=settings.CMDSOL +'\n'        
    out+=settings.CMDFFT +'\n'
    out+=settings.CALPHA +'\n'
    out+=settings.CBINFLAG +'\n'
    
    out+='**** Initial Memory Allocation ****'+'\n'
    out+=settings.InitialMalloc.__str__()[1:-1]+'\n'
    
    out+=target.save_str() #Target defst goes here
    
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
    aeff = settings.scale
    aeff.first *= target.aeff
    aeff.last *= target.aeff
    out+=str(aeff)+'\n'

    out+='**** Define Incident Polarizations ****\n'
    out+=utils.complexV2str(settings.Epol)+'\n'
    out+='2\n' if settings.IORTH else '1\n'

    out+='**** Specify which output files to write ****\n'
    out+= '1\n' if settings.IWRKSC else '0\n'

    out+='**** Prescribe Target Rotations ****\n'
    out+=settings.beta.__str__()+'\n'
    out+=settings.theta.__str__()+'\n'
    out+=settings.phi.__str__()+'\n'

    out+='**** Specify first IWAV, IRAD, IORI (normally 0 0 0) ****\n'
    out+=settings.initial.__str__()[1:-1]+'\n'

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

def _parseline(line):
    """
    Process a line from the DDSCAT file.

    :param line: The input string to process
    :returns: A string with extraneous characters removed
    
    Ignores any characters after a '=' or '!'
    Removes quote characters         
    """
    
    # Strip characters after = or '!'
    pts=[]
    for c in '=!':
        if line.find(c) != -1:
            pts.append(line.find(c))
    
    if pts:
        line = line[:min(pts)]

    # Remove ' and "
    line = line.translate(None, '\'\"')    
    
    # Remove leading and trailing whitespace
    line = line.strip()

    return line


def read(folder=None, fname=None):
    """
    Reads a .par file and returns a DDscat object.
    
    """

    if folder is None:
        folder = '.'
    
    if fname is None:
        fname = 'ddscat.par'
        
    f = open(os.path.join(folder, fname), 'Ur')
    lines = [_parseline(l) for l in f.readlines()]
    f.close()

    # Process target
    directive = lines[10] 
    sh_param = tuple(map(int, lines[11].split()))
    n_mat = int(lines[12])
    material = lines[13: 12+n_mat]
    target = targets.Target(directive, sh_param, material=material)
    del lines[9 : 13+n_mat]    
    
    # Process settings
    settings = core.Settings()    
    settings.CMDTRQ = True if lines[2].upper == 'DOTORQ' else False 
    settings.CMDSOL = lines[3]
    settings.CMDFFT = lines[4]
    settings.CALPHA = lines[5]
    settings.CBINFLAG = lines[6]

    settings.InitialMalloc = np.array(map(int, lines[8].split()))
    settings.NRFLD = True if int(lines[10]) else False
    settings.NRFLD_EXT = np.array(map(float, lines[11].split()[:6]))

    settings.TOL = float(lines[13])
    settings.MXITER = int(lines[15])
    settings.GAMMA = float(lines[17])
    settings.ETASCA = float(lines[19])
    settings.wavelengths = ranges.How_Range.fromstring(lines[21])
    
    settings.NAMBIENT = float(lines[23])

    settings.scale_range = None
    
    settings.Epol = utils.str2complexV(lines[27])
    settings.IORTH = True if int(lines[28])==2 else False

    settings.IWRKSC = True if int(lines[30]) else False
    
    settings.beta = ranges.Lin_Range.fromstring(lines[32])
    settings.theta = ranges.Lin_Range.fromstring(lines[33])
    settings.phi = ranges.Lin_Range.fromstring(lines[34])

    if lines[36].find(',') != -1:
        settings.initial = map(int, lines[36].split(','))
    else:
        settings.initial = map(int, lines[36].split())

    settings.S_INDICES = map(int, lines[39].split())
    
    settings.CMDFRM = lines[41]
    n_scat= int(lines[42])
    
    if n_scat > 0:
        if isinstance(target, targets.Periodic1D):
            settings.scat_planes = [ranges.Scat_Range_1dPBC.fromstring(l) for l in lines[43:43+n_scat]]
        elif isinstance(target, targets.Periodic2D):
            settings.scat_planes = [ranges.Scat_Range_2dPBC.fromstring(l) for l in lines[43:43+n_scat]]
        else: # Assume isolated finite target
            settings.scat_planes = [ranges.Scat_Range.fromstring(l) for l in lines[43:43+n_scat]]

    return core.DDscat(folder=folder, settings=settings, target=target)

  
  
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


    
def QSub_Batchfile(fname, base_path, folders):
    '''
    Create a csh script for batch submission of many runs via qsub.
    
    This assumes that the server uses posix paths, regardless of the path
    convention on the local machine.     
    
    :param fname: the name of the batch file
    :param base_path: the path from which the folders will be resolved.
        This must be an absolute path on the server.
    :param folders: a list of folders (relative to base_path) containing
                 the submission scripts (.sge files)
    '''

    norm=posixpath.normpath
    join=posixpath.join

    with open(fname, 'wb') as f:
        f.write('#!/bin/csh\n' )
        for l in folders:
            folder=norm(join(base_path, norm(l)))
            sge_file=join(folder, 'submit.sge')
            f.write('qsub -wd %s %s \n' % (folder, sge_file))
    
    try:        
        subprocess.call(['chmod', '+x', fname])
    except (OSError):
        pass