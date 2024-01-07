# create user and enable user

useradd -m base
usermod -aG sudo base

# login as base
usermod -aG dialout base
ssh-keygen -t rsa

## linux config

### systemd (so bcu starts up on system startup)

cat setup/backupserver.service | sudo tee /etc/systemd/system/backupserver.service > /dev/null
sudo systemctl daemon-reload
sudo systemctl enable backupserver

### udev (so the backup hdd and pcu serial interface are recognized and named)

cat setup/99-backupserver.rules | sudo tee /etc/udev/rules.d/99-backupserver.rules > /dev/null
sudo reload udev

### fstab (so we can mount our BackupHdd)

sudo mkdir /media/BackupHDD
cat setup/fstab | sudo tee -a /etc/fstab > /dev/null

### ssh (so we communicate with nas)

cat setup/config | tee -a ~/.ssh/config > /dev/null
ssh-copy-id -i ~/.ssh/id_rsa.pub nas
for i in 1 2 3 4 5 6 7 8 9 10; do dd if=/dev/urandom of=dummy_file_$i.txt count=1024 bs=1024; done