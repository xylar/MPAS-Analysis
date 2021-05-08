#!/bin/bash -l

#SBATCH --qos=premium
#SBATCH -C haswell
#SBATCH --nodes=1
#SBATCH --time=4:00:00
#SBATCH --account=m3412
#SBATCH --job-name=mpas_analysis
#SBATCH --output=mpas_analysis_cgm.o%j
#SBATCH --error=mpas_analysis_cgm.e%j
#SBATCH -L cscratch1,SCRATCH,project

export OMP_NUM_THREADS=1

source ~/miniconda3/etc/profile.d/conda.sh
conda activate mpas_dev
export HDF5_USE_FILE_LOCKING=FALSE

srun -N 1 -n 1 mpas_analysis revisions.cfg yrs21-50/CGM.cfg

