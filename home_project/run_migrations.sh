#!/bin/bash

export DATABASE_URL="postgresql://moderation_user:moderation_password@localhost:5432/moderation_db"

pgmigrate migrate \
    --migrations-dir migrations \
    --connection-string "$DATABASE_URL"
