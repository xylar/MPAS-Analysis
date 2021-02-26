#!/bin/bash -l

#SBATCH --partition=regular
#SBATCH -C haswell
#SBATCH --nodes=1
#SBATCH --time=3:00:00
#SBATCH --account=e3sm
#SBATCH --job-name=modGM
#SBATCH --output=modGM.o%j
#SBATCH --error=modGM.e%j
#SBATCH -L cscratch1,SCRATCH,project

source ~/miniconda3/etc/profile.d/conda.sh
conda activate mpas-analysis
export HDF5_USE_FILE_LOCKING=FALSE

srun -N 1 -n 1 python -m mpas_analysis modGM.cfg


