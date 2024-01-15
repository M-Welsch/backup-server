# create user and enable user

useradd -m base
usermod -aG sudo base

# login as base
usermod -aG dialout base
ssh-keygen -t rsa

## linux config

### systemd (so bcu starts up on system startup)

cat setup/backupserver.service | sudo tee /etc/systemd/system/backupserver@.service > /dev/null
sudo systemctl daemon-reload
sudo systemctl enable backupserver@$(systemd-escape " --source backup_data_source").service

### udev (so the backup hdd and pcu serial interface are recognized and named)

cat setup/99-backupserver.rules | sudo tee /etc/udev/rules.d/99-backupserver.rules > /dev/null
sudo reload udev

### fstab (so we can mount our BackupHdd)

sudo mkdir /media/BackupHDD
cat setup/fstab | sudo tee -a /etc/fstab > /dev/null

### ssh (so we communicate with nas)

cat setup/config | tee -a ~/.ssh/config > /dev/null
ssh-copy-id -i ~/.ssh/id_rsa.pub nas

### sudoers (enable base to perform shutdown)

cat setup/sudoers | sudo tee -a /etc/sudoers > /dev/null

## Hints

```shell
# start backup-server
systemctl start backupserver@$(systemd-escape " --source backup_data_source").service

# supervise
journalctl -u 'backupserver@*'
```
