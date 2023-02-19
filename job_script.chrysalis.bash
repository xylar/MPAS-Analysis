#!/bin/bash -l
#SBATCH --nodes=1
#SBATCH --time=2:00:00
#SBATCH --job-name=mpas_analysis
#SBATCH --output=mpas_analysis.o%j
#SBATCH --error=mpas_analysis.e%j

set -e

export OMP_NUM_THREADS=1

source ~/chrysalis/mambaforge/etc/profile.d/conda.sh
source ~/chrysalis/mambaforge/etc/profile.d/mamba.sh
mamba activate mpas_dev

export HDF5_USE_FILE_LOCKING=FALSE

mpas_analysis -m chrysalis --verbose --purge filipe.cfg 20210421_sim7_CORE_60to30E2r2.cfg

