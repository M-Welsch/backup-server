#!/bin/bash
ssh nas "for i in 1 2 3 4 5 6 7 8 9 10; do dd if=/dev/urandom of=datasource/dummy_file_$i.txt count=1024 bs=1024; done"

