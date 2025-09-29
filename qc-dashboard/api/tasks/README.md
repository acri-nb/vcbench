# process_run.py
Contains all functionality for optional processing with hap.py, Truvari and necessary reformating. Script can be ran directly or included as a module with run_pipeline function.

# upload_run.py
Contains all functionality for locating a .zip file in a preset temporary directory, decompressing the file and moving to a preset lab runs directory.

# parsers.py
Contains parsers required by process_run.py. Also currently used by frontend, but it should probably be modified so the frontend does not directly call backend functions.

# utils.py
Contains utility functions for process_run.py

# reformat_csv.csv
Configuration for parsers to determine which columns to delete or name. Reformats csv to be able to read as a list of dicts.