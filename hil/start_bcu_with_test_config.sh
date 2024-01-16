#!/bin/bash

cat /home/base/backup-server/hil/.base_password | sudo -S systemctl start backupserver@\\x2d\\x2dconfig\\x20config_hiltest.yaml

