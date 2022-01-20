#!/bin/bash -l
#SBATCH --nodes=1
#SBATCH --time=2:00:00
{{ sbatch }}
#SBATCH --job-name=mpas_analysis
#SBATCH --output=mpas_analysis.o%j
#SBATCH --error=mpas_analysis.e%j

set -e

source /lcrc/soft/climate/e3sm-unified/test_e3sm_unified_1.6.0rc4_anvil.sh

echo configs: {{ flags }} {{ config }}

{{ parallel_exec }} mpas_analysis --list
{{ parallel_exec }} mpas_analysis --plot_colormaps
{{ parallel_exec }} mpas_analysis --setup_only {{ flags }} {{ config }}
{{ parallel_exec }} mpas_analysis --purge {{ flags }} {{ config }} --verbose
{{ parallel_exec }} mpas_analysis --html_only {{ flags }} {{ config }}

chmod -R ugo+rX {{ html_base }}/{{ out_subdir }}
