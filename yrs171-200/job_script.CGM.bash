#!/bin/bash -l
#SBATCH --nodes=1
#SBATCH --time=2:00:00
#SBATCH --job-name=cgm
#SBATCH --output=cgm.o%j
#SBATCH --error=cgm.e%j

export OMP_NUM_THREADS=1

source ~/chrysalis/miniconda3/etc/profile.d/conda.sh
conda activate mpas_dev
export HDF5_USE_FILE_LOCKING=FALSE

srun -N 1 -n 1 mpas_analysis revisions.cfg yrs171-200/CGM.cfg --verbose

