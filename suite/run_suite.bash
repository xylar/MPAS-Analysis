#!/usr/bin/env bash

set -e

source /global/common/software/e3sm/anaconda_envs/test_e3sm_unified_1.6.0rc5_cori-haswell.sh

main_py=3.9
py=${main_py}

export HDF5_USE_FILE_LOCKING=FALSE

branch=$(git symbolic-ref --short HEAD)

machine=$(python -c "from mache import discover_machine; print(discover_machine())")

./suite/setup.py -p ${py} -r main_py${py} -b ${branch} --clean
./suite/setup.py -p ${py} -r wc_defaults -b ${branch} --no_polar_regions
./suite/setup.py -p ${py} -r no_ncclimo -b ${branch}
./suite/setup.py -p ${py} -r ctrl -b ${branch}
./suite/setup.py -p ${py} -r main_vs_ctrl -b ${branch}
./suite/setup.py -p ${py} -r no_polar_regions -b ${branch} --no_polar_regions
./suite/setup.py -p ${py} -r mesh_rename -b ${branch}
./suite/setup.py -p ${py} -r xarray_master -b ${branch} -e test_mpas_analysis_xarray_master
conda deactivate

# submit the jobs
cd ${machine}_test_suite

cd main_py${main_py}
echo main_py${main_py}
RES=$(sbatch job_script.bash)
cd ..

cd main_vs_ctrl
echo main_vs_ctrl
sbatch --dependency=afterok:${RES##* } job_script.bash
cd ..

for run in wc_defaults no_ncclimo no_polar_regions \
    mesh_rename xarray_master
do
    cd ${run}
    echo ${run}
    sbatch job_script.bash
    cd ..
done

cd ..

# only LCRC machines have a separate QU480 run
if [[ "$machine" == "anvil" || "$machine" == "chrysalis" ]]
then
   py=${main_py}
  ./suite/setup.py -p ${py} -r QU480 -b ${branch}
  cd ${machine}_test_suite/QU480
  echo QU480
  sbatch job_script.bash
  cd ../..
fi
