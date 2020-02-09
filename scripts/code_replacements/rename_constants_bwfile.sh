#!/bin/bash
set -x

find sbws/ -type f -exec sed -i 's/BW_KEYVALUE_SEP_V1/BWLINE_KEYVALUES_SEP_V1/g' {} \;
find sbws/ -type f -exec sed -i 's/BW_KEYVALUES_BASIC/BWLINE_KEYS_V0/g' {} \;
find sbws/ -type f -exec sed -i 's/BW_KEYVALUES_FILE/BWLINE_KEYS_V1_1/g' {} \;
find sbws/ -type f -exec sed -i 's/BW_KEYVALUES_EXTRA_BWS/BWLINE_KEYS_V1_2/g' {} \;
find sbws/ -type f -exec sed -i 's/BANDWIDTH_LINE_KEY_VALUES_MONITOR/BWLINE_KEYS_V1_4/g' {} \;
find sbws/ -type f -exec sed -i 's/BW_KEYVALUES_EXTRA/BWLINE_KEYS_V1/g' {} \;
find sbws/ -type f -exec sed -i 's/BW_KEYVALUES_INT/BWLINE_INT_KEYS/g' {} \;
find sbws/ -type f -exec sed -i 's/BW_KEYVALUES/BWLINE_ALL_KEYS/g' {} \;
find sbws/ -type f -exec sed -i 's/LINE_SEP/LINES_SEP/g' {} \;
find sbws/ -type f -exec sed -i 's/EXTRA_ARG_KEYVALUES/HEADER_KEYS_V1X/g' {} \;
find sbws/ -type f -exec sed -i 's/STATS_KEYVALUES/HEADER_KEYS_V1_2/g' {} \;
find sbws/ -type f -exec sed -i 's/BW_HEADER_KEYVALUES_RECENT_MEASUREMENTS_EXCLUDED/HEADER_RECENT_MEASUREMENTS_EXCLUDED_KEYS/g' {} \;
find sbws/ -type f -exec sed -i 's/BW_HEADER_KEYVALUES_MONITOR/HEADER_KEYS_V1_4/g' {} \;
find sbws/ -type f -exec sed -i 's/BANDWIDTH_HEADER_KEY_VALUES_INIT/HEADER_INIT_KEYS/g' {} \;
find sbws/ -type f -exec sed -i 's/KEYVALUES_INT/HEADER_INT_KEYS/g' {} \;
find sbws/ -type f -exec sed -i 's/UNORDERED_KEYVALUES/HEADER_UNORDERED_KEYS/g' {} \;
find sbws/ -type f -exec sed -i 's/ALL_KEYVALUES/HEADER_ALL_KEYS/g' {} \;
find tests/ -type f -exec sed -i 's/BW_KEYVALUE_SEP_V1/BWLINE_KEYVALUES_SEP_V1/g' {} \;
find tests/ -type f -exec sed -i 's/BW_KEYVALUES_BASIC/BWLINE_KEYS_V0/g' {} \;
find tests/ -type f -exec sed -i 's/BW_KEYVALUES_FILE/BWLINE_KEYS_V1_1/g' {} \;
find tests/ -type f -exec sed -i 's/BW_KEYVALUES_EXTRA_BWS/BWLINE_KEYS_V1_2/g' {} \;
find tests/ -type f -exec sed -i 's/BANDWIDTH_LINE_KEY_VALUES_MONITOR/BWLINE_KEYS_V1_4/g' {} \;
find tests/ -type f -exec sed -i 's/BW_KEYVALUES_EXTRA/BWLINE_KEYS_V1/g' {} \;
find tests/ -type f -exec sed -i 's/BW_KEYVALUES_INT/BWLINE_INT_KEYS/g' {} \;
find tests/ -type f -exec sed -i 's/BW_KEYVALUES/BWLINE_ALL_KEYS/g' {} \;
find tests/ -type f -exec sed -i 's/LINE_SEP/LINES_SEP/g' {} \;
find tests/ -type f -exec sed -i 's/EXTRA_ARG_KEYVALUES/HEADER_KEYS_V1X/g' {} \;
find tests/ -type f -exec sed -i 's/STATS_KEYVALUES/HEADER_KEYS_V1_2/g' {} \;
find tests/ -type f -exec sed -i 's/BW_HEADER_KEYVALUES_RECENT_MEASUREMENTS_EXCLUDED/HEADER_RECENT_MEASUREMENTS_EXCLUDED_KEYS/g' {} \;
find tests/ -type f -exec sed -i 's/BW_HEADER_KEYVALUES_MONITOR/HEADER_KEYS_V1_4/g' {} \;
find tests/ -type f -exec sed -i 's/BANDWIDTH_HEADER_KEY_VALUES_INIT/HEADER_INIT_KEYS/g' {} \;
find tests/ -type f -exec sed -i 's/KEYVALUES_INT/HEADER_INT_KEYS/g' {} \;
find tests/ -type f -exec sed -i 's/UNORDERED_KEYVALUES/HEADER_UNORDERED_KEYS/g' {} \;
find tests/ -type f -exec sed -i 's/ALL_KEYVALUES/HEADER_ALL_KEYS/g' {} \;