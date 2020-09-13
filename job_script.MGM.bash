#!/bin/bash -l

#SBATCH --partition=regular
#SBATCH --qos=premium
#SBATCH -C haswell
#SBATCH --nodes=1
#SBATCH --time=4:00:00
#SBATCH --account=e3sm
#SBATCH --job-name=mpas_analysis
#SBATCH --output=mpas_analysis_mgm.o%j
#SBATCH --error=mpas_analysis_mgm.e%j
#SBATCH -L cscratch1,SCRATCH,project

export OMP_NUM_THREADS=1

source /global/cfs/cdirs/e3sm/software/anaconda_envs/load_test_e3sm_unified.sh
export HDF5_USE_FILE_LOCKING=FALSE

srun -N 1 -n 1 python -m mpas_analysis configs/polarRegions.conf B-MGM.cfg

