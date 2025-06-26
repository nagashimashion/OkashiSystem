#!/bin/bash

# 接続が確立されるまで待機
while ! ping -c 1 -W 1 google.com &> /dev/null; do
    echo "ネットワーク接続を待っています..."
    sleep 1
done

echo "ネットワーク接続完了。アプリケーションを起動します。"
# 自身の環境に合わせて、main.pyが存在するディレクトリへのフルパスを記載してください
cd /home/andolab/okashi-system/
python3 main.py