#!/bin/bash -l
#SBATCH --nodes=1
#SBATCH --time=1:00:00
#SBATCH --job-name=mpas_analysis
#SBATCH --output=mpas_analysis.o%j
#SBATCH --error=mpas_analysis.e%j

export OMP_NUM_THREADS=1

# alternatively, you can load your own development environment
source /home/ac.xylar/chrysalis/mambaforge/etc/profile.d/conda.sh
source /home/ac.xylar/chrysalis/mambaforge/etc/profile.d/mamba.sh
mamba activate mpas_dev
export E3SMU_MACHINE=chrysalis

export HDF5_USE_FILE_LOCKING=FALSE

# For an E3SM cryosphere run, include --polar_regions, or exclude
# this extra flag for default parameters
mpas_analysis --polar_regions --verbose shared.cfg cgm-uib-91-100.cfg

