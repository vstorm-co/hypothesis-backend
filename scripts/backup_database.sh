#!/bin/bash

# Generate file name with current day in it
today=$(date '+%d-%m-%Y')
filename='/TODO/BACKUPS/DIRECTORY/db_'$today'.sql'

# Backup a database and save it to file
cd /TODO/PATH/TO/PROJECT/ && docker-compose -f docker-compose.production.yml exec db pg_dump -U postgres postgres > $filename
