#!/bin/sh
# Runs the backup at 02:30 every night, and every hour tries again if the last success is older than 26 hours
# (for example Google Drive could not be reached). Times are Asia/Kolkata.
set -eu
ln -sf "/usr/share/zoneinfo/${TZ:-Asia/Kolkata}" /etc/localtime
cat > /etc/crontabs/root <<CRON
30 2 * * * /usr/local/bin/backup.sh nightly >> /proc/1/fd/1 2>&1
15 * * * * /usr/local/bin/backup.sh if-missed >> /proc/1/fd/1 2>&1
CRON
echo "backup: scheduled (02:30 nightly, hourly catch-up)"
exec crond -f -l 8
