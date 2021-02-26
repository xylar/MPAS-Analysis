#!/bin/bash -l

#SBATCH --partition=regular
#SBATCH -C haswell
#SBATCH --nodes=1
#SBATCH --time=3:00:00
#SBATCH --account=e3sm
#SBATCH --job-name=noEAmelt
#SBATCH --output=noEAmelt.o%j
#SBATCH --error=noEAmelt.e%j
#SBATCH -L cscratch1,SCRATCH,project

source ~/miniconda3/etc/profile.d/conda.sh
conda activate mpas-analysis
export HDF5_USE_FILE_LOCKING=FALSE

srun -N 1 -n 1 python -m mpas_analysis noEAmelt.cfg


