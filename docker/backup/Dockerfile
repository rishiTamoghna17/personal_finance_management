# Nightly encrypted backup: restic + rclone (Google Drive) + the PostgreSQL client. Same versions on the Mac and on Oracle (arm64).
FROM restic/restic:0.18.1
RUN apk add --no-cache postgresql17-client tzdata rclone
COPY backup.sh /usr/local/bin/backup.sh
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 0755 /usr/local/bin/backup.sh /usr/local/bin/entrypoint.sh
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
